from odoo import models, fields

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    capitulo = fields.Char(string='Capítulo', index=True)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    proyecto_id = fields.Many2one(
        'sicone.proyecto',
        string='Proyecto',
        help='Proyecto de construcción asociado a la cotización/venta.'
    )

    cotizacion_template_id = fields.Many2one(
        'sicone.cotizacion.template',
        string='Plantilla de Cotización',
        help='Plantilla de capítulos e ítems para poblar la cotización.'
    )

    def action_load_template_lines(self):
        """
        Pobla las líneas de la cotización con los capítulos (como secciones)
        y los ítems/productos definidos en la plantilla seleccionada.
        Borra las líneas existentes antes de poblar.
        """
        SaleOrderLine = self.env['sale.order.line']
        for order in self:
            if not order.cotizacion_template_id:
                continue
            # Borra líneas existentes
            order.order_line = [(5, 0, 0)]
            for chapter in order.cotizacion_template_id.chapter_ids.sorted(key=lambda c: c.sequence):
                # Agrega línea de sección para el capítulo
                SaleOrderLine.create({
                    'order_id': order.id,
                    'display_type': 'line_section',
                    'name': chapter.name,
                    'sequence': chapter.sequence,
                })
                # Agrega ítems debajo de la sección
                for item in chapter.item_ids.sorted(key=lambda i: i.sequence):
                    SaleOrderLine.create({
                        'order_id': order.id,
                        'product_id': item.product_id.id,
                        'name': item.product_id.display_name,
                        'product_uom_qty': item.quantity or 1.0,
                        'product_uom': item.uom_id.id or item.product_id.uom_id.id,
                        'sequence': item.sequence,
                        'capitulo': chapter.name,
                    })
