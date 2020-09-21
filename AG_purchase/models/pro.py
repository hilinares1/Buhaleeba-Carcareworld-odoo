from odoo import api, fields, models, SUPERUSER_ID, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import except_orm, ValidationError ,UserError

from ast import literal_eval
from datetime import date
from itertools import groupby
from operator import itemgetter
import time

from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.addons.stock.models.stock_move import PROCUREMENT_PRIORITIES


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
    is_customer = fields.Boolean('Is Customer')
    is_vendor = fields.Boolean('Is Vendor')
    is_employee = fields.Boolean('Is Employee',default=True)

    @api.onchange('is_customer')
    def _change_customer(self):
        for rec in self:
            if rec.is_customer == True:
                rec.state = 'confirmed'
                rec.is_vendor = False
                rec.is_employee = False
                rec.is_confirm = False
            else:
                rec.state = 'draft'
    
    @api.onchange('is_vendor')
    def _change_vendor(self):
        for rec in self:
            if rec.is_vendor == True:
                rec.state = 'draft'
                rec.is_customer = False
                rec.is_employee = False
            else:
                rec.state = 'confirmed'

    @api.onchange('is_employee')
    def _change_employee(self):
        for rec in self:
            if rec.is_employee == True:
                rec.state = 'confirmed'
                rec.is_customer = False
                rec.is_vendor = False
            else:
                rec.state = 'draft'

    def action_submit(self):
        self.write({'state':'approve'})

    def action_approve(self):
        self.write({'state':'confirmed','is_confirm':True})

    def set_to_draft(self):
        self.write({'state':'draft','is_confirm':False})
    
    def action_reject(self):
        self.write({'state':'reject'})


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
        'view_type': 'form',
        'view_id': self.env.ref("stock_landed_costs.view_stock_landed_cost_form").id,
        'target': 'new'
    }

    def action_approve(self):
        res = self.button_validate()
        self.write({'is_approve':3})
        # self.env['stock.landed.cost'].create({'picking_ids':[(6,0, [self.id])]})
        # res = self.view_landed_cost()
        return res 

    

    

    def set_to_draft(self):
        self.write({'is_approve':False})
    
    def action_reject(self):
        self.write({'is_approve':2})


    

