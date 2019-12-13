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
import ConfigParser

print 'Cambiare connector ID (and DB access)!'
import pdb; pdb.set_trace()
connector_id = 5 # REAL connector.server for wordpress # XXX change!
#connector_id = 9 # LOCAL connector.server for wordpress # XXX change!

column = {
    'code': 0,
    'selection': 1,
    'mrp': 2,
    'short': 3,
    'long': 4, 
    'color': 5,
    }
    
file_in = './product.xlsx'
row_start = 1

# -----------------------------------------------------------------------------
# Read configuration parameter:
# -----------------------------------------------------------------------------
# From config file:
cfg_file = os.path.expanduser('../openerp.cfg')
#cfg_file = os.path.expanduser('../local.cfg')

config = ConfigParser.ConfigParser()
config.read([cfg_file])
dbname = config.get('dbaccess', 'dbname')
user = config.get('dbaccess', 'user')
pwd = config.get('dbaccess', 'pwd')
server = config.get('dbaccess', 'server')
port = config.get('dbaccess', 'port')   # verify if it's necessary: getint

# -----------------------------------------------------------------------------
# Connect to ODOO:
# -----------------------------------------------------------------------------
odoo = erppeek.Client(
    'http://%s:%s' % (
        server, port), 
    db=dbname,
    user=user,
    password=pwd,
    )

# Setup as Italian lang:
odoo.context = {'lang': 'it_IT'}

# Pool used:
product_pool = odoo.model('product.product')
web_pool = odoo.model('product.product.web.server')
color_pool = odoo.model('connector.product.color.dot')

# Excel input:
try:
    WB = xlrd.open_workbook(file_in)
except:
    print '[ERROR] Cannot read XLS file: %s' % file_in
    sys.exit()
WS = WB.sheet_by_index(0)

# -----------------------------------------------------------------------------
# Delete all
# -----------------------------------------------------------------------------
web_ids = web_pool.search([
    ('connector_id', '=', connector_id),
    ])
if web_ids:
    print 'Set unpublish all product for this connector, # %s' % len(web_ids)
    web_pool.write(web_ids, {
        'published': False,
        })


# -----------------------------------------------------------------------------
# Create from files:
# -----------------------------------------------------------------------------
i = 0
wp_parent_last = False
import pdb; pdb.set_trace()
for row in range(row_start, WS.nrows):
    i += 1

    # -------------------------------------------------------------------------
    # Mapping:
    # -------------------------------------------------------------------------
    default_code = WS.cell(row, column['code']).value
    selection = (WS.cell(row, column['selection']).value or '').upper()
    mrp = (WS.cell(row, column['mrp']).value or '').upper()
    short_text = WS.cell(row, column['short']).value
    long_text = WS.cell(row, column['long']).value
    color = WS.cell(row, column['color']).value or 'NON SELEZIONABILE'

    if not default_code or selection not in ('X', 'O'):
        print '%s. Selezione non corretta: %s [%s]' % (
            i, default_code, selection)
        continue
        
    # -------------------------------------------------------------------------
    # Color:
    # -------------------------------------------------------------------------
    wp_color_id = False
    if mrp:
        color = '%s-%s' % (
            default_code[6:8].strip().upper() or 'NE',  # XXX Neutro
            default_code[8:].strip().upper(),
            )

    wp_color_ids = color_pool.search([
        ('name', '=', color),
        ])
    if not wp_color_ids:
        print '   Creazione colore: %s' % color
        wp_color_id = color_pool.create({
            'connector_id': connector_id,
            'name': color,
            }).id

    product_ids = product_pool.search([
        ('default_code', '=', default_code),
        ])
    if product_ids:
        product_id = product_ids[0]

    # -------------------------------------------------------------------------
    #                         Product:
    # -------------------------------------------------------------------------
    product_pool.write(product_ids, {
        'emotional_short_description': short_text,
        'emotional_description': long_text,
        })

    # Update package:
    product_pool.auto_package_assign(product_ids)
    
    # -------------------------------------------------------------------------
    #                         Web selection:
    # -------------------------------------------------------------------------
    data = {
        'connector_id': connector_id,
        'wp_color_id': wp_color_id,
        'published': True,
        'product_id': product_id,             
        'wp_type': 'variable',
        }
    
    if selection == 'X':  # Parent
        data.update({
            'wp_parent_template': True,
            'wp_parent_id': False,
            'wp_parent_code': default_code[:6],
            })
        # XXX wp_it_id problem!
    else:  # Variation:
        data.update({
            'wp_parent_template': False,
            'wp_parent_id': wp_parent_last,
            'wp_parent_code': False,
            })

    web_ids = web_pool.search([
        ('connector_id', '=', connector_id),
        ('product_id', '=', product_id),
        ])

    if web_ids:
        print '%s. Aggiornamento: %s' % (i, default_code)
        web_pool.write(web_ids, data)
        web_id = web_ids[0]
    else:    
        print '%s. Creazione: %s' % (i, default_code)
        wb_id = web_pool.create(data).id

    if selection == 'X': 
        # Save for child:
        wp_parent_last = web_id

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
