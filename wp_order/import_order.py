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

    # Button event:
    def partner_wordpress_invoice_on(self, cr, uid, ids, context=None):
        """ Invoice on
        """
        return self.write(cr, uid, ids, {
            'wordpress_invoice': True,
            }, context=context)

    def partner_wordpress_invoice_off(self, cr, uid, ids, context=None):
        """ Invoice on
        """
        return self.write(cr, uid, ids, {
            'wordpress_invoice': False,
            }, context=context)

    _columns = {
        'wordpress': fields.boolean(
            'Wordpress', help='Created from wordpress order'),
        # TODO used?
        'wordpress_invoice': fields.boolean(
            'Wordpress', help='Need invoice, istead of fees'),
        }


class SaleOrder(orm.Model):
    """ Model name: Sale Order
    """

    _inherit = 'sale.order'

    def button_wordpress_detail(self, cr, uid, ids, context=None):
        """ View metadata
        """
        model_pool = self.pool.get('ir.model.data')
        view_id = model_pool.get_object_reference(
            cr, uid,
            'wp_order', 'view_sale_order_wordpress_metadata_form')[1]

        return {
            'type': 'ir.actions.act_window',
            'name': _('Wordpress metadata'),
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_id': ids[0],
            'res_model': 'sale.order',
            'view_id': view_id, # False
            'views': [(view_id, 'form'), (False, 'tree')],
            'domain': [],
            'context': context,
            'target': 'new',  # 'current',
            'nodestroy': False,
            }

    def dummy(self, cr, uid, ids, context=None):
        """ Do nothing (or save)
        """
        return True

    def button_payment_confirmed(self, cr, uid, ids, context=None):
        """ Confirm manual payment
        """
        order = self.browse(cr, uid, ids, context=context)[0]
        connector_id = order.connector_id.id
        wp_id = order.wp_id

        if not connector_id:
            raise osv.except_osv(
                _('Error connector'),
                _('Connector for web site not found on order'),
                )

        # if not wp_id:
        #    raise osv.except_osv(
        #        _('Error connector'),
        #        _('Wordpress order ID not found on ODOO order'),
        #        )

        # ---------------------------------------------------------------------
        # Update status on wordpress site:
        # ---------------------------------------------------------------------
        connector_pool = self.pool.get('connector.server')
        wcapi = connector_pool.get_wp_connector(
            cr, uid, connector_id, context=context)
        data = {
            'status': 'processing',  # completed
            }
        res = wcapi.put('orders/%s' % wp_id, data).json()

        # ---------------------------------------------------------------------
        # Confirmed sale order workflow:
        # ---------------------------------------------------------------------
        self.signal_workflow(cr, uid, ids, 'order_confirm')

        # ---------------------------------------------------------------------
        # Mark as confirmed:
        # ---------------------------------------------------------------------
        return self.write(cr, uid, ids, {
            'wp_payment_confirmed': True,
            }, context=context)

    def _get_corresponding_alert(
            self, cr, uid, ids, fields, args, context=None):
        """ Fields function for calculate
        """
        res = {}
        if len(ids) == 1:
            res[ids[0]] = 'ORDINE WORDPRESS NON FARE FATTURA MA CORRISPETTIVO!'
        return res

    _columns = {
        'wp_id': fields.integer('Worpress ID of order'),
        'connector_id': fields.many2one('connector.server', 'Connector',
            help='Connector Marketplace, is the origin web site'),
        'worpress_record': fields.text('Worpress record'),
        'wp_payment_confirmed': fields.boolean('Payment confirmed'),
        'wordpress_invoice': fields.boolean(
            'Wordpress', help='Need invoice, istead of fees'),
        'wordpress_alert': fields.function(
            _get_corresponding_alert, method=True,
            type='char', string='Alert', store=False),
        }


class ConnectorServer(orm.Model):
    """ Model name: Worpdress Sale order
    """

    _inherit = 'connector.server'

    # TODO Schedule action!

    # -------------------------------------------------------------------------
    # Utility:
    # -------------------------------------------------------------------------
    def get_detail_id_from_code(self, cr, uid, pool, code, context=None):
        """ Return state or country ID
        """
        item_ids = pool.search(cr, uid, [
            ('code', '=', code),
            ], context=context)
        if item_ids:
            return item_ids[0]
            _logger.info('Pool %s code exist: %s' % (pool, code))
        else:
            # TODO create?
            _logger.warning('Pool %s new %s (not for now)' % (pool, code))
            return False

    def get_product_id_wp_or_code(self, cr, uid, line, context=None):
        """ Get product ID, rules:
            Search wp_id for Wordpress ID
            Search default_code
            Search extra DB default_code
            Create if not present
        """
        product_pool = self.pool.get('product.product')

        # Parameters:
        mask = 'C%s'  # TODO create parameter
        name = line['name']
        wp_id = line['product_id']
        default_code = line['sku'] # Mandatory!
        price = line['price'] # TODO Without tax?

        # 1. Search WP ID:
        if wp_id:
            # Search with Worpdress IP:
            product_ids = product_pool.search(cr, uid, [
                ('wp_id', '=', wp_id),
                ], context=context)
            if product_ids:
                return product_ids[0]

        # 2. Search with default_code
        if default_code:
            _logger.warning('Lost WP id for product %s' % default_code)
            product_ids = product_pool.search(cr, uid, [
                ('default_code', '=', default_code),
                ], context=context)
            if product_ids:
                return product_ids[0]

            # 3. Search with mask:
            default_code = mask % default_code
            product_ids = product_pool.search(cr, uid, [
                ('default_code', '=', default_code),
                ], context=context)
            if product_ids:
                return product_ids[0]

            # 4. Create fast product (or import?):
            _logger.warning('Create new product %s' % default_code)
            return product_pool.create(cr, uid, {
                'name': name,
                'default_code': default_code, # Create with masked code!
                'lst_price': price,
                }, context=context)

        return False  # If no code!

    # -------------------------------------------------------------------------
    # Button event:
    # -------------------------------------------------------------------------
    def get_sale_order_now(self, cr, uid, ids, context=None):
        """ Get sale order list
            """
        if context is None:
            context = {}

        # Pool used:
        company_pool = self.pool.get('res.company')
        order_pool = self.pool.get('sale.order')
        line_pool = self.pool.get('sale.order.line')
        partner_pool = self.pool.get('res.partner')
        state_pool = self.pool.get('res.country.state')
        country_pool = self.pool.get('res.country')
        web_product_pool = self.pool.get('product.product.web.server')

        _logger.warning('Read order on wordpress:')

        # ---------------------------------------------------------------------
        # Company reference:
        # ---------------------------------------------------------------------
        company_id = company_pool.search(cr, uid, [], context=context)[0]
        company = company_pool.browse(cr, uid, company_id, context=context)

        # ---------------------------------------------------------------------
        #                        CREATE ORDERS OPERATION:
        # ---------------------------------------------------------------------
        connector_id = ids[0]

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
                    _('Error getting order list: %s' % (res, )),
                    )
            except:
                pass  # no error

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
        force_context = context.copy()  # Used for update manual stock mngmnt

        # Sorted so parent first:
        new_order_ids = []
        _logger.warning('Order found %s' % (len(wp_order), ))
        import pdb;
        pdb.set_trace()
        for record in sorted(
                wp_order, key=lambda x: x['date_created']):

            wp_id = record['id']
            name = record['number']
            date_order = record['date_created'][:10]
            payment_method = record['payment_method']
            status = record['status']
            # XXX Status value:
            # pending In attesa di pagamento
            # on-hold Sospeso
            # processing In lavorazione
            # processing In lavorazione,
            # completed Completo
            # failed Fallito
            # cancelled Cancellato
            # refunded Rimborsato

            # TODO Manage:
            # -----------------------------------------------------------------
            # Shipping add extra line with cost
            # -----------------------------------------------------------------
            # shipping_total
            # shipping_tax

            # -----------------------------------------------------------------
            # Payment method to manage suspended order
            # -----------------------------------------------------------------
            if payment_method in ('bacs', ):  # TODO add other pending payment
                wp_payment_confirmed = False
                new_status = 'pending'
                wf_confirm = False
            else:
                wp_payment_confirmed = True
                new_status = 'suspended'
                wf_confirm = True

            # -----------------------------------------------------------------
            # Discount add extra line with discount value
            # -----------------------------------------------------------------
            # discount_total
            # discount_tax

            # Only on-hold status will be imported again:
            if status not in ('on-hold', ):  # TODO
                _logger.warning('[%s] Status: %s so jumped' % (
                    name, status))
                continue

            # -----------------------------------------------------------------
            #                          ORDER HEADER:
            # -----------------------------------------------------------------
            order_ids = order_pool.search(cr, uid, [
                ('connector_id', '=', connector_id),
                ('wp_id', '=', wp_id),
                ], context=context)

            order_header = {
                'connector_id': connector_id,
                'wp_id': wp_id,
                'client_order_ref': name,
                'date_order': date_order,
                'worpress_record': record,
                'wp_payment_confirmed': wp_payment_confirmed
                }

            if order_ids:
                order_id = order_ids[0]
                # XXX No update of header
            else:
                # Read data:
                record_partner = record['billing']
                record_destination = record['shipping']

                email = record_partner['email']
                wordpress_invoice = False  # TODO check if need invoice!!!!!!

                # Calculated data:
                state_id = self.get_detail_id_from_code(
                    cr, uid, state_pool,
                    record_partner['state'], context=context)
                country_id = self.get_detail_id_from_code(
                    cr, uid, country_pool,
                    record_partner['country'], context=context)

                # -------------------------------------------------------------
                # Partner creation:
                # -------------------------------------------------------------
                partner_ids = partner_pool.search(cr, uid, [
                    ('email', '=', email),
                    ], context=context)

                partner_data = {
                    'is_company': True,
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
                    'state_id': state_id,
                    'country_id': country_id,

                    # TODO evaluate fiscal position:
                    'property_account_position':
                        company.partner_id.property_account_position.id,
                    'wordpress_invoice': wordpress_invoice,
                    }
                if partner_ids:
                    partner_id = partner_ids[0]
                    _logger.warning('Partner exist: %s' % email)
                    # TODO update?
                else:
                    partner_data['wordpress'] = True
                    partner_id = partner_pool.create(
                        cr, uid, partner_data, context=context)
                    _logger.warning('Partner new: %s' % email)

                # Update order if need invoice or account fees
                partner = partner_pool.browse(
                    cr, uid, partner_id, context=context)
                order_header['wordpress_invoice'] = partner.wordpress_invoice

                # -------------------------------------------------------------
                # TODO Destination:
                # -------------------------------------------------------------
                destination_partner_id = False

                # Create destination as partner if not present
                if not any(record_destination.values()):
                    # Use partner reference as destination:
                    record_destination = record_partner
                    _logger.warning(
                        'No partner shipping, using partner address')

                # Extract data:
                destination_name = '%s %s %s' % (
                    record_destination['company'],
                    record_destination['first_name'],
                    record_destination['last_name'],
                    )

                destination_street = record_destination['address_1']
                destination_street2 = record_destination['address_2']
                destination_city = record_destination['city']
                destination_postcode = record_destination['postcode']

                # Calculated data:
                state_id = self.get_detail_id_from_code(
                    cr, uid, state_pool,
                    record_destination['state'], context=context)
                country_id = self.get_detail_id_from_code(
                    cr, uid, country_pool,
                    record_destination['country'], context=context)

                address_ids = partner_pool.search(cr, uid, [
                    ('parent_id', '=', partner_id),
                    ('name', '=', destination_name),
                    ('street', '=', destination_street),
                    ('city', '=', destination_city),
                    ('zip', '=', destination_postcode),
                    ], context=context)
                if address_ids:
                    destination_partner_id = address_ids[0]
                else:
                    _logger.warning('New address created!')
                    destination_partner_id = partner_pool.create(
                        cr, uid, {
                            'wordpress': True,
                            'is_address': True,
                            'parent_id': partner_id,
                            'name': destination_name,
                            'street': destination_street,
                            'street2': destination_street2,
                            'city': destination_city,
                            'zip': destination_postcode,
                            }, context=context)

                order_header.update({
                    'partner_id': partner_id,
                    })

                # -------------------------------------------------------------
                # Update onchange partner data:
                # -------------------------------------------------------------
                order_header.update(
                    order_pool.onchange_partner_id(
                        cr, uid, False, partner_id, context=context).get(
                            'value', {}))

                order_header.update({ # before onchange will be deleted!)
                    'destination_partner_id': destination_partner_id,
                    })

                # -------------------------------------------------------------
                # Order creation:
                # -------------------------------------------------------------
                order_id = order_pool.create(
                    cr, uid, order_header, context=context)
                # TODO Workflow trigger:
                _logger.info('Create %s' % name)
                _logger.warning('Order new %s' % name)

            # -----------------------------------------------------------------
            #                          ORDER DETAIL:
            # -----------------------------------------------------------------
            order_proxy = order_pool.browse(cr, uid, order_id, context=context)
            wp_line = record['line_items']
            if order_proxy.order_line:
                if len(order_proxy.order_line) != len(wp_line):
                    # TODO continue not raise!
                    _logger.error('Line are yet loaded but different!')
                    # raise osv.except_osv(
                    #    _('Error order line'),
                    #    _('Error importing line, yet present but different!'),
                    #    )
                else:
                    _logger.warning('Line are yet load!')
                continue  # yet load the lines

            # Create the lines:
            partner = order_proxy.partner_id
            for line in wp_line:
                name = line['name']
                quantity = line['quantity']
                total = line['total']
                total_tax = line['total_tax']
                price = line['price']

                product_id = self.get_product_id_wp_or_code(
                    cr, uid, line, context=context)

                # -------------------------------------------------------------
                # Manual stock management:
                # -------------------------------------------------------------
                if order_proxy.name == '56154':
                    import pdb: pdb.set_trace()

                web_product_ids = web_product_pool.search(cr, uid, [
                    ('connector_id', '=', connector_id),
                    ('product_id', '=', product_id),
                    ('force_this_stock', '>', 0),  # manage manual q.
                ], context=context)
                if web_product_ids:
                    import pdb; pdb.set_trace()
                    web_product = web_product_pool.browse(web_product_ids)[0]
                    new_qty = web_product.force_this_stock - quantity
                    if new_qty < 0:
                        new_qty = 0
                    force_context['forced_manual_stock_comment'] = \
                        'Scalato ordine: %s' % order_proxy.name
                    web_product_pool.write(cr, uid, {
                        'force_this_stock': new_qty,
                    }, context=context)

                line_data = {
                    'order_id': order_id,
                    'name': name,
                    'product_uom_qty': quantity,
                    'product_id': product_id,
                    }

                # Update with onchange product event:
                onchange = line_pool.product_id_change_with_wh(
                        cr, uid, False,
                        order_proxy.pricelist_id.id,
                        product_id,
                        quantity,
                        False,  # UOM;
                        quantity,
                        False,  # UOS;
                        name,
                        partner.id,
                        partner.lang,
                        True,  # Update tax
                        order_proxy.date_order,
                        False,  # Packaging
                        partner.property_account_position.id,
                        False,  # Flag
                        False,  # warehouse_id
                        context=context).get('value', {})

                # Format correct fhe Tax relation:
                if 'tax_id' in onchange:
                    onchange['tax_id'] = [(6, 0, onchange['tax_id'])]
                line_data.update(onchange)
                line_pool.create(cr, uid, line_data, context=context)

            # -----------------------------------------------------------------
            # Change status:
            # -----------------------------------------------------------------
            # 1. Wordpress status:
            data = {
                'status': new_status,  # 'processing' #completed
                }
            res = wcapi.put('orders/%s' % wp_id, data).json()

            # 2. Order workflow status:
            if wf_confirm:
                order_pool.signal_workflow(
                    cr, uid, [order_id], 'order_confirm')

            # Update order list:
            new_order_ids.append(order_id)

        return {
            'type': 'ir.actions.act_window',
            'name': _('New order'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            # 'res_id': 1,
            'res_model': 'sale.order',
            'view_id': False,
            'views': [(False, 'tree'), (False, 'form')],
            'domain': [('id', 'in', new_order_ids)],
            'context': context,
            'target': 'current',
            'nodestroy': False,
            }
