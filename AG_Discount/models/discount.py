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
        res = super(PurchaseOrderLine,self)._prepare_compute_all_values()
        price = 0.0
        if self.discount :
            if self.is_percentage == True:
                price = self.price_unit - (self.price_unit * (self.discount/100))
            else:
                price = self.price_unit - self.discount/self.product_qty
        else:
            price = self.price_unit
        res['price_unit'] = price
        return res

    # def _get_stock_move_price_unit(self):
    #     """Get correct price with discount replacing current price_unit
    #     value before calling super and restoring it later for assuring
    #     maximum inheritability.

    #     HACK: This is needed while https://github.com/odoo/odoo/pull/29983
    #     is not merged.
    #     """
    #     price_unit = False
    #     if self.discount :
    #         if self.is_percentage == True:
    #             price = self.price_unit - (self.price_unit * (self.discount/100))
    #         else:
    #             price = self.price_unit - self.discount/self.product_qty
    #     else:
    #         price = self.price_unit
    #     # price = self.price_subtotal
    #     if price != self.price_unit:
    #         # Only change value if it's different
    #         price_unit = self.price_unit
    #         self.price_unit = price
    #     price = super()._get_stock_move_price_unit()
    #     if price_unit:
    #         self.price_unit = price_unit
    #     return price


    def _prepare_account_move_line(self, move):
        vals = super(PurchaseOrderLine, self)._prepare_account_move_line(move)
        vals['discount'] = self.discount
        vals['is_percentage'] = self.is_percentage
        return vals


class StockMove(models.Model):
    _inherit = "stock.move"


    def _prepare_account_move_line(self, qty, cost, credit_account_id, debit_account_id, description):
        """
        Generate the account.move.line values to post to track the stock valuation difference due to the
        processing of the given quant.
        """
        self.ensure_one()

        # the standard_price of the product may be in another decimal precision, or not compatible with the coinage of
        # the company currency... so we need to use round() before creating the accounting entries.
        if self.purchase_line_id:
            debit_value = self.purchase_line_id.price_subtotal
            credit_value = debit_value
        else:
            debit_value = self.company_id.currency_id.round(cost)
            credit_value = debit_value

        valuation_partner_id = self._get_partner_id_for_valuation_lines()
        res = [(0, 0, line_vals) for line_vals in self._generate_valuation_lines_data(valuation_partner_id, qty, debit_value, credit_value, debit_account_id, credit_account_id, description).values()]

        return res

    # def _get_price_unit(self):
    #     """Get correct price with discount replacing current price_unit
    #     value before calling super and restoring it later for assuring
    #     maximum inheritability.

    #     HACK: This is needed while https://github.com/odoo/odoo/pull/29983
    #     is not merged.
    #     """
    #     price_unit = False
    #     po_line = self.purchase_line_id
    #     if po_line and self.product_id == po_line.product_id:
    #         if self.discount :
    #             if po_line.is_percentage == True:
    #                 price = po_line.price_unit - (po_line.price_unit * (po_line.discount/100))
    #             else:
    #                 price = po_line.price_unit - po_line.discount/po_line.product_qty
    #         else:
    #             price = po_line.price_unit
    #         # price = po_line.price_subtotal
    #         if price != po_line.price_unit:
    #             # Only change value if it's different
    #             price_unit = po_line.price_unit
    #             po_line.price_unit = price
    #     res = super()._get_price_unit()
    #     if price_unit:
    #         po_line.price_unit = price_unit
    #     return res


# accounts invoice discount

# class AccountMove(models.Model):
#     _inherit = "account.move"

#     total_discount = fields.Float('Discount')

#     def compute_discount(self):
#         for rec in self:
#             length = len(rec.invoice_line_ids)
#             discount = rec.total_discount / length
#             for line in rec.invoice_line_ids:
#                 line.update({'discount': discount})
#                 line.update({'is_percentage': False})

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    is_percentage = fields.Boolean('Is Discount (%)',store=True)
    discount = fields.Float('Discount',store=True)


    @api.onchange('is_percentage')
    def percentage_onchange(self):
        for line in self:
            line.update(line._get_price_total_and_subtotal())
        # return self._get_price_total_and_subtotal()['price_subtotal']

    # @api.onchange('quantity', 'discount','discount_value','is_percentage','price_unit', 'tax_ids')
    # def _onchange_price_subtotal(self):
    #     for line in self:
    #         if not line.move_id.is_invoice(include_receipts=True):
    #             continue
    #         # raise UserError('DDdd')
    #         line.update(line._get_price_total_and_subtotal())
    #         line.update(line._get_fields_onchange_subtotal())
    #         if line.discount_value:
    #             line.update({'discount_value':line.discount_value})
    #         if line.is_percentage:
    #             line.update({'is_percentage':line.is_percentage})

    def _get_price_total_and_subtotal(self, price_unit=None,quantity=None, discount=None, currency=None, product=None, partner=None, taxes=None, move_type=None):
        self.ensure_one()
        return self._get_price_total_and_subtotal_model(
            price_unit=price_unit or self.price_unit,
            quantity=quantity or self.quantity,
            discount=discount or self.discount,
            currency=currency or self.currency_id,
            product=product or self.product_id,
            partner=partner or self.partner_id,
            taxes=taxes or self.tax_ids,
            move_type=move_type or self.move_id.type,
        )
  
    @api.model
    def _get_price_total_and_subtotal_model(self, price_unit, quantity, discount, currency, product, partner, taxes, move_type):
        ''' This method is used to compute 'price_total' & 'price_subtotal'.

        :param price_unit:  The current price unit.
        :param quantity:    The current quantity.
        :param discount:    The current discount.
        :param currency:    The line's currency.
        :param product:     The line's product.
        :param partner:     The line's partner.
        :param taxes:       The applied taxes.
        :param move_type:   The type of the move.
        :return:            A dictionary containing 'price_subtotal' & 'price_total'.
        '''
        res = {}
        # if discount_value == 0.0:
        #     raise UserError('FGD')
        # Compute 'price_subtotal'.
        # price_unit_wo_discount = price_unit * (1 - (discount / 100.0))
        # subtotal = quantity * price_unit_wo_discount
        # price = 0.0
        # if self.discount :
        if discount:
            if self.is_percentage == True:
                price_unit_wo_discount = price_unit * (1 -(discount/100))
            else:
                
                price_unit_wo_discount = price_unit - discount/quantity
        else:
            price_unit_wo_discount = price_unit
        # else:
            # price_unit_wo_discount = self.price_unit
        
        subtotal = quantity * price_unit_wo_discount
        # self.update({'price_subtotal':subtotal})
        # Compute 'price_total'.
        if taxes:
            taxes_res = taxes._origin.compute_all(price_unit_wo_discount,
                quantity=quantity, currency=currency, product=product, partner=partner, is_refund=move_type in ('out_refund', 'in_refund'))
            res['price_subtotal'] = taxes_res['total_excluded']
            res['price_total'] = taxes_res['total_included']
        else:
            res['price_total'] = res['price_subtotal'] = subtotal
        #In case of multi currency, round before it's use for computing debit credit
        if currency:
            res = {k: currency.round(v) for k, v in res.items()}
        return res


    # @api.model_create_multi
    # def create(self, vals_list):
    #     # OVERRIDE
    #     ACCOUNTING_FIELDS = ('debit', 'credit', 'amount_currency')
    #     BUSINESS_FIELDS = ('price_unit', 'quantity', 'discount','discount_value','is_percentage', 'tax_ids')

    #     for vals in vals_list:
    #         move = self.env['account.move'].browse(vals['move_id'])
    #         vals.setdefault('company_currency_id', move.company_id.currency_id.id) # important to bypass the ORM limitation where monetary fields are not rounded; more info in the commit message

    #         if move.is_invoice(include_receipts=True):
    #             currency = move.currency_id
    #             partner = self.env['res.partner'].browse(vals.get('partner_id'))
    #             taxes = self.resolve_2many_commands('tax_ids', vals.get('tax_ids', []), fields=['id'])
    #             tax_ids = set(tax['id'] for tax in taxes)
    #             taxes = self.env['account.tax'].browse(tax_ids)

    #             # Ensure consistency between accounting & business fields.
    #             # As we can't express such synchronization as computed fields without cycling, we need to do it both
    #             # in onchange and in create/write. So, if something changed in accounting [resp. business] fields,
    #             # business [resp. accounting] fields are recomputed.
    #             if any(vals.get(field) for field in ACCOUNTING_FIELDS):
    #                 if vals.get('currency_id'):
    #                     balance = vals.get('amount_currency', 0.0)
    #                 else:
    #                     balance = vals.get('debit', 0.0) - vals.get('credit', 0.0)
    #                 price_subtotal = self._get_price_total_and_subtotal_model(
    #                     vals.get('price_unit', 0.0),
    #                     vals.get('quantity', 0.0),
    #                     vals.get('discount', 0.0),
    #                     currency,
    #                     self.env['product.product'].browse(vals.get('product_id')),
    #                     partner,
    #                     taxes,
    #                     move.type,
    #                 ).get('price_subtotal', 0.0)
    #                 vals.update(self._get_fields_onchange_balance_model(
    #                     vals.get('quantity', 0.0),
    #                     vals.get('discount', 0.0),
    #                     balance,
    #                     move.type,
    #                     currency,
    #                     taxes,
    #                     price_subtotal
    #                 ))
    #                 vals.update(self._get_price_total_and_subtotal_model(
    #                     vals.get('price_unit', 0.0),
    #                     vals.get('quantity', 0.0),
    #                     vals.get('discount', 0.0),
    #                     currency,
    #                     self.env['product.product'].browse(vals.get('product_id')),
    #                     partner,
    #                     taxes,
    #                     move.type,
    #                 ))
    #             elif any(vals.get(field) for field in BUSINESS_FIELDS):
    #                 vals.update(self._get_price_total_and_subtotal_model(
    #                     vals.get('price_unit', 0.0),
    #                     vals.get('quantity', 0.0),
    #                     vals.get('discount', 0.0),
    #                     currency,
    #                     self.env['product.product'].browse(vals.get('product_id')),
    #                     partner,
    #                     taxes,
    #                     move.type,
    #                     vals.get('discount_value', 0.0),
    #                     vals.get('is_percentage', False),
    #                 ))
    #                 vals.update(self._get_fields_onchange_subtotal_model(
    #                     vals['price_subtotal'],
    #                     move.type,
    #                     currency,
    #                     move.company_id,
    #                     move.date,
    #                 ))

    #         # Ensure consistency between taxes & tax exigibility fields.
    #         if 'tax_exigible' in vals:
    #             continue
    #         if vals.get('tax_repartition_line_id'):
    #             repartition_line = self.env['account.tax.repartition.line'].browse(vals['tax_repartition_line_id'])
    #             tax = repartition_line.invoice_tax_id or repartition_line.refund_tax_id
    #             vals['tax_exigible'] = tax.tax_exigibility == 'on_invoice'
    #         elif vals.get('tax_ids'):
    #             tax_ids = [v['id'] for v in self.resolve_2many_commands('tax_ids', vals['tax_ids'], fields=['id'])]
    #             taxes = self.env['account.tax'].browse(tax_ids).flatten_taxes_hierarchy()
    #             vals['tax_exigible'] = not any(tax.tax_exigibility == 'on_payment' for tax in taxes)

    #     lines = super(AccountMoveLine, self).create(vals_list)

    #     moves = lines.mapped('move_id')
    #     if self._context.get('check_move_validity', True):
    #         moves._check_balanced()
    #     moves._check_fiscalyear_lock_date()
    #     lines._check_tax_lock_date()

    #     return lines
