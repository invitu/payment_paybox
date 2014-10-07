# coding: utf-8
from openerp.osv import osv, fields

URL = [('https://preprod-tpeweb.paybox.com/', 'Test pré-production'),
       ('https://tpeweb.paybox.com', 'Production'),
       ('https://tpeweb1.paybox.com', 'Production (secours)')]


class PayboxSettings(osv.Model):

    _inherit = 'res.config.settings'
    _name = 'paybox.settings'

    _columns = {'site': fields.char('Site', size=7),
                'rank': fields.char('Rank', size=2),
                'shop_id': fields.char('Shop id', size=9),
                'key': fields.char('Key', password=True),
                'porteur': fields.char('Porteur'),
                'hash': fields.selection([('sha512', 'SHA512')], 'Hash'),
                'url': fields.selection(URL, 'URL d\'appel'),
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
        return {'site': site, 'rank': rank, 'shop_id': shop_id,
                'key': key, 'porteur': porteur, 'hash': hashname, 'url': url}

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
