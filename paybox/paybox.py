from openerp.osv import osv


class Paybox(osv.Model):

    _inherit = 'portal.payment.acquirer'
