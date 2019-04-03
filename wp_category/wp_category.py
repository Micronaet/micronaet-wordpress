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

    def publish_category_now(self, cr, uid, ids, context=None):
        ''' Publish now button
            Used also for more than one elements (not only button click)
            Note all product must be published on the same web server!            
            '''
        '''
        if context is None:    
            context = {}

        _logger.warning('Publish category all on wordpress:')
        
            
        # ---------------------------------------------------------------------
        #                         WORDPRESS Publish:
        # ---------------------------------------------------------------------
        product_pool = self.pool.get('product.product')
        server_pool = self.pool.get('connector.server')

        wcapi = server_pool.get_wp_connector(
            cr, uid, [first_proxy.connector_id.id], context=context)

        for record in wcapi.get("products/categories").json():
            wp_id = record['id']
            name = record['name']





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
        # First lang = original, second traslate
        for lang in ('it_IT', 'en_US'): #self._langs:  
            db_context['lang'] = lang
                
            for item in self.browse(cr, uid, ids, context=db_context):
                product = item.product_id
                default_code = product.default_code or u''
                name = item.force_name or product.name or u''
                description = item.force_description or \
                    product.large_description or u''
                short = name
                price = u'%s' % (item.force_price or product.lst_price)
                weight = u'%s' % product.weight
                status = 'publish' if item.published else 'private'
                stock_quantity =\
                    int(product.mx_net_mrp_qty - product.mx_mrp_b_locked)
                if stock_quantity < 0:
                    stock_quantity = 0
                # fabric
                # type_of_material

                wp_id = product.wp_id
                wp_lang_id = product.wp_lang_id
                
                # -------------------------------------------------------------
                # Images block:
                # -------------------------------------------------------------
                images = [] 
                for image in item.wp_dropbox_images_ids:
                    if image.dropbox_link:
                        images.append({
                            'src': image.dropbox_link,
                            })

                # -------------------------------------------------------------
                # Category block:
                # -------------------------------------------------------------
                # TODO 
                categories = [] #[{"id": 9,},{"id": 14}]
                
                data = {
                    'name': name,
                    'type': u'simple',
                    'regular_price': price,
                    'description': description,
                    'short_description': name,
                    'sku': default_code,
                    'weight': weight,
                    'stock_quantity': stock_quantity,
                    'status': status,
                    'catalog_visibility': 'visible', #catalog  search  hidden
                    'dimensions': {
                       'width': '%s' % product.width, 
                       'length': '%s' % product.length,
                       'height': '%s' % product.height,
                       }, 
                    
                    'categories': categories,
                    'images': images,
                    }

                if lang != 'it_IT':
                    data['translation_of'] = wp_id
                    data['lang'] = 'en'
                    data['sku'] = '%s_en' % data['sku']
                    
                    # To update or write:
                    item_id = wp_lang_id
                    field = 'wp_lang_id'
                else:
                    item_id = wp_id
                    field = 'wp_id'
                                    
                # TODO manage error and wp_id (could be created but not saved!
                if item_id:
                    try:
                        reply = wcapi.put('products/%s' % item_id, data).json()
                        _logger.warning('Product %s lang %s updated!' % (
                            item_id, lang))
                    except:
                        # TODO Check this error!!!!!!
                        _logger.error('Not updated product %s lang %s!' % (
                            item_id, lang))
                        
                else:
                    reply = wcapi.post('products', data).json()
                    try:
                        return_id = reply['id']
                        _logger.warning('Product %s lang %s created!' % (
                            return_id, lang))
                    except:
                        raise osv.except_osv(
                            _('Errore'), 
                            _('Non connesso al server WP: %s' % reply),
                            )
                    
                    # Update product WP ID:
                    product_pool.write(cr, uid, [product.id], {
                        field: return_id,
                        }, context=context)
        '''    

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
