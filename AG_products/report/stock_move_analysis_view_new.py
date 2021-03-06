# -*- coding: utf-8 -*-
from odoo import fields,models,api,_
from odoo import tools
from odoo.exceptions import UserError, AccessError

class StockMoveAnalysisView(models.Model):
	_name = "stock.move.analysis.view"
	_description = "Stock Move Analysis"
	_auto = False
	_order = 'date'
	_rec_name = 'date'

	date = fields.Datetime(string="Date")
	move_id = fields.Many2one('stock.move',string='Stock  Move')
	product_id = fields.Many2one('product.product', string='Product')
	location = fields.Many2one('stock.location',string='Location')
	qty = fields.Float(string='Quantity')
	#value = fields.Float(string='Value')
	origin = fields.Char(string='Origin')
	warehouse_id = fields.Many2one('stock.warehouse',string='Warehouse')
	batch_name = fields.Char(string="Batch Name")
	source = fields.Many2one('stock.location', string='Source')
	destination = fields.Many2one('stock.location', string='Destination')
	#categ_id = fields.Many2one('product.category',string='Category')
	picking_name = fields.Char(string='Name')
	pr_category = fields.Many2one('product.categories', string="Product Category", domain=[('parent_id', '=', False)])
	sub_pr_category = fields.Many2one('product.categories', string="Sub-Category", domain=[('parent_id', '!=', False)])
	pr_type = fields.Many2one('product.type', string="Product Type", domain=[('parent_id', '=', False)])
	sub_pr_type = fields.Many2one('product.type', string="Sub-Type", domain=[('parent_id', '!=', False)])
	pr_brand = fields.Many2one('product.brand', string="Product Brand")
	# nn_pdt_group_id = fields.Many2one('nn.product.group',string='Group')
	# nn_pdt_sub_group_id = fields.Many2one('nn.product.sub.group',string='Sub Group')
	# nn_pdt_type_id = fields.Many2one('nn.product.type',string='Type')
	src_usage = fields.Char(string='Src Usage')
	des_usage = fields.Char(sring='Des Usage')
	move = fields.Char(string='Move')
	type = fields.Char(string='Operation Type')
	uom_id = fields.Many2one('uom.uom',string='UOM')
	partner_id = fields.Many2one('res.partner',string='Partner')
	# analytic_id =fields.Many2one('account.analytic.account',string="Project")
	# task_id = fields.Many2one('project.task', string="Task")
	price_unit = fields.Float(string='Unit Price')

	 

 
	@api.model
	def init(self):
		# cr = self.env.cr   
		tools.drop_view_if_exists(self._cr, 'stock_move_analysis_view')
		self._cr.execute("""
			CREATE OR REPLACE VIEW stock_move_analysis_view AS
			SELECT row_number() over() AS id,
			sm.date as date,
			sm.id as move_id,
			sm.product_id as product_id,
			
			sm.product_qty as qty,
			
			sm.origin as origin,
			sm.warehouse_id as warehouse_id,
			sml.lot_name as batch_name,
			sm.location_id as source,
			sm.location_dest_id as destination,
			sp.partner_id as partner_id,
			
			sm.price_unit as price_unit,
			-- pt.nn_pdt_group_id as nn_pdt_group_id,
			-- pt.nn_pdt_sub_group_id as nn_pdt_sub_group_id,
			-- pt.nn_pdt_type_id as nn_pdt_type_id,
			sm.location_id as location,
			pt.uom_id as uom_id,
			pt.pr_category as pr_category,
			pt.sub_pr_category as sub_pr_category,
			pt.pr_type as pr_type,
			pt.sub_pr_type as sub_pr_type,
			pt.pr_brand as pr_brand,
			sp.name as picking_name,
			srcloc.usage as src_usage,
			desloc.usage as des_usage,
			CASE
			WHEN sm.product_qty < 0::numeric THEN 'OUT'
			ELSE 'IN'
			END AS move,
			CASE
			/*WHEN srcloc.usage='internal' AND desloc.usage='internal' AND sm.product_qty>0 THEN 'Transfer In'*/
			WHEN srcloc.usage='internal' AND desloc.usage='customer' THEN 'Sales'
			WHEN srcloc.usage='customer' AND desloc.usage='internal' THEN 'Sales Return'
			WHEN srcloc.usage='supplier' AND desloc.usage='internal' THEN 'Purchase'
			WHEN srcloc.usage='internal' AND desloc.usage='supplier' THEN 'Purchase Return'
			
			WHEN srcloc.usage='internal' AND desloc.usage='inventory' THEN 'Inventory Adjustment'
			ELSE 'Unknown Type'
			END AS type
			FROM stock_move sm
			LEFT JOIN stock_location srcloc ON sm.location_id=srcloc.id
			LEFT JOIN stock_location desloc ON sm.location_dest_id=desloc.id
			LEFT JOIN stock_picking sp ON sm.picking_id=sp.id
			LEFT JOIN stock_move_line sml ON sm.id=sml.move_id
			INNER JOIN product_product pp ON sm.product_id=pp.id
			INNER JOIN product_template pt ON pp.product_tmpl_id=pt.id
			WHERE sm.state='done'
			GROUP BY sm.product_id,sm.date,sm.id,desloc.id,srcloc.id,
			sm.product_id,
			sm.product_qty,
			
			sm.origin,
			sm.warehouse_id,
			sml.lot_name,
			sm.location_id,
			sm.location_dest_id,
			sp.partner_id,
			
			pt.pr_category,
			pt.sub_pr_category,
			pt.pr_type,
			pt.sub_pr_type,
			pt.pr_brand,
			sp.name,
			-- pt.nn_pdt_group_id,
			-- pt.nn_pdt_sub_group_id,
			-- pt.nn_pdt_type_id,
			pt.uom_id,
			srcloc.usage,
			desloc.usage
					""")
