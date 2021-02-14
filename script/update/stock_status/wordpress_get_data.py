import os
import woocommerce
import codecs
import pickle
import urllib
import sys
import pdb
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
    """ Log activity on file
    """
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
#                                Spaziogiardino
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
variant_check_double = []
master_variant_list = []

parameter = {'per_page': 40, 'page': 1}
total = 0

double_lang_f = {
    'it': codecs.open('./log/it.double.csv', 'w', 'utf8'),
    'en': codecs.open('./log/en.double.csv', 'w', 'utf8'),
    '': codecs.open('./log/controllo.csv', 'w', 'utf8'),
}

while True:
    print('Reading page %s [Block %s]' % (
        parameter['page'], parameter['per_page']))

    call = 'products'
    reply = wcapi.get(call, params=parameter)
    parameter['page'] += 1

    if reply.status_code >= 300:
        print('Error getting product list', reply.text)
        sys.exit()

    json_reply = reply.json()
    if not json_reply:
        break

    pdb.set_trace()
    for record in json_reply:
        product_id = record['id']
        lang = record['lang']
        sku = record['sku'].replace('&nbsp;', ' ')
        print('    - SKU:', sku, '    Lang:', lang)
        images = record.get('images', False)

        if lang not in variant_db:
            variant_db[lang] = {}

        variation_parameter = {'per_page': 50, 'page': 1}  # Only one call!
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
        for variation in variation_reply.json():
            total += 1
            variation_id = variation['id']

            variation_sku = variation['sku'].replace('&nbsp;', ' ')
            try:
                variation_image = variation['image']
            except:
                variation_image = False

            # -----------------------------------------------------------------
            # Variation color for fabric:
            variant_color = 'NESSUNO'
            try:
                for item in variation['attributes']:
                    if item['id'] != 1:
                        continue
                    variant_color = item['option']
            except:
                variant_color = 'ERRORE'
            double_f = double_lang_f[lang]
            double_f.write(u'%s | %s | %s\n' % (
                sku,
                variation_sku,
                variant_color,
            ))
            double_f.flush()
            key = (lang, sku, variation_sku, variant_color)
            if key in master_variant_list:
                double_lang_f[''].write(u'%s\n' % (key, ))
                double_lang_f[''].flush()
            else:
                master_variant_list.append(key)
            # -----------------------------------------------------------------

            if variation_sku in variant_db[lang]:
                variant_check_double.append((lang, variation_sku))
            variant_db[lang][variation_sku] = {
                'product_id': product_id,
                'product_sku': sku,
                'variation_id': variation_id,
                'variation_sku': variation_sku,
                'product_images': images,
                'variation_image': variation_image,
                }
            print(
                '%s Variant loading ...' % total, 'Variation:', variation_sku)
            # variant_db[lang][variation_sku]

log_activity('Update dump file [%s]' % pickle_file)
pickle.dump(variant_db, open(pickle_file, 'wb'))
log_activity('End get Wordpress product status [%s]' % wordpress_url)

# Save master dump file:
pickle.dump(master_db, open(pickle_master_file, 'wb'))
for comment, filename, double_list in (
        ('master', 'double_master.txt', master_check_double),
        ('variant', 'double_variant.txt', variant_check_double),
        ):
    print('Doppioni %s:' % comment)

    double_f = open('./log/%s' % filename, 'w')
    for record in double_list:
        double_f.write('[%s] %s\n' % record)
    double_f.close()

# TODO clean double variant!
