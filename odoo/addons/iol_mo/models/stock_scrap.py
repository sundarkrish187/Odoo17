from odoo import api, fields, models,_
from odoo.tools import float_compare
from odoo.exceptions import UserError


class StockScrap(models.Model):
    _inherit = "stock.scrap"


    @api.model
    def create(self, vals):
        if vals['location_id'] and vals['scrap_location_id']:
            mts_id = self.env['mts.rejection'].search(['&',('src_location_id','=',vals['location_id']),('dest_location_id', '=', vals['scrap_location_id']),
                            ('date', '>=', fields.Datetime.now().strftime('%Y-%m-%d 00:00:01')),('date', '<=', fields.Datetime.now().strftime('%Y-%m-%d 23:59:59') )])
            if mts_id:
                if  len(mts_id) == 1:
                    vals['mts_id'] = mts_id.id
                else:
                    raise UserError(_("More than one MTS Number created for the location (%s) and date (%s)") % (vals['location_id'],fields.Datetime.now().strftime('%Y-%m-%d'))) 
            else:
                mts_vals = {
                        'src_location_id':vals['location_id'],
                        'dest_location_id': vals['scrap_location_id'],
                        'date' : fields.Datetime.now()
                }
                mts_rej = self.env['mts.rejection'].create(mts_vals)
                vals['mts_id'] = mts_rej.id

        result = super(StockScrap, self).create(vals)
        return result
    
    def write(self, vals):
        for scrap in self:
            if any(key in vals for key in ['location_id', 'scrap_location_id', 'date_done']):
                
                location_id = vals.get('location_id', scrap.location_id.id)
                scrap_location_id = vals.get('scrap_location_id', scrap.scrap_location_id.id)
                
                mts_id = self.env['mts.rejection'].search([
                    ('src_location_id', '=', location_id),
                    ('dest_location_id', '=', scrap_location_id),
                    ('date', '>=', fields.Datetime.now().strftime('%Y-%m-%d 00:00:01')),
                    ('date', '<=', fields.Datetime.now().strftime('%Y-%m-%d 23:59:59'))
                ])

                if mts_id:
                    if len(mts_id) == 1:
                        vals['mts_id'] = mts_id.id
                    else:
                        raise UserError(_("More than one MTS Number created for the location (%s) and date (%s)") % (location_id, fields.Datetime.now().strftime('%Y-%m-%d')))
                else:
                    mts_vals = {
                        'src_location_id': location_id,
                        'dest_location_id': scrap_location_id,
                        'date': fields.Datetime.now()
                    }
                    mts_rej = self.env['mts.rejection'].create(mts_vals)
                    vals['mts_id'] = mts_rej.id

        return super(StockScrap, self).write(vals)
    

    
    mts_id = fields.Many2one("mts.rejection", string="MTS Number", readonly=True)    
