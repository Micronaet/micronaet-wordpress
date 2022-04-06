import os
import woocommerce
import pickle
import urllib
import sys
import erppeek
import ConfigParser

# -----------------------------------------------------------------------------
# Read configuration parameter:
# -----------------------------------------------------------------------------
mode = 'openerp' # 'local'
company_list = ['fia', 'gpb']
lang_list = ['it_IT', 'en_US']
connector_id = 0 # TODO?

# -----------------------------------------------------------------------------
# Pool read:
# -----------------------------------------------------------------------------
pools = {}
for company in company_list:
    pools[company] = {}
    pools[company]['product'] = {}
    pools[company]['web_product'] = {}


# -----------------------------------------------------------------------------
# Worpress parameters:
# -----------------------------------------------------------------------------
config = ConfigParser.ConfigParser()
cfg_file = os.path.expanduser('../wordpress.cfg')
config.read([cfg_file])
wordpress_url = config.get('wordpress', 'url')
consumer_key = config.get('wordpress', 'key')
consumer_secret = config.get('wordpress', 'secret')

# -----------------------------------------------------------------------------
# ODOO Parameters:
# -----------------------------------------------------------------------------
for company in company_list: #['fia', 'gpb']:
    cfg_file = os.path.expanduser('../%s.%s.cfg' % (mode, company))
    config.read([cfg_file])
    dbname = config.get('dbaccess', 'dbname')
    user = config.get('dbaccess', 'user')
    pwd = config.get('dbaccess', 'pwd')
    server = config.get('dbaccess', 'server')
    port = config.get('dbaccess', 'port')   # verify if it's necessary: getint

    # -------------------------------------------------------------------------
    # Connect to ODOO:
    # -------------------------------------------------------------------------
    odoo = erppeek.Client(
        'http://%s:%s' % (server, port),
        db=dbname, user=user, password=pwd,
        )

    # Pool used:
    pools[company]['product'] = odoo.model('product.product')
    pools[company]['web_product'] = odoo.model('product.product.web.server')

# -----------------------------------------------------------------------------
# Collect master - slave data from 2 DB
# -----------------------------------------------------------------------------
odoo_product = {}
for company in company_list:
    # Search italian web master
    select_pool = pools[company]['web_product']
    web_product_ids = select_pool.search([
        ('wp_parent_template', '=', True),
        ])
    total = len(web_product_ids)
    i = 0
    for master in select_pool.browse(web_product_ids):
        i += 1
        if i % 10 == 0:
            print('Read %s product %s of %s' % (company, i, total))
        for wp_lang, wp_id in (
                ('it', master.wp_it_id), ('en', master.wp_en_id),
                ('es', master.wp_es_id), ('fr', master.wp_fr_id),
                ('de', master.wp_de_id)):

            odoo_product[wp_id] = [
                wp_lang,
                master.product_id.default_code,
                company,
                master.product_id,
                master.variant_ids,
                ]

# -----------------------------------------------------------------------------
# Update category:
# -----------------------------------------------------------------------------
# Spaziogiardino
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

wp_all = []
wp_unlink = []
parameter = {
    'per_page': 10,
    'page': 1,
    }
while True:
    reply = wcapi.get('products', params=parameter).json()
    print 'WP Page read:', parameter['page']
    parameter['page'] += 1

    try:
        if reply.get['data']['status'] >= 400:
            print 'Error getting product', reply
            break
    except:
        pass # Records present

    if not reply:
        break

    for record in reply:
        wp_id = record['id']
        lang = record['lang']
        sku = record['sku']

        if wp_id in odoo_product:
            wp_all.append(wp_id)
        else:
            wp_unlink.append(wp_id)
            print('To be unlinked: %s' % sku)

        # TODO check variations:

# Unlink WP product master:
print('Unlinking...', wp_unlink)
for wp_id in wp_unlink:
    print(wcapi.delete('products/%s' % wp_id, params={'force': True}).json())

# Not found:
for odoo_id in set(odoo_product) - set(wp_all):
    print('Not yet published', odoo_product[odoo_id][2],
          odoo_product[odoo_id][1])

    # TODO reset wp_it_id wp_en_id
    # TODO Publish single

