# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools
from odoo.tools.translate import _
from odoo.exceptions import UserError

class OdPeriodClosingWizard(models.TransientModel):
	_name = 'od.period.closing.wizard'
	_description = "Period Closing Wizard"

	date = fields.Date(string='Date', required=True)
	journal_id = fields.Many2one('account.journal', string='Journal', required=True)
	account_id = fields.Many2one('account.account', string='Account', required=True)
	line_id = fields.One2many('od.period.closing.line.wizard','wiz_id',string="Line Id")
	check_line_id = fields.Boolean(string='Check Line Id')


	def show_balance(self):
		if self.line_id:
			self.env['od.period.closing.line.wizard'].search([('wiz_id','=',self.id)]).unlink()
		cr=self.env.cr
		qry=('''SELECT account_code,account_id,balance  from od_period_closing_analysis ''')
		cr.execute(qry)
		result=cr.fetchall()
		for res in result:
			vals = {
					'account_code':res[0],
					'account_id':res[1],
					'balance':res[2],
					'wiz_id':self.id,
					}
			self.env['od.period.closing.line.wizard'].create(vals)
		self.check_line_id=True
		return {
			  'view_type': 'form',
			  "view_mode": 'form',
			  'res_model': 'od.period.closing.wizard',
			  'res_id': self.id,
			  'type': 'ir.actions.act_window',
			  'target': 'new'
			  }
	
	def generate_entries(self):
		if not self.line_id:
			raise UserError(_('No Entry To Generate!!')) 
		closing_report = self.env['od.period.closing.analysis'].search([])
		count=1
		move_pool = self.env['account.move']
		move_line = []
		total_debit = 0.0
		total_credit = 0.0
		
		for report in closing_report:
			credit = 0.0
			debit = 0.0
			account_id = report.account_id and report.account_id.id
			if report.balance >= 0:
				credit = round(report.balance,2)
			else:
				debit = -(round(report.balance,2))
			
			line = (0,0,{'account_id':account_id,'credit':credit,'debit':debit, 'name':'YearClosing'})  
			move_line.append(line)
			total_credit = round((total_credit+credit),2)
			total_debit = round((total_debit+debit),2)
			count = count+1
		
		debit_value=0.0
		credit_value=0.0
		if total_debit > total_credit:
			credit_value = round((total_debit-total_credit),2)
		else:
			debit_value = round((total_credit-total_debit),2)
		
		line_last=(0,0,{'account_id':self.account_id.id,'credit':credit_value ,'debit':debit_value, 'name':'YearClosing'})  
		move_line.append(line_last)
		move_vals = {'journal_id':self.journal_id.id,'date':self.date,'ref': 'YearClosing'} 		
		move_vals['line_ids'] = move_line
		move = move_pool.create(move_vals)


class OrchidPeriodClosingReport(models.Model):
	_name = 'od.period.closing.analysis'
	_description = "Period Closing Report"
	_auto = False

	account_code = fields.Char(string='Account Code')
	account_id = fields.Many2one('account.account', string='Account')
	balance = fields.Float(string='Balance')


	def init(self):
		cr = self.env.cr   
		tools.drop_view_if_exists(cr, 'od_period_closing_analysis')
		cr.execute("""
		
					CREATE or replace view od_period_closing_analysis as 
					(
						SELECT 
							mve.account_id as id,
							acc.code as account_code,
							SUM (mve.debit-mve.credit) AS balance,
							mve.account_id as account_id
						FROM account_move_line mve
						LEFT JOIN account_account acc ON mve.account_id = acc.id
						LEFT JOIN account_account_type actp ON acc.user_type_id = actp.id 
						WHERE 
							actp.include_initial_balance is FALSE 
						GROUP BY mve.account_id,acc.code
					)
				""")
class OdPeriodClosingLineWizard(models.TransientModel):
	_name = 'od.period.closing.line.wizard'
	_description = "Period Closing Line Wizard"

	wiz_id = fields.Many2one('od.period.closing.wizard',string="Wizard Id")
	account_code = fields.Char(string='Account Code')
	account_id = fields.Many2one('account.account', string='Account')
	balance = fields.Float(string='Balance')



