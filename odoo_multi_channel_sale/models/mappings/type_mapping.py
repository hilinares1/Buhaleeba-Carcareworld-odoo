# -*- coding: utf-8 -*-
##############################################################################
# Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>
##############################################################################
from odoo import api,fields,models


class ChannelTypeMappings(models.Model):
	_name        = 'channel.type.mappings'
	_inherit     = 'channel.mappings'
	_rec_name    = 'category_name'
	_description = 'Category Mapping'

	store_type_id = fields.Char('Store Type ID',required=True)
	category_name     = fields.Many2one('product.type','Type')
	odoo_type_id  = fields.Integer('Odoo Type ID',required=True)
	leaf_category     = fields.Boolean('Leaf Category')

	_sql_constraints = [
		(
			'channel_store_store_category_id_uniq',
			'unique(channel_id, store_type_id)',
			'Store Type ID must be unique for channel category mapping!'
		),
		(
			'channel_odoo_category_id_uniq',
			'unique(channel_id, odoo_type_id)',
			'Odoo Type ID must be unique for channel category mapping!'
		)
	]


	def unlink(self):
		for record in self:
			if record.store_type_id:
				match = record.channel_id.match_type_feeds(record.store_type_id)
				if match: match.unlink()
		return super(ChannelTypeMappings, self).unlink()

	@api.onchange('category_name')
	def change_odoo_id(self):
		self.odoo_type_id = self.category_name.id

	def _compute_name(self):
		for record in self:
			record.name = record.category_name.name if record.category_name else 'Deleted'
