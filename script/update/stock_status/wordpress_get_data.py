import os
import woocommerce
import pickle
import urllib
import sys
import erppeek
import ConfigParser
import pickle
from datetime import datetime

# -----------------------------------------------------------------------------
# Read configuration parameter:
# -----------------------------------------------------------------------------
pickle_file = './log/wp_data.p'
pickle_master_file = './log/wp_master_data.p'
activity_file = './log/activity.log'
activity_f = open(activity_file, 'a')

def log_activity(event, mode='info'):
    ''' Log activity on file
    '''
    activity_f.write('%s [%s] %s\n' % (
        datetime.now(),
        mode.upper(),
        event,
        ))

# Worpress parameters:
config = ConfigParser.ConfigParser()
cfg_file = os.path.expanduser('./config/wordpress.cfg')
config.read([cfg_file])
wordpress_url = config.get('wordpress', 'url')
consumer_key = config.get('wordpress', 'key')
consumer_secret = config.get('wordpress', 'secret')
log_activity('Start get Wordpress product status [%s]' % wordpress_url)

# -----------------------------------------------------------------------------
# Spaziogiardino
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

# -----------------------------------------------------------------------------
# Get product - variant status:
# -----------------------------------------------------------------------------
variant_db = {}
master_db = {}
master_check_double = []

parameter = {'per_page': 40, 'page': 1}
total = 0

while True:
    print 'Reading page %s [Block %s]' % (
        parameter['page'], parameter['per_page'])

    call = 'products'
    reply = wcapi.get(call, params=parameter)
    parameter['page'] += 1

    if reply.status_code >= 300:
        print 'Error getting product list', reply.text
        sys.exit()

    json_reply = reply.json()
    if not json_reply:
        break

    for record in json_reply:
        product_id = record['id']
        lang = record['lang']
        sku = record['sku'].replace('&nbsp;', ' ')
        print '    - SKU:', sku, '    Lang:', lang
        images = record.get('images', False)

        if lang not in variant_db:
             variant_db[lang] = {}

        variation_parameter = {'per_page': 50, 'page': 1} # Only one call!
        call = 'products/%s/variations' % product_id
        variation_reply = wcapi.get(call, params=variation_parameter)

        # ---------------------------------------------------------------------
        # Master part:
        # ---------------------------------------------------------------------
        if lang not in master_db:
             master_db[lang] = {}
        if sku in master_db[lang]:  # Yet present
            master_check_double.append((lang, sku))
        master_db[lang][sku] = product_id
        continue # TODO remove
        for variation in variation_reply.json():
            total += 1
            variation_id = variation['id']

            variation_sku = variation['sku'].replace('&nbsp;', ' ')
            variation_image = variation.get('image', False)

            variant_db[lang][variation_sku] = {
                'product_id': product_id,
                'product_sku': sku,
                'variation_id': variation_id,
                'vriation_sku': variation_sku,
                'product_images': images,
                'variation_image': variation_image,
                }
            print '%s Variant loading ...' % total, 'Variation:', variation_sku
            # variant_db[lang][variation_sku]

log_activity('Update dump file [%s]' % pickle_file)
pickle.dump(variant_db, open(pickle_file, 'wb'))
log_activity('End get Wordpress product status [%s]' % wordpress_url)

# Save master dump file:
pickle.dump(master_db, open(pickle_master_file, 'wb'))

print 'Doppioni:'
print '%s' % (master_check_double, )
