import os
import sys
import erppeek
import ConfigParser
import pdb
from datetime import datetime


def log_message(log_file, message, mode='info', verbose=True):
    """ Log message
    """
    mode = mode.upper()
    log_file.write('[%s] %s. %s\n' % (
        mode,
        datetime.now(),
        message,
    ))
    if verbose:
        print(message.strip())


def get_product(line, odoo_db, cache):
    """ Extract product from line if present (primary company)
        Extract product from secondary company with sku
    """
    if 'product' not in cache:
        cache['product'] = {}

    product = line.product_id
    sku = line.sku
    if sku not in cache['product']:
        if product:
            cache['product'][sku] = product
        else:
            product_ids = odoo_db[company_2]['product'].search([
                ('default_code', '=', sku),
            ])
            if product_ids:
                 cache['product'][sku] = \
                     odoo_db[company_2]['product'].browse(product_ids)[0]

    return cache['product'].get(sku)


def get_web_product(line, connectors, odoo_db, cache):
    """ Extract web product from line
    """
    if 'web' not in cache:
        cache['web'] = {}

    product = line.product_id
    sku = line.sku
    if product:
        connector_id = connectors[company_1]
    else:
        connector_id = connectors[company_2]

    if sku not in cache['web']:
        if product:
            pool = odoo_db[company_1]['web']
        else:
            pool = odoo_db[company_2]['web']

        web_ids = pool.search([
            ('connector_id', '=', connector_id),
            ('product_id.default_code', '=', sku),
        ])
        if web_ids:
             cache['web'][sku] = \
                 pool.browse(web_ids)[0]

    return cache['web'].get(sku)


def clean_date(value):
    """ Clean not ascii char
    """
    return (value or '').replace('-', '')


def clean_char(value, limit):
    """ Clean not ascii char
    """
    res = ''
    for c in (value or '').strip():
        if ord(c) < 127:
            res += c
        else:
            res += ' '
    return res[:limit]

# -----------------------------------------------------------------------------
# Read configuration parameter:
# -----------------------------------------------------------------------------
# Parameters:
company_1 = 'gpb'
company_2 = 'fia'
from_date = '2022-01-01'

odoo_db = {}
product_cache = {}
connectors = {}

for root, folders, files in os.walk('..'):
    for cfg_file in files:
        if not cfg_file.startswith('openerp'):
            print('Not a config file: %s' % cfg_file)
            continue
        company = cfg_file.split('.')[1]
        f_log = open(os.path.join('./log', 'export.%s' % company), 'a')

        cfg_file = os.path.expanduser(os.path.join('../', cfg_file))
        config = ConfigParser.ConfigParser()
        config.read([cfg_file])
        dbname = config.get('dbaccess', 'dbname')
        user = config.get('dbaccess', 'user')
        pwd = config.get('dbaccess', 'pwd')
        server = config.get('dbaccess', 'server')
        port = config.get('dbaccess', 'port')
        connector_id = int(config.get('dbaccess', 'connector_id'))
        send_message = eval(config.get('dbaccess', 'send_message'))
        extract_path = config.get('extract', 'path')
        connectors[company] = connector_id

        # ---------------------------------------------------------------------
        # Connect to ODOO:
        # ---------------------------------------------------------------------
        odoo = erppeek.Client(
            'http://%s:%s' % (server, port),
            db=dbname, user=user, password=pwd,
            )
        odoo.context = {'lang': 'it_IT'}
        odoo_db[company] = {
            'order': odoo.model('wordpress.sale.order'),
            'product': odoo.model('product.product'),
            'web': odoo.model('product.product.web.server'),
        }
        log_message(f_log, 'Connected with ODOO, company %s\n' % company)
    break

# -----------------------------------------------------------------------------
#                       Extract order list for Accounting:
# -----------------------------------------------------------------------------
def clean(value):
    """ Clean sku
    """
    return value.replace('\xa0', ' ')

gap = 0.0001
shipping_filename = os.path.join(extract_path, 'wordpress.shipping.csv')
if os.path.exists(shipping_filename):
    log_message(f_log, 'File for export shipping not imported: %s\n' %
                shipping_filename)
else:
    # Use first company order only:
    order_ids = odoo_db[company_1]['order'].search([
        ('real_shipping_total', '>', 0),
        ('shipping_exported', '=', False),
    ])
    orders = odoo_db[company_1]['order'].browse(order_ids)

    shipping_file = open(shipping_filename, 'w')
    log_message(f_log, 'Reading %s order from shipping: Company %s\n' % (
        len(order_ids), company))

    mask = '%-10s%-15s%-10.2f\n'  # todo \r
    for order in orders:
        previous_ship = order.shipping_total
        current_ship = order.real_shipping_total  # Present because of filter!

        net_total = order.total - order.total_tax

        previous_net_total = net_total - previous_ship
        current_net_total = net_total - current_ship

        done = True
        if previous_net_total:  # No division by zero!
            rate = current_net_total / previous_net_total
            if abs(previous_ship - current_ship) > gap:  # Change if different
                for line in order.line_ids:
                    try:
                        shipping_file.write(mask % (
                            order.name,
                            clean(line.sku),
                            line.total * rate,
                        ))
                    except:
                        done = False
                        print('Error converting order: %s [%s]' % (
                            order.name, line.sku))
                        log_message(
                            f_log,
                            'Error converting order: %s' % order.name)

            shipping_file.flush()  # Update file

        # Shipment append:
        carrier_code = order.carrier_supplier_id.accounting_code
        courier_code = order.courier_supplier_id.accounting_code
        if carrier_code and courier_code:
            shipping_code = '%s%s' % (carrier_code, courier_code)
        else:
            shipping_code = 'SPT'
        shipping_file.write(mask % (
            order.name,
            shipping_code,
            current_ship,
        ))

        # Price are similar, no need to update
        if done:
            odoo_db[company_1]['order'].write([order.id], {
                'shipping_exported': True,
            })

    log_message(f_log, 'Shipping order exported: # %s' % len(order_ids))

# -----------------------------------------------------------------------------
#                       Extract order list for Accounting:
# -----------------------------------------------------------------------------
# Use first company order only:
order_ids = odoo_db[company_1]['order'].search([
    ('date_order', '>=', from_date),
])
orders = odoo_db[company_1]['order'].browse(order_ids)
order_file = open(os.path.join(extract_path, 'wordpress.order.csv'), 'w')
log_message(f_log, 'Reading %s order from company %s\n' % (
    len(order_ids), company))

mask = '%-10s%-15s%8s%1s%-30s%-30s%-16s%-30s%-5s%-30s%2s%-8s%-35s%-30s' \
       '%-18s%-45s%-20s%-30s%-5s' \
       '%-10.2f%-10.2f%-10.2f' \
       '%-20s%-10.2f%-1s%-10s%-10s%-3s\n'  # TODO \r

for order in orders:
    wp_record = eval(order.wp_record)
    billing = wp_record['billing']
    meta_data = wp_record['meta_data']
    for line in order.line_ids:
        # Data from product:
        product = get_product(line, odoo_db, product_cache)
        if product:
            cost = product.inventory_cost_no_move or product.standard_price
        else:
            cost = 0.0

        # Data from web product:
        web_product = get_web_product(line, connectors, odoo_db, product_cache)
        if web_product:
            category = brand = ''
            if web_product.brand_id:
                brand = web_product.brand_id.name or ''
            if web_product.wordpress_categ_ids:
                category = web_product.wordpress_categ_ids[0].name  # first!
        else:
            brand = ''
            category = ''
        vat = ''
        if billing['company']:
            contact_type = 'A'
            for item in meta_data:
                if item['key'] == '_billing_vat':
                    vat = item['value'] or ''
                    break
        else:
            contact_type = 'F'

        marketplace = order.marketplace
        last_name = billing['last_name']
        first_name = billing['first_name']
        data = (
            # Header:
            clean_char(order.name, 10),  # Order number
            clean_char(order.state, 15),  # State of order (Causale)
            clean_date(order.date_order),  # Date order (AAAAMMGG)
            contact_type,  # A(zienda) or F(isica) (1 char)
            clean_char(last_name or first_name, 30),  # Last name
            clean_char(first_name or last_name, 30),  # First name
            clean_char(vat, 16),  # Fiscal code (VAT for now)
            clean_char('%s %s' % (
                billing['address_1'], billing['address_2']), 30),  # Address
            clean_char(billing['postcode'], 5),  # ZIP
            clean_char(billing['city'], 30),  # City
            clean_char(billing['country'], 2),  # County
            clean_date(''),  # Birthday (AAAAMMGG) Non presente
            clean_char(order.partner_email, 35),  # Email
            clean_char(order.partner_phone, 30),  # Phone

            # Line:
            clean_char(line.sku, 18),  # SKU
            clean_char(line.name, 45),  # Product description
            clean_char(brand, 20),  # Brand
            clean_char(category, 30),  # Category (more than one!)
            clean_char('NR', 5),  # UOM  (sempre NR?)
            line.quantity,  # Q.  (10.2)
            cost,  # Cost  (10.2)
            line.price,  # List price  (10.2)

            # Footer
            clean_char(order.payment, 20),  # Payment
            (order.real_shipping_total or order.shipping_total),  # Trans. 10.2
            '',  # S = esente IVA (1 char)
            clean_char('', 10),  # Sconto ordine
            clean_char('', 10),  # Coupon sconto
            clean_char(marketplace, 3),   # Marketplace
        )
        order_file.write(mask % data)
        order_file.flush()
