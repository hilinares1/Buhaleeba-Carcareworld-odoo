# -*- coding: utf-8 -*-

from odoo import models, fields,api

from odoo.exceptions import except_orm, ValidationError ,UserError


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    is_landed_costs_line = fields.Boolean(
        string='Landed Costs',related='product_id.landed_cost_ok',store=True
    )

    # @api.onchange('product_id')
    # def get_landed_cost(self):
    #     for rec in self:
    #         if rec.product_id:
    #             rec.is_landed_costs_line = rec.product_id.landed_cost_ok
    #         else:
    #             rec.is_landed_costs_line = False

    def _prepare_account_move_line(self, move):
        res = super(PurchaseOrderLine, self)._prepare_account_move_line(move)
        res.update({
            'is_landed_costs_line': self.is_landed_costs_line,
        })
        return res

class StockPicking(models.Model):
    _inherit = "stock.picking"

    def create(self,vals):
        res = super(StockPicking,self).create(vals)
        if res.classification == 'overseas':
            pur = self.env['purchase.order'].search([('name','=',res.origin)])
            if pur:
                product = []
                for line in pur:
                    for lines in line.order_line:
                        if lines.is_landed_costs_line == True:
                            prod = lines.product_id.id
                            if lines.product_id.property_account_expense_id:
                                account = lines.product_id.property_account_expense_id.id
                            else:
                                raise UserError('Please set the expense account for %s'%(lines.product_id.name))
                            if line.currency_id.id == line.company_id.currency_id.id:
                                cost = lines.price_subtotal
                            else:
                                cost = abs(lines.price_subtotal) * (1/line.currency_rate)
                            pro = {
                                'product_id':prod,
                                'price_unit':cost,
                                'split_method':'equal',
                                'account_id':account
                            }
                            product.append((0,0,pro))
                if product:
                    vals = {
                        'pick':res.id,
                        'flag':1,
                        'picking_ids':[(6,0, [res.id])],
                        'cost_lines':product
                    }
                    self.env['stock.landed.cost'].create(vals)
        return res




# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
