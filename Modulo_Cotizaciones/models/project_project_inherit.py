# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ProjectProject(models.Model):
    _inherit = 'project.project'

    codigo = fields.Char(
        string='Código',
        readonly=True,
        copy=False,
        help='Código único autogenerado para el proyecto'
    )
    cotizacion_template_id = fields.Many2one(
        'sicone.cotizacion.template',
        string='Plantilla de Cotización por Defecto',
        help='Plantilla sugerida para cotizaciones de este proyecto.'
    )
    area_base = fields.Float(string='Área Base (m²)', digits=(12, 2))
    area_cubierta = fields.Float(string='Área Cubierta (m²)', digits=(12, 2))
    area_entrepiso = fields.Float(string='Área Entrepiso (m²)', digits=(12, 2))
    estado = fields.Selection([
        ('prospecto', 'Prospecto'),
        ('cotizacion', 'En Cotización'),
        ('negociacion', 'En Negociación'),
        ('contratado', 'Contratado'),
        ('ejecucion', 'En Ejecución'),
        ('finalizado', 'Finalizado'),
        ('cancelado', 'Cancelado'),
    ], string='Estado', default='prospecto', required=True)
    fecha_creacion = fields.Datetime(string='Fecha de Creación', default=fields.Datetime.now, readonly=True)
    fecha_inicio_estimada = fields.Date(string='Fecha Inicio Estimada')
    fecha_fin_estimada = fields.Date(string='Fecha Fin Estimada')
    usuario_creacion_id = fields.Many2one('res.users', string='Creado por', default=lambda self: self.env.user, readonly=True)
    notas = fields.Text(string='Notas Internas')

    @api.model
    def create(self, vals):
        if not vals.get('codigo'):
            vals['codigo'] = self.env['ir.sequence'].next_by_code('sicone.project') or 'PROY/NEW'
        return super().create(vals)

    @api.constrains('area_base', 'area_cubierta', 'area_entrepiso')
    def _check_areas(self):
        for proyecto in self:
            if proyecto.area_base and proyecto.area_base < 0:
                raise ValidationError('El área base no puede ser negativa')
            if proyecto.area_cubierta and proyecto.area_cubierta < 0:
                raise ValidationError('El área cubierta no puede ser negativa')
            if proyecto.area_entrepiso and proyecto.area_entrepiso < 0:
                raise ValidationError('El área entrepiso no puede ser negativa')

    @api.constrains('fecha_inicio_estimada', 'fecha_fin_estimada')
    def _check_fechas(self):
        for proyecto in self:
            if proyecto.fecha_inicio_estimada and proyecto.fecha_fin_estimada:
                if proyecto.fecha_fin_estimada < proyecto.fecha_inicio_estimada:
                    raise ValidationError('La fecha fin debe ser posterior a la fecha inicio')

    def name_get(self):
        result = []
        for proyecto in self:
            partner = proyecto.partner_id.display_name if proyecto.partner_id else ''
            name = f"[{proyecto.codigo}] {proyecto.name}" if proyecto.codigo else proyecto.name
            if partner:
                name = f"{name} - {partner}"
            result.append((proyecto.id, name))
        return result
