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


    state = fields.Selection([
        ('draft', 'RFQ'),
        ('sent', 'RFQ Sent'),
        ('to approve', 'Operation Manager Approve'),
        ('second approve', 'Purchase Manager Approve'),
        ('purchase', 'Purchase Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled')
    ], string='Status', readonly=True, index=True, copy=False, default='draft', tracking=True)

    # def button_confirm(self):
    #     res = super(PurchaseOrder,self).button_confirm()
    #     # rec = self.env['account.lock.date'].search([('id','=',1)])
    #     # raise UserError(self.date_order)
    #     orderdate = "%s" %(self.date_order)
    #     if dateutil.parser.parse(orderdate).date() <= self.company_id.fiscalyear_lock_date:
    #         lock_date = self.company_id.fiscalyear_lock_date
    #         if self.user_has_groups('account.group_account_manager'):
    #             message = _("You cannot confirm this RFQ prior to and inclusive of the lock date %s.") % format_date(self.env, lock_date)
    #         else:
    #             message = _("You cannot confirm this RFQ prior to and inclusive of the lock date %s. Check the company settings or ask someone with the 'Adviser' role") % format_date(self.env, lock_date)
    #         raise UserError(message)
    #     return res

    def button_confirm(self):
        for order in self:
            orderdate = "%s" %(self.date_order)
            if dateutil.parser.parse(orderdate).date() <= self.company_id.fiscalyear_lock_date:
                lock_date = self.company_id.fiscalyear_lock_date
                if self.user_has_groups('account.group_account_manager'):
                    message = _("You cannot confirm this RFQ prior to and inclusive of the lock date %s.") % format_date(self.env, lock_date)
                else:
                    message = _("You cannot confirm this RFQ prior to and inclusive of the lock date %s. Check the company settings or ask someone with the 'Adviser' role") % format_date(self.env, lock_date)
                raise UserError(message)
            if order.state not in ['draft', 'sent']:
                continue
            order._add_supplier_to_product()
            # Deal with double validation process
            if order.company_id.po_double_validation == 'one_step'\
                    or (order.company_id.po_double_validation == 'two_step'\
                        and order.amount_total < self.env.company.currency_id._convert(
                            order.company_id.po_double_validation_amount, order.currency_id, order.company_id, order.date_order or fields.Date.today()))\
                    or order.user_has_groups('purchase.group_purchase_manager'):
                order.write({'state': 'to approve'})
            else:
                order.write({'state': 'second approve'})
        return True


    # def button_approve(self, force=False):
    #     self.write({'state': 'second approve', 'date_approve': fields.Datetime.now()})
    #     self.filtered(lambda p: p.company_id.po_lock == 'lock').write({'state': 'done'})
    #     return {}

    def button_operation_approve(self):
        self.write({'state': 'to approve', 'date_approve': fields.Datetime.now()})
        # self.button_approve()
        # self.filtered(lambda p: p.company_id.po_lock == 'lock').write({'state': 'done'})
        # return {}
    # def _check_fiscalyear_lock_date(self):
    #     for move in self.filtered(lambda move: move.state == 'posted'):
    #         lock_date = max(move.company_id.period_lock_date or date.min, move.company_id.fiscalyear_lock_date or date.min)
    #         if self.user_has_groups('account.group_account_manager'):
    #             lock_date = move.company_id.fiscalyear_lock_date
    #         if move.date <= (lock_date or date.min):
    #             if self.user_has_groups('account.group_account_manager'):
    #                 message = _("You cannot add/modify entries prior to and inclusive of the lock date %s.") % format_date(self.env, lock_date)
    #             else:
    #                 message = _("You cannot add/modify entries prior to and inclusive of the lock date %s. Check the company settings or ask someone with the 'Adviser' role") % format_date(self.env, lock_date)
    #             raise UserError(message)
    #     return True




class ResPartner(models.Model):
    _inherit = "res.partner"

    is_confirm = fields.Boolean('Is Confirmed',default=False)
    classification = fields.Selection([
        ('overseas', 'Overseas'),
        ('local vendor', 'Local Vendor')], string='Vendor Classification', default='local vendor', copy=False)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approve', 'In Approval'),
        ('confirmed', 'Confirmed'),
        ('reject', 'Reject')], string='Status', default='draft', copy=False)
    partner_type = fields.Selection([
        ('customer', 'Customer'),
        ('vendor', 'Vendor'),
        ('employee', 'Employee')], string='Partner Type',default='customer', copy=False)
    # is_customer = fields.Boolean('Is Customer')
    # is_vendor = fields.Boolean('Is Vendor')
    # is_employee = fields.Boolean('Is Employee',default=True)

    @api.onchange('partner_type')
    def _change_customer(self):
        for rec in self:
            if rec.partner_type == 'customer' :
                rec.state = 'confirmed'
                rec.is_confirm = False
            elif rec.partner_type == 'vendor':
                rec.state = 'draft'
            else:
                rec.state = 'confirmed'
    
    # @api.onchange('is_vendor')
    # def _change_vendor(self):
    #     for rec in self:
    #         if rec.is_vendor == True:
    #             rec.state = 'draft'
    #             rec.is_customer = False
    #             rec.is_employee = False
    #         else:
    #             rec.state = 'confirmed'

    # @api.onchange('is_employee')
    # def _change_employee(self):
    #     for rec in self:
    #         if rec.is_employee == True:
    #             rec.state = 'confirmed'
    #             rec.is_customer = False
    #             rec.is_vendor = False
    #         else:
    #             rec.state = 'draft'

    def action_submit(self):
        self.write({'state':'approve'})

    def action_approve(self):
        self.write({'state':'confirmed','is_confirm':True})

    def set_to_draft(self):
        self.write({'state':'draft','is_confirm':False})
    
    def action_reject(self):
        self.write({'state':'reject'})


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model_create_multi
    def create(self, vals_list):
        users = super(ResUsers, self).create(vals_list)
        for user in users:
            # if partner is global we keep it that way
            user.partner_id.partner_type = 'employee'
        return users

class StockInventory(models.Model):
    _inherit = "stock.inventory"

    def action_validate(self):
        res = super(StockInventory,self).action_validate()
        # rec = self.env['account.lock.date'].search([('id','=',1)])
        # raise UserError(self.date_order)
        orderdate = "%s" %(self.date)
        if dateutil.parser.parse(orderdate).date() <= self.company_id.fiscalyear_lock_date:
            lock_date = self.company_id.fiscalyear_lock_date
            if self.user_has_groups('account.group_account_manager'):
                message = _("You cannot Validate this Inventory Adjustment prior to and inclusive of the lock date %s.") % format_date(self.env, lock_date)
            else:
                message = _("You cannot Validate this Inventory Adjustment prior to and inclusive of the lock date %s. Check the company settings or ask someone with the 'Adviser' role") % format_date(self.env, lock_date)
            raise UserError(message)
        return res

class StockPicking(models.Model):
    _inherit = "stock.picking"

    classification = fields.Selection(related="partner_id.classification",store=True,string='Classification', copy=False)
    is_approve = fields.Integer('Is approve',compute='_is_approve',store=True)
    status = fields.Selection([
        ('approve', 'In Approval'),
        ('no', 'No Approval Needed'),
        ('done', 'Done'),
        ('reject', 'Rejected'),
    ], string='Status',compute='_get_status',
        copy=False, index=True, readonly=True, store=True, tracking=True,)


    def button_validate(self):
        res = super(StockPicking,self).button_validate()
        # rec = self.env['account.lock.date'].search([('id','=',1)])
        # raise UserError(self.date_order)
        orderdate = "%s" %(self.scheduled_date)
        if dateutil.parser.parse(orderdate).date() <= self.company_id.fiscalyear_lock_date:
            lock_date = self.company_id.fiscalyear_lock_date
            if self.user_has_groups('account.group_account_manager'):
                message = _("You cannot Validate this picking prior to and inclusive of the lock date %s.") % format_date(self.env, lock_date)
            else:
                message = _("You cannot Validate this picking prior to and inclusive of the lock date %s. Check the company settings or ask someone with the 'Adviser' role") % format_date(self.env, lock_date)
            raise UserError(message)
        return res

    @api.depends('classification')
    def _is_approve(self):
        for rec in self:
            if rec.picking_type_id.id == 1:
                if not rec.is_approve:
                    if rec.classification == 'local vendor':
                        rec.is_approve = 0
                    else:
                        rec.is_approve = 1
    
    @api.depends('is_approve')
    def _get_status(self):
        for rec in self:
            if rec.picking_type_id.id == 1:
                if rec.state == 'cancel':
                    rec.status = 'no'
                    rec.is_approve = False
                if rec.is_approve == 1:
                    rec.status = 'approve'
                if rec.is_approve == 0:
                    rec.status = 'no'
                if rec.is_approve == 2:
                    rec.status = 'reject'
                if rec.is_approve == 3:
                    rec.status = 'done'
                
            else:
                rec.status = 'no'


    def view_landed_cost(self):
        return {
        #'name': self.order_id,
        'res_model': 'stock.landed.cost',
        'type': 'ir.actions.act_window',
        'context': {},
        'view_mode': 'form',
        # 'view_type': 'form',
        'view_id':False, 
        # self.env.ref("stock_landed_costs.view_stock_landed_cost_form").id,
        'target': 'new'
    }

    # @api.onchange('state','is_approve')
    # def _change_state(self,vals):
    #     if self.picking_type_id.id == 1:
    #         if vals.get('state') == 'done':
    #            res = self.action_approve()
    #            return res


    # def write(self,vals):
    #     super(StockPicking, self).write(vals)
    #     if self.picking_type_id.id == 1:
    #         if self.state == 'done':
    #            self.view_landed_cost()
        # return temp

    def action_approve(self):
        # res = self.button_validate()
        self.write({'is_approve':3})
        # self.env['stock.landed.cost'].create({'picking_ids':[(6,0, [self.id])]})
        # res = self.view_landed_cost()
        return {
        #'name': self.order_id,
        'res_model': 'stock.landed.cost',
        'type': 'ir.actions.act_window',
        'context': {'default_picking_ids':[(6,0, [self.id])]},
        'view_mode': 'form',
        'view_type': 'form',
        'view_id': self.env.ref("stock_landed_costs.view_stock_landed_cost_form").id,
        'target': 'new'
    }
    #     return {
    #     #'name': self.order_id,
    #     'res_model': 'landed.cost.generator',
    #     'type': 'ir.actions.act_window',
    #     'context': dict(self._context, active_ids=self.ids),
    #     'view_mode': 'form',
    #     'view_type': 'form',
    #     'view_id': self.env.ref("AG_purchase.Land_cost_generator_view_form").id,
    #     'target': 'new',
    #     # 'res_id': self.id,
    # } 

    

    

    def set_to_draft(self):
        self.write({'is_approve':False})
    
    def action_reject(self):
        self.write({'is_approve':2})

class StockLandCost(models.Model):
    _inherit = "stock.landed.cost"


    def button_validate(self):
        if any(cost.state != 'draft' for cost in self):
            raise UserError(_('Only draft landed costs can be validated'))
        if not all(cost.picking_ids for cost in self):
            raise UserError(_('Please define the transfers on which those additional costs should apply.'))
        cost_without_adjusment_lines = self.filtered(lambda c: not c.valuation_adjustment_lines)
        if cost_without_adjusment_lines:
            cost_without_adjusment_lines.compute_landed_cost()
        if not self._check_sum():
            raise UserError(_('Cost and adjustments lines do not match. You should maybe recompute the landed costs.'))

        for cost in self:
            for pick in cost.picking_ids:
                pick.button_validate()
            move = self.env['account.move']
            move_vals = {
                'journal_id': cost.account_journal_id.id,
                'date': cost.date,
                'ref': cost.name,
                'line_ids': [],
                'type': 'entry',
            }
            valuation_layer_ids = []
            for line in cost.valuation_adjustment_lines.filtered(lambda line: line.move_id):
                remaining_qty = sum(line.move_id.stock_valuation_layer_ids.mapped('remaining_qty'))
                linked_layer = line.move_id.stock_valuation_layer_ids[:1]

                # Prorate the value at what's still in stock
                cost_to_add = (remaining_qty / line.move_id.product_qty) * line.additional_landed_cost
                if not cost.company_id.currency_id.is_zero(cost_to_add):
                    valuation_layer = self.env['stock.valuation.layer'].create({
                        'value': cost_to_add,
                        'unit_cost': 0,
                        'quantity': 0,
                        'remaining_qty': 0,
                        'stock_valuation_layer_id': linked_layer.id,
                        'description': cost.name,
                        'stock_move_id': line.move_id.id,
                        'product_id': line.move_id.product_id.id,
                        'stock_landed_cost_id': cost.id,
                        'company_id': cost.company_id.id,
                    })
                    linked_layer.remaining_value += cost_to_add
                    valuation_layer_ids.append(valuation_layer.id)
                # Update the AVCO
                product = line.move_id.product_id
                if product.cost_method == 'average' and not float_is_zero(product.quantity_svl, precision_rounding=product.uom_id.rounding):
                    product.with_context(force_company=self.company_id.id).sudo().standard_price += cost_to_add / product.quantity_svl
                # `remaining_qty` is negative if the move is out and delivered proudcts that were not
                # in stock.
                qty_out = 0
                if line.move_id._is_in():
                    qty_out = line.move_id.product_qty - remaining_qty
                elif line.move_id._is_out():
                    qty_out = line.move_id.product_qty
                move_vals['line_ids'] += line._create_accounting_entries(move, qty_out)

            move_vals['stock_valuation_layer_ids'] = [(6, None, valuation_layer_ids)]
            move = move.create(move_vals)
            cost.write({'state': 'done', 'account_move_id': move.id})
            move.post()

            if cost.vendor_bill_id and cost.vendor_bill_id.state == 'posted' and cost.company_id.anglo_saxon_accounting:
                all_amls = cost.vendor_bill_id.line_ids | cost.account_move_id.line_ids
                for product in cost.cost_lines.product_id:
                    accounts = product.product_tmpl_id.get_product_accounts()
                    input_account = accounts['stock_input']
                    all_amls.filtered(lambda aml: aml.account_id == input_account and not aml.full_reconcile_id).reconcile()
        return True
    

