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


class ProductProductLogisticPackage(orm.Model):
    """ Model name: ProductProductLogisticPackage
    """

    _name = 'product.product.logistic.package'
    _description = 'Dati logistici'
    _order = 'name'

    # -------------------------------------------------------------------------
    # Button:
    # -------------------------------------------------------------------------
    def auto_logistic_package_assign(self, cr, uid, ids, context=None):
        """ Auto assign code
        """
        model_package_id = ids[0]
        current = self.browse(cr, uid, model_package_id, context=context)

        product_pool = self.pool.get('product.product')
        product_ids = product_pool.search(cr, uid, [
            ('default_code', '=ilike', '%s%%' % current.name),
            ], context=context)
        _logger.warning('Updating %s logistic product...' % len(product_ids))
        return product_pool.write(cr, uid, product_ids, {
            'logistic_data_id': model_package_id,
            }, context=context)

    _columns = {
        'name': fields.char('Maschera codice', size=30, required=True),
        'mask': fields.char('Maschera codice', size=13, required=True),

        'price': fields.float('Prezzo', digits=(10, 2)),

        'width': fields.float('Largh. cm.', digits=(10, 2)),
        'length': fields.float('Lung. da cm.', digits=(10, 2)),
        'length_to': fields.float('Lung. a cm.', digits=(10, 2)),
        'height': fields.float('Alt. da cm.', digits=(10, 2)),
        'height_to': fields.float('Alt. a cm.', digits=(10, 2)),

        'seat': fields.float('Seduta', digits=(10, 2)),
        'arm': fields.float('Bracciolo', digits=(10, 2)),
        'pipe': fields.float('Diam. Tubo', digits=(10, 2)),

        'pack_width': fields.float('Largh. cm.', digits=(10, 2)),
        'pack_length': fields.float('Lung. cm.', digits=(10, 2)),
        'pack_height': fields.float('Alt. cm.', digits=(10, 2)),

        'pallet_width': fields.float('Largh. bancale', digits=(10, 2)),
        'pallet_length': fields.float('Lung. bancale', digits=(10, 2)),
        'pallet_height': fields.float('Alt. bancale', digits=(10, 2)),

        'pcs_pallet': fields.integer('Pz. per bancale'),
        'pcs_truck': fields.integer('Pz. per truck'),

        'net_weight': fields.integer('Peso netto (gr)'),
        'gross_weight': fields.integer('Peso lordo (gr)'),

        'box_width': fields.integer('Box: larg.'),
        'box_depth': fields.integer('Box: prof..'),
        'box_height': fields.integer('Box: alt.'),

        'pallet_dimension': fields.char('Dim. Pallet', size=30),
        }

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'Nome duplicato!'),
        ]


class ProductProduct(orm.Model):
    """ Model name: ProductProduct
    """

    _inherit = 'product.product'

    _columns = {
        'logistic_data_id': fields.many2one(
            'product.product.logistic.package', 'Dati logistici'),
    }
