from odoo import fields, models

class MrpRoutingWorkcenter(models.Model):
    _inherit = "mrp.routing.workcenter"

    
    component_not_replaced = fields.Boolean(string="Component not replaced" ,
            help="if 'True' means any one component has rejected in this operation the whole product is rejected", default=False)
