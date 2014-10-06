# coding: utf-8
from openerp.osv import osv
from datetime import datetime


class Invoice(osv.Model):

    _inherit = 'account.invoice'

    def get_invoice_id(self, cr, uid, ref, context=None):
        """ search and return invoice id for the given reference """
        invoice_ids = self.search(cr, uid, [('number', '=', ref)])
        if not invoice_ids:
            raise osv.except_osv(u"Action impossible", u"Facture %s non trouvée") % (ref)
        return invoice_ids[0]

    def _portal_payment_block(self, cr, uid, ids, fieldname, arg, context=None):
        """ invoice residual amount is used instead of total amount """
        result = dict.fromkeys(ids, False)
        payment_acquirer = self.pool.get('portal.payment.acquirer')
        for this in self.browse(cr, uid, ids, context=context):
            if(this.type == 'out_invoice' and this.state not in ('draft', 'done')
               and not this.reconciled):
                result[this.id] = payment_acquirer.render_payment_block(
                    cr, uid, this, this.number, this.currency_id, this.residual, context=context)
        return result

    def create_voucher(self, cr, uid, invoice_id, partner_id, montant, name, context=None):
        """ Create the voucher with the right context to create move and move lines
            that will be reconcile """
        voucher = self.pool.get('account.voucher')
        journal = self.pool.get('account.journal')
        account = self.pool.get('account.account')
        bank_journal_id = journal.search(cr, uid, [('name', '=', 'Bank')])
        bank_account_id = account.search(cr, uid, [('name', '=', 'Bank')])
        if not bank_account_id:
            raise osv.except_osv(u"Action impossible",
                                 u"Le compte 'Bank' n'a pas été trouvé")
        if not bank_journal_id:
            raise osv.except_osv(u"Action impossible",
                                 u"Le journal 'Bank' n'a pas été trouvé")
        journal_id = bank_journal_id[0]
        account_id = bank_account_id[0]
        today = datetime.strftime(datetime.today(), '%Y-%m-%d')
        context = {'default_amount': montant, 'default_reference': False, 'uid': 1,
                   'invoice_type': 'out_invoice', 'journal_type': 'sale', 'default_type': 'receipt',
                   'date': today,
                   'search_disable_custom_filters': True, 'voucher_special_currency_rate': 1.0,
                   'default_partner_id': partner_id, 'payment_expected_currency': 1,
                   'active_id': invoice_id, 'close_after_process': True, 'tz': 'Europe/Paris',
                   'active_model': 'account.invoice', 'invoice_id': invoice_id,
                   'voucher_special_currency': 1, 'active_ids': [invoice_id], 'type': 'receipt'}
        values = voucher.recompute_voucher_lines(
            cr, uid, [], partner_id, journal_id, montant,
            1, 'receipt', today, context=context)
        value = values['value']
        values.pop('value')
        values.update(account_id=account_id, name=name)
        values['line_cr_ids'] = [[5, False, False], [0, False, value['line_cr_ids'][0]]]
        voucher_id = voucher.create(cr, uid, values, context=context)
        return voucher_id

    def validate_invoice_paybox(self, cr, uid, ref, montant):
        """ Store payment for the referenced invoice with a specific amount
            Create a voucher to register the payment for the invoice given.
            Then run the workflow """
        context = {}
        # The amount is formatted in cent we need the convert the value
        montant = float(montant)/100
        voucher = self.pool.get('account.voucher')
        invoice_id = self.search(cr, uid, [('number', '=', ref)])
        if not invoice_id:
            raise osv.except_osv(u"La facture %s n'a pas été trouvée",
                                 u"Prenez contact avec l'administrateur") % (ref)
        invoice_id = invoice_id[0]
        invoice = self.browse(cr, uid, invoice_id)
        name = 'Paybox %s' % (invoice.number)
        partner_id = invoice.partner_id.id
        voucher_id = self.create_voucher(cr, uid, invoice_id, partner_id, montant, name)
        voucher.button_proforma_voucher(cr, uid, [voucher_id], context)
        return invoice_id