# coding: utf-8
from openerp.addons.web import http as openerpweb
import logging
from openerp.modules.registry import RegistryManager


logger = logging.getLogger(__name__)


class PayboxController(openerpweb.Controller):
    _cp_path = '/paybox'

    @openerpweb.httprequest
    def index(self, req, **kw):
        params = req.params
        ref = params['Ref']
        # invoice = openerpweb.httprequest.registry.get("account.invoice")
        # invoice_id = None
        # if ref:
        #    invoice_id = invoice.search(req.cr, req.uid, [('number', '=', ref)])
        # if invoice_id:
        #    button = """
    # <form action='localhost:8069/id=%s&view_type=form&model=account.invoice&menu_id=254&action=285 method='POST'>
    #    <button value="*">Retour à la facture</button>
    # </form>
        #              """ % (invoice_id[0])
        if params['Erreur'] == '00000':
            logger.info(u"Paiement effectué avec succès")
            return "<h2 style='color: green'> Paiement effectué avec succès </h2>"
        else:
            logger.info(u"Une erreur s'est produite, le paiement n'a pu être effectué")
            return "<h2 style='color: red'> Une erreur s'est produite, le paiement n'a pu être effectué </h2>"
