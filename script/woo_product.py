#!/usr/bin/python
# -*- coding: utf-8 -*-
###############################################################################
#
# ODOO (ex OpenERP) 
# Open Source Management Solution
# Copyright (C) 2001-2015 Micronaet S.r.l. (<https://micronaet.com>)
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
from woocommerce import API
import json # for dumps (json encode procedure)


__author__ = 'nicola.riolini@gmail.com'
__title__ = 'odoo-woocommerce-api'
__version__ = '1.0'
__license__ = 'AGPL'

url = 'http://demo8.evoluzionetelematica.it/spaziogiardino.it'
consumer_key = 'ck_f00df6028cc22a7e0bf0b8f4579e5f36bd83866a'
consumer_secret = 'cs_a9998513e0c5f1af1abd74885e90f48e49082a78'

# Dropbox:
dropbox_link = 'https://www.dropbox.com/sh/5ohkk61050eqz50/AADk72HgBY9QW8dOw3UZeYxJa?dl=0'
product_image_link = 'https://www.dropbox.com/sh/5ohkk61050eqz50/AADk72HgBY9QW8dOw3UZeYxJa?dl=0&preview=%s' % 'movida.jpg'

product_image_link_1 = 'https://ucc44285a2ab29896cc37b0e0eed.previews.dropboxusercontent.com/p/thumb/AAbB2K1URjHqpitua6xAUUVjf4mgEPpL8YAQ6UXF7Ylz2nRilOaJo7vWn1pPBqc0lZMPah0hkQwUnENiHl5g8Yrlp6E1MJS2NjZmIhZ-8GCTBLfxozptYHwUyF6dz27iM85xJE1_pEKuJkDWRF6Q-QdfxBPXokmY0nStekjc6Jj-NhEc2G_h3MCU1h6gaWexOj4OqJUWzrwddAbUqQnMQppjOvRrPhSmWXvIZ0TsO8ZMCBbNtTe3hHW5OA1xK00YUjKt-f5JeWIcBDMAw1hHxr1SwU4DNiSIgatolJLE3IPhQCrfKCrxZmgo1Tw6LRZ3acDot45eiZlb6Il7De_bAs5p/p.jpeg?size_mode=5'
product_image_link_2 = 'https://ucffe9a1a34b3412a1fa90776eb5.previews.dropboxusercontent.com/p/thumb/AAb-iy0pdcipYiCDwFSCpBodqhlCw33ipl-NyNc7XB5i09EviIOOtj_Ojvj7SnWDqgtSWA0Stk3DBaApHOuF8dzqpfZn2u0eqCDOtAdeno7r8N7N94tCdqlxO99s6xt7-vmIUqRNSTPHHJWM_R83QqYsgNw-ak4ORu6TBqJFZqA6kmqfcCsoLB8R5Y1lNYj5iqK9950dGG6PZ71IDs5t0bHNve9upGpj4SUCVrqsul94Nbc-fxdRTzSM8MyWO6LdF3whrZosUvahw9GjQmKMNr0nOZGUJZrZ9bfBzsy4cbI8jgWhUmhNKZl6f3jY5G2IhGtrFKddXrXRkuYBsCvR-Y2O/p.jpeg?size_mode=5'
product_image_link_3 = 'https://uc3db04eda324dbd114edd53b7a1.previews.dropboxusercontent.com/p/thumb/AAZjwiaB-UXkNVLIVmlvnsxE3CrQiahMKVWem_Pdkbca6MFS2Qa3iVRi6Z8cEjNViKaKATN0edwBXdKvQIfOPJJG51Ct6KUylYxThpFuG7Zo0El62fP1AV_-HK9xk55kTV4ujSWK3JI9BJDTj5wfVZG0qZKJ15cDIAw9k62x0xrE6cVl8sP4oYggf2LS37_EfQAmTHeXte9esScK2_7-ENWMQdTsSc7Q45ctwK4jg8i15Uuzs26lzZ8RhIP6S7xHolJ8137LHaSHE2oB_-x9vxJgTsy7F_TUGB1xnCmSXhGUXZ9tplS1CvfoCN1lBIAMykt0gF77g_FjVEnesaYc3OkW/p.jpeg?size_mode=5'

wcapi = API(
    url=url,
    consumer_key=consumer_key,
    consumer_secret=consumer_secret,
    wp_api=True,
    version="wc/v3"
    )

# -----------------------------------------------------------------------------
# Product creation:
# -----------------------------------------------------------------------------
data = {
    "name": "Product Movida 3 immagini",
    "type": "simple",
    "regular_price": "21.99",
    "description": "Test prod
    uct via ODOO - Python",
    "short_description": "Short description",
    #"categories": [{"id": 9,},{"id": 14}],
    "images": [
        {
            "src": product_image_link_1,
        },
        {
            "src": product_image_link_2,
        },
        {
            "src": product_image_link_3,
        },
        
    #    {
    #        "src": "http://demo.woothemes.com/woocommerce/wp-content/uploads/sites/56/2013/06/T_2_back.jpg"
    #    }
    ]
    }

# -----------------------------------------------------------------------------
# Product retrieve
# -----------------------------------------------------------------------------
res = wcapi.post('products', data).json()
import pdb; pdb.set_trace()
product_id = res['id']

product = wcapi.get('products/%s' % product_id).json()
print 'ID %s - SKU %s - Name %s\n\n' % (
    product['id'],
    product['sku'],
    product['name'],
    )

# -----------------------------------------------------------------------------
# Product update:
# -----------------------------------------------------------------------------
#data = {
#    "regular_price": "24.54"
#    }
#print(wcapi.put("products/%s" % product_id, data).json())

# -----------------------------------------------------------------------------
# Product list:
# -----------------------------------------------------------------------------
for product in wcapi.get("products").json():
    print 'ID %s - SKU %s - Name %s' % (
        product['id'],
        product['sku'],
        product['name'],
        )

# -----------------------------------------------------------------------------
# Product delete:
# -----------------------------------------------------------------------------
#print(wcapi.delete("products/%s" % product_id).json())

# -----------------------------------------------------------------------------
#Batch update
# -----------------------------------------------------------------------------
"""
data = {
    "create": [
        {},
        {},
        ],
    "update": [
        {"id": 799,
         "default_attributes": [
                {
                    "id": 6,
                    "name": "Color,
                    "option": "Green"
                },
                {
                    "id": 0,
                    "name": "Size",
                    "option": "M"
                }
            ]
        }
    ],
    "delete": [794]
}
print(wcapi.post("products/batch", data).json())
"""

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
