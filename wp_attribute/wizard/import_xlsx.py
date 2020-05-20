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
import os
import sys
import logging
import openerp
import xlrd
import base64
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


class ProductProductImportWorpdress(orm.Model):
    """ Model name: Import product for wordpress
    """
    _name = 'product.product.import.wordpress'
    _description = 'Importazione prodotti per Wordpress'
    _order = 'name'

    # --------------------
    # Button event:
    # --------------------
    def extract_line_in_tree(self, cr, uid, ids, context=None):
        """ Extract element in list
        """
        current_proxy = self.browse(cr, uid, ids, context=context)[0]
        line_ids = [item.id for item in current_proxy.line_ids]

        return {
            'type': 'ir.actions.act_window',
            'name': _('Righe'),
            'view_type': 'form',
            'view_mode': 'tree',
            # 'res_id': 1,
            'res_model': 'product.product',
            'view_id': False,
            'views': [(False, 'tree'), (False, 'form')],
            'domain': [('id', 'in', line_ids)],
            'context': context,
            'target': 'current',  # 'new'
            'nodestroy': False,
            }

    def action_check_product_file(self, cr, uid, ids, context=None):
        #TODO
        pass

    def action_import_product(self, cr, uid, ids, context=None):
        """ Create purchase order:
        """
        # Parameters:
        row_start = 1

        # Pool used:
        product_pool = self.pool.get('product.product')

        current_proxy = self.browse(cr, uid, ids, context=context)[0]

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
            default_code = ''

            # Search product:
            product_ids = product_pool.search(cr, uid, [
                ('default_code', '=', default_code)
                ], context=context)

            # Manage product error:
            if not product_ids:
                _logger.error('No product with code: %s' % default_code)
                continue

            elif len(product_ids) > 1:
                _logger.error('More material code: %s' % default_code)
            product_id = product_ids[0]

        _logger.info('Imported: %s' % filename)
        return self.write(cr, uid, ids, {
            'mode': 'imported',
            'file': False,  # reset file for clean database!
            'error': error,
            }, context=context)

    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'file': fields.binary('XLSX file', filters=None),
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
