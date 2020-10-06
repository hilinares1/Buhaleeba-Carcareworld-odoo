# -*- coding: utf-8 -*-
##############################################################################
# Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>
##############################################################################
from odoo import api,fields,models


class ExtraBrand(models.Model):
	_name        = 'extra.brand'
	_description = 'Extra Brand'

	@api.model
	def get_type_list(self):
		mapping_ids = self.env['channel.brand.mappings'].search(
			[('channel_id','=',self.instance_id.id)]
		)
		if mapping_ids:
			return [i.odoo_brand_id for i in mapping_ids]
		return []

	@api.depends('instance_id')
	def _compute_extra_type_domain(self):
		for record in self:
			record.extra_brand_domain_ids = [(6,0,record.get_type_list())]


	instance_id = fields.Many2one('multi.channel.sale','Instance')
	product_id  = fields.Many2one('product.template','Template')
	brand_id = fields.Many2one('product.brand','Internal Brand')

	extra_brand_ids = fields.Many2many(
		comodel_name = 'product.brand',
		string       = 'Extra Brands',
		domain       = '[("id","in",extra_brand_domain_ids)]',
	)

	extra_brand_domain_ids = fields.Many2many(
		comodel_name = 'product.brand',
		relation     = 'extra_brand_ref',
		column1      = 'product_brand_ref',
		column2      = 'table_ref',
		string       = 'Brand Domain',
		compute      = '_compute_extra_type_domain',
	)


	@api.onchange('instance_id')
	def change_domain(self):
		return {
			'domain': {
				'extra_brand_ids': [
					('id','in',self.get_type_list())
				]
			}
		}
