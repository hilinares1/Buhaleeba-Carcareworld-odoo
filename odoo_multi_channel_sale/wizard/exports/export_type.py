# -*- coding: utf-8 -*-
##############################################################################
# Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>
##############################################################################
from odoo import api,fields,models

class ExportType(models.TransientModel):
	_name = 'export.type'
	_description = 'Export Type'
	_inherit = 'export.operation'

	type_ids = fields.Many2many(
		comodel_name = 'product.type',
		string       = 'Type'
	)

	@api.model
	def default_get(self,fields):
		res = super(ExportType,self).default_get(fields)
		if not res.get('type_ids') and self._context.get('active_model')=='product.type':
			res['type_ids'] = self._context.get('active_ids')
		return res
