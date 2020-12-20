from odoo import api, fields, models, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError



# class accountmoveinheirt(models.Model):
#     _inherit = 'account.move'

#     prepare = fields.Char('Prepared by')
#     approved = fields.Char('Approved by')


#     @api.model_create_multi
#     def create(self, vals_list):
#         res = super(accountmoveinheirt,self).create(vals_list)
#         user = self.env['res.users'].search([('id','=',self.env.user.id)])
#         # raise UserError(user.name)
#         res.prepare = user.name
#         return res 


#     def action_approve(self):
#         res = super(accountmoveinheirt,self).action_approve()
#         user = self.env['res.users'].search([('id','=',self.env.user.id)])
#         # raise UserError(user.name)
#         res['approved'] = user.name
#         return res 

class accountjournal(models.Model):
    _inherit = 'account.journal'

    voucher_name = fields.Char('Voucher Header')
