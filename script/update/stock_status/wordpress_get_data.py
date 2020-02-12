import os
import woocommerce
import pickle
import urllib
import sys
import erppeek
import ConfigParser
import pickle

# -----------------------------------------------------------------------------
# Read configuration parameter:
# -----------------------------------------------------------------------------
pickle_file = './log/wp_data.p'

company_list = ['fia', 'gpb']
lang_list = ['it_IT', 'en_US']

connector_id = 0 # TODO?
config = ConfigParser.ConfigParser()

# Worpress parameters:
cfg_file = os.path.expanduser('./config/wordpress.cfg')
config.read([cfg_file])
wordpress_url = config.get('wordpress', 'url')
consumer_key = config.get('wordpress', 'key')
consumer_secret = config.get('wordpress', 'secret')

for root, folders, files in os.path('./config'):
    for filename in files:
        if filename == 'wordpress.cfg':
            continue
        company = database.split('.')[0]       
        database[company] = os.path.join(root, filename)
    break    


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
parameter = {'per_page': 30, 'page': 1}
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

pickle.dump(variant_db, open(pickle_file, 'wb'))
