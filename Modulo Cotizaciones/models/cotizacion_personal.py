# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class CotizacionPersonal(models.Model):
    """Personal Profesional, Administrativo y de Planta con cálculo de prestaciones"""
    _name = 'sicone.cotizacion.personal'
    _description = 'Personal Profesional y Administrativo'
    _order = 'version_id, tipo, sequence, id'
    
    version_id = fields.Many2one('sicone.cotizacion.version', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(default=10)
    
    tipo = fields.Selection([
        ('profesional', 'Profesional y Técnico'),
        ('administrativo', 'Administrativo'),
        ('planta', 'Planta y Gestión Ambiental'),
    ], required=True)
    
    nombre = fields.Selection([
        # Profesional
        ('dir_obra', 'Director de Obra'),
        ('sup_tecnico', 'Supervisor Técnico'),
        ('prof_presupuesto', 'Profesional Presupuesto'),
        ('arq_disenador', 'Arquitecto Diseñador'),
        ('oficial_obra', 'Oficial Obra'),
        ('ayudante_obra', 'Ayudante de Obra'),
        # Administrativo
        ('prof_procesos', 'Profesional de Procesos'),
        ('gerente_gral', 'Gerente General'),
        ('compras', 'Compras'),
        ('contabilidad', 'Contabilidad'),
        ('atencion_cliente', 'Atención al Cliente'),
        ('mantenimiento', 'Mantenimiento y Servicios'),
        ('gestion_humana', 'Desarrollo y Gestión Humana'),
        # Planta
        ('admin_planta', 'Personal Administrativo Planta'),
        ('oper_planta', 'Personal Operativo Planta'),
        ('gest_ambiental', 'Personal Gestión Ambiental'),
    ], required=True)
    
    # Campos editables
    cantidad = fields.Integer('Cantidad', default=1)
    valor_mes = fields.Monetary('Valor/Mes Base', currency_field='currency_id')
    pct_prestaciones = fields.Float('% Prestaciones', digits=(5, 2), default=54.0, help='Porcentaje de prestaciones (típicamente 54%)')
    dedicacion = fields.Float('Dedicación', digits=(3, 2), default=0.5, help='Dedicación al proyecto (0.0 a 1.0)')
    meses = fields.Integer('Meses', help='Número de meses de trabajo en el proyecto')
    
    # Campo calculado
    total = fields.Monetary('Total', compute='_compute_total', store=True, currency_field='currency_id',
                           help='Cantidad × Valor/Mes × (1 + %Prest) × Dedicación × Meses')
    
    currency_id = fields.Many2one('res.currency', related='version_id.currency_id', readonly=True)
    
    @api.depends('cantidad', 'valor_mes', 'pct_prestaciones', 'dedicacion', 'meses')
    def _compute_total(self):
        for personal in self:
            personal.total = (
                personal.cantidad *
                personal.valor_mes *
                (1 + personal.pct_prestaciones / 100.0) *
                personal.dedicacion *
                personal.meses
            )
    
    @api.constrains('cantidad', 'meses')
    def _check_valores(self):
        for personal in self:
            if personal.cantidad < 0:
                raise ValidationError('La cantidad no puede ser negativa.')
            if personal.meses < 0:
                raise ValidationError('Los meses no pueden ser negativos.')
    
    @api.constrains('dedicacion')
    def _check_dedicacion(self):
        for personal in self:
            if not (0.0 <= personal.dedicacion <= 1.0):
                raise ValidationError('La dedicación debe estar entre 0.0 y 1.0')
    
    def name_get(self):
        result = []
        for personal in self:
            nombre = dict(self._fields['nombre'].selection).get(personal.nombre)
            result.append((personal.id, nombre or 'Personal'))
        return result
