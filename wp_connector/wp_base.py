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

class ConnectorServer(orm.Model):
    """ Model name: ConnectorServer
    """    
    _inherit = 'connector.server'

    def get_wp_connector(self, cr, uid, context=None):
        ''' Connect with Word Press API management
        '''
        assert len(ids) == 1, 'Works only with one record a time'
        
        connector = self.browse(cr, uid, ids, context=context)[0]
        if not connector.wordpress:
            _logger.info('Not Wordpress connector')
        
        return woocommerce.API(
            url=connector.wp_url,
            consumer_key=connector.wp_key,
            consumer_secret=connector.wp_secret,
            wp_api=True,
            version="wc/v3"
            )

    _columns = {
        'wordpress': fields.boolean('Wordpress', help='Wordpress web server'),

        'wp_url': fields.char('WP URL', size=180),
        'wp_key': fields.char('WP consumer key', size=180),
        'wp_secret': fields.char('WP consumer secret', size=180),
        
        'wp_api': fields.boolean('WP API'),
        'wp_version': fields.char('WP Version', size=10),
        }
    
    _defaults = {
        'wp_api': lambda *x: True,
        'wp_version': lambda *x: 'wc/v3',        
        }

class ProductProduct(orm.Model):
    """ Model name: ProductProduct
    """

    _inherit = 'product.product'
    
    _columns = {
        'wp_id': fields.integer('Worpress ID'),
        }

class ProductProductWebServer(orm.Model):
    """ Model name: ProductProductWebServer
    """

    _inherit = 'product.product.web.server'
    
    def publish_now(self, cr, uid, ids, context=None):
        ''' Publish now button
            Used also for more than one elements (not only button click)
            Note all product must be published on the same web server!            
        '''    
        if context is None:    
            context = {}

        first_proxy = self.browse(cr, uid, ids, context=context)[0]        
        if not first_proxy.connector_id.wordpress:
            _logger.warning('Not a wordpress proxy, call other')
            super(ProductProductWebServer, self).publish_now(
                cr, uid, ids, context=context)

        # ---------------------------------------------------------------------
        #                         WORDPRESS Publish:
        # ---------------------------------------------------------------------
        _logger.warning('Publish all on wordpress:')
        product_pool = self.pool.get('product.product')
        server_pool = self.pool.get('connector.server')

        wcapi = server_pool.get_wp_connector(cr, uid, context=context)
        
        # Context used here:
        db_context = context.copy()
        db_context['lang'] = self._lang_db

        # Read first element only for setup parameters:        
        connector = first_proxy.connector_id
        db_context['album_id'] = first_proxy.connector_id.album_id.id
        context['album_id'] = first_proxy.connector_id.album_id.id

        # ---------------------------------------------------------------------
        # Publish image:
        # ---------------------------------------------------------------------
        # TODO (save link)
        
        # ---------------------------------------------------------------------
        # Publish product (lang management)
        # ---------------------------------------------------------------------
        for item in self.browse(cr, uid, ids, context=db_context):
            product = item.product_id
            default_code = product.default_code
            name = item.force_name or product.name
            description = item.force_description or product.large_description
            short = name
            price = item.force_price or product.lst_price

            wp_id = product.wp_id
            # fabric
            # type_of_material

                        
            data = {
                'name': name,
                'type': 'simple',
                'regular_price': price,
                'description': description,
                'short_description': name,
                'sku': default_code,
                #"categories": [{"id": 9,},{"id": 14}],
                #"images": [
                #    {"src": product_image_link_1,},
                #    {"src": product_image_link_2,},
                #    {"src": product_image_link_3,},
                #    ]
                }
            
            # TODO manage error and wp_id (could be created but not saved!
            if wp_id:
                reply = wcapi.put('products/%s' % wp_id, data).json()
            else:
                reply = wcapi.post('products', data).json()
                wp_id = reply['id']
                
                # Update product WP ID:
                product_pool.write(cr, uid, [product.id], {
                    'wp_id': wp_id,
                    }, context=context)
                
            
    
        """for lang in self._langs:  
            #if lang == self._lang_db:
            #    continue # no default lang, that create object!
                
            db_context['lang'] = lang
            for item in self.browse(cr, uid, ids, context=db_context):
                product = item.product_id
                default_code = product.default_code

                #    'name': item.force_name or product.name,
                #    'description_sale': 
                #        item.force_description or product.large_description,
                #    'fabric': product.fabric,
                #    'type_of_material': product.type_of_material,
        """

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
