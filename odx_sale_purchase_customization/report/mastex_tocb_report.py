# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

#
# Please note that these reports are not multi-currency !!!
#

from odoo import api, fields, models, tools


class TocbReport(models.Model):
    _name = "tocb.report"
    _description = "Mastex TOCB Report"
    _auto = False
    _rec_name = 'date_order'
    _order = 'date_order desc'

    date_order = fields.Datetime('Order Date', readonly=True, help="Date on which this document has been created")
    name = fields.Char('Order Reference', readonly=True)
    partner_id = fields.Many2one('res.partner', 'Vendor', readonly=True)
    customer_id = fields.Many2one('res.partner', 'Customer', readonly=True)
    country_id = fields.Many2one('res.country', 'Partner Country', readonly=True)
    # bank = fields.Char('Bank', readonly=True)
    # lc_number = fields.Char('LC Number', readonly=True)
    shipment_date = fields.Datetime('Shipment  Date', readonly=True)
    bill_of_ladding_date = fields.Date('Bill Of Lading Date', readonly=True)
    date_arrival = fields.Date('Date Arrival', readonly=True)
    product_id = fields.Many2one('product.product', 'Product', readonly=True)
    purchase_price = fields.Float('Purchase Price', readonly=True)
    selling_price = fields.Float('Selling Price', readonly=True)
    product_uom = fields.Many2one('uom.uom', 'Reference Unit of Measure', required=False, readonly=True)
    qty = fields.Float('Qty', readonly=True)
    actual_qty = fields.Float('Actual Qty', readonly=True)
    no_of_packages = fields.Char('Number Of Packages', readonly=True)
    vendor_total = fields.Float('Vendor Total', readonly=True)
    customer_total = fields.Float('Customer Total', readonly=True)
    # customer_total_with_rate_diffrence = fields.Float('Customer Total With rate Diffrence', readonly=True)
    commission = fields.Float('Commission', readonly=True)
    notes = fields.Char('Notes', readonly=True)

    def _query(self, with_clause='', fields={}, groupby='', from_clause=''):
        with_ = ("WITH %s" % with_clause) if with_clause else ""

        select_ = """
            min(pl.id) as id,
            pl.product_id as product_id,
            pl.actual_qty as actual_qty,
            po.name as name,
            po.date_order as date_order,
            pl.product_qty as qty,
            pl.product_uom as product_uom,
            pl.price_subtotal as vendor_total,
            sl.price_subtotal as customer_total,
            po.shipment_date as shipment_date,
            po.partner_id as partner_id,
            po.customer_id as customer_id,
            p.product_tmpl_id,
            plc.no_of_packages as no_of_packages,
            plc.landing_date_etd as bill_of_ladding_date,
            plc.landing_date_eta as date_arrival,
            partner.country_id as country_id,
            pl.price_unit as purchase_price,
            sl.price_unit as selling_price,
            pl.commission as commission,
            po.notes as notes
        """

        for field in fields.values():
            select_ += field

        from_ = """
                sale_order_line sl
                left outer join purchase_order_line pl on (sl.purchase_order_line_id=pl.id)
                      left outer join purchase_order po on (pl.order_id=po.id)
                      left outer join sale_order so on (sl.order_id=so.id)
                      left outer join purchase_landing_cost plc on (pl.order_id=plc.purchase_id) 
                      left outer join res_partner partner on po.partner_id = partner.id
                        left join product_product p on (pl.product_id=p.id)
                            left join product_template t on (p.product_tmpl_id=t.id)
                    left join uom_uom u on (u.id=pl.product_uom)
                    left join uom_uom u2 on (u2.id=t.uom_id)
                %s
        """ % from_clause

        groupby_ = """
            po.name,
            po.partner_id,
            po.customer_id,
            partner.country_id,
            pl.product_id,
            pl.price_unit,
            pl.product_uom,
            pl.product_qty,
            po.date_order,
            plc.no_of_packages,
            pl.price_subtotal,
            sl.price_subtotal,
            sl.price_unit,
            pl.actual_qty,
            po.shipment_date,
            p.product_tmpl_id,
            plc.landing_date_etd,
            plc.landing_date_eta,
            pl.commission,
            po.notes %s
        """ % (groupby)

        return '%s (SELECT %s FROM %s WHERE pl.product_id IS NOT NULL GROUP BY %s)' % (with_, select_, from_, groupby_)

    def init(self):
        # self._table = sale_report
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (%s)""" % (self._table, self._query()))

