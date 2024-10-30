from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'


    @api.model_create_multi
    def create(self, values):
        res = super(StockMoveLine, self).create(values)
        for line in res:
            if line.state == 'done':
                continue
            if line.location_id.usage == 'transit':
                continue
            if line.product_id.tracking != 'lot':
                continue
            if line.product_id.tracking == 'lot':
                if not line.lot_id:
                    continue
            stock_quant= self.env['stock.quant'].search([ '&',('lot_id', '=', line.lot_id.id) ,('product_id','=',line.product_id.id),('location_id','=',line.location_id.id)])
            if stock_quant.reserved_quantity > stock_quant.quantity:
                raise ValidationError(
                            _(
                                "You cannot assign the lot number (%s) for thre product (%s), stock not available "                                
                            )
                            % (
                                line.lot_id.name,line.product_id.name
                            )
                        )  
        return res
    
    

    def write(self, vals):
        for line in self:
            if line.state == 'done':
                continue
            if line.location_id.usage == 'transit':
                continue
            if 'quant_id' in vals:
                stock_quant = self.env['stock.quant'].browse(vals['quant_id'])
                if stock_quant and (stock_quant.reserved_quantity + line.quantity > stock_quant.quantity):
                    raise ValidationError(
                        _("You cannot assign the lot number (%s) for the product (%s), stock not available") % (
                            stock_quant.lot_id.name, stock_quant.product_id.name
                        )
                    )
        return super(StockMoveLine, self).write(vals)
    
    # def write(self, vals):
    #     for line in self:
    #         if line.state == 'done':
    #             continue
    #         if line.location_id.usage == 'transit':
    #             continue
    #         if vals.get('quant_id'):
    #             stock_quant= self.env['stock.quant'].search([ ('id', '=', vals['quant_id'])])
    #             if stock_quant.reserved_quantity+line.quantity > stock_quant.quantity:
    #                 raise ValidationError(
    #                             _(
    #                                 "You cannot assign the lot number (%s) for thre proeduct (%s), stock not available "                                
    #                             )
    #                             % (
    #                                 stock_quant.lot_id.name,stock_quant.product_id.name
    #                             )
    #                         )
            
    #     return super(StockMoveLine, self).write(vals)