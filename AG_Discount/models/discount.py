from odoo import api, fields, models, SUPERUSER_ID, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import except_orm, ValidationError ,UserError

from ast import literal_eval
from datetime import date
from itertools import groupby
from operator import itemgetter
import time
import dateutil.parser

from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.addons.stock.models.stock_move import PROCUREMENT_PRIORITIES
from odoo.tools.misc import formatLang, format_date, get_lang



class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    total_discount = fields.Float('Discount')

    def compute_discount(self):
        for rec in self:
            length = len(rec.order_line)
            discount = rec.total_discount / length
            for line in rec.order_line:
                line.discount = discount
                line.is_percentage = False




class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line" 

    is_percentage = fields.Boolean('Is Discount (%)',default=False)
    discount = fields.Float('Discount')

    @api.depends('product_qty', 'price_unit', 'taxes_id','discount','is_percentage')
    def _compute_amount(self):
        res = super(PurchaseOrderLine,self)._compute_amount()
        return res
        # for line in self:
        #     vals = line._prepare_compute_all_values()
        #     taxes = line.taxes_id.compute_all(
        #         vals['price_unit'],
        #         vals['currency_id'],
        #         vals['product_qty'],
        #         vals['product'],
        #         vals['partner'])
        #     line.update({
        #         'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
        #         'price_total': taxes['total_included'],
        #         'price_subtotal': taxes['total_excluded'],
        #     })

    def _prepare_compute_all_values(self):
        # Hook method to returns the different argument values for the
        # compute_all method, due to the fact that discounts mechanism
        # is not implemented yet on the purchase orders.
        # This method should disappear as soon as this feature is
        # also introduced like in the sales module.
        self.ensure_one()
        price = 0.0
        if self.discount :
            if self.is_percentage == True:
                price = self.price_unit - (self.price_unit * (self.discount/100))
            else:
                price = self.price_unit - self.discount
        else:
            price = self.price_unit
        return {
            'price_unit': price,
            'currency_id': self.order_id.currency_id,
            'product_qty': self.product_qty,
            'product': self.product_id,
            'partner': self.order_id.partner_id,
        }