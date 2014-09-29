from openerp.osv import osv


class paybox_account_invoice(osv.Model):

    _inherit = 'account.invoice'

    def _portal_payment_block(self, cr, uid, ids, fieldname, arg, context=None):
        result = dict.fromkeys(ids, False)
        payment_acquirer = self.pool.get('portal.payment.acquirer')
        for this in self.browse(cr, uid, ids, context=context):
            if(this.type == 'out_invoice' and this.state not in ('draft', 'done')
               and not this.reconciled):
                result[this.id] = payment_acquirer.render_payment_block(
                    cr, uid, this, this.number, this.currency_id, this.residual, context=context)
        return result
