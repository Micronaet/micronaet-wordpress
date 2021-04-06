import os
import sys
import erppeek
import ConfigParser
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

        log_message(f_log, 'Updating order for %s company' % company)

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
            'web': odoo.model('product.product.server.web'),
        }
        log_message(f_log, 'Connect with ODOO, company %s\n' % company)
    break

# Use first company order only:
order_ids = odoo_db['fia']['order'].search()
orders = odoo_db['fia']['order'].browse(order_ids)
order_file = open(os.path.join('./data', 'wordpress.order.csv'), 'a')
mask = '%-10s%-15s%8s\n'
for order in orders:
    for line in order.order_line:
        product = get_product(line, odoo_db)
        web_product = get_web_product(line, odoo_db)
        order_file.write(mask % (
            order.name or '',
            order.state or '',
            (order.date_order or '').replace('-', ''),
        ))


