from odoo import api, fields, models, _

class PickingType(models.Model):
    _inherit = 'stock.picking.type'

    is_pmma_production_operation = fields.Boolean(string="PMMA Production Operation" ,
            help="To produce multiple lot number in one MO")
    
    is_pmma_tumbling_operation = fields.Boolean(string="PMMA Tumbling Operation" ,
            help="To assign multiple raw Lot Number ")