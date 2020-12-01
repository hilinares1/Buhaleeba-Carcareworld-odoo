# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import except_orm, Warning, RedirectWarning
from datetime import datetime, date
#from datetime import date

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def nn_fill_date(self):
        self.statement_date = datetime.today()

