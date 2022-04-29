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
        'base': fields.boolean(
            'Base', help='Zona base di riferimento per i listini, usata'
                         'per eventuali calcoli di supplementi'),
        'name': fields.char(
            'Zona', size=30, help='Nome della zona del corriere'),
        'description': fields.text(
            'Descrizione zona', help='Indicare il tipo di destinazioni zona'),

        'courier_id': fields.many2one(
            'carrier.supplier', 'Corriere',
            help='Indicato se il sovrapprezzo è applicato direttamente '
                 'alla zona'),
        'broker_id': fields.many2one(
            'carrier.supplier', 'Broker',
            help='Indicato se il sovrapprezzo è applicato direttamente '
                 'alla zona'),
        'cap': fields.text(
            'Lista CAP', help='Lista dei CAP separti da spazio'),
    }


class SaleOrderCarrierPricelist(orm.Model):
    """ Model name: Transport zone extra cost
    """

    _name = 'sale.order.carrier.pricelist'
    _description = 'Prezzi listino base'
    _order = 'from_weight, sequence'
    _rec_name = 'price'

    def _function_get_zone_brocker_id(
            self, cr, uid, ids, fields, args, context=None):
        """ Fields function for calculate
        """
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id] = line.courier_id.broker_id.id
        return res

    _columns = {
        'sequence': fields.integer('Seq.'),
        'broker_id': fields.many2one(
            'carrier.supplier', 'Broker'),
        'courier_id': fields.many2one(
            'carrier.supplier', 'Corriere'),

        'zone_broker_id':  fields.function(
            _function_get_zone_brocker_id, method=True,
            type='many2one', string='Zona Broker',
            help='Campo usato per filtrare le zone del broker padre'),

        'from_weight': fields.float(
            'Dal peso >=', digits=(10, 2), required=True,
            help='Peggiore tra peso fisico e volumetrico'),
        'to_weight': fields.float(
            'Al peso <', digits=(10, 2), required=True,
            help='Peggiore tra peso fisico e volumetrico'),
        'price': fields.float(
            'Prezzo', digits=(10, 2), required=True,
            help='Prezzo base per questo range'),
        'zone_id': fields.many2one(
            'sale.order.carrier.zone', 'Zona', required=True,
        ),
        'base': fields.related(
            'zone_id', 'base', type='boolean', string='Base'),
        }


class SaleOrderBrokerZone(orm.Model):
    """ Model name: Broker Zone also for Courier
    """

    _name = 'sale.order.broker.zone'
    _description = 'Zone broker su corriere'
    _order = 'zone_id'
    _rec_name = 'zone_id'

    _columns = {
        'courier_id': fields.many2one(
            'carrier.supplier', 'Corriere',
            help='Abbinamento zona broker al corriere'),
        'broker_id': fields.related(
            'courier_id', 'broker_id',
            type='many2one', relation='carrier.supplier',
            string='Broker'),
        'zone_id': fields.many2one(
            'sale.order.carrier.zone', 'Zone',
            help='Le zone del corriere sono prese dal broker'),
    }


class SaleOrderCarrierZoneExtra(orm.Model):
    """ Model name: Transport zone extra cost
    """

    _name = 'sale.order.carrier.zone.extra'
    _description = 'Prezzi extra per zona'
    _order = 'mode'
    _rec_name = 'mode'

    _columns = {
        'sequence': fields.integer('Seq.'),
        'is_active': fields.boolean(
            'Attiva', help='Voci disattivate sono da considerare storiche'),
        'mode': fields.selection([
            ('fixed', 'Fisso (valore)'),
            ('fuel', 'Carburante (perc.)'),
            ('pallet', 'Pallet non sovrapponibile (valore)'),

            ('zone', 'Zona >>'),
            ('weight', 'Peso >='),
            ('1dimension', 'Dimensione max >='),
            ('2dimension', 'Min + max dime. >='),
            ('3dimension', 'Somma 3 dimensioni >='),
        ], 'Modalità', required=True),

        'value': fields.float(
            'Valore filtro', digits=(10, 2),
            help='Dove serve indicare il valore da usare per il filtro '
                 'modalità'),
        'value_zone_id': fields.many2one(
            'sale.order.carrier.zone', 'Zona',
            help='Nel caso di filtro in modalità zona, indicare '
                 'quella da usare'),

        'price': fields.float(
            'Sovrapprezzo', digits=(10, 2), required=True,
            help='Maggiorazione applicata alla zona standard calcolata '
                 'con peso'),
        'date': fields.date(
            'Dalla data >=', required=True,
            help='Data da cui viene applicato il sovrapprezzo'),

        'carrier_id': fields.many2one(
            'carrier.supplier', 'Broker',
            help='Indicato se il sovrapprezzo è applicato direttamente '
                 'alla zona'),
        'courier_id': fields.many2one(
            'carrier.supplier', 'Corriere',
            help='Indicato se il sovrapprezzo è applicato direttamente '
                 'alla zona'),
        'zone_id': fields.many2one(
            'sale.order.carrier.zone', 'Zona',
            help='Indicato se il sovrapprezzo è applicato direttamente '
                 'alla zona'),
        'broker_courier_id': fields.many2one(
            'sale.order.broker.zone', 'Broker corriere',
            help='Indicato se il sovrapprezzo è applicato direttamente '
                 'alla zona del broker anche essendo nel corriere'),
    }

    _defaults = {
        'is_active': lambda *x: True,
        'mode': lambda *x: 'fixed',
    }


class SaleOrderCarrierConstraint(orm.Model):
    """ Model name: Transport zone extra cost
    """

    _name = 'sale.order.carrier.constraint'
    _description = 'Vincoli broker corriere'
    _order = 'mode'
    _rec_name = 'mode'

    _columns = {
        'mode': fields.selection([
            ('weight', 'Peso'),
            ('1dimension', 'Dimensione max <='),
            ('2dimension', 'Min + max dime. <='),
            ('3dimension', 'Somma dimensioni <='),
            ('parcel', 'Colli <='),  # todo
        ], 'Vincolo', required=True),
        'value': fields.float(
            'Valore', digits=(10, 2), required=True,
            help='Maggiorazione applicata alla zona standard calcolata '
                 'con peso'),

        'broker_id': fields.many2one(
            'carrier.supplier', 'Broker',
            help='Indicato se il vincolo è applicato direttamente '
                 'alla broker'),
        'courier_id': fields.many2one(
            'carrier.supplier', 'Corriere',
            help='Indicato se il vincolo è applicato direttamente '
                 'alla corriere'),

        # todo needed?:
        'zone_id': fields.many2one(
            'sale.order.carrier.zone', 'Zona',
            help='Indicato se il vincolo è collegato direttamente '
                 'alla zona'),
        'broker_courier_id': fields.many2one(
            'sale.order.broker.zone', 'Broker corriere',
            help='Indicato se il vincolo è applicato direttamente '
                 'alla zona del broker anche essendo nel corriere'),
    }


class SaleOrderCarrierPallet(orm.Model):
    """ Model name: Transport pallet
    """
    _name = 'sale.order.carrier.pallet'
    _description = 'Pallet'
    _order = 'name'

    _columns = {
        'name': fields.char('Nome', char=50, required=True),
        'broker_id': fields.many2one('carrier.supplier', 'Broker'),
        'base': fields.float('Altezza base pallet', digits=(10, 2)),
        'H': fields.float('Altezza cm.', digits=(10, 2), required=True),
        'W': fields.float('Larghezza cm.', digits=(10, 2), required=True),
        'L': fields.float('Lunghezza cm.', digits=(10, 2), required=True),
        'weight': fields.float('Peso max Kg.', digits=(10, 2)),
    }


class ProductProductWebServer(orm.Model):
    """ Model name: Product web server
    """

    _inherit = 'product.product.web.server'

    def _function_volumetric(
            self, cr, uid, ids, fields, args, context=None):
        """ Fields function for calculate
        """
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id] = max(
                line.web_H * line.web_W * line.web_L / 2000.0,
                line.web_weight,
            )
        return res

    _columns = {
        'web_H': fields.float('Altezza cm.', digits=(10, 2)),
        'web_W': fields.float('Larghezza cm.', digits=(10, 2)),
        'web_L': fields.float('Lunghezza cm.', digits=(10, 2)),
        'web_weight': fields.float('Peso Kg.', digits=(10, 2)),
        'web_volumetric': fields.function(
            _function_volumetric, method=True,
            type='many2one', string='Zona Broker',
            help='Campo usato per filtrare le zone del broker padre'),
        # 'pallet_ids': fields.many2many(
        #    'sale.order.carrier.pallet', 'Pallet autotrasporto'),
    }


class CarrierSupplierInherit(orm.Model):
    """ Model name: Parcels supplier
    """

    _inherit = 'carrier.supplier'

    _columns = {
        # Pallet for auto transporter
        'pallet_ids': fields.one2many(
            'sale.order.carrier.pallet', 'broker_id',
            'Pallet',
            help='Elenco pallet utilizzati per l\'autotrasporto'),

        # Constraints
        'carrier_constraint_ids': fields.one2many(
            'sale.order.carrier.constraint', 'broker_id',
            'Vincoli broker', help='Vincoli del  Broker'),
        'courier_constraint_ids': fields.one2many(
            'sale.order.carrier.constraint', 'courier_id',
            'Vincoli corriere', help='Vincoli del corriere'),

        # Pricelist:
        'broker_base_ids': fields.one2many(
            'sale.order.carrier.pricelist', 'broker_id',
            'Listino base broker',
            help='Listino base per Broker'),
        'courier_base_ids': fields.one2many(
            'sale.order.carrier.pricelist', 'courier_id',
            'Listino base corriere',
            help='Listino base per Broker'),

        # Zone:
        'broker_zone_ids': fields.one2many(
            'sale.order.carrier.zone', 'broker_id',
            'Zone broker',
            help='Elenco zone broker se sono sempre le stesse per tutti'
                 'i trasportatori che usa'),
        'courier_zone_ids': fields.one2many(
            'sale.order.carrier.zone', 'courier_id',
            'Zone corriere',
            help='Elenco zone extra per corriere, quando non sono le'
                 'stesse per il broker ma vengono customizzate per '
                 'spedizioniere'),
        'broker_courier_extra_ids': fields.one2many(
            'sale.order.broker.zone', 'courier_id',
            'Zone broker su corriere',
            help='Elenco zone broker utilizzate nel corriere (il corriere'
                 'non ha le sue zone)'),

        # Extra cost
        'broker_extra_ids': fields.one2many(
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


class SaleOrderBrokerZoneInherit(orm.Model):
    """ Model name: Transport broker.courier cost
    """

    _inherit = 'sale.order.broker.zone'

    _columns = {
        'zone_extra_ids': fields.one2many(
            'sale.order.carrier.zone.extra', 'broker_courier_id',
            'Prezzi extra zona broker in corriere',
            help='Elenco prezzi extra per zona')
        }
