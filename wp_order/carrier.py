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


class CarrierConnection(orm.Model):
    """ Model name: Carrier Connection
    """
    _name = 'carrier.connection'
    _description = 'Carrier connection'
    _order = 'name'

    _columns = {
        'name': fields.char('Nome', size=64, required=True),
        'company_id': fields.many2one(
            comodel_name='res.company',
            string='Company',
            required=True),

        'location': fields.char(
            'Location root', size=140, required=True,
            help='Path for endpoint, ex.: https://api.mbeonline.it/ws'),
        'username': fields.char('Username', size=64, required=True),
        'passphrase': fields.char('Passphrase', size=64, required=True),

        'system': fields.char(
            'System', size=10, required=True,
            help='Old way to manage marketplace country'),
        'internal_reference': fields.char(
            'Internal reference', size=10,
            help='Code assigned to every call and returned, used as ID'),
        'customer_id': fields.Integer(
            'Customer ID', required=True, help='Code found in web management'),
        'store_id': fields.char(
            'Store ID', size=4, required=True,
            help='Code used for some calls'),

        # 'auto_print_label': fields.boolean(
        #    'Autoprint label', help='Print label when delivery was sent'),
        # 'cups_printer_id': fields.many2one(
        #    'cups.printer', 'CUPS printer',
        #    help='Label order print with this'),

        # Not used for now:
        'sam_id': fields.char('SAM ID', size=4, help=''),
        'department_id': fields.char('Department ID', size=4, help=''),
    }

    _defaults = {
        'wsdl_root': lambda *x:
            'https://www.onlinembe.it/wsdl/OnlineMbeSOAP.wsdl',
        'system': lambda *x: 'IT',
        'internal_reference': lambda *x: 'MI030-lg',
        }


'''class CarrierSupplier(orm.Model):
    """ Model name: Carrier Connection
    """
    _name = 'carrier.supplier'
    _description = 'Carrier supplier'
    _order = 'name'

    # todo
    _columns = {
        'carrier_connection_id': fields.many2one(
            comodel_name='carrier.connection',
            string='Carrier Connection'),
    }'''


'''class CarrierSupplierMode(orm.Model):
    """ Model name: Parcels supplier mode
    """

    _name = 'carrier.supplier.mode'
    _description = 'Carrier mode'

    # todo
    _columns = {
        'cups_printer_id': fields.many2one(
            'cups.printer', 'CUPS printer', help='Label order print with this')
    }'''


'''class CarrierParcelTemplate(orm.Model):
    """ Model name: Parcels template
    """

    _name = 'carrier.parcel.template'
    _description = 'Carrier template'

    # todo
    _columns = {
        'carrier_connection_id': fields.many2one(
            comodel_name='carrier.connection',
            string='Carrier Connection',
            help='Force carrier connection for small package'),

        'package_type': fields.Selection(
            string='Package type', required=True,
            selection=[
                ('GENERIC', 'Generic'),
                ('ENVELOPE', 'Envelope'),
                ('DOCUMENTS', 'Documents'),
            ]),
        }
    
    _defaults = {
        'package_type': lambda *x: 'GENERIC',
    }'''


class WordpressSaleOrder(orm.Model):
    """ Model name: Wordpress Sale order
    """
    _inherit = 'wordpress.sale.order'

    _columns = {
        'parcel_weight_tree': fields.float(
            'Weight', help='Tree view only for fast insert parcel'),
        'carrier_connection_id': fields.many2one(
            comodel_name='carrier.connection',
            string='Carrier Connection',
            help='Carrier connection used for better quotation'),
        'carrier_id': fields.integer(string='Carrier ID'),
        'carrier_state': fields.selection(
            string='Carrier state',
            selection=[
                ('draft', 'Draft'),
                ('pending', 'Pending'),
                ('sent', 'Sent'),
                ('delivered', 'Delivered'),  # Closed
            ]),
        'delivery_state': fields.selection(
            string='Delivery state',
            selection=[
                ('WAITING_DELIVERY', 'Waiting'),
                ('PARTIALLY_DELIVERED', 'Partially delivered'),
                ('DELIVERED', 'Delivered'),
                ('EXCEPTION', 'Exception'),
                ('NOT_AVAILABLE', 'Not available'),
            ]),
        'master_tracking_id': fields.char('Master Tracking', size=20),
        'system_reference_id': fields.char('System reference ID', size=20),
        'shipper_type': fields.selection(
            string='Shipper type', required=True,
            selection=[
                ('COURIERLDV', 'Courier LDV'),
                ('MBE', 'MBE'),
            ]),

        'ship_type': fields.selection(
            string='Ship type', required=True,
            selection=[
                ('EXPORT', 'Export'),
                ('IMPORT', 'Import'),
                ('RETURN', 'Return'),
            ]),
        'package_type': fields.selection(
            string='Package type', required=True,
            selection=[
                ('GENERIC', 'Generic'),
                ('ENVELOPE', 'Envelope'),
                ('DOCUMENTS', 'Documents'),
            ]),
    }

    _defaults = {
        'carrier_state': lambda *x: 'draft',
        'delivery_state': lambda *x: 'WAITING_DELIVERY',
        'shipper_type': lambda *x: 'COURIERLDV',
        'ship_type': lambda *x: 'EXPORT',
        'package_type': lambda *x: 'GENERIC',
    }


'''
class SaleOrderParcel(orm.Model):
    """ Model name: Parcels for sale order
    """

    _name = 'sale.order.parcel'

    # todo
    _columns = {
        'carrier_connection_id': fields.many2one(
            comodel_name='carrier.connection',
            string='Carrier Connection',
            help='Force carrier connection for small package')
    }
'''
