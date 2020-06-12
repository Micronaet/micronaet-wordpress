import os
import sys
import erppeek
import ConfigParser
import pdb; pdb.set_trace()
# -----------------------------------------------------------------------------
# Read configuration parameter:
# -----------------------------------------------------------------------------
for root, folders, files in os.walk('..'):
    for cfg_file in files:
        if not cfg_file.startswith('openerp'):
            print('Not a config file: %s' % cfg_file)
            continue
        print('Updating order for %s company' % cfg_file.split('.')[1])
        cfg_file = os.path.expanduser(os.path.join('../', cfg_file))
        config = ConfigParser.ConfigParser()
        config.read([cfg_file])
        dbname = config.get('dbaccess', 'dbname')
        user = config.get('dbaccess', 'user')
        pwd = config.get('dbaccess', 'pwd')
        server = config.get('dbaccess', 'server')
        port = config.get('dbaccess', 'port')
        connector_id = config.get('dbaccess', 'connector_id')

        # ---------------------------------------------------------------------
        # Connect to ODOO:
        # ---------------------------------------------------------------------
        odoo = erppeek.Client(
            'http://%s:%s' % (server, port),
            db=dbname, user=user, password=pwd,
            )
        import pdb; pdb.set_trace()
        argv = sys.argv
        if len(argv) != 3:
            # Called without all parameter:
            odoo.context = {'from_yesterday': True}

        connector_pool = odoo.model('connector.server')
        connector_pool.get_sale_order_now([connector_id])
    break
