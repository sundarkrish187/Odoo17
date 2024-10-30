
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



class ScrapReasonCode(models.Model):
    _name = "scrap.reason.code"
    _description = "Reason Code"

    name = fields.Char("Code", required=True)
    description = fields.Text("Description")
    location_id = fields.Many2one("stock.location",string="Scrap Location",domain="[('scrap_location', '=', True)]",)



    def action_print1(self):
        

        client_ip = http.request.httprequest.remote_addr

        try:
            client_hostname = socket.gethostbyaddr(client_ip)[0]
        except socket.herror:
            client_hostname = client_ip
            
        client_url = "http://" + client_hostname + ":5000/print_label"

        data = {
            "file_path": os.path.expanduser(r'C:\Odoo\Label Files\test.btw'),
            "trayDetail": "Detail1",
            "model": "Model1",
            "trayNo": "Tray001",
            "batchNo": "Batch001",
            "power": "Power1",
            "lotno": "Lot001",
            "sFrom": "100",
            "sTo": "200",
            "qty": "50",
            "rackNo": "Rack1"
        }

        try:
            response = requests.post(client_url, json=data)
            if response.status_code == 200:
                print("Print job sent successfully.")
            else:
                print(f"Failed to send print job. Status code: {response.status_code}")
                print("Response content:", response.content)
        except requests.exceptions.RequestException as e:
            print(f"Error sending print job: {e}")