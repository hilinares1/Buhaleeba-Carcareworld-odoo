# -*- coding: utf-8 -*-
##############################################################################
# Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>
##############################################################################
from odoo import fields,models


class ProductBrand(models.Model):
	_inherit = 'product.brand'

	channel_mapping_ids = fields.One2many(
		string       = 'Mappings',
		comodel_name = 'channel.brand.mappings',
		inverse_name = 'category_name',
		copy         = False
	)

	channel_brand_ids = fields.One2many(
		string       = 'Channel Types',
		comodel_name = 'extra.brand',
		inverse_name = 'brand_id',
		copy         = False
	)

	def write(self, vals):
		for record in self:
			record.channel_mapping_ids.write({'need_sync': 'yes'})
			res = super(ProductBrand, record).write(vals)
		return res
