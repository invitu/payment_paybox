# coding: utf-8
from openerp.osv import osv, fields
import hashlib
import hmac
import logging
from random import sample
from string import ascii_letters, digits

URL = [('https://preprod-tpeweb.paybox.com/', 'Test pré-production'),
       ('https://tpeweb.paybox.com', 'Production'),
       ('https://tpeweb1.paybox.com', 'Production (secours)')]

_logger = logging.getLogger(__name__)

magic_md5 = '$1$'
magic_sha256 = '$5$'


def gen_salt(length=8, symbols=None):
    if symbols is None:
        symbols = ascii_letters + digits
    return ''.join(sample(symbols, length))


def md5crypt(raw_pw, salt, magic=magic_md5):
    """ md5crypt FreeBSD crypt(3) based on but different from md5

    The md5crypt is based on Mark Johnson's md5crypt.py, which in turn is
    based on  FreeBSD src/lib/libcrypt/crypt.c (1.2)  by  Poul-Henning Kamp.
    Mark's port can be found in  ActiveState ASPN Python Cookbook.  Kudos to
    Poul and Mark. -agi

    Original license:

    * "THE BEER-WARE LICENSE" (Revision 42):
    *
    * <phk@login.dknet.dk>  wrote  this file.  As  long as  you retain  this
    * notice  you can do  whatever you want with this stuff. If we meet some
    * day,  and you think this stuff is worth it,  you can buy me  a beer in
    * return.
    *
    * Poul-Henning Kamp
    """
    raw_pw = raw_pw.encode('utf-8')
    salt = salt.encode('utf-8')
    hash = hashlib.md5()
    hash.update(raw_pw + magic + salt)
    st = hashlib.md5()
    st.update(raw_pw + salt + raw_pw)
    stretch = st.digest()

    for i in range(0, len(raw_pw)):
        hash.update(stretch[i % 16])

    i = len(raw_pw)

    while i:
        if i & 1:
            hash.update('\x00')
        else:
            hash.update(raw_pw[0])
        i >>= 1

    saltedmd5 = hash.digest()

    for i in range(1000):
        hash = hashlib.md5()

        if i & 1:
            hash.update(raw_pw)
        else:
            hash.update(saltedmd5)

        if i % 3:
            hash.update(salt)
        if i % 7:
            hash.update(raw_pw)
        if i & 1:
            hash.update(saltedmd5)
        else:
            hash.update(raw_pw)

        saltedmd5 = hash.digest()

    itoa64 = './0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'

    rearranged = ''
    for a, b, c in ((0, 6, 12), (1, 7, 13), (2, 8, 14), (3, 9, 15), (4, 10, 5)):
        v = ord(saltedmd5[a]) << 16 | ord(saltedmd5[b]) << 8 | ord(saltedmd5[c])

        for i in range(4):
            rearranged += itoa64[v & 0x3f]
            v >>= 6

    v = ord(saltedmd5[11])

    for i in range(2):
        rearranged += itoa64[v & 0x3f]
        v >>= 6

    return magic + salt + '$' + rearranged


def sh256crypt(cls, password, salt, magic=magic_sha256):
    # see http://en.wikipedia.org/wiki/PBKDF2
    result = password.encode('utf8')
    for i in xrange(cls.iterations):
        # uses HMAC (RFC 2104) to apply salt
        result = hmac.HMAC(result, salt, hashlib.sha256).digest()
    # doesnt seem to be crypt(3) compatible
    result = result.encode('base64')
    return '%s%s$%s' % (magic_sha256, salt, result)


class PayboxSettings(osv.Model):

    _inherit = 'res.config.settings'
    _name = 'paybox.settings'

    def set_key(self, cr, uid, id, name, value, args, context):
        import pdb
        pdb.set_trace()
        if value:
            encrypted = md5crypt(value, gen_salt())
            cr.execute("update ir_config_parameter set value=%s where id=%s", (encrypted, id))
        del value

    def get_key(self, cr, uid, ids, name, args, context):
        cr.execute("select id, value from ir_config_parameter where key = 'paybox.key';")
        import pdb
        pdb.set_trace()
        stored_key = cr.fetchall()
        res = {}
        for id, key in stored_key:
            res[id] = key
        return res

    _columns = {'site': fields.char("Site", size=7),
                'rank': fields.char("Rank", size=2),
                'shop_id': fields.char("Shop id", size=9),
                'key': fields.function(get_key, fnct_inv=set_key, type='char',
                                       string='Key', invisible=True, store=True),
                'crypt_key': fields.char("Key", password=True),
                'porteur': fields.char("Porteur"),
                'hash': fields.selection([('SHA512', 'sha512')], "Hash", select=True),
                'url': fields.selection(URL, u"URL d'appel", select=True),
                'retour': fields.char(u"URL utilisée pour la redirection"),
                'method': fields.selection([('POST', 'Post'), ('GET', 'Get')], u"Méthode",
                                           select=True),
                'devise': fields.selection([('978', 'Euro'), ('840', 'US Dollar')], u"Devise",
                                           select=True),
                }

    _defaults = {'hash': 'SHA512',
                 'url': 'https://preprod-tpeweb.paybox.com/',
                 'method': 'POST',
                 'devise': '978',
                 }

    def get_default_paybox_settings(self, cr, uid, ids, context=None):
        cfg_param = self.pool.get('ir.config_parameter')
        site = cfg_param.get_param(cr, uid, 'paybox.site') or ""
        rank = cfg_param.get_param(cr, uid, 'paybox.rank') or ""
        shop_id = cfg_param.get_param(cr, uid, 'paybox.shop_id') or ""
        key = cfg_param.get_param(cr, uid, 'paybox.key') or ""
        porteur = cfg_param.get_param(cr, uid, 'paybox.porteur') or ""
        hashname = cfg_param.get_param(cr, uid, 'paybox.hash') or ""
        url = cfg_param.get_param(cr, uid, 'paybox.url') or ""
        retour = cfg_param.get_param(cr, uid, 'paybox.retour') or ""
        method = cfg_param.get_param(cr, uid, 'paybox.method') or ""
        devise = cfg_param.get_param(cr, uid, 'paybox.devise') or ""
        return {'site': site, 'rank': rank, 'shop_id': shop_id,
                'key': key, 'porteur': porteur, 'hash': hashname, 'url': url,
                'retour': retour, 'method': method, 'devise': devise}

    def set_devise(self, cr, uid, ids, context=None):
        for i in ids:
            devise = self.browse(cr, uid, i, context)["devise"] or ""
            self.pool.get("ir.config_parameter").set_param(cr, uid, "paybox.devise", devise)

    def set_method(self, cr, uid, ids, context=None):
        for i in ids:
            method = self.browse(cr, uid, i, context)["method"] or ""
            self.pool.get("ir.config_parameter").set_param(cr, uid, "paybox.method", method)

    def set_retour(self, cr, uid, ids, context=None):
        for i in ids:
            retour = self.browse(cr, uid, i, context)["retour"] or ""
            self.pool.get("ir.config_parameter").set_param(cr, uid, "paybox.retour", retour)

    def set_site(self, cr, uid, ids, context=None):
        for i in ids:
            site = self.browse(cr, uid, i, context)["site"] or ""
            self.pool.get("ir.config_parameter").set_param(cr, uid, "paybox.site", site)

    def set_rank(self, cr, uid, ids, context=None):
        for i in ids:
            rank = self.browse(cr, uid, i, context)["rank"] or ""
            self.pool.get("ir.config_parameter").set_param(cr, uid, "paybox.rank", rank)

    def set_shop_id(self, cr, uid, ids, context=None):
        for i in ids:
            shop_id = self.browse(cr, uid, i, context)["shop_id"] or ""
            self.pool.get("ir.config_parameter").set_param(cr, uid, "paybox.shop_id", shop_id)

    def set_key(self, cr, uid, ids, context=None):
        for i in ids:
            key = self.browse(cr, uid, i, context)["key"] or ""
            self.pool.get("ir.config_parameter").set_param(cr, uid, "paybox.key", key)

    def set_porteur(self, cr, uid, ids, context=None):
        for i in ids:
            porteur = self.browse(cr, uid, i, context)["porteur"] or ""
            self.pool.get("ir.config_parameter").set_param(cr, uid, "paybox.porteur", porteur)

    def set_hash(self, cr, uid, ids, context=None):
        for i in ids:
            hashname = self.browse(cr, uid, i, context)["hash"] or ""
            self.pool.get("ir.config_parameter").set_param(cr, uid, "paybox.hash", hashname)

    def set_url(self, cr, uid, ids, context=None):
        for i in ids:
            url = self.browse(cr, uid, i, context)["url"] or ""
            self.pool.get("ir.config_parameter").set_param(cr, uid, "paybox.url", url)
