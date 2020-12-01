from odoo import api, fields, models, SUPERUSER_ID, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import except_orm, ValidationError ,UserError

from ast import literal_eval
from datetime import date
from itertools import groupby
from operator import itemgetter
import time
import dateutil.parser
from functools import partial
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
            # length = len(rec.order_line)
            # discount = rec.total_discount / length
            GT = 0.0
            for line in rec.order_line:
                GT += line.product_qty * line.price_unit
            for line in rec.order_line:
                line.discount = (line.product_qty * line.price_unit * rec.total_discount) / GT
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

    def _get_stock_move_price_unit(self):
        """Get correct price with discount replacing current price_unit
        value before calling super and restoring it later for assuring
        maximum inheritability.

        HACK: This is needed while https://github.com/odoo/odoo/pull/29983
        is not merged.
        """
        price_unit = False
        if self.discount :
            if self.is_percentage == True:
                price = self.price_unit - (self.price_unit * (self.discount/100))
            else:
                price = self.price_unit - self.discount/self.product_qty
        else:
            price = self.price_unit
        # price = self.price_subtotal
        if price != self.price_unit:
            # Only change value if it's different
            price_unit = self.price_unit
            self.price_unit = price
        price = super()._get_stock_move_price_unit()
        if price_unit:
            self.price_unit = price_unit
        return price


    def _prepare_account_move_line(self, move):
        vals = super(PurchaseOrderLine, self)._prepare_account_move_line(move)
        vals['price_unit'] = self.price_unit
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

    def _get_price_unit(self):
        """Get correct price with discount replacing current price_unit
        value before calling super and restoring it later for assuring
        maximum inheritability.

        HACK: This is needed while https://github.com/odoo/odoo/pull/29983
        is not merged.
        """
        price_unit = False
        po_line = self.purchase_line_id
        if po_line and self.product_id == po_line.product_id:
            if po_line.discount :
                if po_line.is_percentage == True:
                    price = po_line.price_unit - (po_line.price_unit * (po_line.discount/100))
                else:
                    price = po_line.price_unit - po_line.discount/po_line.product_qty
            else:
                price = po_line.price_unit
            # price = po_line.price_subtotal
            if price != po_line.price_unit:
                # Only change value if it's different
                price_unit = po_line.price_unit
                po_line.price_unit = price
        res = super()._get_price_unit()
        if price_unit:
            po_line.price_unit = price_unit
        return res


# accounts invoice discount

class AccountMove(models.Model):
    _inherit = "account.move"

    amount_discount = fields.Monetary(string='Discount',
                                         readonly=True,
                                         store=True, track_visibility='always',compute='_compute_amount')
    sales_discount_account_id = fields.Integer(compute='verify_discount')

    @api.depends('amount_discount')
    def verify_discount(self):
        for rec in self:
            rec.sales_discount_account_id = rec.company_id.sales_discount_account.id

    @api.depends(
        'line_ids.debit',
        'line_ids.credit',
        'line_ids.currency_id',
        'line_ids.amount_currency',
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        'line_ids.payment_id.state',
        'amount_discount')
    def _compute_amount(self):
        super(AccountMove, self)._compute_amount()
        for rec in self:
            amount_discount = 0.0
            for line in rec.invoice_line_ids:
                amount_discount += line.discount
            rec.amount_discount = amount_discount
            if amount_discount:
                rec.ks_calculate_discount()
            sign = rec.type in ['in_refund', 'out_refund'] and -1 or 1
            rec.amount_total_company_signed = rec.amount_total * sign
            rec.amount_total_signed = rec.amount_total * sign
            

    def ks_calculate_discount(self):
        for rec in self:
            if rec.amount_discount:
                rec.amount_total = rec.amount_tax + rec.amount_untaxed - rec.amount_discount
                rec.ks_update_universal_discount()


            

    def ks_update_universal_discount(self):
        """This Function Updates the Universal Discount through Sale Order"""
        for rec in self:
            
            already_exists = self.line_ids.filtered(
                lambda line: line.name and line.name.find('Discount of') == 0)
            terms_lines = self.line_ids.filtered(
                lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
            other_lines = self.line_ids.filtered(
                lambda line: line.account_id.user_type_id.type not in ('receivable', 'payable'))
            if already_exists:
                for lines in rec.invoice_line_ids:
                    amount = lines.discount
                    if rec.sales_discount_account_id \
                            and (rec.type == "out_invoice"
                                or rec.type == "out_refund")\
                            and amount > 0:
                        if rec.type == "out_invoice":
                            already_exists.update({
                                'debit': amount > 0.0 and amount or 0.0,
                                'credit': amount < 0.0 and -amount or 0.0,
                            })
                        else:
                            already_exists.update({
                                'debit': amount < 0.0 and -amount or 0.0,
                                'credit': amount > 0.0 and amount or 0.0,
                            })
                    total_balance = sum(other_lines.mapped('balance'))
                    total_amount_currency = sum(other_lines.mapped('amount_currency'))
                    terms_lines.update({
                        'amount_currency': -total_amount_currency,
                        'debit': total_balance < 0.0 and -total_balance or 0.0,
                        'credit': total_balance > 0.0 and total_balance or 0.0,
                    })
            
            if not already_exists and rec.amount_discount > 0:
                in_draft_mode = self != self._origin
                if not in_draft_mode and rec.type == 'out_invoice':
                    # raise UserError(rec.type)
                    rec._recompute_universal_discount_lines()
                
                print()


    @api.onchange('amount_discount','line_ids')
    def _recompute_universal_discount_lines(self):
        """This Function Create The General Entries for Universal Discount"""
        for rec in self:
            type_list = ['out_invoice', 'out_refund', 'in_invoice', 'in_refund']
            for lines in rec.invoice_line_ids:
                if lines.discount > 0 and rec.type in type_list:
                    if rec.is_invoice(include_receipts=True):
                        in_draft_mode = self != self._origin
                        
                        ks_name = "Discount "
                        if lines.discount:
                            ks_value = "of %s amount #" %(lines.product_id.name) + str(lines.discount)
                        else:
                            ks_value = ''
                        ks_name = ks_name + ks_value
                        #           ("Invoice No: " + str(self.ids)
                        #            if self._origin.id
                        #            else (self.display_name))
                        terms_lines = self.line_ids.filtered(
                            lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
                        product = 'Discount of %s'%(lines.product_id.name)
                        already_exists = self.line_ids.filtered(
                                        lambda line: line.name and line.name.find(product) == 0)
                        if already_exists:
                            amount = lines.discount
                            if self.sales_discount_account_id \
                                    and (self.type == "out_invoice"
                                        or self.type == "out_refund"):
                                if self.type == "out_invoice":
                                    already_exists.update({
                                        'name': ks_name,
                                        'debit': amount > 0.0 and amount or 0.0,
                                        'credit': amount < 0.0 and -amount or 0.0,
                                    })
                                else:
                                    already_exists.update({
                                        'name': ks_name,
                                        'debit': amount < 0.0 and -amount or 0.0,
                                        'credit': amount > 0.0 and amount or 0.0,
                                    })
                        else:
                            new_tax_line = self.env['account.move.line']
                            create_method = in_draft_mode and \
                                            self.env['account.move.line'].new or\
                                            self.env['account.move.line'].create

                            if self.sales_discount_account_id \
                                    and (self.type == "out_invoice"
                                        or self.type == "out_refund"):
                                amount = lines.discount
                                dict = {
                                        'move_name': self.name,
                                        'name': ks_name,
                                        'price_unit': lines.discount,
                                        'product_id': lines.product_id.id,
                                        'quantity': 1,
                                        'debit': amount < 0.0 and -amount or 0.0,
                                        'credit': amount > 0.0 and amount or 0.0,
                                        'account_id': self.sales_discount_account_id,
                                        'move_id': self._origin,
                                        'date': self.date,
                                        'exclude_from_invoice_tab': True,
                                        'partner_id': terms_lines.partner_id.id,
                                        'company_id': terms_lines.company_id.id,
                                        'company_currency_id': terms_lines.company_currency_id.id,
                                        }
                                if self.type == "out_invoice":
                                    dict.update({
                                        'debit': amount > 0.0 and amount or 0.0,
                                        'credit': amount < 0.0 and -amount or 0.0,
                                    })
                                else:
                                    dict.update({
                                        'debit': amount < 0.0 and -amount or 0.0,
                                        'credit': amount > 0.0 and amount or 0.0,
                                    })
                                if in_draft_mode:
                                    self.line_ids += create_method(dict)
                                    # Updation of Invoice Line Id
                                    product = 'Discount of %s'%(lines.product_id.name)
                                    duplicate_id = self.invoice_line_ids.filtered(
                                        lambda line: line.name and line.name.find(product) == 0)
                                    self.invoice_line_ids = self.invoice_line_ids - duplicate_id
                                else:
                                    dict.update({
                                        'price_unit': 0.0,
                                        'debit': 0.0,
                                        'credit': 0.0,
                                    })
                                    self.line_ids = [(0, 0, dict)]

                            
                        if in_draft_mode:
                            # Update the payement account amount
                            terms_lines = self.line_ids.filtered(
                                lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
                            other_lines = self.line_ids.filtered(
                                lambda line: line.account_id.user_type_id.type not in ('receivable', 'payable'))
                            total_balance = sum(other_lines.mapped('balance'))
                            total_amount_currency = sum(other_lines.mapped('amount_currency'))
                            terms_lines.update({
                                        'amount_currency': -total_amount_currency,
                                        'debit': total_balance < 0.0 and -total_balance or 0.0,
                                        'credit': total_balance > 0.0 and total_balance or 0.0,
                                    })
                        else:
                            terms_lines = self.line_ids.filtered(
                                lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
                            other_lines = self.line_ids.filtered(
                                lambda line: line.account_id.user_type_id.type not in ('receivable', 'payable'))
                            product = 'Discount of %s'%(lines.product_id.name)
                            already_exists = self.line_ids.filtered(
                                lambda line: line.name and line.name.find(product) == 0)
                            total_balance = sum(other_lines.mapped('balance')) + amount
                            total_amount_currency = sum(other_lines.mapped('amount_currency'))
                            dict1 = {
                                        'debit': amount > 0.0 and amount or 0.0,
                                        'credit': amount < 0.0 and -amount or 0.0,
                            }
                            dict2 = {
                                    'debit': total_balance < 0.0 and -total_balance or 0.0,
                                    'credit': total_balance > 0.0 and total_balance or 0.0,
                                    }
                            self.line_ids = [(1, already_exists.id, dict1), (1, terms_lines.id, dict2)]
                            print()

                elif lines.discount <= 0:
                    product = 'Discount of %s'%(lines.product_id.name)
                    already_exists = self.line_ids.filtered(
                        lambda line: line.name and line.name.find(product) == 0)
                    if already_exists:
                        self.line_ids -= already_exists
                        terms_lines = self.line_ids.filtered(
                            lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
                        other_lines = self.line_ids.filtered(
                            lambda line: line.account_id.user_type_id.type not in ('receivable', 'payable'))
                        total_balance = sum(other_lines.mapped('balance'))
                        total_amount_currency = sum(other_lines.mapped('amount_currency'))
                        terms_lines.update({
                            'amount_currency': -total_amount_currency,
                            'debit': total_balance < 0.0 and -total_balance or 0.0,
                            'credit': total_balance > 0.0 and total_balance or 0.0,
                        })


    def _recompute_tax_lines(self, recompute_tax_base_amount=False):
        ''' Compute the dynamic tax lines of the journal entry.

        :param lines_map: The line_ids dispatched by type containing:
            * base_lines: The lines having a tax_ids set.
            * tax_lines: The lines having a tax_line_id set.
            * terms_lines: The lines generated by the payment terms of the invoice.
            * rounding_lines: The cash rounding lines of the invoice.
        '''
        self.ensure_one()
        in_draft_mode = self != self._origin

        def _serialize_tax_grouping_key(grouping_dict):
            ''' Serialize the dictionary values to be used in the taxes_map.
            :param grouping_dict: The values returned by '_get_tax_grouping_key_from_tax_line' or '_get_tax_grouping_key_from_base_line'.
            :return: A string representing the values.
            '''
            return '-'.join(str(v) for v in grouping_dict.values())

        def _compute_base_line_taxes(base_line):
            ''' Compute taxes amounts both in company currency / foreign currency as the ratio between
            amount_currency & balance could not be the same as the expected currency rate.
            The 'amount_currency' value will be set on compute_all(...)['taxes'] in multi-currency.
            :param base_line:   The account.move.line owning the taxes.
            :return:            The result of the compute_all method.
            '''
            move = base_line.move_id

            if move.is_invoice(include_receipts=True):
                handle_price_include = True
                sign = -1 if move.is_inbound() else 1
                quantity = base_line.quantity
                if base_line.currency_id:
                    # price_unit_foreign_curr = sign * base_line.price_unit * (1 - (base_line.discount / 100.0))
                    price_unit_foreign_curr = sign * base_line.price_unit 
                    price_unit_comp_curr = base_line.currency_id._convert(price_unit_foreign_curr, move.company_id.currency_id, move.company_id, move.date)
                else:
                    price_unit_foreign_curr = 0.0
                    # price_unit_comp_curr = sign * base_line.price_unit * (1 - (base_line.discount / 100.0))
                    price_unit_comp_curr = sign * base_line.price_unit 
                tax_type = 'sale' if move.type.startswith('out_') else 'purchase'
                is_refund = move.type in ('out_refund', 'in_refund')
            else:
                handle_price_include = False
                quantity = 1.0
                price_unit_foreign_curr = base_line.amount_currency
                price_unit_comp_curr = base_line.balance
                tax_type = base_line.tax_ids[0].type_tax_use if base_line.tax_ids else None
                is_refund = (tax_type == 'sale' and base_line.debit) or (tax_type == 'purchase' and base_line.credit)

            balance_taxes_res = base_line.tax_ids._origin.compute_all(
                price_unit_comp_curr,
                currency=base_line.company_currency_id,
                quantity=quantity,
                product=base_line.product_id,
                partner=base_line.partner_id,
                is_refund=is_refund,
                handle_price_include=handle_price_include,
            )

            if move.type == 'entry':
                repartition_field = is_refund and 'refund_repartition_line_ids' or 'invoice_repartition_line_ids'
                repartition_tags = base_line.tax_ids.mapped(repartition_field).filtered(lambda x: x.repartition_type == 'base').tag_ids
                tags_need_inversion = (tax_type == 'sale' and not is_refund) or (tax_type == 'purchase' and is_refund)
                if tags_need_inversion:
                    balance_taxes_res['base_tags'] = base_line._revert_signed_tags(repartition_tags).ids
                    for tax_res in balance_taxes_res['taxes']:
                        tax_res['tag_ids'] = base_line._revert_signed_tags(self.env['account.account.tag'].browse(tax_res['tag_ids'])).ids

            if base_line.currency_id:
                # Multi-currencies mode: Taxes are computed both in company's currency / foreign currency.
                amount_currency_taxes_res = base_line.tax_ids._origin.compute_all(
                    price_unit_foreign_curr,
                    currency=base_line.currency_id,
                    quantity=quantity,
                    product=base_line.product_id,
                    partner=base_line.partner_id,
                    is_refund=self.type in ('out_refund', 'in_refund'),
                    handle_price_include=handle_price_include,
                )

                if move.type == 'entry':
                    repartition_field = is_refund and 'refund_repartition_line_ids' or 'invoice_repartition_line_ids'
                    repartition_tags = base_line.tax_ids.mapped(repartition_field).filtered(lambda x: x.repartition_type == 'base').tag_ids
                    tags_need_inversion = (tax_type == 'sale' and not is_refund) or (tax_type == 'purchase' and is_refund)
                    if tags_need_inversion:
                        balance_taxes_res['base_tags'] = base_line._revert_signed_tags(repartition_tags).ids
                        for tax_res in balance_taxes_res['taxes']:
                            tax_res['tag_ids'] = base_line._revert_signed_tags(self.env['account.account.tag'].browse(tax_res['tag_ids'])).ids

                for b_tax_res, ac_tax_res in zip(balance_taxes_res['taxes'], amount_currency_taxes_res['taxes']):
                    tax = self.env['account.tax'].browse(b_tax_res['id'])
                    b_tax_res['amount_currency'] = ac_tax_res['amount']

                    # A tax having a fixed amount must be converted into the company currency when dealing with a
                    # foreign currency.
                    if tax.amount_type == 'fixed':
                        b_tax_res['amount'] = base_line.currency_id._convert(b_tax_res['amount'], move.company_id.currency_id, move.company_id, move.date)

            return balance_taxes_res

        taxes_map = {}

        # ==== Add tax lines ====
        to_remove = self.env['account.move.line']
        for line in self.line_ids.filtered('tax_repartition_line_id'):
            grouping_dict = self._get_tax_grouping_key_from_tax_line(line)
            grouping_key = _serialize_tax_grouping_key(grouping_dict)
            if grouping_key in taxes_map:
                # A line with the same key does already exist, we only need one
                # to modify it; we have to drop this one.
                to_remove += line
            else:
                taxes_map[grouping_key] = {
                    'tax_line': line,
                    'balance': 0.0,
                    'amount_currency': 0.0,
                    'tax_base_amount': 0.0,
                    'grouping_dict': False,
                }
        self.line_ids -= to_remove

        # ==== Mount base lines ====
        for line in self.line_ids.filtered(lambda line: not line.tax_repartition_line_id):
            # Don't call compute_all if there is no tax.
            if not line.tax_ids:
                line.tag_ids = [(5, 0, 0)]
                continue

            compute_all_vals = _compute_base_line_taxes(line)

            # Assign tags on base line
            line.tag_ids = compute_all_vals['base_tags']

            tax_exigible = True
            for tax_vals in compute_all_vals['taxes']:
                grouping_dict = self._get_tax_grouping_key_from_base_line(line, tax_vals)
                grouping_key = _serialize_tax_grouping_key(grouping_dict)

                tax_repartition_line = self.env['account.tax.repartition.line'].browse(tax_vals['tax_repartition_line_id'])
                tax = tax_repartition_line.invoice_tax_id or tax_repartition_line.refund_tax_id

                if tax.tax_exigibility == 'on_payment':
                    tax_exigible = False

                taxes_map_entry = taxes_map.setdefault(grouping_key, {
                    'tax_line': None,
                    'balance': 0.0,
                    'amount_currency': 0.0,
                    'tax_base_amount': 0.0,
                    'grouping_dict': False,
                })
                taxes_map_entry['balance'] += tax_vals['amount']
                taxes_map_entry['amount_currency'] += tax_vals.get('amount_currency', 0.0)
                taxes_map_entry['tax_base_amount'] += tax_vals['base']
                taxes_map_entry['grouping_dict'] = grouping_dict
            line.tax_exigible = tax_exigible

        # ==== Process taxes_map ====
        for taxes_map_entry in taxes_map.values():
            # Don't create tax lines with zero balance.
            if self.currency_id.is_zero(taxes_map_entry['balance']) and self.currency_id.is_zero(taxes_map_entry['amount_currency']):
                taxes_map_entry['grouping_dict'] = False

            tax_line = taxes_map_entry['tax_line']
            tax_base_amount = -taxes_map_entry['tax_base_amount'] if self.is_inbound() else taxes_map_entry['tax_base_amount']

            if not tax_line and not taxes_map_entry['grouping_dict']:
                continue
            elif tax_line and recompute_tax_base_amount:
                tax_line.tax_base_amount = tax_base_amount
            elif tax_line and not taxes_map_entry['grouping_dict']:
                # The tax line is no longer used, drop it.
                self.line_ids -= tax_line
            elif tax_line:
                tax_line.update({
                    'amount_currency': taxes_map_entry['amount_currency'],
                    'debit': taxes_map_entry['balance'] > 0.0 and taxes_map_entry['balance'] or 0.0,
                    'credit': taxes_map_entry['balance'] < 0.0 and -taxes_map_entry['balance'] or 0.0,
                    'tax_base_amount': tax_base_amount,
                })
            else:
                create_method = in_draft_mode and self.env['account.move.line'].new or self.env['account.move.line'].create
                tax_repartition_line_id = taxes_map_entry['grouping_dict']['tax_repartition_line_id']
                tax_repartition_line = self.env['account.tax.repartition.line'].browse(tax_repartition_line_id)
                tax = tax_repartition_line.invoice_tax_id or tax_repartition_line.refund_tax_id
                tax_line = create_method({
                    'name': tax.name,
                    'move_id': self.id,
                    'partner_id': line.partner_id.id,
                    'company_id': line.company_id.id,
                    'company_currency_id': line.company_currency_id.id,
                    'quantity': 1.0,
                    'date_maturity': False,
                    'amount_currency': taxes_map_entry['amount_currency'],
                    'debit': taxes_map_entry['balance'] > 0.0 and taxes_map_entry['balance'] or 0.0,
                    'credit': taxes_map_entry['balance'] < 0.0 and -taxes_map_entry['balance'] or 0.0,
                    'tax_base_amount': tax_base_amount,
                    'exclude_from_invoice_tab': True,
                    'tax_exigible': tax.tax_exigibility == 'on_invoice',
                    **taxes_map_entry['grouping_dict'],
                })

            if in_draft_mode:
                tax_line._onchange_amount_currency()
                tax_line._onchange_balance()
    
class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    is_percentage = fields.Boolean('Is Discount (%)',index=True,store=True)
    discount = fields.Float('Discount',store=True)
    discount_value = fields.Float(string='Discount', digits='Discount', default=0.0,)
    is_sale = fields.Boolean('From sale',default=False)


    # @api.onchange('is_percentage')
    # def percentage_onchange(self):
    #     for line in self:
    #         line.update(line._get_price_total_and_subtotal(price_unit=self.price_unit, is_percentage=self.is_percentage))
            # if line.move_id:
                # perc = self.env['is.percentage'].create({'name':line.id,'perc':line.is_percentage})
                # line.move_id.write({'is_percentage' : [(6, 0, [perc.id])]})

    @api.onchange('quantity', 'discount', 'price_unit','is_percentage', 'tax_ids')
    def _onchange_price_subtotal(self):
        res = super(AccountMoveLine,self)._onchange_price_subtotal()
        return res

    def _get_price_total_and_subtotal(self, price_unit=None,quantity=None, discount=None, currency=None, product=None, partner=None, taxes=None, move_type=None,is_percentage=None):
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
            is_percentage=is_percentage or self.is_percentage,
        )
  
    
    @api.model
    def _get_price_total_and_subtotal_model(self, price_unit, quantity, discount, currency, product, partner, taxes, move_type,is_percentage=None):
        ''' This method is used to compute 'price_total' & 'price_subtotal'.

        :param price_unit:  The current price unit.
        :param quantity:    The current quantity.
        :param discount:    The current discount.
        :param is_percentage:    The current discount type.
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
        # raise UserError(move_type)
        if discount:
            if is_percentage == True:
                price_unit_wo_discount = price_unit * (1 -(discount/100))
            else:
                # raise UserError(self.is_percentage)
                price_unit_wo_discount = price_unit - discount/quantity
        else:
            price_unit_wo_discount = price_unit
        # price_unit_wo_discount2 = 0.0
        # if self.discount_value:
        #     price_unit_wo_discount2 = price_unit - self.discount_value/quantity
        # else:
            # price_unit_wo_discount = self.price_unit
        
        subtotal = quantity * price_unit_wo_discount
        # self.update({'price_subtotal':subtotal})
        # Compute 'price_total'.
        if taxes:
            if move_type == 'out_invoice':
                taxes_res = taxes._origin.compute_all(price_unit_wo_discount,
                    quantity=quantity, currency=currency, product=product, partner=partner, is_refund=move_type in ('out_refund', 'in_refund'))
                res['price_subtotal'] = taxes_res['total_excluded'] + discount
                res['price_total'] = taxes_res['total_included'] + discount
            else:
                taxes_res = taxes._origin.compute_all(price_unit_wo_discount,
                    quantity=quantity, currency=currency, product=product, partner=partner, is_refund=move_type in ('out_refund', 'in_refund'))
                res['price_subtotal'] = taxes_res['total_excluded'] 
                res['price_total'] = taxes_res['total_included'] 
        else:
            if move_type == 'out_invoice':
                res['price_total'] = res['price_subtotal'] = subtotal + discount
            else:
                res['price_total'] = res['price_subtotal'] = subtotal
        #In case of multi currency, round before it's use for computing debit credit
        if currency:
            res = {k: currency.round(v) for k, v in res.items()}
        return res

    @api.model_create_multi
    def create(self, vals_list):
        # OVERRIDE
        ACCOUNTING_FIELDS = ('debit', 'credit', 'amount_currency')
        BUSINESS_FIELDS = ('price_unit', 'quantity', 'discount','is_percentage', 'tax_ids')

        for vals in vals_list:
            move = self.env['account.move'].browse(vals['move_id'])
            vals.setdefault('company_currency_id', move.company_id.currency_id.id) # important to bypass the ORM limitation where monetary fields are not rounded; more info in the commit message

            if move.is_invoice(include_receipts=True):
                currency = move.currency_id
                partner = self.env['res.partner'].browse(vals.get('partner_id'))
                taxes = self.resolve_2many_commands('tax_ids', vals.get('tax_ids', []), fields=['id'])
                tax_ids = set(tax['id'] for tax in taxes)
                taxes = self.env['account.tax'].browse(tax_ids)

                # Ensure consistency between accounting & business fields.
                # As we can't express such synchronization as computed fields without cycling, we need to do it both
                # in onchange and in create/write. So, if something changed in accounting [resp. business] fields,
                # business [resp. accounting] fields are recomputed.
                if any(vals.get(field) for field in ACCOUNTING_FIELDS):
                    if vals.get('currency_id'):
                        balance = vals.get('amount_currency', 0.0)
                    else:
                        balance = vals.get('debit', 0.0) - vals.get('credit', 0.0)
                    price_subtotal = self._get_price_total_and_subtotal_model(
                        vals.get('price_unit', 0.0),
                        vals.get('quantity', 0.0),
                        vals.get('discount', 0.0),
                        currency,
                        self.env['product.product'].browse(vals.get('product_id')),
                        partner,
                        taxes,
                        move.type,
                        # vals.get('is_percentage', False),
                    ).get('price_subtotal', 0.0)
                    vals.update(self._get_fields_onchange_balance_model(
                        vals.get('quantity', 0.0),
                        vals.get('discount', 0.0),
                        balance,
                        move.type,
                        currency,
                        taxes,
                        price_subtotal
                    ))
                    vals.update(self._get_price_total_and_subtotal_model(
                        vals.get('price_unit', 0.0),
                        vals.get('quantity', 0.0),
                        vals.get('discount', 0.0),
                        currency,
                        self.env['product.product'].browse(vals.get('product_id')),
                        partner,
                        taxes,
                        move.type,
                        vals.get('is_percentage', False),
                    ))
                elif any(vals.get(field) for field in BUSINESS_FIELDS):
                    vals.update(self._get_price_total_and_subtotal_model(
                        vals.get('price_unit', 0.0),
                        vals.get('quantity', 0.0),
                        vals.get('discount', 0.0),
                        currency,
                        self.env['product.product'].browse(vals.get('product_id')),
                        partner,
                        taxes,
                        move.type,
                        vals.get('is_percentage', False),
                    ))
                    vals.update(self._get_fields_onchange_subtotal_model(
                        vals['price_subtotal'],
                        move.type,
                        currency,
                        move.company_id,
                        move.date,
                    ))

            # Ensure consistency between taxes & tax exigibility fields.
            if 'tax_exigible' in vals:
                continue
            if vals.get('tax_repartition_line_id'):
                repartition_line = self.env['account.tax.repartition.line'].browse(vals['tax_repartition_line_id'])
                tax = repartition_line.invoice_tax_id or repartition_line.refund_tax_id
                vals['tax_exigible'] = tax.tax_exigibility == 'on_invoice'
            elif vals.get('tax_ids'):
                tax_ids = [v['id'] for v in self.resolve_2many_commands('tax_ids', vals['tax_ids'], fields=['id'])]
                taxes = self.env['account.tax'].browse(tax_ids).flatten_taxes_hierarchy()
                vals['tax_exigible'] = not any(tax.tax_exigibility == 'on_payment' for tax in taxes)

        lines = super(AccountMoveLine, self).create(vals_list)

        moves = lines.mapped('move_id')
        if self._context.get('check_move_validity', True):
            moves._check_balanced()
        moves._check_fiscalyear_lock_date()
        lines._check_tax_lock_date()

        return lines

class DiscountType(models.Model):
    _name = "discount.type"

    name = fields.Char('Discount Name')
    so_id = fields.Char(string="SO # Woo-commerce")
    order_id = fields.Many2one('sale.order',string="SO # ODOO")
    product_id = fields.Many2one('product.product',string="Product")
    value = fields.Float('Discount Value')

class SaleOrder(models.Model):
    _inherit = "sale.order"

    amount_discount = fields.Float('Discount',compute="_amount_all")

    @api.depends('order_line.price_total','order_line.discount','order_line.is_percentage')
    def _amount_all(self):
        """
        Compute the total amounts of the SO.
        """
        for order in self:
            amount_untaxed = amount_tax = amount_discount = 0.0
            for line in order.order_line:
                if line.discount_value :
                    if line.is_percentage == True:
                        amount_discount += line.price_unit * (line.discount_value/100)
                    else:
                        amount_discount += line.discount_value
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
            order.update({
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax,
                'amount_discount':amount_discount,
                'amount_total': amount_untaxed + amount_tax - amount_discount,
            })

    # def _prepare_invoice(self):
    #     res = super(SaleOrder, self)._prepare_invoice()
    #     for rec in self:
    #         res['amount_discount'] = rec.amount_discount
    #     return res

    # def _compute_amount_undiscounted(self):
    #     for order in self:
    #         total = 0.0
    #         for line in order.order_line:
    #             # if line.discount :
    #             #     if line.is_percentage == True:
    #             #         discount = line.price_unit * (line.discount/100)
    #             #     else:
    #             #         discount = line.price_unit - line.discount/line.product_uom_qty
    #             # else:
    #             #     discount = 0
    #             # total += line.price_subtotal + discount * line.product_uom_qty  # why is there a discount in a field named amount_undiscounted ??
    #             total += line.price_subtotal
    #         order.amount_undiscounted = total

    # def _amount_by_group(self):
    #     for order in self:
    #         currency = order.currency_id or order.company_id.currency_id
    #         fmt = partial(formatLang, self.with_context(lang=order.partner_id.lang).env, currency_obj=currency)
    #         res = {}
    #         for line in order.order_line:
    #             price_reduce = line.price_unit 
    #             # if line.discount :
    #             #     if line.is_percentage == True:
    #             #         price_reduce = line.price_unit * (1.0 - line.discount/100)
    #             #     else:
    #             #         price_reduce = line.price_unit - line.discount/line.product_uom_qty
    #             # else:
    #             #     price_reduce = line.price_unit
    #             taxes = line.tax_id.compute_all(price_reduce, quantity=line.product_uom_qty, product=line.product_id, partner=order.partner_shipping_id)['taxes']
    #             for tax in line.tax_id:
    #                 group = tax.tax_group_id
    #                 res.setdefault(group, {'amount': 0.0, 'base': 0.0})
    #                 for t in taxes:
    #                     if t['id'] == tax.id or t['id'] in tax.children_tax_ids.ids:
    #                         res[group]['amount'] += t['amount']
    #                         res[group]['base'] += t['base']
    #         res = sorted(res.items(), key=lambda l: l[0].sequence)
    #         order.amount_by_group = [(
    #             l[0].name, l[1]['amount'], l[1]['base'],
    #             fmt(l[1]['amount']), fmt(l[1]['base']),
    #             len(res),
    #         ) for l in res]


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    discount_type = fields.Many2many('discount.type',string="Discount Type")
    is_percentage = fields.Boolean('Is Discount (%)',index=True,store=True)
    discount_value = fields.Float(string='Discount', digits='Discount', default=0.0)

    @api.depends('product_uom_qty', 'discount','discount_value', 'price_unit', 'tax_id')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        for line in self:
            if line.discount_value :
                price = line.price_unit - line.discount_value/line.product_uom_qty
            else:
                price = line.price_unit
            # price = line.price_unit 
            taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty, product=line.product_id, partner=line.order_id.partner_shipping_id)
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'] +line.discount_value,
                'price_subtotal': taxes['total_excluded'] +line.discount_value,
            })
            if self.env.context.get('import_file', False) and not self.env.user.user_has_groups('account.group_account_manager'):
                line.tax_id.invalidate_cache(['invoice_repartition_line_ids'], [line.tax_id.id])

    @api.onchange('product_uom')
    def product_uom_change(self):
        res = super(SaleOrderLine,self).product_uom_change()
        return res

    def _prepare_invoice_line(self):
        """
        Prepare the dict of values to create the new invoice line for a sales order line.

        :param qty: float quantity to invoice
        """
        res = super(SaleOrderLine,self)._prepare_invoice_line()
        res['is_sale'] = True
        res['discount'] = self.discount_value
        return res

    # @api.depends('price_unit', 'discount')
    # def _get_price_reduce(self):
    #     for line in self:
    #         # if line.discount :
    #         #     if line.is_percentage == True:
    #         #         line.price_reduce = line.price_unit * (1.0  - (line.discount/100))
    #         #     else:
    #         #         line.price_reduce = line.price_unit - line.discount/line.product_uom_qty
    #         # else:
    #         #     line.price_reduce = line.price_unit
    #         line.price_reduce = line.price_unit 


class Company(models.Model):
    _inherit = "res.company"

    sales_discount_account = fields.Many2one('account.account', string="Sales Discount Account")


class KSResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sales_discount_account = fields.Many2one('account.account', string="Sales Discount Account", related='company_id.sales_discount_account', readonly=False)
    