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


def get_product(line, odoo_db):
    """ Extract product from line
    """
    return True

def get_web_product(line, odoo_db):
    """ Extract web product from line
    """
    return True

# -----------------------------------------------------------------------------
# Read configuration parameter:
# -----------------------------------------------------------------------------
odoo_db = {}
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

        # ---------------------------------------------------------------------
        # Connect to ODOO:
        # ---------------------------------------------------------------------
        odoo = erppeek.Client(
            'http://%s:%s' % (server, port),
            db=dbname, user=user, password=pwd,
            )
        odoo_db[company] = {
            'order': odoo.model('wordpress.sale.order'),
            'product': odoo.model('product.product'),
            'web': odoo.model('product.product.web.server'),
        }
        log_message(f_log, 'Connected with ODOO, company %s\n' % company)
    break

# Use first company order only:
order_ids = odoo_db['fia']['order'].search()
orders = odoo_db['fia']['order'].browse(order_ids)
order_file = open(os.path.join('./data', 'wordpress.order.csv'), 'a')
log_message(f_log, 'Reading %s order from company %s\n' % (
    len(order_ids), company))

mask = '%-10s%-15s%8s%1s%-30s%-30s%-16s%-30s%-5s%-30s%-8s%-35s%-30s' \
       '%-18s%-35s%-20s%-30s%-5s' \
       '%-10.2f%-10.2f%-10.2f' \
       '%-10s%-10.2f%-1s%-10s%-10s\n'

for order in orders:
    for line in order.line_ids:
        product = get_product(line, odoo_db)
        web_product = get_web_product(line, odoo_db)
        data = (
            # Header:
            (order.name or '')[:10],  # Order number
            (order.state or '')[:15],  # State of order (Causale)
            (order.date_order or '').replace('-', ''),  # Date order (AAAAMMGG)
            'F',  # TODO A or F (Azienda or Persona Fisica)
            (order.partner_name or '')[:30],  # Last name
            ('')[:30],  # First name (non importato, unito al cognome)
            ('')[:16],  # Fiscal code (non presente)
            (order.billing or '')[:30],  # Address
            ('')[:5],  # ZIP
            ('')[:30],  # City
            '',  # Birthday (AAAAMMGG) Non presente
            (order.partner_email or '')[:35],  # Email
            (order.partner_phone or '')[:30],  # Phone

            # Line:
            (line.sku or '')[:18],  # SKU
            (line.name or '')[:35],  # Product description
            ('')[:20],  # Brand
            ('')[:30],  # Category (more than one!)
            ('NR')[:5],  # UOM  (sempre NR?)
            line.quantity,  # Q.  (10.2)
            0.0,  # Cost  (10.2)
            line.price,  # List price  (10.2)

            # Footer
            (order.payment)[:10],  # Payment
            (order.real_shipping_total or order.shipping_total),  # Trans. 10.2
            '',  # S = esente IVA
            ('')[:10],  # Sconto ordine
            ('')[:10],  # Coupon sconto
        )
        order_file.write(mask % data)

