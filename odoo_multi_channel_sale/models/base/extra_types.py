# -*- coding: utf-8 -*-
##############################################################################
# Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>
##############################################################################
from odoo import api,fields,models


class ExtraType(models.Model):
	_name        = 'extra.type'
	_description = 'Extra Types'

	@api.model
	def get_type_list(self):
		mapping_ids = self.env['channel.type.mappings'].search(
			[('channel_id','=',self.instance_id.id)]
		)
		if mapping_ids:
			return [i.odoo_type_id for i in mapping_ids]
		return []

	@api.depends('instance_id')
	def _compute_extra_type_domain(self):
		for record in self:
			record.extra_type_domain_ids = [(6,0,record.get_type_list())]


	instance_id = fields.Many2one('multi.channel.sale','Instance')
	product_id  = fields.Many2one('product.template','Template')
	type_id = fields.Many2one('product.type','Internal Type')

	extra_type_ids = fields.Many2many(
		comodel_name = 'product.type',
		string       = 'Extra Types',
		domain       = '[("id","in",extra_type_domain_ids)]',
	)

	extra_type_domain_ids = fields.Many2many(
		comodel_name = 'product.type',
		relation     = 'extra_type_ref',
		column1      = 'product_type_ref',
		column2      = 'table_ref',
		string       = 'Type Domain',
		compute      = '_compute_extra_type_domain',
	)


	@api.onchange('instance_id')
	def change_domain(self):
		return {
			'domain': {
				'extra_type_ids': [
					('id','in',self.get_type_list())
				]
			}
		}
