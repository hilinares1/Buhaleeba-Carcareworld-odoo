# -*- coding: utf-8 -*-
##############################################################################
# Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>
##############################################################################
from ...ApiTransaction import Transaction

from odoo import api,fields,models
from odoo.tools.translate import _
from odoo.exceptions import UserError
import logging
_logger	 = logging.getLogger(__name__)
try:
    from wordpress import API
except ImportError:
    _logger.info(
        '**Please Install wordpress Python Api=>(cmd: pip3 install wordpress)')

class ExportOperation(models.TransientModel):
	_name = 'export.operation'
	_description = 'Export Operation'
	_inherit = 'channel.operation'

	operation=fields.Selection(
		selection=[
			('export','Export'),
			('update','Update')
		],
		default ='export',
		required=True
	)

	object = fields.Selection(
		selection=[
			('product.categories','Category'),
			('product.type','Type'),
			('product.brand','Brand'),
			('product.template','Product Template'),
		],
		default='product.categories',
	)

	def export_button(self):
		connect = self.env['multi.channel.sale'].search([('id','=',self.channel_id.id)])	
		if self.object == 'product.type':
    		
			message = self.sudo().export_update_woocommerce_type()
			count = self.sudo().export_woocommerce_types(0)
			if isinstance(message, str):
				message += str(count)+" Types have been exported"
			else:
				message = str(count)+" Types have been exported"
			return connect.display_message(message)
		elif self.object == 'product.brand':
    			
			message = self.sudo().export_update_woocommerce_brand()
			count = self.sudo().export_woocommerce_brands(0)
			if isinstance(message, str):
				message += str(count)+" Brands have been exported"
			else:
				message = str(count)+" Brands have been exported"
			return connect.display_message(message)

		else:
			if self._context.get('active_model','multi.channel.sale') == 'multi.channel.sale':
				return Transaction(channel=self.channel_id).export_data(
					object = self.object,
					object_ids = self.env[self.object].search([]).ids,
					operation = 'export',
				)
			else:
				return Transaction(channel=self.channel_id).export_data(
					object = self._context.get('active_model'),
					object_ids = self._context.get('active_ids'),
					operation = self.operation,
				)

	def get_wordpress_connection(self,version = "wp/v2"):
		connect = self.env['multi.channel.sale'].search([('id','=',self.channel_id.id)])
		try:
			woocommerce = API(
				url=connect.woocommerce_url,
				consumer_key=connect.woocommerce_consumer_key,
				consumer_secret=connect.woocommerce_secret_key,
				# wp_api=True,
				basic_auth=True,
				# oauth1a_3leg=False,
				# no_auth=False,
				# version=version,
				wp_user="ccwmanager",
				wp_pass="appsgate@2020",
				# timeout=40,
				# query_string_auth=False,
				# verify_ssl        =    False,
				api="wp-json",
				version='wp/v2',
				user_auth = True
			)
		except ImportError:
			raise UserError("**Please Install Wordpress Python Api=>(cmd: pip3 install woocommerce)")
		return woocommerce

	def export_woocommerce_types(self,count , parent_id = False):
    		# self.import_woocommerce_types()
		parent = 0
		# count = 0
		# parent_id = False
		category_records = ''
		connect = self.env['multi.channel.sale'].search([('id','=',self.channel_id.id)])
		category_records = self.env['product.type'].search([])
		if parent_id:
			category_records = self.env['product.type'].browse(parent_id)
		for category in category_records:
			mapping_rec = self.env['channel.type.mappings'].search([('odoo_type_id','in',[category.id]),('channel_id.id','=',self.channel_id.id)])
			if mapping_rec and parent_id:
				return mapping_rec.store_type_id
			if not mapping_rec:
				count = count + 1
				if category.parent_id :
					parent = self.export_woocommerce_types(count, category.parent_id.id)
				version = "wp/v2"
				woocommerce = self.get_wordpress_connection(version)
				category_dict = {
							'name'  		: category.name,
							'description'   : str(category.description),
							
				}
				if parent:
    					
					category_dict.update({'parent': parent,})
				# raise UserError(category_dict.values())
				return_dict = woocommerce.post('ysg_product_type',category_dict).json()
				if 'message' in return_dict:
					raise UserError(_('Error in Creating Types : '+str(return_dict['message'])))
				mapping_dict = {
							'channel_id'	: self.id,
							'store_type_id'	: return_dict['id'],
							'odoo_type_id'	: category.id,
							'category_name'	: category.id,
							'operation'     : 'export'
				}
				obj = self.env['channel.type.mappings']
				connect._create_mapping(obj, mapping_dict)
				if parent_id:
					return return_dict['id']
		connect._cr.commit()
		return count
				# message += str(count)+" types have been exported"
				# return self.display_message(message)

	def export_update_woocommerce_type(self):
		count = 0
		store_brand_id = 0
		connect = self.env['multi.channel.sale'].search([('id','=',self.channel_id.id)])
		category_update = self.env['channel.brand.mappings'].search([('need_sync','=','yes'),('channel_id.id','=',self.channel_id.id)])
		for category_map in category_update:
				category = category_map.category_name
				count += 1
				# if category.parent_id:
				# 	parent_category = self.env['channel.type.mappings'].search([('odoo_type_id','=',category.parent_id.id),('channel_id.id','=',self.id)])
				# 	if not parent_category:
				# 		self.export_woocommerce_types(0)
				# 		parent_category = self.env['channel.type.mappings'].search([('odoo_type_id','=',category.parent_id.id),('channel_id.id','=',self.id)])
				# 		store_type_id = parent_category.store_type_id
				category_dict = {
					'name' 		: category.name,
					'description' 		: str(category.description),
					'parent_id'	: store_brand_id,
				}
				version = "wp/v2"
				woocommerce = self.get_wordpress_connection(version)
				return_dict = woocommerce.put('ysg_product_type/'+category_map.store_brand_id,category_dict).json()
				if 'message' in return_dict:
					raise UserError(_('Error in Updating Types : '+str(return_dict['message'])))
				category_map.need_sync = 'no'
		return connect.display_message(str(count)+" Types Updated  ")

	def export_woocommerce_brands(self,count):
    		# self.import_woocommerce_types()
		parent = 0
		# count = 0
		# parent_id = False
		category_records = ''
		connect = self.env['multi.channel.sale'].search([('id','=',self.channel_id.id)])
		category_records = self.env['product.brand'].search([])
		# if parent_id:
		# 	category_records = self.env['product.type'].browse(parent_id)
		for category in category_records:
			mapping_rec = self.env['channel.brand.mappings'].search([('odoo_brand_id','in',[category.id]),('channel_id.id','=',self.channel_id.id)])
			if mapping_rec :
				return mapping_rec.store_brand_id
			if not mapping_rec:
				count = count + 1
				# if category.parent_id :
				# 	parent = self.export_woocommerce_types(count, category.parent_id.id)
				woocommerce = connect.get_woocommerce_connection()
				category_dict = {
							'name'  : category.name,
							# 'description' 		: category.description,
				}
				# if parent:
				# 	category_dict.update({'parent': parent,})
				return_dict = woocommerce.post('products/attributes/3/terms',category_dict).json()
				if 'message' in return_dict:
					raise UserError(_('Error in Creating brands : '+str(return_dict['message'])))
				mapping_dict = {
							'channel_id'		: self.id,
							'store_brand_id'	: return_dict['id'],
							'odoo_brand_id'	: category.id,
							'category_name'		: category.id,
							'operation'             : 'export'
				}
				obj = self.env['channel.brand.mappings']
				connect._create_mapping(obj, mapping_dict)
				# if parent_id:
				# 	return return_dict['id']
		connect._cr.commit()
		return count

	

	def export_update_woocommerce_brand(self):
		count = 0
		store_brand_id = 0
		connect = self.env['multi.channel.sale'].search([('id','=',self.channel_id.id)])
		category_update = self.env['channel.brand.mappings'].search([('need_sync','=','yes'),('channel_id.id','=',self.channel_id.id)])
		for category_map in category_update:
				category = category_map.category_name
				count += 1
				# if category.parent_id:
				# 	parent_category = self.env['channel.type.mappings'].search([('odoo_type_id','=',category.parent_id.id),('channel_id.id','=',self.id)])
				# 	if not parent_category:
				# 		self.export_woocommerce_types(0)
				# 		parent_category = self.env['channel.type.mappings'].search([('odoo_type_id','=',category.parent_id.id),('channel_id.id','=',self.id)])
				# 		store_type_id = parent_category.store_type_id
				category_dict = {
					'name' 		: category.name,
					# 'description' 		: category.description,
					# 'parent_id'	: store_brand_id,
				}
				woocommerce = connect.get_woocommerce_connection()
				return_dict = woocommerce.put('products/attributes/3/terms/'+category_map.store_brand_id,category_dict).json()
				if 'message' in return_dict:
					raise UserError(_('Error in Updating Brands : '+str(return_dict['message'])))
				category_map.need_sync = 'no'
		return connect.display_message(str(count)+" Brands Updated  ")
