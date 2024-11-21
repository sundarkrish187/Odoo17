from odoo import models, fields, api
from odoo.exceptions import UserError

class MrpProductionBatchLine(models.Model):
    _name = 'mrp.production.batch.line'
    _description = 'Batch Line for Manufacturing Order'

    production_id = fields.Many2one('mrp.production', string="Manufacturing Order", required=True, ondelete="cascade", invisible=True)
    product_id = fields.Many2one( 'product.product', 'Product',
        domain="[('type', 'in', ['product', 'consu'])]", store=True, copy=True, precompute=True,
        readonly=True, required=True, check_company=True, related="production_id.product_id", invisible=True )
    
    product_tracking = fields.Selection(related='product_id.tracking', invisible=True)
    batch_id = fields.Many2one('stock.lot', string="Lot/Serial Number", required=True, domain="[('product_id', '=', product_id), ('production_id', '=', production_id)]") 
    quantity = fields.Float(string="Quantity", required=True)
    


    
    @api.constrains('quantity')
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise UserError("The batch quantity must be greater than zero.")