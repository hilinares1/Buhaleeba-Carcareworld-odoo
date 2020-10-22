# from odoo import fields, models, api
#
#
# class ProductTemplate(models.Model):
#     _inherit = "product.template"
#
#     sub_category = fields.Many2one((),string='Sub Category')
#     brand = fields.Char("Brand")
#
#
# class ProductProduct(models.Model):
#     _inherit = "product.product"
#
#     default_code = fields.Char(readonly=True)
#     last_prise_date = fields.Date()
#     last_prise_vendor = fields.Char()
#     common_name = fields.Char(related='product_tmpl_id.common_name', store=True)
#     prod_code = fields.Char('Part Number', related='product_tmpl_id.prod_code', store=True)
