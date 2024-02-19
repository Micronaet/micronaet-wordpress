import os
import woocommerce
import pickle
import urllib
import sys
import erppeek
import ConfigParser
import shutil
import pdb
import requests


dryrun = False
demo = False


def clean(name):
    """ Clean file name
    """
    name = name.replace('&nbsp;', ' ')
    name = name.replace('_', ' ')
    return name


# -----------------------------------------------------------------------------
# Read configuration parameter:
# -----------------------------------------------------------------------------
# From config file:
cfg_file = os.path.expanduser('../wordpress.cfg')
config = ConfigParser.ConfigParser()

config.read([cfg_file])
wordpress_url = config.get('wordpress', 'url')
consumer_key = config.get('wordpress', 'key')
consumer_secret = config.get('wordpress', 'secret')
image_path = config.get('wordpress', 'path')
# os.system('mkdir -p %s' % image_path)


# CAPI call:
wcapi = woocommerce.API(
    url=wordpress_url,
    consumer_key=consumer_key,
    consumer_secret=consumer_secret,
    wp_api=True,
    version='wc/v3',
    query_string_auth=False,
    timeout=600,
    verify_ssl=False,
    )
parameter = {'per_page': 50, 'page': 1}
variation_parameter = {'per_page': 100, 'page': 1}

log_f = open(os.path.join(image_path, 'log.csv'), 'w')
pickle_filename = './history.pickle'
try:
    history = pickle.load(open(pickle_filename, 'rb'))
except:
    history = {}

if not history:
    # Setup
    history['product'] = {}
    # history['product'] = {}

run = True
pdb.set_trace()
while run:
    reply = wcapi.get('products', params=parameter)
    parameter['page'] += 1

    try:
        if not reply.ok:
            print('Error getting category list', reply)
            break
    except:
        pass  # Records present

    records = reply.json()
    if not records:
        break

    for record in records:
        # ---------------------------------------------------------------------
        # Extract data from record:
        # ---------------------------------------------------------------------
        wp_id = record['id']
        sku = record['sku']
        print('Reading %s' % sku)
        images = []  # todo restore (Remove parent):  record['images']
        history['product'][sku] = {}

        # Child:
        variations = wcapi.get(
            'products/%s/variations' % wp_id, params=variation_parameter)
        for variation in variations.json():
            images = variation['image']
            images.append(image)

        print(images)
        for image in images:
            url = urllib.quote(image['src'].encode('utf8'), ':/')
            image_name = clean(image['name'])
            if image_name[-4:].upper() != '.JPG':
                image_name = '%s.jpg' % image_name

            log_f.write('%s|%s|%s\n' % (
                image_name,
                image['id'],
                image['date_modified'],
                ))

            image_id = image['id']
            filename = os.path.join(image_path, image_name)
            if os.path.isfile(filename):
                print('>> File presente %s' % filename)
                continue
            else:
                print('>> File scaricato %s' % filename)

            # Call as HTTP
            # url = 'http%s' % (url.replace('https', ''))
            response = requests.get(url, stream=True)
            history['product'][sku][image_id] = image
            if not dryrun:
                with open(filename, 'wb') as out_file:
                    shutil.copyfileobj(response.raw, out_file)
                if demo:
                    run = False
                    break

try:
    pickle.dump(history, open(pickle_filename, 'wb'))
except:
    history = {}
