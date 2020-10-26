from odoo import fields, models, api, tools
from datetime import date
from dateutil.relativedelta import relativedelta


class ForecastAnalysisReportWiz(models.TransientModel):
    _name = 'forecast.analysis.report.wiz'
    _description = 'forecast analysis report wiz'

    pr_category = fields.Many2one('product.categories', string="Product Category")
    sub_pr_category = fields.Many2one('product.categories', string="Sub-Category")
    pr_type = fields.Many2one('product.type', string="Product Type")
    sub_pr_type = fields.Many2one('product.type', string="Sub-Type")
    pr_brand = fields.Many2one('product.brand', string="Product Brand")

    duration = fields.Selection([('3moths', 'Last 3 months'),
                                 ('6moths', 'Last 6 months'),
                                 ('12moths', 'Last 12 months'),
                                 ('24moths', 'Last 24 months'),
                                 ('36moths', 'Last 36 months'),
                                 ], string='Duration', required=True, default='3moths')

    def compute_pr_date(self):
        if self.duration == '3moths':
            res = date.today() + relativedelta(months=-3)
        elif self.duration == '6moths':
            res = date.today() + relativedelta(months=-6)
        elif self.duration == '12moths':
            res = date.today() + relativedelta(months=-12)
        elif self.duration == '24moths':
            res = date.today() + relativedelta(months=-24)
        elif self.duration == '36moths':
            res = date.today() + relativedelta(months=-36)
        return res

    def print_report(self):
        self.env['forecast.analysis.report'].search([]).unlink()
        # filtered by category
        if self.pr_category and not self.sub_pr_category and not self.pr_type and not self.sub_pr_type and not self.pr_brand:
            categ_products = self.env['product.product'].search(
                [('pr_category', '=', self.pr_category.id)])
            print('//////////////////////////////////////////////////////',categ_products)

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
        date_befor = self.compute_pr_date()
        date_today = date.today()
        sale_query = """
               SELECT sum(s_o_l.product_uom_qty) AS product_uom_qty, s_o_l.product_id FROM sale_order_line AS s_o_l
               JOIN sale_order AS s_o ON s_o_l.order_id = s_o.id
               WHERE s_o.state IN ('sale','done')
               AND s_o.date_order >= %s
               AND s_o.date_order <= %s
               AND s_o_l.product_id in %s group by s_o_l.product_id"""
        # purchase_query = """
        #        SELECT sum(s_m.product_uom_qty) AS product_qty, s_m.product_id FROM stock_move AS s_m
        #        JOIN stock_picking AS s_p ON s_m.picking_id = s_p.id
        #        INNER JOIN stock_picking_type AS s_p_t ON s_p.picking_type_id = s_p_t.id
        #        WHERE s_p_t.code = 'incoming'
        #        AND s_p.state IN ('draft','waiting','confirmed','assigned')
        #        AND s_m.product_id in %s group by s_m.product_id"""

        params = date_befor, date_today, product_ids if product_ids else (0, 0, 0)
        param = product_ids
        self._cr.execute(sale_query, params)
        sol_query_obj = self._cr.dictfetchall()
        # self._cr.execute(purchase_query, param)
        # pol_query_obj = self._cr.dictfetchall()
        for obj in categ_products:
            sale_value = 0
            # purchase_value = 0
            for sol_product in sol_query_obj:
                if sol_product['product_id'] == obj.id:
                    sale_value = sol_product['product_uom_qty']
            qty_available = obj.qty_available
            reordering_min_qty = obj.with_context({'from_date': date_befor, 'to_date': date_today}).reordering_min_qty
            incoming_qty = obj.incoming_qty
            # for pol_product in pol_query_obj:
            #     if pol_product['product_id'] == obj.id:
            #         purchase_value = pol_product['product_qty']
            suggested = sale_value - (qty_available + incoming_qty + reordering_min_qty)
            vals = {
                'sales_qty': sale_value,
                'product_id': obj.id,
                'pr_category': obj.pr_category.id,
                'sub_pr_category': obj.sub_pr_category.id,
                'pr_brand': obj.pr_brand.id,
                'on_hand': qty_available,
                'pending': incoming_qty,
                'min_stock': reordering_min_qty,
                'suggested': suggested,
            }

            self.env['forecast.analysis.report'].create(vals)

        return {
            'name': 'Forecast Analysis Report',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'views': [(self.env.ref(
                'forecast_analysis_report.forecast_analysis_report_line_tree').id,
                       'tree'),
                      (False, 'form'),
                      (self.env.ref(
                          'forecast_analysis_report.view_forecast_analysis_pivot').id, 'pivot')],
            'res_model': 'forecast.analysis.report',
            'type': 'ir.actions.act_window',
            'target': 'current',
        }


class ForecastAnalysisReport(models.TransientModel):
    _name = 'forecast.analysis.report'
    _description = 'forecast analysis report'

    date = fields.Date('Date')
    product_id = fields.Many2one('product.product', 'Product')
    pr_category = fields.Many2one('product.categories', string="Product Category")
    sub_pr_category = fields.Many2one('product.categories', string="Sub-Category")
    pr_brand = fields.Many2one('product.brand', string="Product Brand")
    sales_qty = fields.Float(string="Sales Qty")
    on_hand = fields.Float('On Hand')
    pending = fields.Float('Pending')
    min_stock = fields.Float('Min.Stock')
    suggested = fields.Float('Suggested ')
