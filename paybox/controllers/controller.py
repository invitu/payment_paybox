# coding: utf-8
from openerp.addons.web import http as openerpweb
import logging
from openerp.modules.registry import RegistryManager
from openerp import pooler, SUPERUSER_ID
from ..paybox_signature import Signature
import urllib
import werkzeug.utils

logger = logging.getLogger(__name__)

sign = Signature()
pubkey = 'http://www1.paybox.com/wp-content/uploads/2014/03/pubkey.pem'
base_url = '#id=%s&view_type=form&model=account.invoice&menu_id=%s&action=%s'
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

    def build_args(self, args):
        msg = 'Mt='+args['Mt']+'&Ref='+urllib.quote_plus(args['Ref'])+'&Auto='+args['Auto']
        msg += '&Erreur='+args['Erreur']+'&Signature='+args['Signature']
        return msg

    def validate_invoice(self, cr, db, ref, montant):
        """ validate the invoice """
        self.registry = RegistryManager.get(db)
        invoice = self.registry.get("account.invoice")
        resp = invoice.validate_invoice_paybox(cr, SUPERUSER_ID, ref, montant)
        return resp

    def get_invoice_state(self, cr, db, invoice_id):
        """ return state of the given invoice id """
        self.registry = RegistryManager.get(db)
        invoice = self.registry.get("account.invoice")
        if not invoice_id:
            return False
        state = invoice.browse(cr, SUPERUSER_ID, invoice_id).state
        return state

    def invoice_message_post(self, cr, db, invoice_id, title, msg):
        """ post message to the openchatter of the invoice """
        self.registry = RegistryManager.get(db)
        invoice = self.registry.get("account.invoice")
        invoice.message_post(
            cr, SUPERUSER_ID, invoice_id, msg, title)

    def get_invoice_id(self, cr, db, ref):
        """ return the invoice id for the ref given """
        self.registry = RegistryManager.get(db)
        invoice = self.registry.get("account.invoice")
        invoice_ids = invoice.search(cr, SUPERUSER_ID, [('number', '=', ref)])
        if not invoice_ids:
            logger.warning(u"[Paybox] - Action impossible, facture %s non trouvée" % (ref))
            return False
        return invoice_ids[0]

    def check_error_code(self, erreur):
        """ check if the error code is a real error or not.
            it also build the message that will be display to the customer """
        if erreur in ERROR_CODE:
            error_msg = ERROR_CODE[erreur]
            return error_msg
        else:
            for err in ERROR_CODE:
                if erreur.startswith(err):
                    error_msg = AUTH_CODE[erreur[-2:]]
                    return error_msg
        return False

    def get_invoice_url(self, cr, db, invoice_id):
        self.registry = RegistryManager.get(db)
        if not invoice_id:
            return '/'
        values = self.registry.get('paybox.settings').get_default_paybox_settings(
            cr, SUPERUSER_ID, None, None)
        return base_url % (invoice_id, values['menu'], values['action'])

    def compute_response(self, cr, params, msg):
        """ check response and do what we are supposed to do """
        key = urllib.urlopen(pubkey).read()
        # we maybe need to handle cases when db & ref are not in params
        db, ref = params['db'], params['Ref']
        invoice_id = self.get_invoice_id(cr, db, ref)
        url = self.get_invoice_url(cr, db, invoice_id)
        if 'Erreur' not in params:
            self.invoice_message_post(
                cr, db, [invoice_id], u"Paiement refusé", u"Paramètre 'Erreur' non trouvé")
            return url
        if 'Auto' not in params:
            self.invoice_message_post(
                cr, db, [invoice_id], u"Paiement refusé", u"Paramètre 'Auto' non trouvé")
            return url
        if 'Signature' not in params:
            self.invoice_message_post(
                cr, db, [invoice_id], u"Paiement refusé", u"Paramètre 'Signature' non trouvé")
            return url
        if 'Mt' not in params:
            self.invoice_message_post(
                cr, db, [invoice_id], u"Paiement refusé", u"Paramètre 'Mt' non trouvé")
            return url
        montant = params['Mt']
        erreur, signature = params['Erreur'], params['Signature']
        error_msg = self.check_error_code(erreur)
        if error_msg:
            self.invoice_message_post(
                cr, db, [invoice_id], u"Paiement annulé ou refusé",
                u"Une erreur est survenue : %s" % (error_msg))
            return url
        if not sign.verify(signature, msg, key):
            self.invoice_message_post(
                cr, db, [invoice_id], u"Paiement refusé", u"Signature non vérifiée")
            return url
        if ref and montant and erreur in ERROR_SUCCESS:
            if self.get_invoice_state(cr, db, invoice_id) == 'paid':
                logger.info(u"Facture déjà payée", u"Paiement non pris en compte")
                # self.invoice_message_post(
                #    cr, db, [invoice_id], u"Facture déjà payée",
                #    u"Paiement en ligne non pris en compte")
                return url
            invoice_id = self.validate_invoice(cr, db, ref, montant)
            if not invoice_id:
                return url
            self.invoice_message_post(
                cr, db, [invoice_id], u"Paiement en ligne accepté",
                u"Montant : %s" % (float(int(montant)/100)))
            return url
        else:
            logger.info(u"[Paybox] - Une erreur s'est produite, le paiement n'a pu être effectué")
            self.invoice_message_post(
                cr, db, [invoice_id], u"Paiement refusé", u"Une erreur est survenue")
            return url

    @openerpweb.httprequest
    def index(self, req, **kw):
        logger.info(u"EFFECTUE")
        cr = pooler.get_db(req.params['db']).cursor()
        msg = req.httprequest.environ['QUERY_STRING']
        url = self.compute_response(cr, req.params, msg)
        cr.commit()
        cr.close()
        return werkzeug.utils.redirect(url, 303)

    @openerpweb.httprequest
    def ipn(self, req, **kw):
        logger.info(u"IPN")
        cr = pooler.get_db(req.params['db']).cursor()
        # The 'db' args is not used to construct the signature
        if req.httprequest.environ['REQUEST_METHOD'] == 'GET':
            msg = req.httprequest.environ['QUERY_STRING']
            mt_pos = msg.find('&Mt')
            msg = msg[mt_pos:]
        else:
            args = req.httprequest.form
            msg = self.build_args(args)
        self.compute_response(cr, req.params, msg)
        cr.commit()
        cr.close()
        return ""

    @openerpweb.httprequest
    def refused(self, req, **kw):
        logger.info(u"REFUSE")
        cr = pooler.get_db(req.params['db']).cursor()
        if 'Ref' not in req.params:
            cr.close()
            return werkzeug.utils.redirect('/', 303)
        invoice_id = self.get_invoice_id(cr, req.params['db'], req.params['Ref'])
        url = self.get_invoice_url(cr, req.params['db'], invoice_id)
        cr.commit()
        cr.close()
        return werkzeug.utils.redirect(url, 303)

    @openerpweb.httprequest
    def cancelled(self, req, **kw):
        logger.info(u"ANNULE")
        cr = pooler.get_db(req.params['db']).cursor()
        if 'Ref' not in req.params:
            cr.close()
            return werkzeug.utils.redirect('/', 303)
        invoice_id = self.get_invoice_id(cr, req.params['db'], req.params['Ref'])
        url = self.get_invoice_url(cr, req.params['db'], invoice_id)
        cr.commit()
        cr.close()
        return werkzeug.utils.redirect(url, 303)
