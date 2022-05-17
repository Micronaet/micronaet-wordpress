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


class WordpressSaleOrder(orm.Model):
    """ Model name: WP order
    """
    _inherit = 'wordpress.sale.order'

    def extract_wordpress_published_report(self, cr, uid, ids, context=None):
        """ Extract list of published elements:
        """
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
            }

        # ---------------------------------------------------------------------
        # Published product:
        # ---------------------------------------------------------------------
        # Width
        excel_pool.column_width(ws_name, [
            8, 10, 19, 25, 35, 15, 15, 15, 15, 20, 40, 15
            ])

        # Print header
        row = 0
        excel_pool.write_xls_line(
            ws_name, row, [
                'Ordine', 'Consegna', 'Tracking',
                'Cliente', 'Destinazione',
                'Corriere', 'Tipo',
                'Spedizioniere', 'Servizio',
                'Imballo', 'Dettaglio',
                'Stato',
                ], default_format=excel_format['header'])

        _logger.warning('Selected order: %s' % len(order_ids))
        for order in sorted(self.browse(
                cr, uid, order_ids, context=context),
                key=lambda o: o.name, reverse=True):
            color_format = excel_format['black']
            row += 1
            excel_pool.write_xls_line(
                ws_name, row, [
                    order.name,
                    order.traking_date or '',
                    order.master_tracking_id or '',
                    order.partner_name,
                    order.shipping,

                    order.carrier_supplier_id.name or '',
                    order.carrier_mode_id.name or '',
                    order.courier_supplier_id.name or '',
                    order.courier_mode_id.name or '',

                    order.parcel_detail or '',
                    order.carrier_description or '',
                    order.carrier_state or '',
                ], default_format=color_format['text'])

        return excel_pool.return_attachment(cr, uid, 'web_product')
