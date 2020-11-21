from odoo import api, fields, models, SUPERUSER_ID, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import except_orm, ValidationError ,UserError

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    is_purchase_consignment = fields.Boolean(string='Is Purchase Consignment')

   # def button_confirm(self): #change in demo
       # for record in self:
            #res = super(PurchaseOrder, self).button_confirm()

            #if record.picking_ids:
             #   if record.is_purchase_consignment == 'True':
                  #  for pick in record.picking_ids:
                      #  pick.move_lines.write({'origin': record.interchanging_po_sequence})
                     #   pick.move_lines.write({'owner_id': record.partner_id})
