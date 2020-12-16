# -*- coding: utf-8 -*-

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import except_orm, ValidationError ,UserError

class Stock(models.Model):
    _inherit = 'stock.picking'

    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting', 'Waiting Another Operation'),
        ('confirmed', 'Waiting'),
        ('in_progress', 'In progress'),
        ('assigned', 'Ready'),
        ('in_transit', 'IN Transit'),
        ('done', 'Done'),
        ('complete', 'Complete'),
        ('cancel', 'Cancelled'),
    ], string='Status', compute='_compute_state',
        copy=False, index=True, readonly=True, store=True, tracking=True,
        help=" * Draft: The transfer is not confirmed yet. Reservation doesn't apply.\n"
             " * Waiting another operation: This transfer is waiting for another operation before being ready.\n"
             " * Waiting: The transfer is waiting for the availability of some products.\n(a) The shipping policy is \"As soon as possible\": no product could be reserved.\n(b) The shipping policy is \"When all products are ready\": not all the products could be reserved.\n"
             " * Ready: The transfer is ready to be processed.\n(a) The shipping policy is \"As soon as possible\": at least one product has been reserved.\n(b) The shipping policy is \"When all products are ready\": all product have been reserved.\n"
             " * Done: The transfer has been processed.\n"
             " * Cancelled: The transfer has been cancelled.")
    store_id = fields.Char('Woocommerce Id',readonly=True)
    payment_method = fields.Char('Payment Method',readonly=True)

    #Code from Bincy commit on 28th Nov added status on delivery
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
        ('cancel-request', 'Cancelled'),
        ('not', 'Not sales picking'),
        ('cancelled', 'Cancelled')
    ], string='Woo-commerce Status', readonly=True, index=True,store=True, copy=False, compute="_get_woo_status", tracking=True)
    

    @api.depends('sale_id')
    def _get_woo_status(self):
        for rec in self:
            if rec.sale_id:
                rec.woo_status = rec.sale_id.woo_status
            else:
                rec.woo_status = 'not'

    def custom_picking_delivered(self):
        if self.move_line_ids_without_package:
            for move in self.move_line_ids_without_package:
                if move.lot_id.name != move.issued_lot:
                    raise UserError('The issued lot and assigned lot from system not same for this product %s'%(move.product_id.name))
        self.state = 'assigned'

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

    def action_assign(self):
        """ Check availability of picking moves.
        This has the effect of changing the state and reserve quants on available moves, and may
        also impact the state of the picking as it is computed based on move's states.
        @return: True
        """
        res = super(Stock, self).action_assign()
        if self.picking_type_code == 'outgoing':
            # if not self.env.context.get('channel_id'):
                self.state = 'in_progress'
        return res
