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
import pdb
import sys
import re
import logging
import erppeek
import openerp
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
    """ Model name: Company parameters
    """

    _inherit = 'connector.server'

    _columns = {
        # Linked database:
        'linked_dbname': fields.char(
            'DB collegato', size=30,
            help='Database collegato per recuperare informazioni prodotti'),
        'linked_user': fields.char('DB utente', size=30),
        'linked_pwd': fields.char('DB password', size=30),
        'linked_server': fields.char('DB server', size=30),
        'linked_port': fields.integer('DB porta'),
    }

    def get_product_linked_database(
            self, cr, uid, ids, default_code, context=None):
        """ Connect with linked database to get extra info
        """
        connector = self.browse(cr, uid, ids, context=context)[0]

        # ---------------------------------------------------------------------
        # Connect to ODOO:
        # ---------------------------------------------------------------------
        if not connector.linked_server:
            return False
        odoo = erppeek.Client(
            'http://%s:%s' % (connector.linked_server, connector.linked_port),
            db=connector.linked_dbname,
            user=connector.linked_user,
            password=connector.linked_pwd,
        )

        product_pool = odoo.model('product.product')
        product_ids = product_pool.search([
            ('default_code', '=', default_code),
        ])
        if not product_ids:
            _logger.error('No product with %s code' % default_code)
            return False
        return product_pool.browse(product_ids)[0]


class ResCompany(orm.Model):
    """ Model name: Company parameters
    """

    _inherit = 'res.company'

    _columns = {
        'carrier_save_label': fields.boolean(
            'Salva etichette', help='Salva le etichette senza stamparle'),
        'carrier_save_label_path': fields.char(
            'Percorso salvataggio su file', size=100),
    }


class CarrierConnection(orm.Model):
    """ Model name: Carrier Connection
    """
    _name = 'carrier.connection'
    _description = 'Carrier connection'
    _order = 'name'

    _columns = {
        'name': fields.char('Nome', size=64, required=True),
        'company_id': fields.many2one(
            'res.company',
            'Azienda',
            required=True),

        'location': fields.char(
            'Root', size=140, required=True,
            help='Path dell\'endpoint, es.: https://api.mbeonline.it/ws'),
        'username': fields.char('Username', size=64, required=True),
        'passphrase': fields.char('Passphrase', size=64, required=True),

        'system': fields.char(
            'Sistema', size=10, required=True,
            help='Vecchio modo per gestire la nazionalità'),
        'internal_reference': fields.char(
            'Riferimento interno', size=10,
            help='Codice utilizzato in ogni chiamata, usato come ID'),
        'customer_id': fields.integer(
            'ID Cliente', required=True, help='Codice nella gestione del portale'),
        'store_id': fields.char(
            'ID Store', size=4, required=True,
            help='Codice usato in alcune chiamate'),

        'auto_print_label': fields.boolean(
            'Stampa automatica',
            help='Stampa etichetta quando è richiesta la consegna'),
        'cups_printer_id': fields.many2one(
            'cups.printer', 'CUPS printer',
            help='Etichetta ordine stampata con questa'),

        # Not used for now:
        'sam_id': fields.char('ID SAM', size=4, help=''),
        'department_id': fields.char('ID Dipartimento', size=4, help=''),
    }

    _defaults = {
        'location': lambda *x:
            'https://api.mbeonline.it/ws',
        'system': lambda *x: 'IT',
        'internal_reference': lambda *x: 'MI030-lg',
        }


class CarrierSupplierMode(orm.Model):
    """ Model name: Parcels supplier mode of delivery
    """

    _name = 'carrier.supplier.mode'
    _description = 'Carrier mode'
    _rec_name = 'name'

    # -------------------------------------------------------------------------
    #                                   COLUMNS:
    # -------------------------------------------------------------------------
    _columns = {
        'name': fields.char('Nome', required=True),
        'account_ref': fields.char('Rif. contabile'),
        'hidden': fields.boolean('Nascosto'),
        'cups_printer_id': fields.many2one(
            'cups.printer', 'CUPS printer',
            help='Label order print with this')
    }


class CarrierSupplier(orm.Model):
    """ Model name: Parcels supplier
    """

    _name = 'carrier.supplier'
    _description = 'Parcel supplier'
    _rec_name = 'name'

    # -------------------------------------------------------------------------
    #                                   COLUMNS:
    # -------------------------------------------------------------------------
    _columns = {
        'hidden': fields.boolean('Nascosto'),
        'prime': fields.boolean('Prime'),
        'name': fields.char('Nome'),
        'accounting_ref': fields.char(
            'Codice contabile', size=10,
            help='Codice contabile, nella quotazione dello sconto il codice'
                 'articolo passato al gestonale sarà il codice broker unito'
                 'al codice corriere'),
        'account_ref': fields.char('Codice'),
        'mode': fields.selection([
            ('carrier', 'Corriere'),
            ('courier', 'Spedizioniere'),
            ], 'Mode', required=True),
        'carrier_mode': fields.selection([
            ('transport', 'Trasportatore'),
            ('auto', 'Autotrasportatore'),
            ], 'Modalità corriere', required=True),
        'zone_mode_extra': fields.selection([
            ('broker', 'Broker'),
            ('courier', 'Corriere'),
            ], 'Modalità costi extra', required=True,
            help='Indica se le zone di divisione CAP si prendono quelle '
                 'del broker o se il corriere ha le sue',
        ),
        'broker_id': fields.many2one(
            'carrier.supplier', 'Broker',
            domain="[('mode', '=', 'carrier')]",
            help='Broker di appartenenza'),
        'mode_id': fields.many2one(
            'carrier.supplier.mode', 'Modalità',
            domain="[('supplier_id.mode', '=', 'carrier')]",
            help='Modalità dello spedizioniere'),

        'carrier_connection_id': fields.many2one(
            'carrier.connection', 'Connessione broker'),
        }

    _defaults = {
        'mode': lambda *x: 'carrier',
        'carrier_mode': lambda *x: 'transport',
        'zone_mode_extra': lambda *x: 'broker',
    }


class CarrierSupplierModeRelations(orm.Model):
    """ Model name: Parcels supplier mode of delivery
    """

    _inherit = 'carrier.supplier.mode'

    _columns = {
        'supplier_id': fields.many2one(
            'carrier.supplier', 'Broker', required=True),
    }


class CarrierParcelTemplate(orm.Model):
    """ Model name: Parcels template
    """

    _name = 'carrier.parcel.template'
    _description = 'Modelli imballo'
    _rec_name = 'name'

    def _get_volumetric_weight(
            self, cr, uid, ids, fields=None, args=None, context=None):
        """ Compute volumetric weight, return value
        """
        res = {}
        for template in self.browse(cr, uid, ids, context=context):
            res[template.id] = (
                template.length * template.width * template.height / 5000.0)
        return res

    # -------------------------------------------------------------------------
    #                                   COLUMNS:
    # -------------------------------------------------------------------------
    _columns = {
        'is_active': fields.boolean('Attivo'),
        'name': fields.char('Nome'),
        'no_label': fields.boolean('No etichetta'),
        'carrier_supplier_id': fields.many2one('carrier.supplier', 'Broker'),
        'length': fields.float('Lunghezza', digits=(16, 2), required=True),
        'width': fields.float('Larghezza', digits=(16, 2), required=True),
        'height': fields.float('Altezza', digits=(16, 2), required=True),
        'dimension_uom_id': fields.many2one('product.uom', 'Product UOM'),
        'weight': fields.function(
            _get_volumetric_weight,
            string='Weight volumetric', digits=(16, 2), type='float',
            help='Volumetric weight (H x L x P / 5000)', readonly=True),
        'weight_uom_id': fields.many2one('product.uom', 'Product UOM'),
        'carrier_connection_id': fields.many2one(
            'carrier.connection',
            'Carrier Connection',
            help='Force carrier connection for small package'),

        'package_type': fields.selection(
            [
                ('GENERIC', 'Generico'),
                ('ENVELOPE', 'Busta'),
                ('DOCUMENTS', 'Documenti'),
            ], 'Tipo imballo', required=True),
    }

    _defaults = {
        'package_type': lambda *x: 'GENERIC',
    }


class SaleOrderParcel(orm.Model):
    """ Model name: Parcels for sale order
    """

    _name = 'sale.order.parcel'
    _description = 'Sale order parcel'
    _rec_name = 'weight'

    def _get_volumetric_weight(
            self, cr, uid, ids, fields=None, args=None, context=None):
        """ Compute volumetric weight, return value
        """
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            weight = (  # Volumetric:
                line.length * line.width * line.height / 5000.0)
            real_weight = line.real_weight
            if line.use_real_weight:
                used_weight = line.real_weight  # Real
            else:  # Greater evaluation:
                if weight > real_weight:
                    used_weight = weight
                else:
                    used_weight = real_weight
            res[line.id] = {
                'weight': weight,  # volumetric
                'used_weight': used_weight,
            }
        return res

    # -------------------------------------------------------------------------
    #                                   COLUMNS:
    # -------------------------------------------------------------------------
    _columns = {
        'order_id': fields.many2one('wordpress.sale.order', 'Ordine WP'),

        # Dimension:
        'length': fields.float('Lunghezza', digits=(16, 2), required=True),
        'width': fields.float('Larghezza', digits=(16, 2), required=True),
        'height': fields.float('Altezza', digits=(16, 2), required=True),
        'dimension_uom_id': fields.many2one('product.uom', 'UM dim.'),
        'use_real_weight': fields.boolean(
            'Usa reale', help='Passa perso reale al posto del volum.'),

        # Weight:
        'real_weight': fields.float('Peso reale', digits=(16, 2)),
        'weight': fields.function(
            _get_volumetric_weight,
            string='Peso Volumetrico', digits=(16, 2), type='float',
            readonly=True, multi=True,
        ),
        'used_weight': fields.function(
            _get_volumetric_weight,
            string='Larghezza usata', digits=(16, 2), type='float',
            readonly=True, multi=True,
        ),
        'weight_uom_id': fields.many2one('product.uom', 'UM peso'),
        'no_label': fields.boolean('No etichetta'),
        'carrier_connection_id': fields.many2one(
            'carrier.connection',
            string='Connessione broker',
            help='Forza connessione per piccoli pacchetti')
    }


class WordpressSaleOrderRelationCarrier(orm.Model):
    """ Model name: Wordpress Sale order
    """
    _inherit = 'wordpress.sale.order'

    def order_form_detail(self, cr, uid, ids, context=None):
        """ Return order form
        """
        tree_view_id = form_view_id = False
        return {
            'type': 'ir.actions.act_window',
            'name': _('Order details'),
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_id': ids[0],
            'res_model': 'wordpress.sale.order',
            'view_id': tree_view_id,
            'views': [(form_view_id, 'form'), (tree_view_id, 'tree')],
            'domain': [],
            'context': context,
            'target': 'current',
            'nodestroy': False,
        }

    def get_product_from_wp_order_line(
            self, cr, uid, connector_id, line, context=None):
        """ Check if product is from this database or from linked
        """
        connector_pool = self.pool.get('connector.server')

        product = line.product_id
        if not product:  # Linked database:
            product = connector_pool.get_product_linked_database(
                cr, uid, [connector_id], line.sku, context=context)

        return product

    def generate_parcel_from_order(self, cr, uid, ids, context=None):
        """ Generate parcels from sale order
        """
        order_id = ids[0]
        parcel_pool = self.pool.get('sale.order.parcel')
        connector_pool = self.pool.get('connector.server')

        order = self.browse(cr, uid, order_id, context=context)

        # Delete previous:
        parcel_ids = parcel_pool.search(cr, uid, [
            ('order_id', '=', order_id),
        ], context=context)
        parcel_pool.unlink(cr, uid, parcel_ids, context=context)

        # Generate parcel from product:
        connector_id = order.connector_id.id
        for line in order.line_ids:
            product = self.get_product_from_wp_order_line(
                cr, uid, connector_id, line, context=context)
            # product = line.product_id
            # if not product:
            #    # Linked database:
            #    product = connector_pool.get_product_linked_database(
            #        cr, uid, [connector_id], line.sku, context=context)
            if product:
                # This database:
                for counter in range(int(line.quantity)):
                    data = {
                        'order_id': order_id,
                        'real_weight': product.weight,
                        'height': product.pack_h,  # height,
                        'width': product.pack_p,  # width,
                        'length': product.pack_l,  # length,
                    }
                    parcel_pool.create(cr, uid, data, context=context)

        return True

    def log_error(self, cr, uid, ids, error, context=None):
        """ Log error in chatter and in console
        """
        if context is None:
            context = {}
        verbose = context.get('verbose', False)

        order = self.browse(cr, uid, ids, context=context)[0]
        message = 'Order: %s [%s]' % (order.name, error)
        _logger.error(message)
        if verbose:
            raise osv.except_osv(
                _('Errore gestione consegne:'),
                message,
            )
        # order.write_log_chatter_message(error)
        return True  # order.write({'soap_last_error': error,})

    def set_carrier_ok_yes(self, cr, uid, ids, context=None):
        """ Override method for send carrier request
        """
        if context is None:
            context = {}
        ctx = context.copy()
        ctx['verbose'] = True
        return self.set_carrier_ok_yes_auto(
            cr, uid, ids, context=ctx)

    def set_carrier_ok_yes_auto(self, cr, uid, ids, context=None):
        """ Override method for send carrier request
        """
        order = self.browse(cr, uid, ids, context=context)

        # ---------------------------------------------------------------------
        # Check options:
        # ---------------------------------------------------------------------
        # Get options if not present (XXX Moved here):
        # if not order.manage_delivery:
        #    return order.log_error(
        #        _('Order not delivery managed from ODOO'))
        if not order.parcel_detail:
            self.generate_parcel_from_order(cr, uid, ids, context=context)

        if not order.parcel_detail:
            return self.log_error(
                cr, uid, ids,
                'Errore aggiungere imballi per la consegna!',
                context=context
                )

        if order.carrier_state in ('sent', 'delivered'):
            return self.log_error(
                cr, uid, ids,
                _('Order sent or delivered cannot confirm!'),
                context=context
                )

        if not order.carrier_supplier_id or not order.parcel_ids:
            return self.log_error(
                cr, uid, ids,
                _('Need carrier name and parcel data for get quotation'),
                context=context,
                )

        if order.carrier_track_id:
            return self.log_error(
                cr, uid, ids,
                _('Track ID yet present, cannot regenerate, '
                  'cancel and reassign if needed'),
                context=context,
            )

        # 1. Get options if not present courier:
        if not order.courier_supplier_id:
            error = self.shipment_options_request(
                    cr, uid, ids, context=context)
            if error:
                return self.log_error(
                    cr, uid, ids,
                    error,
                    context=context,
                )

        if not order.courier_supplier_id:  # Same check after get quotation
            return self.log_error(
                cr, uid, ids,
                _('Cannot generate quotation with this parameters'),
                context=context,
                )

        # 2. Create request:
        error = self.shipment_request(cr, uid, ids, context=context)
        if error:
            return self.log_error(
                cr, uid, ids,
                error,
                context=context,
            )

        # 3. todo Print also labels:
        if order.carrier_connection_id.auto_print_label:
            _logger.warning(_('Auto print label on request!'))
            self.carrier_print_label(cr, uid, ids, context=context)

        # todo self.write_log_chatter_message(_('Carrier data is OK'))

        # Clean error (if present)
        today = datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT)
        return self.write(cr, uid, ids, {
            # 'soap_last_error': False,
            # Check if order needs to be passed in ready status:
            'carrier_ok': True,
            'traking_date': today,
        })

    def set_carrier_ok_no(self, cr, uid, ids, context=None):
        """ Set carrier as UNDO
        """
        # self.write_log_chatter_message(
        #     _('Carrier data is not OK (undo operation)'))
        # todo nothing else?
        error = self.delete_shipments_request(
            cr, uid, ids, context=context)
        return self.write(cr, uid, ids, {
            # 'soap_last_error': False,
            # Check if order needs to be passed in ready status:
            'carrier_ok': False,
            'carrier_state': 'draft',
        })

    def load_template_parcel(self, cr, uid, ids, context=None):
        """ Load this template
        """
        parcel_pool = self.pool.get('sale.order.parcel')
        order = self.browse(cr, uid, ids, context=context)[0]
        template = order.carrier_parcel_template_id

        return parcel_pool.create(cr, uid, {
            'order_id': order.id,
            'length': template.length,
            'width': template.width,
            'height': template.height,
            'no_label': template.no_label,
            'real_weight': order.parcel_weight_tree,
            }, context=context)

    def carrier_get_better_option(self, cr, uid, ids, context=None):
        """ Get better options
        """
        order = self.browse(cr, uid, ids, context=context)[0]
        if not order.carrier_supplier_id:
            raise osv.except_osv(
                _('Controllo pre chiamata'),
                _('Richiesto il nome corriere'),
                )

        if not order.parcel_ids:
            raise osv.except_osv(
                _('Controllo pre chiamata'),
                _('Richiesto almeno un imballo'),
                )
        return self.shipment_options_request(cr, uid, ids, context=context)

    def set_default_carrier_description(self, cr, uid, ids, context=None):
        """ Update description from sale order line
        """
        order_id = ids[0]
        carrier_description = ''
        for line in self.browse(cr, uid, order_id, context=context).line_ids:
            product = line.product_id
            # TODO is expense is not present:
            if product.type == 'service':  # or product.is_expence:
                continue
            carrier_description += '(%s X) %s ' % (
                int(line.quantity),
                (line.name or product.description_sale or product.name or
                 _('Not found')),
                )
        return self.write(cr, uid, ids, {
            'carrier_description': self.sanitize_text(carrier_description)
            }, context=context)

    def _get_parcel_detail(
            self, cr, uid, ids, fields=None, args=None, context=None):
        """ Parcel detail
        """
        res = {}
        for order in self.browse(cr, uid, ids, context=context):
            detail = ''
            for parcel in order.parcel_ids:
                detail += '%sx%sx%s\n' % (
                    int(parcel.height),
                    int(parcel.width),
                    int(parcel.length),
                )
            res[order.id] = detail
        return res

    def _get_delivery_detail(
            self, cr, uid, ids, fields=None, args=None, context=None):
        """ Parcel detail
        """
        res = {}
        for order in self.browse(cr, uid, ids, context=context):
            detail = ''
            for line in order.line_ids:
                detail += '[%s] x %s: %s...\n' % (
                    line.sku,
                    int(line.quantity),
                    line.name[:20],
                )
            res[order.id] = detail
        return res

    def _get_carrier_check_address(
            self, cr, uid, ids, fields=None, args=None, context=None):
        """ Check address for delivery
        """
        # self.ensure_one()

        # Function:
        def format_error(field):
            return '<font color="red"><b> [%s] </b></font>' % field

        def get_partner_data(partner, check_dimension=False):
            """ Embedded function to check partner data
            """
            name = partner.name or ''
            street = partner.street or ''
            street2 = partner.street2 or ''
            error_check = not all((
                name,
                street,
                partner.zip,
                partner.city,
                partner.state_id,
                partner.country_id,
                partner.phone,  # mandatory for carrier?
                # partner.property_account_position_id,
            ))
            if check_dimension:
                if len(name) > check_dimension:
                    name = format_error(name)
                if len(street) > check_dimension:
                    street = format_error(street)
                if len(street2) > check_dimension:
                    street2 = format_error(street2)

            return (
                error_check,
                '%s %s %s - %s %s [%s %s] %s - %s<br/>' % (
                    name,
                    street or format_error(_('Address')),
                    street2 or '',
                    partner.zip or format_error(_('ZIP')),
                    partner.city or format_error(_('City')),
                    partner.state_id.name or format_error(_('State')),
                    partner.country_id.name or format_error(_('Country')),
                    partner.phone or format_error(_('Phone')),
                    partner.property_account_position_id.name or format_error(
                        _('Pos. fisc.')),
                    )
            )
        res = {}
        for order in self.browse(cr, uid, ids, context=context):
            partner = order.partner_invoice_id
            if order.fiscal_position_id != \
                    partner.property_account_position_id:
                check_fiscal = format_error(
                    _('Fiscal pos.: Order: %s, Partner %s<br/>') % (
                        order.fiscal_position_id.name,
                        partner.property_account_position_id.name,
                        ))
            else:
                check_fiscal = ''

            mask = _('%s<b>ORD.:</b> %s\n<b>INV.:</b> %s\n<b>DELIV.:</b> %s')
            error1, partner1_text = get_partner_data(
                order.partner_id)
            error2, partner2_text = get_partner_data(
                partner)
            error3, partner3_text = get_partner_data(
                order.partner_shipping_id)  # check_dimension=34)

            res[order.id] = {
                'carrier_check': mask % (
                    check_fiscal,
                    partner1_text,
                    partner2_text,
                    partner3_text,
                ),
                'carrier_check_error': error1 or error2 or error3,
            }
        return res

    def _get_carrier_parcel_total(
            self, cr, uid, ids, fields = None, args=None, context=None):
        """ Return total depend on type of delivery: manual or shippy
        """
        res = {}
        for order in self.browse(cr, uid, ids, context=context):
            if order.carrier_shippy:
                res[order.id] = len(order.parcel_ids)
            else:
                res[order.id] = order.carrier_manual_parcel
        return res

    def _check_carrier_cost_value(
            self, cr, uid, ids, fields=None, args=None, context=None):
        """ Check if total shipment is correct
        """
        _logger.warning('Recalculate lossy data!')
        res = {}
        for order in self.browse(cr, uid, ids, context=context):
            payed = order.carrier_cost_total
            if not payed:
                res[order.id] = False
                continue

            request = sum([item.price_subtotal for item in order.line_ids
                           if item.product_id.default_code == 'shipment'])
            res[order.id] = payed > request
        return res

    _columns = {
        'carrier_ok': fields.boolean(
            'OK spedizione',
            help='La consegna deve essere confermata quando fatta!'),

        # Master Carrier:
        'carrier_supplier_id': fields.many2one(
            'carrier.supplier', 'Broker',
            domain="[('mode', '=', 'carrier')]"),
        'carrier_mode_id': fields.many2one(
            'carrier.supplier.mode', 'Servizio broker',
            domain="[('supplier_id', '=', carrier_supplier_id)]",
        ),

        'courier_supplier_id': fields.many2one(
            'carrier.supplier', 'Corriere',
            domain="[('hidden', '=', False), "
                   "('mode', '=', 'courier'),"
                   "('mode_id', '=', carrier_mode_id)]"),
        'courier_mode_id': fields.many2one(
            'carrier.supplier.mode', 'Servizio corriere',
            domain="[('hidden', '=', False), "
                   "('supplier_id', '=', courier_supplier_id)]",
        ),

        'carrier_parcel_template_id': fields.many2one(
            'carrier.parcel.template', 'Modelli imballo'),
        'carrier_check': fields.text(
            'Controllo corriere', help='Controlla indirizzo corriere', multi=True,
            compute='_get_carrier_check_address', widget='html'),
        'carrier_check_error': fields.text(
            'Controllo errore corriere', help='Controlla errore indirizzo corriere',
            multi=True, compute='_get_carrier_check_address', widget='html'),

        'carrier_description': fields.text('Descrizione corriere'),
        'carrier_note': fields.text('Note corriere'),
        'carrier_stock_note': fields.text('Note magazziniere'),
        'carrier_total': fields.float('Valore bene', digits=(16, 2)),
        'carrier_ensurance': fields.float('Assicurazione', digits=(16, 2)),
        'carrier_cash_delivery': fields.float(
            'Contrassegno', digits=(16, 2)),
        'carrier_pay_mode': fields.selection([
            ('CASH', 'Contante'),
            ('CHECK', 'Assegno'),
            ], 'Modalità pagamento'),
        'parcel_ids': fields.one2many(
            'sale.order.parcel', 'order_id', 'Colli'),
        'parcel_detail': fields.function(
            _get_parcel_detail,
            string='Dettaglio colli', type='text'),
        'delivery_detail': fields.function(
            _get_delivery_detail,
            string='Dettaglio', type='text'),
        'real_parcel_total': fields.function(
            _get_carrier_parcel_total,
            string='Colli', type='integer',
        ),
        'destination_country_id': fields.related(
            'partner_shipping_id', 'country_id',
            string='Destizione', relation='res.country', type='many2one',
        ),

        # Data from Carrier:
        'carrier_cost': fields.float(
            'Cost', digits=(16, 2), help='Costo verificato'),
        'carrier_cost_total': fields.float(
            'Cost', digits=(16, 2), help='Totale trasporto'),
        'carrier_cost_lossy': fields.function(
            _check_carrier_cost_value,
            string='Perdita su spedizione', mode='boolean',
            help='Perdita su spedizione rispetto a quello esposto!',
            store=False,
        ),
        'carrier_track_id': fields.char(
            'Tracking ID', size=64),
        # TODO extra data needed!

        'has_cod': fields.boolean('Ha COD'),  # CODAvailable
        'has_insurance': fields.boolean(
            'Assicurato'),  # InsuranceAvailable
        'has_safe_value': fields.boolean(
            'Valore assicurato'),  # MBESafeValueAvailable

        'carrier_delivery_date': fields.datetime(
            'Data consegna', readonly=True),
        'carrier_delivery_sign': fields.datetime(
            'Data firma', readonly=True),

        # 'NetShipmentTotalPrice': Decimal('6.80'),  # ??
        # 'IdSubzone': 125,
        # 'SubzoneDesc': 'Italia-Zona A',

        # MBE Portal:
        'parcel_weight_tree': fields.float(
            'Peso',
            help='Peso in vista lista per velocizzare inserimento'),
        'carrier_connection_id': fields.many2one(
            'carrier.connection', 'Connessione broker',
            help='Connessione per avere la quotazione migliore'),
        'carrier_id': fields.integer('ID Broker'),
        'carrier_state': fields.selection(
            [
                ('draft', 'Bozza'),
                ('pending', 'Pendente'),
                ('sent', 'Spedito'),
                ('delivered', 'Consegnato'),  # Closed
            ], 'Stato consegna', required=True),
        'delivery_state': fields.selection(
            [
                ('WAITING_DELIVERY', 'In attesa'),
                ('PARTIALLY_DELIVERED', 'Consegnato parzialmente'),
                ('DELIVERED', 'Consegnato'),
                ('EXCEPTION', 'Eccezione'),
                ('NOT_AVAILABLE', 'Non disponibile'),
            ], 'Dettaglio consegna', required=True),
        'master_tracking_id': fields.char('Master Tracking', size=20),
        'system_reference_id': fields.char('Riferimento di sistema', size=20),
        'shipper_type': fields.selection(
            [
                ('COURIERLDV', 'LDV Corriere'),
                ('MBE', 'MBE'),
            ], 'Shipper type', required=True,
            ),

        'ship_type': fields.selection(
            [
                ('EXPORT', 'Export'),
                ('IMPORT', 'Import'),
                ('RETURN', 'Ritorno'),
            ], 'Tipo consegna', required=True),
        'package_type': fields.selection(
            [
                ('GENERIC', 'Generico'),
                ('ENVELOPE', 'Busta'),
                ('DOCUMENTS', 'Documenti'),
            ], 'Tipo imballo', required=True),

        # Force data:
        'force_invoice_zip': fields.char('Forza CAP', size=5),
        'force_invoice_city': fields.char('Forza Paese', size=40),
        'force_invoice_state': fields.char('Forza Provincia', size=5),
        'force_invoice_country': fields.char('Forza Nazione', size=5),
        'force_invoice_address1': fields.char('Forza Indirizzo 1', size=100),
        'force_invoice_address2': fields.char('Forza Indirizzo 2', size=35),

        'force_shipping_zip': fields.char('Forza CAP (cons.)', size=5),
        'force_shipping_city': fields.char('Forza Paese (cons.)', size=40),
        'force_shipping_state': fields.char('Forza Provincia (cons.)', size=5),
        'force_shipping_country': fields.char('Forza Nazione (cons.)', size=5),
        'force_shipping_address1': fields.char('Forza Indirizzo 1', size=100),
        'force_shipping_address2': fields.char('Forza Indirizzo 2', size=35),

        'label_printed': fields.boolean('Etichetta stampata'),

    }

    _defaults = {
        'carrier_pay_mode': lambda *x: 'CASH',
        'carrier_state': lambda *x: 'draft',
        'delivery_state': lambda *x: 'WAITING_DELIVERY',
        'shipper_type': lambda *x: 'COURIERLDV',
        'ship_type': lambda *x: 'EXPORT',
        'package_type': lambda *x: 'GENERIC',
    }


class CarrierSupplierInherit(orm.Model):
    """ Model name: Add relations
    """

    _inherit = 'carrier.supplier'

    _columns = {
        'mode_ids': fields.one2many(
            'carrier.supplier.mode', 'supplier_id', 'Modalità',
            help='Modalità di consegna del corriere attuale',
        ),
        'child_ids': fields.one2many(
            'carrier.supplier', 'broker_id', 'Corrieri'),
    }
