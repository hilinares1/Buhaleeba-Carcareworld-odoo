# -*- coding: utf-8 -*-

from odoo import models, fields, api


class StockRackRef(models.Model):
    _name = 'stock.rack.shelf'

    name = fields.Char(
        string='Name',
        require=True,
    )
    code = fields.Char(
        string='Code',
        require=True,
    )
    parent_id = fields.Many2one(
        'stock.rack.shelf',
        index=True,
        ondelete='cascade',
    )

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
