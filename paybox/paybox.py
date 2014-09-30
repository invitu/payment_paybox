from openerp.osv import osv
import binascii
import hashlib
import hmac
from urllib import quote as quote
import logging
from datetime import datetime
from openerp.tools.translate import _
from openerp.tools import float_repr


_logger = logging.getLogger(__name__)

try:
    from mako.template import Template as MakoTemplate
except ImportError:
    _logger.warning("Mako templates not available, payment acquirer will not work!")


HASH = {'SHA512': hashlib.sha512}


class PayboxAcquirer(osv.Model):

    _inherit = 'portal.payment.acquirer'

    def render_payment_block(self, cr, uid, object, reference, currency,
                             amount, context=None, **kwargs):
        """ Renders all visible payment acquirer forms for the given rendering context, and
            return them wrapped in an appropriate HTML block, ready for direct inclusion
            in an OpenERP v7 form view """
        acquirer_ids = self.search(cr, uid, [('visible', '=', True)])
        if not acquirer_ids:
            return
        html_forms = []
        # add dbname in the invoice ref to get it back in the controller
        # reference += '-'+cr.dbname
        for this in self.browse(cr, uid, acquirer_ids):
            # Paybox case
            acquirer = this.name
            if acquirer == 'Paybox':
                # The secret key, need to be stored somewhere else
                key = '0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF'
                # The paybox amount is formated in cents so we need to convert
                amount = int(amount*100)
                # These are test variables
                devise = 978
                _hash = 'SHA512'
                identifiant = 110647233
                rang = 32
                site = 1999888
                porteur = 'test@paybox.com'
                retour = 'Mt:M;Ref:R;Auto:A;Erreur:E;Signature:K'
                url_effectue = 'http://localhost:8069/paybox'
                time = datetime.now()
                # We need to concatenate the args to compute the hmac
                args = ('PBX_SITE=' + str(site) + '&PBX_RANG=' + str(rang) +
                        '&PBX_HASH=' + _hash + '&PBX_CMD=' + reference +
                        '&PBX_IDENTIFIANT=' + str(identifiant) + '&PBX_TOTAL=' + str(amount) +
                        '&PBX_DEVISE=' + str(devise) + '&PBX_PORTEUR=' + porteur +
                        '&PBX_RETOUR=' + retour + '&PBX_TIME=' + str(time) +
                        '&PBX_EFFECTUE=' + url_effectue + '&PBX_RUF1=' + 'POST' +
                        '&PBX_REPONDRE_A=' + 'http://localhost:8069')
                hmac = self.compute_hmac(key, _hash, args)
                content = this.render(
                    object, reference, devise, amount, hmac=hmac,
                    identifiant=identifiant, rang=rang, site=site, time=time, devise=devise,
                    retour=retour, effectue=url_effectue, context=context, **kwargs)
            else:
                content = this.render(
                    object, reference, currency, amount, context=context, **kwargs)
            if content:
                html_forms.append(content)
        html_block = '\n'.join(filter(None, html_forms))
        return self._wrap_payment_block(
            cr, uid, html_block, amount, currency, acquirer=acquirer, context=context)

    def compute_hmac(self, key, hash_name, args):
        binary_key = binascii.unhexlify(key)
        concat_args = args
        try:
            hmac_value = hmac.new(binary_key, concat_args, HASH[hash_name]).hexdigest().upper()
        except:
            return False
        return hmac_value

    def render(self, cr, uid, id, object, reference, currency, amount,
               identifiant=None, rang=None, site=None, time=None, devise=None, retour=None,
               effectue=None, hmac=None, context=None, **kwargs):
        """ Renders the form template of the given acquirer as a mako template  """
        if not isinstance(id, (int, long)):
            id = id[0]
        this = self.browse(cr, uid, id)
        if context is None:
            context = {}
        try:
            i18n_kind = _(object._description)  # may fail to translate, but at least we try
            if this.name == 'Paybox':
                result = MakoTemplate(this.form_template).render_unicode(
                    object=object, reference=reference, currency=currency,
                    amount=amount, identifiant=identifiant, rang=rang, site=site, effectue=effectue,
                    time=time, devise=devise, retour=retour, hmac=hmac, kind=i18n_kind,
                    quote=quote, ctx=context, format_exceptions=True)
            else:
                result = MakoTemplate(this.form_template).render_unicode(
                    object=object, reference=reference, currency=currency,
                    amount=amount, kind=i18n_kind, quote=quote, ctx=context,
                    format_exceptions=True)
            return result.strip()
        except Exception:
            _logger.exception("failed to render mako template value for payment.acquirer %s: %r",
                              this.name, this.form_template)
            return

    def _wrap_payment_block(self, cr, uid, html_block, amount, currency, acquirer=None, context=None):
        if not html_block:
            link = '#action=account.action_account_config'
            payment_header = _('You can finish the configuration in the <a href="%s">Bank&Cash settings</a>') % link
            amount = _('No online payment acquirers configured')
            group_ids = self.pool.get('res.users').browse(cr, uid, uid, context=context).groups_id
            if any(group.is_portal for group in group_ids):
                return ''
        else:
            payment_header = _('Pay safely online')
            currency_str = currency.symbol or currency.name
            if acquirer and acquirer == 'Paybox':
                amount_str = float_repr(
                    (float(amount)/100),
                    self.pool.get('decimal.precision').precision_get(cr, uid, 'Account'))
                amount = u"%s %s" % ((currency_str, amount_str) if currency.position == 'before' else (amount_str, currency_str))
            else:
                amount_str = float_repr(
                    amount, self.pool.get('decimal.precision').precision_get(cr, uid, 'Account'))
                amount = u"%s %s" % ((currency_str, amount_str) if currency.position == 'before' else (amount_str, currency_str))

        result = """<div class="payment_acquirers">
                         <div class="payment_header">
                             <div class="payment_amount">%s</div>
                             %s
                         </div>
                         %%s
                     </div>""" % (amount, payment_header)
        return result % html_block
