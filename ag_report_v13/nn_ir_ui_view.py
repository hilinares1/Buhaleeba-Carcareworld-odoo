# -*- coding: utf-8 -*-
from odoo import fields,models,api,_
from odoo.exceptions import UserError

# from openerp.tools.translate import _
class ir_ui_view(models.Model):
    _inherit = 'ir.ui.view'
   
    model =fields.Char('Model',required=True)
  
  #  @api.one
    def add_button(self):
        ir_model_data_obj = self.env['ir.model.data']
      
        name = self.name
        model = self.model
        org_name = name.split('.')
        #raise UserError(org_name)
        org_name = org_name[0]
        if org_name:
            ir_actions_report_xml_data = self.env['ir.actions.report'].search([('report_name', 'ilike', org_name),('model','=',model)],limit=1)
        else:
            ir_actions_report_xml_data = self.env['ir.actions.report'].search([('report_name', 'ilike', name),('model','=',model)],limit=1)
        
        report_name = ir_actions_report_xml_data.report_name
        #raise UserError(report_name)


        if report_name:
            words = []
            words = report_name.split('.')
            print 
            module_name = ''
            module_name = words[0]
            if name:
                print ("hai inside for loop")
                model_data_id = ir_model_data_obj.create({
                                'res_id':self.id,
                                'complete_name': name,
                                'name':name,
                                'model':'ir.ui.view',
                                'module':module_name
                            
                                })
                self.write({'model_data_id':model_data_id.id})
        else:
            raise Warning("No REport available")
        return True








































