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

class InjectorLabelReprint(models.TransientModel):
    _name = 'injector.label.reprint'

    label_print_id =fields.Many2one('injector.label.print', string='Label Print Id', readonly=True) 
    lot_id = fields.Many2one('stock.lot', string='Lot/Serial Number', readonly=True) 
    product_id = fields.Many2one('product.product', 'Product',  readonly=True )     
    sterile_batch =  fields.Char('Sterile Batch', readonly=True)
    mfd_date =  fields.Datetime('Mfd Date', readonly=True)
    exp_date =  fields.Datetime('Exp Date', readonly=True)
    model = fields.Many2one('product.attribute.value', string='Model' ,  readonly=True) 
    reprint_qty = fields.Integer('Reprint Qty', required=True)   
    btw_master_id = fields.Many2one('btw.master', string='Label_Name', readonly=True )


    def action_reprint(self):
        
        if self.model == False or self.exp_date == False or self.lot_id == False or self.sterile_batch == False or self.mfd_date == False:
            raise UserError(('Something Value is missing. Please check.'))
        
        if self.reprint_qty == False or self.reprint_qty < 1:
            raise UserError(('Please Enter RePrint Qty'))


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
                "copies": self.reprint_qty
            }

        try:
            response = requests.post(client_url, json=data)
            if response.status_code == 200:
                print("Print job sent successfully.")
            else:
                raise UserError(('Something Went Worng. Please check.'))
        except requests.exceptions.RequestException as e:
            raise UserError(('Something Went Worng. Please check.'))

        self.label_print_id.write({'reprint_qty': self.label_print_id.reprint_qty + self.reprint_qty })