# -*- coding: utf-8 -*-
###################################################################################
#
#    Copyright (C) 2020 Odox SoftHub LLP(<www.odoxsofthub.com>)
#    Author: Albin Mathew(<albinmathew07@outlook.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###################################################################################
from odoo import fields, models, api, _
from odoo.exceptions import UserError
import base64
from datetime import date, timedelta, datetime


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"
    _description = "Purchase Order"

    @api.depends('order_line.price_total')
    def _amount_all(self):
        for order in self:
            amount_untaxed = amount_tax = total_commission = 0.0
            for line in order.order_line:
                amount_untaxed += line.price_subtotal
                total_commission += line.commission / 100 * line.price_subtotal
                amount_tax += line.price_tax
            order.update({
                'amount_untaxed': order.currency_id.round(amount_untaxed),
                'amount_tax': order.currency_id.round(amount_tax),
                'total_commission': order.currency_id.round(total_commission),
                'amount_total': amount_untaxed + amount_tax,
            })

    sale_order_id = fields.Many2one(comodel_name="sale.order", string="SO#", copy=False)
    customer_id = fields.Many2one(comodel_name='res.partner', string="Customer")

    # Bill of Lading
    landing_line_ids = fields.One2many(comodel_name='purchase.landing.cost', inverse_name='purchase_id',
                                       string="Bill Of Ladings")
    # Instructions
    colour_instructions = fields.Text(string="Colour Instructions")
    packing = fields.Text(string="Packing")
    face_stamp = fields.Html(string="Face Stamp on Paper and Booklet File")
    selvedge = fields.Html(string="Selvedge")
    shipping_mark = fields.Html(string="Shipping Mark")
    shipping_sample_book = fields.Text(string="Shippment Sample")
    notes = fields.Text(string="Notes")
    total_commission = fields.Monetary(string='Total Commission', store=True, readonly=True,
                                       compute='_amount_all', tracking=True)

    # Other details
    shipment_date = fields.Date(string="Shipment Date")
    destination_id = fields.Many2one(comodel_name='res.destination', string='Destination')
    marks = fields.Char(string="Marks")

    # Shipment details
    is_sample_customer = fields.Boolean(string='Sample received from customer')
    is_sample_vendor = fields.Boolean(string='Samples sent to supplier')
    is_vendor_sample_customer = fields.Boolean(string='Supplier initial Sample')
    is_sample_company = fields.Boolean(string='Supplier final samples')
    purchase_shipment_ids = fields.One2many('purchase.shipment', 'purchase_id', string="Shipment Details")

    # attachments
    attachment_ids = fields.One2many('ir.attachment', 'purchase_id', string='Attachment', copy=False)
    attachment_count = fields.Integer(compute='_compute_attachment_count')
    actual_grand_total = fields.Float(string="Net Total", compute='_compute_grand_total')
    actual_total = fields.Float(string="Actual Total", compute='_compute_grand_total')
    actual_commission = fields.Float(string="Actual Commission", compute='_compute_grand_total')

    @api.depends('order_line')
    def _compute_grand_total(self):
        grand_total = 0
        actual_total = 0
        actual_commission = 0
        for record in self:

            for line in self.order_line:
                grand_total = grand_total + line.actual_net_amount
                actual_total = actual_total +  line.actual_total_amount
                actual_commission = actual_commission + line.actual_com_amount
            record.actual_grand_total = grand_total
            record.actual_total = actual_total
            record.actual_commission = actual_commission

    @api.onchange('colour_instructions')
    def _onchange_colour_instructions(self):
        if self.sale_order_id:
            self.sale_order_id.colour_instructions = self.colour_instructions

    @api.onchange('packing')
    def _onchange_packing(self):
        if self.sale_order_id:
            self.sale_order_id.packing = self.packing

    @api.onchange('face_stamp')
    def _onchange_face_stamp(self):
        if self.sale_order_id:
            self.sale_order_id.face_stamp = self.face_stamp

    @api.onchange('selvedge')
    def _onchange_selvedge(self):
        if self.sale_order_id:
            self.sale_order_id.selvedge = self.selvedge

    @api.onchange('shipping_mark')
    def _onchange_shipping_mark(self):
        if self.sale_order_id:
            self.sale_order_id.shipping_mark = self.shipping_mark

    @api.onchange('shipping_sample_book')
    def _onchange_shipping_sample_book(self):
        if self.sale_order_id:
            self.sale_order_id.shipping_sample_book = self.shipping_sample_book

    @api.onchange('notes')
    def _onchange_notes(self):
        if self.sale_order_id:
            self.sale_order_id.notes = self.notes

    @api.onchange('shipment_date')
    def _onchange_shipment_date(self):
        if self.sale_order_id:
            self.sale_order_id.shipment_date = self.shipment_date

    @api.onchange('destination_id')
    def _onchange_destination_id(self):
        if self.sale_order_id and self.destination_id:
            self.sale_order_id.destination_id = self.destination_id.id

    def photos(self):
        return {
            'name': 'Photos',
            'view_type': 'form',
            'view_mode': 'kanban,tree,form',
            'res_model': 'ir.attachment',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'context': {'default_purchase_id': self.id,
                        'default_sale_id': self.sale_order_id.id if self.sale_order_id else ''},
            'domain': [('purchase_id', '=', self.id)]

        }

    @api.depends('attachment_ids')
    def _compute_attachment_count(self):
        for order in self:
            order.attachment_count = len(order.attachment_ids)

    def action_rfq_send(self):
        res = super(PurchaseOrder, self).action_rfq_send()
        result, extension = self.env.ref('odx_sale_purchase_customization.instruction_sheet_purchase').render_qweb_pdf(
            self.ids)
        result = base64.b64encode(result)
        report_name = 'Instruction.pdf'
        data_attach = {
            'name': report_name,
            'datas': result,
            'res_model': 'mail.compose.message',
            'res_id': 0,
            'type': 'binary',  # override default_type from context, possibly meant for another model!
        }
        attachment_id = self.env['ir.attachment'].create(data_attach)
        res['context']['default_extra_attachment_ids'] = [(6, 0, [attachment_id.id])]
        return res

    @api.onchange('purchase_shipment_ids')
    def _onchange_type(self):
        for record in self:
            record.is_sample_customer = False
            record.is_sample_vendor = False
            record.is_vendor_sample_customer = False
            record.is_sample_company = False
            if record.purchase_shipment_ids:
                for shipment in record.purchase_shipment_ids:
                    if shipment.type:
                        if shipment.type == 'sample_customer':
                            record.is_sample_customer = True
                        elif shipment.type == 'sample_vendor':
                            record.is_sample_vendor = True
                        elif shipment.type == 'vendor_sample_customer':
                            record.is_vendor_sample_customer = True
                        elif shipment.type == 'sample_company':
                            record.is_sample_company = True

    def button_confirm(self):
        """ inherited to create sale order,
         first check for an existing sale order for the corresponding PO
         if does not exist, create a new sale order"""
        for record in self:
            res = super(PurchaseOrder, self).button_confirm()
            if not record.sale_order_id and record.customer_id:
                sale_order_line_obj = self.env['sale.order.line']
                attachment_ids = []
                sale_order_obj = self.env['sale.order']
                for attchment in record.attachment_ids:
                    attachment_ids.append((0, 0, {
                        'name': attchment.name,
                        'datas': attchment.datas,
                        "description": attchment.description,
                        "mimetype": attchment.mimetype,
                        'index_content': attchment.index_content,
                        "create_uid": attchment.create_uid.id,
                    }))

                vals = {
                    "partner_id": record.customer_id.id,
                    "vendor_id": record.partner_id.id,
                    "purchase_order_id": record.id,
                    "attachment_ids": attachment_ids,
                    "colour_instructions": record.colour_instructions,
                    "packing": record.packing,
                    "name": record.name,
                    "face_stamp": record.face_stamp,
                    "selvedge": record.selvedge,
                    "shipping_mark": record.shipping_mark,
                    "shipping_sample_book": record.shipping_sample_book,
                    "notes": record.notes,
                    "shipment_date": record.shipment_date,
                    "destination_id": record.destination_id.id,
                    "currency_id": record.currency_id.id,
                }
                sale_order = sale_order_obj.create(vals)
                record.sale_order_id = sale_order.id
                for line in record.order_line:
                    taxes = line.product_id.taxes_id
                    fpos = record.fiscal_position_id
                    taxes_id = fpos.map_tax(taxes, line.product_id, record.partner_id) if fpos else taxes
                    if taxes_id:
                        taxes_id = taxes_id.filtered(lambda x: x.company_id.id == record.company_id.id)
                    sale_order_line = sale_order_line_obj.create({'product_id': line.product_id.id,
                                                                  'name': line.name,
                                                                  'tax_id': [(6, 0, taxes_id.ids)],
                                                                  'product_uom_qty': line.product_qty,
                                                                  "product_uom": line.product_uom.id,
                                                                  'price_unit': line.price_unit,
                                                                  "order_id": sale_order.id,
                                                                  # "discount": line.discount,
                                                                  "purchase_order_line_id": line.id,
                                                                  "actual_qty": line.actual_qty
                                                                  })
                    line.sale_order_line_id = sale_order_line.id

            return res

    def action_view_invoice(self):
        res = super(PurchaseOrder, self).action_view_invoice()
        res['context'].update({'default_ref': self.name, 'default_purchase_order_id': self.id,
                               'default_is_order_to_invoice':True},
                              )
        return res

    @api.model
    def create(self, values):
        """
        adding values to the name from sequence
        :param values:
        :return: new record id
        """
        if values.get('name', _('New')) == _('New'):
            values['name'] = self.env['ir.sequence'].next_by_code('order.reference',
                                                                  None) or _('New')
            values['marks'] = values['name']
            customer_code = ''
            if values.get('customer_id'):
                customer = self.env['res.partner'].browse(values.get('customer_id'))
                customer_code = customer.customer_code
            if values.get('marks'):
                marks_field = values.get('marks')
            else:
                marks_field = ' '

            values['marks'] = '%s %s %s' % (customer_code, values['name'], marks_field)
        return super(PurchaseOrder, self).create(values)

    def name_get(self):
        """adding PO to the name"""
        result = []
        for r in self:
            result.append((r.id, u"%s %s" % ('PO', r.name)))
        return result


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    actual_qty = fields.Float(string='ACTUAL QTY', required=True
                              , default=0.0, copy=False)
    sale_order_line_id = fields.Many2one("sale.order.line", string='Sale Order Line')
    commission = fields.Float('COMMISSION %')
    actual_net_amount = fields.Float(string='NET TOTAL', compute='_compute_actual_net')
    actual_com_amount = fields.Float("ACTUAL COMMISSION", compute='_compute_actual_com')
    total = fields.Float("Total", compute='_compute_amount')
    com_amount = fields.Float("COM AMT", compute='_compute_amount')
    price_subtotal = fields.Monetary(compute='_compute_amount', string='Subtotal', store=True)
    price_total = fields.Monetary(compute='_compute_amount', string='Total', store=True)
    price_tax = fields.Float(compute='_compute_amount', string='Tax', store=True)
    actual_total_amount = fields.Float(string='ACTUAL TOTAL', compute='_compute_actual_net')

    @api.depends('product_qty', 'price_unit', 'taxes_id', 'commission')
    def _compute_amount(self):
        for line in self:
            vals = line._prepare_compute_all_values()
            taxes = line.taxes_id.compute_all(
                vals['price_unit'],
                vals['currency_id'],
                vals['product_qty'],
                vals['product'],
                vals['partner'])
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'total': taxes['total_excluded'],
                'com_amount': (taxes['total_excluded'] * line.commission) / 100,
                'price_subtotal': taxes['total_excluded'] - ((taxes['total_excluded'] * line.commission) / 100),

            })

    @api.depends('actual_qty', 'price_unit', 'commission')
    def _compute_actual_com(self):
        for record in self:
            total = record.actual_qty * record.price_unit
            record.actual_com_amount = (total * record.commission) / 100

    @api.depends('actual_qty', 'price_unit', 'commission')
    def _compute_actual_net(self):
        for record in self:
            total = record.actual_qty * record.price_unit
            record.actual_total_amount = total
            record.actual_net_amount = record.actual_qty * record.price_unit - ((total * record.commission) / 100)

    def _prepare_account_move_line(self, move):
        res = super(PurchaseOrderLine, self)._prepare_account_move_line(move)

        res.update({'quantity': self.actual_qty,
                    'commission': self.commission,
                    'com_amount': self.actual_com_amount,
                    'total': self.actual_net_amount,
                    })
        return res

    @api.onchange('actual_qty')
    def _onchange_actual_qty(self):
        if self.sale_order_line_id:
            self.sale_order_line_id.actual_qty = self.actual_qty

    @api.model_create_multi
    def create(self, values):
        """
        Generates an error message when an additional line is created in PO, when the state
        is in purchase, done
        :param values:
        :return: new record
        """
        res = super(PurchaseOrderLine, self).create(values)
        states = ['purchase', 'done']
        if res.order_id.state in states:
            raise UserError(_('You can not create an additional purchase order line in a confirmed order '))
        return res


class LandingCost(models.Model):
    _name = 'purchase.landing.cost'
    _description = 'Purchase Landing Cost'

    name = fields.Char(string="B/L No", required=True)
    landing_date_etd = fields.Date(string='ETD', required=True)
    landing_date_eta = fields.Date(string='ETA', required=True)
    shipping_company_id = fields.Many2one('shipment.company', string='Shipping Line', required=True,
                                          )
    landing_attachment = fields.Binary(string='Document', attachment=True)
    landing_attachment_name = fields.Char(string='Document Name')
    purchase_id = fields.Many2one(comodel_name='purchase.order', string="Purchase Order", ondelete='cascade')
    no_of_packages = fields.Char(string='No Of Packages')
    destination = fields.Many2one(comodel_name='res.destination', string='Destination')
    marks = fields.Char(string="Marks")
    container_no = fields.Char(string="Container No")
    reference = fields.Char(string="Reference")
    status = fields.Selection([('in_transit', 'In Transit'), ('discharged', 'Discharged')], string='Status')

    @api.onchange('landing_date_etd','landing_date_eta')
    def _onchange_landing_date_etd(self):
        if self.landing_date_etd and self.landing_date_eta:
            if not self.landing_date_etd < self.landing_date_eta:
                raise UserError(_('ETD Cannot be greater than ETA '))
            if self.landing_date_etd <= date.today() <= self.landing_date_eta:
                self.status = 'in_transit'

        if self.landing_date_etd:
            if date.today() < self.landing_date_etd:
                self.status = False
        if self.landing_date_eta:
            if date.today() > self.landing_date_eta:
                self.status = 'discharged'

    def update_status(self):
        laddings = self.search([('status', '!=', 'discharged')])
        for ladding in laddings:
            if ladding.landing_date_eta:
                if date.today() >= ladding.landing_date_eta:
                    ladding.status = 'discharged'


class PurchaseShipment(models.Model):
    _name = 'purchase.shipment'

    shipment_to = fields.Many2one(comodel_name='shipment.destination', string="Shipment To")
    shipment_from = fields.Many2one(comodel_name='shipment.destination', string="Shipment From")
    from_date = fields.Date(string='Dispatch Date', copy=False, default=fields.Date.today(), store=True)
    to_date = fields.Date(string='Expected Delivery Date', copy=False, store=True)
    reference = fields.Char(string="Reference")
    description = fields.Char(string="Description")
    status = fields.Selection([('sent', 'Sent'), ('received', 'Received'), ('delivered', 'Delivered'),
                               ('cancel', 'Canceled')],
                              string='Status')
    type = fields.Selection([('sample_customer', 'Receive sample from customer'),
                             ('sample_vendor', 'Sent sample to vendor'),
                             ('vendor_sample_customer', 'Sent First Sample'),
                             ('sample_company', ' Sent Final Sample'),
                             ('others', ' Others')],
                            string='Type')
    attachment = fields.Binary(string="Files", attachment=True)
    attachment_name = fields.Char(string="File Name")
    purchase_id = fields.Many2one('purchase.order', string="purchase Order", ondelete='cascade')


class ShippingDestination(models.Model):
    _name = 'shipment.destination'
    _description = 'Shipping Destination'

    name = fields.Char("Name", required=True)


class ShippingCompany(models.Model):
    _name = 'shipment.company'
    _description = 'Shipping Company'

    name = fields.Char("Name", required=True)
