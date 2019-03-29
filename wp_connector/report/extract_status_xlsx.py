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
            res = ''
            for image in product.image_ids:
                if image.album_id.id in album_ids:
                    res += u'[%s: %s]' % (image.album_id.code, image.filename)
            return res        
        
        stock_status = True

        # Pool used:
        excel_pool = self.pool.get('excel.writer')
        product_pool = self.pool.get('product.product')
        
        # ---------------------------------------------------------------------
        #                         Excel report:
        # ---------------------------------------------------------------------
        connector = self.browse(cr, uid, ids, context=context)[0]
        album_ids = [item.id for item in connector.album_ids]
        
        ws_name = 'Prodotti'
        excel_pool.create_worksheet(ws_name)

        # Load formats:
        f_title = excel_pool.get_format('title')
        f_header = excel_pool.get_format('header')
        f_text = excel_pool.get_format('text')
        f_number = excel_pool.get_format('number')

        # ---------------------------------------------------------------------
        # Published product:
        # ---------------------------------------------------------------------
        # Width
        excel_pool.column_width(ws_name, [
            15, 
            30, 70, 
            30, 70,
            15,
            10, 10, 20, 
            20, 40,
            ])
            
        # Print header
        row = 0
        excel_pool.write_xls_line(
            ws_name, row, [
            'Codice', 
            'Nome', 'Descrizione', 
            'Name', 'Description',
            'Prezzo',
            'Cat. Stat.', 'Peso', 'Dimensioni',
            'Magazzino', 'Immagini'            
            ], default_format=f_header)

        product_ids = product_pool.search(cr, uid, [
            ('statistic_category', '=', 'P01'),
            ], context=context)
        #product_ids = product_ids[:100] # XXX Remove
        _logger.warning('Selected product: %s' % len(product_ids))

        # Italian report:
        selected = {}
        not_selected = []
        for product in sorted(product_pool.browse(
                cr, uid, product_ids, context=context),
                key = lambda p: (p.default_code, p.name),
                ):
            
            # -----------------------------------------------------------------
            # Parameters:
            # -----------------------------------------------------------------
            # Images:    
            image = get_image_list(self, product, album_ids, context=context)
                    
            # Stock:        
            stock = int(product.mx_net_mrp_qty)
            locked = int(product.mx_mrp_b_locked)
            net = stock - locked
            if net <= 0:
                not_selected.append((product, 'no stock'))
                continue
                
            row += 1
            selected[product.id] = row # To update english lang
            excel_pool.write_xls_line(
                ws_name, row, [
                    product.default_code or '',
                    product.name,
                    product.large_description or '',  
                    '', 
                    '',            
                    product.lst_price,
                    product.statistic_category or '',
                    product.weight,
                    '%s x %s x %s' % (
                        product.width, product.length, product.height),
                    '%s (M. %s - B. %s)' % (net, stock, locked),
                    image,
                    ], default_format=f_text)


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
            excel_pool.write_xls_line(
                ws_name, row, [
                    product.name,
                    product.large_description or '',  
                    ], default_format=f_text, col=3)
        
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
            ], default_format=f_header)

        for product, reason in not_selected:
            row += 1
            excel_pool.write_xls_line(
                ws_name, row, [
                    product.default_code or '',
                    product.name,
                    reason,
                    ], default_format=f_text)

        # ---------------------------------------------------------------------
        # Removed product:
        # ---------------------------------------------------------------------
        ws_name = 'Non inclusi'
        excel_pool.create_worksheet(ws_name)

        # Width
        excel_pool.column_width(ws_name, [15, 40, 30])

        product_ids = product_pool.search(cr, uid, [
            ('statistic_category', '!=', 'P01'),
            ], context=context)
        _logger.warning('Not selected product: %s' % len(product_ids))

        # Print header
        row = 0
        excel_pool.write_xls_line(
            ws_name, row, [
            'Codice', 'Nome', 'Categ. stat.',
            ], default_format=f_header)
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
                    ], default_format=f_text)

        return excel_pool.return_attachment(cr, uid, 'web_product')
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
