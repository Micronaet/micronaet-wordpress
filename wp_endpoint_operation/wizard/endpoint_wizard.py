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
import openerp.addons.decimal_precision as dp
from openerp.osv import fields, osv, expression, orm
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp import SUPERUSER_ID
from openerp import tools
from openerp.tools.translate import _
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT, 
    DEFAULT_SERVER_DATETIME_FORMAT, 
    DATETIME_FORMATS_MAP, 
    float_compare)


_logger = logging.getLogger(__name__)

class ConnectorServer(orm.Model):
    """ Model name: ConnectorServer
    """    
    _inherit = 'connector.server'

    # -------------------------------------------------------------------------
    # Procedure:
    # -------------------------------------------------------------------------
    def wp_update_product_existence(cr, uid, ids, context=None):
        ''' Update existence in WP via connector
        '''
        connector_id = ids[0]
        # Pool used:
        item_pool = self.pool.get('product.product.web.server')
        
        # Open connector:
        wcapi = self.get_wp_connector(
            cr, uid, connector_id, context=context)

        # ---------------------------------------------------------------------
        # Update product selected:
        # ---------------------------------------------------------------------
        item_ids = item_pool.search(cr, uid, [
            ('connector_id', '=', connector_id),
            ], context=context)
        
        for item in item_pool.browse(cr, uid, item_ids, context=context):
            product = item.product_id 
            stock_quantity = item_pool.get_existence_for_product(product)
            
                
                    
        return True

class WpEndpointOperationWizard(orm.TransientModel):
    ''' Wizard for endpoint operations
    '''
    _name = 'wp.endpoint.operation.wizard'

    # -------------------------------------------------------------------------
    # Wizard button event:
    # -------------------------------------------------------------------------
    def action_publish_all(self, cr, uid, ids, context=None):
        ''' Event for button done
        '''
        wiz_browse = self.browse(cr, uid, ids, context=context)[0]
        connector_id = wiz_browse.connector_id.id

        return True

    def action_put_category(self, cr, uid, ids, context=None):
        ''' Put all category
        '''
        return True

    def action_get_category(self, cr, uid, ids, context=None):
        ''' Load all category
        '''
        return True

    def action_existence(self, cr, uid, ids, context=None):
        ''' Publish only existence
        '''
        wiz_browse = self.browse(cr, uid, ids, context=context)[0]
        connector_id = wiz_browse.connector_id.id
        return wp_update_product_existence(
            cr, uid, connector_id, context=context)

    def action_image(self, cr, uid, ids, context=None):
        '''
        '''
        return True

    def action_product_category(self, cr, uid, ids, context=None):
        '''
        '''
        return True

    _columns = {
        'connector_id': fields.many2one(
            'connector.server', 'Connector', required=True,
            domain='[("wordpress", "=", True)]'),
        }
        
    _defaults = {
        }    

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:


