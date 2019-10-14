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
    
'''class ProductPublicCategory(orm.Model):
    """ Model name: ProductProduct
    """

    _inherit = 'product.public.category'
    
    _columns = {
        'wp_id': fields.integer('Worpress ID'),
        }
'''

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
            return (
                default_code[:6].strip(),
                '%s-%s' % (
                    default_code[6:8].strip().upper() or 'NE', # XXX Neutro
                    default_code[8:].strip().upper(),
                    ),
                )

        if context is None:    
            context = {}

        _logger.warning('Publish attribute all on wordpress:')
        
        # ---------------------------------------------------------------------
        #                         WORDPRESS Publish:
        # ---------------------------------------------------------------------
        server_pool = self.pool.get('connector.server')
        web_product_pool = self.pool.get('product.product.web.server')
        
        # ---------------------------------------------------------------------
        #                        CREATE CATEGORY OPERATION:
        # ---------------------------------------------------------------------
        connector_id = ids[0]
        server_proxy = self.browse(cr, uid, connector_id, context=context)
        #data = {'create': [], 'update': []}

        # Read WP Category present:
        wcapi = server_pool.get_wp_connector(
            cr, uid, connector_id, context=context)

        # ---------------------------------------------------------------------        
        # Read all attributes:
        # ---------------------------------------------------------------------        
        current_wp_attribute = wcapi.get(
            'products/attributes').json()

        try:
            test_error = res['data']['status'] == 400
            raise osv.except_osv(
                _('Category error:'), 
                _('Error getting attributes list: %s' % (res, ) ),
                )
        except:
            pass # no error               

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
        # Read current attributes terms:
        # ---------------------------------------------------------------------        
        current_wp_terms = []
        theres_data = True
        parameter = {
            'per_page': 10,
            'page': 0,
            }
        
        _logger.warning('Search all terms for attribute %s...' % (
            attribute_id.keys(), ))
        while theres_data:
            parameter['page'] += 1
            res = wcapi.get(
                'products/attributes/%s/terms' % attribute_id['Tessuto'], 
                params=parameter).json()

            try:
                test_error = res['data']['status'] == 400
                raise osv.except_osv(
                    _('Category error:'), 
                    _('Error getting category list: %s' % (res, ) ),
                    )
            except:
                pass # no error               
                
            if res:
                current_wp_terms.extend(res)
            else:
                theres_data = False

        web_attribute = {}
        for record in current_wp_terms:
            web_attribute[record['name']] = record['id']

        # ---------------------------------------------------------------------
        # Generate attribute terms from product:
        # ---------------------------------------------------------------------
        product_ids = web_product_pool.search(cr, uid, [
            ('connector_id', '=', ids[0]),
            ('product_id.default_code', '=ilike', '127TX%'), # XXX remove
            ], context=context)
        _logger.warning('Product for this connector: %s...' % len(product_ids))

        product_db = {}
        attribute_db = []

        for record in sorted(web_product_pool.browse(cr, uid, product_ids, 
                context=context), 
                key=lambda x: x.product_id.wp_parent_template, reverse=True):
            # First is the template (if present)
            product = record.product_id
            default_code = product.default_code or ''
            if not default_code[:3].isdigit():
                continue
            product_parent, product_attribute = split_code(default_code)
            if product_attribute not in attribute_db:
                attribute_db.append(product_attribute)
            
            if product_parent not in product_db:
                product_db[product_parent] = [
                    record, # Web line with template product
                    [], # Variant product
                    ]
            product_db[product_parent][1].append((product, product_attribute))
            # Extract frame-color from code

        data = {
            'create': [],
            'update': [],
            'delete': [],
            }
        
        # ---------------------------------------------------------------------
        # Update / Create:
        # ---------------------------------------------------------------------
        for attribute in attribute_db:
            item = {
                'name': attribute,
                # 'color': # XXX RGP color
                }
            if attribute in web_attribute:
                data['update'].append(item)
            else:
                data['create'].append(item)

        # ---------------------------------------------------------------------
        # Delete:
        # ---------------------------------------------------------------------
        # XXX Not for now:
        #for name in web_attribute:
        #    if name not in attribute_db:
        #        data['delete'].append(web_attribute[name])

        # ---------------------------------------------------------------------
        # Batch operation:
        # ---------------------------------------------------------------------
        try:
            res = wcapi.post(
                'products/attributes/%s/terms/batch' % attribute_id['Tessuto'], 
                data=data,
                ).json()
        except:
            raise osv.except_osv(
                _('Error'), 
                _('Wordpress server not answer, timeout!'),
                )
        # TODO check result for res
    
        # ---------------------------------------------------------------------        
        # Upload product template / variations:
        # ---------------------------------------------------------------------
        parent_unset = []
        for parent in product_db:
            web_product, variants = product_db[parent]
            product = web_product.product_id
            default_code = product.default_code
            if not product.wp_parent_template:
                parent_unset.append(parent)
                continue
        
            # -----------------------------------------------------------------
            # Upload product reference:
            # -----------------------------------------------------------------            
            # 1. Call upload original procedure:
            translation_of = web_product_pool.publish_now(
                cr, uid, [web_product.id], context=context)
            wp_id = translation_of.get(default_code)
            if not wp_id:
                _logger.error(
                    'Cannot found wp_id, code %s' % default_code)
                # XXX Cannot update!
                continue

            # 2. Update attributes:
            product_parent, product_attribute = split_code(default_code)
            import pdb; pdb.set_trace()
            try:
                res = wcapi.put('products/%s' % wp_id, data={
                    'attributes': [
                        {'id': attribute_id, 'name': product_attribute}, 
                        # TODO Brand?
                    ]}).json()
            except:
                raise osv.except_osv(
                    _('Error'), 
                    _('Wordpress server not answer, timeout!'),
                    )
            import pdb; pdb.set_trace()
            
            # -----------------------------------------------------------------
            # Upload product variations:
            # -----------------------------------------------------------------
            
            
        if parent_unset:
            _logger.error('Set parent for code start with: %s' % (
                parent_unset))

                        
# vim:expandtab:smartindent:ltabstop=4:softtabstop=4:shiftwidth=4:
