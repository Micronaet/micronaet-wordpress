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
company = 'fia'
connector_id = 5

# -----------------------------------------------------------------------------
# Load all pool:
# -----------------------------------------------------------------------------
# Single company:
config = ConfigParser.ConfigParser()
cfg_file = os.path.expanduser('../openerp.%s.cfg' % company)
config.read([cfg_file])
dbname = config.get('dbaccess', 'dbname')
user = config.get('dbaccess', 'user')
pwd = config.get('dbaccess', 'pwd')
server = config.get('dbaccess', 'server')
port = config.get('dbaccess', 'port')   # verify if it's necessary: getint

table = {
    company: {},
    }
for lang in lang_db:
    wp_lang = lang[:2]
    table[company][wp_lang] = {}

    # -------------------------------------------------------------------------
    # Connect to ODOO:
    # -------------------------------------------------------------------------
    odoo = erppeek.Client(
        'http://%s:%s' % (server, port),
        db=dbname, user=user, password=pwd,
        )
    odoo.context = {'lang': lang}

    # Pool used:
    pool = odoo.model('connector.product.color.dot')
    color_ids = pool.search([])
    for color in pool.browse(color_ids):
        table[company][wp_lang][color.name] = color

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
    verify_ssl=False,  # 03/10/2021 problem with new format of CA
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
odoo_selection = {
    'it': table[company]['it'].keys(),
    'en': table[company]['en'].keys(),
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
        wp_lang = record['lang']
        slug = record['name']
        name = record['name'][:-3]


        color = table[company][wp_lang].get(name)
        if not color:
            print 'Color in WP not in ODOO %s' % name
        else:
            #print record
            if name in odoo_selection[wp_lang]:
                print 'Removed [%s] %s' % (wp_lang, name)
                odoo_selection[wp_lang].remove(name)

print 'To create:'
print odoo_selection

translation_id = {}
#link = 'http://my.fiam.it/upload/images/dot_colors/%s.png'
for lang in ['it', 'en']:
    for color in odoo_selection[lang]:
        name = '%s-%s' % (color, lang)
        call = 'products/attributes/%s/terms' % attribute_id

        data = {
            'name': name,
            'lang': lang,
            'color_name': table[company]['it'][color].hint,
            #'color_image': link,
            }
        if lang != 'it':
            data.update({
                'translations': {'it': translation_id[color]}
                })

        reply = wcapi.post(call, data=data)
        wp_check_reply(reply)
        if lang == 'it':
            translation_id[color] = reply.json()['id']

"""        
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

        image = record.get('color_image', False)
        if image:
            #print 'No need to update: %s' % name
            pass # XXX continue            
            
        # Update image:        
        data = {
            'lang': 'it',
            'color_image': 
                'http://my.fiam.it/upload/images/dot_point/%s.png' % name,
            }
        call = 'products/attributes/%s/terms/%s' % (
            attribute_id, term_id,                
            )

        reply = wcapi.put(call, data)
        print 'wcapi.put(%s, %s) >> %s\n\n' % (call, data, reply.json())


            for attribute in lang_color_db[lang]:
                key = attribute[:-3] # Key element (without -it or -en)
                odoo_color = fabric_color_odoo[attribute]
                item = {
                    'name': attribute,
                    'lang': lang,
                    'color_name': odoo_color.hint,
                    }

                # Image part:
                if odoo_color.dropbox_image:
                    item['color_image'] = odoo_color.dropbox_image
                    
                if lang != default_lang: # Different language:
                    # TODO correct 
                    wp_it_id = lang_color_terms[default_lang].get(key)
                    if wp_it_id:
                        item.update({
                            'translations': {'it': wp_it_id}
                            })
                    else:
                        _logger.error('Attribute not found %s %s!' % (
                            key,
                            lang,
                            ))
                        # TODO manage?
"""
