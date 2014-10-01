from openerp.osv import osv


class Invoice(osv.Model):

    _inherit = 'account.invoice'

    def validate_invoice_paybox(self, cr, uid, ref, montant):
        """ Store payment for the referenced invoice with a specific amount """
        invoice_id = self.search(cr, uid, [('number', '=', ref)])
        if not invoice_id:
            raise osv.except_osv(u"La facture %s n'a pas été trouvée",
                                 u"Prenez contact pour supprimer le paiement") % (ref)
        invoice_id = invoice_id[0]
        return invoice_id
