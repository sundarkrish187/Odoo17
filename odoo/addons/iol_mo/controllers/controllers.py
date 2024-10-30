# -*- coding: utf-8 -*-
# from odoo import http


# class IolMo(http.Controller):
#     @http.route('/iol_mo/iol_mo', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/iol_mo/iol_mo/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('iol_mo.listing', {
#             'root': '/iol_mo/iol_mo',
#             'objects': http.request.env['iol_mo.iol_mo'].search([]),
#         })

#     @http.route('/iol_mo/iol_mo/objects/<model("iol_mo.iol_mo"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('iol_mo.object', {
#             'object': obj
#         })

