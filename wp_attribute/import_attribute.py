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

class ProductProductWebServerIntegration(orm.Model):
    """ Model name: ProductProductWebServer
    """

    _inherit = 'product.product.web.server'

    # -------------------------------------------------------------------------
    # Button event:
    # -------------------------------------------------------------------------
    def clean_wp_reference(self, cr, uid, ids, context=None):
        ''' Clean procedura for WP product deleted
        '''
        return self.write(cr, uid, ids, {
            'wp_it_id': False,
            'wp_en_id': False,
            }, context=context)
            
    def publish_master_now(self, cr, uid, ids, context=None):
        ''' Publish but only this
        '''
        connector_pool = self.pool.get('connector.server')
        if context is None:
            context = {}        

        
        current = self.browse(cr, uid, ids, context=context)[0]    
        connector_id = current.connector_id.id
        
        context['domain_extend'] = [
            ('id', '=', ids[0]),
            ]    
        return connector_pool.publish_attribute_now(
            cr, uid, [connector_id], context=context)    
        
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
                _('Non presente il codice da usare quindi non possibile!'),
                )
        
        child_ids = self.search(cr, uid, [
            # Parent code similar:
            ('product_id.default_code', '=ilike', '%s%%' % wp_parent_code),
            
            ('wp_parent_template', '=', False),  # Not parent product
            ('id', '!=', parent_id),  # Not this
            ('connector_id', '=', connector_id),  # This connector
            ], context=context)
        
        _logger.info('Updating %s product...' % len(child_ids))
        return self.write(cr, uid, child_ids, {
            'wp_parent_id': parent_id,            
            }, context=context)

    # -------------------------------------------------------------------------
    # Utility:
    # -------------------------------------------------------------------------
    def reset_parent(self, cr, uid, parent_ids, context=None):
        ''' Remove parent reference
        '''
        return self.write(cr, uid, parent_ids, {
            'wp_parent_code': False,
            'wp_parent_id': False, 
            
            # XXX Lang reset:
            'wp_it_id': False,
            'wp_en_id': False,
            # TODO There's problem if product has no previous parent
            }, context=context)    
        
    def set_as_master_product(self, cr, uid, ids, context=None):
        ''' Set as master product for this connection and remove if present
            previous
        '''
                
        current_id = ids[0]
        current_product = self.browse(cr, uid, current_id, context=context)
        connector_id = current_product.connector_id.id
        default_code = current_product.product_id.default_code
        wp_parent_code = current_product.wp_parent_code  # if auto master
        wp_parent_id = current_product.wp_parent_id  # Current master
        
        # XXX Bad reference (when add new lang):
        wp_it_id = wp_en_id = False
        if wp_parent_id:
            wp_it_id = wp_parent_id.wp_it_id 
            wp_en_id = wp_parent_id.wp_en_id 
        elif wp_parent_code:
            find_parent_ids = self.search(cr, uid, [
                ('wp_parent_code', '=', wp_parent_code),
                ('id', '!=', current_id),
                ('wp_parent_template', '=', True),
                ], context=context)
            if find_parent_ids:    
                wp_parent_id = self.browse(
                    cr, uid, find_parent_ids, context=context)[0]    
                wp_it_id = wp_parent_id.wp_it_id 
                wp_en_id = wp_parent_id.wp_en_id 
        
        if wp_parent_code:
                
            # -----------------------------------------------------------------
            # Case: has parent code:
            # -----------------------------------------------------------------
            # Search parent with same code if present
            previous_ids = self.search(cr, uid, [
                ('wp_parent_code', '=', wp_parent_code),
                ('id', '!=', current_id),
                ], context=context)
                
            # Remove previous situation:
            self.reset_parent(cr, uid, previous_ids, context=context)
            
            # Force this master with code:
            self.link_variant_now(cr, uid, ids, context=context)
               
        elif wp_parent_id: 
            # -----------------------------------------------------------------
            # Case: parent present:
            # -----------------------------------------------------------------
            # Remove previous situation:
            self.reset_parent(cr, uid, [wp_parent_id], context=context)
            
        else: 
            # -----------------------------------------------------------------
            # Case: no parent no code:
            # -----------------------------------------------------------------
            pass # nothing to do
        
        # ---------------------------------------------------------------------
        # Set this as parent
        # ---------------------------------------------------------------------
        return self.write(cr, uid, ids, {
            'wp_parent_template': True,
            'wp_it_id': wp_it_id,
            'wp_en_id': wp_en_id,
            }, context=context)

    _columns = {
        'wp_parent_template': fields.boolean(
            'Prodotto master', 
            help='Prodotto riferimento per raggruppare i prodotti dipendenti'),
        'wp_parent_code': fields.char('Codice appartenenza', 
            help='Codice usato per calcolare appartenenza automatica'),
        'wp_parent_id': fields.many2one(
            'product.product.web.server', 'Prodotto padre'),    
        'wp_color_id': fields.many2one(
            'connector.product.color.dot', 'Colore'),
        }

    _sql_constraints = [
        ('parent_code_uniq', 'unique (wp_parent_code)', 
            'Il codice di appartenenza deve essere unico!'),        
        ]    

class ProductProductWebServerRelation(orm.Model):
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
        'name': fields.char('Code', size=64, required=True,
            help='Frame-Color used on web site for color (as key!)'),             
        'description': fields.char('Web description', size=80, translate=True),
        'hint': fields.char('Hint', size=80, translate=True,
            help='Tooltip text when mouse over image'),
        'dropbox_image': fields.char('Dropbox link', size=180),

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

    def external_get_wp_id(self, cr, uid, ids, context=None):
        ''' External extract data to get Code - Lang: WP ID
        '''
        web_pool = self.pool.get('product.product.web.server')
        connector_id = ids[0]
        not_found = []
        # TODO mangage not parent product!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        
        # Read WP product:
        wcapi = self.get_wp_connector(
            cr, uid, connector_id, context=context)
        _logger.warning('Read all product on wordpress:')

        parameter = {'per_page': 10, 'page': 1}
        theres_data = True
        import pdb; pdb.set_trace()
        while theres_data:
            call = 'products'
            reply = wcapi.get(call, params=parameter).json()
            parameter['page'] += 1
            
            for item in reply:
                wp_id = item['id']
                lang = item['lang']
                default_code = item['sku']
                field = 'wp_%s_id' % lang
                
                if not default_code:
                    not_found.append(wp_id)
                    _logger.warning('Product not found: %s' % (
                        default_code, lang))
                    
                web_ids = web_pool.search(cr, uid, [
                    ('product_id.default_code', '=', default_code),
                    ], context=context)
                if not web_ids:
                    not_found.append(wp_id)
                    _logger.warning('Code: %s lang: %s not found on DB' % (
                        default_code, lang))
                    continue
                    
                if len(web_ids) > 1:
                    import pdb; pdb.set_trace()
                    
                web_product = web_pool.browse(
                    cr, uid, web_ids, context=context)[0]
                this_wp_id = eval('web_product.%s' % field)
                if this_wp_id != wp_id:
                    not_found.append(wp_id)
                    continue
                    
                # Update product reference:
                if not this_wp_id:
                    web_pool.write(cr, uid, web_ids, {
                        field: wp_id,
                        }, context=context)
            break # TODO remove
        return not_found
        
        
    def publish_attribute_now(self, cr, uid, ids, context=None):
        ''' Publish now button
            Used also for more than one elements (not only button click)
            Note all product must be published on the same web server!            
            '''
        """def split_code(default_code, lang='it'):
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
                )"""
        def lang_sort(lang):
            ''' Setup lang order
            '''        
            if 'it' in lang:
                return 1
            elif 'en' in lang:
                return 2
          
        # =====================================================================
        # Log operation on Excel file:
        # ---------------------------------------------------------------------
        now = ('%s' % datetime.now()).replace(
            '/', '').replace(':', '').replace('-', '')[:30]
        ws_name = now
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
        # Sort order and list of languages:
        langs = [
            'it_IT', 
            'en_US',
            ]
        default_lang = 'it'

        if context is None:    
            context = {}

        # Data publish selection (remove this part from publish:
        unpublished = [
            'image', # TODO parametrize
            ]

        # Pool used:
        web_product_pool = self.pool.get('product.product.web.server')
        dot_pool = self.pool.get('connector.product.color.dot')

        connector_id = ids[0]
        server_proxy = self.browse(cr, uid, connector_id, context=context)
        #brand_code = server_proxy.brand_code # As default

        # Read WP Category present:
        wcapi = self.get_wp_connector(
            cr, uid, connector_id, context=context)

        _logger.warning('Publish attribute all on wordpress:')

        # ---------------------------------------------------------------------
        #                          COLLECT DATA: 
        # ---------------------------------------------------------------------
        domain = [
            ('connector_id', '=', ids[0]),
            ('wp_parent_template', '=', True),
            ]
        domain_extend = context.get('domain_extend')    
        if domain_extend:
            domain.extend(domain_extend)
            _logger.warning('Domain extended: %s' % (domain, ))
            
        product_ids = web_product_pool.search(cr, uid, domain, context=context)
        _logger.warning('Product for this connector: %s...' % len(product_ids))

        product_db = {} # Master database for lang - parent - child
        lang_color_db = {} # Master list for color in default lang
        fabric_color_odoo = {} # Dropbox link for image
        product_default_color = {} # First variant showed

        parent_total = 0
        for odoo_lang in langs:
            lang = odoo_lang[:2]
            context_lang = context.copy()
            context_lang['lang'] = odoo_lang
            
            # Start with lang level:
            product_db[odoo_lang] = {}
            lang_color_db[lang] = []

            for parent in web_product_pool.browse(  # Default_selected product:
                    cr, uid, product_ids, context=context_lang): 
                parent_total += 1
                    
                # TODO default_selected is first element                
                default_selected = parent # TODO Change during next loop:
                product_db[odoo_lang][parent] = [default_selected, []] 
                
                for variant in parent.variant_ids:
                    # Note: first variat is parent:                    
                    product = variant.product_id
                    default_code = product.default_code or ''
                    color = variant.wp_color_id.name
                    attribute = color + '-' + lang
                    fabric_color_odoo[attribute] = variant.wp_color_id
                    
                    # Save color for attribute update
                    if attribute not in lang_color_db[lang]:
                        lang_color_db[lang].append(attribute)
                        
                    # Save variant with color element: 
                    product_db[odoo_lang][parent][1].append(
                        (variant, attribute))

                # Save default color for lang product
                product_default_color[(default_selected, lang)
                    ] = default_selected.wp_color_id.name + '-' + lang

        _logger.warning('Parent found: %s' % parent_total)

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
        # Search Master Attribute:
        # ---------------------------------------------------------------------        
        attribute_id = {
            'Tessuto': False,
            'Brand': False,
            # TODO Material, Certificate
            }
        _logger.warning('Searching attribute %s...' % (attribute_id.keys() ))
        for record in current_wp_attribute:
            name = record['name']
            # lang = record['lang'] # TODO not present!
            if record['name'] in attribute_id:
                attribute_id[record['name']] = record['id']
        if not all(attribute_id.values()):
            raise osv.except_osv(
                _('Attribute error'), 
                _('Cannot find some attribute terms %s!') % (attribute_id, ),
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
        
        # TODO need lang?
        lang_color_terms = {
            'it': {},
            'en': {},
            }
        for record in current_wp_terms:
            name = record['name']
            key = name[:-3]
            lang = record['lang']
            lang_color_terms[lang][key] = record['id']

        # ---------------------------------------------------------------------        
        #                        TERMS: (for Brand Attribute)
        # ---------------------------------------------------------------------        
        lang_brand_terms = {} # not needed for now
        
        call = 'products/attributes/%s/terms' % attribute_id['Brand']
        for record in wcapi.get(call).json():
            lang = record['lang']
            name = record['name']

            if lang not in lang_brand_terms:
                lang_brand_terms[lang] = {}
                
            lang_brand_terms[lang][name] = record['id']

        # ---------------------------------------------------------------------
        # Update / Create: (XXX only fabric?)
        # ---------------------------------------------------------------------
        # Start from IT (default) lang:
        for lang in sorted(lang_color_db, key=lambda l: lang_sort(l)):
            # Clean every loop:
            data = {
                'create': [],
                'update': [],
                'delete': [],
                }
            for attribute in lang_color_db[lang]:
                key = attribute[:-3] # Key element (without -it or -en)
                odoo_color = fabric_color_odoo[attribute]
                item = {
                    'name': attribute,
                    'lang': lang,
                    'color_name': odoo_color.hint,
                    }

                # Image part:
                if odoo_color.dropbox_image:
                    item['color_image'] = odoo_color.dropbox_image
                    
                if lang != default_lang: # Different language:
                    # TODO correct 
                    wp_it_id = lang_color_terms[default_lang].get(key)
                    if wp_it_id:
                        item.update({
                            'translations': {'it': wp_it_id}
                            })
                    else:
                        _logger.error('Attribute not found %s %s!' % (
                            key,
                            lang,
                            ))
                        # TODO manage?
                        
                # Only create:
                if key in lang_color_terms[lang]:
                    data['update'].append(item)
                else:
                    data['create'].append(item)

            # -----------------------------------------------------------------
            # Delete:
            # -----------------------------------------------------------------
            # XXX Not for now: 
            # TODO correct
            #for name in lang_color_terms:
            #    if name not in lang_color_db:
            #        data['delete'].append(lang_color_terms[name])

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
                        try:
                            key = record['name'][:-3]                            
                            wp_id = record['id']
                            if not wp_id: # TODO manage error:
                                _logger.error('Not Updated wp_id for %s' % wp_id)
                                continue
            
                            # Update for language not IT (default):
                            lang_color_terms[lang][key] = wp_id 
                        except:
                            _logger.error('No name in %s' % record)
                            import pdb; pdb.set_trace()
                            continue
                                
            except:
                raise osv.except_osv(
                    _('Error'), 
                    _('Wordpress server timeout! \n[%s]') % (sys.exc_info(), ),
                    )

        # ---------------------------------------------------------------------        
        #                       PRODUCT AND VARIATIONS:
        # ---------------------------------------------------------------------
        translation_lang = {}
        parent_unset = []
        
        wp_variant_lang_ref = {}
        for odoo_lang in sorted(product_db, key=lambda l: lang_sort(l)):
            context_lang = context.copy()
            context_lang['lang'] = odoo_lang
            lang = odoo_lang[:2]
            
            for parent in product_db[odoo_lang]:
                master_record, variants = product_db[odoo_lang][parent]
                master_product = master_record.product_id
                master_code = master_product.default_code

                # -------------------------------------------------------------
                # TEMPLATE PRODUCT: Upload product reference:
                # -------------------------------------------------------------
                # 1. Call upload original procedure:
                context['log_excel'] = []
                translation_lang.update(
                    web_product_pool.publish_now(
                        cr, uid, [master_record.id], context=context))
                # TODO Launch only for default lang? (this run twice!)
                # REMOVE: Update brand terms for product:

                # =============================================================
                # Excel log:
                # -------------------------------------------------------------
                row += 1
                excel_pool.write_xls_line(ws_name, row, [
                    'Pubblicazione prodotto base: %s' % master_code,
                    ], default_format=excel_format['title'])

                for log in context['log_excel']:
                    row += 1
                    excel_pool.write_xls_line(ws_name, row, log, 
                        default_format=excel_format['text'], col=1)
                # =============================================================

                lang_product_default_color = product_default_color[
                    (master_record, lang)]

                # -------------------------------------------------------------
                # Setup default attribute:
                # -------------------------------------------------------------
                wp_id, lang_master_name = translation_lang.get(
                    master_code, {}).get(lang, (False, False))
                data = {
                    # Only color (not brand as default)
                    'default_attributes': [{
                        'id': attribute_id['Tessuto'],
                        'option': lang_product_default_color,
                        }],

                    # Write to force code in attribute:
                    'lang': lang,
                    'name': lang_master_name,                    
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
                #          VARIANTS: Setup color terms for product
                # -------------------------------------------------------------
                # 2. Update attributes:
                # First block for setup color:
                data = {
                    # To force lang procedure:
                    'lang': lang,
                    'name': lang_master_name,

                    'attributes': [{
                        'id': attribute_id['Tessuto'], 
                        'options': [],
                        'variation': True,
                        'visible': True,
                        }]}

                # Second element for brand! (mandatory!)
                import pdb; pdb.set_trace()
                if master_record.brand_id:                
                    data['attributes'].append({
                        'id': attribute_id['Brand'], 
                        'options': [master_record.brand_id.name],
                        'variation': False,
                        'visible': True,
                        })

                # Upodate first element colors:
                for line, variant_color in variants:
                    data['attributes'][0]['options'].append(variant_color)
                    
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

                # -------------------------------------------------------------
                #                       VARIANTS: Creation
                # -------------------------------------------------------------
                for item in res:
                    # No option
                    if not item['attributes'] or not item['attributes'][0][
                            'option']:
                        data['delete'].append(item['id'])
                    else:
                        # TODO TEST BETTER:
                        wp_variant_lang_ref[(
                            web_product_pool.wp_clean_code(
                                item['sku'], destination='odoo'), 
                            item['lang'])] = item['id']
                    
                        """
                        if lang == default_lang:
                            wp_variant_lang_ref[
                                (item['sku'], lang)] = item['id']
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
                            wp_variant_lang_ref[(
                                '%-6s%s' % (parent, option), # XXX 
                                lang,
                                )] = item['id']
                        """

                # Clean variant no color:
                if data['delete']:
                    wcapi.post(
                        'products/%s/variations/batch' % wp_id, data).json()
                    # TODO log

                for line, fabric_code in variants:
                    variant = line.product_id
                    variant_code = variant.default_code
                    variant_id = wp_variant_lang_ref.get(
                        (variant_code, lang), False)
                    variant_it_id = wp_variant_lang_ref.get(
                        (variant_code, default_lang), False)                    

                    # XXX Price for S (ingle)
                    price = web_product_pool.get_wp_price(line)

                    # Description:
                    name = line.force_name or variant.name or u''
                    description = line.force_description or \
                        variant.emotional_description or \
                        variant.large_description or u''
                    short_description = line.force_name or \
                        variant.emotional_short_description or name

                    # Create or update variant:
                    data = {
                        'regular_price': u'%s' % price,
                        # sale_price (discounted)
                        'short_description': short_description,
                        'description': description,
                        'lang': lang,    
                        #'slug': self.get_lang_slug(variant_code, lang),
                        # TODO
                        # stock_quantity
                        # stock_status
                        'weight': '%s' % line.weight,
                        'dimensions': {
                            'length': '%s' % line.pack_l,
                            'height': '%s' % line.pack_h,
                            'width': '%s' % line.pack_p,
                            },
                        'stock_quantity': 
                            web_product_pool.get_existence_for_product(
                                variant),
                        'status': 'publish' if line.published else 'private',
                        
                        'attributes': [{
                            'id': attribute_id['Tessuto'], 
                            'option': fabric_code,
                            }]
                        }
                        
                    data['sku'] = web_product_pool.wp_clean_code(variant_code) # used always?
                    if default_lang == lang: # Add language default ref.
                        # data['sku'] = self.wp_clean_code(variant_code)
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
                    image = False
                    if 'image' not in unpublished:
                        for item in line.wp_dropbox_images_ids:                  
                            if item.dropbox_link:
                                image = {
                                    'src': item.dropbox_link,
                                    }
                                break # Only one image in variant!    
                         
                    if image:
                        data['image'] = image

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
                            wp_variant_lang_ref[
                                (variant_code, lang)] = variant_id
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
        # TODO 
        # Update dot color images and records! (here?)
            
        # Rerturn log calls:        
        return excel_pool.return_attachment(
            cr, uid, 'Log call', name_of_file='call.xlsx', context=context)
# vim:expandtab:smartindent:ltabstop=4:softtabstop=4:shiftwidth=4:
