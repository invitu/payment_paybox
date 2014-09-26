from openerp.addons.web import http as http
from openerp.addons.web.http import request as request


class PayboxController(http.Controller):

    @http.route('/paybox/*', type='http')
    def get_response(self):
        import pdb
        pdb.set_trace()
        req = request
        print(req)
        return "<h1>This is a test</h1>"
