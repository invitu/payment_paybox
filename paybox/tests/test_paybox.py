from openerp.tests.common import TransactionCase
from ..paybox_signature import Signature
import os


class TestPaybox(TransactionCase):

    def setUp(self):
        super(TestPaybox, self).setUp()
        self.acquirer = self.registry('portal.payment.acquirer')

    def test_compute_hmac(self):
        key = '0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF'
        args = 'PBX_SITE=1999888&PBX_RANG=32&PBX_HASH=SHA512&PBX_CMD=SAJ/2014/8503&PBX_IDENTIFIANT=110647233&PBX_TOTAL=150.0&PBX_DEVISE=978&PBX_PORTEUR=test@paybox.com&PBX_RETOUR=Mt:M;Ref:R;Auto:A;Erreur:E&PBX_TIME=2014-09-29 10:26:17.542412'
        hash_name = 'SHA512'
        hmac = self.acquirer.compute_hmac(key, hash_name, args)
        self.assertEquals(hmac, '77C0800DF057BC78AA59879DE918168F59759A5F876B00447ABF5C7555A30BF1AFE0ACAD7D33B33415225AA4B5749005F89A05F130CF6D8D7677B77D1DB35A80')

    def test_verify_signature(self):
        sign = Signature()
        path = os.path.dirname(os.path.abspath(__file__))
        key_path = path+'/pubkey.pem'
        sign_path = path+'/sig64.txt'
        data_path = path+'/data.txt'
        signature = open(sign_path, 'r').read()
        data = open(data_path, 'r').read()
        res = sign.verify(signature, data, key_path)
        self.assertTrue(res)
