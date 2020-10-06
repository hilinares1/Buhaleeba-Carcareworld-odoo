# -*- coding: utf-8 -*-
##############################################################################
# Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>
##############################################################################
from odoo import fields,models


class ProductType(models.Model):
	_inherit = 'product.type'

	channel_mapping_ids = fields.One2many(
		string       = 'Mappings',
		comodel_name = 'channel.type.mappings',
		inverse_name = 'category_name',
		copy         = False
	)

	channel_type_ids = fields.One2many(
		string       = 'Channel Types',
		comodel_name = 'extra.type',
		inverse_name = 'type_id',
		copy         = False
	)

	def write(self, vals):
		for record in self:
			record.channel_mapping_ids.write({'need_sync': 'yes'})
			res = super(ProductType, record).write(vals)
		return res
