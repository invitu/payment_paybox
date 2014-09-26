from openerp.addons.web import http as http
from openerp.addons.web.http import httprequest as request


class PayboxController(http.Controller):
    _cp_path = '/paybox/'

    @http.httprequest
    def get_response(self):
        import pdb
        pdb.set_trace()
        req = request
        print(req)
        return "<h1>This is a test</h1>"
