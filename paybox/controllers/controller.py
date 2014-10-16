# coding: utf-8
from openerp.addons.web import http as openerpweb
import logging
from openerp.modules.registry import RegistryManager
from openerp import pooler, SUPERUSER_ID
from openerp.osv import osv
from ..paybox_signature import Signature
import urllib
import werkzeug.utils

logger = logging.getLogger(__name__)

sign = Signature()
pubkey = 'http://www1.paybox.com/wp-content/uploads/2014/03/pubkey.pem'
base_url = '#id=%s&view_type=form&model=account.invoice&menu_id=254&action=285'
ERROR_SUCCESS = ['00000']
ERROR_CODE = {
    '00001': u"La connexion au centre d'autorisation a échoué ou une erreur interne est survenue",
    '001': u"Paiement refusé par le centre d'autorisation", '00003': u"Erreur Paybox",
    '00004': u"Numéro de porteur ou cryptogramme visuel invalide",
    '00006': u"Accès refusé ou site/rang/identifiant incorrect",
    '00008': u"Date de fin de validité incorrecte", '00009': u"Erreur de création d'un abonnement",
    '00010': u"Devise inconnue", '00011': u"Montant incorrect", '00015': u"Paiement déjà effectué",
    '00016': u"Abonné déjà existant", '00021': u"Carte non autorisée",
    '00029': u"Carte non conforme",
    '00030': u"Temps d'attente supérieur à 15 minutes par l'acheteur au niveau la page de paiement",
    '00033': u"Code pays de l'adresse IP du navigateur de l'acheteur non autorisé",
    '00040': u"Opération sans authentification 3-D Secure, bloquée par le filtre",
    }
AUTH_CODE = {
    '03': u"Commerçant invalide", '05': u"Ne pas honorer",
    '12': u"Transaction invalide", '13': u"Montant invalide",
    '14': u"Numéro de porteur invalide", '15': u"Emetteur de carte inconnu",
    '17': u"Annulation client", '19': u"Répéter la transaction ultérieurement",
    '20': u"Réponse erronée (erreur dans le domaine serveur)",
    '24': u"Mise à jour de fichier non supportée",
    '25': u"Impossible de localiser l'enregistrement dans le fichier",
    '26': u"Enregistrement dupliqué, ancien enregistrement remplacé",
    '27': u"Erreur en \"edit\" sur champ de mise à jour fichier",
    '28': u"Accès interdit au fichier", '29': u"Mise à jour de fichier impossible",
    '30': u"Erreur de format", '33': u"Carte expirée",
    '38': u"Nombre d'essais code confidentiel dépassé",
    '41': u"Carte perdue", '43': u"Carte volée", '51': u"Provision insuffisante ou crédit dépassé",
    '54': u"Date de validité de la carte dépassée", '55': u"Code confidentiel erroné",
    '56': u"Carte absente du fichier", '57': u"Transaction non permise à ce porteur",
    '58': u"Transaction interdite au terminal", '59': u"Suspicion de fraude",
    '60': u"L'accepteur de carte doit contacter l'acquéreur",
    '61': u"Dépasse la limite du montant de retrait",
    '63': u"Règles de sécurité non respectées",
    '68': u"Réponse non parvenue ou reçue trop tard",
    '75': u"Nombre d'essais code confidentiel dépassé",
    '76': u"Porteur déjà en opposition, ancien enregistrement conservé",
    '89': u"Echec de l'authentification", '90': u"Arrêt momentané du système",
    '91': u"Emetteur de carte inaccessible", '94': u"Demande dupliquée",
    '96': u"Mauvais fonctionnement du système",
    '97': u"Echéance de la temporisation de surveillance globale",
    }


class PayboxController(openerpweb.Controller):

    _cp_path = '/paybox'

    def check_error_code(self, erreur):
        """ check if the error code is a real error or not.
            it also build the message that will be display to the customer """
        if erreur in ERROR_CODE:
            error_msg = ERROR_CODE[erreur]
            return error_msg
        else:
            for err in ERROR_CODE:
                if erreur.startswith(err):
                    error_msg = AUTH_CODE[err[:-2]]
                    return error_msg
        return False

    def compute_response(self, params, msg, verbose=None):
        """ check response and do what we are supposed to do """
        ref, db, montant = params['Ref'], params['db'], params['Mt']
        erreur, signature = params['Erreur'], params['Signature']
        key = urllib.urlopen(pubkey).read()
        cr = pooler.get_db(db).cursor()
        self.registry = RegistryManager.get(db)
        invoice = self.registry.get("account.invoice")
        invoice_id = invoice.get_invoice_id(cr, SUPERUSER_ID, ref)
        if 'Auto' not in params:
            invoice.message_post(
                cr, SUPERUSER_ID, [invoice_id], u"Paramètre 'Auto' non trouvé",
                u"Paiement refusé")
            cr.commit()
            cr.close()
            return
        if 'Signature' not in params:
            invoice.message_post(
                cr, SUPERUSER_ID, [invoice_id], u"Paramètre 'Signature' non trouvé",
                u"Paiement refusé")
            cr.commit()
            cr.close()
            return
        error_msg = self.check_error_code(erreur)
        if error_msg:
            invoice.message_post(
                cr, SUPERUSER_ID, [invoice_id], u"Une erreur est survenue : %s " % (error_msg),
                u"Paiement refusé")
            cr.commit()
            cr.close()
            return
        if not sign.verify(signature, msg, key):
            invoice.message_post(
                cr, SUPERUSER_ID, [invoice_id], u"Signature incorrecte", u"Paiement refusé")
            cr.commit()
            cr.close()
            return
        if ref and montant and erreur in ERROR_SUCCESS:
            if invoice.browse(cr, SUPERUSER_ID, invoice_id).state == 'paid':
                invoice.message_post(
                    cr, SUPERUSER_ID, [invoice_id], u"Facture déjà payée",
                    u"Paiement non pris en compte")
                cr.commit()
                cr.close()
                return
            invoice_id = invoice.validate_invoice_paybox(cr, SUPERUSER_ID, ref, montant)
            invoice.message_post(
                cr, SUPERUSER_ID, [invoice_id], u"Montant : %s" % (float(int(montant)/100)),
                u"Paiement accepté")
            cr.commit()
            cr.close()
        else:
            logger.info(u"Une erreur s'est produite, le paiement n'a pu être effectué")
            invoice.message_post(
                cr, SUPERUSER_ID, [invoice_id], u"Une erreur est survenue",
                u"Paiement refusé")
            cr.commit()
            cr.close()
            return

    @openerpweb.httprequest
    def index(self, req, **kw):
        logger.info(u"EFFECTUE")
        msg = req.httprequest.environ['QUERY_STRING']
        return self.compute_response(req.params, msg, verbose=True)

    @openerpweb.httprequest
    def ipn(self, req, **kw):
        logger.info(u"IPN")
        msg = req.httprequest.environ['QUERY_STRING']
        return self.compute_response(req.params, msg, verbose=False)

    @openerpweb.httprequest
    def refused(self, req, **kw):
        logger.info(u"REFUSE")
        erreur = req.params['Erreur']
        return self.check_error_code(erreur)

    @openerpweb.httprequest
    def cancelled(self, req, **kw):
        logger.info(u"ANNULE")
        params = req.params
        ref, db = params['Ref'], params['db']
        cr = pooler.get_db(db).cursor()
        self.registry = RegistryManager.get(db)
        invoice = self.registry.get('account.invoice')
        invoice_id = invoice.get_invoice_id(cr, SUPERUSER_ID, ref)
        url = base_url % (invoice_id)
        cr.close()
        return werkzeug.utils.redirect(url, 303)
