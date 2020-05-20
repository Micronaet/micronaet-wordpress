# -*- coding: utf-8 -*-
###############################################################################
#
#    Copyright (C) 2001-2014 Micronaet SRL (<http://www.micronaet.it>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
import logging
import xlrd
import xlsxwriter
import base64
from openerp.osv import fields, osv, expression, orm
from datetime import datetime
from openerp.tools.translate import _
from openerp.tools import (
    DEFAULT_SERVER_DATE_FORMAT,
    DEFAULT_SERVER_DATETIME_FORMAT,
    DATETIME_FORMATS_MAP,
    float_compare)

_logger = logging.getLogger(__name__)


class ProductProductImportWorpdress(orm.Model):
    """ Model name: Import product for wordpress
    """
    _name = 'product.product.import.wordpress'
    _description = 'Importazione prodotti per Wordpress'
    _order = 'name'

    # Button event:
    def extract_line_in_tree(self, cr, uid, ids, context=None):
        """ Extract element in list
        """
        current_proxy = self.browse(cr, uid, ids, context=context)[0]
        product_ids = [item.id for item in current_proxy.product_ids]

        return {
            'type': 'ir.actions.act_window',
            'name': _('Righe'),
            'view_type': 'form',
            'view_mode': 'tree',
            # 'res_id': 1,
            'res_model': 'product.product',
            'view_id': False,
            'views': [(False, 'tree'), (False, 'form')],
            'domain': [('id', 'in', product_ids)],
            'context': context,
            'target': 'current',  # 'new'
            'nodestroy': False,
            }

    def action_check_product_file(self, cr, uid, ids, context=None):
        """ Check file and return esit for importation
        """
        return self._import_xlsx_file(cr, uid, ids, check=True, context=None)

    def action_import_product(self, cr, uid, ids, context=None):
        """ Create purchase order:
        """
        return self._import_xlsx_file(cr, uid, ids, check=False, context=None)

    # Utility:
    def _import_xlsx_file(self, cr, uid, ids, check, context=None):
        """ Utility for import or simply check the file
        """
        # Parameters:
        row_start = 1

        # Pool used:
        product_pool = self.pool.get('product.product')
        web_pool = self.pool.get('product.product.web.server')

        current_proxy = self.browse(cr, uid, ids, context=context)[0]
        connector_id = self.connector_id.id

        # ---------------------------------------------------------------------
        # Save file passed:
        # ---------------------------------------------------------------------
        b64_file = base64.decodestring(current_proxy.file)
        now = datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        filename = '/tmp/tx_%s.xlsx' % now.replace(':', '_').replace('-', '_')
        f = open(filename, 'wb')
        f.write(b64_file)
        f.close()

        xslx_id = current_proxy.id

        # ---------------------------------------------------------------------
        # Load force name (for web publish)
        # ---------------------------------------------------------------------
        try:
            wb = xlrd.open_workbook(filename)
        except:
            raise osv.except_osv(
                _('Error XLSX'),
                _('Cannot read XLS file: %s' % filename),
                )

        # ---------------------------------------------------------------------
        # Loop on all pages:
        # ---------------------------------------------------------------------
        ws = wb.sheet_by_index(0)

        error = ''
        for row in range(row_start, ws.nrows):
            lang_text = {
                'it_IT': {},
                'en_US': {},
            }
            parent_mode = ws.cell(row, 0).value
            published = ws.cell(row, 1).value
            default_code = ws.cell(row, 2).value
            ean = ws.cell(row, 3).value
            name_it = ws.cell(row, 4).value
            name_en = ws.cell(row, 5).value or name_it
            brand_code = ws.cell(row, 6).value
            color_code = ws.cell(row, 7).value
            category_code = ws.cell(row, 8).value
            pricelist = ws.cell(row, 9).value
            lifetime_warranty = ws.cell(row, 10).value
            multiply = ws.cell(row, 11).value
            extra_price = ws.cell(row, 12).value
            material_code = ws.cell(row, 13).value
            pack_l = ws.cell(row, 14).value
            pack_h = ws.cell(row, 15).value
            pack_p = ws.cell(row, 16).value
            box_dimension_it = ws.cell(row, 17).value
            box_dimension_en = ws.cell(row, 18).value or box_dimension_it
            weight = ws.cell(row, 19).value
            weight_net = ws.cell(row, 20).value
            q_x_pack = ws.cell(row, 21).value

            force_name_it = ws.cell(row, 22).value
            force_name_en = ws.cell(row, 23).value
            force_description_it = ws.cell(row, 24).value
            force_description_en = ws.cell(row, 25).value
            force_q_x_pack = ws.cell(row, 26).value
            force_q_ean = ws.cell(row, 27).value
            force_price = ws.cell(row, 28).value
            force_min_stock = ws.cell(row, 29).value

            extended_it = ws.cell(row, 30).value
            extended_en = ws.cell(row, 31).value or extended_it
            emotional_short_it = ws.cell(row, 32).value or emotional_short_it
            emotional_short_en = ws.cell(row, 33).value
            emotional_long_it = ws.cell(row, 34).value
            emotional_long_en = ws.cell(row, 35).value or emotional_long_it

            if not default_code:
                _logger.warning('Default code not found')
                continue

            # Search product:
            product_ids = product_pool.search(cr, uid, [
                ('default_code', '=', default_code)
                ], context=context)

            if product_ids:
                insert_mode = 'update'
            else:
                insert_mode = 'create'

            # Product operation:
            # TODO lang management
            product_data = {
                'default_code': default_code,
                'name': name_it,
                'q_x_pack': q_x_pack,
                'web_description': extended_it,
                'emotional_short_description': emotional_short_it,
                'emotional_description': emotional_long_it,

            }

            # Manage product error:
            if not product_ids:
                _logger.error('No product with code: %s' % default_code)
                continue

            elif len(product_ids) > 1:
                _logger.error('More material code: %s' % default_code)
            product_id = product_ids[0]

        _logger.info('Imported: %s' % filename)
        if check:
            if not error:  # if not error change state:
                self.write(cr, uid, ids, {
                    'mode': 'imported',
                    'error': error,
                }, context=context)
        else:
            self.write(cr, uid, ids, {
                'mode': 'created',
                'file': False,  # reset file for clean database!
                'error': error,
                }, context=context)
        return True  # TODO return xlsx result file

    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'file': fields.binary('XLSX file', filters=None),
        'connector_id': fields.many2one(
            'connector.server', 'Connettore'),
        'mode': fields.selection([
            ('draft', 'Draft'),
            ('imported', 'Imported'),
            ('created', 'Created'),
            ], 'Mode'),
        'error': fields.text('Errore'),
        }

    _defaults = {
        'name':
            lambda *a: _('Imported: %s') % datetime.now().strftime(
                DEFAULT_SERVER_DATE_FORMAT),
        'mode': lambda *x: 'draft',
        }


class ProductProductWordpress(orm.Model):
    """ Model name: Product product imported from wordpress
    """

    _inherit = 'product.product'

    _columns = {
        'xlsx_id': fields.many2one(
            'product.product.import.wordpress.wizard', 'XLSX File'),
        }


class ProductProductImportWorpdressRelations(orm.Model):
    """ Model name: PurchaseOrderXLSX for relations
    """
    _inherit = 'product.product.import.wordpress'

    _columns = {
        'product_ids': fields.one2many(
            'product.product', 'xlsx_id', 'Prodotti'),
        }
