from odoo import models, fields, api
import odoo.addons.decimal_precision as dp


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.depends('order_line.price_total')
    def _amount_discount(self):
        """
        Compute the total discount of PO.
        """
        for order in self:
            amount_discount = 0.0
            for line in order.order_line:
                amount_discount += (line.product_qty * line.price_unit * line.discount) / 100
            order.update({
                'amount_discount': order.currency_id.round(amount_discount),
            })

    discount_type = fields.Selection([('percent', 'Percentage'), ('amount', 'Amount')], string='Discount type',
                                     readonly=True,
                                     states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
                                     default='amount')
    discount_rate = fields.Monetary('Discount Rate', digits=dp.get_precision('Account'),
                                    readonly=True,
                                    states={'draft': [('readonly', False)], 'sent': [('readonly', False)]})
    amount_discount = fields.Monetary(string='Discount', store=True, readonly=True, compute='_amount_discount',
                                      digits=dp.get_precision('Account'), track_visibility='always')

    def action_view_invoice(self):
        result = super(PurchaseOrder, self).action_view_invoice()
        result['context']['default_discount_rate'] = self.discount_rate
        result['context']['default_discount_type'] = self.discount_type
        return result

    @api.onchange('discount_type', 'discount_rate', 'order_line')
    def supply_rate(self):
        if self.discount_rate:
            for order in self:
                if order.discount_type == 'percent':
                    for line in order.order_line:
                        line.discount = order.discount_rate
                else:
                    total = discount = 0.0
                    for line in order.order_line:
                        total += (line.product_qty * line.price_unit)
                    if total:
                        if order.discount_rate != 0:
                            discount = (order.discount_rate / total) * 100
                        else:
                            discount = order.discount_rate
                        for line in order.order_line:
                            line.discount = discount
                            line.discount_value = line.price_unit * line.product_qty * (discount / 100)


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    discount_value = fields.Float('Discount Value', digits=(16, 3), default=0.0)
    discount = fields.Float(string='Discount (%)', digits=(16, 20), default=0.0)
    price_subtotal = fields.Monetary(compute='_compute_amount1', string='Subtotal', store=True)
    price_total = fields.Monetary(compute='_compute_amount1', string='Total', store=True)
    price_tax = fields.Monetary(compute='_compute_amount1', string='Tax', store=True)

    @api.onchange('discount_value')
    def onchange_discount_value(self):
        if self.discount_value and self.price_unit and self.product_qty:
            self.discount = (self.discount_value / (self.price_unit * self.product_qty)) * 100
        else:
            self.discount = 0

    @api.depends('product_qty', 'price_unit', 'taxes_id', 'discount')
    def _compute_amount1(self):
        # super(PurchaseOrderLine, self)._compute_amount()
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.taxes_id.compute_all(price, line.order_id.currency_id, line.product_qty,
                                              product=line.product_id, partner=line.order_id.partner_id)
            line.update({
                'price_tax': taxes['total_included'] - taxes['total_excluded'],
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })

    _sql_constraints = [
        ('discount_limit', 'CHECK (discount <= 100.0)',
         'Discount must be lower than 100%.'),
    ]

    def _get_discounted_price_unit(self):
        """Inheritable method for getting the unit price after applying
        discount(s).

        :rtype: float
        :return: Unit price after discount(s).
        """
        self.ensure_one()
        if self.discount:
            return self.price_unit * (1 - self.discount / 100)
        return self.price_unit
