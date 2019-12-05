# -*- coding: utf-8 -*-
###############################################################################
#
# ODOO (ex OpenERP) 
# Open Source Management Solution
# Copyright (C) 2001-2015 Micronaet S.r.l. (<http://www.micronaet.it>)
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
import ConfigParser
import subprocess
import xlrd

file_in = './emotional.xlsx'
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

print 'Accesso: Server %s Database %s' % (
    server, dbname)

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

# Pool used:
product_pool = odoo.model('product.product')

# Excel input:
try:
    WB = xlrd.open_workbook(file_in)
except:
    print '[ERROR] Cannot read XLS file: %s' % file_in
    sys.exit()
WS = WB.sheet_by_index(0)

import pdb; pdb.set_trace()
for row in range(row_start, WS.nrows):
    default_code = WS.cell(row, 0).value
    short_description = WS.cell(row, 1).value
    description = WS.cell(row, 2).value
    search_code = default_code.replace(' ', '_') + '%'

    product_ids = product_pool.search([
        ('default_code', 'ilike', search_code),
        ])
    print 'Code: %s found %s' % (
        default_code,
        len(product_ids)
        )    
    if not product_ids:
        continue
    
    product_pool.write(product_ids, {
        'emotional_short_description': short_description,
        'emotional_description': description,
        })        

