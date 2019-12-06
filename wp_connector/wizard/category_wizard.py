# -*- coding: utf-8 -*-
###############################################################################
#
# ODOO (ex OpenERP) 
# Open Source Management Solution
# Copyright (C) 2001-2019 Micronaet S.r.l. (<http://www.micronaet.it>)
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

class WordpressSelectProductCategoryWizard(orm.TransientModel):
    ''' Wizard for publish category wizard 
    '''
    _name = 'wordpress.select.product.category.wizard'

    # -------------------------------------------------------------------------
    # Wizard button event:
    # -------------------------------------------------------------------------
    def action_update_category(self, cr, uid, ids, context=None):
        ''' Event for button done
        '''
        if context is None:
            context = {} 
        
        # Pool:
        web_pool = self.pool.get('product.product.web.server')
        category_pool = self.pool.get('product.public.category')
        model_pool = self.pool.get('ir.model.data')
        
        wiz_browse = self.browse(cr, uid, ids, context=context)[0]

        connector_id = wiz_browse.webserver_id.id
        code_start = wiz_browse.code_start
        wordpress_categ_ids = [
            item.id for item in wiz_browse.wordpress_categ_ids]

        # ---------------------------------------------------------------------
        # Generate Domain:
        # ---------------------------------------------------------------------
        domain = []
        if code_start:
            domain.append(
                ('product_id.default_code', '=ilike', '%s%%' % code_start),
                )                
        web_ids = web_pool.search(cr, uid, domain, context=context)
        
        # ---------------------------------------------------------------------
        # Update category:
        # ---------------------------------------------------------------------
        web_pool.write(cr, uid, web_ids, {
            'wordpress_categ_ids': [(6, 0, wordpress_categ_ids)],
            }, context=context)
                
        tree_view_id = model_pool.get_object_reference(
            cr, uid, 
            'wp_connector', 'view_product_product_web_server_wp_tree')[1]
        form_view_id = model_pool.get_object_reference(
            cr, uid, 
            'wp_connector', 'view_product_product_web_server_wp_form')[1]
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Selected'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            #'res_id': 1,
            'res_model': 'product.product.web.server',
            'view_id': tree_view_id,
            'views': [(tree_view_id, 'tree'), (form_view_id, 'form')],
            'domain': [
                ('id', '=', web_ids),
                ],
            'context': context,
            'target': 'current', # 'new'
            'nodestroy': False,
            }
            
    _columns = {
        'webserver_id': fields.many2one(
            'connector.server', 'Webserver', required=True),
        'code_start': fields.char('Code start', size=25, required=True),
        'wordpress_categ_ids': fields.many2many(
            'product.public.category', 'product_wp_cat_wizard_rel', 
            'wizard_id', 'category_id', 
            'Wordpress category', required=True, 
            domain="[('connector_id', '=', webserver_id)]",
            ),
        }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
