# -*- coding: utf-8 -*-
from odoo import models, fields, api

class CotizacionTemplate(models.Model):
    _name = 'sicone.cotizacion.template'
    _description = 'Plantilla de Cotización'
    name = fields.Char('Nombre', required=True)
    chapter_ids = fields.One2many('sicone.cotizacion.template.chapter', 'template_id', string='Capítulos')

class CotizacionTemplateChapter(models.Model):
    _name = 'sicone.cotizacion.template.chapter'
    _description = 'Capítulo de Plantilla de Cotización'
    name = fields.Char('Nombre del Capítulo', required=True)
    sequence = fields.Integer('Secuencia', default=10)
    template_id = fields.Many2one('sicone.cotizacion.template', string='Plantilla', required=True, ondelete='cascade')
    item_ids = fields.One2many('sicone.cotizacion.template.item', 'chapter_id', string='Ítems')

class CotizacionTemplateItem(models.Model):
    _name = 'sicone.cotizacion.template.item'
    _description = 'Ítem de Capítulo de Plantilla'
    product_id = fields.Many2one('product.product', string='Producto', required=True)
    chapter_id = fields.Many2one('sicone.cotizacion.template.chapter', string='Capítulo', required=True, ondelete='cascade')
    sequence = fields.Integer('Secuencia', default=10)
    quantity = fields.Float('Cantidad por defecto', default=1.0)
    uom_id = fields.Many2one('uom.uom', string='Unidad de medida')
