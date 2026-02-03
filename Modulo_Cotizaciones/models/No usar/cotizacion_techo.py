# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class CotizacionTecho(models.Model):
    """Items de Techos y Elementos Constructivos (4 conceptos simplificados)"""
    _name = 'sicone.cotizacion.techo'
    _description = 'Item de Techos y Elementos Constructivos'
    _order = 'version_id, sequence, id'
    
    version_id = fields.Many2one('sicone.cotizacion.version', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(default=10)
    
    nombre = fields.Selection([
        ('cubierta_manto', 'Cubierta, Superboard y Manto'),
        ('cubierta_shingle', 'Cubierta, Superboard y Shingle'),
        ('entrepiso', 'Entrepiso Placa Fácil'),
        ('pergolas', 'Pérgolas y Estructura sin Techo'),
    ], string='Concepto', required=True)
    
    unidad = fields.Selection([('m2', 'm²'), ('ml', 'ml'), ('und', 'und')], default='m2', required=True)
    
    # Campos editables
    cantidad = fields.Float('Cantidad', digits=(12, 2))
    precio_materiales = fields.Monetary('Precio Materiales', currency_field='currency_id')
    precio_equipos = fields.Monetary('Precio Equipos', currency_field='currency_id')
    precio_mano_obra = fields.Monetary('Precio Mano de Obra', currency_field='currency_id')
    
    # Campos calculados
    subtotal_materiales = fields.Monetary(compute='_compute_subtotales', store=True, currency_field='currency_id')
    subtotal_equipos = fields.Monetary(compute='_compute_subtotales', store=True, currency_field='currency_id')
    subtotal_mano_obra = fields.Monetary(compute='_compute_subtotales', store=True, currency_field='currency_id')
    subtotal = fields.Monetary(compute='_compute_subtotales', store=True, currency_field='currency_id')
    
    currency_id = fields.Many2one('res.currency', related='version_id.currency_id', readonly=True)
    
    @api.depends('cantidad', 'precio_materiales', 'precio_equipos', 'precio_mano_obra')
    def _compute_subtotales(self):
        for techo in self:
            techo.subtotal_materiales = techo.cantidad * techo.precio_materiales
            techo.subtotal_equipos = techo.cantidad * techo.precio_equipos
            techo.subtotal_mano_obra = techo.cantidad * techo.precio_mano_obra
            techo.subtotal = techo.subtotal_materiales + techo.subtotal_equipos + techo.subtotal_mano_obra
    
    @api.constrains('cantidad')
    def _check_cantidad(self):
        for techo in self:
            if techo.cantidad <= 0:
                raise ValidationError('La cantidad debe ser mayor a cero.')
    
    def name_get(self):
        result = []
        for techo in self:
            nombre = dict(self._fields['nombre'].selection).get(techo.nombre)
            result.append((techo.id, nombre or 'Techo'))
        return result
