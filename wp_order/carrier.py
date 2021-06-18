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
        'location': lambda *x:
            'https://api.mbeonline.it/ws',
        'system': lambda *x: 'IT',
        'internal_reference': lambda *x: 'MI030-lg',
        }



class CarrierSupplier(orm.Model):
    """ Model name: Parcels supplier
    """

    _name = 'carrier.supplier'
    _description = 'Parcel supplier'
    _rec_name = 'name'

    # -------------------------------------------------------------------------
    #                                   COLUMNS:
    # -------------------------------------------------------------------------
    _columns = {
        'hidden': fields.boolean('Nascosto'),
        'name': fields.char('Nome'),
        'account_ref': fields.char('Codice'),
        'mode': fields.selection(
            string='Mode',
            selection=[
                ('carrier', 'Corriere'),
                ('courier', 'Spedizioniere'),
            ], required=True, default='carrier'),
        'mode_id': fields.many2one(
            'carrier.supplier.mode', 'Modalità',
            domain="[('supplier_id.mode', '=', 'carrier')]",
            help='Modalità dello spedizioniere'),

        'carrier_connection_id': fields.many2one(
            comodel_name='carrier.connection',
            string='Carrier Connection'),
        }


class CarrierSupplierMode(orm.Model):
    """ Model name: Parcels supplier mode of delivery
    """

    _name = 'carrier.supplier.mode'
    _description = 'Carrier mode'
    _rec_name = 'name'

    # -------------------------------------------------------------------------
    #                                   COLUMNS:
    # -------------------------------------------------------------------------
    _columns = {
        'name': fields.char('Nome', required=True),
        'account_ref': fields.car('Account ref.'),
        'supplier_id': fields.many2one(
            'carrier.supplier', 'Carrier', required=True),
        'hidden': fields.boolean('Nascosto'),
        # 'cups_printer_id': fields.many2one(
        #    'cups.printer', 'CUPS printer',
        #    help='Label order print with this')
    }


class CarrierParcelTemplate(orm.Model):
    """ Model name: Parcels template
    """

    _name = 'carrier.parcel.template'
    _description = 'Parcel template'
    _rec_name = 'name'

    def _get_volumetric_weight(
            self, cr, uid, ids, fields=None, args=None, context=None):
        """ Compute volumetric weight, return value
        """
        res = {}
        for template in self.browse(cr, uid, ids, context=context):
            res[template.id] = (
                template.length * template.width * template.height / 5000.0)
        return res

    # -------------------------------------------------------------------------
    #                                   COLUMNS:
    # -------------------------------------------------------------------------
    _columns = {
        'is_active': fields.boolean('Attivo'),
        'name': fields.char('Name'),
        'no_label': fields.boolean('No label'),
        'carrier_supplier_id': fields.many2one('carrier.supplier', 'Carrier'),
        'length': fields.float('Length', digits=(16, 2), required=True),
        'width': fields.float('Width', digits=(16, 2), required=True),
        'height': fields.float('Height', digits=(16, 2), required=True),
        'dimension_uom_id': fields.many2one('product.uom', 'Product UOM'),
        'weight': fields.function(
            'Weight volumetric', digits=(16, 2), type='float',
            compute='_get_volumetric_weight',
            help='Volumetric weight (H x L x P / 5000)', readonly=True),
        'weight_uom_id': fields.many2one('product.uom', 'Product UOM'),
        'carrier_connection_id': fields.many2one(
            comodel_name='carrier.connection',
            string='Carrier Connection',
            help='Force carrier connection for small package'),

        'package_type': fields.selection(
            string='Package type', required=True,
            selection=[
                ('GENERIC', 'Generic'),
                ('ENVELOPE', 'Envelope'),
                ('DOCUMENTS', 'Documents'),
            ]),
    }

    _defaults = {
        'package_type': lambda *x: 'GENERIC',
    }


class SaleOrderParcel(orm.Model):
    """ Model name: Parcels for sale order
    """

    _name = 'sale.order.parcel'
    _description = 'Sale order parcel'
    _rec_name = 'weight'

    @api.multi
    def _get_volumetric_weight(
            self, cr, uid, ids, fields=None, args=None, context=None):
        """ Compute volumetric weight, return value
        """
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            weight = (  # Volumetric:
                line.length * line.width * line.height / 5000.0)
            real_weight = line.real_weight
            if line.use_real_weight:
                used_weight = line.real_weight  # Real
            else:  # Greater evaluation:
                if weight > real_weight:
                    used_weight = weight
                else:
                    used_weight = real_weight
            res[line.id] = {
                'weight': weight,  # volumetric
                'used_weight': used_weight,
            }
        return res

    # -------------------------------------------------------------------------
    #                                   COLUMNS:
    # -------------------------------------------------------------------------
    _columns = {
        'order_id': fields.many2one('wordpress.sale.order', 'Ordine WP'),

        # Dimension:
        'length': fields.float('Lunghezza', digits=(16, 2), required=True),
        'width': fields.float('Larghezza', digits=(16, 2), required=True),
        'height': fields.float('Altezza', digits=(16, 2), required=True),
        'dimension_uom_id': fields.many2one('product.uom', 'UM dim.'),
        'use_real_weight': fields.boolean(
            string='Usa reale', help='Passa perso reale al posto del volum.'),

        # Weight:
        'real_weight': fields.float(
            'Peso reale', digits=(16, 2),
            ),
        'weight': fields.function(
            'Peso Volumetrico', digits=(16, 2), type='float',
            compute='_get_volumetric_weight',
            readonly=True,
        ),
        'used_weight': fields.function(
            'Larghezza usata', digits=(16, 2), type='float',
            compute='_get_volumetric_weight', readonly=True,
        ),
        'weight_uom_id': fields.many2one('product.uom', 'UM peso'),
        'no_label': fields.boolean('No etichetta'),
    }


class WordpressSaleOrder(orm.Model):
    """ Model name: Wordpress Sale order
    """
    _inherit = 'wordpress.sale.order'

    _columns = {
        'carrier_ok': fields.boolean(
            'Carrier OK',
            help='Carrier must be confirmed when done!'),

        # Master Carrier:
        'carrier_supplier_id ': fields.many2one(
            'carrier.supplier', 'Carrier',
            domain="[('mode', '=', 'carrier')]"),
        'carrier_mode_id ': fields.many2one(
            'carrier.supplier.mode', 'Carrier service',
            domain="[('supplier_id', '=', carrier_supplier_id)]",
        ),

        'courier_supplier_id ': fields.many2one(
            'carrier.supplier', 'Courier',
            domain="[('hidden', '=', False), "
                   "('mode', '=', 'courier'),"
                   "('mode_id', '=', carrier_mode_id)]"),
        'courier_mode_id ': fields.many2one(
            'carrier.supplier.mode', 'Courier service',
            domain="[('hidden', '=', False), "
                   "('supplier_id', '=', courier_supplier_id)]",
        ),

        'carrier_parcel_template_id ': fields.many2one(
            'carrier.parcel.template', 'Parcel template'),
        'carrier_check ': fields.text(
            'Carrier check', help='Check carrier address', multi=True,
            compute='_get_carrier_check_address', widget='html'),
        'carrier_check_error ': fields.text(
            'Carrier check', help='Check carrier address error', multi=True,
            compute='_get_carrier_check_address', widget='html'),

        'carrier_description ': fields.text('Carrier description'),
        'carrier_note ': fields.text('Carrier note'),
        'carrier_stock_note ': fields.text('Stock operator note'),
        'carrier_total ': fields.float('Goods value', digits=(16, 2)),
        'carrier_ensurance ': fields.float('Ensurance', digits=(16, 2)),
        'carrier_cash_delivery ': fields.float('Cash on delivery', digits=(16, 2)),
        'carrier_pay_mode ': fields.selection([
            ('CASH', 'Cash'),
            ('CHECK', 'Check'),
            ], 'Pay mode', default='CASH'),
        'parcel_ids ': fields.one2many(
            'sale.order.parcel', 'order_id', 'Parcels'),
        'parcel_detail ': fields.function(
            'Parcel detail', mode=text', compute='_get_parcel_detail'),
        'real_parcel_total ': fields.function(
            string='Colli', mode='integer',
            compute='_get_carrier_parcel_total'),
        'destination_country_id ': fields.many2one(
            'res.country', 'Destination',
            related='partner_shipping_id.country_id',
        ),

        # Data from Carrier:
        'carrier_cost ': fields.float(
            'Cost', digits=(16, 2), help='Net shipment price'),
        'carrier_cost_total ': fields.float(
            'Cost', digits=(16, 2), help='Net shipment total price'),
        'carrier_cost_lossy ': fields.function(
            'Under carrier cost', mode='boolean',
            help='Carrier cost payed less that request!',
            compute='_check_carrier_cost_value',
            store=True,
        ),
        'carrier_track_id ': fields.char(
            'Track ID', size=64),
        # TODO extra data needed!

        'has_cod ': fields.boolean('Has COD'),  # CODAvailable
        'has_insurance ': fields.boolean(
            'Has Insurance'),  # InsuranceAvailable
        'has_safe_value ': fields.boolean(
            'Has safe value'),  # MBESafeValueAvailable

        'carrier_delivery_date ': fields.datetime(
            'Delivery date', readonly=True),
        'carrier_delivery_sign ': fields.datetime(
            'Delivery sign', readonly=True),

        # 'NetShipmentTotalPrice': Decimal('6.80'),  # ??
        # 'IdSubzone': 125,
        # 'SubzoneDesc': 'Italia-Zona A',

        # MBE Portal:
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
