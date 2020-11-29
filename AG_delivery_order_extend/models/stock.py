# -*- coding: utf-8 -*-

from odoo import api, fields, models, SUPERUSER_ID, _

class Stock(models.Model):
    _inherit = 'stock.picking'

    state = fields.Selection(
        selection_add = [
            ('in_transit', 'IN Transit'),
            ('complete', 'Complete'),
        ],
    )
    store_id = fields.Char('Woocommerce Store Id',readonly=True)
    payment_method = fields.Char('Payment Method',readonly=True)
    woo_status = fields.Selection([
        ('no', 'Not Online Sales'),
        ('pending payment', 'Pending Payment'),
        ('pending processing', 'Pending Processing'),
        ('quote request', 'Quote Request'),
        ('on-hold', 'On Hold'),
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('pickup-cod', 'Pickup COD'),
        ('pickup-paid', 'Pickup Paid'),
        ('refunded', 'Refunded'),
        ('failed', 'Failed'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], string='Woo-commerce Status', readonly=True, index=True, store=True, copy=False,
        tracking=True)


    # def custom_picking_delivered(self):
    #     self.state = 'in_transit'

    def custom_picking_complete(self):
        self.state = 'complete'

    def action_done(self):
        """Changes picking state to done by processing the Stock Moves of the Picking

        Normally that happens when the button "Done" is pressed on a Picking view.
        @return: True
        """
        res = super(Stock, self).action_done()
        if self.picking_type_code == 'outgoing':
            so_rec = self.env['sale.order'].search([('id', '=', self.env.context.get('active_id'))])
            for rec in so_rec:
              if rec.woo_status in ['pickup-cod', 'pickup-paid', 'no']:
                    self.state = 'complete'
              else:
                    self.state = 'in_transit'
        return True