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
import re
import logging
import pdb
import requests
import subprocess
import shutil
import base64
# from requests.auth import HTTPBasicAuth  # or HTTPDigestAuth, or OAuth1, etc.
import xml.etree.cElementTree as ElementTree
import openerp
from lxml import etree
import openerp.netsvc as netsvc
import openerp.addons.decimal_precision as dp
from openerp.osv import fields, osv, expression, orm
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp.tools.translate import _


_logger = logging.getLogger(__name__)


class CarrierConnectionMBE(orm.Model):
    """ Model name: Carrier Connection
    """
    _inherit = 'carrier.connection'


class WordpressSaleOrderRelationCarrier(orm.Model):
    """ Model name: Wordpress Sale order
    """
    _inherit = 'wordpress.sale.order'

    # -------------------------------------------------------------------------
    # Printing:
    # -------------------------------------------------------------------------
    def send_report_to_cups_printer(
            self, cr, uid, ids, fullname, printer_code=False, loop=1,
            context=None):
        """ Send report to CUPS printer
            Report file
            Printer code (see printers list)
        """
        printer_pool = self.pool.get('cups.printer')
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)

        printer = False
        if printer_code:  # parameter for the procedure
            printer_ids = printer_pool.search(cr, uid, [
                ('code', '=', printer_code),
            ], context=context)
            if printer_ids:
                printer = printer_pool.browse(
                    cr, uid, printer_ids, context=context)[0]

        if not printer:
            printer = user.default_printer_id or \
                      user.company_id.default_printer_id or False
        if not printer:
            raise osv.except_osv(
                _('Errore Server MBE'),
                _('No printer with code or default setup'),
            )

        if not os.path.isfile(fullname):
            raise osv.except_osv(
                _('Errore Server MBE'),
                _('PDF not found: %s!') % fullname,
            )

        # -o landscape -o fit-to-page -o media=A4
        # -o page-bottom=N -o page-left=N -o page-right=N -o page-top=N
        printer_name = printer.name
        options = printer.options or ''

        # media=Custom.10x10cm
        # -o landscape -o fit-to-page -o media=Custom.2x2

        # -o fit-to-page -o media=A6
        # -o media=Custom.4x4in
        print_command = 'lp %s -d %s "%s"' % (
            options,
            printer_name,
            fullname,
        )
        # todo self.write_log_chatter_message(
        #    _('Printing %s on %s ...') % (fullname, printer_name))

        try:
            for repeat in range(loop):
                os.system(print_command)
                _logger.info('Printing call [time: %s]: %s' % (
                    repeat + 1, print_command))
            self.write(cr, uid, ids, {
                'label_printed': True,
            }, context=context)
        except:
            raise osv.except_osv(
                _('Errore Server MBE'),
                _('Error print PDF invoice on %s!') % printer_name,
            )
        return True

    def carrier_print_label(self, cr, uid, ids, context=None):
        """ Print label via CUPS
        """
        order_id = ids[0]
        order = self.browse(cr, uid, order_id, context=context)
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        # todo mode = 'label_01'
        path = self.get_folder_root_path(cr, 'tracking')

        # todo not managed for now:
        parcel_path = self.get_folder_root_path(cr, 'parcel', root_path=path)
        label_path = self.get_folder_root_path(cr, 'label', root_path=path)
        filename = '%s.1.PDF' % order_id
        fullname = os.path.join(label_path, filename)
        printer_code = \
            order.carrier_mode_id.cups_printer_id.code or \
            order.carrier_connection_id.cups_printer_id.code

        # Check if need to print or to save:
        company = user.company_id
        if company.carrier_save_label:
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

    # -------------------------------------------------------------------------
    # Utility:
    # -------------------------------------------------------------------------
    def clean_ascii_text(self, text):
        """ Replace accent
        """
        replace_list = {
            u'è': 'e\'',
            u'é': 'e\'',
            u'ò': 'o\'',
            u'à': 'a\'',
            u'ì': 'i\'',
            u'ù': 'u\'',
        }
        if not text:
            return ''
        res = ''
        pdb.set_trace()
        for c in text:
            if c in replace_list:
                res += replace_list[c]
            else:
                res += c
        return res


    def get_folder_root_path(
            self, cr, mode, root_path=None):
        """
        """
        if root_path is None:
            root_path = os.path.expanduser(
                '~/.local/share/Odoo/filestore/%s/data' % cr.dbname
                )
        path = os.path.join(root_path, mode)
        os.system('mkdir -p %s' % path)
        return path

    def save_order_label(
            self, cr, uid, ids, reply, mode='label', context=None):
        """ Save order label
        """
        order = self.browse(cr, uid, ids, context=context)[0]
        parcels = len(order.parcel_ids)
        path = self.get_folder_root_path(cr, mode)
        if mode == 'tracking':
            label_path = self.get_folder_root_path(
                cr, 'label', root_path=path)
            parcel_path = self.get_folder_root_path(
                cr, 'parcel', root_path=path)

        counter = 0
        if mode in ('label', 'tracking'):
            label_list = [reply['Labels']['Label']]
        else:
            label_list = [reply['Pdf']]
        for label in label_list:
            if mode in ('label', 'tracking'):
                counter += 1
                label_stream = base64.b64decode(label['Stream'])
                label_type = label['Type']
                filename = '%s.%s.%s' % (
                    order.id, counter, label_type)
                fullname = os.path.join(path, filename)
            else:
                label_stream = label
                fullname = os.path.join(path, '%s.PDF' % (
                    order.id))

            with open(fullname, 'wb') as label_file:
                label_file.write(label_stream)

            # Split label for Courier PDF:
            if mode == 'tracking':
                fullname_label = os.path.join(label_path, filename)
                fullname_parcel = os.path.join(parcel_path, filename)

                # Get number of pages:
                output = subprocess.check_output([
                    'pdftk', fullname, 'dump_data'])
                total_pages = int(('%s' % output).split(
                    'NumberOfPages: ')[-1].split('\n')[0])

                # Split label:
                if total_pages > parcels:
                    half_page = int(total_pages / 2)
                    subprocess.check_output([
                        'pdftk', fullname,
                        'cat', '1-%s' % half_page,
                        'output',
                        fullname_label,
                    ])
                else:  # Label complete is label!
                    shutil.copy(fullname, fullname_label)

                # Split parcel label (if present)
                if total_pages > parcels:
                    output = subprocess.check_output([
                        'pdftk', fullname,
                        'cat', '%s-%s' % (half_page + 1, total_pages),
                        'output',
                        fullname_parcel,
                    ])
                else:
                    _logger.error('No parcel label present')

    def check_size(self, text, size, dotted=False):
        """ Clean text for SOAP call
        """
        text = text or ''
        if dotted:
            if len(text) > (size - 3):
                return '%s...' % text[:size - 3]
        else:
            if len(text) > size:
                return text[:size]
        return text

    def clean_charset(self, text):
        """ Clean text for call
        """
        text = text.strip()
        if not text:
            return ''
        return self.sanitize_text(etree.tostring(etree.HTML(text)))

    def sanitize_text(self, text):
        """ Clean HTML tag from text
        :param text: HTML text to clean
        :return: clean text
        """
        tag_re = re.compile(r'<[^>]+>')
        return tag_re.sub('', text.strip())

    def dict2xml(self, data, level=0, cr=''):
        """ Turn a simple dict of key/value pairs into XML
        """
        result = ''
        level += 1
        spaces = ' ' * level
        for key, value in data.iteritems():
            if type(value) == dict:
                result += '%s<%s>%s%s%s</%s>%s' % (
                    spaces, key, cr,
                    self.dict2xml(value, level, cr),
                    spaces, key, cr)
            elif type(value) == list:
                for item in value:
                    result += '%s<%s>%s%s%s</%s>%s' % (
                        spaces, key, cr,
                        self.dict2xml(item, level, cr),
                        spaces, key, cr)
            else:
                result += '%s<%s>%s</%s>%s' % (spaces, key, value, key, cr)
        return result

    def get_items_parcel_block(self, cr, uid, ids, context=None):
        """ Return parcels block
        """
        order = self.browse(cr, uid, ids, context=context)[0]
        data = {'Item': []}
        for parcel in order.parcel_ids:
            data['Item'].append({
                'Weight': parcel.real_weight or 0.1,  # parcel.used_weight,
                'Dimensions': {
                    'Lenght': parcel.length,  # TODO typo but API write wrong
                    'Height': parcel.height,
                    'Width': parcel.width,
                }
            })
        return data

    def get_shipment_parameters_container(self, cr, uid, ids, context=None):
        """ Return dict for order shipment (for quotation)
        """
        order = self.browse(cr, uid, ids, context=context)[0]
        # todo manage partner data:
        wp_record = eval(order.wp_record)
        shipping = wp_record.get('shipping', {})

        city = self.clean_ascii_text(
            order.force_shipping_city or shipping.get('city', ''))
        data = {
            'DestinationInfo': {
                'ZipCode':  # 12
                    order.force_shipping_zip or shipping.get('postcode', ''),
                'City':  # * 50
                    city,
                'State':  # * 2
                    order.force_shipping_state or shipping.get('state', ''),
                'Country':  # 2
                    order.force_shipping_country or
                    shipping.get('country', ''),
                'idSubzone': '',  # * int
                },

            'ShipType': order.ship_type or '',
            'PackageType': order.package_type or '',
            # order.carrier_mode_id.account_ref
            'Service': '',  # Empty for now * string
            'Courier': '',  # Empty for now * string
            'CourierService': '',  # Empty for now * string
            # 'COD': '',  # * boolean
            # 'CODValue': '',  # * decimal
            # 'CODPaymentMethod': '',  # * token CASH CHECK
            # 'Insurance': '',  # * boolean
            # 'InsuranceValue': '',  # * decimal
            # 'SaturdayDelivery': '',  # * boolean
            # 'SignatureRequired': '',  # * boolean
            # 'MBESafeValue': '',  # * boolean
            # 'MBESafeValueValue': '',  # * decimal

            'Items': order.get_items_parcel_block(),
        }
        return data

    def get_request_container(
            self, cr, uid, ids,
            credentials=True, internal=True, customer=True,
            system=False, store=False, connection=False, context=None):
        """ Get Service connection to make calls, parameters are passed as
            boolean switch:
        """
        assert len(ids) == 1, 'Un\'ordine alla volta'

        # Generic call, check order before after supplier
        # self.carrier_connection_id
        # self.carrier_supplier_id.soap_connection_id

        _logger.warning('Used %s connection!' % connection.name)
        data = {}
        if credentials:
            data['Credentials'] = {
                'Username': connection.username,
                'Passphrase': connection.passphrase,
            }
        if internal:
            data['InternalReferenceID'] = connection.internal_reference
        if customer:
            data['CustomerID'] = connection.customer_id
        if system:
            if type(system) == bool:
                field_name = 'System'
            else:
                field_name = 'SystemType'
            data[field_name] = connection.system
        if store:
            data['StoreID'] = connection.store_id
        return data

    def get_recipient_container(self, cr, uid, ids, context=None):
        """ Return dict for Partner container
        """
        order = self.browse(cr, uid, ids, context=context)[0]
        wp_record = eval(order.wp_record)
        shipping = wp_record.get('shipping', {})
        billing = wp_record.get('billing', {})

        note = wp_record['customer_note'][:35]
        if shipping['address_2']:
            address2 = shipping['address_2']
        else:  # Update partner address with note so always was written
            # if note:
            #     partner.write({'street2': note})
            address2 = note

        name = '%s %s' % (shipping['first_name'], shipping['last_name'])
        return {
            'Name': self.clean_charset(name[:35]),
            'CompanyName': self.clean_charset(
                (shipping['company'] or name)[:35]),
            'Nickname': ''[:100],
            'Address':
                self.clean_charset(
                    order.force_shipping_address1 or
                    shipping['address_1'][:100]),
            'Address2':
                self.clean_charset(
                    order.force_shipping_address2 or
                    shipping['address_2'][:35]),
            'Address3': ''[:35],  # self.clean_charset(
            'Phone': billing['phone'][:50],
            'ZipCode':
                (order.force_shipping_zip or shipping['postcode'])[:12],
            'City':
                (order.force_shipping_city or shipping['city'])[:50],
            'State':
                (order.force_shipping_state or shipping['state'])[:2],
            'Country':
                (order.force_shipping_country or shipping['country'])[:2],
            'Email': billing['email'][:75],
            'SubzoneId': '',  # integer
            'SubzoneDesc': '',
        }

    def get_shipment_container(self, cr, uid, ids, context=None):
        """ Return dict for order shipment
        """
        order = self.browse(cr, uid, ids, context=context)[0]

        wp_record = eval(order.wp_record)
        # shipping = wp_record.get('shipping', {})
        # billing = wp_record.get('billing', {})
        note = self.clean_charset(wp_record['customer_note'][:35])

        data = {
            'ShipperType': order.shipper_type,
            'Description': self.clean_charset(order.check_size(
                order.carrier_description or order.name, 100, dotted=True)),
            'MethodPayment': order.carrier_pay_mode,
            'Service': order.carrier_mode_id.account_ref or '',
            'Courier': order.courier_supplier_id.account_ref or '',
            'CourierService': order.courier_mode_id.account_ref or '',
            'PackageType': order.package_type,
            'Referring': order.name,  # * 30
            'InternalNotes': note,  # TODO * string
            'Notes': note,
            'LabelFormat': 'NEW',  # * token (OLD, NEW)
            'Items': order.get_items_parcel_block(),

            # TODO Option not used for now:
            'Insurance': False,  # boolean
            'COD': False,  # boolean
            # 'CODValue': '',  # * decimal
            # 'InsuranceValue': '',  # * decimal
            # 'CourierAccount': '',  # * string
            # 'Value': '',  # * decimal
            # 'ShipmentCurrency': '',  # * string
            # 'SaturdayDelivery': '',  # * boolean
            # 'SignatureRequired': '',  # * boolean
            # 'ShipmentOrigin': '',  # * string
            # 'ShipmentSource': '',  # * int
            # 'MBESafeValue': '',  # * boolean
            # 'MBESafeValueValue': '',  # * decimal
            # 'MBESafeValueDescription': '',  # * string 100
        }

        # Products* ProductsType
        #    Product ProductType
        #        SKUCode string
        #        Description string
        #        Quantity decimal

        # ProformaInvoice* ProformaInvoiceType
        #        ProformaDetail ProformaDetailType
        #            Amount int
        #            Currency string 10
        #            Value decimal
        #            Unit string 5
        #            Description string 35
        return data

    def update_order_with_soap_reply(self, cr, uid, ids, data, context=None):
        """ Update order data with SOAP reply (error checked in different call)
        """
        # order = self.browse(cr, uid, ids, context=context)[0]
        error = ''
        try:
            master_tracking_id = data['MasterTrackingMBE']
        except:
            raise osv.except_osv(
                _('Errore Server MBE'),
                _('Risposta senza il tracking ID, non valida!'),
            )

        system_reference_id = data['SystemReferenceID']

        try:
            courier_track_id = data['CourierMasterTrk']
            if courier_track_id == master_tracking_id:
                courier_track_id = False
                # Download label
            else:
                # TODO if raise error no label!
                self.save_order_label(
                    cr, uid, ids, data, 'tracking', context=context)

        except:
            courier_track_id = False

        # Label if not Courier is not used:
        # order.save_order_label(reply, 'label')

        # InternalReferenceID 100
        # TrackingMBE* : {'TrackingMBE': ['RL28102279']

        self.write(cr, uid, ids, {
            # 'carrier_state': 'pending',  # todo enable when used portal!
            'master_tracking_id': master_tracking_id,
            'system_reference_id': system_reference_id,
            'carrier_track_id': courier_track_id or master_tracking_id,
        }, context=context)
        return error

    def check_reply_status(
            self, cr, uid, ids, reply, console_log=True,
            undo_error=False, context=None):
        """ Get Service connection to make calls:
            @return Error text if present
        """
        error_text = ''
        try:
            status = reply['Status']  # Status token (OK, ERROR)
        except:
            return 'Errore generico, nessuna risposta dal portale'

        if status == 'ERROR':
            # Error[{'id', 'Description'}]
            # error_text = '%s' % (reply['Errors'], )  # TODO better!
            error_text = reply['Errors']['Error']['Description']\
                .replace('\n', ' ')

            # -----------------------------------------------------------------
            # Undo procedure (delete request) if error:
            # -----------------------------------------------------------------
            if undo_error:  # Parameter for undo in case of error
                try:
                    master_tracking_mbe = reply['MasterTrackingMBE']
                    self.write({
                        'master_tracking_id': master_tracking_mbe,
                    })
                    error = self.delete_shipments_request(
                        cr, uid, ids, context=context)
                    if error:
                        _logger.error('%s' % (error, ))
                    else:
                        _logger.warning(
                            'Tracking MBE used for undo request!')
                except:
                    _logger.error('Tracking MBE not found, no undo request!')

        if console_log and error_text:
            _logger.error(error_text)
        return error_text

    # todo remove:
    def shipment_request(self, cr, uid, ids, context=None):
        """ 15. API Shipment Request: Insert new carrier request
        """
        return True

    def carrier_get_reservation(self, cr, uid, ids, context=None):
        """ Create delivery with this parameters
        """
        if context is None:
            context = {}
        ctx = context.copy()
        ctx['force_api_mode'] = 'create'
        return self.get_rate(cr, uid, ids, context=ctx)

    # -------------------------------------------------------------------------
    # Will be overridden:
    def carrier_remove_reservation(self, cr, uid, ids, context=None):
        """ Delete reservation
        """
        return True

    def get_rate(self, cr, uid, ids, context=None):
        """ Get rate with this prameters
        """
        return True
    # -------------------------------------------------------------------------

    # todo remove?
    def shipment_options_request(self, cr, uid, ids, context=None):
        """ 17. API ShippingOptionsRequest: Get better quotation
            get_rate!
        """
        assert len(ids) == 1, 'Un ordine alla volta'
        return self.get_rate(cr, uid, ids, context=context)

