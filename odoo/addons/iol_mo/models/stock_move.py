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
                                    ('product_id','in',move.lot_ids.production_id.move_raw_ids.product_id.search(['&',('disallow_multiple_lot_wo','=',True),('id','in',move.lot_ids.production_id.move_raw_ids.product_id.ids) ]).ids), 
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
    
    production_ids = fields.Many2many( 'mrp.production',  string='Manufacturing Orders',
                                        domain="[('product_id', '=', product_id), ('company_id', '=', company_id), ('id', 'in', compute_production_ids) ]"  )
    compute_production_ids = fields.One2many('mrp.production',compute="_compute_production_ids" ) 
    is_pmma_tumbling_operation_type = fields.Boolean(compute='_compute_is_pmma_tumbling_operation_type' )


    @api.depends('raw_material_production_id.picking_type_id')
    def _compute_is_pmma_tumbling_operation_type(self):
        for move in self:
            if move.raw_material_production_id.picking_type_id.is_pmma_tumbling_operation == True:
                move.is_pmma_tumbling_operation_type = True
            else:
                move.is_pmma_tumbling_operation_type = False
                

    @api.depends('product_id','location_id','company_id')
    def _compute_production_ids(self):        
        production_ids=self.env['mrp.production'].search([ ('id','in',self.env['stock.quant'].search(['&',('location_id','in',self.location_id.ids), ('product_id','in',self.product_id.ids ), ('company_id','=',self.company_id.id )]).lot_id.production_id.ids)])
        self.compute_production_ids = [(6, 0, [x.id for x in production_ids])] 

    def action_assign_lots(self): 
        for move in self:
            ml= self.env['stock.move.line'].search([('move_id','in', self.env['stock.move'].search([ ('production_id','in', move.production_ids.ids)]).ids )])
            stock_quant_ids= self.env['stock.quant'].search([ '&',('lot_id','in', ml.lot_id.ids ),('product_id','=', move.product_id.id),('location_id','=', move.location_id.id), ('company_id','=', move.company_id.id) ])
            for sq in stock_quant_ids:
                self.env['stock.move.line'].create({
                            'move_id': move.id, 
                            'product_id': move.product_id.id,
                            'product_uom_id': move.product_id.uom_id.id,
                            'state': 'assigned',
                            'quantity': sq.available_quantity,
                            'quantity_product_uom': sq.available_quantity,
                            'location_id': move.location_id.id,
                            'location_dest_id': move.location_dest_id.id,
                            'lot_id': sq.lot_id.id,  
                            'quant_id':sq.id,
                        })
