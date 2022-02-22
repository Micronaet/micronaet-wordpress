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
verbose = False

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
# Connect to ODOO:
# -----------------------------------------------------------------------------
odoo = erppeek.Client(
    'http://%s:%s' % (
        server, port),
    db=dbname,
    user=user,
    password=pwd,
    )

# Pool used (in lang mode):
'''
odoo_lang = {}
odoo.context = {'lang': 'it_IT'}
odoo_lang['it'] = odoo.model('connector.product.color.dot')
odoo.context = {'lang': 'en_US'}
odoo_lang['en'] = odoo.model('connector.product.color.dot')
'''
odoo_lang = odoo.model('connector.product.color.dot')

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
        data = {}
        comment = ''
        hint = ''

        # ---------------------------------------------------------------------
        # Image data:
        # ---------------------------------------------------------------------
        term_id = record['id']
        name = record['name']
        name = name[:-3]  # no -it
        odoo_name = name  # Name is this
        # Transfor for image name:
        name = name.strip()
        name = name.replace(' ', '%20')
        name = name.replace('.png', '')

        image = record.get('color_image', False)
        if not image and lang == 'it':
            comment += '[Update image] '
            # Update image only if not present and it Lang!
            data.update({
                'lang': 'it',
                'color_image':
                    'http://my.fiam.it/upload/images/dot_point/%s.png' % name,
                })

        # ---------------------------------------------------------------------
        # ODOO Data:
        # ---------------------------------------------------------------------
        odoo_ids = odoo_lang.search([('name', '=', odoo_name)])
        if odoo_ids:
            if lang == 'it':
                odoo.context = {'lang': 'it_IT'}
                odoo_lang = odoo.model('connector.product.color.dot')
            else:
                odoo.context = {'lang': 'en_US'}
                odoo_lang = odoo.model('connector.product.color.dot')

            dot = odoo_lang.browse(odoo_ids)[0]
            hint = dot.hint
            if hint and hint != record['color_name']:
                comment += '[Update hint %s]' % hint
                data.update({
                    'id': term_id,
                    'description': '',
                    'name': record['name'],
                    'lang': lang,
                    'color_name': hint,
                    })

        # ---------------------------------------------------------------------
        # Update command:
        # ---------------------------------------------------------------------
        if not data:
            #print 'NOT updated %s' % odoo_name
            continue

        call = 'products/attributes/%s/terms/%s' % (
            attribute_id, term_id,
            )

        reply = wcapi.put(call, data)
        print 'UPDATE |%s| WP |%s| ODOO |%s| >> HINT |%s| COMMENT: |%s|' % (
            lang,
            record['name'],
            odoo_name,
            hint,
            comment,
            )
        if verbose:
            print 'wcapi.put(%s, %s) >> %s\n\n' % (call, data, reply.json())

