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
from requests.auth import HTTPBasicAuth  # or HTTPDigestAuth, or OAuth1, etc.
import xml.etree.cElementTree as ElementTree
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


# -----------------------------------------------------------------------------
# Utility object for convert reply:
# -----------------------------------------------------------------------------
def get_in_type(text):
    """ Return in correct value
    """
    # Boolean:
    if text == 'true':
        return True
    if text == 'false':
        return False

        # Datetime

    # Date

    # Integer
    if not (text or '').startswith('0'):
        try:
            return int(text)
        except:
            pass

            # Float
        try:
            return float(text)
        except:
            pass
    return text


class XmlListConfig(list):
    def __init__(self, aList):
        for element in aList:
            if element:
                # treat like dict
                if len(element) == 1 or element[0].tag != element[1].tag:
                    self.append(XmlDictConfig(element))
                # treat like list
                elif element[0].tag == element[1].tag:
                    self.append(XmlListConfig(element))
            elif element.text:
                text = element.text.strip()
                if text:
                    self.append(text)


class XmlDictConfig(dict):
    """
    Example usage:
    >>> tree = ElementTree.parse('your_file.xml')
    >>> root = tree.getroot()
    >>> xmldict = XmlDictConfig(root)

    Or, if you want to use an XML string:
    >>> root = ElementTree.XML(xml_string)
    >>> xmldict = XmlDictConfig(root)

    And then use xmldict for what it is... a dict.
    """

    def __init__(self, parent_element):
        if parent_element.items():
            self.update(dict(parent_element.items()))
        for element in parent_element:
            if element:
                # treat like dict - we assume that if the first two tags
                # in a series are different, then they are all different.
                if len(element) == 1 or element[0].tag != element[1].tag:
                    aDict = XmlDictConfig(element)
                # treat like list - we assume that if the first two tags
                # in a series are the same, then the rest are the same.
                else:
                    # here, we put the list in dictionary; the key is the
                    # tag name the list elements all share in common, and
                    # the value is the list itself
                    aDict = {element[0].tag: XmlListConfig(element)}
                # if the tag has attributes, add those to the dict
                if element.items():
                    aDict.update(dict(element.items()))
                self.update({element.tag: aDict})
            # this assumes that if you've got an attribute in a tag,
            # you won't be having any text. This may or may not be a
            # good idea -- time will tell. It works for the way we are
            # currently doing XML configuration files...
            elif element.items():
                self.update({element.tag: dict(element.items())})
            # finally, if there are no child tags and no attributes, extract
            # the text
            else:
                self.update({element.tag: get_in_type(element.text)})


class CarrierConnectionMBE(orm.Model):
    """ Model name: Carrier Connection
    """
    _inherit = 'carrier.connection'


class WordpressSaleOrderRelationCarrier(orm.Model):
    """ Model name: Wordpress Sale order
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

        # Filter parameters:
        carrier_mode_search = order.carrier_mode_id.account_ref

        # Courier:
        courier_supplier_search = order.courier_supplier_id.account_ref
        courier_mode_search = order.courier_mode_id.account_ref

        supplier_pool = self.pool.get('carrier.supplier')
        service_pool = self.pool.get('carrier.supplier.mode')
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
        for record in quotation_list:
            connection, quotation = record
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

        # TODO no need to create 21 nov. 2020?!?:
        # Update order with better quotation:
        data = False
        pdb.set_trace()

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

    def get_envelope(self, request, data, cr=''):
        """ Extract xml from dict and put in envelope:
        """
        reply = self.dict2xml(data, level=4, cr=cr)
        result = '''<soapenv:Envelope xmlns:soapenv=
            "http://schemas.xmlsoap.org/soap/envelope/" 
            xmlns:ws="http://www.onlinembe.it/ws/">
            <soapenv:Header/>
            <soapenv:Body>
                <ws:%s>
                    <RequestContainer>%s</RequestContainer>
          </ws:%s>
         </soapenv:Body>
        </soapenv:Envelope>''' % (request, reply, request)
        return result.replace('\n', '').replace('\t', '    ')

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

        data = {
            'DestinationInfo': {
                'ZipCode': shipping.get('postcode', ''),  # 12
                'City': shipping.get('city', ''),  # * 50,
                'State': shipping.get('state', ''),  # * 2
                'Country': shipping.get('country', ''),  # 2
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

    # -------------------------------------------------------------------------
    # SOAP List of function:
    # -------------------------------------------------------------------------
    def shipment_options_request(self, cr, uid, ids, context=None):
        """ 17. API ShippingOptionsRequest: Get better quotation
        """
        assert len(ids) == 1, 'Un ordine alla volta'
        order = self.browse(cr, uid, ids, context=context)[0]

        # Carrier connection (B)
        # todo write correct test:
        carrier_connection = order.carrier_supplier_id.carrier_connection_id
        if not carrier_connection:
            return 'Ordine %s non ha il riferimento alla connessione!' % \
                   order.name
        # if order.state not in 'draft':
        #    return 'Ordine %s è a bozza quindi non pubblicato!' % order.name
        # if order.carrier_soap_id:
        #    return 'Order %s has SOAP ID %s cannot publish!' % (
        #            order.name, order.carrier_soap_id)

        # ---------------------------------------------------------------------
        # SOAP insert call:
        # ---------------------------------------------------------------------
        # A. Economy request:
        # TODO no more use parcel connection (removed from list):
        #    item.soap_connection_id for item in self.parcel_ids
        #    if item.soap_connection_id]

        # B. Standard request:
        error = ''
        reply_list = []

        # Generate data for request:
        header = {'Content-Type': 'text/xml'}

        data = self.get_request_container(
            cr, uid, ids,
            customer=False, system=True, connection=carrier_connection,
            context=context,
        )
        data['ShippingParameters'] = order.get_shipment_parameters_container()
        # data['ShippingParameters']['Service'] = 1 o 2
        payload = self.get_envelope('ShippingOptionsRequest', data)
        _logger.info('Call: %s' % data)
        reply = requests.post(
            carrier_connection.location,
            auth=HTTPBasicAuth(
                carrier_connection.username,
                carrier_connection.passphrase),
            headers=header,
            data=payload,
        )
        if not reply.ok:
            raise osv.except_osv(
                _('Errore Server MBE'),
                _('Risposta non corretta: %s' % reply),
                )
        _logger.warning('\n%s\n\n%s\n' % (data, reply))

        # Parse reply:
        reply_text = reply.text
        data_block = reply_text.split(
            '<RequestContainer>')[-1].split('</RequestContainer>')[0]

        data_block = (
                '<RequestContainer>%s</RequestContainer>' % data_block
        ).encode('ascii', 'ignore').decode('ascii')

        root = ElementTree.XML(data_block)
        result_data = XmlDictConfig(root)
        #try:
        #    record = result_data['ShippingOptions']['ShippingOption']
        #    price = record[0]['NetShipmentTotalPrice']  # NetShipmentPrice
        #except:
        #    raise osv.except_osv(
        #        _('Errore Server MBE'),
        #        _('Risposta errata: %s' % reply),
        #        )
        # error += order.check_reply_status(reply)
        reply_list.append((carrier_connection, result_data))

        # if not error:
        # Update SOAP data for real call
        self.update_with_quotation(cr, uid, ids, reply_list, context=context)
        return True   # error

    def sanitize_text(self, text):
        """ Clean HTML tag from text
        :param text: HTML text to clean
        :return: clean text
        """
        tag_re = re.compile(r'<[^>]+>')
        return tag_re.sub('', text.strip())

