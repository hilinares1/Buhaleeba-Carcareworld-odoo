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

from odoo import api, fields, models
import odoo.addons.decimal_precision as dp


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
            vals['default_code'] =  name
            related_vals['default_code'] = vals['default_code']
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
            vals['default_code'] =  name
            related_vals['default_code'] = vals['default_code']
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

    

