#!/usr/bin/python
# '*'coding: utf'8 '*'
###############################################################################
#
# ODOO (ex OpenERP)
# Open Source Management Solution
# Copyright (C) 2001'2015 Micronaet S.r.l. (<https://micronaet.com>)
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
import erppeek
import xlrd
import woocommerce
import ConfigParser
import slugify
import pickle
from datetime import datetime

# Parameters:
verbose = False  # Log with extra data
lang_db = ['it_IT', 'en_US']

# Load WP link DB:
pickle_file = './log/wp_master_data.p'
master_db = pickle.load(open(pickle_file, 'rb'))

# -----------------------------------------------------------------------------
#                                 Logging:
# -----------------------------------------------------------------------------
activity_file = './log/activity.log'
activity_f = open(activity_file, 'a')


# Utility:
def log_activity(event, mode='info'):
    """ Log activity on file
    """
    activity_f.write('%s [%s] %s\n' % (
        datetime.now(),
        mode.upper(),
        event,
        ))


# -----------------------------------------------------------------------------
# ODOO entry point:
# -----------------------------------------------------------------------------
database = {}
for root, folders, files in os.walk('./config'):
    for filename in files:
        if filename == 'wordpress.cfg':
            continue
        company = filename.split('.')[0]
        cfg_file = os.path.join(root, filename)

        # From config file:
        config = ConfigParser.ConfigParser()
        config.read([cfg_file])
        dbname = config.get('dbaccess', 'dbname')
        user = config.get('dbaccess', 'user')
        pwd = config.get('dbaccess', 'pwd')
        server = config.get('dbaccess', 'server')
        port = config.get('dbaccess', 'port')
        connector_id = eval(config.get('dbaccess', 'connector_id'))

        # ---------------------------------------------------------------------
        # Connect to ODOO:
        # ---------------------------------------------------------------------
        odoo = erppeek.Client(
            'http://%s:%s' % (server, port),
            db=dbname,
            user=user,
            password=pwd,
            )

        database[company] = odoo.model('product.product.web.server')
    break

log_activity('End update ODOO Deadlink ID')

