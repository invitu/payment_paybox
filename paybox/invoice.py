# coding: utf-8
from openerp.osv import osv


class Invoice(osv.Model):

    _inherit = 'account.invoice'

    def validate_invoice_paybox(self, cr, uid, ref, montant):
        """ Store payment for the referenced invoice with a specific amount """
        context = {}
        voucher = self.pool.get('account.voucher')
        period_id = voucher._get_period(cr, uid)
        invoice_id = self.search(cr, uid, [('number', '=', ref)])
        if not invoice_id:
            raise osv.except_osv(u"La facture %s n'a pas été trouvée",
                                 u"Prenez contact avec l'administrateur") % (ref)
        invoice_id = invoice_id[0]
        invoice = self.browse(cr, uid, invoice_id)
        journal_id = invoice.journal_id.id
        account_id = invoice.account_id.id
        partner_id = invoice.partner_id.id
        name = 'Paybox %s' % (ref)
        voucher_id = voucher.create(
            cr, uid,
            {'name': name, 'journal_id': journal_id, 'account_id': account_id,
             'amount': montant, 'type': 'receipt', 'period_id': period_id,
             'partner_id': partner_id}, context)
        voucher.action_move_line_create(cr, uid, [voucher_id])
        return invoice_id
