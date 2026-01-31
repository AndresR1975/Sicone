from odoo import models, fields

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    project_name = fields.Char(string='Nombre del Proyecto')
    project_address = fields.Char(string='Dirección del Proyecto')
    project_phone = fields.Char(string='Teléfono del Proyecto')
    business_manager = fields.Char(string='Business Manager')
    contact_method = fields.Char(string='Medio de Contacto')
    area_base = fields.Float(string='Área Base (m²)')
    area_cubierta = fields.Float(string='Área Cubierta (m²)')
    area_entrepiso = fields.Float(string='Área Entrepiso (m²)')
    niveles = fields.Integer(string='Niveles')
    muro_tipo = fields.Selection([
        ('sencillo', 'Sencillo'),
        ('doble', 'Doble'),
        ('otro', 'Otro'),
    ], string='Tipo de Muro')
    project_date = fields.Date(string='Fecha del Proyecto')
