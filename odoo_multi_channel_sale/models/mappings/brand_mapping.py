# -*- coding: utf-8 -*-
##############################################################################
# Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>
##############################################################################
from odoo import api,fields,models


class ChannelBrandMappings(models.Model):
	_name        = 'channel.brand.mappings'
	_inherit     = 'channel.mappings'
	_rec_name    = 'category_name'
	_description = 'Category Mapping'

	store_brand_id = fields.Char('Store Brand ID',required=True)
	category_name     = fields.Many2one('product.brand','Type')
	odoo_brand_id  = fields.Integer('Odoo Brand ID',required=True)
	leaf_category     = fields.Boolean('Leaf Category')

	_sql_constraints = [
		(
			'channel_store_store_category_id_uniq',
			'unique(channel_id, store_brand_id)',
			'Store Brand ID must be unique for channel category mapping!'
		),
		(
			'channel_odoo_category_id_uniq',
			'unique(channel_id, odoo_brand_id)',
			'Odoo Brand ID must be unique for channel category mapping!'
		)
	]


	def unlink(self):
		for record in self:
			if record.store_brand_id:
				match = record.channel_id.match_type_feeds(record.store_brand_id)
				if match: match.unlink()
		return super(ChannelBrandMappings, self).unlink()

	@api.onchange('category_name')
	def change_odoo_id(self):
		self.odoo_brand_id = self.category_name.id

	def _compute_name(self):
		for record in self:
			record.name = record.category_name.name if record.category_name else 'Deleted'
