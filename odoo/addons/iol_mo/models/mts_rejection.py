from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp

class MTS_Rejection(models.Model):
    _name ='mts.rejection'

    
    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('mts.rejection')
        result = super(MTS_Rejection, self).create(vals)
        return result
    
    name = fields.Char('MTS Number',  default=lambda self: _('New'),
        copy=False, readonly=True, required=True)    
    src_location_id = fields.Many2one('stock.location', string="Source Location", required=True)
    dest_location_id = fields.Many2one('stock.location',string="Destination Location", required=True)
    date = fields.Date(default=fields.Date.today(),required=True)
    scrap_ids = fields.One2many('stock.scrap','mts_id', string="Scrap Products")
