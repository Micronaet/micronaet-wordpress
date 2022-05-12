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

    def clean_text(self, text):
        """ Return char in ASCII
        """
        # return (text or '').decode('utf8').encode(
        # 'ascii', 'xmlcharrefreplace')
        try:
            return (text or u'').decode('utf8').encode('ascii', 'replace')
        except:
            pdb.set_trace()

    # -------------------------------------------------------------------------
    #                             API interface:
    # -------------------------------------------------------------------------
    def get_rate(self, cr, uid, ids, context=None):
        """ Get best rate for this order
        """
        order = self.browse(cr, uid, ids, context=context)[0]

        carrier = order.carrier_supplier_id
        if carrier.account_ref != 'TOP':
            return super(WordpressSaleOrderCarrierTop, self).get_rate(
                cr, uid, ids, context=context)

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
        connection = carrier.carrier_connection_id
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
                'codice_servizio': self.clean_text(service_code),
                'dest_destinatario': self.clean_text(order.partner_name),
                'dest_via': self.clean_text(u'%s %s' % (
                    shipping.get('address_1', ''),
                    shipping.get('address_2', ''),
                    )),
                'dest_comune': self.clean_text(shipping.get('city')),
                'dest_cap': self.clean_text(shipping.get('postcode')),
                'dest_provincia': self.clean_text(shipping.get('state')),
                'dest_nazione': self.clean_text(shipping.get('country', 'IT')),
                'dest_tel': self.clean_text(billing.get('phone', '')),
                'dest_email': self.clean_text(billing.get('mail', '')),
                'dest_riferimento': self.clean_text(u'%s %s' % (
                    shipping.get('last_name', ''),
                    shipping.get('first_name', ''),
                )),
                'valore_merce': 0,
                'imp_assicurato': 0,
                'imp_contrassegno': 0,
                'note_spedizioniere': self.clean_text(wp_record.get(
                    'customer_note')),
                'service_option_CONTRASSEGNO': False,
            },
            'colli': [],
        }
        colli = payload['colli']
        for parcel in order.parcel_ids:
            colli.append({
                'tipo': 'merce',  # todo 'documenti',
                'pesodic': parcel.real_weight,
                'desc': 'Scatola',  # todo?
                'p': parcel.length,
                'l': parcel.width,
                'h': parcel.height,
                })

        pdb.set_trace()
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
