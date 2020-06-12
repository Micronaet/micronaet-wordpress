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

# -----------------------------------------------------------------------------
# Read configuration parameter:
# -----------------------------------------------------------------------------
for root, folders, files in os.walk('..'):
    for cfg_file in files:
        if not cfg_file.startswith('openerp'):
            print('Not a config file: %s' % cfg_file)
            continue
        company = cfg_file.split('.')[1]
        f_log = open(os.path.join('./log', company), 'a')

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

        # ---------------------------------------------------------------------
        # Connect to ODOO:
        # ---------------------------------------------------------------------
        odoo = erppeek.Client(
            'http://%s:%s' % (server, port),
            db=dbname, user=user, password=pwd,
            )
        argv = sys.argv
        if len(argv) != 2:
            print('Call python ./load_order.py [all or yesterday]')
            continue

        # Check call parameters:
        if argv[1].lower() == 'yesterday':
            odoo.context = {'from_yesterday': True}
        log_message(f_log, 'Call mode %s' % argv[1])

        connector_pool = odoo.model('connector.server')
        res = connector_pool.get_sale_order_now([connector_id])
        log_message(f_log, 'End updating order for %s company\n' % company)
    break
