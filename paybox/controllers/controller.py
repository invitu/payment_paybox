# coding: utf-8
from openerp.addons.web import http as openerpweb
import logging
from openerp.modules.registry import RegistryManager
from openerp import pooler, SUPERUSER_ID

logger = logging.getLogger(__name__)


class PayboxController(openerpweb.Controller):
    _cp_path = '/paybox'

    @openerpweb.httprequest
    def index(self, req, **kw):
        params = req.params
        ref, db, montant = params['Ref'], params['db'], params['Montant']
        erreur = params['Erreur']
        cr = pooler.get_db(db)
        self.registry = RegistryManager.get(db)
        invoice = self.registry.get("account.invoice")
        if ref and montant and erreur == '00000':
            logger.info(u"Paiement effectué avec succès")
            invoice.validate_invoice_paybox(cr, SUPERUSER_ID, ref, montant)
        else:
            logger.info(u"Une erreur s'est produite, le paiement n'a pu être effectué")
            return "<h2 style='color: red'> Une erreur s'est produite, le paiement n'a pu être effectué </h2>"
