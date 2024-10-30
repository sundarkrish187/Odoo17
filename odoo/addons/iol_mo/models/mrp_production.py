from itertools import product
from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import ValidationError
from odoo.tools import   float_is_zero
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta



class MrpProduction(models.Model):
    _inherit = 'mrp.production'


    def action_confirm(self):
        result = super(MrpProduction, self).action_confirm()          
        return result


    @api.model
    def create(self, vals):
        if vals.get('sterile_batch'):
            production_ids = self.env['mrp.production'].search(['&',('state','=','done'),('sterile_batch', '=', vals['sterile_batch'])])            
            for production_id in production_ids:
                if vals['product_id'] != production_id.product_id.id:
                    raise UserError("The batch number '%s' is already assigned to another product in the Manufacturing Order '%s'." % 
                                    (vals['sterile_batch'], production_id.name))        

        if vals.get('lot_producing_id'):
            lot = self.env['stock.lot'].browse(vals['lot_producing_id'])
            vals['mfd_date'] = lot.create_date
            vals['exp_date'] = lot.expiration_date
        return super(MrpProduction, self).create(vals)

    def write(self, vals):
        if vals.get('sterile_batch'):
            production_ids = self.env['mrp.production'].search(['&',('state','=','done'),('sterile_batch', '=', vals['sterile_batch'])])            
            for production_id in production_ids:
                if self.product_id.id != production_id.product_id.id:
                    raise UserError("The batch number '%s' is already assigned to another product in the Manufacturing Order '%s'." % 
                                    (vals['sterile_batch'], production_id.name))   
                
        if vals.get('lot_producing_id'):
            lot = self.env['stock.lot'].browse(vals['lot_producing_id'])
            vals['mfd_date'] = lot.create_date
            vals['exp_date'] = lot.expiration_date
        return super(MrpProduction, self).write(vals)

    
    lot_producing_id = fields.Many2one(
        'stock.lot', string='Lot/Serial Number', copy=False,
        domain="[('product_id', '=', product_id), ('company_id', '=', company_id), ('production_id', '=', id) ]" , check_company=True)
    wo_is_running = fields.Boolean( compute='_compute_wo_is_running', help='Technical field to check if produce button can be shown')
    first_wo_finish = fields.Boolean(compute='_compute_wo_is_running', help='Technical field to check if produce button can be shown')
    brand_name = fields.Many2one('product.attribute.value', string='Brand Name', copy=False, domain="[('attribute_id.name', '=', 'Brand_Name')]"  )
    model_name = fields.Many2one('product.attribute.value', string='Model Name', copy=False, domain="[('attribute_id.name', '=', 'Model_Name')]"  )
    power = fields.Many2one('product.attribute.value', string='Power', copy=False, domain="[('attribute_id.name', '=', 'Power')]"  )

    mfd_date = fields.Datetime('Manufacturing Date', readonly=True )
    exp_date = fields.Datetime('Expiration Date', readonly=True )
    sterile_batch =  fields.Char('Sterile Batch' )
    is_inj_assembly_products = fields.Boolean(compute='_compute_product_categ', default=False)
    is_inj_fini_products = fields.Boolean(compute='_compute_product_categ', default=False)


    move_raw_ids = fields.One2many(
        'stock.move', 'raw_material_production_id', 'Components',
        compute='_compute_move_raw_ids', store=True, readonly=False,
        copy=False,
        domain=[('scrapped', '=', False)])



    @api.depends('product_id')
    def _compute_product_categ(self):
        for production in self:
            # Reset both flags to False before assigning
            production.is_inj_assembly_products = False
            production.is_inj_fini_products = False

            if production.product_id.categ_id.name == 'INJECTOR-ASSEMBLY':
                production.is_inj_assembly_products = True
            elif production.product_id.categ_id.name == 'INJECTOR':
                production.is_inj_fini_products = True
            


    @api.onchange('lot_producing_id')
    def _onchange_lot_producing_id(self):
        if self.lot_producing_id:
            self.mfd_date=self.lot_producing_id.create_date
            self.exp_date=self.lot_producing_id.expiration_date

    


    #for avoid cunsumtion issue and quantity issue(backorder)
    def pre_button_mark_done(self):
        confirm_expired_lots = self._check_expired_lots()
        if confirm_expired_lots:
            return confirm_expired_lots
        
        self._button_mark_done_sanity_checks()
        for production in self:
            if float_is_zero(production.qty_producing, precision_rounding=production.product_uom_id.rounding):
                production._set_quantities()

        for production in self:
            if float_is_zero(production.qty_producing, precision_rounding=production.product_uom_id.rounding):
                raise UserError(_('The quantity to produce must be positive!'))

        consumption_issues = self._get_consumption_issues()        
        if consumption_issues:
            for order, product_id, consumed_qty, expected_qty in consumption_issues:
                if product_id.type_of_product == False:
                    continue
                raise ValidationError(
                    _(
                        "You consumed a different quantity than expected for the following products. "
                        "Please review your component consumption. "
                        "Product-%s   Consumed Quantity - %s    Expected Quantity- %s "
                    )
                    % (
                        product_id.name,
                        consumed_qty,
                        expected_qty
                    )
                )
        return True
    

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(MrpProduction, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if view_type == 'form':
            doc = etree.XML(res['arch'])
            for node in doc.xpath("//field[@name='move_raw_ids']/tree/field"):
                if node.get('move_raw_ids') == 1:
                    node.set('readonly', '1')
            res['arch'] = etree.tostring(doc)
        return res


    @api.depends('state', 'product_qty', 'qty_producing')
    def _compute_wo_is_running(self):
        for production in self:
            if production.workorder_ids:
                if any([wo.state != 'done' for wo in production.workorder_ids]):
                    production.wo_is_running = True
                else:
                    production.wo_is_running = False

                if len(production.workorder_ids.ids) != 0:
                    first_wo = self.env['mrp.workorder'].search(['&',('production_id','=',self.id),('id', '=', min(production.workorder_ids.ids))])
                    if first_wo.state == 'done':
                        production.first_wo_finish = True
                    else:
                        production.first_wo_finish = False
                else:
                    production.first_wo_finish = False                
            else:
                production.first_wo_finish = False
                production.wo_is_running = False


        

   