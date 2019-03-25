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
    "name": "Product ODOO #5",
    "type": "simple",
    "regular_price": "21.99",
    "description": "Test product via ODOO - Python",
    "short_description": "Short description",
    #"categories": [{"id": 9,},{"id": 14}],
    #"images": [
    #    {
    #        "src": "http://demo.woothemes.com/woocommerce/wp-content/uploads/sites/56/2013/06/T_2_front.jpg"
    #    },
    #    {
    #        "src": "http://demo.woothemes.com/woocommerce/wp-content/uploads/sites/56/2013/06/T_2_back.jpg"
    #    }
    #]
    }

# -----------------------------------------------------------------------------
# Product retrieve
# -----------------------------------------------------------------------------
res = wcapi.post('products', data).json()
product_id = res['id']

product = wcapi.get('products/%s' % product_id).json()
print 'ID %s - SKU %s - Name %s' % (
    product['id'],
    product['sku'],
    product['name'],
    )

# -----------------------------------------------------------------------------
# Product update:
# -----------------------------------------------------------------------------
data = {
    "regular_price": "24.54"
    }

print(wcapi.put("products/%s" % product_id, data).json())

# -----------------------------------------------------------------------------
# Product list:
# -----------------------------------------------------------------------------
#print(wcapi.get("products").json())
for product in wcapi.get("products").json():
    print 'ID %s - SKU %s - Name %s' % (
        product['id'],
        product['sku'],
        product['name'],
        )

# -----------------------------------------------------------------------------
# Product delete:
# -----------------------------------------------------------------------------
print(wcapi.delete("products/%s" % product_id).json())

# -----------------------------------------------------------------------------
# Product list:
# -----------------------------------------------------------------------------
#print(wcapi.get("products").json())
for product in wcapi.get("products").json():
    print 'ID %s - SKU %s - Name %s' % (
        product['id'],
        product['sku'],
        product['name'],
        )

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

print(wcapi.get("customers").json())


        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
