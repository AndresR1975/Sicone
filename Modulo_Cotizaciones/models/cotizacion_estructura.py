# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class CotizacionEstructura(models.Model):
    """
    Items de Estructura
    Permite múltiples líneas con precios personalizados
    Cada línea tiene: Materiales, Equipos y Mano de Obra
    """
    _name = 'sicone.cotizacion.estructura'
    _description = 'Item de Estructura'
    _order = 'version_id, sequence, id'
    
    # ============================================================================
    # CAMPOS BÁSICOS
    # ============================================================================
    
    version_id = fields.Many2one(
        'sicone.cotizacion.version',
        string='Versión',
        required=True,
        ondelete='cascade',
        index=True
    )
    
    sequence = fields.Integer(
        string='Secuencia',
        default=10
    )
    
    nombre = fields.Char(
        string='Descripción',
        required=True,
        default='Estructura General',
        help='Permite personalizar el nombre si hay múltiples estructuras'
    )
    
    unidad = fields.Selection([
        ('gl', 'Global'),
        ('m2', 'm²'),
        ('m3', 'm³'),
    ], string='Unidad', default='gl', required=True)
    
    # ============================================================================
    # CAMPOS EDITABLES (grises en Excel)
    # ============================================================================
    
    cantidad = fields.Float(
        string='Cantidad',
        digits=(12, 2),
        default=1.0,
        help='Cantidad en la unidad especificada'
    )
    
    precio_materiales = fields.Monetary(
        string='Precio Materiales',
        currency_field='currency_id',
        help='Valor total o unitario de materiales'
    )
    
    precio_equipos = fields.Monetary(
        string='Precio Equipos',
        currency_field='currency_id',
        help='Valor total o unitario de equipos'
    )
    
    precio_mano_obra = fields.Monetary(
        string='Precio Mano de Obra',
        currency_field='currency_id',
        help='Valor total o unitario de M.O.'
    )
    
    # ============================================================================
    # CAMPOS CALCULADOS (blancos en Excel)
    # ============================================================================
    
    subtotal_materiales = fields.Monetary(
        string='Subtotal Materiales',
        compute='_compute_subtotales',
        store=True,
        currency_field='currency_id'
    )
    
    subtotal_equipos = fields.Monetary(
        string='Subtotal Equipos',
        compute='_compute_subtotales',
        store=True,
        currency_field='currency_id'
    )
    
    subtotal_mano_obra = fields.Monetary(
        string='Subtotal Mano de Obra',
        compute='_compute_subtotales',
        store=True,
        currency_field='currency_id'
    )
    
    subtotal = fields.Monetary(
        string='Subtotal Total',
        compute='_compute_subtotales',
        store=True,
        currency_field='currency_id',
        help='Suma de Materiales + Equipos + Mano de Obra'
    )
    
    # ============================================================================
    # CAMPOS DE CONTROL
    # ============================================================================
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        related='version_id.currency_id',
        readonly=True
    )
    
    # ============================================================================
    # MÉTODOS COMPUTE
    # ============================================================================
    
    @api.depends('cantidad', 'precio_materiales', 'precio_equipos', 'precio_mano_obra')
    def _compute_subtotales(self):
        """Calcula todos los subtotales"""
        for estructura in self:
            estructura.subtotal_materiales = estructura.cantidad * estructura.precio_materiales
            estructura.subtotal_equipos = estructura.cantidad * estructura.precio_equipos
            estructura.subtotal_mano_obra = estructura.cantidad * estructura.precio_mano_obra
            estructura.subtotal = (
                estructura.subtotal_materiales +
                estructura.subtotal_equipos +
                estructura.subtotal_mano_obra
            )
    
    # ============================================================================
    # CONSTRAINTS
    # ============================================================================
    
    @api.constrains('cantidad')
    def _check_cantidad(self):
        """Valida que la cantidad sea positiva"""
        for estructura in self:
            if estructura.cantidad <= 0:
                raise ValidationError('La cantidad debe ser mayor a cero.')
    
    @api.constrains('precio_materiales', 'precio_equipos', 'precio_mano_obra')
    def _check_precios(self):
        """Valida que los precios sean no negativos"""
        for estructura in self:
            if estructura.precio_materiales < 0:
                raise ValidationError('El precio de materiales no puede ser negativo.')
            if estructura.precio_equipos < 0:
                raise ValidationError('El precio de equipos no puede ser negativo.')
            if estructura.precio_mano_obra < 0:
                raise ValidationError('El precio de mano de obra no puede ser negativo.')
    
    # ============================================================================
    # MÉTODOS AUXILIARES
    # ============================================================================
    
    def name_get(self):
        """Muestra el nombre personalizado"""
        result = []
        for estructura in self:
            result.append((estructura.id, estructura.nombre))
        return result
