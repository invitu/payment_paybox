# coding: utf-8
from openerp.addons.web import http as openerpweb


class PayboxController(openerpweb.Controller):
    _cp_path = '/paybox'

    @openerpweb.httprequest
    def index(self, req, **kw):
        return "<h1>This is a test</h1>"
