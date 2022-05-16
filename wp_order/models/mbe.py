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
import shutil
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
    # Utility:
    # -------------------------------------------------------------------------
    def print_label(self, cr, uid, ids, context=None):
        """ Extract label
        """
        if context is None:
            context = {}

        order_id = ids[0]
        order = self.browse(cr, uid, order_id, context=context)

        carrier = order.carrier_supplier_id
        if carrier.account_ref != 'MBE':
            return super(
                WordpressSaleOrderCarrierTop, self).print_label(
                cr, uid, ids, context=context)

        # ---------------------------------------------------------------------
        #                              Download label:
        # ---------------------------------------------------------------------
        # Save to file:
        # ---------------------------------------------------------------------
        user = self.pool.get('res.users').browse(
            cr, uid, uid, context=context)
        path = self.get_folder_root_path(cr, 'tracking')

        # todo not managed for now:
        parcel_path = self.get_folder_root_path(cr, 'parcel', root_path=path)
        label_path = self.get_folder_root_path(cr, 'label', root_path=path)
        filename = '%s.1.PDF' % order_id
        fullname = os.path.join(label_path, filename)

        # ---------------------------------------------------------------------
        # Connection:
        # ---------------------------------------------------------------------
        connection = carrier.carrier_connection_id
        root = connection.location
        token = connection.passphrase

        tracking_id = order.carrier_track_id  # must exist
        if not tracking_id:
            raise osv.except_osv(
                _('Errore Etichetta:'),
                _('Impossibile scaricare etichette se non è presente '
                  'il tracking ID!'),
            )

        location = '%sshippings/%s/label/pdf?termica=1&apitoken=%s' % (
            root, tracking_id, token)
        header = {
            'Content-Type': 'application/json',
        }
        reply = requests.get(
            location,
            data=json.dumps({}),
            headers=header,
            verify=False,
        )
        if reply.ok:
            data_pdf = reply.content
            pdf_file = open(fullname, 'wb')
            pdf_file.write(data_pdf)
            pdf_file.close()
            _logger.warning('Save label to file: %s' % fullname)
        else:
            raise osv.except_osv(
                _('Errore etichetta:'),
                _('Il portale non ha restituito nessuna etichetta!'),
            )

        # ---------------------------------------------------------------------
        # Print file:
        # ---------------------------------------------------------------------
        printer_code = \
            order.courier_mode_id.cups_printer_id.code or \
            order.courier_supplier_id.cups_printer_id.code or \
            order.carrier_mode_id.cups_printer_id.code or \
            order.carrier_supplier_id.cups_printer_id.code or \
            order.carrier_connection_id.cups_printer_id.code

        # Check if need to print or to save:
        company = user.company_id
        if company.carrier_save_label:  # todo needed?
            saved_path = os.path.join(
                os.path.expanduser(company.carrier_save_label_path),
                printer_code,
            )
            os.system('mkdir -p %s' % saved_path)  # Create path
            saved_fullname = os.path.join(saved_path, filename)
            shutil.copy(fullname, saved_fullname)
            _logger.warning('Saved label in: %s' % saved_fullname)
        else:
            return self.send_report_to_cups_printer(
                cr, uid, ids, fullname, printer_code, context=context)

    def clean_text(self, text, cut=35):
        """ Return char in ASCII
        """
        # return (text or '').decode('utf8').encode(
        # 'ascii', 'xmlcharrefreplace')
        # return (text or u'').decode('utf8').encode('ascii', 'replace')
        return (text or u'').encode('ascii', 'replace')[:cut]

    # -------------------------------------------------------------------------
    #                             API interface:
    # -------------------------------------------------------------------------
    def shipment_request(self, cr, uid, ids, context=None):
        """ 15. API Shipment Request: Insert new carrier request
        """
        assert len(ids) == 1, 'Un\'ordine alla volta'

        pdb.set_trace()
        order = self.browse(cr, uid, ids, context=context)[0]

        carrier_connection = order.carrier_connection_id
        if not carrier_connection:
            return 'Order %s has carrier without SOAP ref.!' % order.name
        # todo if order.state not in 'draft':
        #    return 'Order %s not in draft mode so no published!' % order.name

        # todo verificare che campo era (ex. carrier_soap_id)
        # if order.carrier_supplier_id:
        #    return 'Order %s has SOAP ID %s cannot publish!' % (
        #            order.name, order.carrier_supplier_id)

        # Write description if not present:
        if not order.carrier_description:
            self.set_default_carrier_description(cr, uid, ids, context=context)

        # -----------------------------------------------------------------
        # HTML insert call:
        # -----------------------------------------------------------------
        data = order.get_request_container(
            customer=False, system=True, connection=carrier_connection)
        data.update({
            'Recipient': self.get_recipient_container(
                cr, uid, ids, context=context),
            'Shipment': self.get_shipment_container(
                cr, uid, ids, context=context),
            })

        result_data = self.html_post(
            cr, uid, ids,
            carrier_connection, 'ShipmentRequest', data, undo_error=True,
            context=context,
            )
        return self.update_order_with_soap_reply(
            cr, uid, ids, result_data, context=context)

    # todo change:
    def carrier_remove_reservation(self, cr, uid, ids, context=None):
        """ Delete reservation
        """
        if context is None:
            context = {}

        order = self.browse(cr, uid, ids, context=context)[0]

        carrier = order.carrier_supplier_id
        if carrier.account_ref != 'MBE':
            return super(
                WordpressSaleOrderCarrierTop, self).carrier_remove_reservation(
                cr, uid, ids, context=context)

        # Connection:
        connection = carrier.carrier_connection_id
        root = connection.location
        token = connection.passphrase

        tracking_id = order.carrier_track_id  # must exist
        if not tracking_id:
            raise osv.except_osv(
                _('Errore Cancellazione:'),
                _('Impossibile cancellare la prenotazione, Tracking ID '
                  'non presente, usare il portale!'),
            )

        location = '%sshippings/%s?apitoken=%s' % (
            root, tracking_id, token)

        header = {
            'Content-Type': 'application/json',
        }
        reply = requests.delete(
            location,
            data=json.dumps({}),
            headers=header,
            verify=False,
        )
        if reply.ok:
            reply_data = reply.json()
            error = reply_data.get('error')
            if error:
                raise osv.except_osv(
                    _('Portale Topfly:'),
                    _('Errore segnalato dal portale:\n%s') % error,
                )
            result = reply_data.get('result')
            if result:
                self.write(cr, uid, ids, {
                    'master_tracking_id': False,
                    'carrier_track_id': False,
                }, context=context)
            else:
                raise osv.except_osv(
                    _('Errore Cancellazione:'),
                    _('La chiamata non permette la cancellazione di questo'
                      'Tracking ID, usare il portale!'),
                )
        return True

    def get_rate(self, cr, uid, ids, context=None):
        """ Get best rate for this order
            Context parameter:
                force_api_mode: preview, create
        """
        if context is None:
            context = {}

        order = self.browse(cr, uid, ids, context=context)[0]

        carrier = order.carrier_supplier_id
        if carrier.account_ref != 'MBE':
            return super(WordpressSaleOrderCarrierTop, self).get_rate(
                cr, uid, ids, context=context)
        # ---------------------------------------------------------------------
        # Create mode:
        # ---------------------------------------------------------------------
        if context.get('force_api_mode') == 'create':
            return self.shipment_request(cr, uid, ids, context=context)

        # ---------------------------------------------------------------------
        # Get rate mode:
        # ---------------------------------------------------------------------
        order = self.browse(cr, uid, ids, context=context)[0]

        # Carrier connection (B)
        # todo write correct test:
        carrier_connection = order.carrier_supplier_id.carrier_connection_id
        if not carrier_connection:
            return 'Ordine %s non ha il riferimento alla connessione!' % \
                   order.name
        # if order.state not in 'draft':
        #    return 'Ordine %s è a bozza quindi non pubblicato!' % order.name
        # if order.carrier_supplier_id:
        #    return 'Order %s has SOAP ID %s cannot publish!' % (
        #            order.name, order.carrier_supplier_id)

        # ---------------------------------------------------------------------
        # SOAP insert call:
        # ---------------------------------------------------------------------
        # A. Economy request:
        # todo no more use parcel connection (removed from list):
        #    item.soap_connection_id for item in self.parcel_ids
        #    if item.soap_connection_id]

        # B. Standard request:
        error = ''
        reply_list = []

        # Generate data for request:
        data = self.get_request_container(
            cr, uid, ids,
            customer=False, system=True, connection=carrier_connection,
            context=context,
        )
        data['ShippingParameters'] = order.get_shipment_parameters_container()
        result_data = self.html_post(
            cr, uid, ids, carrier_connection, 'ShippingOptionsRequest', data,
            undo_error=False, context=context)  # todo True
        reply_list.append((carrier_connection, result_data))

        # if not error:
        # Update data for real call
        self.update_with_quotation(cr, uid, ids, reply_list, context=context)
        return error
