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


class WordpressSaleOrderCarrierMBE(orm.Model):
    """ Model name: Wordpress Sale order for carrier operations
    """
    _inherit = 'wordpress.sale.order'

    # -------------------------------------------------------------------------
    # Utility:
    # -------------------------------------------------------------------------
    def update_with_quotation(
            self, cr, uid, ids, reply_list=None, context=None):
        """ Update order courier fields with reply SOAP
        """
        order = self.browse(cr, uid, ids, context=context)[0]

        # Pool used:
        supplier_pool = self.pool.get('carrier.supplier')
        service_pool = self.pool.get('carrier.supplier.mode')

        # Filter parameters:
        carrier_mode_search = order.carrier_mode_id.account_ref

        # Courier:
        courier_supplier_search = order.courier_supplier_id.account_ref
        courier_mode_search = order.courier_mode_id.account_ref

        better = {}

        # Join quotations in one list:
        quotation_list = []
        for connection, reply in reply_list:
            try:
                quotations = reply['ShippingOptions']['ShippingOption']
            except:
                _logger.error('No shipping option for better quotation')
                continue

            _logger.warning(
                'Quotation founds: %s [Mode search: %s, %s, %s]' % (
                    len(quotations),
                    carrier_mode_search or 'no carrier mode',
                    courier_supplier_search or 'no courier supplier',
                    courier_mode_search or 'no courier mode',
                    ))
            for quotation in quotations:
                quotation_list.append((connection, quotation))

        # Choose better quotation:
        _logger.warning(str(quotation_list))
        for record in quotation_list:
            connection, quotation = record

            # -----------------------------------------------------------------
            # START Init setup  # todo remove
            # -----------------------------------------------------------------
            init_setup = False
            if init_setup:
                # -------------------------------------------------------------
                # A. Courier:
                # -------------------------------------------------------------
                courier_code = str(quotation['Courier'])
                courier_name = str(quotation['CourierDesc'])
                suppliers = supplier_pool.search(cr, uid, [
                    ('account_ref', '=', courier_code),
                    ('mode', '=', 'courier'),
                ], context=context)
                if suppliers:
                    supplier_id = suppliers[0]
                else:
                    supplier_id = supplier_pool.create(cr, uid, {
                        'account_ref': courier_code,
                        'name': courier_name,
                        'mode': 'courier',
                    }, context=context)

                # -------------------------------------------------------------
                # B. Courier service:
                # -------------------------------------------------------------
                service_code = str(quotation['CourierService'])
                service_name = quotation['CourierServiceDesc']
                services = service_pool.search(cr, uid, [
                    ('account_ref', '=', service_code),
                    ('supplier_id', '=', supplier_id),
                ], context=context)
                if not services:
                    service_pool.create(cr, uid, {
                        'account_ref': service_code,
                        'name': service_name,
                        'supplier_id': supplier_id,
                    }, context=context)
            # -----------------------------------------------------------------
            # END Init setup
            # -----------------------------------------------------------------

            try:
                # -------------------------------------------------------------
                # Filter:
                # -------------------------------------------------------------
                # 1. Check carrier if selected in request:
                if (carrier_mode_search and carrier_mode_search !=
                        str(quotation['Service'])):
                    continue

                # 2. Check courier if requested:
                if (courier_supplier_search and courier_supplier_search !=
                        str(quotation['Courier'])):
                    continue

                # 3. Check courier mode if requested:
                if (courier_mode_search and courier_mode_search !=
                        str(quotation['CourierService'])):
                    continue

                # 4. Check and save best quotation:
                if not better or (quotation['NetShipmentTotalPrice'] <
                                  better[1]['NetShipmentTotalPrice']):
                    better = record
            except:
                _logger.error('Error on quotation: %s' % (
                    sys.exc_info(), ))

        # todo no need to create 21 nov. 2020?!?:
        # Update order with better quotation:
        data = False

        if better:
            connection, data = better
            try:
                # -------------------------------------------------------------
                # A. Courier:
                # -------------------------------------------------------------
                courier_code = str(data['Courier'])
                courier_name = str(data['CourierDesc'])
                suppliers = supplier_pool.search(cr, uid, [
                    ('account_ref', '=', courier_code),
                    ('mode', '=', 'courier'),
                ], context=context)
                if suppliers:
                    supplier_id = suppliers[0]
                else:
                    supplier_id = supplier_pool.create(cr, uid, {
                        'account_ref': courier_code,
                        'name': courier_name,
                        'mode': 'courier',
                    }, context=context)

                # -------------------------------------------------------------
                # B. Courier service:
                # -------------------------------------------------------------
                service_code = str(data['CourierService'])
                service_name = data['CourierServiceDesc']
                services = service_pool.search(cr, uid, [
                    ('account_ref', '=', service_code),
                    ('supplier_id', '=', supplier_id),
                ], context=context)
                if services:
                    service_id = services[0]
                else:
                    service_id = service_pool.create(cr, uid, {
                        'account_ref': service_code,
                        'name': service_name,
                        'supplier_id': supplier_id,
                    }, context=context)

                # -------------------------------------------------------------
                # C. Carrier service:
                # -------------------------------------------------------------
                carrier_id = order.carrier_supplier_id.id
                carrier_code = str(data['Service'])
                carrier_name = data['ServiceDesc']
                carriers = service_pool.search(cr, uid, [
                    ('account_ref', '=', carrier_code),
                    ('supplier_id', '=', carrier_id),
                ], context=context)
                if carriers:
                    carrier_mode_id = carriers[0]
                else:
                    carrier_mode_id = service_pool.create(cr, uid, {
                        'account_ref': carrier_code,
                        'name': carrier_name,
                        'supplier_id': carrier_id,
                    }, context=context)

                self.write(cr, uid, ids, {
                    'carrier_connection_id': connection.id,
                    'carrier_cost': data['NetShipmentPrice'],
                    'carrier_cost_total': data['NetShipmentTotalPrice'],
                    'has_cod': data['CODAvailable'],
                    'has_insurance': data['InsuranceAvailable'],
                    'has_safe_value': data['MBESafeValueAvailable'],
                    'courier_supplier_id': supplier_id,
                    'courier_mode_id': service_id,
                    'carrier_mode_id': carrier_mode_id,
                    # 'soap_last_error': False,  # Clean error when write
                }, context=context)

                # 'IdSubzone': 125,
                # 'SubzoneDesc': 'Italia-Zona A',

                return ''
            except:
                data = {}  # Used for new check

        if not data:  # Or previous update error
            # Reset data:
            self.write(cr, uid, ids, {
                'carrier_connection_id': False,
                'carrier_cost': 0.0,
                'carrier_mode_id': False,
                'courier_supplier_id': False,
                'courier_mode_id': False,
            })
            return 'Error updating data on order (clean quotation)'
        return ''

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
                WordpressSaleOrderCarrierMBE, self).print_label(
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
        """ 4. API Delete Shipment Request: Delete shipment request
        """
        if context is None:
            context = {}

        order = self.browse(cr, uid, ids, context=context)[0]
        carrier = order.carrier_supplier_id
        if carrier.account_ref != 'MBE':
            return super(
                WordpressSaleOrderCarrierMBE, self).carrier_remove_reservation(
                cr, uid, ids, context=context)

        error = ''
        carrier_connection = order.carrier_connection_id
        if not carrier_connection:
            return 'Order %s has carrier without SOAP ref.!' % order.name

        master_tracking_id = order.master_tracking_id
        if master_tracking_id:
            data = self.get_request_container(
                cr, uid, ids, system='SystemType',
                connection=carrier_connection, context=context)
            data[
                'MasterTrackingsMBE'] = master_tracking_id  # Also with Loop
            result_data = self.html_post(
                cr, uid, ids,
                carrier_connection, 'DeleteShipmentsRequest', data,
                context=context,
            )
        else:
            _logger.error(
                'Order %s has no master tracking, cannot delete!' %
                order.name)

        # Check carrier_track_id for permit delete:
        if not error:
            order.write({
                'carrier_soap_state': 'draft',
                'master_tracking_id': False,
                'system_reference_id': False,
                'carrier_track_id': False,
                'carrier_mode_id': False,
                'courier_supplier_id': False,
                'courier_mode_id': False,
                'carrier_cost': False,
                'label_printed': True,
            })
        return error

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
            return super(WordpressSaleOrderCarrierMBE, self).get_rate(
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
