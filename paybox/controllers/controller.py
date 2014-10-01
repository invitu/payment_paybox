# coding: utf-8
from openerp.addons.web import http as openerpweb
import logging
from openerp.modules.registry import RegistryManager
from openerp import pooler, SUPERUSER_ID, osv
from ..paybox_signature import Signature

logger = logging.getLogger(__name__)

sign = Signature()


class PayboxController(openerpweb.Controller):
    _cp_path = '/paybox'

    @openerpweb.httprequest
    def index(self, req, **kw):
        params = req.params
        ref, db, montant = params['Ref'], params['db'], params['Mt']
        signature = params['Signature']
        erreur = params['Erreur']
        verified = sign.verify(signature)
        if not verified:
            raise osv.except_osv(u"Signature erronée", u"Le paiement ne peut-être enregistré")
        cr = pooler.get_db(db)
        self.registry = RegistryManager.get(db)
        invoice = self.registry.get("account.invoice")
        if ref and montant and erreur == '00000':
            logger.info(u"Paiement effectué avec succès")
            invoice.validate_invoice_paybox(cr, SUPERUSER_ID, ref, montant)
        else:
            logger.info(u"Une erreur s'est produite, le paiement n'a pu être effectué")
            return "<h2 style='color: red'> Une erreur s'est produite, le paiement n'a pu être effectué </h2>"
