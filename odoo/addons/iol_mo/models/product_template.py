from odoo import fields, models

class ProductTemplate(models.Model):
    _inherit = "product.template"

    
    disallow_multiple_lot_wo = fields.Boolean(string="Disallow Multiple Lot in WO" ,
            help="To restrict multiple lot selection against one MO")
    disallow_multiple_lot_against_blanks_id = fields.Boolean(string="Disallow Lot against made of multiple Blanks Lot" ,
            help="Should not use lathe lot numbers made with multiple blanks lot numbers.")
    disallow_multiple_lot_against_sterile_batch = fields.Boolean(string="Disallow Lot against made of multiple Sterile Batch" ,
            help="Should not use injector Assembly lot numbers made with multiple sterile batch numbers.")
    type_of_product = fields.Selection([('iol', 'IOL'),('injector', 'INJECTOR'),], string='Product Type')
    expiration_year = fields.Integer(string='Expiration Year' )


    allow_negative_stock = fields.Boolean(
        string="Allow Negative Stock",
        help="If this option is not active on this product nor on its "
        "product category and that this product is a stockable product, "
        "then the validation of the related stock moves will be blocked if "
        "the stock level becomes negative with the stock move.",
    )



class ProductCategory(models.Model):
    _inherit = "product.category"

    allow_negative_stock = fields.Boolean(
        string="Allow Negative Stock",
        help="Allow negative stock levels for the stockable products "
        "attached to this category. The options doesn't apply to products "
        "attached to sub-categories of this category.",
    )  