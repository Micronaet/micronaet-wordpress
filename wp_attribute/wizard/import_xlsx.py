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
import base64
from openerp.osv import fields, osv, expression, orm
from datetime import datetime
from openerp.tools.translate import _
from openerp.tools import (
    DEFAULT_SERVER_DATE_FORMAT,
    DEFAULT_SERVER_DATETIME_FORMAT,
    DATETIME_FORMATS_MAP,
    float_compare)
import pdb

_logger = logging.getLogger(__name__)


class ProductProductImportWorpdress(orm.Model):
    """ Model name: Import product for wordpress
    """
    _name = 'product.product.import.wordpress'
    _description = 'Importazione prodotti per Wordpress'
    _order = 'name'

    # Button event:
    def extract_product_in_tree(self, cr, uid, ids, context=None):
        """ Extract element in list
        """
        current_proxy = self.browse(cr, uid, ids, context=context)[0]
        product_ids = [item.id for item in current_proxy.product_ids]

        return {
            'type': 'ir.actions.act_window',
            'name': _('Dettaglio prodotti'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            # 'res_id': 1,
            'res_model': 'product.product',
            'view_id': False,
            'views': [(False, 'tree'), (False, 'form')],
            'domain': [('id', 'in', product_ids)],
            'context': context,
            'target': 'current',  # 'new'
            'nodestroy': False,
            }

    def extract_line_in_tree(self, cr, uid, ids, context=None):
        """ Extract element in list
        """
        model_pool = self.pool.get('ir.model.data')
        tree_id = model_pool.get_object_reference(
            cr, uid,
            'wp_attribute',
            'view_product_product_web_server_wp_parent_tree')[1]
        form_id = model_pool.get_object_reference(
            cr, uid,
            'wp_attribute',
            'view_product_product_web_server_wp_parent_form')[1]

        current_proxy = self.browse(cr, uid, ids, context=context)[0]
        web_ids = [item.id for item in current_proxy.web_ids]

        return {
            'type': 'ir.actions.act_window',
            'name': _('Dettaglio prodotti Master'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            # 'res_id': 1,
            'res_model': 'product.product.web.server',
            'view_id': tree_id,
            'views': [(tree_id, 'tree'), (form_id, 'form')],
            'domain': [
                ('wp_parent_template', '=', True),
                ('id', 'in', web_ids),
            ],
            'context': context,
            'target': 'current',  # 'new'
            'nodestroy': False,
            }

    def action_check_product_file(self, cr, uid, ids, context=None):
        """ Check file and return esit for importation
        """
        return self._import_xlsx_file(
            cr, uid, ids, check=True, context=context)

    def action_import_product(self, cr, uid, ids, context=None):
        """ Create purchase order:
        """
        return self._import_xlsx_file(
            cr, uid, ids, check=False, context=context)

    # Utility:
    def _import_xlsx_file(self, cr, uid, ids, check, context=None):
        """ Utility for import or simply check the file
        """

        def get_foreign_fields(
                cr, uid, table, mode,
                connector_id, fullcode, cache, error_list,
                context=None):
            """ Extract category for category
            """
            foreign_pool = self.pool.get(table)
            if table not in cache:
                cache[table] = {}

            res = []
            for code in fullcode.split(','):
                code = code.strip()
                if not code:
                    _logger.warning(_('Code %s not in %s') % (
                        code, table))
                    continue

                if code not in cache[table]:
                    domain = [('code', '=', code)]
                    if connector_id:
                        domain.append(
                            ('connector_id', '=', connector_id))
                    item_ids = foreign_pool.search(
                        cr, uid, domain, context=context)
                    if item_ids:
                        cache[table][code] = item_ids[0]
                    else:
                        error_list.append(
                            'Codice %s non trovato in %s' % (code, table))
                        continue
                res.append(cache[table][code])

            if not res:
                return False
            elif mode == '2m':
                return [(6, 0, res)]
            else:
                return res[0]

        def number_to_text(value):
            """ Force text number in Excel
            """
            if type(value) in (float, int):
                return '%s' % int(value)
            else:
                return value or ''

        def get_check_value(value):
            """ Extract check box value
                s, S, Y, y, X, x means True
            """
            value = (value or '').upper()
            return (value and value in 'SXY')

        # Parameters:
        xlsx_id = ids[0]

        IT = 'it_IT'
        EN = 'en_US'
        lang_list = (IT, EN)

        # Cache DB:
        cache = {}

        # Pool used:
        product_pool = self.pool.get('product.product')
        web_pool = self.pool.get('product.product.web.server')

        current_proxy = self.browse(cr, uid, xlsx_id, context=context)
        connector_id = current_proxy.connector_id.id
        first_supplier_id = current_proxy.first_supplier_id.id
        row_start = current_proxy.from_line or 1

        # ---------------------------------------------------------------------
        # Save file passed:
        # ---------------------------------------------------------------------
        b64_file = base64.decodestring(current_proxy.file)
        now = datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        filename = '/tmp/tx_%s.xlsx' % now.replace(':', '_').replace('-', '_')
        f = open(filename, 'wb')
        f.write(b64_file)
        f.close()

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
        last_master_id = False  # ID of last master
        pdb.set_trace()
        for row in range(row_start, ws.nrows):
            _logger.info('Reading row: %s' % row)
            lang_text = {IT: {}, EN: {}}
            error_list = []

            # Extract Excel columns:
            is_master = get_check_value(ws.cell(row, 0).value)
            published = not(ws.cell(row, 1).value.strip())
            default_code = number_to_text(ws.cell(row, 2).value).upper()
            ean = ''  # TODO number_to_text(ws.cell(row, 3).value)
            lang_text[IT]['name'] = ws.cell(row, 4).value
            lang_text[EN]['name'] = ws.cell(row, 5).value \
                or lang_text[IT]['name']
            brand_code = ws.cell(row, 6).value
            color_code = ws.cell(row, 7).value
            category_code = ws.cell(row, 8).value
            pricelist = ws.cell(row, 9).value or 0.0
            lifetime_warranty = get_check_value(ws.cell(row, 10).value or '')
            multiply = ws.cell(row, 11).value or 1
            extra_price = ws.cell(row, 12).value or 0.0
            material_code = ws.cell(row, 13).value
            pack_l = ws.cell(row, 14).value or 0.0
            pack_h = ws.cell(row, 15).value or 0.0
            pack_p = ws.cell(row, 16).value or 0.0
            lang_text[IT]['box_dimension'] = ws.cell(row, 17).value
            lang_text[EN]['box_dimension'] = ws.cell(row, 18).value \
                or lang_text[IT]['box_dimension']

            weight = ws.cell(row, 19).value or 0.0
            weight_net = ws.cell(row, 20).value or 0.0
            q_x_pack = ws.cell(row, 21).value or 1

            # Force:
            lang_text[IT]['force_name'] = ws.cell(row, 22).value
            lang_text[EN]['force_name'] = ws.cell(row, 23).value \
                or lang_text[IT]['force_name']
            lang_text[IT]['force_description'] = ws.cell(row, 24).value
            lang_text[EN]['force_description'] = ws.cell(row, 25).value \
                or lang_text[IT]['force_description']
            force_q_x_pack = ws.cell(row, 26).value or False
            force_ean = number_to_text(ws.cell(row, 27).value) or ''
            force_price = ws.cell(row, 28).value or 0.0
            force_discounted = ws.cell(row, 29).value or 0.0
            force_min_stock = ws.cell(row, 30).value or 0.0

            lang_text[IT]['large_description'] = ws.cell(row, 31).value
            lang_text[EN]['large_description'] = ws.cell(row, 32).value \
                or lang_text[IT]['large_description']
            lang_text[IT]['emotional_short_description'] = \
                ws.cell(row, 33).value
            lang_text[EN]['emotional_short_description'] = \
                ws.cell(row, 34).value or \
                lang_text[IT]['emotional_short_description']
            lang_text[IT]['emotional_description'] = ws.cell(row, 35).value
            lang_text[EN]['emotional_description'] = ws.cell(row, 36).value \
                or lang_text[IT]['emotional_description']

            if not default_code:
                _logger.warning('Default code not found')
                continue

            # Calculated foreign keys:
            category_ids = get_foreign_fields(
                cr, uid, 'product.public.category', '2m',
                connector_id, category_code, cache, error_list,
                context=context)

            color_id = get_foreign_fields(
                cr, uid, 'connector.product.color.dot', '2o',
                connector_id, color_code, cache, error_list,
                context=context)

            material_ids = get_foreign_fields(
                cr, uid, 'product.product.web.material', '2m',
                False, material_code, cache, error_list,
                context=context)

            brand_id = get_foreign_fields(
                cr, uid, 'product.product.web.brand', '2o',
                False, brand_code, cache, error_list,
                context=context)

            # TODO check not file system char in default code

            # -----------------------------------------------------------------
            #                      Product operation:
            # -----------------------------------------------------------------
            # Search product:
            product_ids = product_pool.search(cr, uid, [
                ('default_code', '=', default_code)
                ], context=context)
            if len(product_ids) > 1:
                _logger.warning('More material code: %s' % default_code)

            # Non text items:
            product_data = {
                'xlsx_id': xlsx_id,
                'default_code': default_code,
                'q_x_pack': q_x_pack,
                'ean13': ean,
                'lst_price': pricelist,
                'pack_l': pack_l,
                'pack_h': pack_h,
                'pack_p': pack_p,
                'weight': weight,
                'weight_net': weight_net,
            }
            if first_supplier_id:
                product_data['first_supplier_id'] = first_supplier_id

            lang_context = context.copy()
            for lang in lang_list:
                lang_context['lang'] = lang
                product_data.update({
                    'name': lang_text[lang]['name'],
                    'large_description': lang_text[lang]['large_description'],
                    'emotional_short_description':
                        lang_text[lang]['emotional_short_description'],
                    'emotional_description':
                        lang_text[lang]['emotional_description'],
                })
                if product_ids:  # Update record (if exist or for language)
                    # Update only field present:
                    not_used_fields = [
                        field for field in product_data if field not in (
                            'xlsx_id', 'default_code')]

                    for field in not_used_fields:
                        if not product_data[field]:
                            del product_data[field]

                    product_pool.write(
                        cr, uid, product_ids, product_data,
                        context=lang_context)
                else:
                    # For next update save ID:
                    product_ids = [product_pool.create(
                        cr, uid, product_data, context=lang_context)]
            product_id = product_ids[0]

            # -----------------------------------------------------------------
            #                     Web product operation:
            # -----------------------------------------------------------------
            web_ids = web_pool.search(cr, uid, [
                ('connector_id', '=', connector_id),
                ('product_id', '=', product_id),
            ], context=context)

            web_data = {
                'connector_id': connector_id,
                'product_id': product_id,
                'xlsx_id': xlsx_id,

                'wp_type': 'variable',
                'published': published,

                # Foreign keys:
                'wp_color_id': color_id,
                'wordpress_categ_ids': category_ids,
                'material_ids': material_ids,
                'brand_id': brand_id,

                'lifetime_warranty': lifetime_warranty,
                'price_multi': multiply,
                'price_extra': extra_price,

                'weight': weight,
                'weight_net': weight_net,  # No more used!

                # Force:
                'force_ean13': force_ean,
                'force_q_x_pack': force_q_x_pack,
                'force_price': force_price,
                'force_discounted': force_discounted,
                'force_min_stock': force_min_stock,
            }
            for lang in lang_list:
                lang_context['lang'] = lang

                web_data.update({
                    'force_name': lang_text[lang]['force_name'],
                    'force_description': lang_text[lang]['force_description'],
                    'weight_aditional_info': lang_text[lang]['box_dimension'],
                })

                if web_ids:
                    web_pool.write(
                        cr, uid, web_ids, web_data, context=lang_context)
                else:
                    web_ids = [web_pool.create(
                        cr, uid, web_data, context=lang_context)]

            # -----------------------------------------------------------------
            # Update web product data (procedure):
            # -----------------------------------------------------------------
            # 1. Master data:
            if is_master:
                last_master_id = web_ids[0]
                web_pool.write(cr, uid, web_ids, {
                    'wp_parent_template': True,
                    'wp_parent_id': last_master_id,
                }, context=context)
            else:  # Slave:
                web_pool.write(cr, uid, web_ids, {
                    'wp_parent_template': False,
                    'wp_parent_id': last_master_id,
                }, context=context)

            # 2. Volume calc:
            web_pool.update_wp_volume(cr, uid, web_ids, context=context)

        # ---------------------------------------------------------------------
        #                       Closing operation:
        # ---------------------------------------------------------------------
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
            'connector.server', 'Connettore', required=True),
        'first_supplier_id': fields.many2one(
            'res.partner', 'Primo fornitore'),
        'from_line': fields.integer('Da riga', required=1),
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
                DEFAULT_SERVER_DATETIME_FORMAT),
        'mode': lambda *x: 'draft',
        'from_line': lambda *x: 1,
        }


class ProductProductWordpress(orm.Model):
    """ Model name: Product product imported from wordpress
    """

    _inherit = 'product.product'

    _columns = {
        'xlsx_id': fields.many2one(
            'product.product.import.wordpress', 'XLSX File'),
        }


class ProductProductWebServerWordpress(orm.Model):
    """ Model name: Product for webserver
    """

    _inherit = 'product.product.web.server'

    _columns = {
        'xlsx_id': fields.many2one(
            'product.product.import.wordpress', 'XLSX File'),
        }


class ProductProductImportWorpdressRelations(orm.Model):
    """ Model name: PurchaseOrderXLSX for relations
    """
    _inherit = 'product.product.import.wordpress'

    _columns = {
        'product_ids': fields.one2many(
            'product.product', 'xlsx_id', 'Prodotti'),
        'web_ids': fields.one2many(
            'product.product.web.server', 'xlsx_id', 'Prodotti web'),
        }
