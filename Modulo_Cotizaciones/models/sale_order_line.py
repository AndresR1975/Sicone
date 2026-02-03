from odoo import models, fields

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    materiales = fields.Float(string='Materiales', help='Valor informativo de materiales para la línea')
    equipos = fields.Float(string='Equipos', help='Valor informativo de equipos para la línea')
    mano_obra = fields.Float(string='Mano de Obra', help='Valor informativo de mano de obra para la línea')
