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

    def get_wp_connector(self, cr, uid, context=None):
        ''' Connect with Word Press API management
        '''
        assert len(ids) == 1, 'Works only with one record a time'
        
        connector = self.browse(cr, uid, ids, context=context)[0]
        if not connector.wordpress:
            _logger.info('Not Wordpress connector')
        
        return woocommerce.API(
            url=connector.wp_url,
            consumer_key=connector.wp_key,
            consumer_secret=connector.wp_secret,
            wp_api=True,
            version="wc/v3"
            )

    _columns = {
        'wordpress': fields.boolean('Wordpress', help='Wordpress web server'),

        'wp_url': fields.char('WP URL', size=180),
        'wp_key': fields.char('WP consumer key', size=180),
        'wp_secret': fields.char('WP consumer secret', size=180),
        
        'wp_api': fields.boolean('WP API'),
        'wp_version': fields.char('WP Version', size=10),
        }
    
    _defaults = {
        'wp_api': lambda *x: True,
        'wp_version': lambda *x: 'wc/v3',        
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
