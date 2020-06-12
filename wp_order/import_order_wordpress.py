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

import sys
import logging
from openerp.osv import fields, osv, expression, orm
from datetime import datetime, timedelta
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)


class WordpressSaleOrder(orm.Model):
    """ Model name: Wordpress Sale Order
    """

    _name = 'wordpress.sale.order'
    _description = 'Wordpress order'

    _columns = {
        'name': fields.char('Order number'),
        'key': fields.char('Order key'),
        'wp_id': fields.integer('Worpress ID of order'),
        'total': fields.float('Total', digits=(10, 2)),
        'shipping_total': fields.float('Shipping total', digits=(10, 2)),
        'currency': fields.char('Currency'),
        'date_order': fields.date('Date order'),

        'wp_date_created': fields.datetime('Date created'),
        'wp_date_modified': fields.datetime('Date modify'),
        'wp_date_paid': fields.datetime('Date paid'),
        'wp_date_completed': fields.datetime('Date completed'),

        'partner_name': fields.char('Partner', size=40),
        'partner_email': fields.char('Partner email', size=40),
        'partner_phone': fields.char('Partner phone', size=30),

        'payment': fields.char('Payment', size=30),
        'billing': fields.text('Billing'),
        'shipping': fields.text('Shipping'),

        'connector_id': fields.many2one(
            'connector.server', 'Connector',
            help='Connector Marketplace, is the origin web site'),

        'note': fields.text('Note'),

        'wp_record': fields.text('Worpress record'),
        'state': fields.selection([
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('on-hold', 'On hold'),
            ('completed', 'Completed'),
            ('refunded', 'Refunded'),
            ('failed', 'Failed'),
            ('trash', 'Trash'),
            ('cancelled', 'Cancelled'),
            ], 'State'),
        }

    _defaults = {
        'state': lambda *x: 'pending',
    }


class WordpressSaleOrderLine(orm.Model):
    """ Model name: Wordpress Sale Order Line
    """

    _name = 'wordpress.sale.order.line'
    _description = 'Wordpress order line'

    _columns = {
        'order_id': fields.many2one(
            'wordpress.sale.order', 'Order', ondelete='cascade'),
        'name': fields.char('Name'),
        'wp_id': fields.integer('Line ID'),
        'sku': fields.char('SKU'),
        'product_id': fields.many2one('product.product', 'Product'),
        'quantity': fields.float('Q.', digits=(10, 2)),
        'price': fields.float('Price', digits=(10, 2)),
        'total': fields.float('Total', digits=(10, 2)),
    }


class WordpressSaleOrderRelation(orm.Model):
    """ Model name: Wordpress Sale Order relation fields
    """

    _inherit = 'wordpress.sale.order'

    _columns = {
        'line_ids': fields.one2many(
            'wordpress.sale.order.line', 'order_id', 'Line'),
        }


class ConnectorServer(orm.Model):
    """ Model name: Worpdress Sale order
    """

    _inherit = 'connector.server'

    def status_wordpress_order_report(self, cr, uid, ids, context=None):
        """ Status order excel report
        """
        excel_pool = self.pool.get('excel.writer')
        line_pool = self.pool.get('wordpress.sale.order.line')

        # ---------------------------------------------------------------------
        # Collect data:
        # ---------------------------------------------------------------------
        line_ids = line_pool.search(cr, uid, [
            ('order_id.connector_id', '=', ids[0]),
        ], context=context)
        report_data = {
            'all': [],
        }
        for line in line_pool.browse(cr, uid, line_ids, context=context):
            report_data['all'].append(line)

        # ---------------------------------------------------------------------
        # Completed order:
        # ---------------------------------------------------------------------
        ws_name = 'Ordini completi'
        excel_pool.create_worksheet(ws_name)
        row = 0

        # Load formats:
        f_title = excel_pool.get_format('title')
        f_header = excel_pool.get_format('header')
        f_text = excel_pool.get_format('text')
        f_number = excel_pool.get_format('number')

        header = [
            'SKU', 'Prodotto',
            'Q.', 'Prezzo', 'Subtotale',

            'Data', 'Ordine', 'Cliente', 'Pagamento', 'Stato',
            'Valuta', 'Trasporto', 'Totale', 'Netto',
            ]
        width = [
            10, 30,
            10, 10, 12,
            10, 8, 30, 15, 18,
            3, 10, 10, 10,
        ]
        excel_pool.column_width(ws_name, width)

        # 1 Title
        excel_pool.write_xls_line(
            ws_name, row, [
                'Totale ordini arrivati esplosi per articolo'],
            default_format=f_title)
        row += 1

        # 2 Header
        excel_pool.write_xls_line(
            ws_name, row, header, default_format=f_header)
        row += 1

        for line in sorted(report_data['all'],
                           key= lambda x: (x.order_id.name, x.wp_id)):
            order = line.order_id
            shipping = order.shipping_total
            total = order.total
            net = total - shipping
            data = [
                line.sku,
                line.name,

                (line.quantity, f_number),
                (line.price, f_number),
                (line.total, f_number),

                order.date_order,
                order.name,
                order.partner_name or '',
                order.payment or '',
                order.state,

                order.currency,
                (shipping, f_number),
                (total, f_number),
                (net, f_number),  # TODO check VAT!
                ]

            excel_pool.write_xls_line(
                ws_name, row, data, default_format=f_text)
            row += 1
        return excel_pool.return_attachment(cr, uid, 'wordpress_order')

    # Override function to get sold status
    def sold_product_on_website(self, cr, uid, ids, context=None):
        """ Return sold product for default_code
            ids = connector used
        """
        res = {}

        line_pool = self.pool.get('wordpress.sale.order.line')
        line_ids = line_pool.search(cr, uid, [
            ('order_id.connector_id', 'in', ids),
            ('order_id.state', 'in', (
                'pending', 'processing', 'on-hold', 'completed',
                # 'refunded', 'failed', 'trash',  'cancelled',
            )),
        ], context=context)
        for line in line_pool.browse(cr, uid, line_ids, context=context):
            sku = line.sku
            if sku in res:
                res[sku] += line.quantity
            else:
                res[sku] = line.quantity
        return res

    # -------------------------------------------------------------------------
    # Button event:
    # -------------------------------------------------------------------------
    def wp_clean_code(self, code):
        """ Clean code
        """
        return (code or '').replace('&nbsp;', ' ')

    def get_sale_order_now(self, cr, uid, ids, context=None):
        """ Get sale order list
            (context parameter 'from_yesterday' for check from yesterday)
        """
        # Utility:
        def get_clean_date(record_field):
            """ Clean date
            """
            try:
                return record_field.replace('T', ' ')  # [:16]
            except:
                return ''

        if context is None:
            context = {}
        from_yesterday = context.get('from_yesterday')

        # Pool used:
        order_pool = self.pool.get('wordpress.sale.order')
        line_pool = self.pool.get('wordpress.sale.order.line')
        product_pool = self.pool.get('product.product')

        _logger.warning('Read order on wordpress [from_yesterday = %s]' %
                        from_yesterday)

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
        if from_yesterday:
            parameter['after'] = (
                datetime.now() - timedelta(days=1)).strftime(
                    '%Y-%m-%dT00:00:00')

        wp_order = []
        while theres_data:
            parameter['page'] += 1
            reply = wcapi.get(
                'orders', params=parameter)
            if not reply.ok:
                _logger.error('Error reading order')
                continue

            json_reply = reply.json()
            if json_reply:
                wp_order.extend(json_reply)
            else:
                theres_data = False

        # ---------------------------------------------------------------------
        # Insert order
        # ---------------------------------------------------------------------
        # Sorted so parent first:
        new_order_ids = []
        _logger.warning('Order found %s' % (len(wp_order), ))
        for record in wp_order:
            try:
                wp_id = record['id']
                # TODO Date will show not correct (+2 hours)
                wp_date_created = get_clean_date(record['date_created'])
                date_order = wp_date_created[:10]
                wp_date_modified = get_clean_date(record['date_modified'])
                wp_date_paid = get_clean_date(record['date_paid'])
                wp_date_completed = get_clean_date(record['date_completed'])

                # -------------------------------------------------------------
                #                          ORDER HEADER:
                # -------------------------------------------------------------
                order_ids = order_pool.search(cr, uid, [
                    ('connector_id', '=', connector_id),
                    ('wp_id', '=', wp_id),
                    ], context=context)
                number = record['number']
                order_header = {  # Fields used also for update:
                    'connector_id': connector_id,
                    'wp_id': wp_id,
                    'name': number,
                    'currency': record['currency'],
                    'key': record['order_key'],

                    # Date (used '' for slice operation, False for update)
                    'date_order': date_order or False,
                    'wp_date_created': wp_date_created or False,
                    'wp_date_modified': wp_date_modified or False,
                    'wp_date_paid': wp_date_paid or False,
                    'wp_date_completed': wp_date_completed or False,

                    'wp_record': record,
                    'state': record['status'],
                    'note': record['customer_note'],
                    'payment': record['payment_method_title'],
                    'total': record['total'],
                }
                if order_ids:  # XXX No update of header
                    order_id = order_ids[0]
                    order_pool.write(
                        cr, uid, order_ids, order_header, context=context)
                    _logger.info('Yet found (update only line) %s' % number)
                else:  # Read data:
                    # Address:
                    billing = record['billing']
                    shipping = record['shipping']
                    partner_name = '%s %s - %s' % (
                        billing['first_name'],
                        billing['last_name'],
                        billing['company'] or '/',
                    )

                    partner_email = billing['email']
                    partner_phone = billing['phone']

                    partner_billing = '%s %s, %s-%s [%s Naz. %s]' % (
                        billing['address_1'],
                        billing['address_2'],
                        billing['postcode'],
                        billing['city'],
                        billing['state'],
                        billing['country'],
                    )

                    partner_shipping = '%s %s %s >> %s %s, %s-%s [%s]' % (
                        shipping['first_name'],
                        shipping['last_name'],
                        shipping['company'] or '/',

                        shipping['address_1'],
                        shipping['address_2'],
                        shipping['postcode'],
                        shipping['city'],
                        shipping['country'],
                    )

                    order_header.update({
                        'partner_name': partner_name,
                        'partner_email': partner_email,
                        'partner_phone': partner_phone,
                        'billing': partner_billing,
                        'shipping': partner_shipping,
                        'shipping_total': record['shipping_total'],
                    })

                    # ---------------------------------------------------------
                    # Order creation:
                    # ---------------------------------------------------------
                    order_id = order_pool.create(
                        cr, uid, order_header, context=context)
                    _logger.info('Create %s' % number)
                new_order_ids.append(order_id)

                # -------------------------------------------------------------
                # Order line (delete and update:
                # -------------------------------------------------------------
                # Delete:
                order_pool.write(
                    cr, uid, [order_id], {
                        'line_ids': [(6, 6, [])],
                    }, context=context)

                # Update
                for line in record['line_items']:
                    name = line['name']
                    sku = self.wp_clean_code(line['sku'])
                    product_id = False
                    if sku:
                        product_ids = product_pool.search(cr, uid, [
                            ('default_code', '=', sku),
                        ], context=context)
                        if product_ids:
                            product_id = product_ids[0]

                    order_line = {
                        'order_id': order_id,
                        'wp_id': line['id'],
                        'name': name,
                        'sku': sku,
                        'quantity': line['quantity'],
                        'price': line['price'],
                        'total': line['total'],
                        'product_id': product_id,
                        }
                    line_pool.create(cr, uid, order_line, context=context)

            except:
                _logger.error('Error creating order!\n%s' % (sys.exc_info(), ))
                continue

        return {
            'type': 'ir.actions.act_window',
            'name': _('New order'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            # 'res_id': 1,
            'res_model': 'wordpress.sale.order',
            'view_id': False,
            'views': [(False, 'tree'), (False, 'form')],
            'domain': [('id', 'in', new_order_ids)],
            'context': context,
            'target': 'current',
            'nodestroy': False,
            }
