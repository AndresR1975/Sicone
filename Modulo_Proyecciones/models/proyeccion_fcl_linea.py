from odoo import models, fields

class ProyeccionFCLLinea(models.Model):
    _name = 'proyeccion.fcl.linea'
    _description = 'Línea de Proyección de Flujo de Caja'

    proyeccion_id = fields.Many2one('proyeccion.fcl', string='Proyección', required=True, ondelete='cascade')
    fecha = fields.Date(string='Fecha')
    concepto = fields.Char(string='Concepto')
    ingreso = fields.Float(string='Ingreso')
    egreso = fields.Float(string='Egreso')
    saldo = fields.Float(string='Saldo')
    detalle = fields.Text(string='Detalle')
