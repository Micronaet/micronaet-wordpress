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
        stock_status = True

        # Pool used:
        excel_pool = self.pool.get('excel.writer')
        product_pool = self.pool.get('product.product')
        
        # ---------------------------------------------------------------------
        #                         Excel report:
        # ---------------------------------------------------------------------
        # Partner:
        ws_name = 'Prodotti'
        row = 0
        header = [
            'Codice', 'Nome', 'Descrizione', 'Cat. Stat.', 'Magazzino', 
            'Immagini'
            ]
        width = [15, 35, 50, 20, 5, 20]

        excel_pool.create_worksheet(ws_name)

        # Load formats:
        f_title = excel_pool.get_format('title')
        f_header = excel_pool.get_format('header')
        f_text = excel_pool.get_format('text')
        f_number = excel_pool.get_format('number')

        # Setup columns
        excel_pool.column_width(ws_name, width)
            
        # Print header
        excel_pool.write_xls_line(
            ws_name, row, header, default_format=f_header)

        product_ids = product_pool.search(cr, uid, [], context=context)
        _logger.warning('Selected product: %s' % len(product_ids))
        import pdb; pdb.set_trace()
        for product in sorted(product_pool.browse(
                cr, uid, product_ids, context=context),
                key = lambda p: (p.default_code, p.name),
                ):

            row += 1
            excel_pool.write_xls_line(
                ws_name, row, [
                    product.default_code or '',
                    product.name,
                    '',
                    product.statistic_category or '',
                    0.0,
                    '',                    
                    ], default_format=f_text)

        return excel_pool.return_attachment(cr, uid, 'web_product')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
