from  odoo import models, fields, api


class MailComposer(models.TransientModel):
    _inherit = 'mail.compose.message'

    extra_attachment_ids = fields.Many2many(
        'ir.attachment', 'mail_compose_message_ir_extra_attachments_rel',
        'wizard_id', 'attachment_id', 'Attachments')

    def onchange_template_id(self, template_id, composition_mode, model, res_id):
        result = super(MailComposer, self).onchange_template_id(template_id, composition_mode, model, res_id)
        if result.get('value') and result.get('value').get('attachment_ids'):
            attachment_list = result.get('value').get('attachment_ids')[0][2]
            if self.extra_attachment_ids:
                attachment_list += self.extra_attachment_ids.ids
        return result

