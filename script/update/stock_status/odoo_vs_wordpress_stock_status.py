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
import pdb
import erppeek
import woocommerce
import ConfigParser
import pickle

import smtplib
from email.MIMEMultipart import MIMEMultipart
from email.mime.text import MIMEText

from datetime import datetime

verbose = False  # Log with extra data
vat_rate = 1.22
lang_db = ['it_IT', 'en_US']
database = {}
for root, folders, files in os.walk('./config'):
    for filename in files:
        if filename == 'wordpress.cfg':
            continue
        company = filename.split('.')[0]
        database[company] = os.path.join(root, filename)
    break

pickle_file = './log/wp_data.p'
variant_db = pickle.load(open(pickle_file, 'rb'))

activity_file = './log/activity.log'
activity_f = open(activity_file, 'a')


def log_activity(event, mode='info'):
    """ Log activity on file
    """
    activity_f.write('%s [%s] %s\n' % (
        datetime.now(),
        mode.upper(),
        event,
        ))


# -----------------------------------------------------------------------------
# WP web read: Spaziogiardino
# -----------------------------------------------------------------------------
# Worpress parameters:
config = ConfigParser.ConfigParser()
cfg_file = os.path.expanduser('./config/wordpress.cfg')
config.read([cfg_file])
wordpress_url = config.get('wordpress', 'url')
consumer_key = config.get('wordpress', 'key')
consumer_secret = config.get('wordpress', 'secret')
log_activity('Start update stock in Wordpress [%s]' % wordpress_url)

smtp_to = config.get('smtp', 'to')

wcapi = woocommerce.API(
    url=wordpress_url,
    consumer_key=consumer_key,
    consumer_secret=consumer_secret,
    wp_api=True,
    version='wc/v3',
    query_string_auth=True,
    timeout=600,
    )

# -----------------------------------------------------------------------------
# Read configuration parameter:
# -----------------------------------------------------------------------------
empty_stock = []
for company in database:
    cfg_file = database[company]

    # From config file:
    config = ConfigParser.ConfigParser()
    config.read([cfg_file])
    dbname = config.get('dbaccess', 'dbname')
    user = config.get('dbaccess', 'user')
    pwd = config.get('dbaccess', 'pwd')
    server = config.get('dbaccess', 'server')
    port = config.get('dbaccess', 'port')  # verify if it's necessary: getint
    connector_id = eval(config.get('dbaccess', 'connector_id'))

    # -------------------------------------------------------------------------
    # Connect to ODOO:
    # -------------------------------------------------------------------------
    odoo = erppeek.Client(
        'http://%s:%s' % (
            server, port),
        db=dbname,
        user=user,
        password=pwd,
        )

    for lang in lang_db:
        wp_lang = lang[:2]
        odoo.context = {'lang': lang}
        web_product_pool = odoo.model('product.product.web.server')

        web_product_ids = web_product_pool.search([
            ('wp_parent_template', '=', True),
            ])

        for master in web_product_pool.browse(web_product_ids):
            """
            multipack = str(int(variation.price_multi)) \
                if variation.price_multi and variation.price_multi > 1 \
                    else ''
                    
            data = {
                'lang': wp_lang,
                'stock_quantity': stock_quantity,
                'manage_stock': True,
                # Visibility:
                'status': status,
                #'multipack': multipack,
                
                #'stock_status': 'instock', 
                # instock (def.), outofstock, onbackorder
                }                

            # -------------------------------------------------------------
            # Variation update:
            # -------------------------------------------------------------
            call = 'products/%s' % (product_id)

            continue
            """
            for variation in master.variant_ids:
                product = variation.product_id
                default_code = product.default_code  # .replace(' ', '&nbsp;')
                if variation.published:
                    status = 'publish'
                else:
                    status = 'private'
                    print('Unpublished: %s' % default_code)

                if default_code not in variant_db[wp_lang]:
                    print('Master code not found: %s' % default_code)
                    continue

                wp_data = variant_db[wp_lang][default_code]
                product_id = wp_data['product_id']
                variation_id = wp_data['variation_id']

                # XXX Problem with this:
                stock_quantity, stock_comment = \
                    web_product_pool.get_existence_for_product(variation.id)

                # Empty stock mail collect data:
                if wp_lang == 'it':
                    empty_stock.append((
                        company, default_code, product.name,
                        status, stock_quantity, stock_comment,
                    ))
                continue  # TODO remove
                multiplier = variation.price_multi or 1
                if multiplier > 1:
                    stock_quantity = stock_quantity // multiplier

                # XXX Usually disabled:
                multipack = str(int(variation.price_multi)) \
                    if variation.price_multi and variation.price_multi > 1 \
                        else ''

                # Price part:
                price = web_product_pool.get_wp_price_external(variation.id)
                sale_price = u'%s' % (
                        (variation.force_discounted / vat_rate) or '')
                # TODO Always 0:
                # sale_price = variation.wp_web_discounted_net or ''

                # -------------------------------------------------------------
                # Stock data:
                # -------------------------------------------------------------
                data = {
                    'lang': wp_lang,

                    # Stock status:
                    'stock_quantity': stock_quantity,
                    'manage_stock': True,

                    # Price:
                    'regular_price': u'%s' % price,
                    'sale_price': u'%s' % sale_price,

                    # Visibility:
                    'status': status,
                    # 'multipack': multipack,
                    # 'stock_status': 'instock',
                    # instock (def.), outofstock, onbackorder

                    # TODO update more other things?
                    }
                if sale_price:
                    print('Update: %s %s %s' % (
                        default_code, price, sale_price))

                # -------------------------------------------------------------
                # Variation update:
                # -------------------------------------------------------------
                call = 'products/%s/variations/%s' % (
                    product_id, variation_id)
                reply = wcapi.put(call, data)
                if reply.status_code >= 300:
                    print('Error publish stock status: %s, [%s: %s]\n\n%s' % (
                        default_code, call, data,
                        reply.text if verbose else ''))
                else:
                    print('Update %s with stock status: %s [%s: %s]\n%s\n' % (
                        default_code, stock_quantity,  call, data,
                        reply.text if verbose else ''))

log_activity('End update stock in Wordpress [%s]' % wordpress_url)

# -----------------------------------------------------------------------------
# SMTP Sent:
# -----------------------------------------------------------------------------
pdb.set_trace()
if not empty_stock:
    print('No empty stock!')
    sys.exit()

# Parameters:
smtp_subject = 'Segnalazione prodotti Wordpress senza esistenza'
smtp_text_html = ''

for record in empty_stock:
    smtp_text_html += '<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>' \
                      '%s</td><td>%s</td></tr>' % record

# Add table:
smtp_text_html = '''
    <table>
        <tr>
            <th><b>Azienda</b></th>
            <th><b>Codice</b></th>
            <th><b>Nome</b></th>
            <th><b>Stato</b></th>
            <th><b>Q.</b></th>
            <th><b>Calcolo</b></th>
        </tr>%s
    </table>''' % smtp_text_html

# -----------------------
# Get mail server option:
# -----------------------
mailer = odoo.model('ir.mail_server')
mailer_ids = mailer.search([])
if not mailer_ids:
    print('[ERR] No mail server configured in ODOO')
    sys.exit()

odoo_mailer = mailer.browse(mailer_ids)[0]

# Open connection:
print('[INFO] Sending using "%s" connection [%s:%s]' % (
    odoo_mailer.name,
    odoo_mailer.smtp_host,
    odoo_mailer.smtp_port,
    ))

if odoo_mailer.smtp_encryption in ('ssl', 'starttls'):
    smtp_server = smtplib.SMTP_SSL(
        odoo_mailer.smtp_host, odoo_mailer.smtp_port)
else:
    print('[ERR] Connect only SMTP SSL server!')
    sys.exit()

smtp_server.login(odoo_mailer.smtp_user, odoo_mailer.smtp_pass)
for to in smtp_to.replace(' ', '').split(','):
    print('Sending mail to: %s ...' % to)
    msg = MIMEMultipart()
    msg['Subject'] = smtp_subject
    msg['From'] = odoo_mailer.smtp_user
    msg['To'] = smtp_to
    msg.attach(MIMEText(smtp_text_html, 'html'))

    # No attachment for now:
    # part = MIMEBase('application', 'octet-stream')
    # part.set_payload(open(fullname, 'rb').read())
    # Encoders.encode_base64(part)
    # part.add_header(
    #    'Content-Disposition', 'attachment; filename="%s"' % filename)
    # msg.attach(part)

    # Send mail:
    smtp_server.sendmail(odoo_mailer.smtp_user, to, msg.as_string())

smtp_server.quit()
