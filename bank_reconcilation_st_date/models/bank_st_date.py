# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import except_orm, Warning, RedirectWarning
from datetime import datetime, date
#from datetime import date

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.depends('statement_date')
    def nn_fill_date(self):
        # self.statement_date = datetime.today()
        bank_stmt_ids = self.env['bank.statement'].search([('statement_lines', '=', self.id)])
        for bnk_id in bank_stmt_ids:
            self.statement_date = bnk_id.date_to
