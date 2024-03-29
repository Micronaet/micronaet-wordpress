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
import json

_logger = logging.getLogger(__name__)


class WordpressSaleOrder(orm.Model):
    """ Model name: WP order
    """
    _inherit = 'wordpress.sale.order'

    def extract_wordpress_published_report(self, cr, uid, ids, context=None):
        """ Extract list of published elements:
        """
        delivery_mode_text = {
            'manual': 'GPB',
            'prime': 'PRIME',
            'normal': '',
        }
        # Pool used:
        excel_pool = self.pool.get('excel.writer')

        # ---------------------------------------------------------------------
        #                         Excel report:
        # ---------------------------------------------------------------------
        today = datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT)
        order_ids = self.search(cr, uid, [
            ('traking_date', '=', today),
            # todo when all auto restore!:
            # ('master_tracking_id', '!=', False),
            ], context=context)

        ws_name = 'Chiusure giornaliere'
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
            'green': {
                'text': excel_pool.get_format('bg_green'),
                'number': excel_pool.get_format('bg_green_number'),
                },
            }

        # ---------------------------------------------------------------------
        # Published product:
        # ---------------------------------------------------------------------
        # Width
        excel_pool.column_width(ws_name, [
            5, 5, 5,
            8, 6,
            8, 10,
            12, 35, 10,
            20, 35,
            10, 10, 12, 12,
            19, 10,
            ])

        # Print header
        row = 4
        header = [
            'Etich', 'Pronto', 'Spedito',
            'Marketplace', 'Prime',
            'Ordine', 'Consegna',
            'Imballo', 'Dettaglio', 'Peso',
            'Cliente', 'Destinazione',
            'Corriere', 'Tipo', 'Spedizioniere', 'Servizio',
            'Tracking', 'Stato',
            ]
        excel_pool.write_xls_line(
            ws_name, row, header, default_format=excel_format['header'])
        excel_pool.autofilter(ws_name, row, 0, row, len(header) - 1)
        excel_pool.freeze_panes(ws_name, row + 1, 7)

        _logger.warning('Selected order: %s' % len(order_ids))

        summary = {}
        for mode in delivery_mode_text.values():
            summary[mode] = {
                'weight': 0.0,
                'total': 0,
                'parcel': 0,
                'label': 0,
            }

        for order in sorted(self.browse(
                cr, uid, order_ids, context=context),
                key=lambda o: o.delivery_detail):
            row += 1
            master_tracking_id = order.master_tracking_id or ''
            parcel_detail = order.parcel_detail or ''
            manual_label = order.manual_label
            if master_tracking_id or manual_label:
                color_format = excel_format['black']
            elif not parcel_detail:
                color_format = excel_format['yellow']
            else:
                color_format = excel_format['red']

            parcels = len(order.parcel_ids)
            weight = sum([p.real_weight for p in order.parcel_ids])
            mode = delivery_mode_text.get(order.delivery_mode, '')

            # -----------------------------------------------------------------
            # Summary total:
            # -----------------------------------------------------------------
            summary[mode]['weight'] += weight
            summary[mode]['total'] += 1
            summary[mode]['parcel'] += parcels
            if order.label_printed:
                summary[mode]['label'] += 1
            # -----------------------------------------------------------------

            excel_pool.write_xls_line(
                ws_name, row, [
                    'X' if order.label_printed else '',
                    '',
                    '',
                    order.marketplace,
                    mode,
                    order.name,
                    order.traking_date or '',

                    parcel_detail,
                    order.delivery_detail or '',
                    weight or '',

                    order.partner_name,
                    order.shipping,

                    order.carrier_supplier_id.name or '',
                    order.carrier_mode_id.name or '',
                    order.courier_supplier_id.name or '',
                    order.courier_mode_id.name or '',

                    master_tracking_id,
                    order.carrier_state or '',
                ], default_format=color_format['text'])
            excel_pool.row_height(ws_name, row, 36)

        # Summary table:
        row = 0
        header = [
            'Dettaglio', '', '',
            'Ordini', 'Peso', 'Colli', 'Etichette'
            ]
        excel_pool.write_xls_line(
            ws_name, row, header, default_format=excel_format['header'])
        excel_pool.merge_cell(ws_name, [row, 0, row, 2])

        for mode in summary:
            if mode:
                mode_text = mode
            else:
                mode_text = 'Normale'
            line = summary[mode]
            row += 1
            line_data = [
                (mode_text, excel_format['black']['text']),
                '',
                '',
                '%.0f' % line['total'],
                '%.2f' % line['weight'],
                '%.0f' % line['parcel'],
                '%.0f' % line['label'],
            ]
            excel_pool.merge_cell(ws_name, [row, 0, row, 2])
            excel_pool.write_xls_line(
                ws_name, row, line_data,
                default_format=excel_format['black']['number'])
        return excel_pool.return_attachment(cr, uid, 'web_product')
