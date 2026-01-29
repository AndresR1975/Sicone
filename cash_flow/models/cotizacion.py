from odoo import models, fields, api

class CotizacionSicone(models.Model):
    _name = 'cotizador.sicone'
    _description = 'Cotización de Proyecto Sicone'

    name = fields.Char(string='Nombre de la Cotización', required=True)
    cliente = fields.Char(string='Cliente')
    proyecto = fields.Char(string='Proyecto')
    total_costo_directo = fields.Float(string='Total Costo Directo')
    area_base = fields.Float(string='Área Base (m2)')
    fecha_guardado = fields.Datetime(string='Fecha de Guardado', default=fields.Datetime.now)
    datos_json = fields.Text(string='Datos JSON')
