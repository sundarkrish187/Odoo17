# -*- coding: utf-8 -*-
{
    'name': "iol_mo",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
Long description of module's purpose
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','web',"mrp","stock","product"],

    # always loaded
    'data': [
        
        'views/views.xml',
        'views/templates.xml',
        'data/sequence_data.xml',
        'views/mrp_production_view.xml',
        'views/product_template_view.xml',
        'views/stock_lot_view.xml',
        'views/mrp_workorder_view.xml',
        'views/reason_code_view.xml',
        'views/mrp_routing_view.xml',
        'views/stock_scrap_view.xml',
        'views/mts_rejection_view.xml',
        'views/stock_location_views.xml',  
        'views/stock_quant_view.xml',  
        'views/base_menus.xml',  
        'views/Injector_label_print.xml',  
        'views/btw_master_view.xml',    
        'wizard/scrapline_view.xml',
        'wizard/injector_label_reprint_view.xml',
        "reports/mts_rejection_report_template.xml",
        "reports/mts_rejection_report.xml",
        
        'security/security.xml',
        'security/ir.model.access.csv',
        #'views/stock_picking_type_view.xml'
    ],

    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml'
    ],

    

}

