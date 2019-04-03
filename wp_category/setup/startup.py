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

connector_id = 9 # connector.server for wordpress # XXX change!

category_db = [
    ('ARREDAMENTO', [
        'DIVANI',
        'DIVANI LETTO',
        'LIBRERIE',
        'MENSOLE',
        'MOBILI CONTENITORE',
        'POLTRONE E CHAISE LONGUE',
        'POUF',
        'TAVOLI',
        'SEDIE E SGABELLI',
        ]),

    ('ARREDO DA ESTERNO', [
        'SEDIE E SGABELLI DA ESTERNO',
        'TAVOLINI DA ESTERNO',
        'TAVOLI DA ESTERNO',
        'DIVANI E POLTRONE DA ESTERNO',
        'LETTINI, SDRAIO E CHAISE LONGUE',
        'OMBRELLONI',
        'SET DA ESTERNO',
        ]),

    ('ARREDO CAMPING', [
        'SEDIE PIEGHEVOLI',
        'LETTINI',
        ]),

    ('ACCESSORI', [
        'VASI',
        'TESSILE PER LA TAVOLA',
        'CUSCINI E FODERE',
        ]),

    ('CONTRACT', [
        'TAVOLI',
        'SEDIE',
        'DIVANETTI E POLTRONE',
        'ARREDI DA ESTERNO',
        ]),
    ]

# -----------------------------------------------------------------------------
# Read configuration parameter:
# -----------------------------------------------------------------------------
# From config file:
cfg_file = os.path.expanduser('../local.cfg')
#cfg_file = os.path.expanduser('../openerp.cfg')

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
sequence = 0

category_pool = odoo.model('product.public.category')
for category, sub in category_db:
    sequence += 10
    name = category.title()

    parent_id = category_pool.create({
        'enabled': True,
        'name': name,
        'sequence': sequence,
        'parent_id': False,
        'connector_id': connector_id,        
        }).id
    for child in sub:
        name = child.title()
        sequence += 10
        category_pool.create({
            'enabled': True,
            'name': name,
            'sequence': sequence,
            'parent_id': parent_id,
            'connector_id': connector_id,        
            })
            
        
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
