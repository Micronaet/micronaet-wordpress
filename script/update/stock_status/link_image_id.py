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

# -----------------------------------------------------------------------------
# Get product - variant status:
# -----------------------------------------------------------------------------
import pdb; pdb.set_trace()
variant_db = pickle.load(open(pickle_file, 'rb'))
master_ids = []
for sku in variant_db['it']:  # Keep only IT image
    product_id = variant_db['it'][sku]['product_id']
    sku = variant_db['it'][sku]['product_sku']
    variation_id = variant_db['it'][sku]['variation_id']
    variation_sku = variant_db['it'][sku]['variation_sku']
    product_images = variant_db['it'][sku]['product_images']
    variation_image = variant_db['it'][sku]['variation_image']

    if product_id not in master_ids:
        master_ids.append(product_id)
        # Manage master images
        for record_image in product_images:
            name = record_image['name']
            id = record_image['id']

    # Variation image:
    name = variation_image['name']
    id = variation_image['id']

    # Find sku in database
