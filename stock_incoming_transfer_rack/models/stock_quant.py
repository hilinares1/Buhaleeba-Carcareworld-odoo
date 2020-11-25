# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.osv import expression


class StockQuant(models.Model):
    _inherit = 'stock.quant'
    
    rack_shelf_id = fields.Many2one(
        'stock.rack.shelf',
        string='Rack / Shelf',
    )#SMA13

    def name_get(self):
        if not self._context.get('is_custom_rack_shelf'):
            return super(StockQuant, self).name_get()
        quant_lst = []
        for quant in self:
            quant_lst.append((quant.id, quant.product_id.display_name + (' - ' + quant.rack_shelf_id.name_get()[0][1] if quant.rack_shelf_id else '')))
        return quant_lst

    #@Fully Override
    @api.model
    def _get_available_quantity(self, product_id, location_id, lot_id=None, package_id=None, owner_id=None, strict=False, allow_negative=False, rack_shelf_id=False, ml_stock_quant=False):
        """ Return the available quantity, i.e. the sum of `quantity` minus the sum of
        `reserved_quantity`, for the set of quants sharing the combination of `product_id,
        location_id` if `strict` is set to False or sharing the *exact same characteristics*
        otherwise.
        This method is called in the following usecases:
            - when a stock move checks its availability
            - when a stock move actually assign
            - when editing a move line, to check if the new value is forced or not
            - when validating a move line with some forced values and have to potentially unlink an
              equivalent move line in another picking
        In the two first usecases, `strict` should be set to `False`, as we don't know what exact
        quants we'll reserve, and the characteristics are meaningless in this context.
        In the last ones, `strict` should be set to `True`, as we work on a specific set of
        characteristics.

        :return: available quantity as a float
        """
        if not rack_shelf_id and not ml_stock_quant:#SMA13
            return super(StockQuant, self)._get_available_quantity(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=strict, allow_negative=allow_negative)
        self = self.sudo()
        quants = self._gather(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=strict, rack_shelf_id=rack_shelf_id, ml_stock_quant=ml_stock_quant)#SMA13
        rounding = product_id.uom_id.rounding
        if product_id.tracking == 'none':
            available_quantity = sum(quants.mapped('quantity')) - sum(quants.mapped('reserved_quantity'))
            if allow_negative:
                return available_quantity
            else:
                return available_quantity if float_compare(available_quantity, 0.0, precision_rounding=rounding) >= 0.0 else 0.0
        else:
            availaible_quantities = {lot_id: 0.0 for lot_id in list(set(quants.mapped('lot_id'))) + ['untracked']}
            for quant in quants:
                if not quant.lot_id:
                    availaible_quantities['untracked'] += quant.quantity - quant.reserved_quantity
                else:
                    availaible_quantities[quant.lot_id] += quant.quantity - quant.reserved_quantity
            if allow_negative:
                return sum(availaible_quantities.values())
            else:
                return sum([available_quantity for available_quantity in availaible_quantities.values() if float_compare(available_quantity, 0, precision_rounding=rounding) > 0])
    
    
    #@Fully Override
    @api.model
    def _update_available_quantity(self, product_id, location_id, quantity, lot_id=None, package_id=None, owner_id=None, in_date=None, rack_shelf_id=False, ml_stock_quant=False):
        """ Increase or decrease `reserved_quantity` of a set of quants for a given set of
        product_id/location_id/lot_id/package_id/owner_id.

        :param product_id:
        :param location_id:
        :param quantity:
        :param lot_id:
        :param package_id:
        :param owner_id:
        :param datetime in_date: Should only be passed when calls to this method are done in
                                 order to move a quant. When creating a tracked quant, the
                                 current datetime will be used.
        :return: tuple (available_quantity, in_date as a datetime)
        """
        if not rack_shelf_id and not ml_stock_quant:#SMA13
            return super(StockQuant, self)._update_available_quantity(product_id, location_id, quantity, lot_id=lot_id, package_id=package_id, owner_id=owner_id, in_date=in_date)
        self = self.sudo()
        quants = self._gather(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=True, rack_shelf_id=rack_shelf_id, ml_stock_quant=ml_stock_quant)#SMA13
        incoming_dates = [d for d in quants.mapped('in_date') if d]
        incoming_dates = [fields.Datetime.from_string(incoming_date) for incoming_date in incoming_dates]
        if in_date:
            incoming_dates += [in_date]
        # If multiple incoming dates are available for a given lot_id/package_id/owner_id, we
        # consider only the oldest one as being relevant.
        if incoming_dates:
            in_date = fields.Datetime.to_string(min(incoming_dates))
        else:
            in_date = fields.Datetime.now()

        for quant in quants:
            try:
                with self._cr.savepoint():
                    self._cr.execute("SELECT 1 FROM stock_quant WHERE id = %s FOR UPDATE NOWAIT", [quant.id], log_exceptions=False)
                    quant.write({
                        'quantity': quant.quantity + quantity,
                        'in_date': in_date,
                    })
                    break
            except OperationalError as e:
                if e.pgcode == '55P03':  # could not obtain the lock
                    continue
                else:
                    raise
        else:
            self.create({
                'product_id': product_id.id,
                'location_id': location_id.id,
                'quantity': quantity,
                'lot_id': lot_id and lot_id.id,
                'package_id': package_id and package_id.id,
                'owner_id': owner_id and owner_id.id,
                'in_date': in_date,
                'rack_shelf_id': rack_shelf_id,
            })#SMA13
        return self._get_available_quantity(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=False, allow_negative=True, rack_shelf_id=rack_shelf_id, ml_stock_quant=ml_stock_quant), fields.Datetime.from_string(in_date)#SMA13

    #@Fully Override
    def _gather(self, product_id, location_id, lot_id=None, package_id=None, owner_id=None, strict=False, rack_shelf_id=False, ml_stock_quant=False):
        if rack_shelf_id or ml_stock_quant:
            self.env['stock.quant'].flush(['location_id', 'owner_id', 'package_id', 'lot_id', 'product_id'])
            self.env['product.product'].flush(['virtual_available'])
            removal_strategy = self._get_removal_strategy(product_id, location_id)
            removal_strategy_order = self._get_removal_strategy_order(removal_strategy)
            domain = [
                ('product_id', '=', product_id.id),
#                ('rack_shelf_id', '=', rack_shelf_id),#CUSTOM
            ]
            if rack_shelf_id:#SMA13
                domain = expression.AND([[('rack_shelf_id', '=', rack_shelf_id)], domain])
            if ml_stock_quant:#SMA13
                domain = expression.AND([[('id', '=', ml_stock_quant.id)], domain])
            if not strict:
                if lot_id:
                    domain = expression.AND([[('lot_id', '=', lot_id.id)], domain])
                if package_id:
                    domain = expression.AND([[('package_id', '=', package_id.id)], domain])
                if owner_id:
                    domain = expression.AND([[('owner_id', '=', owner_id.id)], domain])
                domain = expression.AND([[('location_id', 'child_of', location_id.id)], domain])
            else:
                domain = expression.AND([[('lot_id', '=', lot_id and lot_id.id or False)], domain])
                domain = expression.AND([[('package_id', '=', package_id and package_id.id or False)], domain])
                domain = expression.AND([[('owner_id', '=', owner_id and owner_id.id or False)], domain])
                domain = expression.AND([[('location_id', '=', location_id.id)], domain])

            # Copy code of _search for special NULLS FIRST/LAST order
            self.check_access_rights('read')
            query = self._where_calc(domain)
            self._apply_ir_rules(query, 'read')
            from_clause, where_clause, where_clause_params = query.get_sql()
            where_str = where_clause and (" WHERE %s" % where_clause) or ''
            query_str = 'SELECT "%s".id FROM ' % self._table + from_clause + where_str + " ORDER BY "+ removal_strategy_order
            
            self._cr.execute(query_str, where_clause_params)
            res = self._cr.fetchall()
            # No uniquify list necessary as auto_join is not applied anyways...
            return self.with_context(rack_shelf_ids=self._context.get("rack_shelf_ids")).browse([x[0] for x in res])
        return super(StockQuant, self)._gather( product_id, location_id, lot_id, package_id, owner_id, strict)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
