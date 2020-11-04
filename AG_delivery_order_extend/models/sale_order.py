# -*- coding: utf-8 -*-

from odoo import api, fields, models, SUPERUSER_ID, _


class SaleOrder(models.Model):
    _inherit = "sale.order"
    _description = "Wocommerce fields addition"

    payment_method = fields.Char('Payment Method', help='Payment Method Name')
    store_id = fields.Char('Woocommerce Store ID', help='Store ID from woocommerce')

    # Don't remove this code, added same code on Automated Action to get store ID upon creation of sale order
    # @api.model_create_multi
    # def create(self, vals):
    #     res = env['channel.order.mappings'].search([('odoo_order_id', '=', record.id)], limit=1)
    #     record.write({'store_id': res.store_order_id})
    #     if res and res.store_order_id:
    #         saleorder_feed = env['order.feed'].search([('store_id', '=', res.store_order_id)], limit=1)
    #         record.write({'payment_method': saleorder_feed.payment_method})
