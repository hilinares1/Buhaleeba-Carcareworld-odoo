# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#    See LICENSE file for full copyright and licensing details.
##########H#########Y#########P#########N#########O#########S###################
import logging
_logger = logging.getLogger(__name__)
from odoo import api, fields, models
from odoo.exceptions import UserError


class ExportWoocommerceCategories(models.TransientModel):
    _inherit = "export.categories"

    def action_woocommerce_export_category(self):
        return self.export_button()

    def woocommerce_export_now(self, record, initial_record_id):
        return_list = [False, ""]
        channel = self._context.get('channel_id')
        woocommerce = self._context.get("woocommerce")
        with_product = self._context.get("with_product")
        if with_product:
            cat_mapped = self.env["channel.category.mappings"].search([
                ("channel_id","=",channel.id),
                ("odoo_category_id","=",record.id)
                ])
            if cat_mapped:
                return [True,{"id":cat_mapped.store_category_id}]
        cat_id = self.woocommerce_sync_categories(
            channel, woocommerce, record, initial_record_id, with_product)
        if cat_id:
            return_list = [True, {"id":cat_id}]
        return return_list

    def woocommerce_sync_categories(self, channel, woocommerce, record, initial_record_id, with_product):
        p_cat_id = 0
        res = ''
        parent_id = record.parent_id
        if parent_id.id:
            is_parent_mapped = self.env['channel.category.mappings'].search([
                ("channel_id", "=", channel.id),
                ("odoo_category_id", '=', parent_id.id)
            ])
            if not is_parent_mapped:
                p_cat_id = self.with_context({
                    'channel_id': channel,
                    'woocommerce': woocommerce,
                }).woocommerce_export_now(parent_id, initial_record_id)
                if p_cat_id[0]:
                    p_cat_id = p_cat_id[1].id
            else:
                p_cat_id = is_parent_mapped.store_category_id
        res = self.woocommerce_create_category(
            woocommerce, channel, record, initial_record_id, p_cat_id, with_product)
        return res

    def woocommerce_create_category(self, woocommerce, channel, record, initial_record_id, p_cat_id, with_product=False):
        returnid = False
        cat_name = record.name
        category_dict = {
            "name": cat_name,
            "parent": p_cat_id,
        }
        return_dict = woocommerce.post(
            'products/categories', category_dict).json()
        if 'message' in return_dict:
            _logger.info('Error in Creating Categories : ' +
                            str(return_dict['message']))
            return False
        returnid = return_dict.get("id")
        if record.id != initial_record_id:
            channel.create_category_mapping(record, returnid)
        return returnid 