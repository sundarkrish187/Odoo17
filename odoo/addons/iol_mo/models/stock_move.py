from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class StockMove(models.Model):
    _inherit = 'stock.move'

    # @api.model_create_multi
    # def create(self, vals_list):        
    #     moves = super(StockMove, self).create(vals_list)
    #     if moves:
    #         for move in moves:
    #             if move.raw_material_production_id and move.product_id.disallow_multiple_lot_wo == True :
    #                 if len(move.lot_ids) > 1:
    #                     raise ValidationError("mAXIMUM 1")                
    #     return moves  

    def write(self, vals):
        res = super().write(vals)
        if self:
            for move in self:
                # lathe  validation( restrict Multiple blanks lot use)
                if move.raw_material_production_id and move.product_id.disallow_multiple_lot_wo == True and not move.scrap_id:
                    if len(move.lot_ids) > 1:
                        raise ValidationError(
                            _(
                                "You cannot select multiple lot number for this raw product (%s) "                                
                            )
                            % (
                                move.product_id.name
                            )
                        )  

                # tumbling validation
                if move.raw_material_production_id and move.product_id.disallow_multiple_lot_against_blanks_id == True and not move.scrap_id:
                    if len(move.lot_ids) > 1:
                        if move.lot_ids.production_id and move.lot_ids.production_id.move_raw_ids :
                            if len(move.lot_ids.production_id.move_raw_ids.lot_ids.search(['&',
                                    ('product_id','=',move.lot_ids.production_id.move_raw_ids.product_id.search([('disallow_multiple_lot_wo','=',True)]).id), 
                                    ('id', 'in', move.lot_ids.production_id.move_raw_ids.lot_ids.ids)])) > 1:

                                raise ValidationError(
                                    _(
                                        "You cannot select multiple lot number of this product (%s)  made with multiple blanks lot numbers   "                                
                                    )
                                    % (
                                        move.product_id.name
                                    )
                                )  

                # Injector Final product validation
                sterile_batches = []
                if move.raw_material_production_id and move.product_id.disallow_multiple_lot_against_sterile_batch == True and not move.scrap_id:

                    # validation for sterile batch mischoose
                    if move.lot_ids:
                        if move.raw_material_production_id.lot_producing_id:
                            if move.lot_ids.production_id : 
                                for production_id in move.lot_ids.production_id: 
                                    if production_id.sterile_batch!= move.raw_material_production_id.lot_producing_id.name:
                                        raise ValidationError( _( " Sterile batch numbers do not match. Please review the selection.  " ) ) 
                        else:
                            raise ValidationError( _(  "You must provide the finished lot number before proceeding."   )  ) 
                             

                    if len(move.lot_ids) > 1:
                        if move.lot_ids.production_id : 

                            for production_id in move.lot_ids.production_id: 

                                if production_id.sterile_batch:
                                    sterile_batches.append(production_id.sterile_batch)
                                    if len(set(sterile_batches)) == 1: 
                                        print("All sterile_batches are the same, proceeding...") 
                                    else: 
                                        raise ValidationError(  _(
                                                "You cannot select multiple lot number of this product (%s)  made with multiple sterile batch numbers   "   )
                                            % ( move.product_id.name )
                                        )  
                                else:
                                    raise ValidationError(  _( "You cannot select a lot number for this product (%s) because the sterile batch is not set.  "  )
                                        % ( move.product_id.name ) )  

                                
                            

        return res


   