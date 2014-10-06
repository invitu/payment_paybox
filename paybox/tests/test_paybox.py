# coding: utf-8

from openerp.tests.common import TransactionCase
from ..paybox_signature import Signature
import os
from openerp.osv import osv


class TestPaybox(TransactionCase):

    def setUp(self):
        super(TestPaybox, self).setUp()
        self.acquirer = self.registry('portal.payment.acquirer')
        self.invoice = self.registry('account.invoice')
        self.journal = self.registry('account.journal')
        self.account = self.registry('account.account')
        self.partner = self.registry('res.partner')
        self.product = self.registry('product.product')
        self.invoice_line = self.registry('account.invoice.line')

    def test_validate_invoice_paybox(self):
        cr, uid, context = self.cr, self.uid, {}
        product_account_id = self.account.search(cr, uid, [('code', '=', '707100')])[0]
        sale_journal = self.journal.search(cr, uid, [('code', '=', 'SAJ')])[0]
        company_id = 1
        partner = self.partner.create(cr, uid, {'name': 'test'})
        product_id = self.product.search(
            cr, uid, [('name_template', '=', 'Adhésion')])[0]
        acc = self.account.search(cr, uid, [('code', '=', '411100')])[0]
        datas = {'number': 'Facture Paybox Test', 'account_id': acc,
                 'partner_id': partner, 'journal_id': sale_journal, 'payment_term': None}
        context['active_ids'] = [partner]
        invoice_id = self.invoice.create(cr, uid, datas)
        self.invoice_line.create(
            cr, uid, {'account_id': product_account_id, 'name': 'Adhésion',
                      'invoice_id': invoice_id, 'price_unit': '100',
                      'price_subtotal': '100', 'company_id': company_id, 'discount': False,
                      'quantity': '1', 'partner_id': partner, 'product_id': product_id}, context)
        self.invoice.action_move_create(cr, uid, [invoice_id])
        self.invoice.invoice_validate(cr, uid, [invoice_id])
        invoice = self.invoice.browse(cr, uid, invoice_id)
        response = self.invoice.validate_invoice_paybox(cr, uid, invoice.number, invoice.residual)
        self.assertEquals(response, invoice.id)
        self.assertEquals(self.invoice.browse(cr, uid, invoice.id).state, 'paid')
        self.assertRaises(osv.except_osv, self.invoice, 'validate_invoice_paybox',
                          cr, uid, invoice.number, invoice.residual)

    def test_create_voucher(self):
        return True

    def test_compute_hmac(self):
        """ ensure that the hmac is well computed """
        key = '0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF'
        args = 'PBX_SITE=1999888&PBX_RANG=32&PBX_HASH=SHA512&PBX_CMD=SAJ/2014/8503&PBX_IDENTIFIANT=110647233&PBX_TOTAL=150.0&PBX_DEVISE=978&PBX_PORTEUR=test@paybox.com&PBX_RETOUR=Mt:M;Ref:R;Auto:A;Erreur:E&PBX_TIME=2014-09-29 10:26:17.542412'
        hash_name = 'SHA512'
        hmac = self.acquirer.compute_hmac(key, hash_name, args)
        self.assertEquals(hmac, '77C0800DF057BC78AA59879DE918168F59759A5F876B00447ABF5C7555A30BF1AFE0ACAD7D33B33415225AA4B5749005F89A05F130CF6D8D7677B77D1DB35A80')

    def test_verify_signature(self):
        """ verify the signature according to datas and public key """
        sign = Signature()
        path = os.path.dirname(os.path.abspath(__file__))
        key_path = path+'/pubkey.pem'
        sign_path = path+'/sig64.txt'
        data_path = path+'/data.txt'
        signature = open(sign_path, 'r').read()
        data = open(data_path, 'r').read()
        key = open(key_path, 'r').read()
        res = sign.verify(signature, data[:-1], key)
        self.assertTrue(res)
