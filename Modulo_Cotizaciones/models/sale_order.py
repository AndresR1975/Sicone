from odoo import models, fields

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    proyecto_id = fields.Many2one(
        'sicone.proyecto',
        string='Proyecto',
        help='Proyecto de construcción asociado a la cotización/venta.'
    )
