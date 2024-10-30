from itertools import product
from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import ValidationError
from odoo.tools import float_compare, float_round
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
# from odoo.tools.profiler import profile
import base64
import os
import sys
import xlrd
import json
import datetime
import tempfile
import binascii
#import pandas as pd
from os.path import dirname, abspath
import inspect
from io import StringIO 
#import openpyxl
import math
import re
# import pymssql




class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    @api.model
    def create(self, vals):
        if 'operation_id' in vals:
            operation_id = self.env['mrp.routing.workcenter'].search([('id', '=', vals['operation_id'])])
            if operation_id:
                vals['component_not_replaced'] = operation_id.component_not_replaced
        result = super(MrpWorkorder, self).create(vals)   
        return result

    

    def write(self, values):
        res = super(MrpWorkorder, self).write(values)        
        if 'state' in values:            
            if values['state'] == 'done':
                for record in self:
                    raw_moves = self.env['stock.move'].search(['&',('workorder_id', '=', record.id),('raw_material_production_id', '=', record.production_id.id)])
                    for raw_move in raw_moves:
                        if raw_move.lot_ids:
                            raw_move_lines = self.env['stock.move.line'].search([('move_id', '=', raw_move.id)])
                            if record.product_id.type_of_product ==False:
                                continue                            
                            if sum([move_line.quantity for move_line in raw_move_lines]) !=record.qty_produced: # Only check Injector and IOL
                                raise ValidationError(_("check Quantity for the raw product. (%s) " )% (raw_move.product_id.name))
                        else:
                            raise ValidationError(_("You need to provide a lot for the raw product. (%s) " )% (raw_move.product_id.name))

        return res
    
    rejection_qty = fields.Float('Rejection Qty', digits=dp.get_precision('Product Unit of Measure'), readonly=True )
    shift = fields.Selection([('shift1', 'Shift I'),('shift2', 'Shift II'),('shift3', 'Shift III'),], string='Shift',default='shift1', required=True)  
    wo_date_start = fields.Datetime('Date Start')
    wo_date_stop = fields.Datetime('Date Stop')
    # is_produced = fields.Boolean(  default=False,compute='_compute_is_produced') 
    is_readonly = fields.Boolean( default=False,compute='_compute_is_readonly')
    is_invisible = fields.Boolean( default=False,compute='_compute_is_invisible') # scrap button visibility 
    invisible_btn_finish_wo = fields.Boolean( default=True,compute='_compute_invisible_btn_finish_wo') # scrap button visibility 
    qty_production = fields.Float('Original Production Quantity', readonly=True, related='', compute='_compute_qty_production')
    resources = fields.One2many('workorder.resourcesnew', string="Resources",inverse_name="workorderId", required=True)
    component_not_replaced = fields.Boolean(string="Component not replaced" ,
            help="if 'True' means any one component has rejected in this operation the whole product is rejected", default=False)

    @api.model
    def validate_resource(self):
        for wo in self:
            if wo.state == 'done':
                continue
            if not wo.resources:
                raise UserError(_("You must add at least one resources to the Workorder."))
            elif (wo.qty_produced + wo.qty_producing) != sum(wo.resources.mapped('total_product_qty')):
                raise UserError(_("Finished Quantity and Resources details Quantity should become same"))
        return True
        
    def _compute_qty_production(self):
        for record in self:
            if not record.blocked_by_workorder_ids:
                record.qty_production = record.production_id.product_qty
            else:
                record.qty_production = record.blocked_by_workorder_ids[0].qty_produced



                
    
    @api.depends('product_id','state')
    def _compute_invisible_btn_finish_wo(self):
        for record in self:
            record.invisible_btn_finish_wo = not (record.component_not_replaced == False and record.state  in ['progress'] and record.qty_produced+ record.rejection_qty == record.qty_production )

    @api.depends('qty_produced','state')
    def _compute_is_readonly(self):
        for record in self:
            record.is_readonly = record.state in ['done','cancel'] or record.qty_produced > 0

    @api.depends('qty_produced','state')
    def _compute_is_invisible(self):
        for record in self:
            record.is_invisible = not (record.state in ['progress'] and record.qty_produced > 0)

    @api.depends('qty_production', 'qty_reported_from_previous_wo', 'qty_produced', 'production_id.product_uom_id')
    def _compute_qty_remaining(self):
        for wo in self:
            if wo.production_id.product_uom_id:
                wo.qty_remaining = max(float_round(wo.qty_production - wo.qty_reported_from_previous_wo - (wo.qty_produced +wo.rejection_qty), precision_rounding=wo.production_id.product_uom_id.rounding), 0)
            else:
                wo.qty_remaining = 0


    def button_start(self):
        # Before start Workorder fill finished lot_id must.
        for workorder in self:
            pre_wo = self.env['mrp.workorder'].search(['&',('id', '<', workorder.id),('production_id', '=', workorder.production_id.id)],order='id desc',limit=1)
            if pre_wo:
                if pre_wo.state !='done':
                    raise UserError(_('Please Complete previous Workorder'))
                
            if workorder.product_id.tracking == 'lot':
                if not workorder.finished_lot_id:
                    raise UserError(_('You need to provide a lot for the finished product.'))
                if not workorder.production_id.sterile_batch and workorder.product_id.categ_id.name == 'INJECTOR-ASSEMBLY':
                    raise UserError(_('You need to provide a Sterile batch number.'))


            #  Fill Components lot_id must against the workorder.
            raw_moves = self.env['stock.move'].search(['&',('workorder_id', '=', workorder.id),('raw_material_production_id', '=', workorder.production_id.id)])
            for raw_move in raw_moves:
                if not raw_move.lot_ids:
                    raise ValidationError(_("You need to provide a lot for the raw product. (%s) " )% (raw_move.product_id.name))  
            
            
            date_finished = workorder.wo_date_stop
            date_start = workorder.wo_date_start
            if workorder.blocked_by_workorder_ids:
                if not date_start or workorder.blocked_by_workorder_ids[0].date_finished >= date_start:
                    raise UserError(_('Please check previous WO Stop date'))
                    
            if not date_start or not date_finished or date_finished < date_start:
                raise UserError(_('Please check Date Start and Date Stop'))
            if  date_finished > fields.Datetime.now():
                raise UserError(_('Date Stop is greater than the current datetime. Please check and correct it'))

        super(MrpWorkorder, self).button_start()

        for workorder in self:
            date_finished = workorder.wo_date_stop
            date_start = workorder.wo_date_start
            workorder.write({'date_start': date_start})

            if workorder.state in ('done', 'cancel'):
                continue
            # # start & end date update for all next workorders-
            # next_wo_ids = self.env['mrp.workorder'].search(['&',('id', '>', workorder.id),('production_id', '=', workorder.production_id.id)])
            # next_wo_ids.write({'date_start': date_finished+ timedelta(hours=0.5),'date_finished':date_finished+ timedelta(hours=1)})


    def button_finish(self):

        
        self.validate_resource()

        for workorder in self:

            date_finished = workorder.wo_date_stop
            date_start = workorder.wo_date_start

            if workorder.state in ('done', 'cancel'):
                continue
            workorder.end_all()

            if workorder.qty_production < workorder.qty_producing :
                raise UserError(_('Original Production Quantity and  Sum of Currently Produced Quantity & Rejected Qty should become same'))
            vals = {
                'qty_produced': workorder.qty_producing,
                'date_finished': date_finished,
                'costs_hour': workorder.workcenter_id.costs_hour,
                'date_start':date_start,
                'qty_remaining':workorder.qty_production - (workorder.qty_producing +workorder.rejection_qty)
            }
            if workorder.blocked_by_workorder_ids:
                if not date_start or workorder.blocked_by_workorder_ids[0].date_finished >= date_start:
                    raise UserError(_('Please check previous WO Stop date'))
                    
            if not date_start or not date_finished or date_finished < date_start:
                raise UserError(_('Please check Date Start and Date Stop'))
            workorder.with_context(bypass_duration_calculation=True).write(vals)

            #next workorder Received Qty(qty_production & qty_producing) updation 
            workorder.needed_by_workorder_ids.write({'qty_production': workorder.qty_produced,'qty_producing': 0,'qty_remaining': workorder.qty_produced})

           

            #mrp_workcenter_productivity update
            time_ids = self.env['mrp.workcenter.productivity'].search([('workorder_id', '=', workorder.id)])
            if time_ids:
                if len(time_ids) > 1:
                    last_time_ids = self.env['mrp.workcenter.productivity'].search([('workorder_id', '=', workorder.id)],order='id desc', limit=len(time_ids)-1)
                    last_time_ids.unlink()
            time_id = self.env['mrp.workcenter.productivity'].search([('workorder_id', '=', workorder.id)])
            if time_id:
                vals1 = {                    
                    'date_start': date_start ,
                    'date_end':date_finished
                    }
                time_id.write(vals1)

            # update state to progress for  Injector Product
            # if workorder.product_id.type_of_product == 'injector':
            #     workorder.write({'state': 'progress'})
            # else:
            #     if workorder.qty_produced + workorder.rejection_qty == workorder.qty_production:
            #         workorder.write({'state': 'done'})
            #     else:
            #         workorder.write({'state': 'progress'})

            if workorder.component_not_replaced == False:
                workorder.write({'state': 'progress'})
            else:
                if workorder.qty_produced + workorder.rejection_qty == workorder.qty_production:
                    workorder.write({'state': 'done'})
                else:
                    workorder.write({'state': 'progress'})
            

        return True
    

    def move_to_scrap(self):
        for wo in self:            
                view = self.env.ref('iol_mo.scrap_product_form_view')
                wiz = self.env['scrap.products.by.quantity'].create({'workorder_id': wo.id,'src_location_id':wo.production_id.location_src_id.id})
                return {
                    'name': _('scrap Move'),
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'scrap.products.by.quantity',
                    'views': [(view.id, 'form')],
                    'view_id': view.id,
                    'target': 'new',
                    'res_id': wiz.id,
                    'context': {'current_wo_id': self.id},
                }
        

    #the button only visible for 'Injector' product 
    def button_finish_wo(self):
        for wo in self:  
            pre_wo = self.env['mrp.workorder'].search([('id', '=', wo.id-1)])

            if wo.production_id.id == pre_wo.production_id.id:
                if pre_wo.state == 'done':
                    if (wo.qty_produced + wo.rejection_qty) == wo.qty_production:
                        wo.state ='done'
            elif (wo.qty_produced + wo.rejection_qty) == wo.qty_production:
                wo.state ='done'         
                
        
         
        

        