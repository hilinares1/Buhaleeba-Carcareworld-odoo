from odoo import fields, models, api, tools
from datetime import date
from dateutil.relativedelta import relativedelta


class SlowMovingReportWiz(models.TransientModel):
    _name = 'slow.fast.moving.report.wiz'
    _description = 'slow moving report wiz'

    pr_category = fields.Many2one('product.categories', string="Product Category")
    sub_pr_category = fields.Many2one('product.categories', string="Sub-Category")
    pr_type = fields.Many2one('product.type', string="Product Type")
    sub_pr_type = fields.Many2one('product.type', string="Sub-Type")
    pr_brand = fields.Many2one('product.brand', string="Product Brand")

    from_date = fields.Date(required=True)
    to_date = fields.Date(required=True)

    def print_report(self):
        self.env['slow.fast.moving.report'].search([]).unlink()
        # filtered by category
        if self.pr_category and not self.sub_pr_category and not self.pr_type and not self.sub_pr_type and not self.pr_brand:
            categ_products = self.env['product.product'].search(
                [('pr_category', '=', self.pr_category.id)])

        # filtered by category and sub_pr_category
        elif self.pr_category and self.sub_pr_category and not self.pr_type and not self.sub_pr_type and not self.pr_brand:
            categ_products = self.env['product.product'].search(
                [('pr_category', '=', self.pr_category.id),
                 ('sub_pr_category', '=', self.sub_pr_category.id)])

        # filtered by category and pr_type
        elif self.pr_category and not self.sub_pr_category and self.pr_type and not self.sub_pr_type and not self.pr_brand:
            categ_products = self.env['product.product'].search(
                [('pr_category', '=', self.pr_category.id),
                 ('pr_type', '=', self.pr_type.id)
                 ])

        # filtered by category and sub_pr_type
        elif self.pr_category and not self.sub_pr_category and not self.pr_type and self.sub_pr_type and not self.pr_brand:
            categ_products = self.env['product.product'].search(
                [('pr_category', '=', self.pr_category.id),
                 ('sub_pr_type', '=', self.sub_pr_type.id)
                 ])
        # filtered by category and pr_brand
        elif self.pr_category and not self.sub_pr_category and not self.pr_type and not self.sub_pr_type and self.pr_brand:
            categ_products = self.env['product.product'].search(
                [('pr_category', '=', self.pr_category.id),
                 ('pr_brand', '=', self.pr_brand.id)
                 ])
        # filtered by sub_pr_category
        elif not self.pr_category and self.sub_pr_category and not self.pr_type and not self.sub_pr_type and not self.pr_brand:
            categ_products = self.env['product.product'].search(
                [('sub_pr_category', '=', self.sub_pr_category.id)])

        # filtered by sub_pr_category and pr_type
        elif not self.pr_category and self.sub_pr_category and self.pr_type and not self.sub_pr_type and not self.pr_brand:
            categ_products = self.env['product.product'].search(
                [('sub_pr_category', '=', self.sub_pr_category.id),
                 ('pr_type', '=', self.pr_type.id)
                 ])
        # filtered by sub_pr_category and sub_pr_type
        elif not self.pr_category and self.sub_pr_category and not self.pr_type and self.sub_pr_type and not self.pr_brand:
            categ_products = self.env['product.product'].search(
                [('sub_pr_category', '=', self.sub_pr_category.id),
                 ('sub_pr_type', '=', self.sub_pr_type.id)
                 ])
        # filtered by sub_pr_category and pr_brand
        elif not self.pr_category and self.sub_pr_category and not self.pr_type and not self.sub_pr_type and self.pr_brand:
            categ_products = self.env['product.product'].search(
                [('sub_pr_category', '=', self.sub_pr_category.id),
                 ('pr_brand', '=', self.pr_brand.id)
                 ])
        # filtered by pr_type
        elif not self.pr_category and not self.sub_pr_category and self.pr_type and not self.sub_pr_type and not self.pr_brand:
            categ_products = self.env['product.product'].search(
                [('pr_type', '=', self.pr_type.id)])

        # filtered by pr_type and sub_pr_type
        elif not self.pr_category and not self.sub_pr_category and self.pr_type and self.sub_pr_type and not self.pr_brand:
            categ_products = self.env['product.product'].search(
                [('pr_type', '=', self.pr_type.id),
                 ('sub_pr_type', '=', self.sub_pr_type.id)
                 ])
        # filtered by pr_type and pr_brand
        elif not self.pr_category and not self.sub_pr_category and self.pr_type and not self.sub_pr_type and self.pr_brand:
            categ_products = self.env['product.product'].search(
                [('pr_type', '=', self.pr_type.id),
                 ('pr_brand', '=', self.pr_brand.id)
                 ])
        # filtered by sub_pr_type
        elif not self.pr_category and not self.sub_pr_category and not self.pr_type and self.sub_pr_type and not self.pr_brand:
            categ_products = self.env['product.product'].search(
                [('sub_pr_type', '=', self.sub_pr_type.id)])
        # filtered by sub_pr_type and pr_brand
        elif not self.pr_category and not self.sub_pr_category and not self.pr_type and self.sub_pr_type and self.pr_brand:
            categ_products = self.env['product.product'].search(
                [('sub_pr_type', '=', self.sub_pr_type.id),
                 ('pr_brand', '=', self.pr_brand.id)
                 ])
        # filtered by pr_brand
        elif not self.pr_category and not self.sub_pr_category and not self.pr_type and not self.sub_pr_type and self.pr_brand:
            categ_products = self.env['product.product'].search(
                [('pr_brand', '=', self.pr_brand.id)])

        # filtered by pr_category and sub_pr_category and pr_type
        elif self.pr_category and self.sub_pr_category and self.pr_type and not self.sub_pr_type and not self.pr_brand:
            categ_products = self.env['product.product'].search(
                [('pr_category', '=', self.pr_category.id),
                 ('sub_pr_category', '=', self.sub_pr_category.id),
                 ('pr_type', '=', self.pr_type.id)
                 ])
        # filtered by pr_category and sub_pr_category and sub_pr_type
        elif self.pr_category and self.sub_pr_category and not self.pr_type and self.sub_pr_type and not self.pr_brand:
            categ_products = self.env['product.product'].search(
                [('pr_category', '=', self.pr_category.id),
                 ('sub_pr_category', '=', self.sub_pr_category.id),
                 ('sub_pr_type', '=', self.sub_pr_type.id)
                 ])
        # filtered by pr_category and sub_pr_category and pr_brand
        elif self.pr_category and self.sub_pr_category and not self.pr_type and not self.sub_pr_type and self.pr_brand:
            categ_products = self.env['product.product'].search(
                [('pr_category', '=', self.pr_category.id),
                 ('sub_pr_category', '=', self.sub_pr_category.id),
                 ('pr_brand', '=', self.pr_brand.id)
                 ])
        # filtered by sub_pr_category and pr_type and sub_pr_type
        elif not self.pr_category and self.sub_pr_category and self.pr_type and self.sub_pr_type and not self.pr_brand:
            categ_products = self.env['product.product'].search(
                [('sub_pr_category', '=', self.sub_pr_category.id),
                 ('pr_type', '=', self.pr_type.id),
                 ('sub_pr_type', '=', self.sub_pr_type.id)
                 ])
        # filtered by sub_pr_category and pr_type and sub_pr_type
        elif not self.pr_category and self.sub_pr_category and self.pr_type and not self.sub_pr_type and self.pr_brand:
            categ_products = self.env['product.product'].search(
                [('sub_pr_category', '=', self.sub_pr_category.id),
                 ('pr_type', '=', self.pr_type.id),
                 ('pr_brand', '=', self.pr_brand.id),
                 ])
        # filtered by pr_type and sub_pr_type and pr_brand
        elif not self.pr_category and not self.sub_pr_category and self.pr_type and self.sub_pr_type and self.pr_brand:
            categ_products = self.env['product.product'].search(
                [('pr_type', '=', self.pr_type.id),
                 ('sub_pr_type', '=', self.sub_pr_type.id),
                 ('pr_brand', '=', self.pr_brand.id)
                 ])
        # filtered by pr_category and sub_pr_category and pr_type and sub_pr_type
        elif self.pr_category and self.sub_pr_category and self.pr_type and self.sub_pr_type and not self.pr_brand:
            categ_products = self.env['product.product'].search(
                [('pr_category', '=', self.pr_category.id),
                 ('sub_pr_category', '=', self.sub_pr_category.id),
                 ('pr_type', '=', self.pr_type.id),
                 ('sub_pr_type', '=', self.sub_pr_type.id),
                 ])
        # filtered by pr_category and sub_pr_category and pr_type and pr_brand
        elif self.pr_category and self.sub_pr_category and self.pr_type and not self.sub_pr_type and self.pr_brand:
            categ_products = self.env['product.product'].search(
                [('pr_category', '=', self.pr_category.id),
                 ('sub_pr_category', '=', self.sub_pr_category.id),
                 ('pr_type', '=', self.pr_type.id),
                 ('pr_brand', '=', self.pr_brand.id),
                 ])
        # filtered by sub_pr_category and pr_type and sub_pr_type and pr_brand
        elif not self.pr_category and self.sub_pr_category and self.pr_type and self.sub_pr_type and self.pr_brand:
            categ_products = self.env['product.product'].search(
                [('sub_pr_category', '=', self.sub_pr_category.id),
                 ('pr_type', '=', self.pr_type.id),
                 ('sub_pr_type', '=', self.sub_pr_type.id),
                 ('pr_brand', '=', self.pr_brand.id),
                 ])
        # filtered by pr_category and sub_pr_category and pr_type and sub_pr_type and pr_brand
        elif self.pr_category and self.sub_pr_category and self.pr_type and self.sub_pr_type and self.pr_brand:
            categ_products = self.env['product.product'].search(
                [('pr_category', '=', self.pr_category.id),
                 ('sub_pr_category', '=', self.sub_pr_category.id),
                 ('pr_type', '=', self.pr_type.id),
                 ('sub_pr_type', '=', self.sub_pr_type.id),
                 ('pr_brand', '=', self.pr_brand.id),
                 ])
        else:
            categ_products = self.env['product.product'].search([])

        product_ids = tuple([pro_id.id for pro_id in categ_products])
        sale_query = """
                       SELECT sum(s_o_l.product_uom_qty) AS product_uom_qty, s_o_l.product_id FROM sale_order_line AS s_o_l
                       JOIN sale_order AS s_o ON s_o_l.order_id = s_o.id
                       WHERE s_o.state IN ('sale','done')
                       AND s_o.date_order >= %s
                       AND s_o.date_order <= %s
                       AND s_o_l.product_id in %s group by s_o_l.product_id"""

        params = self.from_date, self.to_date, product_ids if product_ids else (0, 0, 0)
        param = product_ids
        self._cr.execute(sale_query, params)
        sol_query_obj = self._cr.dictfetchall()
        # ///////////////////////////////////////////////////////////////////
        stock_move = """
                        SELECT sum(s_m.product_uom_qty) AS product_qty, s_m.product_id FROM stock_move AS s_m
                        JOIN stock_picking AS s_p ON s_m.picking_id = s_p.id
                        INNER JOIN stock_picking_type AS s_p_t ON s_p.picking_type_id = s_p_t.id
                        WHERE s_p_t.code = 'outgoing'
                        AND s_p.scheduled_date >= %s
                        AND s_p.scheduled_date <= %s
                        AND s_p.state = 'done'
                        AND s_m.product_id in %s group by s_m.product_id"""
        param_new = (date.today() + relativedelta(months=-3)), date.today(), product_ids if product_ids else (
            0, 0, 0)
        self._cr.execute(stock_move, param_new)
        move_query_obj = self._cr.dictfetchall()
        for obj in categ_products:
            qty_available = obj.qty_available

            sale = self.env['sale.order.line'].search(
                [('order_id.state', 'in', ['sale', 'done']),
                 ('product_id', '=', obj.id),
                 ('order_id.date_order', '>=', self.from_date),
                 ('order_id.date_order', '<=', self.to_date)], order='order_id', limit=1)


            sale_qty = 0
            for sol_product in sol_query_obj:
                if sol_product['product_id'] == obj.id:
                    sale_qty = sol_product['product_uom_qty']

            consumption = 0
            for mov_product in move_query_obj:
                if mov_product['product_id'] == obj.id:
                    consumption = mov_product['product_qty']

            re = (qty_available + consumption) * 100
            if re == 0:
                indications = consumption / 1
            else:
                indications = consumption / re

            if indications > 65:
                indication = 'fast'
            if indications <= 65 and indications > 35:
                indication = 'normal'
            elif indications <= 35 and indications > 10:
                indication = 'slow'
            elif indications <= 10:
                indication = 'dead'

            vals = {
                'product_id': obj.id,
                'pr_category': obj.pr_category.id,
                'sub_pr_category': obj.sub_pr_category.id,
                'pr_brand': obj.pr_brand.id,
                'on_hand': qty_available,
                'sale_qty': sale_qty,
                'sale_last_date': sale.order_id.date_order,
                'indication': indication,
            }

            self.env['slow.fast.moving.report'].create(vals)

        return {
            'name': 'Slow Fast Moving Report',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'views': [(self.env.ref(
                'slow_fast_moving_report.slow_fast_moving_report_line_tree').id,
                       'tree'),
                      (False, 'form'),
                      (self.env.ref(
                          'slow_fast_moving_report.view_slow_fast_moving_report_pivot').id, 'pivot')],
            'res_model': 'slow.fast.moving.report',
            'type': 'ir.actions.act_window',
            'target': 'current',
        }


class ForecastAnalysisReport(models.TransientModel):
    _name = 'slow.fast.moving.report'
    _description = 'slow fast moving report'

    sale_last_date = fields.Date('Last Sales')
    product_id = fields.Many2one('product.product', 'Product')
    pr_category = fields.Many2one('product.categories', string="Product Category")
    sub_pr_category = fields.Many2one('product.categories', string="Sub-Category")
    pr_brand = fields.Many2one('product.brand', string="Product Brand")
    sale_qty = fields.Float(string="Total Sales Qty")
    on_hand = fields.Float('Available Qty')
    indication = fields.Selection(
        string='Indication',
        selection=[('fast', 'Fast'),
                   ('normal', 'Normal/Reguler'),
                   ('slow', 'Slow'),
                   ('dead', 'Dead'),
                   ])
