from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import calendar
from datetime import datetime

class StockLot(models.Model):
    _inherit = 'stock.lot'

    production_id = fields.Many2one(
        'mrp.production', 'Manufacturing Order',check_company=True)

    lot_prefix=fields.Char('Lot Prefix' )
    lot_number=fields.Char('Lot Number' )
    r_power = fields.Float('Power', digits=(12,2))
    a_power = fields.Float('A.Power', digits=(12,2))
    cyl_value =fields.Float('cyl value', digits=(12,2))
    mtf_value =fields.Float('MTF value', digits=(12,2))
    mtf_rejection =fields.Boolean(default=False)
    microscope_rejection =fields.Boolean(default=False)
    sterilization_batch = fields.Char('Batch Number')
    reflot=fields.Char('Reflot')
    printname=fields.Char('Printname')
    type=fields.Many2one('order.type')
    pouch_labeled=fields.Boolean(default=False)
       
    @api.model_create_multi
    def create(self, vals_list):
        lot = super(StockLot, self).create(vals_list)

        # Expiry date update based on custom field expiration_year
        if lot.product_id.type_of_product in ['injector', 'iol'] and lot.product_id.use_expiration_date:
            mfd_date = lot.create_date
            mfd_month = mfd_date.month
            mfd_year = mfd_date.year

            exp_year = mfd_year + lot.product_id.expiration_year
            exp_month = mfd_month - 1

            if exp_month == 0:
                exp_month = 12
                exp_year -= 1

            last_day = calendar.monthrange(exp_year, exp_month)[1]

            lot.write({'expiration_date': datetime(exp_year, exp_month, last_day).date()})

        
        if lot.production_id:
            if lot.product_id.tracking =='lot':
                if lot.product_id.id == lot.production_id.product_id.id:
                    if len(self.env['stock.lot'].search(['&',('production_id', '=', lot.production_id.id),('product_id','=',lot.product_id.id),('company_id','=',lot.company_id.id)])) > 1:
                        raise ValidationError("You can not create multiple Lot number for single MO.")
                    else:
                        return lot
                else:
                    raise ValidationError("You can not change product")
        else:
            return lot




   

 
