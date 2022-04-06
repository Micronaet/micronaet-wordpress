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
import requests
import json
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

    def button_export_current_status(self, cr, uid, ids, context=None):
        """ Export file in language selected
        """
        excel_pool = self.pool.get('excel.writer')
        web_pool = self.pool.get('product.product.web.server')

        wizard = self.browse(cr, uid, ids, context=context)[0]

        # Wizard parameters:
        connector_id = wizard.connector_id.id
        wizard_langs = wizard.lang_ids

        default_lang = 'it_IT'
        langs = [default_lang]  # Used as default language

        # Generate Lang list for print product:
        counter = {}
        row = 2  # 2 line for header
        counter[default_lang] = row
        for lang in wizard_langs:
            lang_code = lang.code
            if lang_code not in langs:
                langs.append(lang_code)
                row += 1
                counter[lang_code] = row
        row_step = len(langs)

        # ---------------------------------------------------------------------
        #                            Excel file:
        # ---------------------------------------------------------------------
        ws_name = 'Prodotti pubblicati'
        excel_pool.create_worksheet(ws_name)

        # Load formats:
        excel_format = {
            'title': excel_pool.get_format('title'),
            'header': excel_pool.get_format('header'),
            'black': {
                'header': excel_pool.get_format('header_black'),
                'text': excel_pool.get_format('text'),
                'number': excel_pool.get_format('number'),
                },
            'red': {
                'text': excel_pool.get_format('bg_red'),
                'number': excel_pool.get_format('bg_red_number'),
                },
            'yellow': {
                'text': excel_pool.get_format('bg_yellow'),
                'number': excel_pool.get_format('bg_yellow_number'),
                },
            'blue': {
                'header': excel_pool.get_format('header_blue'),
                'text': excel_pool.get_format('bg_blue'),
                'number': excel_pool.get_format('bg_blue_number'),
                },
            'orange': {
                'text': excel_pool.get_format('bg_orange'),
                'number': excel_pool.get_format('bg_orange_number'),
                },
            'grey': {
                'text': excel_pool.get_format('bg_grey'),
                'number': excel_pool.get_format('bg_grey_number'),
                },
            }

        # Width
        excel_pool.column_width(ws_name, [
            10, 7, 8, 15,
            15, 40,
            25, 25, 25,
            10, 9, 9, 10,
            25,
            12, 12, 12,
            25, 12, 12,
            10,
            30, 30, 20,
            12, 10, 10, 10,
            30, 30, 40,
            35, 35, 35, 35, 35,
        ])

        # Print header
        header = [
                '[Lingua]', '[Padre]', 'Pubblicato', '[Codice prodotto]',
                'EAN', '* [Nome prodotto] *',

                '< [Brand] >', '< [Codice Colore] >', '< [Categorie] >',
                'Listino', 'Garanzia vita', 'Moltiplicatore', 'Prezzo extra',
                '< Materiale >',

                'Imballo L', 'Imballo H', 'Imballo P',
                '* Box dimensioni *', 'Peso lordo', 'Peso netto',
                'Q x pack',

                '* Forza Nome *', '* Forza Descrizione *', 'Forza Q x pack',
                'EAN', 'Prezzo', 'Sconto', 'Stock minimo',

                '* Large *', '* Emo short *', '* Emo long *',

                '* Bullet 1 *', '* Bullet 2 *', '* Bullet 3 *', '* Bullet 4 *',
                '* Bullet 5 *',
                ]
        row = 0
        excel_pool.write_xls_line(
            ws_name, row, range(len(header)),
            default_format=excel_format['black']['header'])
        row += 1
        excel_pool.write_xls_line(
            ws_name, row, header,
            default_format=excel_format['blue']['header'])

        # Write comment for help import:
        comment_list = {
            0: {
                u'Indicare la lingua come codice lingua_codice nazione, es.'
                u'it_IT, en_US, fr_FR, de_DE, es_ES, pt_PT':
                    [0],
                u'Indicare con X il prodotto padre e con O il prodotto figlio'
                u'(maiuscolo o minuscolo non importa), i figli sono sempre '
                u'sotto al proprio padre!':
                    [1],
                u'Indicare con X se il prodotto va messo come visibile sul '
                u'sito altrimenti viene pubblicato ma reso privato':
                    [2],
            },
            1: {
                u'In questa colonna vanno messi i codici '
                u'vedere in anagrafica)':
                    [13],
                u'In questa colonna i testi vanno tradotti in base alla riga':
                    [17, 21, 22, 28, 29, 30, 31, 32, 33, 34, 35],
                u'In questa colonna i campi sono obbligatori':
                    [0, 1, 3],
                u'In questa colonna i campi sono obbligatori e tradotti in '
                u'base alla riga':
                    [5],
                u'In questa colonna i campi sono obbligatori e vanno inseriti '
                u'come codici (vedere in anagrafica)':
                    [6, 7, 8],
            },
        }
        for row in comment_list:
            for comment in comment_list[row]:
                for col in comment_list[row][comment]:
                    excel_pool.write_comment(
                        ws_name, row, col, comment)

        # Collect data master - child for report:
        web_product_ids = web_pool.search(cr, uid, [
            ('connector_id', '=', connector_id),
            ('wp_parent_template', '=', True),
        ], context=context)

        # Sort master with after his child:
        product_ids = []
        for web_product in web_pool.browse(
                cr, uid, web_product_ids, context=context):
            product_ids.append(web_product.id)
            for child in web_product.variant_ids:
                if child != web_product:
                    product_ids.append(child.id)

        ctx = context or {}
        for lang in langs:
            ctx['lang'] = lang
            row = counter[lang]
            # todo sorted?
            is_default = lang == default_lang
            for web_product in web_pool.browse(
                    cr, uid, product_ids, context=ctx):
                product = web_product.product_id

                # Blocks:
                if web_product.wordpress_categ_ids:
                    category_block = ', '.join(
                        [c.code for c in web_product.wordpress_categ_ids
                         if c.code])
                else:
                    category_block = ''
                if web_product.material_ids:
                    material_block = ', '.join(
                        [m.code for m in web_product.material_ids
                         if m.code])
                else:
                    material_block = ''
                parent = 'X' if web_product.wp_parent_template else 'O'
                published = 'X' if web_product.wp_parent_template else 'O'
                data = [
                    (lang, excel_format['blue']['text']),

                    ((parent if is_default else ''),
                     excel_format['blue']['text']),

                    ('X' if published else 'O') if is_default else '',

                    (product.default_code if is_default else '',
                     excel_format['blue']['text']),

                    product.ean13 if is_default else '',

                    (product.name, excel_format['orange']['text']),

                    (web_product.brand_id.code if is_default else '',
                     excel_format['grey']['text']),

                    (web_product.wp_color_id.code if is_default else '',
                     excel_format['grey']['text']),

                    (category_block if is_default else '',
                     excel_format['grey']['text']),

                    product.lst_price if is_default else '',
                    web_product.lifetime_warranty if is_default else '',
                    web_product.price_multi if is_default else '',
                    web_product.price_extra if is_default else '',

                    (material_block if is_default else '',
                     excel_format['grey']['text']),

                    product.pack_l if is_default else '',
                    product.pack_h if is_default else '',
                    product.pack_p if is_default else '',

                    (web_product.weight_aditional_info,
                     excel_format['yellow']['text']),

                    product.weight if is_default else '',
                    product.weight_net if is_default else '',
                    product.q_x_pack if is_default else '',

                    (web_product.force_name,
                     excel_format['yellow']['text']),

                    (web_product.force_description,
                     excel_format['yellow']['text']),

                    web_product.force_q_x_pack if is_default else '',
                    web_product.force_ean13 if is_default else '',
                    web_product.force_price if is_default else '',
                    web_product.force_discounted if is_default else '',
                    web_product.force_min_stock if is_default else '',

                    (product.large_description,
                     excel_format['yellow']['text']),

                    (web_product.emotional_short_description,
                     excel_format['yellow']['text']),

                    (web_product.emotional_description,
                     excel_format['yellow']['text']),

                    (web_product.bullet_point_1,
                     excel_format['yellow']['text']),

                    (web_product.bullet_point_2,
                     excel_format['yellow']['text']),

                    (web_product.bullet_point_3,
                     excel_format['yellow']['text']),

                    (web_product.bullet_point_4,
                     excel_format['yellow']['text']),

                    (web_product.bullet_point_5,
                     excel_format['yellow']['text']),
                ]
                excel_pool.write_xls_line(
                    ws_name, row, data,
                    default_format=excel_format['black']['text'])
                row += row_step

        return excel_pool.return_attachment(cr, uid, 'web_product_published')

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
            try:
                code_splitted = fullcode.split(',')
            except:
                return res
            for code in code_splitted:
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

        def get_float(value):
            """ Force text number in Excel
            """
            if type(value) in (float, int):
                return value
            elif type(value) == str:
                try:
                    return float(value.replace(',', '.'))
                except:
                    return 0.0
            else:
                return 0.0

        def get_check_value(value):
            """ Extract check box value
                s, S, Y, y, X, x means True
            """
            try:
                value = (value or '').strip().upper()
            except:
                return False
            return (value and value in 'SXY')

        def translate_text(text, from_code, to_code, uri):
            """ Translate text from lang code to code
            """
            headers = {
                'content-type': 'application/json',
            }

            payload = {
                'jsonrpc': '2.0',
                'params': {
                    'command': 'translate',
                    'parameters': {
                        'text': text, 'from': from_code[:2], 'to': to_code[:2],
            }}}
            response = requests.post(
                uri, headers=headers, data=json.dumps(payload))
            response_json = response.json()
            if response_json['success']:
                return response_json.get('reply', {}).get('translate')
            else:
                _logger.error('Cannot translate: %s' % text)
                return False

        # Parameters:
        xlsx_id = ids[0]
        lang_list = ('it_IT', 'en_US', 'fr_FR')  # todo from table

        # Cache DB:
        cache = {}

        # Pool used:
        product_pool = self.pool.get('product.product')
        web_pool = self.pool.get('product.product.web.server')

        current_proxy = self.browse(cr, uid, xlsx_id, context=context)
        connector_id = current_proxy.connector_id.id
        first_supplier_id = current_proxy.first_supplier_id.id
        row_start = (current_proxy.from_line or 1) - 1
        auto_translate = current_proxy.auto_translate
        no_translate_product = current_proxy.no_translate_product

        if auto_translate:
            translate_uri = current_proxy.translate_uri
            auto_lang_list = [l.code for l in current_proxy.lang_ids]

        translated_fields = (
            'name', 'box_dimension', 'force_name',
            'force_description', 'large_description',
            'emotional_short_description', 'emotional_description',
            'bullet_point_1', 'bullet_point_2',
            'bullet_point_3', 'bullet_point_4', 'bullet_point_5'
        )

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
        for row in range(row_start, ws.nrows):
            _logger.info('\n\nReading row: %s' % row)
            lang_text = {}  # {IT: {}, EN: {}}
            error_list = []

            # Extract Excel columns:
            default_lang = ws.cell(row, 0).value or 'it_IT'
            if default_lang not in lang_list:
                error_list.append(
                    'Codice lingua non trovato %s' % default_lang)
                # todo not raise! (for now yes)
                raise osv.except_osv(
                    _('Error XLSX'),
                    _('Codice lingua non trovato %s' % default_lang),
                )
            lang_text[default_lang] = {}

            is_master = get_check_value(ws.cell(row, 1).value)
            published = get_check_value(ws.cell(row, 2).value)
            default_code = number_to_text(ws.cell(row, 3).value).upper()
            ean = ''  # todo number_to_text(ws.cell(row, 4).value)
            lang_text[default_lang]['name'] = ws.cell(row, 5).value
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
            lang_text[default_lang]['box_dimension'] = ws.cell(row, 17).value
            weight = get_float(ws.cell(row, 18).value)
            weight_net = get_float(ws.cell(row, 19).value)
            q_x_pack = get_float(ws.cell(row, 20).value) or 1

            # Force:
            lang_text[default_lang]['force_name'] = ws.cell(row, 21).value
            lang_text[default_lang]['force_description'] = \
                ws.cell(row, 22).value
            force_q_x_pack = get_float(ws.cell(row, 23).value) or False
            force_ean = number_to_text(ws.cell(row, 24).value) or ''
            force_price = ws.cell(row, 25).value or 0.0
            force_discounted = ws.cell(row, 26).value or 0.0
            force_min_stock = ws.cell(row, 27).value or 0.0
            lang_text[default_lang]['large_description'] = \
                ws.cell(row, 28).value
            lang_text[default_lang]['emotional_short_description'] = \
                ws.cell(row, 29).value
            lang_text[default_lang]['emotional_description'] = \
                ws.cell(row, 30).value

            # Bullet point:
            lang_text[default_lang]['bullet_point_1'] = ws.cell(row, 31).value
            lang_text[default_lang]['bullet_point_2'] = ws.cell(row, 32).value
            lang_text[default_lang]['bullet_point_3'] = ws.cell(row, 33).value
            lang_text[default_lang]['bullet_point_4'] = ws.cell(row, 34).value
            lang_text[default_lang]['bullet_point_5'] = ws.cell(row, 35).value

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

            # todo check not file system char in default code

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
            }

            # Old producut.product not updated:
            if not product_ids:
                product_data.update({
                    'default_code': default_code,
                    'q_x_pack': q_x_pack,
                    'ean13': ean,
                    'lst_price': pricelist,
                    'pack_l': pack_l,
                    'pack_h': pack_h,
                    'pack_p': pack_p,
                    'weight': weight,
                    'weight_net': weight_net,
                    })

                if first_supplier_id:
                    product_data['first_supplier_id'] = first_supplier_id

            # -----------------------------------------------------------------
            # Read other language:
            # -----------------------------------------------------------------
            if auto_translate:
                for lang_code in auto_lang_list:
                    lang_text[lang_code] = {}
                    for field in translated_fields:
                        field_text = lang_text[default_lang][field]
                        translate = ''
                        if field_text:
                            translate = translate_text(
                                field_text, default_lang, lang_code,
                                translate_uri)

                        if translate:
                            lang_text[lang_code][field] = translate
                        else:
                            lang_text[lang_code][field] = field_text

            else:
                for row in range(row + 1, ws.nrows):
                    lang_code = ws.cell(row, 0).value
                    if lang_code not in lang_list:
                        error_list.append(
                            'Codice lingua non trovato %s' % lang_code)
                        # todo not raise! (for now yes)
                        raise osv.except_osv(
                            _('Error XLSX'),
                            _('Codice lingua non trovato %s' % lang_code),
                        )
                    default_code_lang = \
                        number_to_text(ws.cell(row, 3).value).upper()
                    if default_code_lang and default_code_lang != default_code:
                        row -= 1  # Resume previous line for return master loop
                        break
                    lang_text[lang_code] = {}

                    lang_text[lang_code]['name'] = \
                        ws.cell(row, 5).value or \
                        lang_text[default_lang]['name']
                    lang_text[lang_code]['box_dimension'] = \
                        ws.cell(row, 17).value or \
                        lang_text[default_lang]['box_dimension']
                    lang_text[lang_code]['force_name'] = \
                        ws.cell(row, 21).value or \
                        lang_text[default_lang]['force_name']
                    lang_text[lang_code]['force_description'] = \
                        ws.cell(row, 22).value or \
                        lang_text[default_lang]['force_description']
                    lang_text[lang_code]['large_description'] = \
                        ws.cell(row, 28).value or \
                        lang_text[default_lang]['large_description']
                    lang_text[lang_code]['emotional_short_description'] = \
                        ws.cell(row, 29).value or \
                        lang_text[default_lang]['emotional_short_description']
                    lang_text[lang_code]['emotional_description'] = \
                        ws.cell(row, 30).value or \
                        lang_text[default_lang]['emotional_description']
                    lang_text[lang_code]['bullet_point_1'] = \
                        ws.cell(row, 31).value or \
                        lang_text[default_lang]['bullet_point_1']
                    lang_text[lang_code]['bullet_point_2'] = \
                        ws.cell(row, 32).value or \
                        lang_text[default_lang]['bullet_point_2']
                    lang_text[lang_code]['bullet_point_3'] = \
                        ws.cell(row, 33).value or \
                        lang_text[default_lang]['bullet_point_3']
                    lang_text[lang_code]['bullet_point_4'] = \
                        ws.cell(row, 34).value or \
                        lang_text[default_lang]['bullet_point_4']
                    lang_text[lang_code]['bullet_point_5'] = \
                        ws.cell(row, 35).value or \
                        lang_text[default_lang]['bullet_point_5']

            lang_context = context.copy()
            for lang in lang_text:  # Loop only in passed languages
                if no_translate_product and lang != 'it_IT':
                    _logger.warning('Language jumped, not updated product')
                    continue
                lang_context['lang'] = lang

                # -------------------------------------------------------------
                # Product translate terms:
                # -------------------------------------------------------------
                # Translate only new product or check no translate flag:
                if not no_translate_product or not product_ids:
                    product_data.update({
                        'name':
                            lang_text[lang]['name'],
                        'large_description':
                            lang_text[lang]['large_description'],
                        'emotional_short_description':
                            lang_text[lang]['emotional_short_description'],
                        'emotional_description':
                            lang_text[lang]['emotional_description'],
                    })

                if product_ids:  # Update record (if exist or for language)
                    # Clean field not present:
                    not_used_fields = [
                        field for field in product_data if field not in (
                            'xlsx_id', 'default_code')]

                    # Clean empty field before write:
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
            for lang in lang_text:
                lang_context['lang'] = lang

                # -------------------------------------------------------------
                # Web product translate terms:
                # -------------------------------------------------------------
                web_data.update({
                    'force_name': lang_text[lang]['force_name'],
                    'force_description': lang_text[lang]['force_description'],
                    'weight_aditional_info': lang_text[lang]['box_dimension'],
                    'bullet_point_1': lang_text[lang]['bullet_point_1'],
                    'bullet_point_2': lang_text[lang]['bullet_point_2'],
                    'bullet_point_3': lang_text[lang]['bullet_point_3'],
                    'bullet_point_4': lang_text[lang]['bullet_point_4'],
                    'bullet_point_5': lang_text[lang]['bullet_point_5'],
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
        'no_translate_product': fields.boolean(
            'Prodotto non tradurre',
            help='Indica alla impoortazione di non toccare le traduzioni'
                 'della parte salvata in anagrafica prodotto '
                 '(nome, descrizione ecc.)'),
        'auto_translate': fields.boolean('Auto traduzione'),
        'translate_uri': fields.char('URI di traduzione', size=200),
        'lang_ids': fields.many2many(
            'res.lang', 'translate_product_lang_rel',
            'wizard_id', 'lang_id', 'Lingue',
            help='Indicare le lingue extra rispetto a quella default presente'
                 ' nel file'),

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
        'translate_uri':
            lambda *x:
            'http://192.168.1.176:5000/API/v1.0/micronaet/translate',
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
