from odoo import api, fields, models, SUPERUSER_ID, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import except_orm, ValidationError ,UserError

class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_asset = fields.Boolean(string='Is Asset Product')


class StockInventory(models.Model):
    _inherit = "stock.inventory"

    # rack_shelf_ids = fields.Many2many('stock.rack.shelf',string='Rack/Shelf ID', states={'draft': [('readonly', False)]})
    owner_ids = fields.Many2many('res.partner',string='Owner', states={'draft': [('readonly', False)]})

    def action_start(self):
        res = super(StockInventory,self).action_start()
        self.ensure_one()
        self._action_start()
        self._check_company()
        self.action_open_inventory_lines()
        return res

    def action_open_inventory_lines(self):
        self.ensure_one()
        action = {
            'type': 'ir.actions.act_window',
            'views': [(self.env.ref('stock.stock_inventory_line_tree2').id, 'tree')],
            'view_mode': 'tree',
            'name': _('Inventory Lines'),
            'res_model': 'stock.inventory.line',
        }
        context = {
            'default_is_editable': True,
            'default_inventory_id': self.id,
            'default_company_id': self.company_id.id,
        }
        # Define domains and context
        domain = [
            ('inventory_id', '=', self.id),
            ('location_id.usage', 'in', ['internal', 'transit'])
        ]
        if self.location_ids:
            context['default_location_id'] = self.location_ids[0].id
            if len(self.location_ids) == 1:
                if not self.location_ids[0].child_ids:
                    context['readonly_location_id'] = True

        if self.product_ids:
            if len(self.product_ids) == 1:
                context['default_product_id'] = self.product_ids[0].id

        if self.owner_ids:
            if len(self.owner_ids) == 1:
                context['default_partner_id'] = self.owner_ids[0].id

        # if self.rack_shelf_ids:
        #     if len(self.rack_shelf_ids) == 1:
        #         context['default_rack_shelf_id'] = self.rack_shelf_ids[0].id

        action['context'] = context
        action['domain'] = domain
        return action




    def _get_inventory_lines_values(self):
        # TDE CLEANME: is sql really necessary ? I don't think so

        locations = self.env['stock.location']
        if self.location_ids:
            locations = self.env['stock.location'].search([('id', 'child_of', self.location_ids.ids)])
        else:
            locations = self.env['stock.location'].search(
                [('company_id', '=', self.company_id.id), ('usage', 'in', ['internal', 'transit'])])
        domain = ' sq.location_id in %s AND sq.quantity != 0 AND pp.active'
        args = (tuple(locations.ids),)

        # shelfs = self.env['stock.rack.shelf']
        # if self.rack_shelf_id:
        #
        #     shelfs = self.env['stock.rack.shelf'].search([('id','in',self.rack_shelf_id.ids)])
        # else:
        #     shelfs = self.env['stock.rack.shelf'].search([('parent_id','=',self.parent_id.id)])
        #
        # args = (tuple(shelfs.ids),)
        vals = []
        Product = self.env['product.product']
        # Empty recordset of products available in stock_quants
        quant_products = self.env['product.product']

        # If inventory by company
        if self.company_id:
            domain += ' AND sq.company_id = %s'
            args += (self.company_id.id,)
        if self.product_ids:
            domain += ' AND sq.product_id in %s'
            args += (tuple(self.product_ids.ids),)

        if self.owner_ids:
            domain += ' AND sq.owner_id in %s'
            args += (tuple(self.owner_ids.ids),)

        # if self.rack_shelf_ids:
        #     domain += 'AND sq.rack_shelf_id in %s'
        #     args += (tuple(self.rack_shelf_ids.ids),)

        self.env['stock.quant'].flush(
            ['company_id', 'product_id', 'quantity', 'location_id', 'lot_id', 'package_id', 'owner_id'])
        self.env['product.product'].flush(['active'])
        self.env.cr.execute("""SELECT sq.product_id, sum(sq.quantity) as product_qty, sq.location_id, sq.lot_id as prod_lot_id, sq.package_id, sq.owner_id as partner_id,
               FROM stock_quant sq
               LEFT JOIN product_product pp
               ON pp.id = sq.product_id
               WHERE %s
               GROUP BY sq.product_id, sq.location_id, sq.lot_id, sq.package_id, sq.owner_id """ % domain, args)

        for product_data in self.env.cr.dictfetchall():
            product_data['company_id'] = self.company_id.id
            product_data['inventory_id'] = self.id
            # replace the None the dictionary by False, because falsy values are tested later on
            for void_field in [item[0] for item in product_data.items() if item[1] is None]:
                product_data[void_field] = False
            product_data['theoretical_qty'] = product_data['product_qty']
            if self.prefill_counted_quantity == 'zero':
                product_data['product_qty'] = 0
            if product_data['product_id']:
                product_data['product_uom_id'] = Product.browse(product_data['product_id']).uom_id.id
                quant_products |= Product.browse(product_data['product_id'])
            vals.append(product_data)
        return vals


# class InventoryLine(models.Model):
#     _inherit = "stock.inventory.line"

#     rack_id = fields.Many2one('stock.rack.shelf',string='Rack/Shelf ID')
                                    # domain=lambda self: self._domain_rack_shelf_ids())
    #
    # @api.model
    # def _domain_rack_shelf_ids(self):
    #     if self.env.context.get('active_model') == 'stock.inventory':
    #         inventory = self.env['stock.inventory'].browse(self.env.context.get('active_id'))
    #         if inventory.exists() and len(inventory.rack_shelf_id) > 1:
    #             return "[('id', 'in', %s)]" % inventory.rack_shelf_id.ids
    #     return "[ '|', ('parent_id', '=', False), ('parent_id', '=', parent_id)]"
