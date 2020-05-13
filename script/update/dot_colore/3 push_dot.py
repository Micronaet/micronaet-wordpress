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

attribute_name = 'Tessuto'
lang_db = ['it_IT', 'en_US']
default_lang = 'it'

# Fiam:
connector_id = 5

# -----------------------------------------------------------------------------
# Utility:
# -----------------------------------------------------------------------------
def wp_check_reply(reply):
    """ reply correct over 300
    """
    try:
        if reply.status_code >= 300:        
            print 'Error from server!'
            sys.exit()
    except:
        print 'Error unmanaged in reply!'
        sys.exit()
    

# -----------------------------------------------------------------------------
# Read configuration parameter:
# -----------------------------------------------------------------------------
# Worpress parameters:
config = ConfigParser.ConfigParser()
cfg_file = os.path.expanduser('../wordpress.cfg')
config.read([cfg_file])
wordpress_url = config.get('wordpress', 'url')
consumer_key = config.get('wordpress', 'key')
consumer_secret = config.get('wordpress', 'secret')

# From config file:
cfg_file = os.path.expanduser('../openerp.fia.cfg')
config = ConfigParser.ConfigParser()
config.read([cfg_file])
dbname = config.get('dbaccess', 'dbname')
user = config.get('dbaccess', 'user')
pwd = config.get('dbaccess', 'pwd')
server = config.get('dbaccess', 'server')
port = config.get('dbaccess', 'port')   # verify if it's necessary: getint

# -----------------------------------------------------------------------------
# WP web read: Spaziogiardino
# -----------------------------------------------------------------------------
wcapi = woocommerce.API(
    url=wordpress_url,
    consumer_key=consumer_key,
    consumer_secret=consumer_secret,
    wp_api=True,
    version='wc/v3',
    query_string_auth=True,
    timeout=600,
    )

wp_attribute = {}

parameter = {
    'per_page': 20,
    'page': 0,
    }
while True:
    parameter['page'] += 1
    call = 'products/attributes'
    reply = wcapi.get(call, params=parameter)#.json()

    wp_check_reply(reply)
    records = reply.json()
    if not records:
        break

    for record in records:
        if record['name'] == attribute_name:
            attribute_id = record['id']
            break    
            
    if attribute_id:
        break

parameter = {
    'per_page': 30,
    'page': 0,
    }

while True:
    parameter['page'] += 1    
    call = 'products/attributes/%s/terms' % attribute_id    
    reply = wcapi.get(call, params=parameter)

    # Retrieve all Fabric attribute:
    wp_check_reply(reply)
    records = reply.json()
    if not records:
        break

    for record in records:
        item_id = record['id']
        lang = record['lang']
        if lang != 'it':
            continue # only italian!
        term_id = record['id']
        name = record['name']
        name = name[:-3] # no -it
        name = name.strip()
        name = name.replace(' ', '%20')
        name = name.replace('.png', '')
        import pdb; pdb.set_trace()

        image = record.get('color_image', False)
        data = {
            #'name': attribute,
            #'lang': lang,
            #'color_name': odoo_color.hint,
            }
        if not image:
            # Update image:        
            data.update({
                'lang': 'it',
                'color_image': 
                    'http://my.fiam.it/upload/images/dot_point/%s.png' % name,
                })
        if not data:
            continue
        
        call = 'products/attributes/%s/terms/%s' % (
            attribute_id, term_id,                
            )

        reply = wcapi.put(call, data)
        print 'wcapi.put(%s, %s) >> %s\n\n' % (call, data, reply.json())

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
