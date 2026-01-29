# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PrecioReferencia(models.Model):
    """Catálogo de precios históricos y sugeridos"""
    _name = 'sicone.precio.referencia'
    _description = 'Precio de Referencia'
    _order = 'categoria, nombre'
    
    active = fields.Boolean('Activo', default=True)
    
    categoria = fields.Selection([
        ('diseno', 'Diseños y Planificación'),
        ('estructura', 'Estructura'),
        ('mamposteria', 'Mampostería'),
        ('techo', 'Techos'),
        ('cimentacion', 'Cimentación'),
        ('complementario', 'Complementarios'),
        ('personal', 'Personal'),
    ], required=True, index=True)
    
    nombre = fields.Char('Nombre del Item', required=True, index=True)
    unidad = fields.Char('Unidad', help='Ej: m², ml, und, gl')
    
    # Precios unitarios
    precio_materiales = fields.Monetary('Precio Materiales', currency_field='currency_id')
    precio_equipos = fields.Monetary('Precio Equipos', currency_field='currency_id')
    precio_mano_obra = fields.Monetary('Precio Mano de Obra', currency_field='currency_id')
    precio_unitario = fields.Monetary('Precio Unitario Total', currency_field='currency_id',
                                      help='Para items que usan precio único')
    
    # Para personal
    valor_mes = fields.Monetary('Valor/Mes', currency_field='currency_id')
    pct_prestaciones = fields.Float('% Prestaciones', digits=(5, 2), default=54.0)
    
    # Control
    fecha_actualizacion = fields.Date('Última Actualización', default=fields.Date.today)
    notas = fields.Text('Notas')
    
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)
    
    def name_get(self):
        result = []
        for precio in self:
            nombre = f"{precio.nombre}"
            if precio.unidad:
                nombre += f" ({precio.unidad})"
            result.append((precio.id, nombre))
        return result
