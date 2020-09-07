# -*- coding: utf-8 -*-
###################################################################################
#
#    Copyright (C) 2020 Odox SoftHub LLP(<www.odoxsofthub.com>)
#    Author: Albin Mathew(<albinmathew07@outlook.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###################################################################################
import ast

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.depends(
        'discount_type',
        'discount_rate',
        'line_ids.debit',
        'line_ids.credit',
        'line_ids.amount_currency',
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        'currency_charge',
        'line_ids.payment_id.state')
    def _compute_amount(self):

        invoice_ids = [move.id for move in self if move.id and move.is_invoice(include_receipts=True)]
        self.env['account.payment'].flush(['state'])
        if invoice_ids:
            self._cr.execute(
                '''
                    SELECT move.id
                    FROM account_move move
                    JOIN account_move_line line ON line.move_id = move.id
                    JOIN account_partial_reconcile part ON part.debit_move_id = line.id OR part.credit_move_id = line.id
                    JOIN account_move_line rec_line ON
                        (rec_line.id = part.credit_move_id AND line.id = part.debit_move_id)
                        OR
                        (rec_line.id = part.debit_move_id AND line.id = part.credit_move_id)
                    JOIN account_payment payment ON payment.id = rec_line.payment_id
                    JOIN account_journal journal ON journal.id = rec_line.journal_id
                    WHERE payment.state IN ('posted', 'sent')
                    AND journal.post_at = 'bank_rec'
                    AND move.id IN %s
                ''', [tuple(invoice_ids)]
            )
            in_payment_set = set(res[0] for res in self._cr.fetchall())
        else:
            in_payment_set = {}

        for move in self:
            total_untaxed = 0.0
            total_untaxed_currency = 0.0
            total_tax = 0.0
            total_tax_currency = 0.0
            total_residual = 0.0
            total_residual_currency = 0.0
            currencies = set()
            total_commission = 0.0
            amount_discount = 0.0
            for line in move.line_ids:
                if line.currency_id:
                    currencies.add(line.currency_id)

                # Untaxed amount.
                if (move.is_invoice(include_receipts=True) and not line.exclude_from_invoice_tab) \
                        or (move.type == 'entry' and line.debit and not line.tax_line_id):
                    total_untaxed += line.balance
                    total_untaxed_currency += line.amount_currency
                    total_commission += line.com_amount

                # Tax amount.
                if line.tax_line_id:
                    total_tax += line.balance
                    total_tax_currency += line.amount_currency

                # Residual amount.
                if move.type == 'entry' or line.account_id.user_type_id.type in ('receivable', 'payable'):
                    total_residual += line.amount_residual
                    total_residual_currency += line.amount_residual_currency

            total = total_untaxed + total_tax
            total_currency = total_untaxed_currency + total_tax_currency
            if move.type == 'entry' or move.is_outbound():
                sign = 1
            else:
                sign = -1
            if move.discount_type:
                if move.discount_type == 'percent':
                    if total_currency:
                        amount_discount = (sign * total_currency * move.discount_rate) / 100
                    else:
                        amount_discount = (sign * total * move.discount_rate) / 100
                else:
                    amount_discount = move.discount_rate

            move.amount_discount = amount_discount
            move.amount_commission = sum(
                (line.quantity * line.price_unit * line.commission) / 100 for line in move.invoice_line_ids)
            move.amount_untaxed = sign * (total_untaxed_currency if len(currencies) == 1 else total_untaxed) + sum(
                (line.quantity * line.price_unit * line.discount) / 100 for line in move.invoice_line_ids)
            move.amount_tax = sign * (total_tax_currency if len(currencies) == 1 else total_tax)

            move.amount_total = sign * (
                total_currency if len(currencies) == 1 else total) - total_commission - amount_discount + move.currency_charge
            if move.type in ['out_invoice', 'out_refund']:
                move.amount_total = sign * (total_currency if len(
                    currencies) == 1 else total) - total_commission - amount_discount + move.bank_charge_currency + \
                                    move.currency_charge

            move.amount_residual = -sign * (total_residual_currency if len(currencies) == 1 else total_residual)
            move.amount_untaxed_signed = -total_untaxed
            move.amount_tax_signed = -total_tax
            move.amount_total_signed = -total
            move.amount_residual_signed = total_residual

            currency = len(currencies) == 1 and currencies.pop() or move.company_id.currency_id
            is_paid = currency and currency.is_zero(move.amount_residual) or not move.amount_residual

            # Compute 'invoice_payment_state'.
            if move.state == 'posted' and is_paid:
                if move.id in in_payment_set:
                    move.invoice_payment_state = 'in_payment'
                else:
                    move.invoice_payment_state = 'paid'
            else:
                move.invoice_payment_state = 'not_paid'

    def _get_default_reference(self):
        """:return PO reference"""

        if self._context.get('default_ref'):
            return self._context.get('default_ref')
        return False

    reference = fields.Char(string='Reference', copy=False, store=True, default=_get_default_reference,
                            readonly=True, states={'draft': [('readonly', False)]})
    sale_id = fields.Many2one('sale.order', string="Sale Order", store=True, readonly=True)
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order', store=True, readonly=True)
    discount_type = fields.Selection([('percent', 'Percentage'), ('amount', 'Amount')], string='Discount Type',
                                     readonly=True, states={'draft': [('readonly', False)]}, default='percent')
    discount_rate = fields.Float('Discount Amount', digits=(16, 2), readonly=True,
                                 states={'draft': [('readonly', False)]})
    amount_discount = fields.Monetary(string='Discount', store=True, readonly=True, compute='_compute_amount',
                                      track_visibility='always')
    amount_commission = fields.Monetary(string='Commission', store=True, readonly=True, compute='_compute_amount',
                                        track_visibility='always')
    is_order_to_invoice = fields.Boolean('Order To Invoice')
    bank_charge = fields.Float(string="Bank Charge", default=100, copy=True, readonly=True,
                               states={'draft': [('readonly', False)]})
    bank_charge_currency = fields.Float(string="Bank Charge", default=100, copy=True, readonly=True,
                                        states={'draft': [('readonly', False)]})
    customer_currency_id = fields.Many2one('res.currency', string='Customer Currency')
    currency_charge = fields.Float('Currency Charge', compute='_compute_currency_charge')

    @api.depends('customer_currency_id', 'currency_id', 'amount_untaxed_signed')
    def _compute_currency_charge(self):
        for record in self:
            if record.customer_currency_id and record.currency_id:
                currency_amount = record.company_id.currency_id._convert(record.amount_untaxed_signed,
                                                                         record.currency_id, record.company_id,
                                                                         record.date)
                customer_currency_amount = record.company_id.currency_id._convert(record.amount_untaxed_signed,
                                                                                  record.customer_currency_id,
                                                                                  record.company_id,
                                                                                  record.date)
                print(customer_currency_amount, currency_amount)
                record.currency_charge = currency_amount - customer_currency_amount
            else:
                record.currency_charge = 0

    def _get_reconciled_info_JSON_values(self):
        self.ensure_one()
        foreign_currency = self.currency_id if self.currency_id != self.company_id.currency_id else False

        reconciled_vals = []
        pay_term_line_ids = self.line_ids.filtered(
            lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
        pay_term_line_ids = pay_term_line_ids.filtered(lambda line: not line.is_commission_line)
        pay_term_line_ids = pay_term_line_ids.filtered(lambda line: not line.is_discount_line)
        pay_term_line_ids = pay_term_line_ids.filtered(lambda line: not line.is_bank_fee_line)
        partials = pay_term_line_ids.mapped('matched_debit_ids') + pay_term_line_ids.mapped('matched_credit_ids')

        for partial in partials:
            counterpart_lines = partial.debit_move_id + partial.credit_move_id
            commission_line_ids = counterpart_lines.filtered(lambda line: line.is_commission_line)
            discount_line_ids = counterpart_lines.filtered(lambda line: line.is_discount_line)
            bank_fee_line_ids = counterpart_lines.filtered(lambda line: line.is_bank_fee_line)
            if bank_fee_line_ids or discount_line_ids or commission_line_ids:
                continue
            counterpart_line = counterpart_lines.filtered(lambda line: line not in self.line_ids)

            if foreign_currency and partial.currency_id == foreign_currency:
                amount = partial.amount_currency
            else:
                amount = partial.company_currency_id._convert(partial.amount, self.currency_id, self.company_id,
                                                              self.date)

            if float_is_zero(amount, precision_rounding=self.currency_id.rounding):
                continue
            ref = counterpart_line.move_id.name
            if counterpart_line.move_id.ref:
                ref += ' (' + counterpart_line.move_id.ref + ')'

            reconciled_vals.append({
                'name': counterpart_line.name,
                'journal_name': counterpart_line.journal_id.name,
                'amount': amount,
                'currency': self.currency_id.symbol,
                'digits': [69, self.currency_id.decimal_places],
                'position': self.currency_id.position,
                'date': counterpart_line.date,
                'payment_id': counterpart_line.id,
                'account_payment_id': counterpart_line.payment_id.id,
                'payment_method_name': counterpart_line.payment_id.payment_method_id.name if counterpart_line.journal_id.type == 'bank' else None,
                'move_id': counterpart_line.move_id.id,
                'ref': ref,
            })
        return reconciled_vals

    @api.onchange('discount_type', 'discount_rate', 'invoice_line_ids')
    def supply_rate(self):
        self._recompute_dynamic_lines()

    def button_dummy(self):
        self.supply_rate()
        return True

    @api.onchange('bank_charge', 'currency_id', 'customer_currency_id')
    def _onchange_bank_charge(self):
        if self.currency_id != self.company_id.currency_id:
            amount_currency = abs(self.bank_charge)
            self.bank_charge_currency = self.company_currency_id._convert(amount_currency, self.currency_id,
                                                                          self.company_id,
                                                                          self.date)
        else:
            self.bank_charge_currency = self.bank_charge
        self._recompute_dynamic_lines()

    def _recompute_bank_fee_lines(self):
        """ thi function is used to create journal item for bank fee"""
        self.ensure_one()
        in_draft_mode = self != self._origin

        def _prepare_bank_fee_move_line(self):
            """
            This function used to prepare bank fee line
            :return:{dict} containing {field: value} for the account.move.line
            """
            self.ensure_one()
            get_param = self.env['ir.config_parameter'].sudo().get_param
            bank_fee_account = get_param('odx_sale_purchase_customization.bank_fee_account_id')
            if not bank_fee_account:
                raise UserError(_("Please configure a account for bank_fee in settings."))
            bank_fee_account = ast.literal_eval(bank_fee_account)
            bank_fee_account_id = self.env["account.account"].search([('id', '=', bank_fee_account)], limit=1)
            amount_currency = 0.0
            bank_fee_amount = self.bank_charge_currency
            if self.currency_id != self.company_id.currency_id:
                amount_currency = abs(bank_fee_amount)
                bank_fee_amount = self.currency_id._convert(amount_currency, self.company_currency_id,
                                                            self.company_id,
                                                            self.date)
            bank_fee_move_line = {
                'debit': bank_fee_amount < 0.0 and - bank_fee_amount or 0.0,
                'credit': bank_fee_amount > 0.0 and bank_fee_amount or 0.0,
                'name': '%s: %s' % (self.reference, 'Bank Fee'),
                'move_id': self.id,
                'currency_id': self.currency_id.id if self.currency_id != self.company_id.currency_id else False,
                'account_id': bank_fee_account_id.id,
                'exclude_from_invoice_tab': True,
                'partner_id': self.partner_id.id,
                'amount_currency': -amount_currency,
                'quantity': 1.0,
                'is_bank_fee_line': True

            }
            return bank_fee_move_line

        def _prepare_bank_fee_move_partner_line(self):
            """
            this function used t
            :return:{dict} containing {field: value} for the account.move.line
            """
            self.ensure_one()
            if self.partner_id:
                # Retrieve account from partner.
                if self.is_sale_document(include_receipts=True):
                    partner_account = self.partner_id.property_account_receivable_id
                else:
                    partner_account = self.partner_id.property_account_payable_id
            else:
                # Search new account.
                domain = [
                    ('company_id', '=', self.company_id.id),
                    ('internal_type', '=',
                     'receivable' if self.type in ('out_invoice', 'out_refund', 'out_receipt') else 'payable'), ]
                partner_account = self.env['account.account'].search(domain, limit=1)
            amount_currency = 0.0
            bank_fee_amount = self.bank_charge_currency
            if self.currency_id != self.company_id.currency_id:
                amount_currency = abs(bank_fee_amount)
                bank_fee_amount = self.currency_id._convert(amount_currency, self.company_currency_id,
                                                            self.company_id,
                                                            self.date)
            bank_fee_move_partner_line = {
                'credit': bank_fee_amount < 0.0 and - bank_fee_amount or 0.0,
                'debit': bank_fee_amount > 0.0 and bank_fee_amount or 0.0,
                'name': '%s: %s' % (self.reference, 'Bank Fee'),
                'move_id': self.id,
                'currency_id': self.currency_id.id if self.currency_id != self.company_id.currency_id else False,
                'account_id': partner_account.id,
                'exclude_from_invoice_tab': True,
                'partner_id': self.partner_id.id,
                'amount_currency': amount_currency,
                'quantity': 1.0,
                'is_bank_fee_line': True
            }
            return bank_fee_move_partner_line

        existing_bank_fee_lines = self.line_ids.filtered(lambda line: line.is_bank_fee_line)
        if existing_bank_fee_lines:
            self.line_ids -= existing_bank_fee_lines
        bank_fee_amount = self.bank_charge
        if bank_fee_amount:
            bank_fee_move_line = _prepare_bank_fee_move_line(self)
            bank_fee_move_partner_line = _prepare_bank_fee_move_partner_line(self)
            create_method = in_draft_mode and self.env['account.move.line'].new or self.env[
                'account.move.line'].create
            new_bank_fee_line = create_method(bank_fee_move_line)
            new_bank_fee_partner_line = create_method(bank_fee_move_partner_line)
            if in_draft_mode:
                new_bank_fee_line._onchange_amount_currency()
                new_bank_fee_line._onchange_balance()
                new_bank_fee_partner_line._onchange_amount_currency()
                new_bank_fee_partner_line._onchange_balance()

    def _recompute_discount_lines(self):
        """ thi function is used to create journal item for discount"""
        self.ensure_one()
        in_draft_mode = self != self._origin

        def _prepare_discount_move_line(self):
            """
            This function searches a specific product i.e, discount and
            returns field values required in purchase journal entry line.
            The whole purpose is to add a new product for discount from
            the product configured in account.move.line
            :return:{dict} containing {field: value} for the account.move.line
            """
            self.ensure_one()
            get_param = self.env['ir.config_parameter'].sudo().get_param
            discount_account = get_param('odx_sale_purchase_customization.discount_account_id')
            if not discount_account:
                raise UserError(_("Please configure a account for discount in settings."))
            discount_account = ast.literal_eval(discount_account)
            discount_account_id = self.env["account.account"].search([('id', '=', discount_account)], limit=1)
            amount_currency = 0.0
            if self.type == 'entry' or self.is_outbound():
                sign = 1
            else:
                sign = -1
            discount_amount = sign * self.amount_discount
            if self.currency_id != self.company_id.currency_id:
                amount_currency = discount_amount
                discount_amount = self.currency_id._convert(amount_currency, self.company_currency_id,
                                                            self.company_id,
                                                            self.date)
            discount_move_line = {
                'debit': discount_amount < 0.0 and - discount_amount or 0.0,
                'credit': discount_amount > 0.0 and discount_amount or 0.0,
                'name': '%s: %s' % (self.reference, 'Discount'),
                'move_id': self.id,
                'currency_id': self.currency_id.id if self.currency_id != self.company_id.currency_id else False,
                'account_id': discount_account_id.id,
                'exclude_from_invoice_tab': True,
                'partner_id': self.partner_id.id,
                'amount_currency': -amount_currency,
                'quantity': 1.0,
                'is_discount_line': True

            }
            return discount_move_line

        def _prepare_discount_move_partner_line(self):
            """
            This function searches a specific product i.e, discount and
            returns field values required in purchase journal entry line.
            The whole purpose is to add a new product for discount from
            the product configured in account.move.line
            :return:{dict} containing {field: value} for the account.move.line
            """
            self.ensure_one()
            if self.partner_id:
                # Retrieve account from partner.
                if self.is_sale_document(include_receipts=True):
                    partner_account = self.partner_id.property_account_receivable_id
                else:
                    partner_account = self.partner_id.property_account_payable_id
            else:
                # Search new account.
                domain = [
                    ('company_id', '=', self.company_id.id),
                    ('internal_type', '=',
                     'receivable' if self.type in ('out_invoice', 'out_refund', 'out_receipt') else 'payable'), ]
                partner_account = self.env['account.account'].search(domain, limit=1)
            amount_currency = 0.0
            if self.type == 'entry' or self.is_outbound():
                sign = 1
            else:
                sign = -1
            discount_amount = sign * self.amount_discount
            if self.currency_id != self.company_id.currency_id:
                amount_currency = discount_amount
                discount_amount = self.currency_id._convert(amount_currency, self.company_currency_id,
                                                            self.company_id,
                                                            self.date)
            discount_move_partner_line = {
                'credit': discount_amount < 0.0 and - discount_amount or 0.0,
                'debit': discount_amount > 0.0 and discount_amount or 0.0,
                'name': '%s: %s' % (self.reference, 'Discount'),
                'move_id': self.id,
                'currency_id': self.currency_id.id if self.currency_id != self.company_id.currency_id else False,
                'account_id': partner_account.id,
                'exclude_from_invoice_tab': True,
                'partner_id': self.partner_id.id,
                'amount_currency': amount_currency,
                'quantity': 1.0,
                'is_discount_line': True
            }
            return discount_move_partner_line

        existing_discount_lines = self.line_ids.filtered(lambda line: line.is_discount_line)
        if existing_discount_lines:
            self.line_ids -= existing_discount_lines
        discount_amount = self.amount_discount
        if discount_amount:
            discount_move_line = _prepare_discount_move_line(self)
            discount_move_partner_line = _prepare_discount_move_partner_line(self)
            create_method = in_draft_mode and self.env['account.move.line'].new or self.env[
                'account.move.line'].create
            new_discount_line = create_method(discount_move_line)
            new_discount_partner_line = create_method(discount_move_partner_line)

            if in_draft_mode:
                new_discount_line._onchange_amount_currency()
                new_discount_line._onchange_balance()
                new_discount_partner_line._onchange_amount_currency()
                new_discount_partner_line._onchange_balance()

    def _recompute_commission_lines(self):
        """ thi function is used to create journal item for commission"""
        self.ensure_one()
        in_draft_mode = self != self._origin

        def _prepare_commission_move_line(self):
            """
            This function searches a specific product i.e, commission and
            returns field values required in purchase journal entry line.
            The whole purpose is to add a new product for commission from
            the product configured in account.move.line
            :return:{dict} containing {field: value} for the account.move.line
            """
            self.ensure_one()
            get_param = self.env['ir.config_parameter'].sudo().get_param
            account = get_param('odx_sale_purchase_customization.commission_account_id')
            if not account:
                raise UserError(_("Please configure a account for commission in settings."))
            account = ast.literal_eval(account)
            account_id = self.env["account.account"].search([('id', '=', account)], limit=1)
            commission_amount = 00.0
            amount_currency = 0.0
            for line in self.invoice_line_ids:
                commission_amount += line.com_amount
            if self.currency_id != self.company_id.currency_id:
                amount_currency = abs(commission_amount)
                commission_amount = self.currency_id._convert(amount_currency, self.company_currency_id,
                                                              self.company_id,
                                                              self.date)
            commission_move_line = {
                'debit': commission_amount < 0.0 and - commission_amount or 0.0,
                'credit': commission_amount > 0.0 and commission_amount or 0.0,
                'name': '%s: %s' % (self.reference, 'Commission'),
                'move_id': self.id,
                'currency_id': self.currency_id.id if self.currency_id != self.company_id.currency_id else False,
                'account_id': account_id.id,
                'exclude_from_invoice_tab': True,
                'partner_id': self.partner_id.id,
                'amount_currency': -amount_currency,
                'quantity': 1.0,
                'is_commission_line': True

            }
            return commission_move_line

        def _prepare_commission_move_partner_line(self):
            """
            This function searches a specific product i.e, commission and
            returns field values required in purchase journal entry line.
            The whole purpose is to add a new product for commission from
            the product configured in account.move.line
            :return:{dict} containing {field: value} for the account.move.line
            """
            self.ensure_one()
            partner_account = False
            if self.partner_id:
                # Retrieve account from partner.
                if self.is_sale_document(include_receipts=True):
                    partner_account = self.partner_id.property_account_receivable_id
                else:
                    partner_account = self.partner_id.property_account_payable_id
            else:
                # Search new account.
                domain = [
                    ('company_id', '=', self.company_id.id),
                    ('internal_type', '=',
                     'receivable' if self.type in ('out_invoice', 'out_refund', 'out_receipt') else 'payable'), ]
                partner_account = self.env['account.account'].search(domain, limit=1)

            commission_amount = 00.0
            amount_currency = 0.0
            for line in self.invoice_line_ids:
                commission_amount += line.com_amount
            if self.currency_id != self.company_id.currency_id:
                amount_currency = abs(commission_amount)
                commission_amount = self.currency_id._convert(amount_currency, self.company_currency_id,
                                                              self.company_id,
                                                              self.date)
            commission_move_partner_line = {
                'credit': commission_amount < 0.0 and - commission_amount or 0.0,
                'debit': commission_amount > 0.0 and commission_amount or 0.0,
                'name': '%s: %s' % (self.reference, 'Commission'),
                'move_id': self.id,
                'currency_id': self.currency_id.id if self.currency_id != self.company_id.currency_id else False,
                'account_id': partner_account.id,
                'exclude_from_invoice_tab': True,
                'partner_id': self.partner_id.id,
                'amount_currency': amount_currency,
                'quantity': 1.0,
                'is_commission_line': True
            }
            return commission_move_partner_line

        existing_commission_lines = self.line_ids.filtered(lambda line: line.is_commission_line)
        if existing_commission_lines:
            self.line_ids -= existing_commission_lines
        commission_amount = 0.00
        for line in self.invoice_line_ids:
            commission_amount += line.com_amount
        if commission_amount:
            commission_move_line = _prepare_commission_move_line(self)
            commission_move_partner_line = _prepare_commission_move_partner_line(self)
            create_method = in_draft_mode and self.env['account.move.line'].new or self.env[
                'account.move.line'].create
            new_commission_line = create_method(commission_move_line)
            new_commission_partner_line = create_method(commission_move_partner_line)

            if in_draft_mode:
                new_commission_line._onchange_amount_currency()
                new_commission_line._onchange_balance()
                new_commission_partner_line._onchange_amount_currency()
                new_commission_partner_line._onchange_balance()

    def _recompute_currency_charge_lines(self):
            """ thi function is used to create journal item for currency charge"""
            self.ensure_one()
            in_draft_mode = self != self._origin

            def _prepare_currency_move_line(self):
                """
                This function searches a specific product i.e, discount and
                returns field values required in purchase journal entry line.
                The whole purpose is to add a new product for discount from
                the product configured in account.move.line
                :return:{dict} containing {field: value} for the account.move.line
                """
                self.ensure_one()
                get_param = self.env['ir.config_parameter'].sudo().get_param
                currency_diff_account = get_param('odx_sale_purchase_customization.currency_diff_account_id')
                if not currency_diff_account:
                    raise UserError(_("Please configure a account for Currency Diff in settings."))
                currency_diff_account = ast.literal_eval(currency_diff_account)
                currency_diff_account_id = self.env["account.account"].search([('id', '=', currency_diff_account)],
                                                                              limit=1)
                amount_currency = 0.0
                if self.type == 'entry' or self.is_outbound():
                    sign = 1
                else:
                    sign = -1
                currency_charge = sign * self.currency_charge
                if self.currency_id != self.company_id.currency_id:
                    amount_currency = currency_charge
                    currency_charge = self.currency_id._convert(amount_currency, self.company_currency_id,
                                                                self.company_id,
                                                                self.date)
                currency_move_line = {
                    'credit': currency_charge < 0.0 and - currency_charge or 0.0,
                    'debit': currency_charge > 0.0 and currency_charge or 0.0,
                    'name': '%s: %s' % (self.reference, 'Currency Charge'),
                    'move_id': self.id,
                    'currency_id': self.currency_id.id if self.currency_id != self.company_id.currency_id else False,
                    'account_id': currency_diff_account_id.id,
                    'exclude_from_invoice_tab': True,
                    'partner_id': self.partner_id.id,
                    'amount_currency': amount_currency,
                    'quantity': 1.0,
                    'is_currency_charge_line': True
                }
                return currency_move_line

            existing_currency_charge_lines = self.line_ids.filtered(lambda line: line.is_currency_charge_line)
            if existing_currency_charge_lines:
                self.line_ids -= existing_currency_charge_lines
            currency_charge = self.currency_charge
            if currency_charge:
                currency_charge_move_line = _prepare_currency_move_line(self)
                create_method = in_draft_mode and self.env['account.move.line'].new or self.env[
                    'account.move.line'].create
                new_discount_line = create_method(currency_charge_move_line)

                if in_draft_mode:
                    new_discount_line._onchange_amount_currency()
                    new_discount_line._onchange_balance()

    def _recompute_payment_terms_lines(self):
        ''' Compute the dynamic payment term lines of the journal entry.'''
        self.ensure_one()
        in_draft_mode = self != self._origin
        today = fields.Date.context_today(self)
        self = self.with_context(force_company=self.journal_id.company_id.id)

        def _get_payment_terms_computation_date(self):
            ''' Get the date from invoice that will be used to compute the payment terms.
            :param self:    The current account.move record.
            :return:        A datetime.date object.
            '''
            if self.invoice_payment_term_id:
                return self.invoice_date or today
            else:
                return self.invoice_date_due or self.invoice_date or today

        def _get_payment_terms_account(self, payment_terms_lines):
            ''' Get the account from invoice that will be set as receivable / payable account.
            :param self:                    The current account.move record.
            :param payment_terms_lines:     The current payment terms lines.
            :return:                        An account.account record.
            '''
            if payment_terms_lines:
                # Retrieve account from previous payment terms lines in order to allow the user to set a custom one.
                return payment_terms_lines[0].account_id
            elif self.partner_id:
                # Retrieve account from partner.
                if self.is_sale_document(include_receipts=True):
                    return self.partner_id.property_account_receivable_id
                else:
                    return self.partner_id.property_account_payable_id
            else:
                # Search new account.
                domain = [
                    ('company_id', '=', self.company_id.id),
                    ('internal_type', '=',
                     'receivable' if self.type in ('out_invoice', 'out_refund', 'out_receipt') else 'payable'),
                ]
                return self.env['account.account'].search(domain, limit=1)

        def _compute_payment_terms(self, date, total_balance, total_amount_currency):
            ''' Compute the payment terms.
            :param self:                    The current account.move record.
            :param date:                    The date computed by '_get_payment_terms_computation_date'.
            :param total_balance:           The invoice's total in company's currency.
            :param total_amount_currency:   The invoice's total in invoice's currency.
            :return:                        A list <to_pay_company_currency, to_pay_invoice_currency, due_date>.
            '''
            if self.invoice_payment_term_id:
                to_compute = self.invoice_payment_term_id.compute(total_balance, date_ref=date,
                                                                  currency=self.currency_id)
                if self.currency_id != self.company_id.currency_id:
                    # Multi-currencies.
                    to_compute_currency = self.invoice_payment_term_id.compute(total_amount_currency, date_ref=date,
                                                                               currency=self.currency_id)
                    return [(b[0], b[1], ac[1]) for b, ac in zip(to_compute, to_compute_currency)]
                else:
                    # Single-currency.
                    return [(b[0], b[1], 0.0) for b in to_compute]
            else:
                return [(fields.Date.to_string(date), total_balance, total_amount_currency)]

        def _compute_diff_payment_terms_lines(self, existing_terms_lines, account, to_compute):
            ''' Process the result of the '_compute_payment_terms' method and creates/updates corresponding invoice lines.
            :param self:                    The current account.move record.
            :param existing_terms_lines:    The current payment terms lines.
            :param account:                 The account.account record returned by '_get_payment_terms_account'.
            :param to_compute:              The list returned by '_compute_payment_terms'.
            '''
            # As we try to update existing lines, sort them by due date.
            existing_terms_lines = existing_terms_lines.sorted(lambda line: line.date_maturity or today)
            existing_terms_lines_index = 0

            # Recompute amls: update existing line or create new one for each payment term.
            new_terms_lines = self.env['account.move.line']
            for date_maturity, balance, amount_currency in to_compute:
                if self.journal_id.company_id.currency_id.is_zero(balance) and len(to_compute) > 1:
                    continue

                if existing_terms_lines_index < len(existing_terms_lines):
                    # Update existing line.
                    candidate = existing_terms_lines[existing_terms_lines_index]
                    existing_terms_lines_index += 1
                    candidate.update({
                        'date_maturity': date_maturity,
                        'amount_currency': -amount_currency,
                        'debit': balance < 0.0 and -balance or 0.0,
                        'credit': balance > 0.0 and balance or 0.0,
                    })
                else:
                    # Create new line.
                    create_method = in_draft_mode and self.env['account.move.line'].new or self.env[
                        'account.move.line'].create
                    candidate = create_method({
                        'name': self.invoice_payment_ref or '',
                        'debit': balance < 0.0 and -balance or 0.0,
                        'credit': balance > 0.0 and balance or 0.0,
                        'quantity': 1.0,
                        'amount_currency': -amount_currency,
                        'date_maturity': date_maturity,
                        'move_id': self.id,
                        'currency_id': self.currency_id.id if self.currency_id != self.company_id.currency_id else False,
                        'account_id': account.id,
                        'partner_id': self.commercial_partner_id.id,
                        'exclude_from_invoice_tab': True,
                    })
                new_terms_lines += candidate
                if in_draft_mode:
                    candidate._onchange_amount_currency()
                    candidate._onchange_balance()
            return new_terms_lines

        existing_terms_lines = self.line_ids.filtered(
            lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
        # remove commission line
        others_lines = existing_terms_lines.filtered(lambda line: not line.is_commission_line)
        # remove discount line
        existing_terms_lines = existing_terms_lines.filtered(lambda line: not line.is_discount_line)
        # remove bank fee line
        existing_terms_lines = existing_terms_lines.filtered(lambda line: not line.is_bank_fee_line)

        others_lines = self.line_ids.filtered(
            lambda line: line.account_id.user_type_id.type not in ('receivable', 'payable'))
        # remove commission line
        others_lines = others_lines.filtered(lambda line: not line.is_commission_line)
        # remove discount line
        others_lines = others_lines.filtered(lambda line: not line.is_discount_line)
        # remove bank fee line
        others_lines = others_lines.filtered(lambda line: not line.is_bank_fee_line)
        company_currency_id = self.company_id.currency_id
        total_balance = sum(others_lines.mapped(lambda l: company_currency_id.round(l.balance)))
        total_amount_currency = sum(others_lines.mapped('amount_currency'))

        if not others_lines:
            self.line_ids -= existing_terms_lines
            return

        computation_date = _get_payment_terms_computation_date(self)
        account = _get_payment_terms_account(self, existing_terms_lines)
        to_compute = _compute_payment_terms(self, computation_date, total_balance, total_amount_currency)
        new_terms_lines = _compute_diff_payment_terms_lines(self, existing_terms_lines, account, to_compute)

        # Remove old terms lines that are no longer needed.
        self.line_ids -= existing_terms_lines - new_terms_lines

        if new_terms_lines:
            self.invoice_payment_ref = new_terms_lines[-1].name or ''
            self.invoice_date_due = new_terms_lines[-1].date_maturity

    def _recompute_dynamic_lines(self, recompute_all_taxes=False, recompute_tax_base_amount=False):
        ''' Recompute all lines that depend of others.

        For example, tax lines depends of base lines (lines having tax_ids set). This is also the case of cash rounding
        lines that depend of base lines or tax lines depending the cash rounding strategy. When a payment term is set,
        this method will auto-balance the move with payment term lines.

        :param recompute_all_taxes: Force the computation of taxes. If set to False, the computation will be done
                                    or not depending of the field 'recompute_tax_line' in lines.
        '''
        for invoice in self:
            # Dispatch lines and pre-compute some aggregated values like taxes.
            for line in invoice.line_ids:
                if line.recompute_tax_line:
                    recompute_all_taxes = True
                    line.recompute_tax_line = False

            # Compute taxes.
            if recompute_all_taxes:
                invoice._recompute_tax_lines()
            if recompute_tax_base_amount:
                invoice._recompute_tax_lines(recompute_tax_base_amount=True)

            if invoice.is_invoice(include_receipts=True):

                # Compute cash rounding.
                invoice._recompute_cash_rounding_lines()

                # compute currency charge
                invoice._recompute_currency_charge_lines()

                # Compute payment terms.
                invoice._recompute_payment_terms_lines()

                # additional line
                # compute commission line
                invoice._recompute_commission_lines()

                # compute discount line
                invoice._recompute_discount_lines()

                # compute bank fee lines
                if invoice.type in ['out_invoice', 'out_refund'] and invoice.partner_id:
                    invoice._recompute_bank_fee_lines()

                # Only synchronize one2many in onchange.
                if invoice != invoice._origin:
                    invoice.invoice_line_ids = invoice.line_ids.filtered(lambda line: not line.exclude_from_invoice_tab)

    def action_post(self):
        res = super(AccountMove, self).action_post()
        existing_terms_lines = self.line_ids.filtered(
            lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
        existing_terms_lines.reconcile()
        return res


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    commission = fields.Float(string='Commission %')
    total = fields.Float(string="Total")
    com_amount = fields.Float(string="Com.Amount")
    is_commission_line = fields.Boolean(string="Is commission Line")
    is_discount_line = fields.Boolean(string="Is Discount Line")
    is_bank_fee_line = fields.Boolean(string="Is Bank Fee Line")
    is_currency_charge_line = fields.Boolean(string="Is Bank Fee Line")

    @api.onchange('commission', 'price_unit', 'quantity', 'price_subtotal')
    def _onchange_commission(self):
        total = self.price_unit * self.quantity
        if self.commission:
            self.com_amount = (total * self.commission) / 100
            self.total = self.price_subtotal - self.com_amount
