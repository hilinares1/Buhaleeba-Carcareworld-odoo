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
    currency_rate = fields.Float('Rate')
    is_update = fields.Integer('Is Updated')
    rfq_name = fields.Char('Rfq Reference', required=True, select=True, copy=False,
                            help="Unique number of the purchase order, "
                                 "computed automatically when the purchase order is created.")
    interchanging_rfq_sequence = fields.Char('Sequence', copy=False)
    interchanging_po_sequence = fields.Char('Sequence', copy=False)
    currency_value = fields.Float('Currency After Rate',compute="_get_curreny_value")

    @api.depends('currency_rate')
    def _get_curreny_value(self):
        for rec in self:
            rec.currency_value = abs(rec.amount_total) * (1/rec.currency_rate)

    @api.model
    def create(self, vals):
        if vals.get('name','New') == 'New':
            name = self.env['ir.sequence'].next_by_code('purchase.order.quot') or 'New'
            vals['rfq_name'] = vals['name'] = name
            
        return super(PurchaseOrder, self).create(vals)

    @api.model
    def _prepare_picking(self):
        if not self.group_id:
            self.group_id = self.group_id.create({
                'name': self.name,
                'partner_id': self.partner_id.id
            })
        if not self.partner_id.property_stock_supplier.id:
            raise UserError(_("You must set a Vendor Location for this partner %s") % self.partner_id.name)
        return {
            'picking_type_id': self.picking_type_id.id,
            'partner_id': self.partner_id.id,
            'user_id': False,
            'date': self.date_order,
            'origin': self.name,
            'currency_rate': self.currency_rate,
            'currency_id': self.currency_id.id,
            'location_dest_id': self._get_destination_location(),
            'location_id': self.partner_id.property_stock_supplier.id,
            'company_id': self.company_id.id,
        }

    @api.onchange('currency_id')
    def _currency_change(self):
        for rec in self:
            rec.currency_rate = rec.currency_id.rate

    def action_view_invoice(self):
        '''
        This function returns an action that display existing vendor bills of given purchase order ids.
        When only one found, show the vendor bill immediately.
        '''
        result = super(PurchaseOrder,self).action_view_invoice()
        result['context']['default_currency_rate'] = self.currency_rate
        result['context']['default_is_purchase'] = 1
        return result

    def button_draft(self):
        res = super(PurchaseOrder, self).button_draft()
        if self.interchanging_rfq_sequence:
            self.write({'interchanging_po_sequence':self.name})
            self.write({'name':self.interchanging_rfq_sequence})
        
        return res

    def button_confirm(self):
        for order in self:
            orderdate = "%s" %(order.date_order)
            # Fixed by sana on 18th November 2020, Fixed issue: TypeError: '<=' not supported between instances of 'datetime.date' and 'bool'
            #  order.company_id.fiscalyear_lock_date value passing False
            if order.company_id.fiscalyear_lock_date:
                if dateutil.parser.parse(orderdate).date() <= order.company_id.fiscalyear_lock_date:
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

            if order.interchanging_rfq_sequence:
                order.write({'name': order.interchanging_po_sequence})
            else:
                new_name = self.env['ir.sequence'].next_by_code('purchase.order') or '/'
                order.write({'interchanging_rfq_sequence':order.name})
                order.write({'name': new_name})
                
            order.picking_ids.write({'origin': order.interchanging_po_sequence})
            if order.picking_ids:
                for pick in order.picking_ids:
                    pick.move_lines.write({'origin': order.interchanging_po_sequence})
            order.update_purchase_pricelist()
        return True

    def button_operation_approve(self):
        self.write({'state': 'to approve', 'date_approve': fields.Datetime.now()})
    
    def update_purchase_pricelist(self):
        for order in self:
            for line in order.order_line:
                pricelist = self.env['product.supplierinfo'].search([('name','=',order.partner_id.id),('product_tmpl_id','=',line.product_id.product_tmpl_id.id)])
                if pricelist:
                    for price in pricelist:
                        price.price = line.price_unit
                        # price.currency_id = order.currency_id.id

class StockMove(models.Model):
    _inherit = "stock.move"

    # pickup_store_details = fields.Text('Pickup store Details')

    def _create_account_move_line(self, credit_account_id, debit_account_id, journal_id, qty, description, svl_id, cost):
        self.ensure_one()
        AccountMove = self.env['account.move'].with_context(default_journal_id=journal_id)

        move_lines = self._prepare_account_move_line(qty, cost, credit_account_id, debit_account_id, description)
        if move_lines:
            if self.picking_id.currency_rate != self.picking_id.currency_id.rate:
                currency_rate = self.picking_id.currency_rate
                is_purchase = 1
            else:
                currency_rate = self.picking_id.currency_id.rate
                is_purchase = 0
            
            date = self._context.get('force_period_date', fields.Date.context_today(self))
            new_account_move = AccountMove.sudo().create({
                'journal_id': journal_id,
                'line_ids': move_lines,
                'date': date,
                'ref': description,
                'stock_move_id': self.id,
                'currency_rate': currency_rate,
                'is_purchase':is_purchase,
                'stock_valuation_layer_ids': [(6, None, [svl_id])],
                'type': 'entry',
            })
            new_account_move.post()


class ResPartner(models.Model):
    _inherit = "res.partner"

    is_confirm = fields.Boolean('Is Confirmed',default=False)
    classification = fields.Selection([
        ('overseas', 'Overseas'),
        ('sister', 'Sister Company'),
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
    sequence_no = fields.Char('Code', required=True, copy=False, readonly=True, index=True, default=lambda self: _('New'),track_visibility="onchange")
    
    # is_customer = fields.Boolean('Is Customer')
    # is_vendor = fields.Boolean('Is Vendor')
    # is_employee = fields.Boolean('Is Employee',default=True)


    @api.onchange('classification')
    def onchange_classification(self):
        for rec in self:
            # raise UserError(self.env.company.sister_company_receivable_account.name)
            if rec.classification == 'sister':
                rec.property_account_receivable_id  = self.env.company.sister_company_receivable_account.id
                rec.property_account_payable_id  = self.env.company.sister_company_payable_account.id

    @api.model_create_multi
    def create(self, vals_list):
        partners = super(ResPartner, self).create(vals_list)
        for user in partners:
            # if partner is global we keep it that way
            # user.partner_id.partner_type = 'employee'
            # if user.sequence_no == 'New':
            user.sequence_no = self.env['ir.sequence'].next_by_code('res.partner.code') or 'New'
        return partners

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
        if self.company_id.fiscalyear_lock_date:
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
        ('land', 'Create Landed cost'),
        ('approve', 'In Approval'),
        ('no', 'No Approval Needed'),
        ('done', 'Done'),
        ('reject', 'Rejected'),
    ], string='Status',compute='_get_status',
        copy=False, index=True, readonly=True, store=True, tracking=True,)
    currency_rate = fields.Float('Currency Rate')
    currency_id = fields.Many2one('res.currency',string="Currency")
    land_count = fields.Float('Land Count',compute="_land_count")
    pickup_store_details = fields.Text('Pickup store Details',compute="_get_store_detail")
    # woo_order_id = fields.Char('Woo-commerce Order ID',compute="_get_store_detail")

    @api.depends('sale_id')
    def _get_store_detail(self):
        for rec in self:
            if rec.sale_id:
                rec.pickup_store_details = rec.sale_id.pickup_store_details
                rec.store_id = rec.sale_id.store_id
                rec.payment_method = rec.sale_id.payment_method
            else:
                rec.pickup_store_details = ""

    def _land_count(self):
        for each in self:
            land = self.env['stock.landed.cost'].search([('picking_ids','in',self.id)])
            if land:
                each.land_count = len(land)
            else:
                each.land_count = 0

    def button_validate(self):
        res = super(StockPicking,self).button_validate()
        # rec = self.env['account.lock.date'].search([('id','=',1)])
        # raise UserError(self.date_order)
        orderdate = "%s" %(self.scheduled_date)
        # Fixed by sana on 18th November 2020, Fixed issue: TypeError: '<=' not supported between instances of 'datetime.date' and 'bool'
        #  order.company_id.fiscalyear_lock_date value passing False
        if self.company_id.fiscalyear_lock_date:
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
                        rec.is_approve = 4
    
    @api.depends('is_approve')
    def _get_status(self):
        for rec in self:
            if rec.picking_type_id.id == 1 and rec.partner_id:
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
                if rec.is_approve == 4:
                    rec.status = 'land'
                
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


    def write(self,vals):
        result = super(StockPicking, self).write(vals)
        for res in self:
            if res.picking_type_id.id == 1 and res.classification == 'overseas':
                # raise UserError(vals.get('state'))
                if res.state == 'done':
                    land = self.env['stock.landed.cost'].search([('picking_ids','in',self.id)])
                    # raise UserError('test')
                    land.button_validate()
            if res.state == 'in_transit':
                if self.sale_id:
                    self.sale_id.create_vendor_bill()
        return result

    def action_approve(self):
        # res = self.button_validate()
        self.write({'is_approve':3})

    def action_approve_land(self):
        # res = self.button_validate()
        self.write({'is_approve':4})
        # self.env['stock.landed.cost'].create({'picking_ids':[(6,0, [self.id])]})
        # res = self.view_landed_cost()
        return {
        #'name': self.order_id,
        'res_model': 'stock.landed.cost',
        'type': 'ir.actions.act_window',
        'context': {'default_picking_ids':[(6,0, [self.id])],'default_flag':1,'default_pick':self.id},
        'view_mode': 'form',
        'view_type': 'form',
        'view_id': self.env.ref("stock_landed_costs.view_stock_landed_cost_form").id,
        'target': 'new'
    }

    def action_landed_cost_tree(self):
        self.ensure_one()
        domain = [
            ('picking_ids','in',self.id)]
        return {
            'name': _('Landed Cost'),
            'domain': domain,
            'res_model': 'stock.landed.cost',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'tree,form',
            'view_type': 'form',
            'help': _('''<p class="oe_view_nocontent_create">
                           Click to Create for New Landed Cost
                        </p>'''),
            'limit': 80,
            'context': {'default_picking_ids':[(6,0, [self.id])],'default_flag':1,'default_pick':self.id},
        }

    def set_to_draft(self):
        self.write({'is_approve':False})
    
    def action_reject(self):
        self.write({'is_approve':2})

class StockLandCost(models.Model):
    _inherit = "stock.landed.cost"

    flag = fields.Integer('Falg',default=0)
    pick = fields.Many2one('stock.picking',string="picking")


    # @api.onchange('name')
    # def _change_name(self):
    #     for rec in self:
    #         if rec.flag == 1:
    #             # raise UserError('dddd')
    #             land = self.env['stock.picking'].search([('id','in',rec.picking_ids.ids)])
    #             land.write({'is_approve':3})

    @api.model
    def create(self, vals):
        res = super(StockLandCost, self).create(vals)
        if res.flag == 1:
            # raise UserError(self.picking_ids)
            land = self.env['stock.picking'].search([('id','=',res.pick.id)])
            # raise UserError(land)
            land.write({'is_approve':1})
        else:
            land = self.env['stock.picking'].search([('id','=',res.pick.id)])
            # raise UserError(land)
            if land:
                land.write({'is_approve':4})
        return res

    # @api.model
    # def create(self, vals):
    #     if vals.get('name', _('New')) == _('New'):
    #         vals['name'] = self.env['ir.sequence'].next_by_code('stock.landed.cost')

    #     if vals.get('flag') == 1:
    #         # raise UserError(self.picking_ids)
    #         land = self.env['stock.picking'].search([('id','=',vals.get('pick'))])
    #         raise UserError(land)
    #         land.write({'is_approve':3})
    #     return super(StockLandCost, self).create(vals)

class AccountMove(models.Model):
    _inherit = "account.move"

    so_link = fields.Many2one('sale.order',string="Sale Order")

class SaleOrder(models.Model):
    _inherit = "sale.order"

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
        ('cancelled', 'Cancelled')
    ], string='Woo-commerce Status', readonly=True, index=True,store=True, copy=False, compute="_get_woo_status", tracking=True)
    inv_count = fields.Float('Count',compute="_land_count")
    vender_flag = fields.Integer('vendor flag',default=0)

   
    def email_after_confirm(self):
        for rec in self:
            # rec.submit_leadd = True
            channel_all_employees = self.env.ref('AG_purchase.channel_all_confirmed_orders').read()[0]
            template_new_employee = self.env.ref('AG_purchase.email_template_data_to_approve_confirmed_orders').read()[0]
            # raise ValidationError(_(template_new_employee))
            if template_new_employee:
                # MailTemplate = self.env['mail.template']
                body_html = template_new_employee['body_html']
                subject = template_new_employee['subject']
                # raise ValidationError(_('%s %s ') % (body_html,subject))
                ids = channel_all_employees['id']
                channel_id = self.env['mail.channel'].search([('id', '=', ids)])
                message = """ Hello Inventory team
                            This order [%s] is confirmed from the sales team 
                            
                            Thanks"""%(rec.name)
                channel_id.message_post(body=message, subject='Confirmed Sale Order',subtype='mail.mt_comment')
            
    def action_confirm(self):
        res = super(SaleOrder,self).action_confirm()
        self.email_after_confirm()
        return res

    def _land_count(self):
        for each in self:
            land = self.env['account.move'].search([('so_link','=',self.id)])
            if land:
                each.inv_count = len(land)
            else:
                each.inv_count = 0

    @api.depends('channel_mapping_ids')
    @api.onchange('state')
    def _get_woo_status(self):
        for rec in self:
            if rec.channel_mapping_ids:
                for map in rec.channel_mapping_ids:
                    res = self.env['order.feed'].search([('store_id','=',map.store_order_id)])
                    if res:
                        rec.woo_status = res.order_state
            else:
                rec.woo_status = 'no'


    def create_vendor_bill(self):
        # for rec in self:
        if self.vender_flag == 0:
            if self.shipping_id:
                invoice = self.env['account.move']
                val = []
                order_line = {
                    'product_id': self.channel_mapping_ids[0].channel_id.delivery_product_id.id,
                    'price_unit':   self.shipping_full,
                    
                }
                val.append((0,0,order_line))
                vals = {
                    'partner_id': self.shipping_id.id,
                    'type':'in_invoice',
                    'so_link':self.id,
                    'invoice_line_ids':val,
                }
                
                invoice.create(vals)
                self.vender_flag = 1
            else:
                raise UserError('No shipping to create for this order')

    def action_invoice_tree(self):
        self.ensure_one()
        domain = [
            ('so_link','=',self.id)]
        return {
            'name': _('Vendor Bill'),
            'domain': domain,
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'tree,form',
            'view_type': 'form',
            'help': _('''<p class="oe_view_nocontent_create">
                           Click to Create vendor bill
                        </p>'''),
            'limit': 80,
            'create':False
            # 'context': {'default_picking_ids':[(6,0, [self.id])],'default_flag':1,'default_pick':self.id},
        }

    def _prepare_invoice(self):
        res = super(SaleOrder, self)._prepare_invoice()
        for rec in self:
            if rec.points_amt:
                if self.channel_mapping_ids:
                    # raise UserError("BOOOOOOOO")
                    res.update({
                        'points_amt':rec.points_amt,
                        'points_product_id':self.channel_mapping_ids[0].channel_id.points_product_id.id,
                        'points_crebit_account_id':self.channel_mapping_ids[0].channel_id.points_crebit_account_id.id,
                        'points_debit_account_id':self.channel_mapping_ids[0].channel_id.points_debit_account_id.id,
                        'channel_id':self.channel_mapping_ids[0].channel_id.id,
                        'store_order_id':self.channel_mapping_ids[0].store_order_id,
                        })
                else:
                    # raise UserError("BLLLLLLLLLLLLLLL")
                    res.update({
                        'points_amt':0})
        return res

    # @api.onchange('picking_ids','state')
    # def _onchange_pick(self):
    #     for rec in self:
    #         if rec.pickup_store_details:
    #             for line in rec.picking_ids:
    #                 line.pickup_store_details  = rec.pickup_store_details
                

class Company(models.Model):
    _inherit = "res.company"

    sister_company_receivable_account = fields.Many2one('account.account', string="Sister Company Receivable Account")
    sister_company_payable_account = fields.Many2one('account.account', string="Sister Company Payable Account")


class KSResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sister_company_receivable_account = fields.Many2one('account.account', string="Sister Company Receivable Account", related='company_id.sister_company_receivable_account', readonly=False)
    sister_company_payable_account = fields.Many2one('account.account', string="Sister Company Payable Account", related='company_id.sister_company_payable_account', readonly=False)
    
class LandedCostLine(models.Model):
    _inherit = 'stock.landed.cost.lines'

    @api.onchange('product_id')
    def onchange_product_id(self):
        res = super(LandedCostLine,self).onchange_product_id()
        if self.product_id:
            if self.product_id.product_tmpl_id.property_account_expense_id.id:
                self.account_id = self.product_id.product_tmpl_id.property_account_expense_id.id
            else:
                raise UserError('Please set the expense account in %s master'%(self.product_id.name))

        return res







