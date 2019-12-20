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
from slugify import slugify


_logger = logging.getLogger(__name__)

class ConnectorServer(orm.Model):
    """ Model name: ConnectorServer
    """    
    _inherit = 'connector.server'

    # -------------------------------------------------------------------------
    # Utility:
    # -------------------------------------------------------------------------
    def get_lang_slug(self, name, lang):
        ''' Slug problem with lang
        '''
        slug = slugify(name)
        return slug + ('' if lang == 'it' else '-en')

    def get_wp_connector(self, cr, uid, ids, context=None):
        ''' Connect with Word Press API management
        '''        
        timeout = 400 # TODO parametrize

        connector = self.browse(cr, uid, ids, context=context)[0]
        if not connector.wordpress:
            _logger.info('Not Wordpress connector')

        _logger.info('>>> Connecting: %s%s API: %s, timeout=%s' % (
            connector.wp_url,
            connector.wp_version,
            connector.wp_api,
            timeout,        
            ))
        try:    
            return woocommerce.API(
                url=connector.wp_url,
                consumer_key=connector.wp_key,
                consumer_secret=connector.wp_secret,
                wp_api=connector.wp_api,
                version=connector.wp_version,
                timeout=timeout, 
                )
        except:
            _logger.error('Cannot connect to Wordpress!!')        

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
    
    def auto_package_assign(self, cr, uid, ids, context=None):
        ''' Auto assign code
        '''
        package_pool = self.pool.get('product.product.web.package')
        for product in self.browse(cr, uid, ids, context=context):
            default_code = product.default_code or ''
            if not default_code:
                _logger.error('No default code, no package assigned!')
                continue

            # -----------------------------------------------------------------            
            # Search:    
            # -----------------------------------------------------------------
            # Mode 6:      
            search_code = '%-6s' % default_code[:6]
            package_ids = package_pool.search(cr, uid, [
                ('name', 'ilike', search_code),
                ], context=context)
            if package_ids:
                self.write(cr, uid, [product.id], {
                    'model_package_id': package_ids[0],
                    }, context=context)    

                _logger.warning('Code 6 "%s" found #%s !' % (
                    search_code, len(package_ids)))
                continue

            # Mode 3:
            search_code = default_code[:3]
            package_ids = package_pool.search(cr, uid, [
                ('name', 'ilike', search_code),
                ], context=context)
            if package_ids:
                self.write(cr, uid, [product.id], {
                    'model_package_id': package_ids[0],
                    }, context=context)
                _logger.warning(
                    'Auto assign package: Code 3 "%s" found #%s !' % (
                        search_code, len(package_ids)))
            else:    
                _logger.error(
                    'Auto assign package: Code not found %s !' % default_code)
        return True

    _columns = {
        # 'wp_id': fields.integer('Worpress ID'),
        # 'wp_lang_id': fields.integer('Worpress translate ID'),
        'emotional_short_description': fields.text(
            'Emozionale breve', translate=True),
        'emotional_description': fields.text(
            'Emozionale dettagliata', translate=True),
        'model_package_id': fields.many2one(
            'product.product.web.package', 'Package'),
        }

class ProductImageFile(orm.Model):
    """ Model name: ProductImageFile
    """

    _inherit = 'product.image.file'

    _columns = {
        'dropbox_link': fields.char('Dropbox link', size=100),
        }

'''class ProductProductWebServerLang(orm.Model):
    """ Model name: ProductProductWebServer ID for lang
    """

    _name = 'product.product.web.server.lang'
    _description = 'Product published with lang'
    _rec_name = 'lang'    
    
    _columns = {
        'web_id': fields.many2one('product.product.web.server', 'Link'),
        'lang': fields.char('Lang code', size=10, required=True),
        'wp_id': fields.integer('WP ID', required=True),
        }
    
    _defaults = {
        # Default value:
        'wp_type': lambda *x: 'simple',
        }    
'''

class ProductProductWebCategory(orm.Model):
    """ Model name: ProductProductWebPackage
    """

    _name = 'product.product.web.category'
    _description = 'Category template'
    _order = 'name'
    
    # -------------------------------------------------------------------------
    # Button event:
    # -------------------------------------------------------------------------
    def update_product_category(self, cr, uid, ids, context=None):
        ''' Update product category for all selected item of this connector
        '''
        line_pool = self.pool.get('product.product.web.server')
        
        current = self.browse(cr, uid, ids, context=context)[0]
        category_ids = [item.id for item in current.category_ids]
        
        line_ids = line_pool.search(cr, uid, [
            ('connector_id', '=', current.connection_id.id),
            ('product_id.default_code', '=ilike', '%s%%' % current.name)
            ], context=context)
            
        if line_ids:
            line_pool.write(cr, uid, line_ids, {
                'wordpress_categ_ids': [(6, 0, category_ids)],
                }, context=context)
            
            _logger.info('Updated %s records' % len(line_ids))                
        return True

    _columns = {
        'connection_id': fields.many2one('connector.server', 'Server', 
            required=True),
        'name': fields.char('Codice padre', size=20, required=True),
        'category_ids': fields.many2many(
            'product.public.category', 'template_web_category_rel', 
            'product_id', 'category_id', 
            'Category', required=True),
        }

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'Nome duplicato!'),
        ]

class ProductProductWebPackage(orm.Model):
    """ Model name: ProductProductWebPackage
    """

    _name = 'product.product.web.package'
    _description = 'Package data'    
    _order = 'name'

    # -------------------------------------------------------------------------
    # Button:
    # -------------------------------------------------------------------------
    def auto_package_assign(self, cr, uid, ids, context=None):
        ''' Auto assign code
        '''
        model_package_id = ids[0]
        current = self.browse(cr, uid, model_package_id, context=context)
        
        product_pool = self.pool.get('product.product')
        product_ids = product_pool.search(cr, uid, [
            ('default_code', '=ilike', '%s%%' % current.name),
            ], context=context)
        _logger.warning('Updating %s product...' % len(product_ids))
        return product_pool.write(cr, uid, product_ids, {
            'model_package_id': model_package_id,
            }, context=context)
    
    _columns = {
        'name': fields.char('Codice padre', size=10, required=True),
        
        'pcs_box': fields.integer('pcs / box'),
        'pcs_pallet': fields.integer('pcs / pallet'),

        'net_weight': fields.integer('Peso netto (gr)'),
        'gross_weight': fields.integer('Peso lordo (gr)'),

        'box_width': fields.integer('Box: larg.'),
        'box_depth': fields.integer('Box: prof..'),
        'box_height': fields.integer('Box: alt.'),

        'pallet_dimension': fields.char('Dim. Pallet', size=30),
        }
        
    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'Nome duplicato!'),
        ]

class ProductProductWebServer(orm.Model):
    """ Model name: ProductProductWebServer
    """

    _inherit = 'product.product.web.server'
    
    # -------------------------------------------------------------------------
    # Utility:
    # -------------------------------------------------------------------------
    def get_existence_for_product(self, product):
        ''' Return real existence for web site
        '''
        stock_quantity = int(product.mx_net_mrp_qty - product.mx_mrp_b_locked)
        # TODO manage q x pack?
        #q_x_pack = product.q_x_pack or 1
        #stock_quantity //= q_x_pack
        if stock_quantity < 0:
            return 0
        return stock_quantity
    
    def get_category_block_for_publish(self, item, lang):
        ''' Get category block for data record WP
        '''     
        categories = []
        for category in item.wordpress_categ_ids:
            wp_id = eval('category.wp_%s_id' % lang)
            wp_parent_id = eval('category.parent_id.wp_%s_id' % lang)
            if not wp_id:
                continue
            categories.append({'id': wp_id })
            if category.connector_id.wp_all_category and category.parent_id:                
                categories.append({'id': wp_parent_id})
        return categories        
        
    # -------------------------------------------------------------------------
    # Button event:
    # -------------------------------------------------------------------------
    '''def clean_reference(self, cr, uid, ids, context=None):
        """ Delete all link
        """
        assert len(ids) == 1, 'Works only with one record a time'
        
        lang_pool = self.pool.get('product.product.web.server.lang')
        lang_ids = lang_pool.search(cr, uid, [
            ('web_id', '=', ids[0]),
            ], context=context)
        return lang_pool.unlink(cr, uid, lang_ids, context=context)    
        '''
        
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

    def wp_clean_code(self, default_code, destination='wp'):
        ''' Return default code for Wordpress
        '''
        if destination == 'wp':        
            return default_code.replace(' ', '&nbsp;')
        else: # odoo    
            return default_code.replace('&nbsp;', ' ')

    def get_wp_price(self, line):
        ''' Extract price depend on force, discount and VAT
        '''
        product = line.product_id
        if line.force_price:
            price = line.force_price
        else:
            price = product.lst_price * (
                100.0 - line.connector_id.discount) / 100.0
            
        price += line.connector_id.add_vat * price / 100.0
        if price < line.connector_id.min_price:
            price = line.connector_id.min_price   

        # ADD approx?         
        return price
 
    def publish_now(self, cr, uid, ids, context=None):
        ''' Publish now button
            Used also for more than one elements (not only button click)
            Note all product must be published on the same web server!            
        '''    
        default_lang = 'it'
        
        if context is None:    
            context = {}

        override_sku = context.get('override_sku', False)

        log_excel = context.get('log_excel', False)
        
        first_proxy = self.browse(cr, uid, ids, context=context)[0]    
        if not first_proxy.connector_id.wordpress:
            _logger.warning('Not a wordpress proxy, call other')
            return super(ProductProductWebServer, self).publish_now(
                cr, uid, ids, context=context)

        # ---------------------------------------------------------------------
        #                         WORDPRESS Publish:
        # ---------------------------------------------------------------------
        _logger.warning('Publish all on wordpress:')
        product_pool = self.pool.get('product.product')
        server_pool = self.pool.get('connector.server')
        #lang_pool = self.pool.get('product.product.web.server.lang')

        wcapi = server_pool.get_wp_connector(
            cr, uid, [first_proxy.connector_id.id], context=context)
        
        #res = wcapi.get("products").json() # XXX list of all products

        # Context used here:
        context_lang = context.copy()

        # Read first element only for setup parameters:        
        connector = first_proxy.connector_id
        context_lang['album_id'] = first_proxy.connector_id.album_id.id
        context['album_id'] = first_proxy.connector_id.album_id.id

        # ---------------------------------------------------------------------
        # Publish image:
        # ---------------------------------------------------------------------
        # TODO (save link)
        
        # ---------------------------------------------------------------------
        # Publish product (lang management)
        # ---------------------------------------------------------------------
        translation_lang = {}

        # First lang = original, second traslate
        for odoo_lang in ('it_IT', 'en_US'):
            lang = odoo_lang[:2] # WP lang
            context_lang['lang'] = odoo_lang  # self._lang_db

            for item in self.browse(cr, uid, ids, context=context_lang):
            
                # Readability:
                product = item.product_id                
                default_code = product.default_code or u''
                if override_sku == False:
                    sku = default_code
                else:    
                    sku = override_sku

                # Description: 
                name = item.force_name or product.name or u''
                description = item.force_description or \
                    product.emotional_description or \
                    product.large_description or u''
                short = product.emotional_short_description or name or u''

                price = u'%s' % self.get_wp_price(item)
                weight = u'%s' % product.weight
                status = 'publish' if item.published else 'private'
                stock_quantity = self.get_existence_for_product(product)
                wp_id = eval('item.wp_%s_id' % lang)
                wp_it_id = item.wp_it_id # Default product for language
                # fabric, type_of_material

                # -------------------------------------------------------------
                # Images block:
                # -------------------------------------------------------------
                images = [] 
                for image in item.wp_dropbox_images_ids:
                    dropbox_link = image.dropbox_link
                    if dropbox_link and dropbox_link.startswith('http'):                        
                        images.append({
                            'src': image.dropbox_link,
                            })

                # -------------------------------------------------------------
                # Category block:
                # -------------------------------------------------------------
                categories = self.get_category_block_for_publish(item, lang)

                # Text data (in lang):
                data = {
                    'name': name,
                    'description': description,
                    'short_description': short,
                    'sku': self.wp_clean_code(sku), # XXX not needed
                    'lang': lang,
                    # It doesn't update:
                    'categories': categories,
                    'wp_type': item.wp_type,
                    }
                if images:
                    data['images'] = images

                if lang == default_lang:
                    # Numeric data:
                    data.update({
                        'type': item.wp_type,
                        #'sku': self.wp_clean_code(sku),
                        'regular_price': price,
                        # sale_price (discounted)
                        'stock_quantity': stock_quantity,
                        'status': status,
                        'catalog_visibility': 'visible', #catalog  search  hidden
                        
                        # Forced in variant:
                        #'weight': weight,
                        #'dimensions': {
                        #   'width': '%s' % product.width, 
                        #   'length': '%s' % product.length,
                        #   'height': '%s' % product.height,
                        #   }, 
                        })
                        
                else: # Other lang (only translation
                    if not wp_it_id: 
                        _logger.error(
                            'Product %s without default IT [%s]' % (
                                lang, default_code))
                        continue    
                    
                    # Translation:
                    data.update({
                        'translations': {'it': wp_it_id},
                        })
                            
                # -------------------------------------------------------------
                #                         Update:
                # -------------------------------------------------------------
                if wp_id:
                    try:
                        call = 'products/%s' % wp_id
                        reply = wcapi.put(call, data).json()

                        if log_excel != False:
                            log_excel.append(('put', call, u'%s' % (data), 
                                u'%s' % (reply)))

                        if reply.get('code') in (                        
                                'product_invalid_sku',
                                'woocommerce_rest_product_invalid_id'):
                            pass # TODO Manage this case?
                            #wp_id = False # will be created after    
                        else:
                            _logger.warning('Product %s lang %s updated!' % (
                                wp_id, lang))                            
                    except:
                        # TODO manage this error if present
                        _logger.error('Not updated ID %s lang %s [%s]!' % (
                            wp_id, lang, data))

                # -------------------------------------------------------------
                #                         Create:
                # -------------------------------------------------------------
                if not wp_id:
                    # Create (will update wp_id from now)
                    try:
                        call = 'products'
                        reply = wcapi.post(call, data).json()
                        if log_excel != False:
                            log_excel.append(('post', call, u'%s' % (data), 
                                u'%s' % (reply)))
                    except: # Timeout on server:
                        _logger.error('Server timeout: %s' % (data, ))
                        continue

                    try:         
                        if reply.get('code') == 'product_invalid_sku':
                            wp_id = reply['data']['resource_id']
                            _logger.error(
                                'Product %s lang %s duplicated [%s]!' % (
                                    wp_id, lang, reply))
                            
                        else:    
                            wp_id = reply['id']
                            _logger.warning('Product %s lang %s created!' % (
                                wp_id, lang))
                    except:
                        raise osv.except_osv(
                            _('Error'), 
                            _('Reply not managed: %s' % reply),
                            )
                        continue    
                    
                    if wp_id:
                        self.write(cr, uid, [item.id], {
                            'wp_%s_id' % lang: wp_id,
                            }, context=context)

                # Save translation of ID (for language product)   
                if default_code not in translation_lang:
                    translation_lang[default_code] = {}
                translation_lang[default_code][lang] = (wp_id, name)
        return translation_lang

    # -------------------------------------------------------------------------
    # Function fields:
    # -------------------------------------------------------------------------
    def _get_album_images(self, cr, uid, ids, fields, args, context=None):
        ''' Fields function for calculate 
        '''     
        res = {}
        for current in self.browse(cr, uid, ids, context=context):
            server_album_ids = [
                item.id for item in current.connector_id.album_ids]
            
            res[current.id] = [
                image.id for image in current.product_id.image_ids \
                    if image.album_id.id in server_album_ids]             
        return res

    def _get_product_detail_items(
            self, cr, uid, ids, fields, args, context=None):
        ''' Fields function for calculate 
        '''    
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id] = {}

            product = line.product_id
            model = product.model_package_id
            if model:
                res[line.id] = {
                    'pack_l': float(model.box_width),
                    'pack_h': float(model.box_height),
                    'pack_p': float(model.box_depth),
                    
                    'weight': float(model.gross_weight) / 1000.0,
                    'weight_net': float(model.net_weight) / 1000.0,

                    'q_x_pack': float(model.pcs_box),
                    'lst_price': product.lst_price,
                    # pallet dimension
                    }
            else:
                res[line.id] = {
                    'pack_l': product.pack_l,
                    'pack_h': product.pack_h,
                    'pack_p': product.pack_p,
                    
                    'weight': product.weight,
                    'weight_net': product.weight_net,

                    'q_x_pack': product.q_x_pack,
                    'lst_price': product.lst_price,
                    }
        return res

    _columns = {
        'wp_it_id': fields.integer('WP it ID'),
        'wp_en_id': fields.integer('WP en ID'),
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
        #'lang_wp_ids': fields.one2many(
        #    'product.product.web.server.lang', 'web_id', 'WD ID'),
        
        # ---------------------------------------------------------------------
        # Product related/linked fields:
        # ---------------------------------------------------------------------
        'model_package_id': fields.related(
            'product_id', 'model_package_id', readonly=1,
            type='many2one', relation='product.product.web.package', 
            string='Modello imballo'),
            
        'pack_l': fields.function(
            _get_product_detail_items, method=True, readonly=1,
            type='float', string='L. Pack', multi=True,
            ), 
        'pack_h': fields.function(
            _get_product_detail_items, method=True, readonly=1,
            type='float', string='H. Pack', multi=True,
            ), 
        'pack_p': fields.function(
            _get_product_detail_items, method=True, readonly=1,
            type='float', string='P. Pack', multi=True, 
            ), 

        'weight': fields.function(
            _get_product_detail_items, method=True, readonly=1,
            type='float', string='Peso lordo', multi=True,
            ), 
        'weight_net': fields.function(
            _get_product_detail_items, method=True, readonly=1,
            type='float', string='Peso netto', multi=True, 
            ), 

        'lst_price': fields.function(
            _get_product_detail_items, method=True, readonly=1,
            type='float', string='Listino', multi=True, 
            ), 

        'q_x_pack': fields.function(
            _get_product_detail_items, method=True, readonly=1,
            type='float', string='Q. x Pack', multi=True,
            ), 

        # ---------------------------------------------------------------------
        # Link related to product
        # ---------------------------------------------------------------------
        'product_pack_l': fields.related(
            'product_id', 'pack_l', type='float', string='Pack L prodotto'),
        'product_pack_h': fields.related(
            'product_id', 'pack_h', type='float', string='Pack H prodotto'),
        'product_pack_p': fields.related(
            'product_id', 'pack_p', type='float', string='Pack P prodotto'),

        'product_weight': fields.related(
            'product_id', 'weight', type='float', string='Peso netto prodotto'),
        'product_weight_net': fields.related(
            'product_id', 'weight_net', type='float', string='Peso lordo prodotto'),

        'product_lst_price': fields.related(
            'product_id', 'lst_price', type='float', string='Listino'),
        'product_q_x_pack': fields.related(
            'product_id', 'q_x_pack', type='float', string='Q x pack prodotto'),
        # ---------------------------------------------------------------------

        'wp_type': fields.selection([
            ('simple', 'Simple product'),
            ('grouped', 'Grouped product'),
            ('external', 'External product'),
            ('variable', 'Variable product'),
            ], 'Wordpress type'),
        }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
