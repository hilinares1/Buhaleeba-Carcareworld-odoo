from odoo import api, fields, models, SUPERUSER_ID, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import except_orm, ValidationError ,UserError





class PurchaseOrders(models.Model):
    _inherit = "purchase.order"

    is_purchase_consignment = fields.Boolean(string='Is Purchase Consignment')

    def button_approve(self):

        res = super(PurchaseOrders, self).button_approve()
        for order in self:
            if order.is_purchase_consignment == True:

                order.picking_ids.write({'owner_id': order.partner_id.id})
            else:
                order.picking_ids.write({'owner_id': False})

        return res
