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
import requests
import json
from openerp.osv import fields, osv, expression, orm
from datetime import datetime, timedelta
from openerp import tools
from openerp.tools.translate import _
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT,
    DEFAULT_SERVER_DATETIME_FORMAT,
    DATETIME_FORMATS_MAP,
    float_compare)

_logger = logging.getLogger(__name__)


class WordpressSaleOrderCarrierTop(orm.Model):
    """ Model name: Wordpress Sale order for carrier operations
    """
    _inherit = 'wordpress.sale.order'

    # -------------------------------------------------------------------------
    #                             API interface:
    # -------------------------------------------------------------------------
    def get_rate(self, cr, uid, ids, code, context=None):
        """ Get best rate for this order
        """
        web_product_pool = self.pool.get('product.product.web.server')

        order = self.browse(cr, uid, ids, context=context)[0]

        carrier = order.carrier_supplier_id

        if carrier.code != 'TOP':
            return super(WordpressSaleOrderCarrierTop, self).get_rate(
                cr, uid, ids, code, context=context)

        # ---------------------------------------------------------------------
        # Parameters:
        # ---------------------------------------------------------------------
        carrier_mode = order.carrier_mode_id
        courier_supplier = order.courier_supplier_id
        courier_mode = order.courier_mode_id
        service_code = courier_mode.account_ref
        if not all((courier_supplier, courier_mode, carrier_mode)):
            raise osv.except_osv(
                _('Errore Get Rate:'),
                _('Non presenti tutti e 4 i parametri richiesti per avere una'
                  'quotazione'),
            )

        # Connection:
        connection = carrier.connection_id
        root = connection.location
        token = connection.passphrase
        location = '%sshippings/preview?apitoken=%s' % (root, token)

        wp_record = eval(order.wp_record)
        billing = wp_record.get('billing', {})
        shipping = wp_record.get('shipping', {})
        header = {
            'Content-Type': 'application/json',
        }

        payload = {
            'header': {
                'codice_servizio': service_code,
                'dest_destinatario': order.partner_name,
                'dest_via': '%s %s' % (
                    shipping.get('address_1'),
                    shipping.get('address_2'),
                    ),
                'dest_comune': shipping.get('city'),
                'dest_cap': shipping.get('postcode'),
                'dest_provincia': shipping.get('state'),
                'dest_nazione': shipping.get('country', 'IT'),
                'dest_tel': billing.get('phone'),
                'dest_email': billing.get('mail'),
                'dest_riferimento': '%s %s' % (
                    shipping.get('last_name', ''),
                    shipping.get('first_name', ''),
                ),
                'valore_merce': 0,
                'imp_assicurato': 0,
                'imp_contrassegno': 0,
                'note_spedizioniere': wp_record.get('customer_note', ''),
                'service_option_CONTRASSEGNO': False,
            },
            'colli': [],
        }
        colli = payload['colli']
        connector_id = False
        for line in order.line_ids:
            if not connector_id:
                connector_id = order.connector_id.id

            # Search sku data on 2 database
            product = self.get_product_from_wp_order_line(
                cr, uid, connector_id, line, context=context)
            if not product:
                # raise error
                continue

            product_id = product.id
            web_product = web_product_pool.search(cr, uid, [
                ('product_id', '=', product_id),
                ('connector_id.wordpress', '=', True),
            ], context=context)

            h = web_product.web_H or web_product.pack_h
            w = web_product.web_W or web_product.pack_l
            l = web_product.web_L or web_product.pack_p
            weight = web_product.web_weight or web_product.product_id.weight
            # volumetric = web_product.web_volumetric

            colli.append({
                'tipo': 'merce',  # todo 'documenti',
                'pesodic': weight,
                'desc': 'una scatola',
                'p': l,
                'l': w,
                'h': h,
                })

        reply = requests.post(
            location,
            data=json.dumps(payload),
            headers=header,
        )

        if reply.ok:
            reply_data = reply.json()
            total = reply_data.get('shipping', {}).get('imp_totale')
            self.write(cr, uid, ids, {
                'pricelist_shipping_total': total,  # quotation price
                # 'real_shipping_total': total,  # confirmed price
            }, context=context)
            # todo manage error
        return True
