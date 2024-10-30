
from odoo import fields, models
from odoo.addons import decimal_precision as dp

class report(models.Model):
    _name ='workorder.resourcesnew'

    def _get_visible_employee(self):
        current_user = self.env.user
        current_company= self.env.company
        result = self.env['hr.employee'].search([('user_id', '=', current_user.id)])
        lines = self.env['hr.employee'].search(['&',('department_id', '=', result.department_id.id),('company_id', '=',current_company.id )])
        #domain =[('id', '=', -1)]
        employee_list=[]
        for line in lines:
            employee_list.append(line.id)
        if employee_list:
            domain =[('id', 'in', employee_list)]
            return domain
        #return domain
    
    
    def _get_visible_material(self):    
     resource_list=[]
     result = self.env['resource.resource'].search([('resource_type', '=', 'material')])
     for res in result:
        resource_list.append(res.id)
     if resource_list:
      domain =[('id', 'in', resource_list)]
      return domain  
    
    employeename = fields.Many2one('hr.employee', string="Employee Name", domain=_get_visible_employee)
    machinename = fields.Many2one('resource.resource',string="Machine Name",domain=_get_visible_material)  
    total_product_qty = fields.Float(string="Quantity",digits=dp.get_precision('Unit of Measure'))  
    workorderId= fields.Many2one('mrp.workorder')