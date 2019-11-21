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

class ProductProduct(orm.Model):
    """ Model name: ProductProduct
    """

    _inherit = 'product.product'
    
    _columns = {
        'wp_parent_template': fields.boolean(
            'Template for variants', 
            help='Product used as tempalte for variants (first six char of '
                'code)'),
        }
    
class ProductPublicCategory(orm.Model):
    """ Model name: ProductProduct
    """

    _inherit = 'connector.server'

    def publish_attribute_now(self, cr, uid, ids, context=None):
        ''' Publish now button
            Used also for more than one elements (not only button click)
            Note all product must be published on the same web server!            
            '''
        def split_code(default_code):
            ''' Split 2 part of code
            '''   
            default_code = (default_code or '')[:12] # No exta part
            res = (
                default_code[:6].strip(),
                '%s-%s' % (
                    default_code[6:8].strip().upper() or 'NE', # XXX Neutro
                    default_code[8:].strip().upper(),
                    ),
                )
            return res    
        
        # ---------------------------------------------------------------------
        # Handle connector:
        # ---------------------------------------------------------------------
        default_lang = 'it'

        if context is None:    
            context = {}

        # Pool used:
        server_pool = self.pool.get('connector.server')
        web_product_pool = self.pool.get('product.product.web.server')

        connector_id = ids[0]
        server_proxy = self.browse(cr, uid, connector_id, context=context)

        # Read WP Category present:
        wcapi = server_pool.get_wp_connector(
            cr, uid, connector_id, context=context)

        _logger.warning('Publish attribute all on wordpress:')

        # ---------------------------------------------------------------------
        #                          COLLECT DATA: 
        # ---------------------------------------------------------------------
        product_ids = web_product_pool.search(cr, uid, [
            ('connector_id', '=', ids[0]),
            
            # -----------------------------------------------------------------
            # XXX REMOVE:
            #('product_id.default_code', '=ilike', '005TX   O%'),
            ('product_id.default_code', '=ilike', '127TX%'),
            ('product_id.default_code', 'not ilike', '____________S'),
            # -----------------------------------------------------------------
            ], context=context)
        _logger.warning('Product for this connector: %s...' % len(product_ids))

        # TODO update product as variant: (XXX all product or only template?)
        web_product_pool.write(cr, uid, product_ids, {
            'wp_type': 'variable',
            }, context=context)
        
        product_db = {}
        attribute_db = []
        company_name = False # For brand

        for record in sorted(web_product_pool.browse(cr, uid, product_ids, 
                context=context), 
                key=lambda x: x.product_id.wp_parent_template, reverse=True):

            # First is the template (if present)
            product = record.product_id
            if not company_name:
                company_name = product.company_id.name.upper().split()[0] # XXX
                
            default_code = product.default_code or ''
            if not default_code[:3].isdigit(): # TODO MT and TL?
                _logger.warning('Not used %s' % default_code)
                continue

            product_parent, product_attribute = split_code(default_code)
            if product_attribute not in attribute_db:
                attribute_db.append(product_attribute)
            
            if product_parent not in product_db:
                product_db[product_parent] = [
                    record, # Web line with template product
                    [], # Variant product
                    ]
            else: # First record became product, other variants:     
                product_db[product_parent][1].append(
                    (record, product_attribute))
            # Extract frame-color from code

        # ---------------------------------------------------------------------        
        #                     ATTRIBUTES: (need Tessuto, Brand)
        # ---------------------------------------------------------------------   
        current_wp_attribute = wcapi.get('products/attributes').json()

        error = ''
        try:
            if current_wp_attribute['data']['status'] >= 400:
                error = current_wp_attribute['message']
        except:
            pass

        if error:    
            raise osv.except_osv(_('Connection error:'), error)

        # ---------------------------------------------------------------------        
        # Search Tessuto attribute:
        # ---------------------------------------------------------------------        
        attribute_id = {
            'Tessuto': False,
            'Brand': False,
            }
        _logger.warning('Searching attribute %s...' % (attribute_id.keys() ))
        for record in current_wp_attribute:
            if record['name'] in attribute_id:
                attribute_id[record['name']] = record['id']
        
        if not all(attribute_id.values()):
            raise osv.except_osv(
                _('Attribute error'), 
                _('Cannot find attribute %s!') % (attribute_id, ),
                )        

        # ---------------------------------------------------------------------        
        #                        TERMS: (for Tessuto Attribute)
        # ---------------------------------------------------------------------        
        current_wp_terms = []
        theres_data = True
        parameter = {'per_page': 10, 'page': 1}
        _logger.warning('Search all terms for attribute %s...' % (
            attribute_id.keys(), ))

        while theres_data:
            res = wcapi.get(
                'products/attributes/%s/terms' % attribute_id['Tessuto'], 
                params=parameter).json()
            parameter['page'] += 1

            try:
                if res.get['data']['status'] >= 400:
                    raise osv.except_osv(
                        _('Category error:'), 
                        _('Error getting category list: %s' % (res, ) ),
                        )
            except:
                pass # Records present            
            if res:
                current_wp_terms.extend(res)
            else:
                theres_data = False

        web_attribute = {}
        for record in current_wp_terms:
            web_attribute[(record['name'], record['lang'])] = record['id']

        # ---------------------------------------------------------------------
        # Update / Create:
        # ---------------------------------------------------------------------
        for lang in ('it', 'en'):
            # Clean every loop:
            data = {
                'create': [],
                'update': [],
                'delete': [],
                }
            for attribute in attribute_db:
                name = attribute + ('' if lang == 'it' else '-en') # XXX remove?
                item = {
                    'name': name,
                    'lang': lang,
                    # 'color': # XXX RGP color
                    }
                    
                if lang != default_lang: # Different language:
                    wp_it_id = web_attribute.get((attribute, default_lang))
                    if wp_it_id:
                        item.update({
                            'translations': {'it': wp_it_id}
                            })
                    else:
                        _logger.error('Attribute not found %s %s!' % (
                            attribute,
                            lang,
                            ))
                        # TODO manage?
                        
                if (name, lang) in web_attribute:
                    pass # data['update'].append(item) # no data to update
                else:
                    data['create'].append(item)

            # -----------------------------------------------------------------
            # Delete:
            # -----------------------------------------------------------------
            # XXX Not for now:
            #for name in web_attribute:
            #    if name not in attribute_db:
            #        data['delete'].append(web_attribute[name])

            # -----------------------------------------------------------------
            # Batch operation:
            # -----------------------------------------------------------------
            try:
                if any(data.values()): # only if one is present
                    res = wcapi.post(
                        'products/attributes/%s/terms/batch' % \
                            attribute_id['Tessuto'], 
                        data=data,
                        ).json()
                    
                    # ---------------------------------------------------------
                    # Save WP ID (only in dict not in ODOO Object)
                    # ---------------------------------------------------------
                    for record in res.get('create', ()):
                        wp_id = record['id']
                        if not wp_id: # TODO manage error:
                            _logger.error('Not Updated wp_id for %s' % wp_id)
                            continue

                        # Update for next language:
                        # name = attribute + ('' if lang == 'it' else '.') # XXX remove?
                        web_attribute[(record['name'], lang)] = wp_id 
            except:
                raise osv.except_osv(
                    _('Error'), 
                    _('Wordpress server not answer, timeout!'),
                    )
    
        # ---------------------------------------------------------------------        
        #                       PRODUCT AND VARIATIONS:
        # ---------------------------------------------------------------------
        translation_lang = {}
        parent_unset = []
        for parent in product_db:
            for odoo_lang in ('it_IT', 'en_US'):
                lang = odoo_lang[:2]
                context_lang = context.copy()
                context_lang['lang'] = odoo_lang
            
                web_product, variants = product_db[parent]
                product = web_product.product_id
                default_code = product.default_code
                if not product.wp_parent_template:
                    parent_unset.append(parent)
                    continue
            
                # -------------------------------------------------------------
                # TEMPLATE PRODUCT: Upload product reference:
                # -------------------------------------------------------------
                # 1. Call upload original procedure:
                translation_lang.update(
                    web_product_pool.publish_now(
                        cr, uid, [web_product.id], context=context_lang))
                wp_id = translation_lang.get(default_code, {}).get(lang)
                return True
                
                # Setup default attribute:
                parent_parent, parent_attribute = split_code(default_code)
                data = {'default_attributes': [{
                    'id': attribute_id['Tessuto'],
                    'option': parent_attribute,
                    }]}
                reply = wcapi.put('products/%s' % wp_id, data).json()
                
                if not wp_id:
                    _logger.error(
                        'Cannot found wp_id, code %s' % default_code)
                    # XXX Cannot update!
                    continue

                # -----------------------------------------------------------------
                # VARIANTS: Creation
                # -----------------------------------------------------------------
                # 2. Update attributes:
                data = {'attributes': [{
                    'id': attribute_id['Tessuto'], 
                    #'name': 'Tessuto',
                    'options': [],
                    #'name': variant_attribute,
                    'variation': True,
                    }]}                
                for line, variant_attribute in variants:
                    variant = line.product_id
                    data['attributes'][0]['options'].append(variant_attribute)
                    
                try:
                    res = wcapi.post('products/%s' % wp_id, data=data).json()
                except:
                    raise osv.except_osv(
                        _('Error'), 
                        _('Wordpress server not answer, timeout!'),
                        )
                
                # -----------------------------------------------------------------
                # Upload product variations:
                # -----------------------------------------------------------------
                variations_web = wcapi.get('products/%s/variations' % wp_id).json()
                
                data = {
                    'delete': [],
                    }

                #current_variation = {}
                variation_ids = {}
                for item in variations_web:
                    # No option
                    if not item['attributes'] or not item['attributes'][0][
                            'option']:
                        data['delete'].append(item['id'])
                    else:
                        #current_variation[
                        #    item['attributes'][0]['option']] = item['id']
                        variation_ids[item['sku']] = item['id']

                # Clean variation no color:
                if data['delete']:
                    wcapi.post('products/%s/variations/batch' % wp_id, data).json()

                # Get all variations:
                res = wcapi.get('products/%s/variations' % wp_id).json()

                for line, fabric_code in variants:
                    variant = line.product_id
                    variant_code = variant.default_code
                    # Create or update variation:
                    # XXX Price for S (ingle)

                    data = {
                        'sku': variant_code,
                        'price': u'%s' % (line.force_price or variant.lst_price),
                        'short_description': 
                            line.force_name or variant.name or u'',
                        'description': line.force_description or \
                            variant.large_description or u'',
                        # TODO
                        # stock_quantity
                        # stock_status
                        # weight
                        # dimensions
                        'stock_quantity': 
                            web_product_pool.get_existence_for_product(variant),
                        'status': 'publish' if line.published else 'private',
                        
                        'attributes': [{
                            'id': attribute_id['Tessuto'], 
                            'option': fabric_code,
                            }]
                        }
                    # -------------------------------------------------------------
                    # Images block:
                    # -------------------------------------------------------------
                    images = [] 
                    position = 0
                    for image in line.wp_dropbox_images_ids:                  
                        if image.dropbox_link:
                            position += 1
                            images.append({
                                'src': image.dropbox_link,
                                'position': position,
                                # name
                                # alt
                                })
                    if images:
                        data['image'] = images # XXX Raise error

                    variation_id = variation_ids.get(variant_code, False)
                    if variation_id: # Update
                        operation = 'UPD'
                        res = wcapi.put('products/%s/variations/%s' % (
                            wp_id,
                            variation_id,
                            ), data).json()                        
                        #del(current_variation[fabric_code]) XXX for clean operat.
                    else: # Create
                        operation = 'NEW'
                        res = wcapi.post(
                            'products/%s/variations' % wp_id, data).json()
                        try:
                            variation_id = res['id']
                        except:
                            variation_id = '?'    

                    if res.get('data', {}).get('status', 0) >= 400:
                        _logger.error('%s Variant: %s [%s] >> %s [%s] %s' % (
                            operation,
                            variant_code, 
                            variation_id,
                            fabric_code,
                            res.get('message', 'Error without comment'),                        
                            wp_id,
                            ))
                    else:
                        _logger.info('Variant %s [%s] update on %s' % (
                            variant_code, 
                            variation_id or 'NEW',
                            wp_id,
                            ))
                # Delete also remain
                
        if parent_unset:
            _logger.error('Set parent for code start with: %s' % (
                parent_unset))
                        
# vim:expandtab:smartindent:ltabstop=4:softtabstop=4:shiftwidth=4:
