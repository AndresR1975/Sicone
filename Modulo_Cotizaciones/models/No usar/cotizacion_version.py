# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError


class CotizacionVersion(models.Model):
    """
    Modelo de Versiones de Cotización SICONE
    Contiene toda la información detallada de cada versión de cotización
    Incluye los dos capítulos: Cotización y Cimentaciones/Complementarios
    """
    _name = 'sicone.cotizacion.version'
    _description = 'Versión de Cotización'
    _order = 'cotizacion_id, numero_version desc'
    
    # ============================================================================
    # CAMPOS BÁSICOS Y CONTROL
    # ============================================================================
    
    cotizacion_id = fields.Many2one(
        'sicone.cotizacion',
        string='Cotización',
        required=True,
        ondelete='cascade',
        index=True
    )
    
    numero_version = fields.Integer(
        string='Versión #',
        required=True,
        readonly=True
    )
    
    activa = fields.Boolean(
        string='Versión Activa',
        default=False,
        help='Solo puede haber una versión activa por cotización'
    )
    
    fecha_creacion = fields.Datetime(
        string='Fecha de Creación',
        default=fields.Datetime.now,
        readonly=True
    )
    
    usuario_id = fields.Many2one(
        'res.users',
        string='Creado por',
        default=lambda self: self.env.user,
        readonly=True
    )
    
    notas_cambios = fields.Text(
        string='Notas de Cambios',
        help='Descripción de los cambios realizados en esta versión'
    )
    
    # Archivo Excel asociado (opcional)
    archivo_excel_id = fields.Many2one(
        'ir.attachment',
        string='Archivo Excel Cargado',
        help='Archivo Excel desde el cual se importó esta versión'
    )
    
    # ============================================================================
    # DATOS BASE DEL PROYECTO
    # ============================================================================
    
    area_base = fields.Float(
        string='Área Base (m²)',
        digits=(12, 2),
        required=True,
        help='Área base del proyecto - CAMPO CRÍTICO que alimenta cálculos de Diseños'
    )
    
    area_cubierta = fields.Float(
        string='Área Cubierta (m²)',
        digits=(12, 2)
    )
    
    area_entrepiso = fields.Float(
        string='Área Entrepiso (m²)',
        digits=(12, 2)
    )
    
    # ============================================================================
    # CAPÍTULO 1: COTIZACIÓN (Diseños + Estructura + Mampostería + Techos)
    # ============================================================================
    
    # --- Sección 1: Diseños y Planificación (4 conceptos) ---
    diseno_ids = fields.One2many(
        'sicone.cotizacion.diseno',
        'version_id',
        string='Diseños y Planificación',
        help='Diseño Arquitectónico, Estructural, Desarrollo y Visita Técnica'
    )
    
    total_disenos = fields.Monetary(
        string='Total Diseños',
        compute='_compute_capitulo1',
        store=True,
        currency_field='currency_id'
    )
    
    # --- Sección 2: Estructura (permite múltiples líneas) ---
    estructura_ids = fields.One2many(
        'sicone.cotizacion.estructura',
        'version_id',
        string='Estructura',
        help='Permite múltiples líneas de estructura con precios personalizados'
    )
    
    total_estructura = fields.Monetary(
        string='Total Estructura',
        compute='_compute_capitulo1',
        store=True,
        currency_field='currency_id'
    )
    
    # --- Sección 3: Mampostería (permite múltiples líneas) ---
    mamposteria_ids = fields.One2many(
        'sicone.cotizacion.mamposteria',
        'version_id',
        string='Mampostería',
        help='Permite múltiples líneas de mampostería con precios diferentes'
    )
    
    total_mamposteria = fields.Monetary(
        string='Total Mampostería',
        compute='_compute_capitulo1',
        store=True,
        currency_field='currency_id'
    )
    
    # --- Sección 4: Techos y Elementos Constructivos (4 conceptos) ---
    techo_ids = fields.One2many(
        'sicone.cotizacion.techo',
        'version_id',
        string='Techos y Elementos Constructivos',
        help='Cubiertas, Entrepiso, Pérgolas (simplificado a 4 conceptos)'
    )
    
    total_techos = fields.Monetary(
        string='Total Techos',
        compute='_compute_capitulo1',
        store=True,
        currency_field='currency_id'
    )
    
    # --- Subtotal Costos Directos Capítulo 1 ---
    subtotal_costos_directos_cap1 = fields.Monetary(
        string='Subtotal Costos Directos Cap1',
        compute='_compute_capitulo1',
        store=True,
        currency_field='currency_id',
        help='Suma de Diseños + Estructura + Mampostería + Techos'
    )
    
    # --- AIU Capítulo 1 (Editables con valores sugeridos) ---
    cap1_comision_ventas = fields.Monetary(
        string='Cap1 - Comisión Ventas',
        currency_field='currency_id',
        help='Valor editable de comisión de ventas'
    )
    
    cap1_imprevistos = fields.Monetary(
        string='Cap1 - Imprevistos',
        currency_field='currency_id',
        help='Valor editable de imprevistos'
    )
    
    cap1_pct_administracion = fields.Float(
        string='Cap1 - % Administración',
        digits=(5, 2),
        default=27.5,
        help='Porcentaje sugerido de administración (editable)'
    )
    
    cap1_administracion_sugerido = fields.Monetary(
        string='Cap1 - Administración Sugerido',
        compute='_compute_capitulo1',
        currency_field='currency_id',
        help='Valor sugerido calculado automáticamente'
    )
    
    cap1_administracion = fields.Monetary(
        string='Cap1 - Administración',
        currency_field='currency_id',
        help='Valor editable de administración (puede diferir del sugerido)'
    )
    
    cap1_logistica = fields.Monetary(
        string='Cap1 - Logística',
        currency_field='currency_id',
        help='Valor editable de logística'
    )
    
    cap1_pct_utilidad = fields.Float(
        string='Cap1 - % Utilidad',
        digits=(5, 2),
        default=26.6,
        help='Porcentaje sugerido de utilidad (editable)'
    )
    
    cap1_utilidad_sugerido = fields.Monetary(
        string='Cap1 - Utilidad Sugerido',
        compute='_compute_capitulo1',
        currency_field='currency_id',
        help='Valor sugerido calculado automáticamente'
    )
    
    cap1_utilidad = fields.Monetary(
        string='Cap1 - Utilidad',
        currency_field='currency_id',
        help='Valor editable de utilidad (puede diferir del sugerido)'
    )
    
    total_aiu_cap1 = fields.Monetary(
        string='Total AIU Cap1',
        compute='_compute_capitulo1',
        store=True,
        currency_field='currency_id',
        help='Suma de Comisión + Imprevistos + Administración + Logística + Utilidad'
    )
    
    # --- Total Final Capítulo 1 ---
    total_capitulo1 = fields.Monetary(
        string='Total Capítulo 1',
        compute='_compute_capitulo1',
        store=True,
        currency_field='currency_id',
        help='Costos Directos + AIU del Capítulo 1'
    )
    
    # ============================================================================
    # CAPÍTULO 2: CIMENTACIONES Y COMPLEMENTARIOS
    # ============================================================================
    
    # --- Cimentaciones (2 opciones que coexisten, se selecciona 1 al aprobar) ---
    cimentacion_opcion_activa = fields.Selection([
        ('opcion1', 'Opción 1 - Pilas a 3m y 5m'),
        ('opcion2', 'Opción 2 - Pilotes de Apoyo'),
    ], string='Opción de Cimentación Seleccionada',
       help='Se elige al aprobar la cotización. Ambas opciones coexisten en el sistema.')
    
    # Opción 1: Pilas
    cim_op1_ids = fields.One2many(
        'sicone.cotizacion.cimentacion',
        'version_id',
        string='Cimentación Opción 1',
        domain=[('opcion', '=', 'opcion1')]
    )
    
    subtotal_cim_op1 = fields.Monetary(
        string='Subtotal Cim Opción 1',
        compute='_compute_capitulo2',
        store=True,
        currency_field='currency_id'
    )
    
    cim_op1_pct_comision = fields.Float(
        string='Cim Op1 - % Comisión',
        digits=(5, 2),
        default=3.0
    )
    
    cim_op1_pct_aiu = fields.Float(
        string='Cim Op1 - % AIU',
        digits=(5, 2),
        default=47.0
    )
    
    cim_op1_logistica = fields.Monetary(
        string='Cim Op1 - Logística',
        currency_field='currency_id'
    )
    
    total_cim_op1 = fields.Monetary(
        string='Total Cim Opción 1',
        compute='_compute_capitulo2',
        store=True,
        currency_field='currency_id'
    )
    
    # Opción 2: Pilotes
    cim_op2_ids = fields.One2many(
        'sicone.cotizacion.cimentacion',
        'version_id',
        string='Cimentación Opción 2',
        domain=[('opcion', '=', 'opcion2')]
    )
    
    subtotal_cim_op2 = fields.Monetary(
        string='Subtotal Cim Opción 2',
        compute='_compute_capitulo2',
        store=True,
        currency_field='currency_id'
    )
    
    cim_op2_pct_comision = fields.Float(
        string='Cim Op2 - % Comisión',
        digits=(5, 2),
        default=3.0
    )
    
    cim_op2_pct_aiu = fields.Float(
        string='Cim Op2 - % AIU',
        digits=(5, 2),
        default=47.0
    )
    
    cim_op2_logistica = fields.Monetary(
        string='Cim Op2 - Logística',
        currency_field='currency_id'
    )
    
    total_cim_op2 = fields.Monetary(
        string='Total Cim Opción 2',
        compute='_compute_capitulo2',
        store=True,
        currency_field='currency_id'
    )
    
    # --- Complementarios (12 ítems incluyendo Tapacanal y Lagrimales) ---
    complementario_ids = fields.One2many(
        'sicone.cotizacion.complementario',
        'version_id',
        string='Complementarios'
    )
    
    subtotal_complementarios = fields.Monetary(
        string='Subtotal Complementarios',
        compute='_compute_capitulo2',
        store=True,
        currency_field='currency_id'
    )
    
    comp_pct_comision = fields.Float(
        string='Comp - % Comisión',
        digits=(5, 2),
        default=3.0
    )
    
    comp_pct_aiu = fields.Float(
        string='Comp - % AIU',
        digits=(5, 2),
        default=15.0
    )
    
    comp_logistica = fields.Monetary(
        string='Comp - Logística',
        currency_field='currency_id'
    )
    
    total_complementarios = fields.Monetary(
        string='Total Complementarios',
        compute='_compute_capitulo2',
        store=True,
        currency_field='currency_id'
    )
    
    # --- Total Final Capítulo 2 (usando opción seleccionada) ---
    total_capitulo2 = fields.Monetary(
        string='Total Capítulo 2',
        compute='_compute_capitulo2',
        store=True,
        currency_field='currency_id',
        help='Total de la opción de cimentación seleccionada + Complementarios'
    )
    
    # ============================================================================
    # ADMINISTRACIÓN (Personal + Otros Conceptos)
    # ============================================================================
    
    # --- Personal Profesional y Técnico ---
    personal_prof_ids = fields.One2many(
        'sicone.cotizacion.personal',
        'version_id',
        string='Personal Profesional',
        domain=[('tipo', '=', 'profesional')]
    )
    
    # --- Personal Administrativo ---
    personal_admin_ids = fields.One2many(
        'sicone.cotizacion.personal',
        'version_id',
        string='Personal Administrativo',
        domain=[('tipo', '=', 'administrativo')]
    )
    
    # --- Personal Planta y Gestión Ambiental ---
    personal_planta_ids = fields.One2many(
        'sicone.cotizacion.personal',
        'version_id',
        string='Personal Planta',
        domain=[('tipo', '=', 'planta')]
    )
    
    # --- Otros Conceptos Administrativos (11 categorías) ---
    otros_admin_ids = fields.One2many(
        'sicone.cotizacion.concepto.admin',
        'version_id',
        string='Otros Conceptos Administrativos'
    )
    
    # --- Total Administración ---
    total_personal = fields.Monetary(
        string='Total Personal',
        compute='_compute_administracion',
        store=True,
        currency_field='currency_id'
    )
    
    total_otros_admin = fields.Monetary(
        string='Total Otros Conceptos Admin',
        compute='_compute_administracion',
        store=True,
        currency_field='currency_id'
    )
    
    total_administracion = fields.Monetary(
        string='Total Administración',
        compute='_compute_administracion',
        store=True,
        currency_field='currency_id',
        help='Total de Personal + Otros Conceptos Administrativos'
    )
    
    # ============================================================================
    # TOTALES GENERALES
    # ============================================================================
    
    total_general = fields.Monetary(
        string='Total General Cotización',
        compute='_compute_totales_generales',
        store=True,
        currency_field='currency_id',
        help='Suma de ambos capítulos'
    )
    
    # ============================================================================
    # CAMPOS DE CONTROL
    # ============================================================================
    
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        related='cotizacion_id.company_id',
        store=True,
        readonly=True
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        related='company_id.currency_id',
        readonly=True
    )
    
    # ============================================================================
    # MÉTODOS COMPUTE - CAPÍTULO 1
    # ============================================================================
    
    @api.depends(
        'diseno_ids.subtotal',
        'estructura_ids.subtotal',
        'mamposteria_ids.subtotal',
        'techo_ids.subtotal',
        'cap1_comision_ventas',
        'cap1_imprevistos',
        'cap1_administracion',
        'cap1_logistica',
        'cap1_utilidad',
        'cap1_pct_administracion',
        'cap1_pct_utilidad'
    )
    def _compute_capitulo1(self):
        """Calcula todos los totales del Capítulo 1"""
        for version in self:
            # Sumar todas las líneas de cada sección
            version.total_disenos = sum(version.diseno_ids.mapped('subtotal'))
            version.total_estructura = sum(version.estructura_ids.mapped('subtotal'))
            version.total_mamposteria = sum(version.mamposteria_ids.mapped('subtotal'))
            version.total_techos = sum(version.techo_ids.mapped('subtotal'))
            
            # Subtotal costos directos
            version.subtotal_costos_directos_cap1 = (
                version.total_disenos +
                version.total_estructura +
                version.total_mamposteria +
                version.total_techos
            )
            
            # Valores sugeridos de AIU
            if version.subtotal_costos_directos_cap1:
                version.cap1_administracion_sugerido = (
                    version.subtotal_costos_directos_cap1 * 
                    (version.cap1_pct_administracion / 100.0)
                )
                version.cap1_utilidad_sugerido = (
                    version.subtotal_costos_directos_cap1 * 
                    (version.cap1_pct_utilidad / 100.0)
                )
            else:
                version.cap1_administracion_sugerido = 0.0
                version.cap1_utilidad_sugerido = 0.0
            
            # Total AIU (usando valores editables finales)
            version.total_aiu_cap1 = (
                version.cap1_comision_ventas +
                version.cap1_imprevistos +
                version.cap1_administracion +
                version.cap1_logistica +
                version.cap1_utilidad
            )
            
            # Total final capítulo 1
            version.total_capitulo1 = (
                version.subtotal_costos_directos_cap1 + 
                version.total_aiu_cap1
            )
    
    # ============================================================================
    # MÉTODOS COMPUTE - CAPÍTULO 2
    # ============================================================================
    
    @api.depends(
        'cim_op1_ids.subtotal',
        'cim_op1_pct_comision',
        'cim_op1_pct_aiu',
        'cim_op1_logistica',
        'cim_op2_ids.subtotal',
        'cim_op2_pct_comision',
        'cim_op2_pct_aiu',
        'cim_op2_logistica',
        'complementario_ids.subtotal',
        'comp_pct_comision',
        'comp_pct_aiu',
        'comp_logistica',
        'cimentacion_opcion_activa'
    )
    def _compute_capitulo2(self):
        """Calcula todos los totales del Capítulo 2"""
        for version in self:
            # --- Cimentación Opción 1 ---
            version.subtotal_cim_op1 = sum(version.cim_op1_ids.mapped('subtotal'))
            
            if version.subtotal_cim_op1:
                comision_op1 = version.subtotal_cim_op1 * (version.cim_op1_pct_comision / 100.0)
                aiu_op1 = version.subtotal_cim_op1 * (version.cim_op1_pct_aiu / 100.0)
                version.total_cim_op1 = (
                    version.subtotal_cim_op1 + 
                    comision_op1 + 
                    aiu_op1 + 
                    version.cim_op1_logistica
                )
            else:
                version.total_cim_op1 = 0.0
            
            # --- Cimentación Opción 2 ---
            version.subtotal_cim_op2 = sum(version.cim_op2_ids.mapped('subtotal'))
            
            if version.subtotal_cim_op2:
                comision_op2 = version.subtotal_cim_op2 * (version.cim_op2_pct_comision / 100.0)
                aiu_op2 = version.subtotal_cim_op2 * (version.cim_op2_pct_aiu / 100.0)
                version.total_cim_op2 = (
                    version.subtotal_cim_op2 + 
                    comision_op2 + 
                    aiu_op2 + 
                    version.cim_op2_logistica
                )
            else:
                version.total_cim_op2 = 0.0
            
            # --- Complementarios ---
            version.subtotal_complementarios = sum(version.complementario_ids.mapped('subtotal'))
            
            if version.subtotal_complementarios:
                comision_comp = version.subtotal_complementarios * (version.comp_pct_comision / 100.0)
                aiu_comp = version.subtotal_complementarios * (version.comp_pct_aiu / 100.0)
                version.total_complementarios = (
                    version.subtotal_complementarios + 
                    comision_comp + 
                    aiu_comp + 
                    version.comp_logistica
                )
            else:
                version.total_complementarios = 0.0
            
            # --- Total Capítulo 2 (según opción seleccionada) ---
            if version.cimentacion_opcion_activa == 'opcion1':
                total_cimentacion = version.total_cim_op1
            elif version.cimentacion_opcion_activa == 'opcion2':
                total_cimentacion = version.total_cim_op2
            else:
                # Si no hay opción seleccionada, usar la mayor
                total_cimentacion = max(version.total_cim_op1, version.total_cim_op2)
            
            version.total_capitulo2 = total_cimentacion + version.total_complementarios
    
    # ============================================================================
    # MÉTODOS COMPUTE - ADMINISTRACIÓN
    # ============================================================================
    
    @api.depends(
        'personal_prof_ids.total',
        'personal_admin_ids.total',
        'personal_planta_ids.total',
        'otros_admin_ids.subtotal'
    )
    def _compute_administracion(self):
        """Calcula totales de administración"""
        for version in self:
            total_prof = sum(version.personal_prof_ids.mapped('total'))
            total_admin = sum(version.personal_admin_ids.mapped('total'))
            total_planta = sum(version.personal_planta_ids.mapped('total'))
            
            version.total_personal = total_prof + total_admin + total_planta
            version.total_otros_admin = sum(version.otros_admin_ids.mapped('subtotal'))
            version.total_administracion = version.total_personal + version.total_otros_admin
    
    # ============================================================================
    # MÉTODOS COMPUTE - TOTALES GENERALES
    # ============================================================================
    
    @api.depends('total_capitulo1', 'total_capitulo2')
    def _compute_totales_generales(self):
        """Calcula el total general de la cotización"""
        for version in self:
            version.total_general = version.total_capitulo1 + version.total_capitulo2
    
    # ============================================================================
    # CONSTRAINTS Y VALIDACIONES
    # ============================================================================
    
    @api.constrains('activa', 'cotizacion_id')
    def _check_unica_version_activa(self):
        """Valida que solo haya una versión activa por cotización"""
        for version in self:
            if version.activa:
                otras_activas = self.search([
                    ('cotizacion_id', '=', version.cotizacion_id.id),
                    ('activa', '=', True),
                    ('id', '!=', version.id)
                ])
                if otras_activas:
                    raise ValidationError(
                        'Solo puede haber una versión activa por cotización. '
                        'Desactive primero la versión actual.'
                    )
    
    @api.constrains('area_base')
    def _check_area_base(self):
        """Valida que el área base sea positiva"""
        for version in self:
            if version.area_base <= 0:
                raise ValidationError('El área base debe ser mayor a cero.')
    
    @api.constrains('numero_version')
    def _check_numero_version(self):
        """Valida que el número de versión sea único por cotización"""
        for version in self:
            duplicados = self.search([
                ('cotizacion_id', '=', version.cotizacion_id.id),
                ('numero_version', '=', version.numero_version),
                ('id', '!=', version.id)
            ])
            if duplicados:
                raise ValidationError(
                    f'Ya existe una versión #{version.numero_version} '
                    f'para esta cotización.'
                )
    
    # ============================================================================
    # MÉTODOS CRUD
    # ============================================================================
    
    def write(self, vals):
        """Validaciones al modificar"""
        # Si se desactiva una versión, no debe haber activas
        if 'activa' in vals and not vals['activa']:
            for version in self:
                if version.cotizacion_id.version_activa_id == version:
                    raise UserError(
                        'No puede desactivar la versión activa sin activar otra. '
                        'Active primero una versión diferente.'
                    )
        
        return super(CotizacionVersion, self).write(vals)
    
    def copy(self, default=None):
        """Personaliza la duplicación de versiones"""
        default = dict(default or {})
        default.update({
            'activa': False,
            'fecha_creacion': fields.Datetime.now(),
            'usuario_id': self.env.user.id,
        })
        return super(CotizacionVersion, self).copy(default)
    
    # ============================================================================
    # MÉTODOS DE ACCIÓN
    # ============================================================================
    
    def action_activar_version(self):
        """Activa esta versión y desactiva las demás"""
        self.ensure_one()
        
        # Desactivar todas las versiones de esta cotización
        self.cotizacion_id.version_ids.write({'activa': False})
        
        # Activar esta versión
        self.activa = True
        
        # Actualizar número de versión activa en la cotización
        self.cotizacion_id.version_activa_numero = self.numero_version
    
    def action_copiar_desde_sugeridos(self):
        """Copia los valores sugeridos a los campos editables de AIU Cap1"""
        self.ensure_one()
        self.cap1_administracion = self.cap1_administracion_sugerido
        self.cap1_utilidad = self.cap1_utilidad_sugerido
    
    def action_seleccionar_opcion_cimentacion(self):
        """Wizard para seleccionar opción de cimentación"""
        self.ensure_one()
        return {
            'name': 'Seleccionar Opción de Cimentación',
            'type': 'ir.actions.act_window',
            'res_model': 'sicone.wizard.seleccionar.cimentacion',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_version_id': self.id}
        }
    
    def name_get(self):
        """Personaliza el nombre mostrado de la versión"""
        result = []
        for version in self:
            activa = ' (ACTIVA)' if version.activa else ''
            name = f"{version.cotizacion_id.name} - V{version.numero_version}{activa}"
            result.append((version.id, name))
        return result

