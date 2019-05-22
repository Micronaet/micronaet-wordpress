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

        _logger.warning('Publish category all on wordpress:')
        
        # ---------------------------------------------------------------------
        #                         WORDPRESS Publish:
        # ---------------------------------------------------------------------
        server_pool = self.pool.get('connector.server')
        category_pool = self.pool.get('product.public.category')
        
        # ---------------------------------------------------------------------
        #                        CREATE CATEGORY OPERATION:
        # ---------------------------------------------------------------------
        connector_id = ids[0]
        server_proxy = self.browse(cr, uid, connector_id, context=context)
        data = {'create': [], 'update': []}

        # Read WP Category present:
        wcapi = server_pool.get_wp_connector(
            cr, uid, connector_id, context=context)

        # ---------------------------------------------------------------------        
        # Read all category:
        # ---------------------------------------------------------------------        
        theres_data = True
        parameter = {
            'per_page': 10,
            'page': 0,
            }
        current_wp_category = []
        while theres_data:
            parameter['page'] += 1
            res = wcapi.get(
                'products/categories', params=parameter).json()

            try:
                test_error = res['data']['status'] == 400
                raise osv.except_osv(
                    _('Category error:'), 
                    _('Error getting category list: %s' % (res, ) ),
                    )
            except:
                pass # no error               
                
            if res:
                current_wp_category.extend(res)
            else:
                theres_data = False

            
        # ---------------------------------------------------------------------        
        # Loading used dict DB
        # ---------------------------------------------------------------------        
        wp_db = {}
        wp_name = {} # TODO manage!
        for record in current_wp_category:
            wp_db[record['id']] = record['name']
            wp_name[(record['parent'] or False, record['name'])] = record['id']

        # ---------------------------------------------------------------------
        #                                Mode IN:
        # ---------------------------------------------------------------------
        # TODO Language management!!!
        if server_proxy.wp_category == 'in':
            _logger.warning(
                'Mode IN Wordpress category import [# %s]' % len(
                    current_wp_category))

            parent_wp_db = {}
            # Sorted so parent first:
            for record in sorted(current_wp_category, 
                    key=lambda x: x['parent']):
                wp_id = record['id']
                parent_id = record['parent'] or False
                name = record['name']
                
                category_ids = category_pool.search(cr, uid, [
                    ('connector_id', '=', connector_id),
                    ('wp_id', '=', wp_id),
                    ], context=context)
                if category_ids:
                    odoo_id = category_ids[0]
                    category_pool.write(cr, uid, category_ids, {
                        'parent_id': parent_wp_db.get(
                            parent_id, False),
                        'name': name,
                        'sequence': record['menu_order'], 
                        }, context=context)                    
                    _logger.info('Update %s' % name)    
                else:                   
                    odoo_id = category_pool.create(cr, uid, {
                        'enabled': True,
                        'connector_id': connector_id,
                        'wp_id': wp_id,
                        'parent_id': parent_wp_db.get(
                            parent_id, False),
                        'name': name,
                        'sequence': record['menu_order'], 
                        }, context=context)
                    _logger.info('Create %s' % name)    
                   
                # Save root parent ID: 
                parent_wp_db[wp_id] = odoo_id
            return True
                        
        # ---------------------------------------------------------------------
        #                                Mode OUT:
        # ---------------------------------------------------------------------
        # A. Read ODOO PARENT category:
        # ---------------------------------------------------------------------
        _logger.warning('Mode OUT Wordpress category export')
        odoo_parent = {}
        category_ids = category_pool.search(cr, uid, [
            ('connector_id', '=', connector_id),
            ('parent_id', '=', False),
            ], context=context)

        for category in category_pool.browse(
                cr, uid, category_ids, context=context):    
            wp_id = category.wp_id            
            odoo_id = category.id
            name = category.name
            
            record_data = {
                'name': name,
                'parent': 0,
                'menu_order': category.sequence,
                'display': 'default',
                }

            # Check if present (same name or ID):            
            key = (False, name)
            if key in wp_name:
                wp_id = wp_name[key]
                # Update this wp_id (same name)
                category_pool.write(cr, uid, [category.id], {
                    'wp_id': wp_id,
                    }, context=context)
                
            if wp_id in wp_db: # Update (ID or Name present)
                record_data['id'] = wp_id
                data['update'].append(record_data)
                try:
                    del(wp_db[wp_id])
                except:
                    pass # yet deleted (from Front end?)
    
            else: # Create:
                data['create'].append(record_data)
                odoo_parent[name] = odoo_id

        res = wcapi.post('products/categories/batch', data).json()
        for record in res.get('create', ()):
            wp_id = record['id']
            if not wp_id:
                # TODO manage error:
                _logger.error('Not Updated wp_id for %s' % wp_id)
                continue

            name = record['name']
            odoo_id = odoo_parent.get(name, False)
            if not odoo_id:
                _logger.error('Not Updated wp_id for %s' % name)
                continue

            category_pool.write(cr, uid, odoo_id, {
                'wp_id': record['id'],
                }, context=context)
            odoo_parent[name] = odoo_id
            _logger.info('Updated wp_id for %s' % name)

        # ---------------------------------------------------------------------
        # B. Read ODOO category child:
        # ---------------------------------------------------------------------
        odoo_child = {}
        data = {'create': [], 'update': []}
        category_ids = category_pool.search(cr, uid, [
            ('connector_id', '=', connector_id),
            ('parent_id', '!=', False),
            ], context=context)

        for category in category_pool.browse(
                cr, uid, category_ids, context=context):    
            wp_id = category.wp_id            
            odoo_id = category.id
            name = category.name
            parent_wp_id = category.parent_id.wp_id
            
            record_data = {
                'name': name,
                'parent': parent_wp_id,
                'menu_order': category.sequence,
                'display': 'default',
                }

            # Check if present :
            key = (parent_wp_id, name)
            if key in wp_name:
                wp_id = wp_name[key]
                # Update this wp_id (same name)
                category_pool.write(cr, uid, [category.id], {
                    'wp_id': wp_id,
                    }, context=context)

            if wp_id in wp_db: # Update
                record_data['id'] = wp_id
                data['update'].append(record_data)
                try:
                    del(wp_db[wp_id])
                except:
                    pass # yet deleted (from Front end?)
    
            else: # Create:
                data['create'].append(record_data)
                odoo_child[name] = odoo_id

        # ---------------------------------------------------------------------
        #                     UPDATE / DELETE CATEGORY OPERATION:
        # ---------------------------------------------------------------------
        data['delete'] = wp_db.keys()
        try:
            res = wcapi.post('products/categories/batch', data).json()
        except:
            raise osv.except_osv(
                _('Error'), 
                _('Wordpress server not answer, timeout!'),
                )
                        
        # Update category with WP ID:
        for record in res.get('create', ()):
            wp_id = record['id']
            if not wp_id:
                # TODO manage error:
                _logger.error('Not Updated wp_id for %s' % wp_id)
                continue
                
            name = record['name']
            odoo_id = odoo_child.get(name, False)
            if not odoo_id:
                _logger.error('Not Updated wp_id for %s' % name)
                continue
                
            category_pool.write(cr, uid, odoo_id, {
                'wp_id': record['id'],
                }, context=context)
            _logger.info('Updated wp_id for %s' % name)
        return True
        # TODO      
        # Check updated
        # Check deleted
        # Update product first category?
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
