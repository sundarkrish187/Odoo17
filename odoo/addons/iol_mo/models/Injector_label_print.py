from odoo import fields, models, api,  http
import win32com.client
import pythoncom
import os
import inspect
import win32print
import sys
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
import win32api
import subprocess
import requests
import socket
from odoo.exceptions import UserError
from datetime import datetime
from odoo import fields
import time
import pymssql
import pyodbc 



class InjectorLabelPrint(models.Model):
    _name = "injector.label.print"
    _description = "Injector Label Print"

    
    lot_id = fields.Many2one('stock.lot', string='Lot/Serial Number', required=True, copy=False ) 
    product_id = fields.Many2one('product.product', 'Product', required=True, copy=False, domain="[('id', 'in', product_ids)]") 
    product_ids = fields.One2many('product.product',compute="_compute_product_ids")  
    sterile_batch =  fields.Char('Sterile Batch', readonly=True)
    mfd_date =  fields.Datetime('Mfd Date', readonly=True)
    exp_date =  fields.Datetime('Exp Date', readonly=True)
    model = fields.Many2one('product.attribute.value', string='Model', required=True, copy=False, domain="[('id', 'in', compute_models_ids)]"  )    
    compute_models_ids = fields.One2many('product.attribute.value',compute="_compute_models" )    
    label_count =  fields.Integer('Label Count', readonly=True)
    printed_qty = fields.Integer('Printed Qty', readonly=True)
    remaining_qty = fields.Integer('Remaining Qty', readonly=True)
    reprint_qty = fields.Integer('Reprint Qty', readonly=True)    
    state = fields.Selection(
            [('not_labelled', 'Not Labelled'),
             ('labelled', 'Labelled') ], string='State', readonly=True, default='not_labelled',  store=True)
    
    btw_master_id = fields.Many2one('btw.master', string='Label_Name', required=True,domain="[('id', 'in', btw_master_ids)]")
    btw_master_ids = fields.One2many('product.attribute.value',compute="_compute_btw_master_ids" )    


    _sql_constraints = [
        ('name_ref_uniq', 'unique (lot_id,product_id)', 'The combination of serial number must be unique across a product'),
    ]



    @api.depends('model')
    def _compute_btw_master_ids(self):        
        btw_master_ids=self.env['btw.master'].search([ ('model_no.id','=',self.model.ids )])
        self.btw_master_ids = [(6, 0, [x.id for x in btw_master_ids])] 
        # if btw_master_ids:
        #     self.btw_master_id =btw_master_ids[0]


    @api.depends('product_id')
    def _compute_models(self):        
        model_ids=self.env['product.attribute.value'].search([ '&', ('attribute_id.name','=','Model_Name'), ('id','in',self.product_id.attribute_line_ids.value_ids.ids )])
        self.compute_models_ids = [(6, 0, [x.id for x in model_ids])] 
        # if model_ids:
        #     self.model =model_ids[0]
        
    
    @api.depends('lot_id')
    def _compute_product_ids(self):        
        product_ids=self.env['product.product'].search([ ('id','=',self.lot_id.product_id.id )])
        self.product_ids = [(6, 0, [x.id for x in product_ids])]
        # if  product_ids:
        #     self.product_id = product_ids[0]
        
        if self.lot_id.production_id:
            if self.lot_id.production_id.state != 'done':
                raise UserError(('The Manufacturing process is not completed. Please check.'))
            self.sterile_batch = self.lot_id.production_id.sterile_batch
            self.mfd_date =  self.lot_id.production_id.mfd_date
            self.exp_date = self.lot_id.production_id.exp_date
            self.label_count = self.lot_id.production_id.qty_produced  
            
            self.remaining_qty = self.label_count - self.printed_qty     


        


    def action_print(self):      
        
        client_ip = http.request.httprequest.remote_addr
        try:
            client_hostname = socket.gethostbyaddr(client_ip)[0]
        except socket.herror:
            client_hostname = client_ip            
        client_url = "http://" + client_hostname + ":5000/print_label"   

        # get file name form BTW Master  
        file_name = self.btw_master_id.file_name
        
        data = {
                "file_path": os.path.expanduser(os.path.join(r'C:\Odoo\Label Files', file_name)),
                "Ref": self.model.name,
                "lot": self.sterile_batch,
                "Lotno": self.lot_id.name,
                "mfd": self.mfd_date.strftime('%Y-%m'),
                "exp": self.exp_date.strftime('%Y-%m'),
                "copies": self.remaining_qty
            }
        

        # Update MySQL Database for IOL lens box pack
        databases = [  "PHILIC","PHOBIC", "PHOBIC_Preloaded"] 
        for database in databases:

            try:
                if database == 'PHILIC':                    
                    conn_str = ("DRIVER={ODBC Driver 17 for SQL Server};" "SERVER=IOLSERVER2023;" "DATABASE="+database+";" "UID=sa;" "PWD=sachin3123!@#;" )  
                else:
                    conn_str = ("DRIVER={ODBC Driver 17 for SQL Server};" "SERVER=13.127.122.180;" "DATABASE="+database+";" "UID=pandian-admin;" "PWD=aspiration2@sep2024;" )   
                            
                conn = pyodbc.connect(conn_str)
                cursor = conn.cursor()

                my_select_query = """SELECT * FROM Injector_Label WHERE Str_batch = ?"""
                cursor.execute(my_select_query, (self.sterile_batch,))  
                injector_rows = cursor.fetchall()

                if len(injector_rows) > 0:
                    if len(injector_rows) == 1:
                        for row in injector_rows:
                            if row.BTWLabelName == self.btw_master_id.label_name:
                                update_query = """UPDATE Injector_Label SET Qty = ? 
                                                WHERE Str_batch = ? AND BTWLabelName = ?"""
                                cursor.execute(update_query, (int(row.Qty)+self.remaining_qty, self.sterile_batch, self.btw_master_id.label_name))
                                conn.commit()
                            else:
                                raise UserError(('The BTWLabelName does not match. Cannot update.')) 
                    else:
                        raise UserError(('The Batch More than one time presnet in MSSQL Database. Cannot update.'))  
                else:
                    my_query = """INSERT INTO Injector_Label (Inj_Ref, Mfd_Year, Mfd_Month, Exp_year, Exp_Month, Str_batch, Qty, Created_Date, Updated_by,BTWLabelName) 
                    VALUES  (?, ?, ?, ?, ?, ?, ?, GETDATE(), ?, ?)"""
                    cursor.execute(my_query,(self.model.name,self.mfd_date.strftime('%Y'), self.mfd_date.strftime('%m'),self.exp_date.strftime('%Y'), self.exp_date.strftime('%m'),
                                            self.sterile_batch,self.remaining_qty, self.env['res.users'].browse(self.env.uid).name, self.btw_master_id.label_name))
                    conn.commit() 
            except Exception as e: 
                print(f"An error occurred: {e}")
                
            finally:
                cursor.close()
                conn.close()

        # Print command
        try:
            response = requests.post(client_url, json=data)
            if response.status_code == 200:
                print("Print job sent successfully.")
            else:
                raise UserError(('Something Went Worng. Please check.'))
        except requests.exceptions.RequestException as e:
            raise UserError(('Something Went Worng. Please check.'))

        self.printed_qty = self.printed_qty + self.remaining_qty
        self.remaining_qty = self.label_count - self.printed_qty
        if self.remaining_qty == 0:
            self.state = 'labelled'

        
    


    def move_to_reprint(self):
        for wo in self:            
                view = self.env.ref('iol_mo.injector_label_reprint_form_view')
                return {
                    'name': ('Injector Label Reprint'),
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'injector.label.reprint', 
                    'target': 'new', 
                    'context': {
                        'default_label_print_id': self.id,
                        'default_lot_id': self.lot_id.id,
                        'default_product_id': self.product_id.id,
                        'default_sterile_batch': self.sterile_batch,
                        'default_mfd_date': self.mfd_date,
                        'default_exp_date': self.exp_date,
                        'default_model': self.model.id,
                        'default_btw_master_id': self.btw_master_id.id,
                    },
                }

