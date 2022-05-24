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


class WordpressSaleOderPrintLabelWizard(orm.TransientModel):
    """ Wizard for label price
    """
    _name = 'wordpress.sale.oder.print.label.wizard'

    # --------------------
    # Wizard button event:
    # --------------------
    def action_print(self, cr, uid, ids, context=None):
        """ Event for button done
        """
        order_pool = self.pool.get('wordpress.sale.order')
        if context is None:
            context = {}

        # Read parameter (todo not now)
        wizard = self.browse(cr, uid, ids, context=context)[0]
        only_prime = wizard.only_prime
        only_unprinted = wizard.only_unprinted

        today = str(datetime.now())[:10]
        order_ids = order_pool.search(cr, uid, [
            ('traking_date', '=', today),
            ('label_printed', '=', False),
            # ('manual_label', '!=', False),
        ], context=context)
        if not order_ids:
            raise osv.except_osv(
                _('Errore'),
                _('Etichette Prime, non stampate, in consegna oggi '
                  'non presenti!'),
            )
        for order in order_pool.browse(cr, uid, order_ids, context=context):
            if order.delivery_mode != 'prime':  # Jump no prime order
                continue
            if not order.manual_label:  # Jump not manual label
                continue
            _logger.info('Print order label: %s' % order.name)

        # todo return order error?
        return {
            'type': 'ir.actions.act_window_close'
            }

    _columns = {
        'only_prime': fields.boolean('Solo Amazon prime'),
        'only_unprinted': fields.boolean('Solo non stampate'),
        }

    _defaults = {
        'only_prime': lambda *x: True,
        'only_unprinted': lambda *x: True,
        }
