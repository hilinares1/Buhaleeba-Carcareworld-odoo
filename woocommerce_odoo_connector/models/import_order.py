#!/usr/bin/env python
# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#    See LICENSE file for full copyright and licensing details.
#################################################################################

from odoo import api,fields,models
from odoo.tools.translate import _
from datetime import datetime,timedelta
from odoo.addons.odoo_multi_channel_sale.tools import extract_list as EL
from odoo.exceptions import UserError
import logging
_logger	 = logging.getLogger(__name__)
try:
	from woocommerce import API
except ImportError:
	_logger.info('**Please Install Woocommerce Python Api=>(cmd: pip3 install woocommerce)')

class MultiChannelSale(models.Model):
	_inherit = "multi.channel.sale"

	def create_or_get_woocommerce_voucher(self, vouchers):
		voucher_rec = self.env['product.feed'].search([('name','=','voucher')])
		if not voucher_rec:
			voucher_rec = self.create_woocommerce_voucher()
		voucher_list = []
		for voucher in vouchers:
			voucher_line = {
							'line_name'		  		: "Voucher",
							'line_price_unit' 		: -(float(voucher['amount'])),
							'line_product_uom_qty'  : 1,
							'line_product_id'		: voucher_rec.store_id,
							'line_source'			: 'discount'
			}
			voucher_list.append((0,0,voucher_line))
		return voucher_list
	
	def create_woocommerce_voucher(self):
		data = {
				'name'		:"voucher",
				'store_id'	:"wc",
				'channel_id':self.id,
				'type'		:'service'
		}
		product_rec = self.env['product.feed'].create(data)
		feed_res = dict(create_ids=[product_rec],update_ids=[])
		self.env['channel.operation'].post_feed_import_process(self,feed_res)
		return product_rec
	
	def create_or_get_woocommerce_shipping(self,shipping_line):
		shipping_rec = self.env['product.feed'].search([('name','=','shipping')])
		if not shipping_rec:
			shipping_rec = self.create_woocommerce_shipping()
		shipping_list = []
		for shipping in shipping_line:
			if float(shipping['total'])>0:
				tax = self.get_woocommerce_taxes(shipping['taxes'])
				shipping_line = {
								'line_name'		  		: "Shipping",
								'line_price_unit' 		: float(shipping['total']),
								'line_product_uom_qty'  : 1,
								'line_product_id'		: shipping_rec.store_id,
								'line_taxes'			: tax,
								'line_source'			: 'delivery',
				}
				shipping_list.append((0,0,shipping_line))
		return shipping_list

	def create_woocommerce_shipping(self):
		data = {
				'name'		:"shipping",
				'store_id'	:"sh",
				'channel_id':self.id,
				'type'		:'service'
		}
		product_rec = self.env['product.feed'].create(data)
		feed_res = dict(create_ids=[product_rec],update_ids=[])
		self.env['channel.operation'].post_feed_import_process(self,feed_res)
		return product_rec

	def get_woocommerce_taxes(self,data):
		l = []
		if data:
			for taxes in data:
				if 'total' in taxes:
					if taxes['total']:
						if float(taxes['total'])>0:
							l.append({'id':taxes['id']})
		return l

	def get_woocommerce_order_line(self, data,sid=None,pay_status=None,cod_additional_cost=None):
		order_lines = []
		variant = 0
		for line in data:
			if not  self.env['channel.template.mappings'].search([('store_product_id','=',line['product_id']),('channel_id.id','=',self.id)]):
				self.import_woocommerce_products_id(line['product_id'])
			product_template_id = self.env['channel.product.mappings'].search([('store_variant_id','=',line['variation_id']),('channel_id.id','=',self.id)])
			if not product_template_id:
				product_template_id = self.env['channel.product.mappings'].search([('store_product_id','=',line['product_id']),('channel_id.id','=',self.id)])

			order_line_dict = {
					'line_name'				:line['name'],
					'line_price_unit'		:line['item_unit_price'],
					'line_discount'         :self.get_woocommerce_discount_values(line['total_discount_amount'],line['discount_type'],sid),
					'line_discount_points'  :self.get_woocommerce_discount_values_points(line['total_discount_amount'],line['discount_type'],sid),
					'line_discount_type'    :self.get_woocommerce_discount_types(line['discount_type'],sid),
					'line_product_id'		:product_template_id.store_product_id,
					'line_variant_ids'		:product_template_id.store_variant_id,
					'line_taxes'			:self.get_woocommerce_taxes(line['taxes'])
			}
			order_lines.append((0,0,order_line_dict))
		# if pay_status == "cod":
		# 	if cod_additional_cost:
		# 		raise UserError('tessssst') 
					# order_line_dict = {
					# 		'line_name'				:line['name'],
					# 		'line_price_unit'		:line['item_unit_price'],
					# 		'line_discount'         :line['total_discount_amount'],
					# 		'line_discount_type'    :self.get_woocommerce_discount_types(line['discount_type'],sid),
					# 		'line_product_id'		:product_template_id.store_product_id,
					# 		'line_variant_ids'		:product_template_id.store_variant_id,
					# 		'line_taxes'			:self.get_woocommerce_taxes(line['taxes'])
					# }
					# order_lines.append((0,0,order_line_dict))
		return order_lines

	def get_woocommerce_discount_types(self,data,sid):
		l = []
		dis = self.env['discount.type']
		if data:
			for type in data:
				voucher_line = {
								'name'		  		: type['type'],
								'value' 		: type['order_item_value'],
								'so_id'  : "%s"%(sid),
				}
				discount = dis.create(voucher_line)
				l.append(discount.id)
		return [(6, None, l)]

	def get_woocommerce_discount_values(self,dis_data,data,sid):
		points = 0
		dis = self.env['discount.type']
		if data:
			for type in data:
				points_type = type['type']
				if points_type == "Points":
    				points += type['order_item_value']
		return dis_data - points

	def get_woocommerce_discount_values_points(self,dis_data,data,sid):
    		points = 0
		dis = self.env['discount.type']
		if data:
			for type in data:
				points_type = type['type']
				if points_type == "Points":
    				points += type['order_item_value']
		return points


	def import_woocommerce_orders(self):
		self.import_woocommerce_attribute()
		self.import_woocommerce_categories()
		woocommerce = self.get_woocommerce_connection()
		message = ''
		self.woc_check_and_create_tax(woocommerce)
		list_order = []
		count = 0
		context = dict(self._context)
		order_feed_data = self.env['order.feed']
		date = self.with_context({'name':'order'}).get_woocommerce_import_date()
		if not date:
			raise UserError(_("Please set date in multi channel configuration"))
		try:
			i=1
			while(i):
				order_data = woocommerce.get('orders?page='+str(i)+'&after='+date).json()
				if 'errors' in order_data:
					raise UserError(_("Error : "+str(order_data['errors'][0]['message'])))
				else :
					if order_data:
						i=i+1
						for order in order_data:
							_logger.info("===============================>%r",order['id'])
							if not order_feed_data.search([('store_id','=',order['id']),('channel_id.id','=',self.id)]):
								count = count + 1
								if order['id']:
									woocommerce2 = woocommerce
									if woocommerce2:
										order_data = woocommerce2.get("orders/"+str(order['id'])).json()
										data = order_data['line_items']
										pay_status = order_data['ysg_payment_status']
										cod_additional_cost = order_data['ysg_cod_additional_cost']
										raise UserError(pay_status)
										order_lines = self.get_woocommerce_order_line(data,order_data['id'],pay_status,cod_additional_cost)
										if order['shipping_lines']:
											order_lines += self.create_or_get_woocommerce_shipping(order_data['shipping_lines'])
								customer ={}
								if order['customer_id']:
									customer = woocommerce.get('customers/'+str(order['customer_id'])).json()
								else:
									customer.update({'first_name':order['billing']['first_name'],'last_name':order['billing']['last_name'],'email':order['billing']['email'] })
								_logger.info("===================>%r",[order['billing'],order['shipping'],customer,order])
								method_title ='Delivery'
								if order['shipping_lines']:
									method_title = order['shipping_lines'][0]['method_title']
								pickup_store_detail = ""
								if order['status'] == 'pickup-cod' or order['status'] == 'pickup-paid':
									ship = True
									pickuup= {}
									
									pickuup = order['ysg_pickup_store_details']
									# raise UserError(pickuup)
									# for lines in pickuup:
									pickup_store_detail = pickuup['name']
										# raise UserError(lines['name'])
										#  + str(line['address']) + str(line['city']) +str(line['phone'])+str(line['store_country'])
								else:
									ship = False
								# raise UserError("%s %s"%(order['status'],order['payment_method_title']))
								if order['status'] == 'pending processing' and order['payment_method_title'] == 'Cash on delivery':
									shiping = True
								else:
									shiping = False
								order_dict={
											'store_id'		 : order['id'],
											'channel_id'	 : self.id,
											'partner_id'	 : order['customer_id'] or order['billing']['email'],
											'payment_method' : order['payment_method_title'],
											'line_type'		 : 'multi',
											'carrier_id'	 : method_title,
											'line_ids'		 : order_lines,
											'shipping_full'  : order['shipping_full'],
											'points_amt'  : order['ysg_order_earned_points'],
											'pickup_store_details'  : pickup_store_detail,
											'states_ship'    : ship,
											'states_shiping'    : shiping,
											'currency'		 : order['currency'],
											'customer_name'  : customer['first_name'] +" "+customer['last_name'],
											'customer_email' : customer['email'],
											'order_state'	 : order['status'],
											}
								if order['billing']:
									order_dict.update({
													'invoice_partner_id': order['billing']['email'],
													'invoice_name'	   	: order['billing']['first_name']+" "+order['billing']['last_name'],
													'invoice_email'    	: order['billing']['email'],
													'invoice_phone'    	: order['billing']['phone'],
													'invoice_street'   	: order['billing']['address_1'],
													'invoice_street2'  	: order['billing']['address_2'],
													'invoice_zip'	   	: order['billing']['postcode'],
													'invoice_city'	   	: order['billing']['city'],
													'invoice_state_id' 	: order['billing']['state'],
													'invoice_country_id': order['billing']['country'],
													})
								if order['shipping']:
									order_dict['same_shipping_billing'] = False
									order_dict.update({
													'shipping_partner_id'   :order['billing']['email'],
													'shipping_name'	   		:order['shipping']['first_name']+" "+order['billing']['last_name'],
													'shipping_street'   	:order['shipping']['address_1'],
													'shipping_street2'  	:order['shipping']['address_2'],
													'shipping_email'		:order['billing']['email'],
													'shipping_zip'	   		:order['shipping']['postcode'],
													'shipping_city'	   		:order['shipping']['city'],
													'shipping_state_id' 	:order['shipping']['state'],
													'shipping_country_id'	:order['shipping']['country'],
													})
								order_rec = order_feed_data.with_context(context).create(order_dict)
								self._cr.commit()
								list_order.append(order_rec)
					else:
						i=0
			context.update({'group_by':'state',
						})
			list_order.reverse()
			feed_res = dict(create_ids=list_order,update_ids=[])
			self.env['channel.operation'].with_context(context).post_feed_import_process(self,feed_res)
			self.import_order_date = str(datetime.now().date())
			message +=  str(count)+" Order(s) Imported!"
			return self.display_message(message)
		except Exception as e:
			raise UserError(_("Error : "+str(e)))
	
	def import_all_woocommerce_orders(self):
		self.import_woocommerce_attribute()
		self.import_woocommerce_categories()
		woocommerce = self.get_woocommerce_connection()
		message = ''
		self.woc_check_and_create_tax(woocommerce)
		list_order = []
		count = 0
		context = dict(self._context)
		order_feed_data = self.env['order.feed']
		pagination_info = self.pagination_info
		limit = self.api_record_limit
		if not pagination_info:
			pagination_info = {}
		else:
			pagination_info = eval(pagination_info)
		try:
			i=pagination_info.get("import_order_last_page",1)			
			while(i):
				url = 'orders?page='+str(i)
				if limit:
					url += '&per_page=%s'%(limit)
				order_data = woocommerce.get(url).json()
				if 'errors' in order_data:
					raise UserError(_("Error : "+str(order_data['errors'][0]['message'])))
				else :
					if order_data:
						i=i+1
						for order in order_data:
							_logger.info("===============================>%r",order['id'])
							if not order_feed_data.search([('store_id','=',order['id']),('channel_id.id','=',self.id)]):
								count = count + 1
								if order['id']:
									woocommerce2 = woocommerce
									if woocommerce2:
										order_data = woocommerce2.get("orders/"+str(order['id'])).json()
										data = order_data['line_items']
										pay_status = order_data['ysg_payment_status']
										cod_additional_cost = order_data['ysg_cod_additional_cost']
										raise UserError(pay_status)
										order_lines = self.get_woocommerce_order_line(data,order_data['line_items'],pay_status,cod_additional_cost)
										if order['shipping_lines']:
											order_lines += self.create_or_get_woocommerce_shipping(order_data['shipping_lines'])
								customer ={}
								if order['customer_id']:
									customer = woocommerce.get('customers/'+str(order['customer_id'])).json()
								else:
									customer.update({'first_name':order['billing']['first_name'],'last_name':order['billing']['last_name'],'email':order['billing']['email'] })
								_logger.info("===================>%r",[order['billing'],order['shipping'],customer,order])
								method_title ='Delivery'
								if order['shipping_lines']:
									method_title = order['shipping_lines'][0]['method_title']
								pickup_store_detail = ""
								if order['status'] == 'pickup-cod' or order['status'] == 'pickup-paid':
									ship = True
									pickuup= {}
									
									pickuup = order['ysg_pickup_store_details']
									# raise UserError(pickuup)
									# for lines in pickuup:
									pickup_store_detail = pickuup['name']
										# raise UserError(lines['name'])
										#  + str(line['address']) + str(line['city']) +str(line['phone'])+str(line['store_country'])
								else:
									ship = False

								# raise UserError("%s %s"%(order['status'],order['payment_method_title']))
								if order['status'] == 'pending processing' and order['payment_method_title'] == 'Cash on delivery':
									shiping = True
								else:
									shiping = False
								order_dict={
											'store_id'		 : order['id'],
											'channel_id'	 : self.id,
											'partner_id'	 : order['customer_id'] or order['billing']['email'],
											'payment_method' : order['payment_method_title'],
											'line_type'		 : 'multi',
											'carrier_id'	 : method_title,
											'line_ids'		 : order_lines,
											'shipping_full'  : order['shipping_full'],
											'points_amt'  : order['ysg_order_earned_points'],
											'pickup_store_details'  : pickup_store_detail,
											'states_ship'    : ship,
											'states_shiping'    : shiping,
											'currency'		 : order['currency'],
											'customer_name'  : customer['first_name'] +" "+customer['last_name'],
											'customer_email' : customer['email'],
											'order_state'	 : order['status'],
											}
								if order['billing']:
									order_dict.update({
													'invoice_partner_id': order['billing']['email'],
													'invoice_name'	   	: order['billing']['first_name']+" "+order['billing']['last_name'],
													'invoice_email'    	: order['billing']['email'],
													'invoice_phone'    	: order['billing']['phone'],
													'invoice_street'   	: order['billing']['address_1'],
													'invoice_street2'  	: order['billing']['address_2'],
													'invoice_zip'	   	: order['billing']['postcode'],
													'invoice_city'	   	: order['billing']['city'],
													'invoice_state_id' 	: order['billing']['state'],
													'invoice_country_id': order['billing']['country'],
													})
								if order['shipping']:
									order_dict['same_shipping_billing'] = False
									order_dict.update({
													'shipping_partner_id'   :order['billing']['email'],
													'shipping_name'	   		:order['shipping']['first_name']+" "+order['billing']['last_name'],
													'shipping_street'   	:order['shipping']['address_1'],
													'shipping_street2'  	:order['shipping']['address_2'],
													'shipping_email'		:order['billing']['email'],
													'shipping_zip'	   		:order['shipping']['postcode'],
													'shipping_city'	   		:order['shipping']['city'],
													'shipping_state_id' 	:order['shipping']['state'],
													'shipping_country_id'	:order['shipping']['country'],
													})
								order_rec = order_feed_data.with_context(context).create(order_dict)
								self._cr.commit()
								list_order.append(order_rec)
								list_order.reverse()
								if limit:
									feed_res = dict(create_ids=list_order,update_ids=[])
									self.env['channel.operation'].post_feed_import_process(self,feed_res)
								pagination_info["import_order_last_page"] = i
								self.write({
									"pagination_info":pagination_info
								})
								self._cr.commit()
					else:
						i=0
						pagination_info["import_order_last_page"] = 1
						self.write({
							"pagination_info":pagination_info
						})
						self._cr.commit()
			context.update({'group_by':'state',
						})
			self.import_order_date = str(datetime.now().date())
			message +=  str(count)+" Order(s) Imported!"
			return self.display_message(message)
		except Exception as e:
			raise UserError(_("Error : "+str(e)))
