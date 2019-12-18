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

class ConnectorServer(orm.Model):
    """ Model name: ConnectorServer
    """    
    _inherit = 'connector.server'

    def extract_wordpress_published_report(self, cr, uid, ids, context=None):
        ''' Extract list of published elements:
        '''
        def get_image_list(self, product, album_ids, context=None):
            ''' Fields function for calculate 
            '''     
            if context is None:
                context = {}
            
            image_mode = context.get('image_mode', 'filename')
                
            res = ''
            for image in product.image_ids:
                if image.album_id.id in album_ids:
                    if image_mode == 'filename':
                        res += u'[%s: %s]' % (
                            image.album_id.code, image.filename)
                    else:        
                        res += u'[%s: %s]' % (
                            image.album_id.code, image.dropbox_link)                            
            return res
        
        stock_status = True

        # Pool used:
        excel_pool = self.pool.get('excel.writer')
        product_pool = self.pool.get('product.product')
        connector_pool = self.pool.get('product.product.web.server')

        # ---------------------------------------------------------------------
        #                         Excel report:
        # ---------------------------------------------------------------------
        connector = self.browse(cr, uid, ids, context=context)[0]
        album_ids = [item.id for item in connector.album_ids]
        
        ws_name = 'Prodotti'
        excel_pool.create_worksheet(ws_name)

        # Load formats:
        excel_format = {
            'title': excel_pool.get_format('title'),
            'header': excel_pool.get_format('header'),
            'black': {
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
            }

        # ---------------------------------------------------------------------
        # Published product:
        # ---------------------------------------------------------------------
        # Width
        excel_pool.column_width(ws_name, [
            5, 15, 20,
            30, 70, 
            30, 70,
            50, 10, 15, 15, 
            10, 10, 
            5, 20, 
            20, 
            40, 40, 
            ])
            
        # Print header
        row = 0
        excel_pool.write_xls_line(
            ws_name, row, [
            'Pubbl.', 'Codice', 'Colore',
            'Nome', 'Descrizione',  
            '(Name)', '(Description)',
            'Categorie', 'Mag.', 'Prezzo ODOO', 'Prezzo WP',
            'Cat. Stat.', 'Peso', 
            'Mod. imb.', 'Imballo',
            'Magazzino', 'Immagini', 'Link',
            ], default_format=excel_format['header'])

        line_ids = connector_pool.search(cr, uid, [
            ('connector_id', '=', connector.id),
            ], context=context)
        _logger.warning('Selected product: %s' % len(line_ids))

        # Italian report:
        grouped = {}
        color_format_all = {}
        selected = {}
        not_selected = []        
        for line in sorted(connector_pool.browse(
                cr, uid, line_ids, context=context), 
                key = lambda p: (
                    p.product_id.default_code, 
                    p.product_id.name),
                ):
            product = line.product_id
            default_code = product.default_code or ''

            # -----------------------------------------------------------------
            # Parameters:
            # -----------------------------------------------------------------
            # Images:    
            image = get_image_list(
                self, product, album_ids, context=context)
            dropbox_image = get_image_list(
                self, product, album_ids, context={'image_mode': 'url'})
                    
            # Stock:        
            stock = int(product.mx_net_mrp_qty)
            locked = int(product.mx_mrp_b_locked)
            net = stock - locked
            published = 'X' if line.published else ''
            if not published:
                color_format = excel_format['yellow']                
            elif net <= 0:
                color_format = excel_format['red']
            else:    
                color_format = excel_format['black']
                #not_selected.append((product, 'no stock'))
                #continue
            
            # -----------------------------------------------------------------
            # Group data:
            # -----------------------------------------------------------------
            default_code6 = default_code[:6].strip()
            if default_code6:
                if default_code6 not in grouped:
                    grouped[default_code6] = []
                grouped[default_code6].append(default_code[6:].strip())
              
            row += 1
            selected[product.id] = row # To update english lang
            color_format_all[product.id] = color_format
            
            # Readability:
            short_description = line.force_name or \
                product.emotional_short_description or \
                product.name or u''

            description = line.force_description or \
                product.emotional_description or \
                product.large_description or u''
            
            odoo_price = line.force_price or product.lst_price
            price = connector_pool.get_wp_price(line)
    
            excel_pool.write_xls_line(
                ws_name, row, [
                    published,
                    default_code,
                    line.wp_color_id.name or '',
                    short_description,  # product.name,
                    description,  # product.large_description or '',  
                    '', 
                    '',     
                    ', '.join(tuple(
                        [c.name for c in line.wordpress_categ_ids])),
                    net,
                    
                    odoo_price,
                    price,
                    product.statistic_category or '',
                    line.weight_net,
                    'X' if product.model_package_id else '',
                    '%s x %s x %s' % (
                        line.pack_l, line.pack_h, line.pack_p),
                    '%s (M. %s - B. %s)' % (net, stock, locked),
                    image,
                    dropbox_image,
                    ], default_format=color_format['text'])


        # English report (integration):
        product_ids = product_pool.search(cr, uid, [
            ('id', 'in', selected.keys()),
            ], context=context)
        _logger.warning('Update English text: %s' % len(product_ids))

        ctx = context.copy()
        ctx['lang'] = 'en_US'
        for product in product_pool.browse(
                cr, uid, product_ids, context=ctx):
                
            row = selected[product.id]
            color_format = color_format_all[product.id]

            # Readability:
            short_description = line.force_name or \
                product.emotional_short_description or \
                product.name or u''

            description = line.force_description or \
                product.emotional_description or \
                product.large_description or u''
                
            excel_pool.write_xls_line(
                ws_name, row, [
                    short_description,  # product.name,
                    description,  # product.large_description or '',  
                    ], default_format=color_format['text'], col=3)

        # ---------------------------------------------------------------------
        # Web Schema
        # ---------------------------------------------------------------------
        ws_name = 'Web schema'
        excel_pool.create_worksheet(ws_name)

        # Width
        excel_pool.column_width(ws_name, [20, 60])

        # Print header
        row = 0
        excel_pool.write_xls_line(
            ws_name, row, [
            'Codice padre', 'Telaio-Colori',
            ], default_format=excel_format['header'])

        for code6 in grouped:
            row += 1
            excel_pool.write_xls_line(
                ws_name, row, [
                    code6,
                    ', '.join(grouped[code6]),
                    ], default_format=excel_format['black']['text'])
        
        # ---------------------------------------------------------------------
        # Not selected product:
        # ---------------------------------------------------------------------
        ws_name = 'Scartati'
        excel_pool.create_worksheet(ws_name)

        # Width
        excel_pool.column_width(ws_name, [15, 40, 30])

        # Print header
        row = 0
        excel_pool.write_xls_line(
            ws_name, row, [
            'Codice', 'Nome', 'Motivo',
            ], default_format=excel_format['header'])

        for product, reason in not_selected:
            row += 1
            excel_pool.write_xls_line(
                ws_name, row, [
                    product.default_code or '',
                    product.name,
                    reason,
                    ], default_format=excel_format['black']['text'])

        # ---------------------------------------------------------------------
        # Removed product:
        # ---------------------------------------------------------------------
        ws_name = 'Non inclusi'
        excel_pool.create_worksheet(ws_name)

        # Width
        excel_pool.column_width(ws_name, [15, 40, 30])
        # TODO Correct?
        product_ids = product_pool.search(cr, uid, [
            ('statistic_category', '!=', 'P01'),
            ], context=context)
        _logger.warning('Not selected product: %s' % len(product_ids))

        # Print header
        row = 0
        excel_pool.write_xls_line(
            ws_name, row, [
            'Codice', 'Nome', 'Categ. stat.',
            ], default_format=excel_format['header'])
        for product in sorted(product_pool.browse(
                cr, uid, product_ids, context=context),
                key = lambda p: (p.default_code, p.name),
                ):

            row += 1
            excel_pool.write_xls_line(
                ws_name, row, [
                    product.default_code or '',
                    product.name,
                    product.statistic_category or '',
                    ], default_format=excel_format['black']['text'])

        return excel_pool.return_attachment(cr, uid, 'web_product')
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
