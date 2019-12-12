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

class ProductProductWebServer(orm.Model):
    """ Model name: ProductProductWebServer
    """

    _inherit = 'product.product.web.server'

    # -------------------------------------------------------------------------
    # Button event:
    # -------------------------------------------------------------------------
    def link_variant_now(self, cr, uid, ids, context=None):
        ''' Link all child variant
        '''
        parent_id = ids[0]
        current_product = self.browse(cr, uid, parent_id, context=context)
        connector_id = current_product.connector_id.id
        wp_parent_code = current_product.wp_parent_code
        if not wp_parent_code:
            raise osv.except_osv(
                _('Errore'), 
                _('Non presnete il codice da usare quindi non possibile!'),
                )
        
        child_ids = self.search(cr, uid, [
            # Parent code similar:
            ('product_id.default_code', '=ilike', '%s%%' % wp_parent_code),
            
            ('wp_parent_id', '!=', parent_id),  # Different parent:
            ('id', '!=', parent_id),  # Not this
            ('connector_id', '=', connector_id),  # This connector:
            ], context=context)
            
        return self.write(cr, uid, child_ids, {
            'wp_parent_id': parent_id,            
            }, context=context)

    # -------------------------------------------------------------------------
    # Utility:
    # -------------------------------------------------------------------------
    #TODO remove
    def get_product_search_parent(self, cr, uid, ids, default_code, 
            connection_id, context=None):
        ''' Find all product with same parent in web product
        '''
        if len(default_code) <= 3:  # Short parent
            search_code = '%s%%' % default_code[:3]
        else: #<= 6  # Long parent    
            search_code = '%6s%%' % default_code[:3]
        
        web_product_ids = self.search(cr, uid, [
            ('product_id.default_code', '=ilike', search_code),
            ], context=context)
        
        if web_product_ids:
            self.write(cr, uid, web_product_ids, {
                'connection_id': connection_id,
                'wp_parent_template': False
                }, context=context)
            # TODO save wp_it_id and wp_en_id?
        
    def set_as_master_product(cr, uid, ids, context=None):
        ''' Set as master product for this connection and remove if present
            previous
        '''
        current_product = self.browse(cr, uid, ids, context=context)[0]
        connection_id = current_product.connection_id.id
        default_code = current_product.product_id.default_code
        if not default_code:
            raise osv.except_osv(
                _('Errore'), 
                _('Codice non presente, impossibile impostarlo!'),
                )
        
        # ---------------------------------------------------------------------
        # Remove all previous parent if present:        
        # ---------------------------------------------------------------------
        web_product_ids = self.get_product_search_parent(
            cr, uid, ids, web_product.product_id.default_code, 
            connection_id,
            context=context)
            
        # ---------------------------------------------------------------------
        # Set this as parent
        # ---------------------------------------------------------------------
        return self.write(cr, uid, ids, {
            'wp_parent_template': True,
            }, context=context)

    _columns = {
        'wp_parent_template': fields.boolean(
            'Prodotto master', 
            help='Prodotto riferimento per raggruppare i prodotti dipendenti'),
        'wp_parent_code': fields.char('Codice appartenenza', 
            help='Codice usato per calcolare appartenenza automatica'),
        'wp_parent_id': fields.many2one(
            'product.product.web.server', 'Prodotto padre'),    
        }

class ProductProductWebServer(orm.Model):
    """ Model name: ProductProductWebServer
    """

    _inherit = 'product.product.web.server'

    _columns = {
        'variant_ids': fields.one2many(
            'product.product.web.server', 'wp_parent_id', 'Varianti'),
        }

class ConnectorProductColorDot(orm.Model):
    """ Model name: ConnectorProductColorDot
    """
    
    _name = 'connector.product.color.dot'
    _description = 'Color dot'
    _rec_name = 'name'
    _order = 'name'

    def _get_image_name(self, cr, uid, ids, fields, args, context=None):
        ''' Fields function for calculate 
        '''
        res = {}        
        path = False
        with_check = len(ids) == 1
        for image in self.browse(cr, uid, ids, context=context):
            if not path:
                path = os.path.expanduser(image.connector_id.dot_image_path)
            
            name = '%s.png' % image.name.upper()
            fullname = os.path.join(path, name)
            
            if with_check:
                image_present = os.path.isfile(fullname)
            else: 
                image_present = False

            res[image.id] = {
                'image_name': name,
                'image_fullname': fullname,
                'image_present': image_present,
                }
        return res        
        
    _columns = {
        'not_active': fields.boolean('Not active'),
        'connector_id': fields.many2one(
            'connector.server', 'Server', required=True),
        'name': fields.char('Code', size=64, required=True, translate=True,
            help='Frame-Color used on web site for color'),             
        'description': fields.char('Web description', size=80, translate=True),
        'hint': fields.char('Hint', size=80, translate=True,
            help='Tooltip text when mouse over image'),

        # Image in particular folder   
        'image_name': fields.function(
            _get_image_name, method=True, multi=True,
            type='char', string='Image name',), 
        'image_fullname': fields.function(
            _get_image_name, method=True, multi=True,
            type='char', string='Image fullname'), 
        'image_present': fields.function(
            _get_image_name, method=True, multi=True,
            type='boolean', string='Image present'), 
        }

'''
class ProductProduct(orm.Model):
    """ Model name: ProductProduct
    """

    _inherit = 'product.product'
    
    _columns = {
        # TODO remove:
        'wp_parent_template': fields.boolean(
            'Template for variants', 
            help='Product used as tempalte for variants (first six char of '
                'code)'),
        }
'''

class ProductPublicCategory(orm.Model):
    """ Model name: ProductProduct
    """

    _inherit = 'connector.server'

    _columns = {
        'brand_code': fields.char('Brand code', size=30, required=True, 
            help='Brand used for attribute name for company product'),
        'dot_image_path': fields.char('Color image', size=180, required=True,
            help='Color path for dot images, use ~ for home'),
        }
        
    def publish_attribute_now(self, cr, uid, ids, context=None):
        ''' Publish now button
            Used also for more than one elements (not only button click)
            Note all product must be published on the same web server!            
            '''
        def split_code(default_code, lang='it'):
            ''' Split 2 part of code
            '''   
            default_code = (default_code or '')[:12] # No exta part
            return (
                default_code[:6].strip(),
                '%s-%s-%s' % (
                    default_code[6:8].strip().upper() or 'NE',  # XXX Neutro
                    default_code[8:].strip().upper(),
                    lang.upper(),
                    ),
                )
        
        # =====================================================================
        # Log operation on Excel file:
        # ---------------------------------------------------------------------
        ws_name = 'Chiamate'
        excel_pool = self.pool.get('excel.writer')        
        excel_pool.create_worksheet(ws_name)
        excel_pool.set_format()
        excel_format = {
            'title': excel_pool.get_format('title'),
            'header': excel_pool.get_format('header'),
            'text': excel_pool.get_format('text'),
            }
        row = 0
        excel_pool.write_xls_line(ws_name, row, [
            'Commento',
            'Chiamata',
            'End point',
            'Data',
            'Reply',
            ], default_format=excel_format['header'])
        excel_pool.column_width(ws_name, [30, 20, 30, 50, 100])
        # =====================================================================

        # ---------------------------------------------------------------------
        # Handle connector:
        # ---------------------------------------------------------------------
        default_lang = 'it'

        if context is None:    
            context = {}

        # Pool used:
        web_product_pool = self.pool.get('product.product.web.server')
        dot_pool = self.pool.get('connector.product.color.dot')

        connector_id = ids[0]
        server_proxy = self.browse(cr, uid, connector_id, context=context)
        brand_code = server_proxy.brand_code

        # Read WP Category present:
        wcapi = self.get_wp_connector(
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

        for odoo_lang in ('it_IT', 'en_US'):
            lang = odoo_lang[:2]
            context_lang = context.copy()
            context_lang['lang'] = odoo_lang
            records = web_product_pool.browse(
                cr, uid, product_ids, context=context_lang)
            
            for record in sorted(records, 
                    key=lambda x: x.wp_parent_template, 
                    reverse=True
                    ):

                # First is the template (if present)
                product = record.product_id
                default_code = product.default_code or ''
                if not default_code[:3].isdigit(): # TODO MT and TL?
                    _logger.warning('Not used %s' % default_code)
                    continue

                product_parent, product_attribute = split_code(
                    default_code, lang)
                if product_attribute not in attribute_db:
                    attribute_db.append(product_attribute)
              
                # A. Create master product and prepara for variant:  
                if product_parent not in product_db:
                    product_db[product_parent] = [
                        record, # Web line with template product
                        {}, # Variant product (not the first)
                        ]
                  
                # B. Add variant:
                if lang not in product_db[product_parent][1]:
                    product_db[product_parent][1][lang] = []
                product_db[product_parent][1][lang].append(
                    (record, product_attribute))
                # Extract frame-color from code

        _logger.warning('Parent found: %s' % len(product_db))

        # ---------------------------------------------------------------------        
        #                     ATTRIBUTES: (need Tessuto, Brand)
        # ---------------------------------------------------------------------   
        call = 'products/attributes'
        current_wp_attribute = wcapi.get(call).json()
        
        # =====================================================================
        # Excel log:
        # ---------------------------------------------------------------------   
        row += 1
        excel_pool.write_xls_line(ws_name, row, [
            'Richiesta elenco attributi:',
            ], default_format=excel_format['title'])
        row += 1
        excel_pool.write_xls_line(ws_name, row, [
            'Elenco attributi',
            'get',
            call,
            '',
            u'%s' % (current_wp_attribute, ),
            ], default_format=excel_format['text'])
        # =====================================================================
        
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
            # TODO Material, Certificate
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

        # =====================================================================
        # Excel log:
        # ---------------------------------------------------------------------   
        row += 1
        excel_pool.write_xls_line(ws_name, row, [
            'Richiesta termini:',
            ], default_format=excel_format['title'])
        # =====================================================================

        # Fabric attribute:
        while theres_data:
            call = 'products/attributes/%s/terms' % attribute_id['Tessuto']
            res = wcapi.get(
                call, params=parameter).json()
            parameter['page'] += 1
            
            # =================================================================
            # Excel log:
            # -----------------------------------------------------------------
            row += 1
            excel_pool.write_xls_line(ws_name, row, [
                'Lettura attributi tessuto',
                'get',
                call,
                u'%s' % (parameter),
                u'%s' % (res, ),
                ], default_format=excel_format['text'])
            # =================================================================

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
            web_attribute[record['name']] = record['id']

        # ---------------------------------------------------------------------        
        #                        TERMS: (for Brand Attribute)
        # ---------------------------------------------------------------------        
        brand_attribute = {} # not needed for now
        brand_company_id = {}
        
        call = 'products/attributes/%s/terms' % attribute_id['Brand']
        for record in wcapi.get(call).json():
            lang = record['lang']
            name = record['name']
            record_id = record['id']

            if lang not in brand_attribute:
                brand_attribute[lang] = {}
                
            brand_attribute[lang][name] = record_id
            if brand_code == name and lang == default_lang:
                brand_company_id = {
                    lang: record_id,
                    }

        # ---------------------------------------------------------------------
        # Update / Create: (XXX only fabric?)
        # ---------------------------------------------------------------------
        for lang in ('it', 'en'):
            # Clean every loop:
            data = {
                'create': [],
                'update': [],
                'delete': [],
                }
            for attribute in attribute_db: 
                if attribute[-2:] != lang.upper():
                    continue # only terms for this lang
                item = {
                    'name': attribute,
                    'lang': lang,
                    #'slug': self.get_lang_slug(attribute, lang)
                    # 'color': # XXX RGP color
                    }
                    
                if lang != default_lang: # Different language:
                    wp_it_id = web_attribute.get(
                        attribute[:-2] + default_lang.upper())
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
                        
                if attribute in web_attribute:
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
            # Batch operation (fabric terms for attribute manage):
            # -----------------------------------------------------------------            
            try:
                # =============================================================
                # Excel log:
                # -------------------------------------------------------------
                row += 1
                excel_pool.write_xls_line(ws_name, row, [
                    'Aggiornamento tessuti:',
                    ], default_format=excel_format['title'])
                # =============================================================

                if any(data.values()): # only if one is present
                    call = 'products/attributes/%s/terms/batch' % \
                        attribute_id['Tessuto']
                    res = wcapi.post(call, data=data).json()

                    # =========================================================
                    # Excel log:
                    # ---------------------------------------------------------
                    row += 1
                    excel_pool.write_xls_line(ws_name, row, [
                        'Batch attributi tessuto',
                        'post',
                        call,
                        u'%s' % (data),
                        u'%s' % (res, ),
                        ], default_format=excel_format['text'])
                    # =========================================================
                    
                    # ---------------------------------------------------------
                    # Save WP ID (only in dict not in ODOO Object)
                    # ---------------------------------------------------------
                    for record in res.get('create', ()):
                        wp_id = record['id']
                        if not wp_id: # TODO manage error:
                            _logger.error('Not Updated wp_id for %s' % wp_id)
                            continue

                        # Update for next language:
                        web_attribute[record['name']] = wp_id 
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

        context['log_excel'] = []
        context['override_sku'] = '' # SKU not present for product 
        for parent in product_db:
            web_product, lang_variants = product_db[parent]

            # -----------------------------------------------------------------
            # TEMPLATE PRODUCT: Upload product reference:
            # -----------------------------------------------------------------
            # 1. Call upload original procedure:
            translation_lang.update(
                web_product_pool.publish_now(
                    cr, uid, [web_product.id], context=context))
            
            # -----------------------------------------------------------------
            # Update brand terms for product:
            # -----------------------------------------------------------------
            #call = 'products/attributes/%s/terms/batch' % \
            #    attribute_id['Tessuto']
            #res = wcapi.post(call, data=data).json()

            # =================================================================
            # Excel log:
            # -----------------------------------------------------------------
            row += 1
            excel_pool.write_xls_line(ws_name, row, [
                'Pubblicazione prodotto base',
                ], default_format=excel_format['title'])

            for log in context['log_excel']:
                row += 1
                excel_pool.write_xls_line(ws_name, row, log, 
                    default_format=excel_format['text'], col=1)
                # =============================================================

            product = web_product.product_id
            default_code = product.default_code
            if not web_product.wp_parent_template:
                parent_unset.append(parent)
                continue

            web_variant = {}

            for odoo_lang in ('it_IT', 'en_US'):
                lang = odoo_lang[:2]
                context_lang = context.copy()
                context_lang['lang'] = odoo_lang

                variants = lang_variants.get(lang, [])

                # -------------------------------------------------------------
                # Setup default attribute:
                # -------------------------------------------------------------
                wp_id, lang_name = translation_lang.get(
                    default_code, {}).get(lang, (False, False))
                parent_parent, parent_attribute = split_code(
                    default_code, lang)
                data = {
                    'default_attributes': [{
                        'id': attribute_id['Tessuto'],
                        'option': parent_attribute,
                        }, 
                        # No brand default
                        #{
                        #'id': attribute_id['Brand'],
                        #'option': brand_code,
                        #},
                        ],

                    # Write to force code in attribute:
                    'lang': lang,
                    'name': lang_name,                    
                    }

                call = 'products/%s' % wp_id
                reply = wcapi.put(call, data).json()
                
                # =============================================================
                # Excel log:
                # -------------------------------------------------------------
                row += 1
                excel_pool.write_xls_line(ws_name, row, [
                    'Pubblicazione varianti lingua %s' % lang ,
                    ], default_format=excel_format['title'])
                row += 1
                excel_pool.write_xls_line(ws_name, row, [
                    'Default nella scheda prodotto',
                    'put',
                    call,
                    u'%s' % (data),
                    u'%s' % (reply, ),
                    ], default_format=excel_format['text'])
                # =============================================================
                
                if not wp_id:
                    _logger.error(
                        'Cannot found wp_id, code %s' % default_code)
                    # XXX Cannot update!
                    continue
                
                # -------------------------------------------------------------
                #                        VARIANTS: Creation
                # -------------------------------------------------------------
                # 2. Update attributes:
                data = {
                    # For force lang procedure:
                    'lang': lang,
                    'name': lang_name,

                    'attributes': [{
                        'id': attribute_id['Tessuto'], 
                        'options': [],
                        'variation': True,
                        'visible': True,
                        # XXX remove?:
                        #'name': 'Tessuto',
                        #'name': variant_attribute,
                        }]}

                # NOTE: Second element for brand!
                #brand_lang = brand_company_id.get(lang)
                #if brand_lang:
                data['attributes'].append({
                    'id': attribute_id['Brand'], 
                    'options': [brand_code],
                    'variation': False,
                    'visible': True,
                    })

                # Upodate first element colors:
                for line, variant_attribute in variants:
                    variant = line.product_id
                    data['attributes'][0]['options'].append(variant_attribute)
                    
                try:
                    call = 'products/%s' % wp_id
                    res = wcapi.post(call, data=data).json()
                    
                    # =========================================================
                    # Excel log:
                    # ---------------------------------------------------------
                    row += 1
                    excel_pool.write_xls_line(ws_name, row, [
                        'Aggiornamento termini attributi',
                        'post',
                        call,
                        u'%s' % (data),
                        u'%s' % (res, ),
                        ], default_format=excel_format['text'])
                    # =========================================================
                    
                except:
                    raise osv.except_osv(
                        _('Error'), 
                        _('Wordpress server not answer, timeout!'),
                        )
                
                # -------------------------------------------------------------
                # Upload product variations:
                # -------------------------------------------------------------
                call = 'products/%s/variations' % wp_id
                res = wcapi.get(call).json()
                    
                # =============================================================
                # Excel log:
                # -------------------------------------------------------------
                row += 1
                excel_pool.write_xls_line(ws_name, row, [
                    'Lettura varianti attuali',
                    'get',                    
                    call,
                    u'',
                    u'%s' % (res, ),
                    ], default_format=excel_format['text'])
                # =============================================================

                data = {
                    'delete': [],
                    }

                for item in res:
                    # No option
                    if not item['attributes'] or not item['attributes'][0][
                            'option']:
                        data['delete'].append(item['id'])
                    else:
                        #current_variant[
                        #    item['attributes'][0]['option']] = item['id']

                        if lang == default_lang:
                            web_variant[(item['sku'], lang)] = item['id']
                        else:
                            # Variant has no sku, compose from parent + option
                            option = False
                            for attribute in item['attributes']:
                                if attribute['id'] == attribute_id['Tessuto']:
                                    option = attribute['option']
                            if not option:
                                _logger.error(
                                    'Cannot get sku for variant %s' % (item, ))
                                continue
                            option = option[:-3].replace('-', '') # remove lang
                            web_variant[(
                                '%-6s%s' % (parent, option), 
                                lang,
                                )] = item['id']

                # Clean variant no color:
                if data['delete']:
                    wcapi.post(
                        'products/%s/variations/batch' % wp_id, data).json()
                    # TODO log

                for line, fabric_code in variants:
                    variant = line.product_id
                    variant_code = variant.default_code
                    variant_id = web_variant.get(
                        (variant_code, lang), False)
                    variant_it_id = web_variant.get(
                        (variant_code, 'it'), False)                    

                    # XXX Price for S (ingle)

                    # Description:
                    short_description = line.force_name or \
                        variant.emotional_short_description or \
                        variant.name or u''

                    description = line.force_description or \
                        variant.emotional_description or \
                        variant.large_description or u''

                    # Create or update variant:
                    data = {
                        'regular_price': u'%s' % (
                            line.force_price or variant.lst_price),
                        # sale_price (discounted)
                        'short_description': short_description,
                        'description': description,
                        'lang': lang,    
                        #'slug': self.get_lang_slug(variant_code, lang),
                        # TODO
                        # stock_quantity
                        # stock_status
                        # weight
                        # dimensions
                        'stock_quantity': 
                            web_product_pool.get_existence_for_product(
                                variant),
                        'status': 'publish' if line.published else 'private',
                        
                        'attributes': [{
                            'id': attribute_id['Tessuto'], 
                            'option': fabric_code,
                            }]
                        }
                        
                    data['sku'] = variant_code
                    #if default_lang == lang: # Add language default ref.
                    #    data['sku'] = variant_code
                    if default_lang == lang: # Add language default ref.
                        pass
                    else:
                        if not variant_it_id:
                            _logger.error(
                                'Cannot update variant in lang, no it: %s' % (
                                    variant_code
                                    ))
                            continue # XXX test if correct!
                            
                        data['translations'] = {
                            'it': variant_it_id, # Created before
                            }
                        
                    # ---------------------------------------------------------
                    # Images block:
                    # ---------------------------------------------------------
                    image = [] 
                    for image in line.wp_dropbox_images_ids:                  
                        if image.dropbox_link:
                            image = {
                                'src': image.dropbox_link,
                                }
                            break # Only one image in variant!    
                                
                    if image:
                        data['image'] = image

                    #variant_id = variant_ids.get(
                    #    (variant_code, lang), False)
                    if variant_id: # Update
                        operation = 'UPD'
                        call = 'products/%s/variations/%s' % (
                            wp_id,
                            variant_id,
                            )
                        res = wcapi.put(call, data).json()
                        #del(current_variant[fabric_code]) #for clean operat.
                        
                        # =====================================================
                        # Excel log:
                        # -----------------------------------------------------
                        row += 1
                        excel_pool.write_xls_line(ws_name, row, [
                            'Aggiorna variante',
                            'put',
                            call,
                            u'%s' % (data, ),
                            u'%s' % (res, ),
                            ], default_format=excel_format['text'])
                        # =====================================================

                    else: # Create
                        operation = 'NEW'
                        call = 'products/%s/variations' % wp_id
                        res = wcapi.post(call, data).json()

                        # =====================================================
                        # Excel log:
                        # -----------------------------------------------------
                        row += 1
                        excel_pool.write_xls_line(ws_name, row, [
                            'Crea variante',
                            'post',
                            call,
                            u'%s' % (data, ),
                            u'%s' % (res, ),
                            ], default_format=excel_format['text'])
                        # =====================================================

                        try:
                            variant_id = res['id']
                            # Save for other lang:
                            web_variant[(variant_code, lang)] = variant_id
                        except:
                            variant_id = '?'    

                    if res.get('data', {}).get('status', 0) >= 400:
                        _logger.error('%s Variant: %s [%s] >> %s [%s] %s' % (
                            operation,
                            variant_code, 
                            variant_id,
                            fabric_code,
                            res.get('message', 'Error without comment'),                        
                            wp_id,
                            ))
                    else:
                        _logger.info('%s Variant %s [%s] linked to %s' % (
                            operation,
                            variant_code, 
                            variant_id or 'NEW',
                            wp_id,
                            ))
                # TODO Delete also remain
                
        if parent_unset:
            _logger.error('Set parent for code start with: %s' % (
                parent_unset))
             
        # ---------------------------------------------------------------------
        # Attribute update ODOO VS WP:
        # ---------------------------------------------------------------------
        for attribute in attribute_db:
            if not attribute.endswith('-IT'):
                continue
            
            name = attribute[:-3] # TODO remove
            dot_ids = dot_pool.search(cr, uid, [(
                'name', '=', name)], context=context)    
            if not dot_ids:
                dot_pool.create(cr, uid, {
                    'connector_id': connector_id,
                    'name': name,                    
                    }, context=context)
            
        # Rerturn log calls:        
        return excel_pool.return_attachment(
            cr, uid, 'Log call', name_of_file='call.xlsx', context=context)
# vim:expandtab:smartindent:ltabstop=4:softtabstop=4:shiftwidth=4:
