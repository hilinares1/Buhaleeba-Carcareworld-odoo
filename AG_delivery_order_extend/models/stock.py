# -*- coding: utf-8 -*-

from odoo import api, fields, models, SUPERUSER_ID, _

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

    # state = fields.Selection(
    #     selection_add = [
    #         ('in_transit', 'IN Transit'),
    #         ('complete', 'Complete'),
    #     ],
    # )

    def custom_picking_delivered(self):
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