# -*- coding: utf-8 -*-

from odoo import api, fields, models, SUPERUSER_ID, _
from datetime import datetime, timedelta , date


class SaleOrder(models.Model):
    _inherit = "sale.order"
    _description = "Wocommerce fields addition"

    payment_method = fields.Char('Payment Method', help='Payment Method Name')
    store_id = fields.Char('Woocommerce ID', help='Store ID from woocommerce')
    receive_state = fields.Text('Delivery status', compute="ready_state")
    # Don't remove this code, added same code on Automated Action to get store ID upon creation of sale order
    # @api.model_create_multi
    # def create(self, vals):
    #     res = env['channel.order.mappings'].search([('odoo_order_id', '=', record.id)], limit=1)
    #     record.write({'store_id': res.store_order_id})
    #     if res and res.store_order_id:
    #         saleorder_feed = env['order.feed'].search([('store_id', '=', res.store_order_id)], limit=1)
    #         record.write({'payment_method': saleorder_feed.payment_method})

    # Bincy Code merge on 28 Nov
    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()

        for do_pick in self.picking_ids:
            do_pick.write({'payment_method': self.payment_method,
                           'store_id':self.store_id})

        return res


    @api.depends('expected_date')
    def ready_state(self):
        current_date = date.today()
        for rec in self:

            text2 = ''
            dos = self.env['stock.picking'].search([('origin', '=', rec.name)])
            for do in dos:
                if do.state == 'waiting':
                    text2 = str(do.name) + '  |  ' + 'Waiting another operation' + '\n' + text2
                elif do.state == 'confirmed':
                    text2 = str(do.name) + '  |  ' + 'Waiting' + '\n' + text2
                elif do.state == 'assigned':
                    text2 = str(do.name) + '  |  ' + 'Ready' + '\n' + text2
                else:
                    text2 = str(do.name) + '  |  ' + str(do.state) + '\n' + text2
            rec.receive_state = text2
