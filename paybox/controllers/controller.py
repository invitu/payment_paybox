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
AUTH_ERROR_CODE = {
    '03': u"Commerçant invalide",
    '05': u"Ne pas honorer",
    '12': u"Transaction invalide",
    '13': u"Montant invalide",
    '14': u"Numéro de porteur invalide",
    '15': u"Emetteur de carte inconnu",
    '17': u"Annulation client",
    '19': u"Répéter la transaction ultérieurement",
    '20': u"Réponse erronée (erreur dans le domaine serveur)",
    '24': u"Mise à jour de fichier non supportée",
    '25': u"Impossible de localiser l'enregistrement dans le fichier",
    '26': u"Enregistrement dupliqué, ancien enregistrement remplacé",
    '27': u"Erreur en \"edit\" sur champ de mise à jour fichier",
    '28': u"Accès interdit au fichier",
    '29': u"Mise à jour de fichier impossible",
    '30': u"Erreur de format",
    '33': u"Carte expirée",
    '38': u"Nombre d'essais code confidentiel dépassé",
    }


class PayboxController(openerpweb.Controller):

    _cp_path = '/paybox'

    @openerpweb.httprequest
    def index(self, req, **kw):
        msg = req.httprequest.environ['QUERY_STRING']
        key = urllib.urlopen(pubkey).read()
        params = req.params
        ref, db, montant = params['Ref'], params['db'], params['Mt']
        auth = params['Auto']
        signature = params['Signature']
        erreur = params['Erreur']
        verified = sign.verify(signature, msg, key)
        if not verified:
            raise osv.except_osv(u"Signature erronée", u"Le paiement ne peut-être enregistré")
        if auth in AUTH_ERROR_CODE:
            error_msg = AUTH_ERROR_CODE[auth]
            return "<h2> %s </h2>" % (error_msg)
        cr = pooler.get_db(db).cursor()
        self.registry = RegistryManager.get(db)
        invoice = self.registry.get("account.invoice")
        if ref and montant and erreur == '00000':
            logger.info(u"Paiement effectué avec succès")
            invoice_id = invoice.validate_invoice_paybox(cr, SUPERUSER_ID, ref, montant)
            url = base_url % (invoice_id)
            cr.commit()
            cr.close()
            return werkzeug.utils.redirect(url, 303)
        else:
            logger.info(u"Une erreur s'est produite, le paiement n'a pu être effectué")
            invoice_id = invoice.get_invoice_id(cr, SUPERUSER_ID, ref)
            url = base_url % (invoice_id)
            return werkzeug.utils.redirect(url, 303)

    @openerpweb.httprequest
    def refused(self, req, **kw):
        params = req.params
        ref, db = params['Ref'], params['db']
        cr = pooler.get_db(db).cursor()
        self.registry = RegistryManager.get(db)
        invoice = self.registry.get('account.invoice')
        invoice_id = invoice.get_invoice_id(cr, SUPERUSER_ID, ref)
        url = base_url % (invoice_id)
        return werkzeug.utils.redirect(url, 303)

    @openerpweb.httprequest
    def cancelled(self, req, **kw):
        params = req.params
        ref, db = params['Ref'], params['db']
        cr = pooler.get_db(db).cursor()
        self.registry = RegistryManager.get(db)
        invoice = self.registry.get('account.invoice')
        invoice_id = invoice.get_invoice_id(cr, SUPERUSER_ID, ref)
        url = base_url % (invoice_id)
        return werkzeug.utils.redirect(url, 303)
