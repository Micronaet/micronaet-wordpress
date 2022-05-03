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
import json
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
        'price': fields.char(
            'Prezzo', size=120, required=True,
            help='Prezzo base per questo range (è un campo formula)'),
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
            # Formula:
            ('formula', 'Formula'),

            # Fixed:
            ('fixed', 'Fisso (valore)'),
            ('fuel', 'Carburante (perc.)'),
            ('pallet', 'Pallet non sovrapponibile (valore)'),

            # Zone with select:
            ('zone', 'Zona >>'),

            # Dimension  with value:
            ('weight', 'Peso >='),

            ('1dimension', 'Dimensione max >='),
            ('2dimension', 'Min + max dime. >='),
            # ('2bdimension', '2 massime dimensioni >='),
            ('3dimension', 'Somma 3 dimensioni >='),

            # ('Ldimension', 'Lunghezza >='),
            # ('Hdimension', 'Altezza >='),
            # ('Wdimension', 'Larghezza >='),

        ], 'Modalità', required=True),

        'formula': fields.char(
            'Formula', size=130,
            help='Formula per il calcolo, es.: '
                 'l > 180 and l < 210 and weight > 100'
                 'max(l, h, w) < 100'
                 'sum(sorted((l, h, w))[-2:])'
                 'Use: weight, l, h, m, volumetric, volume as variables'),
        'value': fields.float(
            'Valore filtro', digits=(10, 2),
            help='Dove serve indicare il valore da usare per il filtro '
                 'modalità'),
        'value_zone_id': fields.many2one(
            'sale.order.carrier.zone', 'Zona',
            help='Nel caso di filtro in modalità zona, indicare '
                 'quella da usare'),

        'price': fields.char(
            'Sovrapprezzo', size=120, required=True,
            help='Maggiorazione applicata alla zona standard calcolata '
                 'con peso (il campo è una formula, usarlo quando '
                 'c\'è da indicare ad esempio: weight *  3.5'),
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
            # Formula:
            ('formula', 'Formula'),

            ('weight', 'Peso >='),
            # ('Ldimension', 'Lunghezza >='),
            # ('Hdimension', 'Altezza >='),
            # ('Wdimension', 'Larghezza >='),

            ('1dimension', 'Dimensione max >='),
            ('2dimension', 'Min + max dim. >='),
            # ('2bdimension', '2 dimens. più lunghe >='),
            ('3dimension', 'Somma dim. >='),

            ('parcel', 'Colli >='),  # todo
        ], 'Vincolo', required=True),
        'value': fields.float(
            'Valore', digits=(10, 2),
            help='Maggiorazione applicata alla zona standard calcolata '
                 'con peso'),
        'formula': fields.char(
            'Formula', size=130,
            help='Formula con test per capire se il vincolo è rispettato'
                 'o meno.'),

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


class ProductProductCourier(orm.Model):
    """ Model name: Transport for product
    """
    _name = 'product.product.courier'
    _description = 'Trasporto prodotti'
    _order = 'product_id'

    _columns = {
        'sequence': fields.integer('Seq.'),
        'product_id': fields.many2one(
            'product.product', 'Prodotto'),
        'courier_id': fields.many2one(
            'carrier.supplier', 'Corriere', required=True),
        'broker_id': fields.related(
            'courier_id', 'broker_id',
            type='many2one', relation='carrier.supplier',
            string='Broker'),
        'base_cost': fields.float(
            'Costo base', digits=(10, 2),
            help='Costo extra per la consegna del prodotto (imballaggio,'
                 'confezionamento, etichettatura o altre spese accessorie'),
        'pallet_id': fields.many2one(
            'sale.order.carrier.pallet', 'Pallet autotrasporto'),
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
        for product in self.browse(cr, uid, ids, context=context):
            res[product.id] = max(
                (product.web_H * product.web_W * product.web_L) / 2000.0,
                product.web_weight,
            )
        return res

    _columns = {
        'web_H': fields.float('Altezza cm.', digits=(10, 2)),
        'web_W': fields.float('Larghezza cm.', digits=(10, 2)),
        'web_L': fields.float('Lunghezza cm.', digits=(10, 2)),
        'web_weight': fields.float('Peso Kg.', digits=(10, 2)),
        'web_volumetric': fields.function(
            _function_volumetric, method=True,
            type='float', digits=(10, 2), string='Peso volumetrico',
            help='Peso volumetrico (max tra peso e HxLxW / 2000)'),
        # 'pallet_ids': fields.many2many(
        #    'sale.order.carrier.pallet', 'Pallet autotrasporto'),

        # Best transport:
        'carrier_extra': fields.float(
            'Extra costo', digits=(10, 2),
            help='Costo extra per la consegna del prodotto (imballaggio,'
                 'confezionamento, etichettatura o altre spese accessorie'),
        'courier_ids': fields.one2many(
            'product.product.courier', 'courier_id',
            'Corrieri da usare',
            help='Elenco corrieri da usare per il trasporto di questo '
                 'prodotto'),
    }


class CarrierSupplierInherit(orm.Model):
    """ Model name: Parcels supplier
    """

    _inherit = 'carrier.supplier'

    def print_all_product_broker(self, cr, uid, ids, context=None):
        """ Print all product for this broker
        """
        def product_check_constraints(
                courier, h, w, l, volumetric, weight, mode='contraints',
                cache=None):
            """ Return and cache constraints comment
            """
            # -----------------------------------------------------------------
            # Cache mode:
            # -----------------------------------------------------------------
            if cache is None:
                cache = {}  # Cache will not be used correctly!
            if mode not in cache:
                cache[mode] = {}

            if courier not in cache[mode]:
                # Broker:
                cache[mode][courier] = [
                    rule for rule in courier.broker_id.carrier_constraint_ids]
                # Courier:
                cache[mode][courier].extend(
                    [rule for rule in courier.carrier_constraint_ids])

            # -----------------------------------------------------------------
            # Check constraints:
            # -----------------------------------------------------------------
            comment = ''
            error = False  # todo needed, if error still red the cell
            for constraint in cache[mode][courier]:
                mode = constraint.mode
                value = constraint.value
                formula = constraint.formula

                dimension1 = max(h, w, l)
                dimension2 = dimension1 + min(h, w, l)
                dimension3 = sum((h, w, l))
                volume = h * w * l

                if mode == 'formula':
                    try:
                        if eval(formula):
                            comment += '[VINCOLO] Formula (%s) \n' % formula
                    except:
                        comment += '[ERR] Formula errata (%s)' % formula
                if mode == 'weight' and weight > value:
                    comment += '[VINCOLO] Peso <= %s attuale %s \n' % (
                        value, weight,
                    )
                if mode == '1dimension' and dimension1 > value:
                    comment += '[VINCOLO] 1 dimens. <= %s attuale %s \n' % (
                        value, dimension1,
                    )
                if mode == '2dimension' and dimension2 > value:
                    comment += '[VINCOLO] 2 dimens. <= %s attuale %s \n' % (
                        value, dimension2,
                    )
                if mode == '3dimension' and dimension3 > value:
                    comment += '[VINCOLO] 3 dimens. <= %s attuale %s \n' % (
                        value, dimension3,
                    )
            return comment

        def get_extra_price(courier, mode='extra', cache=None):
            """ Return and cache extra price rule list
            """
            if cache is None:
                cache = {}  # Cache will not be used correctly!
            if mode not in cache:
                cache[mode] = {}

            if courier not in cache[mode]:
                # todo manage replace and add rate in discount list!
                # Before Broker:
                cache[mode][courier] = [
                    rule for rule in courier.broker_id.broker_extra_ids]
                # After Courier:
                cache[mode][courier].extend(
                    [rule for rule in courier.courier_extra_ids])
            return cache[mode][courier]

        def get_zone(carrier, pos, mode='broker', cache=None):
            """ Search zoned for this carrier (broker or courier)
                Cache is used for keep value one loaded
                position for indexing columns
            """
            if cache is None:
                cache = {}  # Cache will not be used correctly!
            if mode not in cache:
                cache[mode] = {}
            if carrier not in cache[mode]:
                cache[mode][carrier] = [{}, False, 0]  # Zones, Base, pos
                zones = sorted(
                    eval('carrier.%s_zone_ids' % mode),
                    key=lambda z: z.name)
                for zone in zones:
                    if zone.base:
                        cache[mode][carrier][1] = zone
                    cache[mode][carrier][0][zone] = pos
                    pos += 1
                cache[mode][carrier][2] = pos
            return cache[mode][carrier]

        def get_prices(courier, h, w, l, volumetric, weight):
            """ Search price in:
                courier pricelist
                broker pricelist
            """
            volume = h * w * l
            price_pool = self.pool.get('sale.order.carrier.pricelist')
            courier_price_ids = price_pool.search(cr, uid, [
                '&', '&',
                '|',
                ('courier_id', '=', courier.id),
                ('broker_id', '=', courier.broker_id.id),

                ('from_weight', '<', volumetric),
                ('to_weight', '>=', volumetric),
            ], context=context)
            res = {}

            # Broker and Courier pricelist weight rules:
            base_price = 0.0
            # todo add comment to check calc?

            # -----------------------------------------------------------------
            # 1. Range of weight - Zone:
            # -----------------------------------------------------------------
            for price in price_pool.browse(
                    cr, uid, courier_price_ids, context=context):
                zone = price.zone_id

                pl_price = eval(price.price)
                res[zone] = {
                    'price': pl_price,
                    'comment': '',
                    'error': False,
                }
                if zone.base:
                    base_price = pl_price
                    base_comment = '* '
                else:
                    base_comment = ''

                res[zone]['comment'] += '%s\n' % zone.name
                res[zone]['comment'] += 'Listino %s%s [%s-%s] \n' % (
                    pl_price, base_comment,
                    int(price.from_weight), int(price.to_weight),
                )

            # -----------------------------------------------------------------
            # 2 Extra price "Zone rule":
            # -----------------------------------------------------------------
            extra_rules = get_extra_price(courier, cache=cache)
            for extra_rule in extra_rules:
                if extra_rule.mode == 'zone':
                    # todo Price is base price + extra for this rule:
                    price = extra_rule.price or '0'
                    rule_price = eval(price)  # is a formula
                    # todo manage error

                    extra_rule_price = base_price + rule_price
                    if extra_rule.value_zone_id in res:
                        res[extra_rule.value_zone_id]['comment'] += \
                            '[ERR] Prezzo extra e prezzo di listino presenti\n'
                        res[extra_rule.value_zone_id]['error'] = True
                    else:
                        res[extra_rule.value_zone_id] = {
                            'price': extra_rule_price,
                            'comment': 'Extra (zona): '
                                       'B. %s + X. %s\n' % (
                                           base_price, rule_price),
                            'error': False,
                        }
                    if not base_price:
                        res[extra_rule.value_zone_id]['comment'] += \
                            '[ERR] Prezzo base a zero\n'
                        res[extra_rule.value_zone_id]['error'] = True

            # -----------------------------------------------------------------
            # 3. Other extra price rule:
            # -----------------------------------------------------------------
            extra_price = 0.0
            comment = ''
            error_extra_price = False
            extra_rate = []

            for extra_rule in extra_rules:
                mode = extra_rule.mode
                value = extra_rule.value
                formula = extra_rule.formula
                price = eval(extra_rule.price)  # now is formula

                dimension1 = max(h, w, l)
                dimension2 = dimension1 + min(h, w, l)
                dimension3 = sum((h, w, l))
                volume = h * w * l  # used for formula check

                if mode == 'zone':
                    continue  # Yet consider
                elif mode == 'formula':
                    try:
                        if eval(formula):
                            extra_price += price
                            comment += u'[Formula (%s): %s] ' % (
                                formula, price)
                    except:
                        comment += u'[ERR] Formula error: %s ' % formula
                        error_extra_price = True
                elif mode == 'weight' and weight >= value:
                    extra_price += price
                    comment += u'[Peso >=%s: %s] ' % (value, price)
                elif mode == '1dimension' and dimension1 >= value:
                    extra_price += price
                    comment += u'[1 dim. >=%s: %s] ' % (value, price)
                elif mode == '2dimension' and dimension2 >= value:
                    extra_price += price
                    comment += u'[2 dim. >=%s: %s] ' % (value, price)
                elif mode == '3dimension' and dimension3 >= value:
                    extra_price += price
                    comment += u'[3 dim. >=%s: %s] ' % (value, price)
                elif mode == 'fuel':
                    extra_rate.append(price)
                # elif mode == 'pallet' and dimension2 >= value:
                #    extra_price += price
                # todo manage extra list!

            # Loop to add extra price:
            if extra_price:  # Loop for add it:
                for zone in res:
                    res[zone]['price'] += extra_price
                    res[zone]['comment'] += 'Extra %s: %s\n' % (
                        extra_price, comment)
                    if error_extra_price:
                        res[zone]['error'] = True

            # -----------------------------------------------------------------
            # 4. Extra fuel:
            # -----------------------------------------------------------------
            if extra_rate:  # Loop for add it:
                this_rate = extra_rate[0]  # For now only one!
                extra_rate_error = len(extra_rate) > 1
                for zone in res:
                    current = res[zone]['price']
                    res[zone]['price'] = current * (100.0 + this_rate) / 100.0
                    res[zone]['comment'] += \
                        'Extra benzina B. %s + %s%%: %s\n' % (
                        current, this_rate, res[zone]['price'])

                    if extra_rate_error:
                        res[zone]['comment'] += \
                            '[ERR] Troppe %% benzina %s' % (extra_rate, )
                        res[zone]['error'] = True
            return res

        # ---------------------------------------------------------------------
        #                 MASTER PROCEDURE:
        # ---------------------------------------------------------------------
        # Pool used:
        excel_pool = self.pool.get('excel.writer')
        web_product_pool = self.pool.get('product.product.web.server')
        stored_pool = self.pool.get('carrier.supplier.stored.data')

        # ---------------------------------------------------------------------
        # JSON Store management:
        # ---------------------------------------------------------------------
        if context is None:
            context = {}

        store_data = True  # todo context.get('force_store_data')
        current_db = cr.dbname  # Used to check external linked product
        if store_data:
            stored_ids = stored_pool.search(cr, uid, [], context=context)
            stored_pool.unlink(cr, uid, stored_ids, context=context)
            _logger.info('Clean all previous stored data')

        # Parameters:
        # today = datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT)
        fall_back = True  # Fall back of dimension and weight on web product
        cache = {}
        comment_param = parameters = {
            'width': 400,
            }

        # Load all brokers:
        broker_ids = self.search(cr, uid, [
            ('mode', '=', 'carrier'),
            ('no_transport', '=', False),
        ], context=context)
        brokers = sorted(
            self.browse(cr, uid, broker_ids, context=context),
            key=lambda b: b.name,
        )

        # ---------------------------------------------------------------------
        #                         Excel report:
        # ---------------------------------------------------------------------
        ws_name = 'Sviluppo trasporti'
        excel_pool.create_worksheet(ws_name)

        # Load formats:
        excel_format = {
            'title': excel_pool.get_format('title'),
            'header': excel_pool.get_format('header'),
            'white': {
                'text': excel_pool.get_format('text'),
                'number': excel_pool.get_format('number'),
                },
            'blue': {
                'text': excel_pool.get_format('bg_blue'),
                'number': excel_pool.get_format('bg_blue_number'),
                },
            'red': {
                'text': excel_pool.get_format('bg_red'),
                'number': excel_pool.get_format('bg_red_number'),
                },
            'yellow': {
                'text': excel_pool.get_format('bg_yellow'),
                'number': excel_pool.get_format('bg_yellow_number'),
                },
            'green': {
                'text': excel_pool.get_format('bg_green'),
                'number': excel_pool.get_format('bg_green_number'),
                },
            }

        # ---------------------------------------------------------------------
        #                       Published product:
        # ---------------------------------------------------------------------
        # Width
        col_width = [
            1, 12, 30,
            7, 7, 7, 7, 10,

            5, 12, 1, 12,
        ]
        col_width.extend([13 for i in range(30)])
        excel_pool.column_width(ws_name, col_width)

        # Hide column:
        excel_pool.column_hidden(ws_name, [0, 10])

        # ---------------------------------------------------------------------
        # Hidden row:
        # ---------------------------------------------------------------------
        row = 0
        hidden_header = [
            'id', '', '', '', '', '', '', '',
            'sequence', '', 'courier', '', 'price']
        excel_pool.write_xls_line(
            ws_name, row, hidden_header, default_format=excel_format['header'])
        excel_pool.row_hidden(ws_name, [row])

        # ---------------------------------------------------------------------
        # Print header
        # ---------------------------------------------------------------------
        row += 1
        header = [
            'ID', 'Codice', 'Nome',
            'H', 'W', 'L', 'Peso', 'Peso v.',
        ]
        product_col = len(header)
        header2 = [
            'Scelta', 'Broker', 'ID', 'Corriere',
        ]
        broker_col = product_col + len(header2)
        empty = ['' for item in range(product_col)]

        header.extend(header2)  # Write also in header the header2
        excel_pool.write_xls_line(
            ws_name, row, header, default_format=excel_format['header'])
        excel_pool.freeze_panes(ws_name, 2, 3)

        # ---------------------------------------------------------------------
        # Collect data for write in line:
        # ---------------------------------------------------------------------
        # Generate a cross db product list:
        master_ids = web_product_pool.search(cr, uid, [
            ('wp_parent_template', '=', True),
            ], context=context)
        # Current database:
        master_product = [p for p in web_product_pool.browse(
                cr, uid, master_ids, context=context)]

        # Linked database:
        connector_pool = self.pool.get('connector.server')
        connector_ids = connector_pool.search(cr, uid, [
            ('wordpress', '=', True),
        ], context=context)
        if connector_ids:
            wp_connector = connector_pool.browse(
                cr, uid, connector_ids, context=context)[0]

            try:
                odoo = erppeek.Client(
                    'http://%s:%s' % (
                        wp_connector.linked_server, wp_connector.linked_port),
                    db=wp_connector.linked_dbname,
                    user=wp_connector.linked_user,
                    password=wp_connector.linked_pwd,
                )

                # Pool used:
                linked_product_pool = odoo.model('product.product.web.server')
                linked_master_ids = linked_product_pool.search([
                    ('wp_parent_template', '=', True),
                    ])
                master_product.extend([p for p in linked_product_pool.browse(
                        linked_master_ids)])
            except:
                _logger.error('Cannot login on linked database')

        master_product = sorted(
            master_product,
            key=lambda o: o.product_id.default_code,
        )

        _logger.warning('Selected product: %s' % len(master_ids))
        for web_product in master_product:
            if store_data:
                json_product = {}

            product = web_product.product_id
            if row == 1:
                row += 1
            product_row = row
            h = web_product.web_H
            w = web_product.web_W
            l = web_product.web_L
            weight = web_product.web_weight
            volumetric = web_product.web_volumetric
            if fall_back:
                h = h or web_product.pack_h
                w = w or web_product.pack_l
                l = l or web_product.pack_p
                weight = weight or web_product.weight
                volumetric = volumetric or web_product.wp_volume

            excel_pool.write_xls_line(
                ws_name, row, [
                    u'%s-%s' % (product.company_id.name, product.id),
                    product.default_code or '',
                    product.name or '',
                    h,
                    w,
                    l,
                    weight,
                    volumetric,
                ], default_format=excel_format['white']['text'])

            for broker in brokers:
                broker_name = broker.name
                broker_zones, default_zone, pos = get_zone(
                    broker, broker_col, cache=cache)

                couriers = sorted(broker.child_ids, key=lambda c: c.name)
                header_load = True
                for courier in couriers:
                    row += 1

                    # ---------------------------------------------------------
                    #                    Header 2 (first time)
                    # ---------------------------------------------------------
                    if header_load:
                        header_load = False
                        # -----------------------------------------------------
                        # Header 2: Zones:
                        # -----------------------------------------------------
                        # 1. Empty:
                        if product_row != row - 1:
                            excel_pool.write_xls_line(
                                ws_name, row-1, empty,
                                default_format=excel_format['white']['text'],
                                )
                        # 2. Fixed common part:
                        excel_pool.write_xls_line(
                            ws_name, row-1, header2,
                            default_format=excel_format['header'],
                            col=product_col)
                        # 3. Broker Zone:
                        excel_pool.write_xls_line(
                            ws_name, row - 1, [
                                z.name for z in sorted(
                                    broker_zones,
                                    key=lambda bz: bz.name
                                )],
                            default_format=excel_format['header'],
                            col=broker_col)
                    courier_col = broker_col + len(broker_zones)

                    # ---------------------------------------------------------
                    #               Check constraints:
                    # ---------------------------------------------------------
                    constraint_comment = product_check_constraints(
                        courier, h, w, l, volumetric, weight, cache=cache)

                    # ---------------------------------------------------------
                    #               Data price for courier:
                    # ---------------------------------------------------------
                    courier_zones, _, courier_col = get_zone(
                        courier, courier_col, mode='courier', cache=cache)

                    # 1. Empty:
                    excel_pool.write_xls_line(
                        ws_name, row, empty,
                        default_format=excel_format['white']['text'])

                    if constraint_comment:
                        data_color = excel_format['red']

                        # Write comment on courier cell:
                        excel_pool.write_comment(
                            ws_name, row, product_col + 3, constraint_comment,
                            comment_param)
                    else:
                        data_color = excel_format['white']

                    sequence = 0  # todo read from product correct value

                    # 2. Data (colored depend on constraints):
                    excel_pool.write_xls_line(
                        ws_name, row, [
                            # choose better solution:
                            '' if constraint_comment else sequence,
                            broker_name,
                            # Hidden ID only if courier present:
                            '' if constraint_comment else courier.id,
                            courier.name,
                        ],
                        default_format=data_color['text'],
                        col=product_col)

                    if store_data and not constraint_comment:  # used courier:
                        if sequence not in json_product:
                            json_product[sequence] = {}
                        if courier.id not in json_product[sequence]:
                            json_product[sequence][courier.id] = {}

                    # Pricelist will be added only if not constraints problem:
                    if not constraint_comment:
                        pricelist = get_prices(
                            courier, h, w, l, volumetric, weight)
                        for zone in pricelist:
                            # Explode data:
                            pl_data = pricelist[zone]
                            pl_price = pl_data['price']
                            pl_comment = pl_data['comment']
                            pl_error = pl_data['error']

                            if pl_error or not pl_price:
                                color_format = excel_format['red']
                            elif zone == default_zone:
                                color_format = excel_format['blue']
                            else:
                                color_format = excel_format['white']

                            # Broker pricelist / zones:
                            price_col = broker_zones.get(zone)
                            if price_col:
                                excel_pool.write_xls_line(
                                    ws_name, row, [pl_price],
                                    default_format=color_format['number'],
                                    col=price_col)

                                if store_data:  # todo manage pririty!!
                                    json_product[sequence][courier.id][
                                        zone.id] = pl_price

                                if pl_comment:
                                    excel_pool.write_comment(
                                        ws_name, row, price_col, pl_comment,
                                        comment_param)
                            else:
                                # Courier pricelist / zones:
                                price_col = courier_zones.get(zone)
                                if price_col:
                                    excel_pool.write_xls_line(
                                        ws_name, row, [pl_price],
                                        default_format=color_format['number'],
                                        col=price_col)
                                    if store_data:  # todo manage priority!
                                        json_product[sequence][courier.id][
                                            zone.id] = pl_price

                                    if pl_comment:
                                        # Write also zone name:
                                        pl_comment = '%s\n%s' % (
                                            zone.name,
                                            pl_comment,
                                            )
                                        excel_pool.write_comment(
                                            ws_name, row, price_col,
                                            pl_comment, comment_param)
            # Store JSON data for this product
            if store_data:
                if current_db == product.company_id.name:
                    product_id = product.id
                    linked_product_ref = ''
                else:
                    product_id = False
                    linked_product_ref = product.id

                stored_pool.create(cr, uid, {
                    'product_id': product_id,
                    'default_code': product.default_code,
                    'linked_product_ref': linked_product_ref,
                    'json_data': json.dumps(json_product),
                }, context=context)

                row += 1  # to print header
        return excel_pool.return_attachment(cr, uid, 'web_product')

    _columns = {
        'no_transport': fields.boolean(
            'No trasporto',
            help='Indica che il corriere non ha costo di trasporto, '
                 'utilizzato generalmente per il ritoro a magazzino'),
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


class CarrierSupplierStoredData(orm.Model):
    """ Model name: Stored data
    """

    _name = 'carrier.supplier.stored.data'
    _description = 'Dati storicizzati'
    _rec_name = 'product_id'

    def _function_json_data_html(
            self, cr, uid, ids, fields, args, context=None):
        """ Fields function for calculate
        """
        courier_pool = self.pool.get('carrier.supplier')
        zone_pool = self.pool.get('sale.order.carrier.zone')

        res = {}
        for product in self.browse(cr, uid, ids, context=context):
            res[product.id] = ''
            product_id = product.product_id
            linked_product_ref = product.linked_product_ref

            if product_id:
                name = 'DB attuale: %s\n' % product_id
            else:
                name = 'DB collegato: %s\n' % linked_product_ref

            res[product.id] += 'Ordine: %s\n' % sequence
            product_json = json.loads(product.json_data)
            for sequence in product_json:
                res[product.id] += 'Seq.: %s\n' % sequence
                for courier_id in product_json[sequence]:
                    courier = courier_pool.browse(
                        cr, uid, int(courier_id), context=context)
                    res[product.id] += 'Corriere.: %s\n' % courier.name
                    for zone_id in product_json[sequence][courier_id]:
                        zone = zone_pool.browse(
                            cr, uid, int(zone_id), context=context)
                        price = product_json[sequence][courier_id][zone_id]
                        res[product.id] += 'Zona.: %s - Prezzo: %s\n' % (
                            zone.name, price)
        return res

    _columns = {
        'product_id': fields.many2one('product.product', 'Prodotto'),
        'default_code': fields.char('Prodotto collegato', size=20),
        'linked_product_ref': fields.integer('Prodotto collegato'),
        'json_data': fields.text('JSON Data'),
        'json_data_html':  fields.function(
            _function_json_data_html, method=True,
            type='text', string='Dettaglio trasporti',
            help='Campo che sviluppa i trasporti giornalmente per la scelta'
                 'del migliore da utilizzare'),
        }

