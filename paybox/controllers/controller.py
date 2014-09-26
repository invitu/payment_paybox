import openerp.http as http
from openerp.http import request


class PayboxController(http.Controller):

    @http.route('/paybox/*', type='http')
    def get_response(self):
        import pdb
        pdb.set_trace()
        req = request
        print(req)
        return "<h1>This is a test</h1>"
