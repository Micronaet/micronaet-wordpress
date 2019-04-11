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

    def get_wp_connector(self, cr, uid, ids, context=None):
        ''' Connect with Word Press API management
        '''        
        connector = self.browse(cr, uid, ids, context=context)[0]
        if not connector.wordpress:
            _logger.info('Not Wordpress connector')

        return woocommerce.API(
            url=connector.wp_url,
            consumer_key=connector.wp_key,
            consumer_secret=connector.wp_secret,
            wp_api=connector.wp_api,
            version=connector.wp_version,
            timeout=10, # TODO parametrize
            )

    _columns = {
        'wordpress': fields.boolean('Wordpress', help='Wordpress web server'),

        'wp_all_category': fields.boolean('All category', 
            help='Public all product with category and parent also'),
        'wp_url': fields.char('WP URL', size=180),
        'wp_key': fields.char('WP consumer key', size=180),
        'wp_secret': fields.char('WP consumer secret', size=180),
        
        'wp_api': fields.boolean('WP API'),
        'wp_version': fields.char('WP Version', size=10),

        'album_ids': fields.many2many(
            'product.image.album', 
            'connector_album_rel', 'server_id', 'album_id', 'Album'),
        'wp_category': fields.selection([
            ('out', 'ODOO Original WP replicated'),
            ('in', 'WP Original ODOO replicated'),
            ], 'Category management', required=True),
        }
    
    _defaults = {
        'wp_api': lambda *x: True,
        'wp_version': lambda *x: 'wc/v3',        
        'wp_category': lambda *x: 'out',
        'wp_all_category': lambda *x: True,
        }

class ProductProduct(orm.Model):
    """ Model name: ProductProduct
    """

    _inherit = 'product.product'
    
    _columns = {
        'wp_id': fields.integer('Worpress ID'),
        'wp_lang_id': fields.integer('Worpress translate ID'),
        }

class ProductImageFile(orm.Model):
    """ Model name: ProductImageFile
    """

    _inherit = 'product.image.file'

    _columns = {
        'dropbox_link': fields.char('Dropbox link', size=100),
        }

class ProductProductWebServerLang(orm.Model):
    """ Model name: ProductProductWebServer ID for lang
    """

    _name = 'product.product.web.server.lang'
    _description = 'Product published with lang'
    
    _columns = {
        'web_id': fields.many2one('product.product.web.server', 'Link'),
        'lang': fields.char('Lang code', size=10, required=True),
        'wp_id': fields.integer('WP ID', required=True),
        }

class ProductProductWebServer(orm.Model):
    """ Model name: ProductProductWebServer
    """

    _inherit = 'product.product.web.server'
    
    # Utility:
    def get_existence_for_product(self, product):
        ''' Return real existence for web site
        '''
        stock_quantity = int(product.mx_net_mrp_qty - product.mx_mrp_b_locked)
        if stock_quantity < 0:
            return 0
        return stock_quantity    
        
    def open_image_list_product(self, cr, uid, ids, context=None):
        '''
        '''
        model_pool = self.pool.get('ir.model.data')
        view_id = model_pool.get_object_reference(
            cr, uid, 
            'wp_connector', 'view_product_product_web_server_form')[1]
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Image detail'),
            'view_type': 'form',
            'view_mode': 'form,form',
            'res_id': ids[0],
            'res_model': 'product.product.web.server',
            'view_id': view_id, # False
            'views': [(view_id, 'form'), (False, 'tree')],
            'domain': [],
            'context': context,
            'target': 'new',
            'nodestroy': False,
            }

    def publish_now(self, cr, uid, ids, context=None):
        ''' Publish now button
            Used also for more than one elements (not only button click)
            Note all product must be published on the same web server!            
        '''    
        default_lang = 'it_IT'
        
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

        wcapi = server_pool.get_wp_connector(
            cr, uid, [first_proxy.connector_id.id], context=context)
        
        # Context used here:
        db_context = context.copy()
        db_context['lang'] = self._lang_db

        # Read first element only for setup parameters:        
        connector = first_proxy.connector_id
        db_context['album_id'] = first_proxy.connector_id.album_id.id
        context['album_id'] = first_proxy.connector_id.album_id.id
        
        wp_all_category = connector.wp_all_category

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
            translation_of = False
                
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
                
                # Read Wordpress ID in lang:
                lang_wp_ids = {}
                for lang in product.lang_wb_ids:                
                    lang_wp_ids[lang.name] = lang.wp_id
                    # Default lang reference for translated product:
                    if lang == default_lang:
                        translation_of = lang.wp_id
                
                stock_quantity = self.get_existence_for_product(product)
                # fabric
                # type_of_material

                # Wordpress ID in lang to update:
                wp_id = product.get(lang, False) 

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
                categories = []
                for category in item.wordpress_categ_ids:
                    if not category.wp_id:
                        continue
                    categories.append({'id': category.wp_id })
                    if wp_all_category and category.parent_id:
                        categories.append({'id': category.parent_id.wp_id })

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
                
                if lang != default_lang:
                    data['translation_of'] = translation_of
                    wp_lang = lang[:2] #'en'
                    data['lang'] = wp_lang
                    data['sku'] = '%s_%s' % (data['sku'], wp_lang)

                # TODO manage error and wp_id (could be created but not saved!
                #  MANAGE {u'message': u'SKU non valido o duplicato', u'code': u'product_invalid_sku', u'data': {u'status': 400, u'resource_id': 70}}")
                if wp_id:
                    try:
                        reply = wcapi.put('products/%s' % wp_id, data).json()
                        _logger.warning('Product %s lang %s updated!' % (
                            wp_id, lang))
                    except:
                        # TODO Check this error!!!!!!
                        _logger.error('Not updated product %s lang %s!' % (
                            wp_id, lang))
                        
                else:
                    reply = wcapi.post('products', data).json()
                    try:
                        returned_id = reply['id']
                        _logger.warning('Product %s lang %s created!' % (
                            return_id, lang))
                    except:
                        raise osv.except_osv(
                            _('Errore'), 
                            _('Non connesso al server WP: %s' % reply),
                            )
                    
                    # Update product WP ID:
                    item_pool.create(cr, uid, {
                        'web_id': item.id,
                        'name': lang,
                        'wp_id': returned_id,
                        }, context=context)

    # -------------------------------------------------------------------------
    # Function fields:
    # -------------------------------------------------------------------------
    def _get_album_images(self, cr, uid, ids, fields, args, context=None):
        ''' Fields function for calculate 
        '''     
        assert len(ids) == 1, 'Works only with one record a time'  

        this_image = self.browse(cr, uid, ids, context=context)[0]
        res = {}
        server_album_ids = [
            item.id for item in this_image.connector_id.album_ids]
        
        res[ids[0]] = [
            image.id for image in this_image.product_id.image_ids \
                if image.album_id.id in server_album_ids]             
        return res        

    _columns = {
        'wordpress_categ_ids': fields.many2many(
            'product.public.category', 'product_wp_rel', 
            'product_id', 'category_id', 
            'Wordpress category'),
        'wp_dropbox_images_ids': fields.function(
            _get_album_images, method=True, obj='product.image.file',
            type='one2many', string='Album images', 
            store=False),                        
        'wordpress': fields.related(
            'connector_id', 'wordpress', 
            type='boolean', string='Wordpress'),    
        'lang_wp_ids': fields.one2many(
            'product.product.web.server.lang', 'web_id', 'WD ID'),
        }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
