# -*- coding: utf-8 -*-
##############################################################################
# Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>
##############################################################################
from odoo import api,fields,models
from logging import getLogger

_logger = getLogger(__name__)


class StockMove(models.Model):
	_inherit = 'stock.move'

	def _action_done(self, **kwargs):
		"""
			Makes the move done and if all moves are done,it will finish the picking.
			@return:
		"""
		context = self.env.context.copy() or {}
		super(StockMove,self)._action_done(**kwargs)

		context['stock_operation'] = '_action_done'
		self.with_context(context).post_operation()
		return True

	def _action_confirm(self, *args, **kwargs):
		""" Confirms stock move or put it in waiting if it's linked to another move.
		"""
		res = super(StockMove, self)._action_confirm(*args, **kwargs)
		ctx = dict(self._context or {})
		ctx['stock_operation'] = '_action_confirm'
		res.with_context(ctx).post_operation()
		return res

	def _action_cancel(self, *args, **kwargs):
		ctx = dict(self._context or {})
		ctx['action_cancel'] = True
		ctx['stock_operation'] = '_action_cancel'

		check = False
		for obj in self:
			if obj.state == "cancel":
				check = True
		res = super(StockMove, self)._action_cancel(*args, **kwargs)
		if not check:
			self.with_context(ctx).post_operation()
		return res

	def post_operation(self):
		ctx = dict(self._context or {})
		channel_ids = self.env['multi.channel.sale'].search([]).ids

		if '_action_done' == ctx['stock_operation']:
			todo = [move.id for move in self if move.state == 'draft']
			if todo:
				ids = self.action_confirm(todo)
		ids = self
		for data in ids:
			# data = self.browse(id.id)
			erp_product_id = data.product_id.id
			flag = 1  # means there is some origin.
			if (data.origin != False) and data.picking_type_id.code not in ['incoming']:
				# Check if origin is 'Sale' and channel is available,no need to update
				# quantity on this particular channel.
				sale_id = self.env['sale.order'].search([('name','=',data.origin)])
				if sale_id:
					channel_id = sale_id.channel_mapping_ids.channel_id
					def_location = channel_id.location_id.id
					if channel_id and channel_id.id in channel_ids:
						channel_ids.remove(channel_id.id)
					flag = 0 # no need to update quantity on this channel id,update on others channels.
			else:
				flag = 2  # no origin.

			if flag == 1:
				if data.picking_type_id:
					check_pos = self.env['ir.model'].search([('model','=','pos.order')])
					if check_pos:
						pos_order_data = self.env['pos.order'].search(
							[('name','=',data.origin)]
						)
						if pos_order_data:
							lines = pos_order_data[0].lines
							for line in lines:
								get_line_data = self.env['pos.order.line'].search(
									[
										('product_id','=',erp_product_id),
										('id','=',line.id)
									]
								)
								if get_line_data:
									data.product_qty = get_line_data[0].qty
			if channel_ids:
				self.multichannel_sync_quantity(
					{
						'product_id'      : erp_product_id,
						'location_dest_id': data.location_dest_id.id,
						'product_qty'     : data.product_qty,
						'channel_ids'     : channel_ids,
						'source_loc_id'   : data.location_id.id,
					}
				)

	def multichannel_sync_quantity(self,pick_details):
		"""
			Method to be overridden by the multichannel modules to provide real time stock update feature
		"""
		channel_list = self._context.get('channel_list')
		if channel_list:
			variant     = self.env['product.product'].browse(pick_details.get('product_id'))
			for mapping in variant.channel_mapping_ids:
				instance = mapping.channel_id
				channel  = instance.channel
				if channel in channel_list:
					location_id = instance.location_id.id
					if instance.auto_sync_stock:
						if pick_details.get('source_loc_id') == location_id or \
							pick_details.get('location_dest_id') == location_id:
							qty = instance.with_context(location=location_id).get_quantity(variant)
						else:
							break
						if hasattr(instance,'sync_quantity_%s'%channel):
							if not getattr(instance,'sync_quantity_%s'%channel)(mapping,qty):
								_logger.error('Failed to sync stock to %s',channel)
						else:
							_logger.warn('%r: stock not synchronized.',channel)
		else:
			_logger.warn('Error in use of StockMove class : use of sync_quantity_(*channel) function to sync stock from Odoo to Channel')
		return True
