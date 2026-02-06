from odoo import models, fields, api
from odoo.exceptions import UserError
import base64
import io
import openpyxl

class ImportFCLWizard(models.TransientModel):
    _name = 'import.fcl.wizard'
    _description = 'Wizard para importar movimientos de flujo de caja y crear asientos contables'

    proyecto_id = fields.Many2one('sicone.proyecto', string='Proyecto', required=True)
    sale_order_id = fields.Many2one('sale.order', string='Cotización')
    journal_id = fields.Many2one('account.journal', string='Diario contable', required=True)
    excel_file = fields.Binary(string='Archivo Excel', required=True)
    filename = fields.Char(string='Nombre del archivo')

    def action_import_fcl(self):
        self.ensure_one()
        if not self.excel_file:
            raise UserError('Debe seleccionar un archivo Excel')
        excel_data = base64.b64decode(self.excel_file)
        excel_file = io.BytesIO(excel_data)
        wb = openpyxl.load_workbook(excel_file, data_only=True)
        ws = wb.active
        AccountMove = self.env['account.move']
        AccountMoveLine = self.env['account.move.line']
        for row in ws.iter_rows(min_row=2, values_only=True):
            fecha = row[0]
            concepto = row[1]
            ingreso = row[2] or 0.0
            egreso = row[3] or 0.0
            detalle = row[4] if len(row) > 4 else ''
            if not fecha or (not ingreso and not egreso):
                continue
            # Crear asiento contable por movimiento
            move_vals = {
                'date': fecha,
                'journal_id': self.journal_id.id,
                'ref': concepto,
                'line_ids': []
            }
            # Ingreso: Debe banco, Haber ingreso
            if ingreso:
                move_vals['line_ids'].append((0, 0, {
                    'account_id': self.journal_id.default_debit_account_id.id,
                    'name': concepto,
                    'debit': ingreso,
                    'credit': 0.0,
                    'date': fecha,
                    'ref': detalle,
                }))
                move_vals['line_ids'].append((0, 0, {
                    'account_id': self.journal_id.default_credit_account_id.id,
                    'name': concepto,
                    'debit': 0.0,
                    'credit': ingreso,
                    'date': fecha,
                    'ref': detalle,
                }))
            # Egreso: Debe gasto, Haber banco
            if egreso:
                move_vals['line_ids'].append((0, 0, {
                    'account_id': self.journal_id.default_credit_account_id.id,
                    'name': concepto,
                    'debit': 0.0,
                    'credit': egreso,
                    'date': fecha,
                    'ref': detalle,
                }))
                move_vals['line_ids'].append((0, 0, {
                    'account_id': self.journal_id.default_debit_account_id.id,
                    'name': concepto,
                    'debit': egreso,
                    'credit': 0.0,
                    'date': fecha,
                    'ref': detalle,
                }))
            AccountMove.create(move_vals)
