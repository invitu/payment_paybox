from openerp.osv import osv
import binascii
import hashlib
import hmac


class Paybox(osv.Model):

    _inherit = 'portal.payment.acquirer'


class HMAC(osv.Model):

    _name = 'hmac'

    def generate_hmac(self, key, hash_name, args):
        binary_key = binascii.unhexlify(key)
        concat_args = args
        try:
            hmac_value = hmac.new(binary_key, concat_args, hashlib.hash_name).hexdigest().upper()
        except:
            return False
        return hmac_value
