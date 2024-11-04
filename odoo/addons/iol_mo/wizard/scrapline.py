from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.addons import decimal_precision as dp
from odoo.tools import float_compare, float_round

# class StockMoveExt(models.Model):
#     _inherit = 'stock.move'

#     scrap_product_line_id = fields.Many2one('scrap.product.line', 'Scrap Line')

class ScrapProductsByQuantity(models.TransientModel):
    _name = 'scrap.products.by.quantity'
    _inherit = ['mail.thread']
    _description ='Bulk Scrap'

    def _get_default_scrap_location_id(self):
        company_id = self.env.context.get('default_company_id') or self.env.company.id
        return self.env['stock.location'].search([('scrap_location', '=', True), ('company_id', 'in', [company_id, False])], limit=1).id


    def _get_default_location_id(self):
        context = self.env.context
        if 'active_id' in context:
            return self.env['mrp.workorder'].search([('id', '=', self.env.context['active_id'])]).production_id.location_src_id.id
        elif 'params' in context:
            if 'id' in self.env.context['params']:
                return self.env['mrp.production'].search([('id', '=', self.env.context['params']['id'])]).location_src_id.id
        else:
            return self.production_id.location_src_id.id
        

    name = fields.Char('Reference',  default=lambda self: _('New'),
        copy=False, readonly=True, required=True,
        states={'done': [('readonly', True)]})
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True,
                                 states={'done': [('readonly', True)]})
    src_location_id = fields.Many2one('stock.location', string='Source Location', domain="[('usage', '=', 'internal'), ('company_id', 'in', [company_id, False])]",
         states={'done': [('readonly', True)]}, default=_get_default_location_id, check_company=True) #required=True,
    dest_location_id = fields.Many2one('stock.location', string='Scrap Location', default=_get_default_scrap_location_id,
        domain="[('scrap_location', '=', True), ('company_id', 'in', [company_id, False])]", required=True, states={'done': [('readonly', True)]}, check_company=True)
    date = fields.Date(default=fields.Date.today())
    scrap_line = fields.One2many('scrap.product.line', 'scrap_id', string='Order Lines', copy=True, states={'done': [('readonly', True)]})  #,required=True
    quantity = fields.Float(string='Scrap Quanity')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
        ], string='Status', default='draft', readonly=True, tracking=True)
    date_done = fields.Datetime('Done date', readonly=True)
    workorder_id = fields.Many2one('mrp.workorder')
    production_id = fields.Many2one('mrp.production', 'Manufacturing Order',check_company=True)
    scrap_desc = fields.One2many('scrapreson.qty','scrap_id', string="Scrap reason") #, required=True
    is_component_not_replaced = fields.Boolean( default=False,compute='_compute_is_component_not_replaced', readonly=True)
    mts_id = fields.Many2one('mts.rejection', 'MTS No', readonly=True, compute='_compute_mts_id')



    @api.depends('src_location_id','dest_location_id')
    def _compute_mts_id(self):
        for record in self:
            mts_id = self.env['mts.rejection'].search(['&',('src_location_id','=',record.src_location_id.id),('dest_location_id', '=', record.dest_location_id.id),
                            ('date', '>=', fields.Datetime.now().strftime('%Y-%m-%d 00:00:01')),('date', '<=', fields.Datetime.now().strftime('%Y-%m-%d 23:59:59') )])
            if mts_id:
                if  len(mts_id) == 1:
                    record.mts_id = mts_id
                else:
                    raise UserError(_("More than one MTS Number created for the location (%s) and date (%s)") % (record.src_location_id.id,fields.Datetime.now().strftime('%Y-%m-%d'))) 
            else:
                mts_vals = {
                        'src_location_id':record.src_location_id.id,
                        'dest_location_id': record.dest_location_id.id,
                        'date' : fields.Datetime.now()
                }
                mts_rej = self.env['mts.rejection'].create(mts_vals)
                record.mts_id = mts_rej.id


    @api.depends('workorder_id','production_id')
    def _compute_is_component_not_replaced(self):
        for record in self:
            if self.workorder_id.operation_id.component_not_replaced == True:
                record.is_component_not_replaced = True
            else:
                record.is_component_not_replaced = False
    
    @api.onchange('company_id')
    def _onchange_company_id(self):
        if self.company_id:
            warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.company_id.id)], limit=1)
            self.location_id = warehouse.lot_stock_id
            self.scrap_location_id = self.env['stock.location'].search([
                ('scrap_location', '=', True),
                ('company_id', 'in', [self.company_id.id, False]),
            ], limit=1)
        else:
            self.location_id = False
            self.scrap_location_id = False
    

# Automatically get raw products of current & previous WO  
    @api.onchange('quantity')
    def _onchange_quantity(self):
        if self.quantity < 1 :
            raise UserError(_("Quantity should become minimum 1 qty"))
        elif (self.quantity + self.workorder_id.qty_produced+ self.workorder_id.rejection_qty ) > self.workorder_id.qty_production and self.is_component_not_replaced == True:
            raise UserError(_("Quantity should become less than or equal from original production qty."))
        else:          
            values = []  
            cur_and_pre_workorders = self.get_cur_and_pre_workorders()
            self.scrap_line = [(5, 0, 0)]

            

            for workorder in cur_and_pre_workorders:
                for move in workorder.move_raw_ids:
                    move_lines = self.env['stock.move.line'].search([('move_id', 'in', move.ids)])
                    
                    for move_line in move_lines:
                        lot_id = move_line.lot_id.ids[0] if move_line.lot_id else False
                        qty=0
                        for bom_line_ids in workorder.production_id.bom_id.bom_line_ids:                            
                            if bom_line_ids.product_id.id == move.product_id.id:
                                if bom_line_ids.bom_id.product_qty == 1:
                                    qty=self.quantity * bom_line_ids.product_qty
                                else:
                                    qty=self.quantity * bom_line_ids.product_qty / bom_line_ids.bom_id.product_qty
                                break

                        vals = { 
                            'product_id': move.product_id.id,
                            'scrap_id': self.ids[0],             
                            'lot_id': lot_id,       
                            'src_loc_id': self.src_location_id.id,
                            'dest_loc_id': self.dest_location_id.id,
                            'quantity': qty,  
                        }            
                        values.append(vals)  

            if values:
                list_scrap_line = [(0, 0, scrap_line_value) for scrap_line_value in values]
                self.scrap_line = list_scrap_line
            else:
                self.scrap_line = [(5, 0, 0)]  



    def get_cur_and_pre_workorders(self):
        current_wo= self.env['mrp.workorder'].search([('id', '=', self.env.context['current_wo_id'])])
        cur_and_pre_wos = self.env['mrp.workorder'].search(['&',('production_id','=',current_wo.production_id.id),('id', '<=', current_wo.id)])
        return cur_and_pre_wos

    def unlink(self):
        if 'done' in self.mapped('state'):
            raise UserError(_('You cannot delete a scrap which is done.'))
        return super(ScrapProductsByQuantity, self).unlink()

    def action_done(self):
        if (self.quantity) != sum(self.scrap_desc.mapped('total_product_qty')):
                raise UserError(_("Check Scrap Qty and  Scrap Reason Qty"))
        self._check_company()
        for rec in self:
            for line in rec.scrap_line:
                scrap_vals = {
                        'name' : rec.name,
                        'company_id':self.env.company.id,
                        'product_id': line.product_id.id,
                        'lot_id' : line.lot_id.id,
                        'product_uom_id': line.product_uom.id,
                        'location_id': line.src_loc_id.id,
                        'scrap_location_id': line.dest_loc_id.id,
                        'scrap_qty': line.quantity,
                        'production_id':rec.workorder_id.production_id.id,
                        'workorder_id': rec.workorder_id.id,
                }
                scrap = self.env['stock.scrap'].create(scrap_vals)

                scrap.action_validate()

            rec.state = 'done'
            rec.date_done = fields.Datetime.now()

            if self.is_component_not_replaced == True:
                current_wo = self.env['mrp.workorder'].search([('id', '=', self.workorder_id.id)])
                current_wo.write({'rejection_qty': current_wo.rejection_qty + self.quantity }) 
                current_wo.qty_producing=current_wo.qty_production - (current_wo.rejection_qty + current_wo.qty_produced)
                pre_wo = self.env['mrp.workorder'].search([('id', '=', current_wo.id-1)])

                if current_wo.production_id.id == pre_wo.production_id.id:
                    if pre_wo.state == 'done':
                        if (current_wo.qty_produced + current_wo.rejection_qty) == current_wo.qty_production:
                            current_wo.state ='done'
                elif (current_wo.qty_produced + current_wo.rejection_qty) == current_wo.qty_production:
                    current_wo.state ='done'
                

            

class ScrapProductLine(models.TransientModel):
    _name = 'scrap.product.line'
    _description = 'Bulk Scrap Process Line'

    @api.depends('product_id', 'src_loc_id')
    def _get_available_qty(self):
        quant_obj = self.env['stock.quant']
        for rec in self:
            rec.available_qty = 0.0
            if rec.product_id and rec.src_loc_id:
                quants = quant_obj.search(
                    [('product_id', '=', rec.product_id.id), ('location_id', '=', rec.src_loc_id.id)])
                rec.available_qty = sum(quants.mapped('quantity'))

    scrap_id = fields.Many2one('scrap.products.by.quantity', string='Order Reference', required=True, ondelete='cascade', index=True, copy=False)
    product_id = fields.Many2one('product.product', 'Product Name', ondelete='restrict',required=True,) #default= lambda self: self.env.context['current_wo_id']
    lot_id = fields.Many2one('stock.lot', 'Lot/Serial Number', required=True)
    quantity = fields.Float(string='Scrap Quanity',required=True)
    available_qty = fields.Float(string='Available Quanity', compute="_get_available_qty", store=True)
    src_loc_id = fields.Many2one('stock.location', string='Source Location',required=True)
    dest_loc_id = fields.Many2one('stock.location', string="Scrap Location",required=True)
    product_uom = fields.Many2one('uom.uom', related='product_id.uom_id', string='Product Unit of Measure',required=True)

    _sql_constraints = [
        ('qty_gt_zero', 'CHECK (quantity>0.00)', 'Product Quantity to be scrapped needs to be greater than 0.'),
    ]

    @api.onchange('product_id', 'src_loc_id')
    def get_quantity(self):
        quant_obj = self.env['stock.quant']
        if self.product_id and self.src_loc_id:
            quants = quant_obj.search([('product_id', '=', self.product_id.id), ('location_id', '=',   self.src_loc_id.id)])
            self.quantity = sum(quants.mapped('quantity'))

        valid_product_ids = []
        products = self.env['product.product'].search([])
        for product in products:
            quants = quant_obj.search(
                [('product_id', '=', product.id), ('location_id', '=', self.src_loc_id.id)])
            available_qty = sum(quants.mapped('quantity'))
            if available_qty > 0.00:
                valid_product_ids.append(product.id)

        return {'domain':{'product_id':[
            ('id','in',valid_product_ids),
            ('type', 'in', ['product', 'consu']),
            '|', ('company_id', '=', False), ('company_id', '=', self.scrap_id.company_id.id)
        ]}}

    @api.onchange('quantity')
    def onchange_scrap_qty(self):
        if self.quantity and self.quantity > self.available_qty:
            raise UserError("You can't scrap more than available quantity.")

class reson(models.TransientModel):
     _name ='scrapreson.qty'    
     scrapreason = fields.Many2one('scrap.reason.code', string="Scrapreason")
     scrap_id = fields.Many2one('scrap.products.by.quantity', string='Order Reference', required=True, ondelete='cascade', index=True, copy=False)
     total_product_qty = fields.Float(string="Quantity",digits=dp.get_precision('Unit of Measure'))
     workorder_id = fields.Many2one('mrp.workorder')