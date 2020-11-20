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
