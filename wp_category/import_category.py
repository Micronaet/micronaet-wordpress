#!/usr/bin/python
# -*- coding: utf-8 -*-
###############################################################################
#
# ODOO (ex OpenERP)
# Open Source Management Solution
# Copyright (C) 2001-2015 Micronaet S.r.l. (<https://micronaet.com>)
# Developer: Nicola Riolini @thebrush (<https://it.linkedin.com/in/thebrush>)
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

import os
import sys
import logging
import openerp
import json
import woocommerce
import openerp.netsvc as netsvc
import openerp.addons.decimal_precision as dp
from openerp.osv import fields, osv, expression, orm
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp import SUPERUSER_ID, api
from openerp import tools
from openerp.tools.translate import _
from openerp.tools.float_utils import float_round as round
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT,
    DEFAULT_SERVER_DATETIME_FORMAT,
    DATETIME_FORMATS_MAP,
    float_compare)


_logger = logging.getLogger(__name__)


class ProductPublicCategory(orm.Model):
    """ Model name: ProductProduct
    """

    _inherit = 'product.public.category'

    _columns = {
        # 'wp_id': fields.integer('Worpress ID'), # replaced!
        'wp_en_id': fields.integer('Worpress ID en'),
        'wp_it_id': fields.integer('Worpress ID it'),
        'wp_es_id': fields.integer('Worpress ID es'),
        'wp_fr_id': fields.integer('Worpress ID fr'),
        'wp_de_id': fields.integer('Worpress ID de'),
        }


class ProductPublicCategory(orm.Model):
    """ Model name: ProductProduct
    """

    _inherit = 'connector.server'

    def clean_and_republish_id_now(self, cr, uid, ids, context=None):
        """ Procedure used for recreate category deleted from backupffice
        """
        category_pool = self.pool.get('product.public.category')
        category_ids = category_pool.search(cr, uid, [
            ('connector_id', '=', ids[0]),
            ], context=context)
        category_pool.write(cr, uid, category_ids, {
            'wp_it_id': False,
            'wp_en_id': False,
            'wp_es_id': False,
            'wp_fr_id': False,
            'wp_de_id': False,
            }, context=context)
        return self.publish_category_now(cr, uid, ids, context=context)

    def publish_category_now(self, cr, uid, ids, context=None):
        """ Publish now button
            Used also for more than one elements (not only button click)
            Note all product must be published on the same web server!
            """
        if context is None:
            context = {}

        _logger.warning('Publish category all on wordpress:')
        default_lang = 'it'

        # ---------------------------------------------------------------------
        #                         WORDPRESS Publish:
        # ---------------------------------------------------------------------
        server_pool = self.pool.get('connector.server')
        category_pool = self.pool.get('product.public.category')

        # =====================================================================
        # Log operation on Excel file:
        # ---------------------------------------------------------------------
        ws_name = 'Chiamate'
        excel_pool = self.pool.get('excel.writer')
        excel_pool.create_worksheet(ws_name)
        excel_pool.set_format()
        excel_format = {
            'title': excel_pool.get_format('title'),
            'header': excel_pool.get_format('header'),
            'text': excel_pool.get_format('text'),
            }
        row = 0
        excel_pool.write_xls_line(ws_name, row, [
            'Commento',
            'Chiamata',
            'End point',
            'Data',
            'Reply',
            ], default_format=excel_format['header'])
        excel_pool.column_width(ws_name, [30, 20, 30, 50, 100])
        # =====================================================================

        # ---------------------------------------------------------------------
        #                        CREATE CATEGORY OPERATION:
        # ---------------------------------------------------------------------
        connector_id = ids[0]
        server_proxy = self.browse(cr, uid, connector_id, context=context)
        data = {'create': [], 'update': []}

        # Read WP Category present:
        wcapi = server_pool.get_wp_connector(
            cr, uid, connector_id, context=context)

        # ---------------------------------------------------------------------
        # Read all category:
        # ---------------------------------------------------------------------
        parameter = {
            'per_page': 10,
            'page': 0,
            }
        current_wp_category = []
        while True:
            parameter['page'] += 1
            call = 'products/categories'
            res = wcapi.get(call, params=parameter).json()

            # =================================================================
            # Excel log:
            # -----------------------------------------------------------------
            row += 1
            excel_pool.write_xls_line(ws_name, row, [
                'Lettura categorie',
                ], default_format=excel_format['title'])
            row += 1
            excel_pool.write_xls_line(ws_name, row, [
                'get',
                call,
                u'%s' % (parameter),
                u'%s' % (res, ),
                ], default_format=excel_format['text'], col=1)
            # =================================================================

            try:
                test_error = res['data']['status'] == 400
                raise osv.except_osv(
                    _('Category error:'),
                    _('Error getting category list: %s' % (res, )),
                    )
            except:
                pass # no error

            if res:
                current_wp_category.extend(res)
            else:
                break

        # ---------------------------------------------------------------------
        # Loading used dict DB
        # ---------------------------------------------------------------------
        odoo_name2id = {} # (name, lang) > ID

        wp_id2name = {} # name > WP ID
        wp_name2id = {} # parent, name, lang > WP ID TODO manage!

        for record in current_wp_category:
            wp_id2name[record['id']] = record['name']
            wp_name2id[(
                record['parent'] or False,
                record['name'],
                record['lang'],
                )] = record['id']

        # ---------------------------------------------------------------------
        #                                Mode IN:
        # ---------------------------------------------------------------------
        # TODO Language management!!!
        if server_proxy.wp_category == 'in':
            wp_id2odoo_id = {} # WP ID 2 ODOO ID (for fast information)
            for odoo_lang in ('it_IT', ):# XXX create only italian? 'en_US'):
                lang = odoo_lang[:2]
                context_lang = context.copy()
                context_lang['lang'] = odoo_lang

                _logger.warning(
                    'Wordpress category import Lang %s' % lang)

                # Sorted so parent first:
                for record in sorted(current_wp_category,
                        key=lambda x: x['parent']):
                    if lang != record['lang']:
                        continue

                    # Readability:
                    wp_id = record['id']
                    wp_parent_id = record['parent'] or False
                    name = record['name']

                    # Save WP ID
                    if lang == default_lang:
                        wp_it_id = wp_id
                    else:
                        wp_it_id = record['translations'][default_lang]

                    category_ids = category_pool.search(cr, uid, [
                        ('connector_id', '=', connector_id),
                        ('wp_%s_id' % default_lang, '=', wp_it_id),
                        ], context=context_lang)
                    if category_ids:
                        odoo_id = category_ids[0]
                        category_pool.write(cr, uid, category_ids, {
                            # No parent update for update (it was created)
                            # 'parent_id': wp_id2odoo_id.get(
                            #    wp_parent_id, False),
                            # 'sequence': record['menu_order'],
                            'name': name,
                            }, context=context_lang)
                        _logger.info('Update %s' % name)
                    else:
                        odoo_id = category_pool.create(cr, uid, {
                            'enabled': True,
                            'connector_id': connector_id,
                            'wp_%s_id' % lang: wp_id,
                            'parent_id': wp_id2odoo_id.get(
                                wp_parent_id, False),
                            'name': name,
                            'sequence': record['menu_order'],
                            }, context=context_lang)
                        _logger.info('Create %s' % name)

                    # Save root parent ID:
                    wp_id2odoo_id[wp_id] = odoo_id
            return True

        # ---------------------------------------------------------------------
        #                                Mode OUT:
        # ---------------------------------------------------------------------
        # A. Read ODOO PARENT category:
        # ---------------------------------------------------------------------
        odoo_child = {}

        for sign in ('=', '!='): # parent, child
            # -----------------------------------------------------------------
            # Search category touched:
            # -----------------------------------------------------------------
            category_ids = category_pool.search(cr, uid, [
                ('connector_id', '=', connector_id),
                ('parent_id', sign, False),
                ], context=context)

            # Loop on language:
            for odoo_lang in ('it_IT', 'en_US'):
                lang = odoo_lang[:2]
                data = {'create': [], 'update': []}
                context_lang = context.copy()
                context_lang['lang'] = odoo_lang

                _logger.warning(
                    'Wordpress export category, lang: %s, mode: %s' % (
                        lang, 'parent' if sign == '=' else 'child'))

                for category in category_pool.browse(
                        cr, uid, category_ids, context=context_lang):
                    # ---------------------------------------------------------
                    # Readability:
                    # ---------------------------------------------------------
                    odoo_id = category.id
                    name = category.name
                    sequence = category.sequence
                    wp_id = eval('category.wp_%s_id' % lang)  # current lang
                    wp_it_id = category.wp_it_id  # reference lang
                    field_id = 'wp_%s_id' % lang  # current field name
                    if sign == '=':  # parent mode
                        parent_wp_id = False
                    else:
                        parent_wp_id = eval('category.parent_id.wp_%s_id' % (
                            lang))

                    record_data = {
                        'name': name,
                        'parent': parent_wp_id or 0,
                        'menu_order': sequence,
                        'display': 'default',
                        'lang': lang,
                        'slug': server_pool.get_lang_slug(name, lang),
                        }
                    if default_lang != lang:  # Add language default ref.
                        record_data['translations'] = {
                            'it': wp_it_id,  # Created before
                            }

                    # Check if present (same name or ID):
                    key = (parent_wp_id, name, lang)
                    if key in wp_name2id:  # check name if present (for use it)
                        wp_id = wp_name2id[key]

                        # Update this wp_id (same name)
                        category_pool.write(cr, uid, [category.id], {
                            field_id: wp_id,
                            }, context=context_lang)

                    if wp_id in wp_id2name: # Update (ID or Name present)
                        record_data['id'] = wp_id
                        data['update'].append(record_data)
                        try:
                            del(wp_id2name[wp_id])
                        except:
                            pass # yet deleted (from Front end?)

                    else: # Create:
                        data['create'].append(record_data)
                        odoo_name2id[(name, lang)] = odoo_id

                # -------------------------------------------------------------
                # Batch create / update depend on language:
                # -------------------------------------------------------------
                call = 'products/categories/batch'
                res = wcapi.post(call, data).json()

                # =============================================================
                # Excel log:
                # -------------------------------------------------------------
                row += 1
                excel_pool.write_xls_line(ws_name, row, [
                    'Aggiornamento batch',
                    ], default_format=excel_format['title'])
                row += 1
                excel_pool.write_xls_line(ws_name, row, [
                    'post',
                    call,
                    u'%s' % (data, ),
                    u'%s' % (res, ),
                    ], default_format=excel_format['text'], col=1)
                # =============================================================

                for record in res.get('create', ()):
                    wp_id = record['id']
                    if not wp_id:
                        # TODO manage error:
                        _logger.error('Not Updated wp_id for %s' % wp_id)
                        continue
                    try:
                        lang = record['lang']
                    except:
                        raise osv.except_osv(
                            _('Wrong response'),
                            _('Record is error? [%s]' % record),
                            )

                    name = record['name']
                    odoo_id = odoo_name2id.get((name, lang), False)
                    if not odoo_id:
                        _logger.error('Not Updated wp_id for %s' % name)
                        continue

                    field_id = 'wp_%s_id' % lang # current field name

                    # Save WP ID in lang correct:
                    category_pool.write(cr, uid, odoo_id, {
                        field_id: wp_id,
                        }, context=context)
                    odoo_name2id[(name, lang)] = odoo_id
                    _logger.info('Updated wp_id for %s' % name)

                # -------------------------------------------------------------
                # Save WP ID in ODOO Category:
                # -------------------------------------------------------------
                for record in res.get('create', ()):
                    wp_id = record['id']
                    if not wp_id:
                        # TODO manage error:
                        _logger.error('Not Updated wp_id for %s' % wp_id)
                        continue

                    name = record['name']

                    odoo_id = odoo_name2id.get((name, lang), False)
                    if not odoo_id:
                        _logger.error('Not Updated wp_id for %s' % name)
                        continue

                    category_pool.write(cr, uid, odoo_id, {
                        'wp_%s_id' % lang: record['id'],
                        }, context=context)
                    _logger.info('Updated wp_id for %s' % name)

        # ---------------------------------------------------------------------
        # Delete category no more present
        # ---------------------------------------------------------------------
        if wp_id2name:
            data = {
                'delete': wp_id2name.keys(),
                }
            try:
                call = 'products/categories/batch'
                res = wcapi.post(call, data).json()

                # =============================================================
                # Excel log:
                # -------------------------------------------------------------
                row += 1
                excel_pool.write_xls_line(ws_name, row, [
                    'Eliminazione non presenti',
                    ], default_format=excel_format['title'])
                row += 1
                excel_pool.write_xls_line(ws_name, row, [
                    'post',
                    call,
                    u'%s' % (data, ),
                    u'%s' % (res, ),
                    ], default_format=excel_format['text'], col=1)
                # =============================================================

            except:
                raise osv.except_osv(
                    _('Error'),
                    _('Wordpress server not answer, timeout!'),
                    )
        # Rerturn log calls:
        return excel_pool.return_attachment(
            cr, uid, 'Log call', name_of_file='call.xlsx', context=context)
        # TODO
        # Check updated
        # Check deleted
        # Update product first category?
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
