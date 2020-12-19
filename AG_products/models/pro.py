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

from odoo import api, fields, models , _
import odoo.addons.decimal_precision as dp
from datetime import date

from odoo.exceptions import except_orm, ValidationError ,UserError

from ast import literal_eval
from itertools import groupby
from operator import itemgetter
import time
import dateutil.parser

from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.addons.stock.models.stock_move import PROCUREMENT_PRIORITIES
from odoo.tools.misc import formatLang, format_date, get_lang


class ProductTemplate(models.Model):
    _inherit = "product.template"

    internal_ref = fields.Char('Second Internal Reference')
    is_confirm = fields.Boolean('Is Confirmed',default=False)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approve', 'In Approval'),
        ('confirmed', 'Confirmed'),
        ('reject', 'Reject')], string='Status', default='draft', copy=False)

    pr_category = fields.Many2one('product.categories',string="Product Category",domain=[('parent_id','=',False)])
    sub_pr_category = fields.Many2one('product.categories',string="Sub-Category",domain=[('parent_id','!=',False)])
    pr_type = fields.Many2one('product.type',string="Product Type",domain=[('parent_id','=',False)])
    sub_pr_type = fields.Many2one('product.type',string="Sub-Type",domain=[('parent_id','!=',False)])
    pr_brand = fields.Many2one('product.brand',string="Product Brand")
    is_manager = fields.Integer('manger',compute="_get_is_manager")

    @api.depends('state')
    def _get_is_manager(self):
        for rec in self:
            if self.env.user.has_group("AG_purchase.group_purchase_operation_manager"):
                rec.is_manager = 1
            else:
                rec.is_manager = 0
    

    def action_submit(self):
        self.write({'state':'approve'})

    def action_approve(self):
        self.write({'state':'confirmed','is_confirm':True})

    def set_to_draft(self):
        self.write({'state':'draft','is_confirm':False})
    
    def action_reject(self):
        self.write({'state':'reject'})


    @api.model_create_multi
    def create(self, vals_list):
        ''' Store the initial standard price in order to be able to retrieve the cost of a product template for a given date'''
        templates = super(ProductTemplate, self).create(vals_list)

        for template, vals in zip(templates, vals_list):
            related_vals = {}
            # if vals.get('default_code','') == '':
            name = self.env['ir.sequence'].next_by_code('product.template.code') or ' '
            vals['internal_ref'] =  name
            related_vals['internal_ref'] = vals['internal_ref']
            if related_vals:
                template.write(related_vals)
            

        return templates

class ProductProduct(models.Model):
    _inherit = "product.product"

    # internal_ref = fields.Char('Second Internal Reference',index=True)

    @api.model_create_multi
    def create(self, vals_list):
        products = super(ProductProduct, self.with_context(create_product_product=True)).create(vals_list)
        # `_get_variant_id_for_combination` depends on existing variants
        # self.clear_caches()
        for template, vals in zip(products, vals_list):
            related_vals = {}
            # if vals.get('default_code','') == '':
            name = self.env['ir.sequence'].next_by_code('product.template.code') or ' '
            vals['internal_ref'] =  name
            related_vals['internal_ref'] = vals['internal_ref']
            if related_vals:
                template.write(related_vals)
        return products

    def action_submit(self):
        self.write({'state':'approve'})

    def action_approve(self):
        self.write({'state':'confirmed','is_confirm':True})

    def set_to_draft(self):
        self.write({'state':'draft','is_confirm':False})
    
    def action_reject(self):
        self.write({'state':'reject'})

    
class ProductCategory(models.Model):
    _name = "product.categories"

    name = fields.Char('Name',required=True)
    slug = fields.Char('Slug')
    parent_id = fields.Many2one('product.categories',string="Parent Category",domain=[('parent_id','=',False)])
    description = fields.Text('Description')
    display_type = fields.Selection([
        ('Default', 'Default'),
        ('Products', 'Products'),
        ('Subcategories', 'Subcategories'),
        ('Both', 'Both')], string='Display Type', default='Default', copy=False)


class ProductType(models.Model):
    _name = "product.type"

    name = fields.Char('Name',required=True)
    slug = fields.Char('Slug')
    parent_id = fields.Many2one('product.type',string="Parent Type",domain=[('parent_id','=',False)])
    description = fields.Text('Description')

    
class ProductBrand(models.Model):
    _name = "product.brand"

    name = fields.Char('Name',required=True)
    description = fields.Text('Description')

class StockInventory(models.Model):
    _inherit = "stock.inventory"

    # def action_validate(self):
    #     res = super(StockInventory,self).action_validate()
    #     self.create_journal()
    #     return res

    prefill_counted_quantity = fields.Selection(string='Counted Quantities',
        help="Allows to start with prefill counted quantity for each lines or "
        "with all counted quantity set to zero.", default='zero',
        selection=[('counted', 'Default to stock on hand'), ('zero', 'Default to zero')])

    def action_validate(self):
        if not self.exists():
            return
        self.ensure_one()
        if not self.user_has_groups('stock.group_stock_manager'):
            # raise UserError(_("Only a stock manager can validate an inventory adjustment."))
            y = 1
        if not self.user_has_groups('account.group_account_invoice'):
            raise UserError(_("Only a accounts can validate an inventory adjustment."))
        if self.state != 'confirm':
            raise UserError(_(
                "You can't validate the inventory '%s', maybe this inventory " +
                "has been already validated or isn't ready.") % (self.name))
        inventory_lines = self.line_ids.filtered(lambda l: l.product_id.tracking in ['lot', 'serial'] and not l.prod_lot_id and l.theoretical_qty != l.product_qty)
        lines = self.line_ids.filtered(lambda l: float_compare(l.product_qty, 1, precision_rounding=l.product_uom_id.rounding) > 0 and l.product_id.tracking == 'serial' and l.prod_lot_id)
        if inventory_lines and not lines:
            wiz_lines = [(0, 0, {'product_id': product.id, 'tracking': product.tracking}) for product in inventory_lines.mapped('product_id')]
            wiz = self.env['stock.track.confirmation'].create({'inventory_id': self.id, 'tracking_line_ids': wiz_lines})
            return {
                'name': _('Tracked Products in Inventory Adjustment'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'views': [(False, 'form')],
                'res_model': 'stock.track.confirmation',
                'target': 'new',
                'res_id': wiz.id,
            }
        self._action_done()
        self.line_ids._check_company()
        self._check_company()
        self.create_journal()
        return True

    def create_journal(self):
        # for rec in self:
        # if self.vender_flag == 0:
        # if self.shipping_id:
        name = ""
        # for rec in self.product_ids:
        for line in self.line_ids:
            invoice = self.env['account.move']
            # val = []
            # order_line = {
            #     'product_id': self.channel_mapping_ids[0].channel_id.delivery_product_id.id,
            #     'price_unit':   self.shipping_full,
                
            # }
            name = self.name + '-' + line.product_id.name
            dict = []
            if line.cost_difference != 0:
                if line.categ_id.property_account_creditor_price_difference_categ:
                    if line.difference_qty < 0 :
                        amount = line.cost_difference * line.product_qty
                        dict1 = {
                                # 'move_name': self.name,
                                'name': name,
                                'price_unit': abs(line.cost_difference),
                                'product_id': line.product_id.id,
                                'quantity': abs(line.product_qty),
                                'debit':0.0,
                                'credit': abs(amount),
                                # 'debit': self.cost_difference < 0.0 and -self.cost_difference or 0.0,
                                # 'credit': self.cost_difference > 0.0 and self.cost_difference or 0.0,
                                'account_id': line.categ_id.property_stock_valuation_account_id.id,
                                # 'move_id': self._origin,
                                # 'date': self.date,
                                # 'exclude_from_invoice_tab': True,
                                # 'partner_id': terms_lines.partner_id.id,
                                'company_id': self.company_id.id,
                                # 'company_currency_id': self.company_currency_id.id,
                                }
                        dict.append((0,0,dict1))
                        dict2 = {
                                # 'move_name': self.name,
                                'name': name,
                                'price_unit': abs(line.cost_difference),
                                'product_id': line.product_id.id,
                                'quantity': abs(line.product_qty),
                                'debit': abs(amount),
                                'credit': 0.0,
                                # 'debit': self.cost_difference > 0.0 and self.cost_difference or 0.0,
                                # 'credit': self.cost_difference < 0.0 and -self.cost_difference or 0.0 ,
                                'account_id': line.categ_id.property_account_creditor_price_difference_categ.id,
                                # 'move_id': self._origin,
                                # 'date': self.date,
                                # 'exclude_from_invoice_tab': True,
                                # 'partner_id': terms_lines.partner_id.id,
                                'company_id': self.company_id.id,
                                # 'company_currency_id': self.company_currency_id.id,
                                }
                        dict.append((0,0,dict2))
                    if line.difference_qty > 0 :
                        amount = line.cost_difference * line.product_qty
                        dict1 = {
                                # 'move_name': self.name,
                                'name': name,
                                'price_unit': abs(line.cost_difference),
                                'product_id': line.product_id.id,
                                'quantity': abs(line.product_qty),
                                'debit':0.0,
                                'credit': abs(amount),
                                # 'debit': self.cost_difference < 0.0 and -self.cost_difference or 0.0,
                                # 'credit': self.cost_difference > 0.0 and self.cost_difference or 0.0,
                                'account_id': line.categ_id.property_account_creditor_price_difference_categ.id,
                                # 'move_id': self._origin,
                                # 'date': self.date,
                                # 'exclude_from_invoice_tab': True,
                                # 'partner_id': terms_lines.partner_id.id,
                                'company_id': self.company_id.id,
                                # 'company_currency_id': self.company_currency_id.id,
                                }
                        dict.append((0,0,dict1))
                        dict2 = {
                                # 'move_name': self.name,
                                'name': name,
                                'price_unit': abs(line.cost_difference),
                                'product_id': line.product_id.id,
                                'quantity': abs(line.product_qty),
                                'debit': abs(amount),
                                'credit': 0.0,
                                # 'debit': self.cost_difference > 0.0 and self.cost_difference or 0.0,
                                # 'credit': self.cost_difference < 0.0 and -self.cost_difference or 0.0 ,
                                'account_id': line.categ_id.property_stock_valuation_account_id.id,
                                # 'move_id': self._origin,
                                # 'date': self.date,
                                # 'exclude_from_invoice_tab': True,
                                # 'partner_id': terms_lines.partner_id.id,
                                'company_id': self.company_id.id,
                                # 'company_currency_id': self.company_currency_id.id,
                                }
                        dict.append((0,0,dict2))
                    if line.difference_qty == 0 and line.cost_difference != 0:
                        amount = line.cost_difference * line.product_qty
                        dict1 = {
                                # 'move_name': self.name,
                                'name': name,
                                'price_unit': abs(line.cost_difference),
                                'product_id': line.product_id.id,
                                'quantity': abs(line.product_qty),
                                'debit':0.0,
                                'credit': abs(amount),
                                # 'debit': self.cost_difference < 0.0 and -self.cost_difference or 0.0,
                                # 'credit': self.cost_difference > 0.0 and self.cost_difference or 0.0,
                                'account_id': line.categ_id.property_stock_valuation_account_id.id,
                                # 'move_id': self._origin,
                                # 'date': self.date,
                                # 'exclude_from_invoice_tab': True,
                                # 'partner_id': terms_lines.partner_id.id,
                                'company_id': self.company_id.id,
                                # 'company_currency_id': self.company_currency_id.id,
                                }
                        dict.append((0,0,dict1))
                        dict2 = {
                                # 'move_name': self.name,
                                'name': name,
                                'price_unit': abs(line.cost_difference),
                                'product_id': line.product_id.id,
                                'quantity': abs(line.product_qty),
                                'debit': abs(amount),
                                'credit': 0.0,
                                # 'debit': self.cost_difference > 0.0 and self.cost_difference or 0.0,
                                # 'credit': self.cost_difference < 0.0 and -self.cost_difference or 0.0 ,
                                'account_id': line.categ_id.property_account_creditor_price_difference_categ.id,
                                # 'move_id': self._origin,
                                # 'date': self.date,
                                # 'exclude_from_invoice_tab': True,
                                # 'partner_id': terms_lines.partner_id.id,
                                'company_id': self.company_id.id,
                                # 'company_currency_id': self.company_currency_id.id,
                                }
                        dict.append((0,0,dict2))
                else:
                    raise UserError("Set the price differnce account in the product category %s"%(line.categ_id.name))
            # val.append((0,0,order_line))
            # moveid = False
            # for move in self.move_ids:
            #     if move.product_id.id == line.product_id.id:
            #         moveid = move.id
            if line.difference_qty != 0 or line.cost_difference != 0:
                vals = {
                    # 'partner_id': self.shipping_id.id,
                    'ref': name,
                    'type':'entry',
                    'stock_adjustment_id':self.id,
                    'date':self.accounting_date or date.today(),
                    # 'so_link':self.id,
                    'line_ids':dict,
                    # 'invoice_line_ids':val,
                }
            
                inv = invoice.create(vals)
                inv.action_post()
                # self.vender_flag = 1
            # else:
            #     raise UserError('No shipping to create for this order')

    def action_get_account_moves(self):
        self.ensure_one()
        action_ref = self.env.ref('account.action_move_journal_line')
        if not action_ref:
            return False
        action_data = action_ref.read()[0]
        action_data['domain'] = ['|',('stock_move_id.id', 'in', self.move_ids.ids),('stock_adjustment_id','=',self.id)]
        action_data['context'] = dict(self._context, create=False)
        return action_data

class StockInventoryLine(models.Model):
    _inherit = "stock.inventory.line"

    product_cost = fields.Float('Cost',compute="onchange_product_cost",readonly=True)
    product_cost_new = fields.Float('New Cost',compute="onchange_product_cost_new",store=True,readonly=False)
    cost_difference = fields.Float('Cost Difference',compute="_cost_difference")

    @api.depends('product_id')
    def onchange_product_cost(self):
        for rec in self:
            rec.product_cost = rec.product_id.standard_price

    @api.depends('product_id')
    def onchange_product_cost_new(self):
        for rec in self:
            rec.product_cost_new = rec.product_id.standard_price

    @api.depends('product_id')
    @api.onchange('product_cost_new')
    def _cost_difference(self):
        for rec in self:
            rec.cost_difference = rec.product_cost_new - rec.product_cost


class PickingType(models.Model):
    _inherit = "stock.picking.type"  


    count_picking_in_progress = fields.Integer(compute='_compute_picking_count_in')


    def get_action_picking_tree_progress(self):
        return self._get_action('AG_products.action_picking_tree_progress')

    def _compute_picking_count_in(self):
        # TDE TODO count picking can be done using previous two
        domains = {
            # 'count_picking_draft': [('state', '=', 'draft')],
            'count_picking_in_progress': [('state', '=', 'in_progress')],
            # 'count_picking_waiting': [('state', 'in', ('confirmed', 'waiting'))],
            # 'count_picking_ready': [('state', '=', 'assigned')],
            # 'count_picking': [('state', 'in', ('assigned', 'waiting', 'confirmed'))],
            # 'count_picking_late': [('scheduled_date', '<', time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)), ('state', 'in', ('assigned', 'waiting', 'confirmed'))],
            # 'count_picking_backorders': [('backorder_id', '!=', False), ('state', 'in', ('confirmed', 'assigned', 'waiting'))],
        }
        for field in domains:
            data = self.env['stock.picking'].read_group(domains[field] +
                [('state', 'not in', ('done', 'cancel')), ('picking_type_id', 'in', self.ids)],
                ['picking_type_id'], ['picking_type_id'])
            count = {
                x['picking_type_id'][0]: x['picking_type_id_count']
                for x in data if x['picking_type_id']
            }
            for record in self:
                record[field] = count.get(record.id, 0)
        # for record in self:
        #     record.rate_picking_late = record.count_picking and record.count_picking_late * 100 / record.count_picking or 0
        #     record.rate_picking_backorders = record.count_picking and record.count_picking_backorders * 100 / record.count_picking or 0


    

