from odoo import models, fields

class CotizacionPonderada(models.Model):
    _name = 'cotizacion.ponderada'
    _description = 'Cotización Ponderada'

    sale_order_id = fields.Many2one('sale.order', string='Cotización', ondelete='cascade', required=True)
    concepto = fields.Char(string='Concepto', required=True)
    valor = fields.Float(string='Valor', required=True)
    peso = fields.Float(string='Peso', required=True)
