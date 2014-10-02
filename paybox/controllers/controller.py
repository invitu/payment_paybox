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


class PayboxController(openerpweb.Controller):
    _cp_path = '/paybox'

    @openerpweb.httprequest
    def index(self, req, **kw):
        msg = req.httprequest.environ['QUERY_STRING']
        key = urllib.urlopen(pubkey).read()
        params = req.params
        ref, db, montant = params['Ref'], params['db'], params['Mt']
        signature = params['Signature']
        erreur = params['Erreur']
        verified = sign.verify(signature, msg, key)
        if not verified:
            raise osv.except_osv(u"Signature erronée", u"Le paiement ne peut-être enregistré")
        cr = pooler.get_db(db).cursor()
        self.registry = RegistryManager.get(db)
        invoice = self.registry.get("account.invoice")
        if ref and montant and erreur == '00000':
            logger.info(u"Paiement effectué avec succès")
            invoice_id = invoice.validate_invoice_paybox(cr, SUPERUSER_ID, ref, montant)
            url = '#id=%s&view_type=form&model=account.invoice&menu_id=254&action=285' % (invoice_id)
            return werkzeug.utils.redirect(url, 303)
        else:
            logger.info(u"Une erreur s'est produite, le paiement n'a pu être effectué")
            return "<h2 style='color: red'> Une erreur s'est produite, le paiement n'a pu être effectué </h2>"
