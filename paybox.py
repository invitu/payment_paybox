# coding: utf-8
from openerp.osv import osv
import binascii
import hashlib
import urllib
import logging
from datetime import datetime
from openerp.tools.translate import _
from openerp.tools import float_repr


_logger = logging.getLogger(__name__)

DEVISE = {'Euros': '978'}
HASH = {'SHA512': hashlib.sha512}
URL = [('Production', 'https://tpeweb.paybox.com'),
       ('Production (secours)', 'https://tpeweb1.paybox.com')]
paiement_cgi = 'cgi/MYchoix_pagepaiement.cgi'
load = 'load.htm'
server_status_ok = '<div id="server_status" style="text-align:center;">OK</div>'


class PayboxAcquirer(osv.Model):

    _inherit = 'payment.acquirer'

    def _get_providers(self, cr, uid, context=None):
        providers = super(PayboxAcquirer, self)._get_providers(cr, uid, context=context)
        providers.append(['paybox', 'Paybox'])
        return providers

    def get_paybox_settings(self, cr, uid, ids, context=None):
        """ return paybox settings values """
        paybox_values = self.pool.get('paybox.settings').get_default_paybox_settings(
            cr, uid, ids, context)
        return paybox_values

    def check_paybox_url(self, cr, uid, url, context=None):
        """ check if the server aimed is ok. The second url is used if problems are encountered"""
        url_load = url+load
        response = ''
        try:
            response = urllib.urlopen(url_load).read()
        except:
            _logger.error(u"""[Paybox] - Vérification échouée, l'URL semble non accessible.
Essaie d'une url différente...""")
        if server_status_ok not in response:
            for prod_url in URL:
                if url in prod_url:
                    if URL.index(prod_url) == 0:
                        url = URL[1][1]
                    else:
                        url = URL[0][1]
                    break
        url_load = url+load
        try:
            response = urllib.urlopen(url_load).read()
        except:
            _logger.error(u"""[Paybox] - Vérification échouée, l'URL semble non accessible.
Vérifiez votre connectivité """)
            raise osv.except_osv(
                u"L'url du serveur Paybox semble inaccessible",
                u"Vérifiez l'état de votre connection")
        return url

    def build_paybox_args(self, cr, uid, reference, currency, amount, context=None):
        """ return args needed to fill paybox form. Most of the args needed are
            set in the paybox settings part """
        db_args = "?db=%s" % (cr.dbname)
        invoice = self.pool.get('account.invoice')
        paybox_values = self.get_paybox_settings(cr, uid, None)
        for value in paybox_values:
            if not value:
                raise osv.except_osv(
                    u"Génération du formulaire Paybox impossible",
                    u"Tous les champs de configuration doivent être renseignés")
        # values extracted from the paybox settings part
        key = unicode(paybox_values['key'])
        identifiant, devise = paybox_values['shop_id'], paybox_values['devise']
        rang, site = paybox_values['rank'], paybox_values['site']
        porteur, _hash = paybox_values['porteur'], paybox_values['hash']
        if reference:
            invoice_ids = invoice.search(cr, uid, [('number', '=', reference)])
            if invoice_ids:
                partner = invoice.browse(cr, uid, invoice_ids[0]).partner_id
                porteur = partner.email if partner.email else porteur
        url = self.check_paybox_url(cr, uid, paybox_values['url'])
        url += paiement_cgi
        url_retour = paybox_values['retour']
        url_ipn = paybox_values['ipn']
        # the paybox amount need to be formated in cents so we convert it
        amount = str(int(amount*100))
        retour = u"Mt:M;Ref:R;Auto:A;Erreur:E;Signature:K"
        url_effectue = url_retour+db_args
        url_annule = url_retour+'/cancelled/'+db_args
        url_refuse = url_retour+'/refused/'+db_args
        url_ipn = url_ipn+'/ipn/'+db_args
        time = str(datetime.now())
        # we need to concatenate the args to compute the hmac
        args = ('PBX_SITE=' + site + '&PBX_RANG=' + rang +
                '&PBX_HASH=' + _hash + '&PBX_CMD=' + reference +
                '&PBX_IDENTIFIANT=' + identifiant + '&PBX_TOTAL=' + amount +
                '&PBX_DEVISE=' + devise + '&PBX_PORTEUR=' + porteur +
                '&PBX_RETOUR=' + retour + '&PBX_TIME=' + time +
                '&PBX_EFFECTUE=' + url_effectue + '&PBX_REFUSE=' + url_refuse +
                '&PBX_ANNULE=' + url_annule +
                '&PBX_REPONDRE_A=' + url_ipn)
        hmac = self.compute_hmac(key, _hash, args)
        return dict(hmac=hmac, hash=_hash, porteur=porteur, url=url, identifiant=identifiant,
                    rank=rang, site=site, url_ipn=url_ipn, refuse=url_refuse, time=time,
                    devise=devise, retour=retour, annule=url_annule, amount=amount,
                    effectue=url_effectue)

    def render_payment_block(self, cr, uid, object, reference, currency,
                             amount, context=None, **kwargs):
        """ Renders all visible payment acquirer forms for the given rendering context, and
            return them wrapped in an appropriate HTML block, ready for direct inclusion
            in an OpenERP v7 form view """
        acquirer_ids = self.search(cr, uid, [('visible', '=', True)])
        if not acquirer_ids:
            return
        html_forms = []
        for this in self.browse(cr, uid, acquirer_ids):
            # Paybox case
            acquirer = this.name
            if acquirer == 'Paybox':
                # just to avoid rendering for non handled payment terms
                if object.payment_term:
                    continue
                # when the invoice is cancelled
                if not reference:
                    continue
                vals = self.build_paybox_args(
                    cr, uid, reference, currency, amount, context=context)
                if not vals:
                    _logger.warning(u"""[Paybox] - Génération formulaire Paybox impossible.
Données insuffisantes """)
                    continue
                content = this.render(
                    object, reference, vals['devise'], vals['amount'], hmac=vals['hmac'],
                    url=vals['url'], hash=vals['hash'], porteur=vals['porteur'],
                    identifiant=vals['identifiant'], rank=vals['rank'], site=vals['site'],
                    ipn=vals['url_ipn'], time=vals['time'], devise=vals['devise'],
                    retour=vals['retour'], effectue=vals['effectue'],
                    annule=vals['annule'], refuse=vals['refuse'], context=context, **kwargs)
            else:
                content = this.render(
                    object, reference, currency, amount, context=context, **kwargs)
            if content:
                html_forms.append(content)
        html_block = '\n'.join(filter(None, html_forms))
        return self._wrap_payment_block(
            cr, uid, html_block, amount, currency, acquirer=acquirer, context=context)

    def compute_hmac(self, key, hash_name, args):
        """ compute hmac with key, hash and args given """
        try:
            binary_key = binascii.unhexlify(key)
        except:
            _logger.exception("Cannot decode key")
            # We may just log this error and not raise exception
            raise osv.except_osv(u"Calcul HMAC impossible", u"Vérifiez la valeur de la clé")
        concat_args = args
        try:
            import hmac
            hmac_value = hmac.new(binary_key, concat_args, HASH[hash_name]).hexdigest().upper()
        except:
            # We may just log this error and not raise exception
            _logger.exception("Calcul HMAC impossible")
            raise osv.except_osv(u"Calcul HMAC impossible", u"Une erreur s'est produite")
        return hmac_value

    def paybox_form_generate_values(self, cr, uid, id, partner_values, tx_values, context=None):
        reference = tx_values['reference']
        currency = tx_values['currency'] and tx_values['currency'].name or ''
        amount = tx_values['amount']
        vals = self.build_paybox_args(
            cr, uid, reference, currency, amount, context=context)

        tx_values.update(vals)
        return partner_values, tx_values

    def paypal_form_generate_values(self, cr, uid, id, partner_values, tx_values, context=None):
        base_url = self.pool['ir.config_parameter'].get_param(cr, SUPERUSER_ID, 'web.base.url')
        acquirer = self.browse(cr, uid, id, context=context)

        paypal_tx_values = dict(tx_values)
        paypal_tx_values.update({
            'cmd': '_xclick',
            'business': acquirer.paypal_email_account,
            'item_name': '%s: %s' % (acquirer.company_id.name, tx_values['reference']),
            'item_number': tx_values['reference'],
            'amount': tx_values['amount'],
            'currency_code': tx_values['currency'] and tx_values['currency'].name or '',
            'address1': partner_values['address'],
            'city': partner_values['city'],
            'country': partner_values['country'] and partner_values['country'].name or '',
            'state': partner_values['state'] and partner_values['state'].name or '',
            'email': partner_values['email'],
            'zip': partner_values['zip'],
            'first_name': partner_values['first_name'],
            'last_name': partner_values['last_name'],
            'return': '%s' % urlparse.urljoin(base_url, PaypalController._return_url),
            'notify_url': '%s' % urlparse.urljoin(base_url, PaypalController._notify_url),
            'cancel_return': '%s' % urlparse.urljoin(base_url, PaypalController._cancel_url),
        })
        if acquirer.fees_active:
            paypal_tx_values['handling'] = '%.2f' % paypal_tx_values.pop('fees', 0.0)
        if paypal_tx_values.get('return_url'):
            paypal_tx_values['custom'] = json.dumps({'return_url': '%s' % paypal_tx_values.pop('return_url')})
        return partner_values, paypal_tx_values

    def _wrap_payment_block(self, cr, uid, html_block, amount,
                            currency, acquirer=None, context=None):
        """ override original method to add the paybox html block """
        if not html_block:
            if acquirer and acquirer == 'Paybox':
                return ''
            else:
                link = '#action=account.action_account_config'
                payment_header = _(""" You can finish the configuration in the
<a href="%s">Bank&Cash settings</a>""") % link
                amount = _('No online payment acquirers configured')
                group_ids = self.pool.get('res.users').browse(
                    cr, uid, uid, context=context).groups_id
                if any(group.is_portal for group in group_ids):
                    return ''
        else:
            payment_header = _('Pay safely online')
            currency_str = currency.symbol or currency.name
            if acquirer and acquirer == 'Paybox':
                amount_str = float_repr(
                    amount,
                    self.pool.get('decimal.precision').precision_get(cr, uid, 'Account'))
                amount = (u"%s %s" % ((currency_str, amount_str)
                          if currency.position == 'before' else (amount_str, currency_str)))
            else:
                amount_str = float_repr(
                    amount, self.pool.get('decimal.precision').precision_get(cr, uid, 'Account'))
                amount = (u"%s %s" % ((currency_str, amount_str)
                          if currency.position == 'before' else (amount_str, currency_str)))

        result = """<div class="payment_acquirers">
                         <div class="payment_header">
                             <div class="payment_amount">%s</div>
                             %s
                         </div>
                         %%s
                     </div>""" % (amount, payment_header)
        return result % html_block
