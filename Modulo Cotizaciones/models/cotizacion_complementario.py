# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class CotizacionComplementario(models.Model):
    """Items Complementarios (12 ítems incluyendo Tapacanal y Lagrimales)"""
    _name = 'sicone.cotizacion.complementario'
    _description = 'Item Complementario'
    _order = 'version_id, sequence, id'
    
    version_id = fields.Many2one('sicone.cotizacion.version', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(default=10)
    
    nombre = fields.Selection([
        ('aguas_lluvias', 'Red Aguas Lluvias'),
        ('hidrosanitaria', 'Red Hidrosanitaria'),
        ('escalas', 'Estructura Escalas Metálicas'),
        ('campamento', 'Campamento y baño'),
        ('cerramiento', 'Cerramiento en tela'),
        ('canoa_metalica', 'Canoa Metálica'),
        ('ruana_metalica', 'Ruana Metálica'),
        ('tapacanal', 'Tapacanal'),  # NUEVO ítem recurrente
        ('lagrimales', 'Lagrimales'),  # NUEVO ítem recurrente
        ('revoque', 'Revoque'),
        ('fajas_ranuras', 'Fajas, Ranuras y Filetes'),
        ('otros', 'Otros conceptos'),
    ], required=True)
    
    calibre = fields.Char('Calibre', help='Ej: 24, 26. Aplicable a items metálicos como Canoas y Ruanas')
    
    unidad = fields.Selection([('gl', 'gl'), ('m2', 'm²'), ('ml', 'ml'), ('und', 'und')], required=True)
    
    # Campos editables
    cantidad = fields.Float('Cantidad', digits=(12, 2))
    precio_unitario = fields.Monetary('Precio Unitario', currency_field='currency_id')
    
    # Campo calculado
    subtotal = fields.Monetary(compute='_compute_subtotal', store=True, currency_field='currency_id')
    
    currency_id = fields.Many2one('res.currency', related='version_id.currency_id', readonly=True)
    
    @api.depends('cantidad', 'precio_unitario')
    def _compute_subtotal(self):
        for comp in self:
            comp.subtotal = comp.cantidad * comp.precio_unitario
    
    @api.constrains('cantidad')
    def _check_cantidad(self):
        for comp in self:
            if comp.cantidad < 0:
                raise ValidationError('La cantidad no puede ser negativa.')
    
    def name_get(self):
        result = []
        for comp in self:
            nombre = dict(self._fields['nombre'].selection).get(comp.nombre)
            if comp.calibre and comp.nombre in ['canoa_metalica', 'ruana_metalica']:
                nombre = f"{nombre} Calibre {comp.calibre}"
            result.append((comp.id, nombre or 'Complementario'))
        return result
