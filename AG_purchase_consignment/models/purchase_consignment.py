from odoo import api, fields, models, SUPERUSER_ID, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import except_orm, ValidationError ,UserError

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    is_purchase_consignment = fields.Boolean(string='Is Consignment Purchase')

    def button_confirm(self): #change in demo
        for record in self:
            res = super(PurchaseOrder, self).button_confirm()
            if record.is_purchase_consignment == True:
                print('---True---')
                record.picking_ids.write({'owner_id': record.partner_id.id})
            else:
                record.picking_ids.write({'owner_id': False})
                print('---False---')

            return res
