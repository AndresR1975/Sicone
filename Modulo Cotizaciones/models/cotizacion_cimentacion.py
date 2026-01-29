# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class CotizacionCimentacion(models.Model):
    """Items de Cimentación (Opciones 1 y 2 coexisten)"""
    _name = 'sicone.cotizacion.cimentacion'
    _description = 'Item de Cimentación'
    _order = 'version_id, opcion, sequence, id'
    
    version_id = fields.Many2one('sicone.cotizacion.version', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(default=10)
    
    opcion = fields.Selection([
        ('opcion1', 'Opción 1 - Pilas a 3m y 5m'),
        ('opcion2', 'Opción 2 - Pilotes de Apoyo'),
    ], required=True, help='Ambas opciones coexisten, se selecciona una al aprobar')
    
    nombre = fields.Selection([
        ('pilas', 'Pilas a 3m y 5m de profundidad'),
        ('pilotes', 'Pilotes de Apoyo'),
        ('vigas_losa', 'Cimentación Vigas y Losa'),
    ], required=True)
    
    unidad = fields.Selection([('und', 'und'), ('m2', 'm²')], required=True)
    
    # Campos editables
    cantidad = fields.Float('Cantidad', digits=(12, 2))
    precio_unitario = fields.Monetary('Precio Unitario', currency_field='currency_id')
    
    # Campo calculado
    subtotal = fields.Monetary(compute='_compute_subtotal', store=True, currency_field='currency_id')
    
    currency_id = fields.Many2one('res.currency', related='version_id.currency_id', readonly=True)
    
    @api.depends('cantidad', 'precio_unitario')
    def _compute_subtotal(self):
        for cim in self:
            cim.subtotal = cim.cantidad * cim.precio_unitario
    
    @api.constrains('cantidad')
    def _check_cantidad(self):
        for cim in self:
            if cim.cantidad < 0:
                raise ValidationError('La cantidad no puede ser negativa.')
    
    def name_get(self):
        result = []
        for cim in self:
            nombre = dict(self._fields['nombre'].selection).get(cim.nombre)
            opcion = dict(self._fields['opcion'].selection).get(cim.opcion)
            result.append((cim.id, f"{opcion} - {nombre}"))
        return result
