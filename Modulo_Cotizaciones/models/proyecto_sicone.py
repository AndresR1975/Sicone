# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    resumen_estructura = fields.Monetary(string="Estructura (Resumen)", readonly=True, currency_field='currency_id')
    resumen_otros = fields.Monetary(string="Otros (Resumen)", readonly=True, currency_field='currency_id')
    resumen_disenos = fields.Monetary(string="Diseños (Resumen)", readonly=True, currency_field='currency_id')

    resumen_total_costo_directo = fields.Monetary(
        string="Total Costo Directo",
        readonly=True,
        currency_field='currency_id',
        compute='_compute_resumen_total_costo_directo'
    )

    # ADMINISTRACIÓN DEL PROYECTO
    comision_ventas = fields.Monetary(string="Comisión Ventas", readonly=True, currency_field='currency_id')
    imprevistos = fields.Monetary(string="Imprevistos", readonly=True, currency_field='currency_id')
    porcentaje_sugerido_admon = fields.Float(string="% Sugerido Admon / Costo", readonly=True)
    vlr_sugerido_admon = fields.Monetary(string="Vlr Sugerido Admon", readonly=True, currency_field='currency_id')
    calculo_admon = fields.Monetary(string="Cálculo Admon", readonly=True, currency_field='currency_id')
    administracion = fields.Monetary(string="Administración", readonly=True, currency_field='currency_id')
    logistica = fields.Monetary(string="Logística", readonly=True, currency_field='currency_id')
    porcentaje_sugerido_utilidad = fields.Float(string="% Sugerido Utilidad / Costo", readonly=True)
    vlr_sugerido_utilidad = fields.Monetary(string="Vlr Sugerido Utilidad", readonly=True, currency_field='currency_id')
    calculo_utilidad = fields.Monetary(string="Cálculo Utilidad", readonly=True, currency_field='currency_id')
    utilidad = fields.Monetary(string="Utilidad", readonly=True, currency_field='currency_id')
    total_aiu = fields.Monetary(string="Total AIU", readonly=True, currency_field='currency_id')

    # VALOR TOTAL DEL PROYECTO
    valor_total_directos = fields.Monetary(string="Directos (Valor Total)", readonly=True, currency_field='currency_id')
    valor_total_aiu = fields.Monetary(string="AIU (Valor Total)", readonly=True, currency_field='currency_id')
    valor_total_subtotal_costo_directo = fields.Monetary(string="Subtotal Costo Directo", readonly=True, currency_field='currency_id')
    valor_total_descuento = fields.Monetary(string="Descuento", readonly=True, currency_field='currency_id')
    valor_total_total_costo_directo = fields.Monetary(string="Total Costo Directo (Valor Total)", readonly=True, currency_field='currency_id')
    valor_total_m2 = fields.Float(string="Valor m²", readonly=True)

    # VALOR TOTAL DEL PROYECTO CON CIMENTACIONES Y COMPLEMENTARIOS
    costo_directo_cim_comp = fields.Monetary(string="Costo Directo (Cim/Comp)", readonly=True, currency_field='currency_id')
    cimentaciones = fields.Monetary(string="Cimentaciones", readonly=True, currency_field='currency_id')
    complementarios = fields.Monetary(string="Complementarios", readonly=True, currency_field='currency_id')
    total_costo_proyecto_cim_comp = fields.Monetary(string="Total Costo Proyecto (Cim/Comp)", readonly=True, currency_field='currency_id')
    valor_m2_cim_comp = fields.Float(string="Valor m² (Cim/Comp)", readonly=True)

    def _compute_resumen_total_costo_directo(self):
        for order in self:
            order.resumen_total_costo_directo = (
                (order.resumen_estructura or 0.0)
                + (order.resumen_otros or 0.0)
                + (order.resumen_disenos or 0.0)
            )


class ProyectoSicone(models.Model):
    """
    Modelo principal para Proyectos SICONE
    Contiene la información general de cada proyecto de construcción
    """
    _name = 'sicone.proyecto'
    _description = 'Proyecto de Construcción SICONE'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'fecha_creacion desc'
    
    # ============================================================================
    # CAMPOS BÁSICOS
    # ============================================================================
    
    name = fields.Char(
        string='Nombre del Proyecto',
        required=True,
        tracking=True,
        help='Nombre identificador del proyecto de construcción'
    )
    
    codigo = fields.Char(
        string='Código',
        readonly=True,
        copy=False,
        help='Código único autogenerado para el proyecto'
    )
    
    active = fields.Boolean(
        string='Activo',
        default=True,
        tracking=True
    )
    
    # ============================================================================
    # INFORMACIÓN DEL CLIENTE
    # ============================================================================
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Contacto Principal',
        required=True,
        tracking=True,
        help='Contacto o empresa principal asociada al proyecto.'
    )
    
    # ============================================================================
    # PLANTILLA DE COTIZACIÓN ASOCIADA (opcional)
    # ============================================================================
    cotizacion_template_id = fields.Many2one(
        'sicone.cotizacion.template',
        string='Plantilla de Cotización por Defecto',
        help='Plantilla sugerida para cotizaciones de este proyecto.'
    )

    # ============================================================================
    # DATOS TÉCNICOS DEL PROYECTO
    # ============================================================================
    
    area_base = fields.Float(
        string='Área Base (m²)',
        digits=(12, 2),
        tracking=True,
        help='Área base del proyecto en metros cuadrados'
    )
    
    area_cubierta = fields.Float(
        string='Área Cubierta (m²)',
        digits=(12, 2),
        tracking=True
    )
    
    area_entrepiso = fields.Float(
        string='Área Entrepiso (m²)',
        digits=(12, 2),
        tracking=True
    )
    
    descripcion = fields.Text(
        string='Descripción del Proyecto',
        tracking=True
    )
    
    # ============================================================================
    # ESTADO Y SEGUIMIENTO
    # ============================================================================
    
    estado = fields.Selection([
        ('prospecto', 'Prospecto'),
        ('cotizacion', 'En Cotización'),
        ('negociacion', 'En Negociación'),
        ('contratado', 'Contratado'),
        ('ejecucion', 'En Ejecución'),
        ('finalizado', 'Finalizado'),
        ('cancelado', 'Cancelado'),
    ], string='Estado', default='prospecto', required=True, tracking=True)
    
    fecha_creacion = fields.Datetime(
        string='Fecha de Creación',
        default=fields.Datetime.now,
        readonly=True
    )
    
    fecha_inicio_estimada = fields.Date(
        string='Fecha Inicio Estimada',
        tracking=True
    )
    
    fecha_fin_estimada = fields.Date(
        string='Fecha Fin Estimada',
        tracking=True
    )
    
    # ============================================================================
    # RELACIONES
    # ============================================================================
    
    # cotizacion_ids = fields.One2many(
    #     'sicone.cotizacion',
    #     'proyecto_id',
    #     string='Cotizaciones'
    # )
    
    # cotizacion_count = fields.Integer(
    #     string='N° Cotizaciones',
    #     compute='_compute_cotizacion_count'
    # )
    
    # ============================================================================
    # CAMPOS DE CONTROL
    # ============================================================================
    
    usuario_creacion_id = fields.Many2one(
        'res.users',
        string='Creado por',
        default=lambda self: self.env.user,
        readonly=True
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        default=lambda self: self.env.company,
        required=True
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        related='company_id.currency_id',
        readonly=True
    )
    
    notas = fields.Text(
        string='Notas Internas'
    )
    
    # ============================================================================
    # MÉTODOS COMPUTE
    # ============================================================================
    
    # @api.depends('cotizacion_ids')
    # def _compute_cotizacion_count(self):
    #     """Calcula el número de cotizaciones asociadas"""
    #     for proyecto in self:
    #         proyecto.cotizacion_count = len(proyecto.cotizacion_ids)
    
    # ============================================================================
    # MÉTODOS CRUD Y CONSTRAINTS
    # ============================================================================
    
    @api.model
    def create(self, vals):
        """Genera código automático al crear"""
        if not vals.get('codigo'):
            vals['codigo'] = self.env['ir.sequence'].next_by_code('sicone.proyecto') or 'PROY/NEW'
        return super(ProyectoSicone, self).create(vals)
    
    @api.constrains('area_base', 'area_cubierta', 'area_entrepiso')
    def _check_areas(self):
        """Valida que las áreas sean positivas"""
        for proyecto in self:
            if proyecto.area_base and proyecto.area_base < 0:
                raise ValidationError('El área base no puede ser negativa')
            if proyecto.area_cubierta and proyecto.area_cubierta < 0:
                raise ValidationError('El área cubierta no puede ser negativa')
            if proyecto.area_entrepiso and proyecto.area_entrepiso < 0:
                raise ValidationError('El área entrepiso no puede ser negativa')
    
    @api.constrains('fecha_inicio_estimada', 'fecha_fin_estimada')
    def _check_fechas(self):
        """Valida que la fecha fin sea posterior a la fecha inicio"""
        for proyecto in self:
            if proyecto.fecha_inicio_estimada and proyecto.fecha_fin_estimada:
                if proyecto.fecha_fin_estimada < proyecto.fecha_inicio_estimada:
                    raise ValidationError('La fecha fin debe ser posterior a la fecha inicio')
    
    # ============================================================================
    # MÉTODOS DE ACCIÓN
    # ============================================================================
    
    # def action_view_cotizaciones(self):
    #     """Abre la vista de cotizaciones del proyecto"""
    #     self.ensure_one()
    #     return {
    #         'name': 'Cotizaciones',
    #         'type': 'ir.actions.act_window',
    #         'res_model': 'sicone.cotizacion',
    #         'view_mode': 'tree,form',
    #         'domain': [('proyecto_id', '=', self.id)],
    #         'context': {
    #             'default_proyecto_id': self.id,
    #             'default_cliente': self.cliente,
    #             'default_direccion': self.direccion,
    #         }
    #     }
    # 
    # def action_crear_cotizacion(self):
    #     """Crea una nueva cotización para este proyecto"""
    #     self.ensure_one()
    #     return {
    #         'name': 'Nueva Cotización',
    #         'type': 'ir.actions.act_window',
    #         'res_model': 'sicone.cotizacion',
    #         'view_mode': 'form',
    #         'target': 'current',
    #         'context': {
    #             'default_proyecto_id': self.id,
    #             'default_cliente': self.cliente,
    #             'default_direccion': self.direccion,
    #         }
    #     }
    
    def name_get(self):
        """Personaliza el nombre mostrado del proyecto"""
        result = []
        for proyecto in self:
            partner = proyecto.partner_id.display_name if proyecto.partner_id else ''
            if proyecto.codigo:
                name = f"[{proyecto.codigo}] {proyecto.name}"
            else:
                name = proyecto.name
            if partner:
                name = f"{name} - {partner}"
            result.append((proyecto.id, name))
        return result
