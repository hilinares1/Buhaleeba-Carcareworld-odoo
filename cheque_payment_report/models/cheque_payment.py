from odoo import fields, models


class accountPaymentCus(models.Model):
    _inherit = "account.payment"

    user_id = fields.Many2one('res.users', default=lambda self: self.env.user)
    checked_by = fields.Char()
    approved_by = fields.Char()
    received_by = fields.Char()
    cheque_number = fields.Char(string="Cheque Number")
