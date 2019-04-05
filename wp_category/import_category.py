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
import logging
import openerp
import json
import woocommerce
import openerp.netsvc as netsvc
import openerp.addons.decimal_precision as dp
from openerp.osv import fields, osv, expression, orm
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp import SUPERUSER_ID, api
from openerp import tools
from openerp.tools.translate import _
from openerp.tools.float_utils import float_round as round
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT, 
    DEFAULT_SERVER_DATETIME_FORMAT, 
    DATETIME_FORMATS_MAP, 
    float_compare)


_logger = logging.getLogger(__name__)

class ProductPublicCategory(orm.Model):
    """ Model name: ProductProduct
    """

    _inherit = 'product.public.category'
    
    _columns = {
        'wp_id': fields.integer('Worpress ID'),
        }

class ProductPublicCategory(orm.Model):
    """ Model name: ProductProduct
    """

    _inherit = 'connector.server'

    def publish_category_now(self, cr, uid, ids, context=None):
        ''' Publish now button
            Used also for more than one elements (not only button click)
            Note all product must be published on the same web server!            
            '''
        if context is None:    
            context = {}

        server_id = ids[0]
        _logger.warning('Publish category all on wordpress:')
        
        # ---------------------------------------------------------------------
        #                         WORDPRESS Publish:
        # ---------------------------------------------------------------------
        product_pool = self.pool.get('product.product')
        server_pool = self.pool.get('connector.server')
        category_pool = self.pool.get('product.public.category')
        
        # ---------------------------------------------------------------------
        # Read WP category:
        # ---------------------------------------------------------------------
        data = {
            'create': [],
            'update': [],
            #'delete': [],
            }

        wcapi = server_pool.get_wp_connector(cr, uid, server_id, context=context)
        wp_db = {}
        for record in wcapi.get("products/categories").json():
            wp_db[record['id']] = record['name']
        
        # ---------------------------------------------------------------------
        # Read ODOO category parent:
        # ---------------------------------------------------------------------
        odoo_db = {}
        category_ids = category_pool.search(cr, uid, [
            ('parent_id', '=', False),
            ('connector_id', '=', server_id),
            ], context=context)    
        import pdb; pdb.set_trace()
        for category in category_pool.browse(
                cr, uid, category_ids, context=context):    
            wp_id = category.wp_id            
            odoo_id = category.id
            name = category.name
            
            wp_data = {
                'name': name,
                'parent': 0,
                'menu_order': category.sequence,
                'display': 'default',
                #'description': '',
                #'count': 36,
                #"id": 9,
                #"slug": "clothing",
                #"image": {
                #  "id": 730,
                #  "date_created": "2017-03-23T00:01:07",
                #  "date_created_gmt": "2017-03-23T03:01:07",
                #  "date_modified": "2017-03-23T00:01:07",
                #  "date_modified_gmt": "2017-03-23T03:01:07",
                #  "src": "https://example.com/wp-content/uploads/2017/03/T_2_front.jpg",
                #  "name": "",
                #  "alt": ""
                #},
                #"_links": {
                #  "self": [
                #    {
                #      "href": "https://example.com/wp-json/wc/v3/products/categories/9"
                #    }
                #  ],
                #  "collection": [
                #    {
                #      "href": "https://example.com/wp-json/wc/v3/products/categories"
                #    }
                #  ]
                }

            # Check if present :
            if wp_id in wp_db: # Update
                wp_data['id'] = wp_id
                data['update'].append(wp_data)
                try:
                    del(wp_db[wp_id])
                except:
                    pass # yet deleted (from Front end?)
    
            else: # Create:
                data['create'].append(wp_data)
                odoo_db[name] = odoo_id
                    
        data['delete'] = wp_ids.keys()
        res = wcapi.post("products/categories/batch", data).json()
        
        # Update category with WP ID:
        for record in res['create']:
            name = record['name']
            odoo_id = odoo_db.get(name, False)
            if not odoo_id:
                _logger.error('Not Updated wp_id for %s' % name)
                continue
                
            category_pool.write(cr, uid, odoo_id, {
                'wp_id': record['id'],
                }, context=context)
            _logger.info('Updated wp_id for %s' % name)
      
        # TODO      
        # Check updated
        # Check deleted
        # Update product first category?
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
