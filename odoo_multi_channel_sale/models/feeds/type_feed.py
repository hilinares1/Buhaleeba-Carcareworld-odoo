# -*- coding: utf-8 -*-
##############################################################################
# Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>
##############################################################################
from odoo import api, fields, models
from odoo.addons.odoo_multi_channel_sale.tools import extract_list as EL

from logging import getLogger
_logger = getLogger(__name__)


class TypeFeed(models.Model):
    _name = 'type.feed'
    _inherit = 'wk.feed'
    _description = 'type Feed'

    description = fields.Text('Description')
    parent_id = fields.Char('Store Parent ID')
    leaf_category = fields.Boolean('Leaf Category')

    @api.model
    def _create_feeds(self, category_data_list):
        success_ids, error_ids = [], []
        self = self.contextualize_feeds('type')
        for category_data in category_data_list:
            feed = self._create_feed(category_data)
            if feed:
                self += feed
                success_ids.append(category_data.get('store_id'))
            else:
                error_ids.append(category_data.get('store_id'))
        return success_ids, error_ids, self

    def _create_feed(self, category_data):
        channel_id = category_data.get('channel_id')
        store_id = str(category_data.get('store_id'))
        feed_id = self._context.get('type_feeds').get(
            channel_id, {}).get(store_id)
        try:
            if feed_id:
                feed = self.browse(feed_id)
                category_data.update(state='draft')
                feed.write(category_data)
            else:
                feed = self.create(category_data)
        except Exception as e:
            _logger.error(
                "Failed to create feed for Collection: "
                f"{category_data.get('store_id')}"
                f" Due to: {e.args[0]}"
            )
        else:
            return feed

    @api.model
    def get_channel_specific_type_vals(self, channel_id, vals):
        if hasattr(self, 'get_%s_specific_categ_vals' % channel_id.channel):
            return getattr(
                self, 'get_%s_specific_categ_vals' % channel_id.channel
            )(channel_id, vals)
        return vals

    def import_type(self, channel_id):
        self.ensure_one()
        message = ""
        update_id = None
        create_id = None
        state = 'done'

        vals = EL(self.read(self.get_type_fields()))
        vals = self.get_channel_specific_type_vals(channel_id, vals)
        store_id = vals.pop('store_id')

        if not vals.get('name'):
            message += "<br/>Type without name can't evaluated"
            state = 'error'
        if not store_id:
            message += "<br/>Type without store ID can't evaluated"
            state = 'error'

        parent_id = vals.pop('parent_id')
        if parent_id:
            res = self.get_type_id(parent_id, channel_id)
            res_parent_id = res.get('type_id')
            if res_parent_id:
                vals['parent_id'] = res_parent_id
            else:
                _logger.error('#CategError1 %r' % res)
                state = 'error'
        vals.pop('description', None)
        vals.pop('website_message_ids', '')
        vals.pop('message_follower_ids', '')

        match = self._context.get('ctype_mappings').get(
            channel_id.id, {}).get(self.store_id)
        if match:
            match = self.env['channel.type.mappings'].browse(match)
            if state == 'done':
                update_id = match
                try:
                    match.category_name.write(vals)
                    message += '<br/> type %s successfully updated' % (
                        vals.get('name', ''))
                except Exception as e:
                    _logger.error('#CategError2 %r', e)
                    message += '<br/>%s' % (e)
                    state = 'error'
            elif state == 'error':
                message += '<br/>Error while type update.'
        else:
            if state == 'done':
                try:
                    erp_id = self.env['product.type'].create(vals)
                    create_id = channel_id.create_type_mapping(
                        erp_id, store_id, self.leaf_category
                    )
                    message += '<br/> Category %s Successfully Evaluate' % (
                        vals.get('name', ''))
                except Exception as e:
                    _logger.error('#CategError3 %r', e)
                    message += '<br/>%s' % (e)
                    state = 'error'

        self.set_feed_state(state=state)
        self.message = "%s <br/> %s" % (self.message, message)
        return dict(
            create_id=create_id,
            update_id=update_id,
            message=message
        )

    def import_items(self):
        self = self.contextualize_feeds(
            'type', self.mapped('channel_id').ids)
        self = self.contextualize_mappings(
            'type', self.mapped('channel_id').ids)
        update_ids = []
        create_ids = []
        message = ''
        context = self._context.copy() or {}
        for record in self:
            sync_vals = dict(
                status='error',
                action_on='type',
                action_type='import',
            )
            channel_id = record.channel_id
            res = record.with_context(**context).import_type(channel_id)
            msz = res.get('message', '')
            message += msz

            update_id = res.get('update_id')
            if update_id:
                update_ids.append(update_id)
            create_id = res.get('create_id')
            if create_id:
                create_ids.append(create_id)
            mapping_id = update_id or create_id
            if mapping_id:
                mapping_vals = mapping_id.read(
                    {'store_type_id', 'odoo_type_id'})[0]
                sync_vals['status'] = 'success'
                sync_vals['ecomstore_refrence'] = mapping_vals['store_type_id']
                sync_vals['odoo_id'] = mapping_vals['odoo_type_id']
                context.get('type_mappings', {}).setdefault(channel_id.id, {})[
                    sync_vals['ecomstore_refrence']] = mapping_vals['id']
            sync_vals['summary'] = msz
            channel_id._create_sync(sync_vals)
        if self._context.get('get_mapping_ids'):
            return dict(
                update_ids=update_ids,
                create_ids=create_ids,
            )
        message = self.get_feed_result(feed_type='type')
        return self.env['multi.channel.sale'].display_message(message)
