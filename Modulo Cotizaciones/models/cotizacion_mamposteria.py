# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class CotizacionMamposteria(models.Model):
    """
    Items de Mampostería
    Permite múltiples líneas con precios diferentes por m²
    Cada línea tiene: Materiales, Equipos y Mano de Obra
    """
    _name = 'sicone.cotizacion.mamposteria'
    _description = 'Item de Mampostería'
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
        default='Mampostería',
        help='Ej: Mampostería Muro Exterior, Mampostería Muro Interior'
    )
    
    unidad = fields.Selection([
        ('m2', 'm²'),
    ], string='Unidad', default='m2', required=True)
    
    # ============================================================================
    # CAMPOS EDITABLES (grises en Excel)
    # ============================================================================
    
    cantidad = fields.Float(
        string='Cantidad (m²)',
        digits=(12, 2),
        help='Área total de mampostería en metros cuadrados'
    )
    
    precio_materiales = fields.Monetary(
        string='Precio Materiales ($/m²)',
        currency_field='currency_id',
        help='Precio de materiales por metro cuadrado'
    )
    
    precio_equipos = fields.Monetary(
        string='Precio Equipos ($/m²)',
        currency_field='currency_id',
        help='Precio de equipos por metro cuadrado'
    )
    
    precio_mano_obra = fields.Monetary(
        string='Precio Mano de Obra ($/m²)',
        currency_field='currency_id',
        help='Precio de mano de obra por metro cuadrado'
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
        for mamposteria in self:
            mamposteria.subtotal_materiales = mamposteria.cantidad * mamposteria.precio_materiales
            mamposteria.subtotal_equipos = mamposteria.cantidad * mamposteria.precio_equipos
            mamposteria.subtotal_mano_obra = mamposteria.cantidad * mamposteria.precio_mano_obra
            mamposteria.subtotal = (
                mamposteria.subtotal_materiales +
                mamposteria.subtotal_equipos +
                mamposteria.subtotal_mano_obra
            )
    
    # ============================================================================
    # CONSTRAINTS
    # ============================================================================
    
    @api.constrains('cantidad')
    def _check_cantidad(self):
        """Valida que la cantidad sea positiva"""
        for mamposteria in self:
            if mamposteria.cantidad <= 0:
                raise ValidationError('La cantidad debe ser mayor a cero.')
    
    @api.constrains('precio_materiales', 'precio_equipos', 'precio_mano_obra')
    def _check_precios(self):
        """Valida que los precios sean no negativos"""
        for mamposteria in self:
            if mamposteria.precio_materiales < 0:
                raise ValidationError('El precio de materiales no puede ser negativo.')
            if mamposteria.precio_equipos < 0:
                raise ValidationError('El precio de equipos no puede ser negativo.')
            if mamposteria.precio_mano_obra < 0:
                raise ValidationError('El precio de mano de obra no puede ser negativo.')
    
    # ============================================================================
    # MÉTODOS AUXILIARES
    # ============================================================================
    
    def name_get(self):
        """Muestra el nombre personalizado"""
        result = []
        for mamposteria in self:
            result.append((mamposteria.id, mamposteria.nombre))
        return result
