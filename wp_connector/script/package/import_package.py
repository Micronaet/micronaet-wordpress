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


file_in = './package.xls'
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
    
# Pool used:
package_pool = odoo.model('product.product.web.package')

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
previous_ids = package_pool.search([])
#if web_ids:
#    print 'Set unpublish all product for this connector, # %s' % len(web_ids)
#    web_pool.write(web_ids, {
#        'published': False,
#        })
        
# -----------------------------------------------------------------------------
# Create from files:
# -----------------------------------------------------------------------------
i = 0
for row in range(row_start, WS.nrows):
    i += 1

    # Mapping:
    name = WS.cell(row, 0).value.upper()
    
    pcs_box = WS.cell(row, 1).value or False
    pcs_pallet = WS.cell(row, 2).value or False

    net_weight = WS.cell(row, 3).value or False
    gross_weight = WS.cell(row, 4).value or False

    box_width = WS.cell(row, 5).value or False
    box_depth = WS.cell(row, 6).value or False
    box_height = WS.cell(row, 7).value or False

    pallet_dimension = WS.cell(row, 8).value or False

    if len(name) == 5:
        name += ' '

    package_ids = package_pool.search([
        ('name', '=', name),
        ])

    # -------------------------------------------------------------------------
    #                         Web selection:
    # -------------------------------------------------------------------------
    data = {
        'name': name,
        'pcs_box': pcs_box,
        'pcs_pallet': pcs_pallet,
        'net_weight': net_weight,
        'gross_weight': gross_weight,
        'box_width': box_width,
        'box_depth': box_depth,
        'box_height': box_height,
        'pallet_dimension': pallet_dimension,
        }
    
    if package_ids:
        print '%s. Aggiornamento: %s' % (i, name)
        package_pool.write(package_ids, data)
    else:    
        print '%s. Creazione: %s' % (i, name)
        package_pool.create(data)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
