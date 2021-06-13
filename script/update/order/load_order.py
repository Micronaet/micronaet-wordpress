import os
import pdb
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
            print('[ERROR] Not a config file: %s' % cfg_file)
            continue
        company = cfg_file.split('.')[1]
        f_log = open(os.path.join('./log', company), 'a')

        log_message(f_log, '[INFO] Updating order for %s company' % company)

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
        argv = sys.argv
        if len(argv) != 2:
            print('[INFO] Call python ./load_order.py [all or yesterday]')
            continue

        # Check call parameters:
        if argv[1].lower() == 'yesterday':
            odoo.context = {'from_yesterday': True}
        else:
            # Send message with all order from wordpress to the manager group
            if send_message:
                odoo.context = {'report_log': True}
        log_message(f_log, '[INFO] Call mode %s' % argv[1])

        connector_pool = odoo.model('connector.server')
        res = connector_pool.get_sale_order_now([connector_id])
        log_message(
            f_log, '[INFO] End updating order for %s company\n' % company)

        order_pool = odoo.model('wordpress.sale.order')
        order_pool.raise_message_new_order(False)
        log_message(
            f_log, '[INFO] Raise new order in Telegram %s company\n' % company)
        if send_message:  # Manage order only in send message database!
            # Generate ODOO order
            log_message(
                f_log, '[INFO] Generate ODOO order: %s\n' % company)
            order_pool.confirm_all_new_sale_order()

            # Cancel removed order
            log_message(
                f_log, '[INFO] Cancel not confirmed order: %s\n' % company)
            try:
                order_pool.cancel_all_sale_order_removed()
            except:
                print(str(sys.exc_info()))

            # Confirm picking for wp order confirmed
            log_message(
                f_log, '[INFO] Check completed order: %s\n' % company)
            try:
                order_pool.unload_stock_for_sale_order_completed()
            except:
                print(str(sys.exc_info()))

    break
