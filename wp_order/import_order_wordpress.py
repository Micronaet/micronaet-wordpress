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
import pdb
import time

from openerp.osv import fields, osv, expression, orm
from datetime import datetime, timedelta
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)


class WordpressSaleOrder(orm.Model):
    """ Model name: Wordpress Sale Order
    """

    _name = 'wordpress.sale.order'
    _description = 'Wordpress order'

    def generate_sale_order(self, cr, uid, ids, context=None):
        """ Generate sale order if there's some product of this database
        """
        order_pool = self.pool.get('sale.order')
        line_pool = self.pool.get('sale.order.line')

        wp_order_id = ids[0]
        wp_order = self.browse(cr, uid, wp_order_id, context=context)
        order_line = []
        connector = wp_order.connector_id
        for line in wp_order.line_ids:
            if line.product_id:
                order_line.append(line)

        # Header:
        client_order_ref = 'WP.%s' % wp_order.name
        partner_id = connector.wp_auto_partner_id.id

        # Check if yet present (for sure)
        order_ids = order_pool.search(cr, uid, [
            ('client_order_ref', '=', client_order_ref),
            ('partner_id', '=', partner_id),
        ], context=context)
        if order_ids:
            _logger.error(
                'Order yet present, no generation: %s' % client_order_ref)
            return self.write(cr, uid, ids, {
                'need_sale_order': False,
            }, context=context)

        if not order_line:
            _logger.error(
                'No order line for this DB, order: %s' % client_order_ref)
            return self.write(cr, uid, ids, {
                'need_sale_order': False,
            }, context=context)

        # Generate order
        try:
            header_data = order_pool.onchange_partner_id(
                cr, uid, [], partner_id, context=context).get('value', {})
        except:
            _logger.error('Error generating onchange partner')
            return self.write(cr, uid, ids, {
                'need_sale_order': False,
            }, context=context)

        date_order = wp_order.date_order
        header_data.update({
            'wordpress_order_id': wp_order_id,
            'partner_id': partner_id,
            'date_order': date_order,
            'date_deadline': date_order,
            'client_order_ref': client_order_ref,
            'destination_partner_id': partner_id,
        })
        order_id = order_pool.create(
            cr, uid, header_data, context=context)
        order = order_pool.browse(cr, uid, order_id, context=context)

        # Update wordpress order:
        self.write(cr, uid, [wp_order_id], {
            'sale_order_id': order_id,
            'need_sale_order': False,
        }, context=context)

        # Create order line:
        sequence = 0
        for line in order_line:
            product = line.product_id
            sequence += 1
            product_uom_qty = line.quantity

            line_data = line_pool.product_id_change_with_wh(
                cr, uid, False,
                order.pricelist_id.id,
                product.id,
                product_uom_qty,
                False,
                product_uom_qty,
                False,
                product.name,
                partner_id,
                False,
                True,
                date_order,
                False,
                order.fiscal_position.id,
                False,
                order.warehouse_id.id,
                context=context,
                ).get('value', {})

            # TODO update discount?
            line_data.update({
                'order_id': order_id,
                'product_id': product.id,
                'name': line.name,
                'product_uom': product.uom_id.id,
                'product_uom_qty': product_uom_qty,
                'product_uos_qty': product_uom_qty,
                'price_unit': product.lst_price,
                # wp_id
            })
            line_pool.create(cr, uid, line_data, context=context)

        # todo Confirm order created:

        # Generated or not no more generation
        return self.write(cr, uid, ids, {
            'need_sale_order': False,
        }, context=context)

    def raise_message_new_order(self, cr, uid, ids, context=None):
        """ Raise message for new order
        """
        order_ids = self.search(cr, uid, [
            ('alert', '=', False),
        ], context=context)
        if not order_ids:
            return False
        for order_id in sorted(order_ids, reverse=True):
            loop = True
            max_loop = 20
            while loop:
                try:
                    self.new_wordpress_order_message(
                        cr, uid, [order_id], context=context)
                    time.sleep(3)
                    loop = False
                except Exception:
                    _logger.warning(
                        'Warning cannot raise telegram order: %s' % order_id)
                    max_loop -= 1
                    time.sleep(10)
                    if max_loop <= 0:
                        _logger.error(
                            'Error cannot raise telegram order 20 times: '
                            '%s' % order_id)
                        loop = False
        return True

    def get_marketplace(self, email):
        """ Get market place from email
        """
        if (email or '').endswith('@marketplace.amazon.it'):
            return 'Amazon'
        else:
            return 'Wordpress'

    def new_wordpress_order_message(self, cr, uid, ids, context=None):
        """ Telegram message when new order
        """
        order_id = ids[0]
        try:
            order = self.browse(cr, uid, order_id, context=context)
            server_pool = self.pool.get('connector.server')
            marketplace = self.get_marketplace(order.partner_email)
            if marketplace == 'Amazon':
                shipping = 'Incluso'
            else:  # Wordpress
                shipping = order.shipping_total or 'Non presente'
            detail = ''
            for line in order.line_ids:
                detail += ' >> %s x *%s* %s\n' % (
                    line.quantity, line.sku, line.name)
            message = 'Marketplace: *%s* Totale: *%s* \nOrdine: %s del %s\n' \
                      'Consegna: %s\n' \
                      'Trasporto esposto: %s\nDettagli:\n%s' % (
                            marketplace,
                            order.total,
                            order.name,
                            order.date_order,
                            order.shipping.split(',')[-1],
                            shipping,
                            detail,
                        )
            server_pool.server_send_telegram_message(
                cr, uid, [order.connector_id.id], message, context=context)
            return self.write(cr, uid, [order_id], {
                'alert': True,
            }, context=context)
        except:
            _logger.error('Error send message, insert only order!')
            return False

    _columns = {
        'alert': fields.boolean('Alert inviato'),
        'name': fields.char('Order number'),
        'key': fields.char('Order key'),
        'wp_id': fields.integer('Worpress ID of order'),
        'total': fields.float('Total', digits=(10, 2)),
        'total_tax': fields.float('Totale tasse', digits=(10, 2)),
        'shipping_total': fields.float('Shipping total', digits=(10, 2)),
        'real_shipping_total': fields.float(
            'Spedizione effettiva', digits=(10, 2)),
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

        # Auto order:
        'need_sale_order': fields.boolean(
            'Richiesto generazione',
            help='Richiesta la generazione di ordine di vendita '
                 'appena importato'),
        'sale_order_id': fields.many2one(
            'sale.order', 'Ordine ufficiale',
            help='Ordine ufficiale se presente almeno un articolo di questo '
                 'database'),

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
            context: send_group > name of group if file will be sent
        """
        if context is None:
            context = {}
        send_group = context.get('send_group')

        excel_pool = self.pool.get('excel.writer')
        line_pool = self.pool.get('wordpress.sale.order.line')
        order_pool = self.pool.get('wordpress.sale.order')
        web_product_pool = self.pool.get('product.product.web.server')
        connector_id = ids[0]

        # Utility:
        def get_extra_cost(mode, period, total):
            """ Extract extra cost
            """
            if mode == 'micronaet':
                if period >= '2021-03':
                    return total * 0.05
            return 0.0

        def get_standard_data_line(excel_pool, ws_name, row, line):
            """ Return list of fields for this line
            """
            order = line.order_id
            shipping = order.shipping_total
            total = order.total
            net = total - shipping
            state = order.state

            # Color setup:
            write_comment = False
            if state in ('trash', 'failed', 'cancelled'):
                color = excel_format['red']
                net = 0
                write_comment = True
            elif state in ('refunded', ):
                color = excel_format['orange']
                net = 0
                write_comment = True
            elif state in ('pending', 'on-hold'):
                color = excel_format['yellow']
                net = 0
                write_comment = True
            elif state in ('processing', ):
                color = excel_format['blue']
            elif state in ('completed', ):
                color = excel_format['green']
            else:
                color = excel_format['white']

            data = [
                line.sku,
                line.name,

                (line.quantity, color['number']),
                (line.price, color['number']),
                (line.total, color['number']),

                order.date_order,
                order.wp_date_paid or '',
                order.wp_date_completed or '',
                order.name,
                order.partner_name or '',
                order.payment or '',
                state,

                order.currency,
                (shipping, color['number']),
                (total, color['number']),
                (net, color['number']),  # TODO check VAT!
                ]
            # Write line:
            excel_pool.write_xls_line(
                ws_name, row, data, default_format=color['text'])

            # Add comment:
            if write_comment:
                excel_pool.write_comment(
                    ws_name, row, len(data) - 1,
                    u'Il netto è presente per gli ordini completi/confermati')

        # ---------------------------------------------------------------------
        # Collect data:
        # ---------------------------------------------------------------------
        line_ids = line_pool.search(cr, uid, [
            ('order_id.connector_id', '=', ids[0]),
        ], context=context)
        report_data = {
            'all': [],
            'completed': [],  # today
            'working': [],  # working order
            'waiting': [],  # waiting for payment
            'shipping': [],  # transport present
            'invoiced': {},  # invoiced
        }
        today = ('%s' % (datetime.now() - timedelta(days=1)))[:10]

        # ---------------------------------------------------------------------
        # Order invoiced:
        order_ids = order_pool.search(cr, uid, [
            ('connector_id', '=', connector_id),
        ], context=context)
        for order in order_pool.browse(
                cr, uid, order_ids, context=context):
            state = order.state
            date = order.date_order
            period = date[:7]
            total = order.total
            tax = order.total_tax
            shipping = order.real_shipping_total or order.shipping_total
            if order.shipping_total and not order.real_shipping_total:
                missed = 1
            else:
                missed = 0

            # currency = order.currency
            if not date:
                _logger.error('No order date error (%s)!' % order.name)
                continue
            if period not in report_data['invoiced']:
                report_data['invoiced'][period] = {
                    'missed': 0,  # transport
                    'order': 0,  # total order

                    'done': 0.0,
                    'done_shipping': 0.0,
                    'done_tax': 0.0,

                    'pending': 0.0,
                    'pending_shipping': 0.0,
                    'pending_tax': 0.0,

                    'cancel': 0.0,
                }

            if state in ('completed', ):
                report_data['invoiced'][period]['done'] += total
                report_data['invoiced'][period]['done_shipping'] += shipping
                report_data['invoiced'][period]['done_tax'] += tax
                report_data['invoiced'][period]['missed'] += missed
                report_data['invoiced'][period]['order'] += 1
            elif state in ('pending', 'processing', 'on-hold'):  # pending
                report_data['invoiced'][period]['pending'] += total
                report_data['invoiced'][period]['pending_shipping'] += shipping
                report_data['invoiced'][period]['pending_tax'] += shipping
            elif state in ('refunded', 'failed', 'trash', 'cancelled'):
                report_data['invoiced'][period]['cancel'] += total

        # ---------------------------------------------------------------------
        # Product analysis database (init setup):
        product_stats = {}
        web_product_ids = web_product_pool.search(cr, uid, [
            ('connector_id', '=', connector_id),
        ], context=context)
        for web_product in web_product_pool.browse(
                cr, uid, web_product_ids, context=context):
            product = web_product.product_id
            product_stats[product] = {
                'quantity': 0.0,
                'total': 0.0,
                'last_price': 0.0,
                'last_date': False,
            }

        for line in line_pool.browse(cr, uid, line_ids, context=context):
            order = line.order_id
            state = order.state
            product = line.product_id or False
            if product not in product_stats:
                product_stats[product] = {
                    'quantity': 0.0,
                    'total': 0.0,
                    'last_price': 0.0,
                    'last_date': False,
                }
            report_data['all'].append(line)

            completed = (order.wp_date_completed or '')[:10]
            if completed:   # For statistic:
                product_stats[product]['quantity'] += line.quantity
                product_stats[product]['total'] += line.total

                date_order = line.order_id.date_order
                if not product_stats[product]['last_date'] or \
                        date_order > product_stats[product]['last_date']:
                    product_stats[product]['last_price'] = line.price
                    product_stats[product]['last_date'] = date_order

            if completed and completed >= today:
                report_data['completed'].append(line)

            if state in ('processing', ):
                report_data['working'].append(line)

            if state in ('pending', 'on-hold'):
                report_data['waiting'].append(line)

            if line.order_id.shipping_total:
                report_data['shipping'].append(line)

        # ---------------------------------------------------------------------
        # Completed order:
        # ---------------------------------------------------------------------
        ws_name = 'Ordini completi'
        excel_pool.create_worksheet(ws_name)
        row = 0

        # Load formats:
        excel_format = {
            'title': excel_pool.get_format('title'),
            'header': excel_pool.get_format('header'),
            'white': {
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
            'orange': {
                'text': excel_pool.get_format('bg_orange'),
                'number': excel_pool.get_format('bg_orange_number'),
            },
            'grey': {
                'text': excel_pool.get_format('bg_grey'),
                'number': excel_pool.get_format('bg_grey_number'),
            },
            'green': {
                'text': excel_pool.get_format('bg_green'),
                'number': excel_pool.get_format('bg_green_number'),
            },
            'blue': {
                'text': excel_pool.get_format('bg_blue'),
                'number': excel_pool.get_format('bg_blue_number'),
            },
        }

        header = [
            'SKU', 'Prodotto',
            'Q.', 'Prezzo', 'Subtotale',

            'Data', 'Pagato', 'Completo',
            'Ordine', 'Cliente', 'Pagamento', 'Stato',
            'Val.', 'Trasporto', 'Totale', 'Netto',
            ]
        width = [
            16, 40,
            6, 6, 8,
            9, 16, 16,
            7, 35, 20, 18,
            4, 10, 10, 10,
        ]
        excel_pool.column_width(ws_name, width)

        # 1 Title
        excel_pool.write_xls_line(
            ws_name, row, [
                'Totale ordini arrivati esplosi per articolo'],
            default_format=excel_format['title'])
        row += 2

        # 2 Header
        excel_pool.write_xls_line(
            ws_name, row, header, default_format=excel_format['header'])
        excel_pool.autofilter(ws_name, row, 0, row, len(width) - 1)
        row += 1

        for line in sorted(report_data['all'],
                           key=lambda x: (x.order_id.name, x.wp_id),
                           reverse=True):
            get_standard_data_line(excel_pool, ws_name, row, line)
            row += 1

        # ---------------------------------------------------------------------
        # Order invoiced per period:
        # ---------------------------------------------------------------------
        ws_name = 'Ordini fatturati per periodo'
        invoiced_header_a = [
            'Periodo',
            'Annullati',
            'Pendenti', '', '',
            'Completati', '', '',
            'Costi', '', '', 'Netto',
            '# Ordini', 'Trasp. manc.'

        ]

        invoiced_header_b = [
            '',
            'Totale',
            'Totale', 'Trasporto', 'Imposte',
            'Totale', 'Trasporto', 'Imposte',
            'Micronaet', 'Keywords', 'Spese access.', ''
            '', '',
        ]

        invoiced_width = [
            12,
            10,  # Cancel
            10, 10, 10,  # Pending
            10, 10, 10,  # Completed
            10, 10, 10, 15,
            10, 10,
        ]
        excel_pool.create_worksheet(ws_name)
        row = 0
        excel_pool.column_width(ws_name, invoiced_width)

        # 1 Title
        excel_pool.write_xls_line(
            ws_name, row, [
                'Elenco ordini fatturati raggruppati per anno-mese [DB: %s]' %
                cr.dbname,
            ],
            default_format=excel_format['title'])
        row += 2

        # ---------------------------------------------------------------------
        # 2 Header
        # ---------------------------------------------------------------------
        # Part A:
        excel_pool.write_xls_line(
            ws_name, row, invoiced_header_a,
            default_format=excel_format['header'])

        # Setup header:
        excel_pool.merge_cell(ws_name, [row, 0, row + 1, 0])  # Periodo
        excel_pool.merge_cell(ws_name, [row, 11, row + 1, 11])  # Netto
        excel_pool.merge_cell(ws_name, [row, 12, row + 1, 12])  # #Ordini
        excel_pool.merge_cell(ws_name, [row, 13, row + 1, 13])  # Trasp. manc

        excel_pool.merge_cell(ws_name, [row, 2, row, 4])  # Pendenti
        excel_pool.merge_cell(ws_name, [row, 5, row, 7])  # Completi
        excel_pool.merge_cell(ws_name, [row, 8, row, 10])  # Costi
        row += 1

        # Part B:
        excel_pool.write_xls_line(
            ws_name, row, invoiced_header_b,
            default_format=excel_format['header'])
        excel_pool.autofilter(
            ws_name, row, 0, row + 1, len(invoiced_width) - 1)
        row += 1

        color = excel_format['white']
        for period in sorted(report_data['invoiced'], reverse=True):
            invoiced_data = report_data['invoiced'][period]
            keyword_cost = 0.0
            accessory_cost = 0.0

            net = invoiced_data['done'] - invoiced_data['done_tax'] - \
                  invoiced_data['done_shipping']  # First level
            micronaet_cost = get_extra_cost('micronaet', period, net)
            net -= micronaet_cost  # Second level
            data = [
                (period, color['text']),
                invoiced_data['cancel'],
                invoiced_data['pending'], invoiced_data['pending_shipping'],
                invoiced_data['pending_tax'],

                invoiced_data['done'], invoiced_data['done_shipping'],
                invoiced_data['done_tax'],

                micronaet_cost,
                keyword_cost,
                accessory_cost,

                net,
                invoiced_data['order'],
                invoiced_data['missed'],
            ]

            excel_pool.write_xls_line(
                ws_name, row, data, default_format=color['number'])
            row += 1

        # ---------------------------------------------------------------------
        # Completed order:
        # ---------------------------------------------------------------------
        ws_name = 'Ordini chiusi da ieri'
        excel_pool.create_worksheet(ws_name)
        row = 0
        excel_pool.column_width(ws_name, width)

        # 1 Title
        excel_pool.write_xls_line(
            ws_name, row, [
                'Elenco righe ordine chiusi da ieri'],
            default_format=excel_format['title'])
        row += 2

        # 2 Header
        excel_pool.write_xls_line(
            ws_name, row, header, default_format=excel_format['header'])
        excel_pool.autofilter(ws_name, row, 0, row, len(width) - 1)
        row += 1

        for line in sorted(report_data['completed'],
                           key=lambda x: (
                                x.order_id.wp_date_completed, x.wp_id)):
            get_standard_data_line(excel_pool, ws_name, row, line)
            row += 1

        # ---------------------------------------------------------------------
        # Waiting order:
        # ---------------------------------------------------------------------
        ws_name = 'Ordini in attesa di pagamento'
        excel_pool.create_worksheet(ws_name)
        row = 0
        excel_pool.column_width(ws_name, width)

        # 1 Title
        excel_pool.write_xls_line(
            ws_name, row, [
                'Elenco righe ordine che sono in attesa di pagamento'],
            default_format=excel_format['title'])
        row += 2

        # 2 Header
        excel_pool.write_xls_line(
            ws_name, row, header, default_format=excel_format['header'])
        excel_pool.autofilter(ws_name, row, 0, row, len(width) - 1)
        row += 1

        for line in sorted(report_data['waiting'],
                           key=lambda x: (
                                x.order_id.name, x.wp_id)):
            get_standard_data_line(excel_pool, ws_name, row, line)
            row += 1

        # ---------------------------------------------------------------------
        # Working order:
        # ---------------------------------------------------------------------
        ws_name = 'Ordini da preparare'
        excel_pool.create_worksheet(ws_name)
        row = 0
        excel_pool.column_width(ws_name, width)

        # 1 Title
        excel_pool.write_xls_line(
            ws_name, row, [
                'Elenco righe ordine confermati da preparare'],
            default_format=excel_format['title'])
        row += 2

        # 2 Header
        excel_pool.write_xls_line(
            ws_name, row, header, default_format=excel_format['header'])
        excel_pool.autofilter(ws_name, row, 0, row, len(width) - 1)
        row += 1

        for line in sorted(report_data['working'],
                           key=lambda x: (
                                x.order_id.name, x.wp_id)):
            get_standard_data_line(excel_pool, ws_name, row, line)
            row += 1

        # ---------------------------------------------------------------------
        # Shipping order:
        # ---------------------------------------------------------------------
        ws_name = 'Ordini con trasporto'
        excel_pool.create_worksheet(ws_name)
        row = 0
        excel_pool.column_width(ws_name, width)

        # 1 Title
        excel_pool.write_xls_line(
            ws_name, row, [
                'Elenco righe ordine con costo di trasporto presente'],
            default_format=excel_format['title'])
        row += 2

        # 2 Header
        excel_pool.write_xls_line(
            ws_name, row, header, default_format=excel_format['header'])
        excel_pool.autofilter(ws_name, row, 0, row, len(width) - 1)
        row += 1

        for line in sorted(report_data['shipping'],
                           key=lambda x: (
                                x.order_id.name, x.wp_id)):
            get_standard_data_line(excel_pool, ws_name, row, line)
            row += 1

        # ---------------------------------------------------------------------
        # Shipping order:
        # ---------------------------------------------------------------------
        ws_name = 'Analisi prodotti'
        product_header = [
            'Pubbl.',
            'Codice', 'Prodotto',
            'Venduto q.', 'Fatturato',
            'Ultima vendita', 'Ultimo p.d.v.',
            'Esistenza web',
            'Prezzo ODOO', 'Prezzo web', 'Costo Adwords',
        ]
        product_width = [
            8,
            15, 40,
            10, 10,
            10, 12,
            10,
            10, 10, 10,
        ]

        excel_pool.create_worksheet(ws_name)
        row = 0
        excel_pool.column_width(ws_name, product_width)

        # 1 Title
        excel_pool.write_xls_line(
            ws_name, row, [
                'Sato prodotti web'],
            default_format=excel_format['title'])
        row += 2

        # 2 Header
        excel_pool.write_xls_line(
            ws_name, row, product_header,
            default_format=excel_format['header'])
        excel_pool.autofilter(ws_name, row, 0, row, 2)
        row += 1

        if False in product_stats:
            del(product_stats[False])

        for product in sorted(product_stats, key=lambda x: x.default_code):
            # 1. Order data:
            order_data = product_stats[product]

            # 2. Web product data:
            web_product_ids = web_product_pool.search(cr, uid, [
                ('connector_id', '=', connector_id),
                ('product_id', '=', product.id),
            ], context=context)
            if web_product_ids:
                web_product = web_product_pool.browse(
                    cr, uid, web_product_ids, context=context)[0]
                stock_qty, stock_comment = \
                    web_product_pool.get_existence_for_product(
                        cr, uid, web_product, context=context)
                multiplier = web_product.price_multi or 1
                if multiplier > 1:
                    stock_qty = stock_qty // multiplier
                odoo_price = web_product.force_price or web_product.lst_price
                price = web_product_pool.get_wp_price(web_product)
                published = web_product.published
            else:
                stock_qty = 0.0
                stock_comment = odoo_price = price = published = ''

            if not published:
                color = excel_format['grey']
            elif stock_qty > 0:
                color = excel_format['white']
            else:
                color = excel_format['red']
            product_data = [
                'X' if published else '',
                product.default_code or '',
                product.name or '',
                (order_data['quantity'] or '', color['number']),
                (order_data['total'] or '', color['number']),
                order_data['last_date'] or '',
                (order_data['last_price'] or '', color['number']),

                (stock_qty, color['number']),
                # stock_comment
                (odoo_price, color['number']),
                (price, color['number']),
                ('', color['number']),  # Adwords cost
            ]
            # Write line:
            excel_pool.write_xls_line(
                ws_name, row, product_data,
                default_format=color['text'])
            row += 1

        # ---------------------------------------------------------------------
        # Return excel file:
        if send_group:
            excel_pool.send_mail_to_group(
                cr, uid,
                send_group,
                'Ordini Wordpress',
                'Elenco ordini Wordpress',
                'ordinato.xlsx',
                context=context)
            return True
        else:
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
            Context parameters:
                'from_yesterday' for check from yesterday)
                'report_log' for send email with status report
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
        report_log = context.get('report_log')

        # Pool used:
        order_pool = self.pool.get('wordpress.sale.order')
        line_pool = self.pool.get('wordpress.sale.order.line')
        product_pool = self.pool.get('product.product')
        web_product_pool = self.pool.get('product.product.web.server')

        _logger.warning(
            'Read order on wordpress [from_yesterday=%s, report_log=%s]' % (
                from_yesterday, report_log))

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
        force_context = context.copy()  # Used for update manual stock manag.

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

                partner_email = record['billing']['email']
                total = record['total']
                marketplace = order_pool.get_marketplace(partner_email)

                if marketplace == 'Amazon':
                    total_tax = float(total) * 0.22 / 1.22
                    # todo get shipping included total:
                    shipping_total = 0.0
                else:  # Worpress
                    total_tax = record['total_tax']
                    shipping_total = record['shipping_total']
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
                    'total': total,
                    'total_tax': total_tax,
                    'shipping_total': shipping_total,
                }
                if order_ids:  # XXX No update of header
                    run_mode = 'write'
                    order_id = order_ids[0]
                    order_pool.write(
                        cr, uid, order_ids, order_header, context=context)
                    _logger.info('Yet found (update only line) %s' % number)
                else:  # Read data:
                    run_mode = 'create'

                    # Address:
                    billing = record['billing']
                    shipping = record['shipping']
                    partner_name = '%s %s - %s' % (
                        billing['first_name'],
                        billing['last_name'],
                        billing['company'] or '/',
                    )

                    # partner_email = billing['email']
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
                order_total = 0.0
                for line in record['line_items']:
                    name = line['name']
                    sku = self.wp_clean_code(line['sku'])
                    product_id = False
                    quantity = line['quantity']
                    if sku:
                        product_ids = product_pool.search(cr, uid, [
                            ('default_code', '=', sku),
                        ], context=context)
                        if product_ids:
                            product_id = product_ids[0]

                    # ---------------------------------------------------------
                    # Manual stock management:
                    # ---------------------------------------------------------
                    if run_mode == 'create':
                        web_product_ids = web_product_pool.search(cr, uid, [
                            ('connector_id', '=', connector_id),
                            ('product_id', '=', product_id),
                            ('force_this_stock', '>', 0),  # manage manual q.
                        ], context=context)
                        if web_product_ids:
                            web_product = web_product_pool.browse(
                                cr, uid, web_product_ids, context=context)[0]
                            new_qty = web_product.force_this_stock - quantity
                            if new_qty < 0:
                                _logger.error('Negative status on web order!')
                                new_qty = 0
                            force_context['forced_manual_stock_comment'] = \
                                'Scalato ordine: %s' % number
                            web_product_pool.write(cr, uid, web_product_ids, {
                                'force_this_stock': new_qty,
                            }, context=force_context)

                    if marketplace == 'Amazon':
                        line_price = float(line['price']) / 1.22
                        line_total = float(line['price']) * float(line['quantity']) / 1.22
                    else:  # Wordpress
                        line_price = float(line['price'])
                        line_total = float(line['price']) * float(line['quantity'])
                    order_total += line_total

                    order_line = {
                        'order_id': order_id,
                        'wp_id': line['id'],
                        'name': name,
                        'sku': sku,
                        'quantity': quantity,
                        'price': line_price,
                        'total': line_total,
                        'product_id': product_id,
                        }
                    line_pool.create(cr, uid, order_line, context=context)

                # Update total:
                order_tax = order_total * 0.22
                order_pool.write(
                    cr, uid, [order_id], {
                        'total_tax': order_tax,
                        'total': order_total + order_tax,
                    }, context=context)

            except:
                _logger.error('Error creating order!\n%s' % (sys.exc_info(), ))
                continue

        if report_log:  # Send mail to manager group
            ctx = context.copy()
            ctx['send_group'] = 'wp_connector.group_order_report_manager'
            return self.status_wordpress_order_report(
                cr, uid, ids, context=ctx)
        else:
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


class SaleOrder(orm.Model):
    """ Model name: Sale Order
    """

    _inherit = 'sale.order'

    _columns = {
        'wordpress_order_id': fields.many2one(
            'wordpress.sale.order', 'Ordine Wordpress')
    }
