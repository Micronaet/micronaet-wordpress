#!/usr/bin/python
# '*'coding: utf'8 '*'
###############################################################################
# Copyright (C) 2001'2015 Micronaet S.r.l. (<https://micronaet.com>)
# Developer: Nicola Riolini @thebrush (<https://it.linkedin.com/in/thebrush>)
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
model_db = {}
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
        model_db[company] = odoo.model('product.product.web.server')
    break

import pdb; pdb.set_trace()
total = 0
for lang in master_db:
    for sku in master_db[lang]:
        sku = sku.replace('&nbsp;', ' ')
        wp_id = master_db[lang][sku]
        field = 'wp_%s_id' % lang

        for company in model_db:
            model = model_db[company]
            # Master with sku and WP ID different:
            web_ids = model.search([
                ('wp_parent_template', '=', True),
                ('product_id.default_code', '=', sku),
                # (field, '!=', wp_id),
                (field, '=', 0),
            ])
            if web_ids:
                total += 1
                print '%s [%s]: Update %s with %s: %s' % (
                    company, lang, sku, field, wp_id,
                )
                #model.write(web_ids, {
                #    field: wp_id,
                #})
                break  # Exit loop when update

log_activity('End update ODOO Deadlink ID: %s' % total)

