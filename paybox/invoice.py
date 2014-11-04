# coding: utf-8
from openerp.osv import osv
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class Invoice(osv.Model):

    _inherit = 'account.invoice'

    def get_credit_line(self, cr, uid, lines, montant, name, context=None):
        """ return index of the right line """
        invoice_number = name[7:]
        for line in lines:
            if not line['name'] == invoice_number:
                continue
            if not line['amount'] == montant:
                continue
            return True, lines.index(line)
        return False, False

    def get_invoice_id(self, cr, uid, ref, context=None):
        """ search and return invoice id for the given reference """
        invoice_ids = self.search(cr, uid, [('number', '=', ref)])
        if not invoice_ids:
            logger.warning(u"[Paybox] Action impossible", u"Facture %s non trouvée") % (ref)
            return False
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

    def create_move(self, cr, uid, invoice):
        journal = self.pool.get('account.journal')
        period = self.pool.get('account.period')
        move = self.pool.get('account.move')
        today = datetime.today()
        bank_journal_id = journal.search(cr, uid, [('code', '=', 'BNK2')])
        period_id = invoice.period_id.id if invoice else period.find(cr, uid, today)
        values = {'journal_id': bank_journal_id[0], 'period_id': period_id,
                  'date': today, 'name': '/'}
        move_id = move.create(cr, uid, values)
        return move_id

    def create_move_lines(self, cr, uid, invoice, move_id, montant):
        """ create move lines for the given amount and linked to given move_id """
        move_lines = []
        journal = self.pool.get('account.journal')
        period = self.pool.get('account.period')
        account = self.pool.get('account.account')
        move_line = self.pool.get('account.move.line')
        today = datetime.today()
        bank_journal_id = journal.search(cr, uid, [('code', '=', 'BNK2')])
        bank_account_id = account.search(cr, uid, [('code', '=', '512102')])
        customer_account_id = account.search(cr, uid, [('code', '=', '411100')])
        period_id = invoice.period_id.id if invoice else period.find(cr, uid, today)
        partner_id = invoice.partner_id.id if invoice else False
        values = {'journal_id': bank_journal_id[0], 'period_id': period_id,
                  'move_id': move_id, 'date': today, 'credit': montant,
                  'account_id': customer_account_id[0], 'name': '/',
                  'partner_id': partner_id}
        credit_line_id = move_line.create(cr, uid, values)
        move_lines.append(credit_line_id)
        values = {'journal_id': bank_journal_id[0], 'period_id': period_id,
                  'move_id': move_id, 'date': today, 'debit': montant,
                  'account_id': bank_account_id[0], 'name': '/',
                  'partner_id': partner_id}
        move_line.create(cr, uid, values)
        return move_lines

    def reconcile(self, cr, uid, invoice, line_id, montant):
        """ reconcile lines from line_ids """
        reconcile = self.pool.get('account.move.line.reconcile')
        move_line = self.pool.get('account.move.line')
        move_id = invoice.move_id.id
        move_line_id = move_line.search(
            cr, uid, ['&', ('move_id', '=', move_id), ('debit', '=', montant)])
        if not move_line_id:
            logger.warning(
                u"Le paiement de %s n'a pas été lettré",
                u"Vérifiez les montants et effectuer le lettrage manuellement") % (montant)
            return False
        line_id.append(move_line_id[0])
        context = {'active_ids': line_id}
        reconcile.trans_rec_reconcile_full(cr, uid, {}, context)
        return True

    def validate_invoice_paybox(self, cr, uid, ref, montant):
        """ Store payment for the referenced invoice with a specific amount
            Create a voucher to register the payment for the invoice given.
            Then run the workflow """
        # The amount is formatted in cent we need the convert the value
        montant = float(montant)/100
        invoice_id = self.get_invoice_id(cr, uid, ref)
        invoice = self.browse(cr, uid, invoice_id) if invoice_id else False
        move_id = self.create_move(cr, uid, invoice)
        move_line_id = self.create_move_lines(cr, uid, invoice, move_id, montant)
        if invoice:
            self.reconcile(cr, uid, invoice, move_line_id, montant)
        return invoice_id
