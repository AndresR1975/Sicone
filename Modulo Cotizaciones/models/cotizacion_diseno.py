# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class CotizacionDiseno(models.Model):
    """
    Items de Diseños y Planificación
    Se multiplican por el área base del proyecto
    """
    _name = 'sicone.cotizacion.diseno'
    _description = 'Item de Diseños y Planificación'
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
        default=10,
        help='Orden de visualización'
    )
    
    nombre = fields.Selection([
        ('arq', 'Diseño Arquitectónico'),
        ('estr', 'Diseño Estructural'),
        ('dev', 'Desarrollo del Proyecto'),
        ('vis', 'Visita Técnica'),
    ], string='Concepto', required=True)
    
    # ============================================================================
    # CAMPOS EDITABLES (grises en Excel)
    # ============================================================================
    
    precio_unitario = fields.Monetary(
        string='Precio Unitario ($/m²)',
        currency_field='currency_id',
        help='Se multiplica por área base del proyecto'
    )
    
    # ============================================================================
    # CAMPOS CALCULADOS (blancos en Excel)
    # ============================================================================
    
    area_base = fields.Float(
        string='Área Base (m²)',
        related='version_id.area_base',
        readonly=True,
        help='Área base desde la versión'
    )
    
    subtotal = fields.Monetary(
        string='Subtotal',
        compute='_compute_subtotal',
        store=True,
        currency_field='currency_id',
        help='Precio Unitario × Área Base'
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
    
    @api.depends('precio_unitario', 'version_id.area_base')
    def _compute_subtotal(self):
        """Calcula el subtotal multiplicando precio × área base"""
        for diseno in self:
            area = diseno.version_id.area_base or 0.0
            diseno.subtotal = diseno.precio_unitario * area
    
    # ============================================================================
    # CONSTRAINTS
    # ============================================================================
    
    @api.constrains('precio_unitario')
    def _check_precio(self):
        """Valida que el precio sea no negativo"""
        for diseno in self:
            if diseno.precio_unitario < 0:
                raise ValidationError('El precio unitario no puede ser negativo.')
    
    # ============================================================================
    # MÉTODOS AUXILIARES
    # ============================================================================
    
    def name_get(self):
        """Muestra el nombre del concepto"""
        result = []
        for diseno in self:
            nombre = dict(self._fields['nombre'].selection).get(diseno.nombre)
            result.append((diseno.id, nombre or 'Diseño'))
        return result
