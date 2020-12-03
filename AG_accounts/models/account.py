# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2019-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Faslu Rahman(odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################

from odoo import api, fields, models, tools, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
import odoo.addons.decimal_precision as dp
from odoo.tools import float_is_zero, float_compare, safe_eval, date_utils, email_split, email_escape_char, email_re
from odoo.tools.misc import formatLang, format_date, get_lang

from datetime import date, timedelta
from itertools import groupby
from itertools import zip_longest
from hashlib import sha256
from json import dumps

import json
import re


class AccountMove(models.Model):
    _inherit = "account.move"


    @api.model
    def _get_default_invoice_date(self):
        return fields.Date.today() if self._context.get('default_type', 'entry') in ('in_invoice', 'in_refund', 'in_receipt') else False

    @api.model
    def _get_default_currency(self):
        ''' Get the default currency from either the journal, either the default journal's company. '''
        journal = self._get_default_journal()
        return journal.currency_id or journal.company_id.currency_id

    @api.model
    def _get_default_journal(self):
        ''' Get the default journal.
        It could either be passed through the context using the 'default_journal_id' key containing its id,
        either be determined by the default type.
        '''
        move_type = self._context.get('default_type', 'entry')
        journal_type = 'general'
        if move_type in self.get_sale_types(include_receipts=True):
            journal_type = 'sale'
        elif move_type in self.get_purchase_types(include_receipts=True):
            journal_type = 'purchase'

        if self._context.get('default_journal_id'):
            journal = self.env['account.journal'].browse(self._context['default_journal_id'])

            if move_type != 'entry' and journal.type != journal_type:
                raise UserError(_("Cannot create an invoice of type %s with a journal having %s as type.") % (move_type, journal.type))
        else:
            company_id = self._context.get('force_company', self._context.get('default_company_id', self.env.company.id))
            domain = [('company_id', '=', company_id), ('type', '=', journal_type)]

            journal = None
            if self._context.get('default_currency_id'):
                currency_domain = domain + [('currency_id', '=', self._context['default_currency_id'])]
                journal = self.env['account.journal'].search(currency_domain, limit=1)

            if not journal:
                journal = self.env['account.journal'].search(domain, limit=1)

            if not journal:
                error_msg = _('Please define an accounting miscellaneous journal in your company')
                if journal_type == 'sale':
                    error_msg = _('Please define an accounting sale journal in your company')
                elif journal_type == 'purchase':
                    error_msg = _('Please define an accounting purchase journal in your company')
                raise UserError(error_msg)
        return journal


    currency_rate = fields.Float('Rate')
    is_update = fields.Integer('Is Updated')
    is_confirm = fields.Integer('Is Confirmed',default=0)
    state = fields.Selection(selection=[
            ('confirm', 'In confirm'),
            ('approve', 'Approval'),
            ('secapprove', 'Second Approval'),
            ('draft', 'Draft'),
            ('posted', 'Posted'),
            ('cancel', 'Cancelled')
        ], string='Status', required=True, readonly=True, copy=False, tracking=True,
        default='confirm')
    partner_id = fields.Many2one('res.partner', readonly=True, tracking=True,
        states={'draft': [('readonly', False)],'confirm': [('readonly', False)]},
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        string='Partner', change_default=True)
    invoice_date = fields.Date(string='Invoice/Bill Date', readonly=True, index=True, copy=False,
        states={'draft': [('readonly', False)],'confirm': [('readonly', False)]},
        default=_get_default_invoice_date)
    invoice_payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms',
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        readonly=True, states={'draft': [('readonly', False)],'confirm': [('readonly', False)]})
    invoice_date_due = fields.Date(string='Due Date', readonly=True, index=True, copy=False,
        states={'draft': [('readonly', False)],'confirm': [('readonly', False)]})
    currency_id = fields.Many2one('res.currency', store=True, readonly=True, tracking=True, required=True,
        states={'draft': [('readonly', False)],'confirm': [('readonly', False)]},
        string='Currency',
        default=_get_default_currency)
    journal_id = fields.Many2one('account.journal', string='Journal', required=True, readonly=True,
        states={'draft': [('readonly', False)],'confirm': [('readonly', False)]},
        domain="[('company_id', '=', company_id)]",
        default=_get_default_journal)
    invoice_line_ids = fields.One2many('account.move.line', 'move_id', string='Invoice lines',
        copy=False, readonly=True,
        domain=[('exclude_from_invoice_tab', '=', False)],
        states={'draft': [('readonly', False)],'approve': [('readonly', False)],'confirm': [('readonly', False)]})
    line_ids = fields.One2many('account.move.line', 'move_id', string='Journal Items', copy=True, readonly=True,
        states={'draft': [('readonly', False)],'approve': [('readonly', False)],'confirm': [('readonly', False)]})
    is_purchase = fields.Integer('Purchase',default=0)
    points_amt = fields.Float('Points')
    points_product_id = fields.Many2one('product.product',string='Points Product')
    points_crebit_account_id = fields.Many2one('account.account',string='Points Credit Account')
    points_debit_account_id = fields.Many2one('account.account',string='Points Debit Account')
    res_model = fields.Char('Related Document Model')
    res_id = fields.Integer('Related Document ID')
    share_link = fields.Char(string="Link", compute='_compute_share_link')
    channel_id = fields.Many2one('multi.channel.sale',string="channel")
    store_order_id = fields.Char('Order_id')


    def export_update_woocommerce_brand(self):
        if self.channel_id:
            connect = self.env['multi.channel.sale'].search([('id','=',self.channel_id.id)])
            category_update = self.env['channel.order.mappings'].search([('store_order_id','=',self.store_order_id),('channel_id.id','=',self.channel_id.id)])
            for category_map in category_update:
                # category = category_map.category_name
                # count += 1
                    # if category.parent_id:
                    # 	parent_category = self.env['channel.type.mappings'].search([('odoo_type_id','=',category.parent_id.id),('channel_id.id','=',self.id)])
                    # 	if not parent_category:
                    # 		self.export_woocommerce_types(0)
                    # 		parent_category = self.env['channel.type.mappings'].search([('odoo_type_id','=',category.parent_id.id),('channel_id.id','=',self.id)])
                    # 		store_type_id = parent_category.store_type_id
                category_dict = {
                        'transaction_id' 		: self.share_link,
                        # 'description' 		: category.description,
                        # 'parent_id'	: store_brand_id,
                    }
                woocommerce = connect.get_woocommerce_connection()
                return_dict = woocommerce.put('orders/'+self.store_order_id,category_dict).json()
                if 'message' in return_dict:
                    raise UserError(_('Error in Updating Brands : '+str(return_dict['message'])))
                    # category_map.need_sync = 'no'
            return connect.display_message(" Brands Updated  ")

    # @api.model
    # def default_get(self, fields):
    #     result = super(AccountMove, self).default_get(fields)
    #     result['res_model'] = self._context.get('active_model', False)
    #     result['res_id'] = self._context.get('active_id', False)
    #     if result['res_model'] and result['res_id']:
    #         record = self.env[result['res_model']].browse(result['res_id'])
    #         result['share_link'] = record.get_base_url() + record._get_share_url(redirect=True)
    #     return result

    @api.depends('res_model', 'res_id')
    def _compute_share_link(self):
        for rec in self:
            rec.share_link = False
            rec.res_model = 'account.move'
            rec.res_id = self.id
            if rec.res_model:
                res_model = self.env[rec.res_model]
                if isinstance(res_model, self.pool['portal.mixin']) and rec.res_id:
                    record = res_model.browse(rec.res_id)
                    # raise UserError(record._get_share_url(redirect=True))
                    rec.share_link = record.get_base_url() + record._get_share_url(redirect=True) + '&report_type=pdf&download=true'
                    rec.share_link = rec.share_link.replace('mail/view', 'my/invoices/%s'%(rec.res_id))
                    # raise UserError(rec.share_link)

    def action_post(self):
        res = super(AccountMove, self).action_post()
        if self.points_amt:
            dict = []
            dict1 = {
                    # 'move_name': self.name,
                    'name': "Earned Point",
                    'price_unit': self.points_amt,
                    'product_id': self.points_product_id.id,
                    'quantity': 1,
                    'debit':0.0,
                    'credit': self.points_amt,
                    'account_id': self.points_crebit_account_id.id,
                    # 'move_id': self._origin,
                    # 'date': self.date,
                    'exclude_from_invoice_tab': True,
                    # 'partner_id': terms_lines.partner_id.id,
                    'company_id': self.company_id.id,
                    # 'company_currency_id': terms_lines.company_currency_id.id,
                    }
            dict.append((0,0,dict1))
            dict2 = {
                    # 'move_name': self.name,
                    'name': "Earned Point",
                    'price_unit': self.points_amt,
                    'product_id': self.points_product_id.id,
                    'quantity': 1,
                    'debit': self.points_amt,
                    'credit': 0.0,
                    'account_id': self.points_debit_account_id.id,
                    # 'move_id': self._origin,
                    # 'date': self.date,
                    'exclude_from_invoice_tab': True,
                    # 'partner_id': terms_lines.partner_id.id,
                    'company_id': self.company_id.id,
                    'company_currency_id': self.company_currency_id.id,
                    }
            dict.append((0,0,dict2))
            self.update({'line_ids':dict})
        return res

    @api.model_create_multi
    def create(self, vals_list):
        reses = super(AccountMove,self).create(vals_list)
        for res in reses:
            if res.type == 'out_refund' or res.type == 'entry':
                res.state = 'confirm'
                res.is_confirm = 1
            else:
                res.state = 'draft'
            if res.is_purchase != 0:
                res._currency_change()
            else:
                res.currency_rate = res.currency_id.rate
        return reses

    def send_to_approve(self):
        for rec in self:
            rec.write({'state':'approve'})

    def action_approve(self):
        for rec in self:
            rec.action_post()
            # rec.write({'state':'draft'})
    
    # def action_second_approve(self):
    #     for rec in self:
    #         rec.write({'state':'draft'})

    @api.onchange('currency_id')
    def _currency_change(self):
        for rec in self:
            if rec.is_purchase == 0:
                rec.currency_rate = rec.currency_id.rate

    # @api.onchange('invoice_line_ids')
    def currency_changes(self):
        value = {}
        vals = []
        for rec in self:
            if rec.line_ids:
                for res in rec.line_ids:
                    #Fixed by sana on 18th November 2020, Fixed issue: when create vendor bill from purchase order while save price set ZERO
                    #  and all amount makes ZERO
                    if res.company_id.currency_id != res.move_id.currency_id:
                        amount_currency = abs(res.amount_currency) * (1 / rec.currency_rate)
                        amount_currency = tools.float_round(amount_currency, precision_digits=2)
                        if res.debit == 0 and res.credit != 0:
                            credit = amount_currency
                            # credit = tools.float_round(float(amount_currency), precision_digits=2)
                            value = {'debit': 0, 'credit': round(credit,2), 'account_id': res.account_id.id}
                        elif res.debit != 0 and res.credit == 0:
                            debit = amount_currency
                            value = {'debit': debit, 'credit': 0, 'account_id': res.account_id.id}
                        print ("valsss",value)
                        vals.append((1, res.id, value))
            if vals:
                rec.update({'line_ids': vals})
                rec.is_update = rec.is_update + 1
                # rec.write({'debit':debit,'credit':credit})
            else:
                raise UserError('The jornal lines is empty nothing to update')

# Commented by SANA 19 November to solve multiple issue related to Stock Accounting entry not generated.
    # def post(self):
    #     # `user_has_group` won't be bypassed by `sudo()` since it doesn't change the user anymore.
    #     if not self.env.su and not self.env.user.has_group('account.group_account_invoice'):
    #         raise AccessError(_("You don't have the access rights to post an invoice."))
    #     for move in self:
    #         if not move.line_ids.filtered(lambda line: not line.display_type):
    #             raise UserError(_('You need to add a line before posting.'))
    #         if move.auto_post and move.date > fields.Date.today():
    #             date_msg = move.date.strftime(get_lang(self.env).date_format)
    #             raise UserError(_("This move is configured to be auto-posted on %s" % date_msg))
    #
    #         if not move.partner_id:
    #             if move.is_sale_document():
    #                 raise UserError(_("The field 'Customer' is required, please complete it to validate the Customer Invoice."))
    #             elif move.is_purchase_document():
    #                 raise UserError(_("The field 'Vendor' is required, please complete it to validate the Vendor Bill."))
    #
    #         if move.is_invoice(include_receipts=True) and float_compare(move.amount_total, 0.0, precision_rounding=move.currency_id.rounding) < 0:
    #             raise UserError(_("You cannot validate an invoice with a negative total amount. You should create a credit note instead. Use the action menu to transform it into a credit note or refund."))
    #
    #         # Handle case when the invoice_date is not set. In that case, the invoice_date is set at today and then,
    #         # lines are recomputed accordingly.
    #         # /!\ 'check_move_validity' must be there since the dynamic lines will be recomputed outside the 'onchange'
    #         # environment.
    #         if move.is_update == 0:
    #             if not move.invoice_date and move.is_invoice(include_receipts=True):
    #                 move.invoice_date = fields.Date.context_today(self)
    #                 move.with_context(check_move_validity=False)._onchange_invoice_date()
    #
    #
    #         # When the accounting date is prior to the tax lock date, move it automatically to the next available date.
    #         # /!\ 'check_move_validity' must be there since the dynamic lines will be recomputed outside the 'onchange'
    #         # environment.
    #         # if (move.company_id.tax_lock_date and move.date <= move.company_id.tax_lock_date) and (move.line_ids.tax_ids or move.line_ids.tag_ids):
    #         #     move.date = move.company_id.tax_lock_date + timedelta(days=1)
    #         #     move.with_context(check_move_validity=False)._onchange_currency()
    #
    #     # Create the analytic lines in batch is faster as it leads to less cache invalidation.
    #     self.mapped('line_ids').create_analytic_lines()
    #     for move in self:
    #         if move.auto_post and move.date > fields.Date.today():
    #             raise UserError(_("This move is configured to be auto-posted on {}".format(move.date.strftime(get_lang(self.env).date_format))))
    #
    #         move.message_subscribe([p.id for p in [move.partner_id] if p not in move.sudo().message_partner_ids])
    #
    #         to_write = {'state': 'posted'}
    #
    #         if move.name == '/':
    #             # Get the journal's sequence.
    #             sequence = move._get_sequence()
    #             if not sequence:
    #                 raise UserError(_('Please define a sequence on your journal.'))
    #
    #             # Consume a new number.
    #             to_write['name'] = sequence.with_context(ir_sequence_date=move.date).next_by_id()
    #
    #         move.write(to_write)
    #
    #         # Compute 'ref' for 'out_invoice'.
    #         if move.type == 'out_invoice' and not move.invoice_payment_ref:
    #             to_write = {
    #                 'invoice_payment_ref': move._get_invoice_computed_reference(),
    #                 'line_ids': []
    #             }
    #             for line in move.line_ids.filtered(lambda line: line.account_id.user_type_id.type in ('receivable', 'payable')):
    #                 to_write['line_ids'].append((1, line.id, {'name': to_write['invoice_payment_ref']}))
    #             move.write(to_write)
    #
    #         if move == move.company_id.account_opening_move_id and not move.company_id.account_bank_reconciliation_start:
    #             # For opening moves, we set the reconciliation date threshold
    #             # to the move's date if it wasn't already set (we don't want
    #             # to have to reconcile all the older payments -made before
    #             # installing Accounting- with bank statements)
    #             move.company_id.account_bank_reconciliation_start = move.date
    #
    #     for move in self:
    #         if not move.partner_id: continue
    #         if move.type.startswith('out_'):
    #             move.partner_id._increase_rank('customer_rank')
    #         elif move.type.startswith('in_'):
    #             move.partner_id._increase_rank('supplier_rank')
    #         else:
    #             continue
    #
    #     # Trigger action for paid invoices in amount is zero
    #     self.filtered(
    #         lambda m: m.is_invoice(include_receipts=True) and m.currency_id.is_zero(m.amount_total)
    #     ).action_invoice_paid()
    #
    #     # Force balance check since nothing prevents another module to create an incorrect entry.
    #     # This is performed at the very end to avoid flushing fields before the whole processing.
    #     self._check_balanced()
    #     return True

        #     if not move.partner_id:
        #         if move.is_sale_document():
        #             raise UserError(_("The field 'Customer' is required, please complete it to validate the Customer Invoice."))
        #         elif move.is_purchase_document():
        #             raise UserError(_("The field 'Vendor' is required, please complete it to validate the Vendor Bill."))
        #
        #     if move.is_invoice(include_receipts=True) and float_compare(move.amount_total, 0.0, precision_rounding=move.currency_id.rounding) < 0:
        #         raise UserError(_("You cannot validate an invoice with a negative total amount. You should create a credit note instead. Use the action menu to transform it into a credit note or refund."))
        #
        #     # Handle case when the invoice_date is not set. In that case, the invoice_date is set at today and then,
        #     # lines are recomputed accordingly.
        #     # /!\ 'check_move_validity' must be there since the dynamic lines will be recomputed outside the 'onchange'
        #     # environment.
        #     if move.is_update == 0:
        #         if not move.invoice_date and move.is_invoice(include_receipts=True):
        #             move.invoice_date = fields.Date.context_today(self)
        #             move.with_context(check_move_validity=False)._onchange_invoice_date()
        #
        #
        #     # When the accounting date is prior to the tax lock date, move it automatically to the next available date.
        #     # /!\ 'check_move_validity' must be there since the dynamic lines will be recomputed outside the 'onchange'
        #     # environment.
        #     # if (move.company_id.tax_lock_date and move.date <= move.company_id.tax_lock_date) and (move.line_ids.tax_ids or move.line_ids.tag_ids):
        #     #     move.date = move.company_id.tax_lock_date + timedelta(days=1)
        #     #     move.with_context(check_move_validity=False)._onchange_currency()
        #
        # # Create the analytic lines in batch is faster as it leads to less cache invalidation.
        # self.mapped('line_ids').create_analytic_lines()
        # for move in self:
        #     if move.auto_post and move.date > fields.Date.today():
        #         raise UserError(_("This move is configured to be auto-posted on {}".format(move.date.strftime(get_lang(self.env).date_format))))
        #
        #     move.message_subscribe([p.id for p in [move.partner_id] if p not in move.sudo().message_partner_ids])
        #
        #     to_write = {'state': 'posted'}
        #
        #     if move.name == '/':
        #         # Get the journal's sequence.
        #         sequence = move._get_sequence()
        #         if not sequence:
        #             raise UserError(_('Please define a sequence on your journal.'))
        #
        #         # Consume a new number.
        #         to_write['name'] = sequence.with_context(ir_sequence_date=move.date).next_by_id()
        #
        #     move.write(to_write)
        #
        #     # Compute 'ref' for 'out_invoice'.
        #     if move.type == 'out_invoice' and not move.invoice_payment_ref:
        #         to_write = {
        #             'invoice_payment_ref': move._get_invoice_computed_reference(),
        #             'line_ids': []
        #         }
        #         for line in move.line_ids.filtered(lambda line: line.account_id.user_type_id.type in ('receivable', 'payable')):
        #             to_write['line_ids'].append((1, line.id, {'name': to_write['invoice_payment_ref']}))
        #         move.write(to_write)
        #
        #     if move == move.company_id.account_opening_move_id and not move.company_id.account_bank_reconciliation_start:
        #         # For opening moves, we set the reconciliation date threshold
        #         # to the move's date if it wasn't already set (we don't want
        #         # to have to reconcile all the older payments -made before
        #         # installing Accounting- with bank statements)
        #         move.company_id.account_bank_reconciliation_start = move.date
        #
        # for move in self:
        #     if not move.partner_id: continue
        #     if move.type.startswith('out_'):
        #         move.partner_id._increase_rank('customer_rank')
        #     elif move.type.startswith('in_'):
        #         move.partner_id._increase_rank('supplier_rank')
        #     else:
        #         raise UserError('The jornal lines is empty nothing to update')
        #
        # # Trigger action for paid invoices in amount is zero
        # self.filtered(
        #     lambda m: m.is_invoice(include_receipts=True) and m.currency_id.is_zero(m.amount_total)
        # ).action_invoice_paid()
        #
        # # Force balance check since nothing prevents another module to create an incorrect entry.
        # # This is performed at the very end to avoid flushing fields before the whole processing.
        # self._check_balanced()
        # return True

#Commented by SANA 19 November to solve multiple issue related to Stock Accounting entry not generated,
# Conflicted with Tax calculation on Customer Invoice, Discount gives issue to
# class AccountMoveLine(models.Model):
#     _inherit = "account.move.line"
#
#
#     price_tax = fields.Float('Vat Amount',compute="get_price_tax")
#
#     @api.onchange('quantity','discount','discount_value','is_percentage','price_unit','tax_ids')
#     def get_price_tax(self):
#         for rec in self:
#             # raise UserError(rec.price_unit)
#             if rec.discount :
#                 if rec.is_percentage == True:
#                     price_unit_wo_discount = rec.price_unit * (1 - (rec.discount or 0.0) / 100.0)
#                 else:
#                     price_unit_wo_discount = rec.price_unit  - rec.discount/rec.quantity
#             elif rec.discount_value:
#                 price_unit_wo_discount = rec.price_unit  - rec.discount_value/rec.quantity
#             else:
#                 price_unit_wo_discount = rec.price_unit
#             taxes = rec.tax_ids.compute_all(price_unit_wo_discount, rec.move_id.currency_id, rec.quantity, product=rec.product_id, partner=rec.move_id.partner_shipping_id)
#             rec.price_tax = sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))


class AccountAsset(models.Model):
    _inherit = "account.asset.asset"

    asset_code = fields.Char(string='Sequence',readonly=True)
    # custom_description = fields.Text(string='Description',)
    custom_record_brand = fields.Char(string='Record Brand',)
    custom_model_number = fields.Char(string='Model Number',)
    custom_serial_number = fields.Char(string='Serial Number',)
    custom_manufacturer_id = fields.Many2one('res.partner', string='Manufacturer',)
    # custom_purchase_id = fields.Many2one('purchase.order',string='Purchase order',)
    custom_receive_date = fields.Date(string='Received Date',)
    custom_warranty_information = fields.Char(string='Warranty Information',)
    custom_warranty_expire_date = fields.Date(string='Warranty Date',)
    custom_warranty_service_provider = fields.Many2one('res.partner',string='Warranty Service Provider',)

    custom_source_department_id = fields.Many2one('hr.department', string="Source Location")
    custom_source_partner_id = fields.Many2one('res.partner',string="Source Custodian")


    @api.model
    def create(self, vals):
        res = super(AccountAsset, self).create(vals)
        number = self.env['ir.sequence'].next_by_code('account.seq')
        res.asset_code = number
        return res
