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
import openerp.addons.decimal_precision as dp
from openerp.osv import fields, osv, expression, orm
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp import SUPERUSER_ID
from openerp import tools
from openerp.tools.translate import _
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT,
    DEFAULT_SERVER_DATETIME_FORMAT,
    DATETIME_FORMATS_MAP,
    float_compare)


_logger = logging.getLogger(__name__)


class WordpressSaleOderCarrierReportWizard(orm.TransientModel):
    """ Wizard for label price
    """
    _name = 'wordpress.sale.oder.carrier.report.wizard'

    # --------------------
    # Wizard button event:
    # --------------------
    def action_print(self, cr, uid, ids, context=None):
        """ Event for button done
        """
        order_pool = self.pool.get('wordpress.sale.order')
        excel_pool = self.pool.get('excel.writer')

        if context is None:
            context = {}

        # ---------------------------------------------------------------------
        # Read parameter
        # ---------------------------------------------------------------------
        wizard = self.browse(cr, uid, ids, context=context)[0]
        from_date = wizard.from_date
        to_date = wizard.to_date

        # ---------------------------------------------------------------------
        # Generate Domain:
        # ---------------------------------------------------------------------
        domain = []
        # if from_date:
        #    domain.append(('traking_date', '>=', from_date))
        # if to_date:
        #    domain.append(('traking_date', '<=', to_date))

        # ---------------------------------------------------------------------
        #                         Collect data:
        # ---------------------------------------------------------------------
        today = str(datetime.now())[:10]
        order_ids = order_pool.search(cr, uid, domain, context=context)
        if not order_ids:
            raise osv.except_osv(
                _('Errore'),
                _('Nessuna consegna presente nel range di date scelto!'),
            )

        report_data = {}
        for order in order_pool.browse(cr, uid, order_ids, context=context):
            date = order.traking_date or order.date_order
            if date < from_date or date > to_date:
                continue  # Order extra range

            if order.delivery_mode == 'prime':
                carrier_name = 'Prime TNT'
            else:
                carrier_name = order.carrier_supplier_id.name or ''
            if carrier_name not in report_data:
                report_data[carrier_name] = []
            report_data[carrier_name].append(order)

        # ---------------------------------------------------------------------
        #                         Excel report:
        # ---------------------------------------------------------------------
        today = datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT)

        # ---------------------------------------------------------------------
        # Published product:
        # ---------------------------------------------------------------------
        # Width
        col_width = [
            15, 15, 15,
            35, 35,
            5, 5,
            12, 12, 15,
            10, 10,
            15, 15, 15, 15,
            ]

        # Print header
        header = [
            'Ordine', 'Data', 'Spedito',
            'Cliente', 'Consegna',
            'Colli', 'Peso',
            'Track ID', 'LDV ID', 'Stato',
            'Esposto', 'Costo',
            'Corriere', 'Tipo', 'Spedizioniere', 'Servizio',
            ]

        _logger.warning('Selected order: %s' % len(order_ids))

        excel_format = False
        for ws_name in report_data:
            excel_pool.create_worksheet(ws_name)

            # Load formats:
            if not excel_format:
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

            # Write Header:
            row = 0
            excel_pool.write_xls_line(
                ws_name, row, ['Movimenti carrier: %s data %s' % (
                    ws_name, today,
                    )], default_format=excel_format['title'])

            row += 1
            excel_pool.column_width(ws_name, col_width)
            excel_pool.write_xls_line(
                ws_name, row, header, default_format=excel_format['header'])
            excel_pool.autofilter(ws_name, row, 0, row, len(header) - 1)
            excel_pool.freeze_panes(ws_name, row + 1, 4)

            orders = report_data[ws_name]
            for order in sorted(orders, key=lambda o: o.name):  # todo name?
                row += 1

                order_name = order.name
                prime_order = order.delivery_mode == 'prime'
                # manual_label = order.manual_label
                master_tracking_id = order.master_tracking_id or ''
                parcel_detail = order.parcel_detail or ''
                manual_label = order.manual_label

                # Color:
                # if not parcel_detail:
                #    color_format = excel_format['yellow']
                if master_tracking_id or prime_order:
                    color_format = excel_format['black']
                else:
                    color_format = excel_format['red']

                parcels = len(order.parcel_ids)
                weight = sum([p.real_weight for p in order.parcel_ids])

                excel_pool.write_xls_line(
                    ws_name, row, [
                        # order.marketplace
                        order_name,
                        order.date_order or '',
                        order.traking_date or '',

                        order.billing or '',
                        order.shipping or '',

                        # 'X' if prime_order else '',
                        parcels or '',
                        weight or '',

                        order.carrier_track_id or '',
                        order.master_tracking_id or '',
                        order.state or '',

                        order.carrier_cost or '',
                        order.real_shipping_total or '',

                        order.carrier_supplier_id.name or '',
                        order.carrier_mode_id.name or '',
                        order.courier_supplier_id.name or '',
                        order.courier_mode_id.name or '',

                        # order.delivery_detail or '',
                        # order.carrier_state or '',
                    ], default_format=color_format['text'])

        return excel_pool.return_attachment(cr, uid, 'carrier_cost')

    _columns = {
        'from_date': fields.date('Dalla data', required=True),
        'to_date': fields.date('Alla data', required=True),
        }

