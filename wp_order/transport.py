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
import pdb
import sys
import re
import logging
import erppeek
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


class SaleOrderCarrierZone(orm.Model):
    """ Model name: Transport zone
    """

    _name = 'sale.order.carrier.zone'
    _description = 'Zone corriere'
    _order = 'name'

    _columns = {
        'name': fields.char(
            'Zona', size=30, help='Nome della zona del corriere'),
        'description': fields.text(
            'Descrizione zona', help='Indicare il tipo di destinazioni zona'),

        'courier_id': fields.many2one(
            'carrier.supplier', 'Corriere',
            help='Indicato se il sovrapprezzo è applicato direttamente '
                 'alla zona'),
        'carrier_id': fields.many2one(
            'carrier.supplier', 'Broker',
            help='Indicato se il sovrapprezzo è applicato direttamente '
                 'alla zona'),
    }


class SaleOrderCarrierZoneExtra(orm.Model):
    """ Model name: Transport zone extra cost
    """

    _name = 'sale.order.carrier.zone.extra'
    _description = 'Prezzi extra per zona'
    _order = 'mode'
    _rec_name = 'mode'

    _columns = {
        'is_active': fields.boolean(
            'Attiva', help='Voci disattivate sono da considerare storiche'),
        'mode': fields.selection([
            ('fixed', 'Fisso (valore)'),
            ('fuel', 'Carburante (perc.)'),
            ('pallet', 'Pallet non sovrapponibile (valore)'),
        ], 'Modalità', required=True),
        'price': fields.float(
            'Sovrapprezzo', digits=(10, 2), required=True,
            help='Maggiorazione applicata alla zona standard calcolata '
                 'con peso'),
        'date': fields.date(
            'Dalla data >=', required=True,
            help='Data da cui viene applicato il sovrapprezzo'),

        'zone_id': fields.many2one(
            'sale.order.carrier.zone', 'Zona',
            help='Indicato se il sovrapprezzo è applicato direttamente '
                 'alla zona'),
        'courier_id': fields.many2one(
            'carrier.supplier', 'Corriere',
            help='Indicato se il sovrapprezzo è applicato direttamente '
                 'alla zona'),
        'carrier_id': fields.many2one(
            'carrier.supplier', 'Broker',
            help='Indicato se il sovrapprezzo è applicato direttamente '
                 'alla zona'),
    }

    _defaults = {
        'is_active': lambda *x: True,
        'mode': lambda *x: 'fixed',
    }


class CarrierSupplierInherit(orm.Model):
    """ Model name: Parcels supplier
    """

    _inherit = 'carrier.supplier'

    _columns = {
        'carrier_zone_ids': fields.one2many(
            'sale.order.carrier.zone', 'carrier_id',
            'Zone broker',
            help='Elenco zone broker se sono sempre le stesse per tutti'
                 'i trasportatori che usa'),
        'courier_zone_ids': fields.one2many(
            'sale.order.carrier.zone', 'courier_id',
            'Zone corriere',
            help='Elenco zone extra per corriere, quando non sono le'
                 'stesse per il broker ma vengono customizzate per '
                 'spedizioniere'),

        'carrier_extra_ids': fields.one2many(
            'sale.order.carrier.zone.extra', 'carrier_id',
            'Prezzi extra broker',
            help='Elenco prezzi extra per broker'),
        'courier_extra_ids': fields.one2many(
            'sale.order.carrier.zone.extra', 'courier_id',
            'Prezzi extra corriere',
            help='Elenco prezzi extra per corriere')
        }


class SaleOrderCarrierZoneInherit(orm.Model):
    """ Model name: Transport zone
    """

    _inherit = 'sale.order.carrier.zone'

    _columns = {
        'zone_extra_ids': fields.one2many(
            'sale.order.carrier.zone.extra', 'zone_id',
            'Prezzi extra zona',
            help='Elenco prezzi extra per zona')
        }
