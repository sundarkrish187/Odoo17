from odoo import fields, models, api 

class LabelPrinter(models.Model):
    _name = 'btw.master'
    _description = 'BTW Master'





    product_type = fields.Selection(
            [('pmma', 'PMMA'),
             ('philic', 'PHILIC'),
              ('phobic', 'PHOBIC'),
              ('phobic_np', 'PHOBIC-NP')], string='product Type', required=True)
    department = fields.Selection(
            [('pouch', 'Pouch'),
             ('box', 'Box'),
              ('injector', 'Injector')], string='Department', required=True)
    model_no = fields.Many2one('product.attribute.value', string='Model', required=True, copy=False, domain="[('attribute_id.name', '=', 'Model_Name')]"  )  
    type_name = fields.Selection(
            [('local', 'Local'),
             ('export', 'Export')], string='Type Name', required=True)
    label_name = fields.Char(string='Label Name', required=True) 
    file_name = fields.Char(string='File Name', required=True, readonly=True, compute="_compute_file_name" )


    @api.depends('label_name')
    def _compute_display_name(self):
        for record in self:
            record.display_name = record.label_name or 'Unnamed'


    @api.depends('department','model_no','type_name','label_name')
    def _compute_file_name(self):  
        for record in self:       
            record.file_name = "_".join(filter(None, [
                        record.product_type,
                        record.department,
                        record.type_name,
                        record.label_name
                    ])) + ".btw"