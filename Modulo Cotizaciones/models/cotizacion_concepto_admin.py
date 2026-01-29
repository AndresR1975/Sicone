# -*- coding: utf-8 -*-

from odoo import models, fields, api


class CotizacionConceptoAdmin(models.Model):
    """Conceptos Administrativos con subitems en JSON (11 categorías)"""
    _name = 'sicone.cotizacion.concepto.admin'
    _description = 'Conceptos Administrativos'
    _order = 'version_id, categoria, id'
    
    version_id = fields.Many2one('sicone.cotizacion.version', required=True, ondelete='cascade', index=True)
    
    categoria = fields.Selection([
        ('polizas', 'Pólizas de Seguros'),
        ('pagos_prov', 'Pagos Provisionales'),
        ('pagos_mens', 'Pagos Mensuales'),
        ('dotaciones', 'Dotaciones'),
        ('pagos_obra', 'Pagos de Obra'),
        ('siso', 'SISO - Seguridad Industrial'),
        ('asesores', 'Asesores Externos'),
        ('impuestos', 'Impuestos'),
        ('costos_fijos', 'Costos Fijos'),
        ('descuentos', 'Descuentos'),
        ('terceros', 'Pagos a Terceros'),
    ], required=True)
    
    # Detalle de items en JSON para flexibilidad
    items_detalle = fields.Json(
        'Detalle de Items',
        default={},
        help='Diccionario con {nombre_item: valor}'
    )
    
    # Subtotal calculado
    subtotal = fields.Monetary(
        'Subtotal',
        compute='_compute_subtotal',
        store=True,
        currency_field='currency_id'
    )
    
    currency_id = fields.Many2one('res.currency', related='version_id.currency_id', readonly=True)
    
    @api.depends('items_detalle')
    def _compute_subtotal(self):
        for concepto in self:
            if concepto.items_detalle:
                concepto.subtotal = sum(concepto.items_detalle.values())
            else:
                concepto.subtotal = 0.0
    
    def name_get(self):
        result = []
        for concepto in self:
            nombre = dict(self._fields['categoria'].selection).get(concepto.categoria)
            result.append((concepto.id, nombre or 'Concepto Admin'))
        return result
