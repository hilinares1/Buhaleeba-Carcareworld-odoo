#!/usr/bin/env python
# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#    See LICENSE file for full copyright and licensing details.
#################################################################################

from odoo import api,fields,models
from odoo.tools.translate import _
from odoo.exceptions import UserError
import logging
_logger	 = logging.getLogger(__name__)

try:
	from woocommerce import API
except ImportError:
	_logger.info('**Please Install Woocommerce Python Api=>(cmd: pip3 install woocommerce)')
	
class MultiChannelSale(models.Model):
	_inherit = "multi.channel.sale"

	
	def export_all_woocommerce_types(self):
		message = self.sudo().export_update_woocommerce_type()
		count = self.sudo().export_woocommerce_types(0)
		message += str(count)+" types have been exported"
		return self.display_message(message)

	def export_woocommerce_types(self,count , parent_id = False):
		# self.import_woocommerce_types()
		parent = 0
		category_records = ''
		# if not parent_id and 'active_ids' in self._context:
		# 	if self._context['active_ids'] and self._context['active_model'] == 'product.category':
		# 		category_records=self.env['product.category'].browse(self._context['active_ids'])
		# elif not parent_id:
		category_records = self.env['product.type'].search([])
		if parent_id:
			category_records = self.env['product.type'].browse(parent_id)
		for category in category_records:
			mapping_rec = self.env['channel.type.mappings'].search([('odoo_type_id','in',[category.id]),('channel_id.id','=',self.id)])
			if mapping_rec and parent_id:
				return mapping_rec.store_type_id
			if not mapping_rec:
				# count = count + 1
				if category.parent_id :
					parent = self.export_woocommerce_types(count, category.parent_id.id)
				woocommerce = self.get_woocommerce_connection()
				category_dict = {
								'name'  : category.name,
				}
				if parent:
					category_dict.update({'parent': parent,})
				return_dict = woocommerce.post('products/attributes',category_dict).json()
				if 'message' in return_dict:
					raise UserError(_('Error in Creating Types : '+str(return_dict['message'])))
				mapping_dict = {
							'channel_id'		: self.id,
							'store_type_id'	: return_dict['id'],
							'odoo_type_id'	: category.id,
							'category_name'		: category.id,
							'operation'             : 'export'
				}
				obj = self.env['channel.type.mappings']
				self._create_mapping(obj, mapping_dict)
				if parent_id:
					return return_dict['id']
				count = count + 1
		self._cr.commit()
		return count

	def export_woocommerce_type_id(self, category):
		parent= False
		if category:
			mapping_rec = self.env['channel.type.mappings'].search([('odoo_type_id','=',category.id),('channel_id.id','=',self.id)])
			if not mapping_rec:
				if category.parent_id:
					parent = self.export_woocommerce_types(0, category.parent_id.id)
				woocommerce = self.get_woocommerce_connection()
				category_dict = {
								'name' : category.name,
				}
				if parent:
					category_dict.update({'parent': parent,})
				return_dict = woocommerce.post('products/product types',category_dict).json()
				if 'message' in return_dict:
					raise UserError(_('Error in Creating Types : '+str(return_dict['message'])))
				mapping_dict = {
							'channel_id'		: self.id,
							'store_type_id'	: return_dict['id'],
							'odoo_type_id'	: category.id,
							'category_name'		: category.id,
							'operation'             : 'export'
				}
				obj = self.env['channel.type.mappings']
				self._create_mapping(obj, mapping_dict)
				self._cr.commit()
				return return_dict['id']
		return False