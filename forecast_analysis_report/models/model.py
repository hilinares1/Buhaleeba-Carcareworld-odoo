from odoo import fields, models, api, tools
from datetime import date
from dateutil.relativedelta import relativedelta


class ForecastAnalysisReportWiz(models.TransientModel):
    _name = 'forecast.analysis.report.wiz'
    _description = 'forecast analysis report wiz'

    category_id = fields.Many2one('product.category')

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
        if self.category_id:
            categ_products = self.env['product.product'].search([('categ_id', '=', self.category_id.id)])

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
        purchase_query = """
               SELECT sum(p_o_l.product_qty) AS product_qty, p_o_l.product_id FROM purchase_order_line AS p_o_l
               JOIN purchase_order AS p_o ON p_o_l.order_id = p_o.id
               INNER JOIN stock_picking_type AS s_p_t ON p_o.picking_type_id = s_p_t.id
               INNER JOIN stock_picking AS s_p ON s_p_t.id = s_p.picking_type_id
               WHERE p_o.state IN ('purchase','done')
               AND s_p.state IN ('draft','waiting','confirmed','assigned')
               AND p_o.date_order >= %s
               AND p_o.date_order <= %s
               AND p_o_l.product_id in %s group by p_o_l.product_id"""

        params = date_befor, date_today, product_ids if product_ids else (0, 0, 0)
        self._cr.execute(sale_query, params)
        sol_query_obj = self._cr.dictfetchall()
        self._cr.execute(purchase_query, params)
        pol_query_obj = self._cr.dictfetchall()
        for obj in categ_products:
            sale_value = 0
            purchase_value = 0
            for sol_product in sol_query_obj:
                if sol_product['product_id'] == obj.id:
                    sale_value = sol_product['product_uom_qty']
            qty_available = obj.qty_available
            reordering_min_qty = obj.with_context({'from_date': date_befor, 'to_date': date_today}).reordering_min_qty
            for pol_product in pol_query_obj:
                if pol_product['product_id'] == obj.id:
                    purchase_value = pol_product['product_qty']
            suggested = sale_value - (qty_available + purchase_value + reordering_min_qty)
            vals = {

                'sales_qty': sale_value,
                'product_id': obj.id,
                'category_id': obj.categ_id.id,
                'on_hand': qty_available,
                'pending': purchase_value,
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
    category_id = fields.Many2one(
        'product.category', 'Product Category',
        help="Select category for the current product")
    sales_qty = fields.Float(string="Sales Qty")
    on_hand = fields.Float('On Hand')
    pending = fields.Float('Pending')
    min_stock = fields.Float('Min.Stock')
    suggested = fields.Float('Suggested ')
