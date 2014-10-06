from openerp.osv import osv, fields


class PayboxSettings(osv.Model):

    _inherit = 'res.config.settings'
    _name = 'paybox.settings'

    _columns = {'site': fields.char('Site'),
                'rank': fields.char('Rank'),
                'shop_id': fields.char('Shop id'),
                'key': fields.char('Key', password=True), }

    def get_paybox_settings(self, cr, uid, ids, context=None):
        cfg_param = self.pool.get('ir.config_parameter')
        site = cfg_param.get_param(cr, uid, 'paybox.site') or ''
        rank = cfg_param.get_param(cr, uid, 'paybox.rank') or ''
        shop_id = cfg_param.get_param(cr, uid, 'paybox.shop_id') or ''
        key = cfg_param.get_param(cr, uid, 'paybox.key') or ''
        return {'site': site, 'rank': rank, 'shop_id': shop_id, 'key': key}

    def set_site(self, cr, uid, ids, context=None):
        for i in ids:
            site = self.browse(cr, uid, i, context)["site"] or cr.dbname or ""
            self.pool.get("ir.config_parameter").set_param(cr, uid, "paybox.site", site)

    def set_rank(self, cr, uid, ids, context=None):
        for i in ids:
            rank = self.browse(cr, uid, i, context)["rank"] or cr.dbname or ""
            self.pool.get("ir.config_parameter").set_param(cr, uid, "paybox.rank", rank)

    def set_shop_id(self, cr, uid, ids, context=None):
        for i in ids:
            shop_id = self.browse(cr, uid, i, context)["shop_id"] or cr.dbname or ""
            self.pool.get("ir.config_parameter").set_param(cr, uid, "paybox.shop_id", shop_id)

    def set_key(self, cr, uid, ids, context=None):
        for i in ids:
            key = self.browse(cr, uid, i, context)["key"] or cr.dbname or ""
            self.pool.get("ir.config_parameter").set_param(cr, uid, "paybox.key", key)
