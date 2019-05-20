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
import json
import woocommerce
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

class ResPartner(orm.Model):
    """ Model name: Res partner
    """

    _inherit = 'res.partner'
    
    _columns = {
        'wordpress':fields.boolean(
            'Wordpress', help='Created from wordpress order'),
        }

class SaleOrder(orm.Model):
    """ Model name: Sale Order
    """

    _inherit = 'sale.order'
    
    _columns = {
        'wp_id': fields.integer('Worpress ID of order'),
        'connector_id': fields.many2one('connector.server', 'Connector', 
            help='Connector Marketplace, is the origin web site'),
        }

class ConnectorServer(orm.Model):
    """ Model name: Worpdress Sale order
    """

    _inherit = 'connector.server'

    # TODO Schedule action!
    
    # -------------------------------------------------------------------------
    # Button event:
    # -------------------------------------------------------------------------
    def get_sale_order_now(self, cr, uid, ids, context=None):
        ''' Get sale order list
            '''
        if context is None:    
            context = {}

        # Pool used:
        order_pool = self.pool.get('sale.order')
        partner_pool = self.pool.get('res.partner')
        country_pool = self.pool.get('res.country')
        state_pool = self.pool.get('res.country.state')
        
        _logger.warning('Read order on wordpress:')

        # ---------------------------------------------------------------------
        #                        CREATE ORDERS OPERATION:
        # ---------------------------------------------------------------------
        connector_id = ids[0]
        server_proxy = self.browse(cr, uid, connector_id, context=context)

        # Read WP Order present:
        wcapi = self.get_wp_connector(
            cr, uid, connector_id, context=context)

        # ---------------------------------------------------------------------        
        # Read all orders:
        # ---------------------------------------------------------------------        
        theres_data = True
        parameter = {
            'per_page': 20,
            'page': 0,
            # TODO 'after': '2019-05-01T00:00:00' Add clause from search
            }
        wp_order = []
        while theres_data:
            parameter['page'] += 1
            res = wcapi.get(
                'orders', params=parameter).json()

            try:
                test_error = res['data']['status']
                raise osv.except_osv(
                    _('Order error:'), 
                    _('Error getting oredr list: %s' % (res, ) ),
                    )
            except:
                pass # no error
                
                
            if res:
                wp_order.extend(res)
            else:
                theres_data = False

        '''
        {
        "id": 727,
        "parent_id": 0,
        "number": "727",
        "order_key": "wc_order_58d2d042d1d",
        "created_via": "rest-api",
        "version": "3.0.0",
        "status": "processing",
        "currency": "USD",
        "date_created": "2017-03-22T16:28:02",
        "date_created_gmt": "2017-03-22T19:28:02",
        "date_modified": "2017-03-22T16:28:08",
        "date_modified_gmt": "2017-03-22T19:28:08",
        "discount_total": "0.00",
        "discount_tax": "0.00",
        "shipping_total": "10.00",
        "shipping_tax": "0.00",
        "cart_tax": "1.35",
        "total": "29.35",
        "total_tax": "1.35",
        "prices_include_tax": false,
        "customer_id": 0,
        "customer_ip_address": "",
        "customer_user_agent": "",
        "customer_note": "",
        
        "billing": {
          "first_name": "John",
          "last_name": "Doe",
          "company": "",
          "address_1": "969 Market",
          "address_2": "",
          "city": "San Francisco",
          "state": "CA",
          "postcode": "94103",
          "country": "US",
          "email": "john.doe@example.com",
          "phone": "(555) 555-5555"
        },

        "shipping": {
          "first_name": "John",
          "last_name": "Doe",
          "company": "",
          "address_1": "969 Market",
          "address_2": "",
          "city": "San Francisco",
          "state": "CA",
          "postcode": "94103",
          "country": "US"
        },

        "payment_method": "bacs",
        "payment_method_title": "Direct Bank Transfer",
        "transaction_id": "",
        "date_paid": "2017-03-22T16:28:08",
        "date_paid_gmt": "2017-03-22T19:28:08",
        "date_completed": null,
        "date_completed_gmt": null,
        "cart_hash": "",
        "meta_data": [
          {
            "id": 13106,
            "key": "_download_permissions_granted",
            "value": "yes"
          },
          {
            "id": 13109,
            "key": "_order_stock_reduced",
            "value": "yes"
          }
        ],
        "line_items": [
          {
            "id": 315,
            "name": "Woo Single #1",
            "product_id": 93,
            "variation_id": 0,
            "quantity": 2,
            "tax_class": "",
            "subtotal": "6.00",
            "subtotal_tax": "0.45",
            "total": "6.00",
            "total_tax": "0.45",
            "taxes": [
              {
                "id": 75,
                "total": "0.45",
                "subtotal": "0.45"
              }
            ],
            "meta_data": [],
            "sku": "",
            "price": 3
          },
          {
            "id": 316,
            "name": "Ship Your Idea &ndash; Color: Black, Size: M Test",
            "product_id": 22,
            "variation_id": 23,
            "quantity": 1,
            "tax_class": "",
            "subtotal": "12.00",
            "subtotal_tax": "0.90",
            "total": "12.00",
            "total_tax": "0.90",
            "taxes": [
              {
                "id": 75,
                "total": "0.9",
                "subtotal": "0.9"
              }
            ],
            "meta_data": [
              {
                "id": 2095,
                "key": "pa_color",
                "value": "black"
              },
              {
                "id": 2096,
                "key": "size",
                "value": "M Test"
              }
            ],
            "sku": "Bar3",
            "price": 12
          }
        ],
        "tax_lines": [
          {
            "id": 318,
            "rate_code": "US-CA-STATE TAX",
            "rate_id": 75,
            "label": "State Tax",
            "compound": false,
            "tax_total": "1.35",
            "shipping_tax_total": "0.00",
            "meta_data": []
          }
        ],
        "shipping_lines": [
          {
            "id": 317,
            "method_title": "Flat Rate",
            "method_id": "flat_rate",
            "total": "10.00",
            "total_tax": "0.00",
            "taxes": [],
            "meta_data": []
          }
        ],
        "fee_lines": [],
        "coupon_lines": [],
        "refunds": [],
        "_links": {
          "self": [
            {
              "href": "https://example.com/wp-json/wc/v3/orders/727"
            }
          ],
          "collection": [
            {
              "href": "https://example.com/wp-json/wc/v3/orders"
            }
          ]
        }},                    
        '''  
        # ---------------------------------------------------------------------
        # Insert order
        # ---------------------------------------------------------------------
        # Sorted so parent first:
        for record in sorted(wp_order, 
                key=lambda x: x['date_created']):
            wp_id = record['id']
            name = record['number']
            date_order = record['date_created']
            
            order_ids = order_pool.search(cr, uid, [
                ('connector_id', '=', connector_id),
                ('wp_id', '=', wp_id),
                ], context=context)
            if order_ids:
                odoo_id = order_ids[0]
                
                # TODO 
                #order_pool.write(cr, uid, order_ids, {
                #    'parent_id': parent_wp_db.get(
                #        parent_id, False),
                #    'name': name,
                #    'sequence': record['menu_order'], 
                #    }, context=context)                    
                #_logger.info('Update %s' % name)    
            else:
                import pdb; pdb.set_trace()
                # Read data:
                record_partner = record['billing']
                state_code = record_partner['country']
                country_code = record_partner['state']

                # -------------------------------------------------------------
                # State:
                # -------------------------------------------------------------
                state_ids = state_pool.search(cr, uid, [
                    ('code', '=', state_code),
                    ], context=context)
                if state_ids:
                    state_id = state_ids[0]    
                else:
                    # TODO create state?
                    state_id = False    

                # -------------------------------------------------------------
                # Country:
                # -------------------------------------------------------------
                country_ids = country_pool.search(cr, uid, [
                    ('code', '=', country_code),
                    ], context=context)
                if country_ids:
                    country_id = country_ids[0]    
                else:
                    # TODO create state?
                    country_id = False    
                
                # -------------------------------------------------------------
                # Partner creation:
                # -------------------------------------------------------------
                partner_ids = partner_pool.search(cr, uid, [
                    ('email', '=', record_partner['email']),
                    ], context=context)
                partner_data = {
                    'name': '%s %s %s' % (
                        record_partner['company'],
                        record_partner['first_name'],
                        record_partner['last_name'],                                                
                        ),
                    'street': record_partner['address_1'],
                    'street2': record_partner['address_2'],
                    'city': record_partner['city'],
                    'zip': record_partner['postcode'],
                    'email': record_partner['email'],
                    'phone': record_partner['phone'],
                    'city_id': city_id,
                    'country_id': country_id,  
                    
                    }    
                if partner_ids:
                    partner_id = partner_ids[0]
                    #`TODO update?
                else:                
                    partner_data['wordpress'] = True                    
                    partner_id = partner_pool.create(
                        cr, uid, partner_data, context=context)

                # -------------------------------------------------------------
                # Destination:                
                # -------------------------------------------------------------
                destination_partner_id = False
                            
                order_header = {
                    'connector_id': connector_id,
                    'wp_id': wp_id,
                    'client_order_ref': name,
                    'partner_id': partner_id,
                    'destination_partner_id': destination_partner_id,
                    'date_order': date_order,
                    }    

                # -------------------------------------------------------------
                # Update onchange partner data:
                # -------------------------------------------------------------
                onchange = order_pool.onchange_partner_id(
                    cr, uid, False, partner_id, context=context).get(
                        'value', {})
                order_header.update(onchange)    

                # -------------------------------------------------------------
                # Order creation:
                # -------------------------------------------------------------
                order_id = order_pool.create(
                    cr, uid, order_header, context=context)
                # TODO Workflow trigger:    
                _logger.info('Create %s' % name)    
                
                # -------------------------------------------------------------
                # Line creation:
                # -------------------------------------------------------------
                # line_items    
        return True
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
