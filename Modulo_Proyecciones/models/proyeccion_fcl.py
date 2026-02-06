from odoo import models, fields

class ProyeccionFCL(models.Model):
    _name = 'proyeccion.fcl'
    _description = 'Proyección de Flujo de Caja'

    name = fields.Char(string='Nombre de la Proyección', required=True)
    proyecto_id = fields.Many2one('sicone.proyecto', string='Proyecto', required=True)
    sale_order_id = fields.Many2one('sale.order', string='Cotización', required=True)
    fecha_inicio = fields.Date(string='Fecha de Inicio')
    fecha_fin = fields.Date(string='Fecha de Fin')
    estado = fields.Selection([
        ('borrador', 'Borrador'),
        ('confirmada', 'Confirmada'),
        ('cerrada', 'Cerrada')
    ], string='Estado', default='borrador')
    # Resumen de totales
    total_ingresos = fields.Float(string='Total Ingresos')
    total_egresos = fields.Float(string='Total Egresos')
    saldo_final = fields.Float(string='Saldo Final')
    # Relación a líneas de proyección
    linea_ids = fields.One2many('proyeccion.fcl.linea', 'proyeccion_id', string='Líneas de Proyección')
