import os
import woocommerce
import pickle
import urllib
import sys
import erppeek
import ConfigParser
import shutil
import requests

def clean(name):
    """ Clean file name
    """
    return name.replace('&nbsp;', ' ')


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
    )

parameter = {'per_page': 50, 'page': 1}

import pdb; pdb.set_trace()
while True:
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
        images = record['images']

        for image in images:
            import pdb; pdb.set_trace()
            url = urllib.quote(image['src'].encode('utf8'), ':/')
            # image_name = image['name']
            image_id = image['id']
            jpg_name = os.path.join(image_path, '%s.jpg' % sku)
            filename = clean(os.path.join(image_path, jpg_name))

            response = requests.get(url, stream=True)
            with open(filename, 'wb') as out_file:
                shutil.copyfileobj(response.raw, out_file)
