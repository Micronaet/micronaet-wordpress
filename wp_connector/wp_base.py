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
import time
import logging
import woocommerce
import sys
import pdb
import requests
import pickle
import telepot
from datetime import datetime
from openerp.osv import fields, osv, expression, orm
from openerp.tools.translate import _
from openerp.tools.float_utils import float_round as round
from slugify import slugify

_logger = logging.getLogger(__name__)


class ProductProductWebBrand(orm.Model):
    """ Model name: ProductProductWebBrand
    """

    _name = 'product.product.web.brand'
    _description = 'Web Brand'
    _rec_name = 'name'
    _order = 'name'

    _columns = {
        'name': fields.char(
            'Brand', size=64, required=True, translate=True),
        'code': fields.char(
            'Sigla', size=10, required=True,
            help='Sigla utilizzata nelle importazioni'),
        'description': fields.text('Description for web', translate=True),

        # Translate fields:
        'wp_it_id': fields.integer('WP it ID'),
        'wp_en_id': fields.integer('WP en ID'),
        }


class ProductProductWebMaterial(orm.Model):
    """ Model name: ProductProductWebMaterial
    """

    _name = 'product.product.web.material'
    _description = 'Web material'
    _rec_name = 'name'
    _order = 'name'

    _columns = {
        'name': fields.char(
            'Material', size=64, required=True, translate=True),
        'code': fields.char('Sigla', size=10, required=True,
            help='Sigla utilizzata nelle importazioni'),
        'description': fields.text('Description for web', translate=True),

        # Translate fields:
        'wp_it_id': fields.integer('WP it ID'),
        'wp_en_id': fields.integer('WP en ID'),
        }


class ConnectorServer(orm.Model):
    """ Model name: ConnectorServer
    """
    _inherit = 'connector.server'

    def publish_image_on_wordpress(self, cr, uid, ids, context=None):
        """ Scheduled action for publish image on web site and
        """
        if context is None:
            context = {}
        force_remove = False  # TODO put it after upload image in product

        # Media access:
        connector = self.browse(cr, uid, ids, context=context)[0]
        root_url = connector.wp_url
        username = connector.wp_username
        password = connector.wp_password
        author_id = connector.wp_user_id
        auth = (username, password)
        url = '%s/wp-json/wp/v2/media' % root_url

        for album in connector.album_ids:
            _logger.info('Seek album: %s' % album.name)
            # Read pickle file for album
            album_path = os.path.expanduser(album.path)
            pickle_path = os.path.join(album_path, 'pickle')
            pickle_file = os.path.join(
                pickle_path, 'wordpress_%s.pickle' % album.code)
            if os.path.isfile(pickle_file):
                try:
                    pickle_album = pickle.load(open(pickle_file, 'rb'))
                except:
                    _logger.error('Pickle file damnaged, restore from Dropbox')
                    raise osv.except_osv(
                            _('Errore'),
                            _('Pickle file danneggiato, ripristinare da '
                              'Dropbox una versione recente: '
                              '%s' % pickle_file),
                            )
            else:
                pickle_album = {}
                os.system('mkdir -p %s' % pickle_path)

            for root, folders, files in os.walk(album_path):
                for filename in files:
                    if filename.split('.')[-1].upper() != 'JPG':
                        _logger.error('Not an image: %s' % filename)
                        continue

                    fullname = os.path.join(root, filename)
                    if fullname not in pickle_album:
                        pickle_album[fullname] = {
                            'modify': False,
                            'media_id': False,
                            'url': url,
                            'remove': [],  # media_id to remove when updated
                        }
                    # Check modify date:
                    (
                        mode, ino, dev, nlink, uid, gid, size,
                        atime, mtime, ctime) = os.stat(fullname)

                    modify_time = time.ctime(mtime)
                    if modify_time != pickle_album[fullname]['modify'] or \
                            not pickle_album[fullname]['media_id']:
                        pickle_album[fullname]['modify'] = modify_time

                        # Update web site:
                        headers = {
                            'Content-Type': 'image/jpg',
                            'Content-Disposition':
                                'attachment; filename="%s"' % fullname,
                        }
                        params = {
                            'lang': 'it',
                            'title': filename,
                            'status': 'publish',
                            'author': author_id,
                            'alt_text': filename,
                            'caption': filename,  # TODO change some data?
                            'description': filename,
                        }

                        # Open file in different ways:
                        if not os.path.isfile(fullname):
                            _logger.error(
                                'File deleted during procedure: %s' % filename)
                            continue
                        file_handler = open(fullname, 'rb')  # handler
                        image_data = file_handler.read()  # binary data

                        reply = requests.post(
                            url,
                            headers=headers,
                            params=params,
                            data=image_data,
                            auth=auth,
                        )
                        try:
                            reply_json = reply.json()
                            wp_id = reply_json['id']
                            image_url = reply_json['source_url']
                        except:  # Error reply
                            _logger.error(reply.text)
                            continue

                        # Manage old media:
                        old_media_id = pickle_album[fullname]['media_id']
                        if old_media_id:
                            pickle_album[fullname]['remove'].append(
                                old_media_id)
                        pickle_album[fullname]['media_id'] = wp_id
                        pickle_album[fullname]['url'] = image_url
                        _logger.info('Update image: %s' % filename)

                        # -----------------------------------------------------
                        # Delete old:
                        # -----------------------------------------------------
                        if force_remove:
                            for remove_id in pickle_album[fullname]['remove']:
                                delete_url = '%s/wp-json/wp/v2/media/%s' % (
                                    root_url, remove_id)
                                params = {'force': True, }
                                try:
                                    reply = requests.delete(
                                        delete_url,
                                        # headers=headers
                                        params=params,
                                        auth=auth,
                                    )
                                    _logger.info(
                                        'Old image deleted' if reply.ok else
                                        'Old image not deleted!')
                                except:
                                    _logger.error(
                                        'Error remove media: %s' % remove_id)
                    else:
                        _logger.info('No need to update: %s' % filename)

                    # Store every image published:
                    pickle.dump(pickle_album, open(pickle_file, 'wb'))
                break  # Not subfolders

            # Store pickle file for every album:
            pickle.dump(pickle_album, open(pickle_file, 'wb'))
        return True

    # -------------------------------------------------------------------------
    # Utility:
    # -------------------------------------------------------------------------
    def get_lang_slug(self, name, lang):
        """ Slug problem with lang
        """
        slug = slugify(name)
        return slug + ('' if lang == 'it' else '-en')

    def wp_loopcall(self, wcapi, mode, call, data=None, params=None):
        """ Call in loop mode the end point procedure
        """
        # Define correct call:
        if mode in ('put', 'post', 'get'):
            wp_function = eval('wcapi.%s' % mode)
        else:
            _logger.error('Cannot call wcapi.%s' % mode)
            return False  # Will raise error in super function

        # Infinite loop call:
        try_total = 0
        while True:
            try_total += 1
            try:
                if mode == 'get':
                    return wp_function(call, params=params)
                else:  # post, put
                    return wp_function(call, data)
            except:
                pdb.set_trace()
                _logger.error(
                    'Server error [try #%s] mode: %s %s %s %s\n%s' % (
                        try_total,
                        mode,
                        call,
                        data,
                        params,
                        sys.exc_info(),
                    ))
                # TODO Raise with some external method
                continue  # new try
        return False  # Never passed from here

    def get_wp_connector(self, cr, uid, ids, context=None):
        """ Connect with Word Press API management
        """
        timeout = 600  # TODO parametrize

        connector = self.browse(cr, uid, ids, context=context)[0]
        if not connector.wordpress:
            _logger.info('Not Wordpress connector')

        _logger.info('>>> Connecting: %s%s API: %s, timeout=%s' % (
            connector.wp_url,
            connector.wp_version,
            connector.wp_api,
            timeout,
            ))
        try:
            return woocommerce.API(
                url=connector.wp_url,
                consumer_key=connector.wp_key,
                consumer_secret=connector.wp_secret,
                wp_api=connector.wp_api,
                version=connector.wp_version,
                timeout=timeout,
                )
        except:
            _logger.error('Cannot connect to Wordpress!!')

    def update_wp_volume(self, cr, uid, ids, context=None):
        """ Update all product
        """
        image_pool = self.pool.get('product.product.web.server')
        image_ids = image_pool.search(cr, uid, [
            ('connector_id', '=', ids[0]),
            ], context=context)
        _logger.info('Updating volume for %s product' % len(image_ids))
        return image_pool.update_wp_volume(
           cr, uid, image_ids, context=context)

    def get_gtin(self, line):
        """ Return GTIN number depend on parameters
        """
        ean13 = line.force_ean13 or ''  # line.product_id.ean13 or ''
        if line.connector_id.wp_ean_gtin and ean13:
            return ean13
        return ''

    def telegram_send_message(
            self, message, token, group):
        """ Send message with Telegram
        """
        try:
            bot = telepot.Bot(str(token))
            bot.getMe()

            bot.sendMessage(
                group,
                message,
            )
        except:
            _logger.error('Error sending Telegram message')
            return False
        return True

    _columns = {
        'wp_publish_image': fields.boolean('Pubblica immagini'),
        'wp_ean_gtin': fields.boolean('EAN GTIN', help='Use EAN code in GTIN'),
        'wordpress': fields.boolean('Wordpress', help='Wordpress web server'),

        'wp_all_category': fields.boolean(
            'All category',
            help='Public all product with category and parent also'),

        # Media:
        'wp_username': fields.char('WP username', size=180),
        'wp_password': fields.char('WP password', size=180),
        'wp_user_id': fields.integer('WP Author ID'),

        'wp_url': fields.char('WP URL', size=180),
        'wp_key': fields.char('WP consumer key', size=180),
        'wp_secret': fields.char('WP consumer secret', size=180),

        'wp_api': fields.boolean('WP API'),
        'wp_version': fields.char('WP Version', size=10),

        'album_ids': fields.many2many(
            'product.image.album',
            'connector_album_rel', 'server_id', 'album_id', 'Album'),
        'wp_category': fields.selection([
            ('out', 'ODOO Original WP replicated'),
            ('in', 'WP Original ODOO replicated'),
            ], 'Category management', required=True),

        # Telegram:
        'telegram_message': fields.boolean(
            'Attiva notifica Telegram',
            help='Ad ogni nuovo ordine viene comunicato in Telegram nel gruppo'
                 'di amministrazione sito'),
        'telegram_token': fields.char('Telegram Token', size=50),
        'telegram_group': fields.char('Telegram Token', size=50),
    }

    _defaults = {
        'wp_api': lambda *x: True,
        'wp_version': lambda *x: 'wc/v3',
        'wp_category': lambda *x: 'out',
        'wp_all_category': lambda *x: True,
        }


class ProductProduct(orm.Model):
    """ Model name: ProductProduct
    """

    _inherit = 'product.product'

    def auto_package_assign(self, cr, uid, ids, context=None):
        """ Auto assign code
        """
        package_pool = self.pool.get('product.product.web.package')
        for product in self.browse(cr, uid, ids, context=context):
            default_code = product.default_code or ''
            if not default_code:
                _logger.error('No default code, no package assigned!')
                continue

            # -----------------------------------------------------------------
            # Search:
            # -----------------------------------------------------------------
            # Mode 6:
            search_code = '%-6s' % default_code[:6]
            package_ids = package_pool.search(cr, uid, [
                ('name', 'ilike', search_code),
                ], context=context)
            if package_ids:
                self.write(cr, uid, [product.id], {
                    'model_package_id': package_ids[0],
                    }, context=context)

                _logger.warning('Code 6 "%s" found #%s !' % (
                    search_code, len(package_ids)))
                continue

            # Mode 3:
            search_code = default_code[:3]
            package_ids = package_pool.search(cr, uid, [
                ('name', 'ilike', search_code),
                ], context=context)
            if package_ids:
                self.write(cr, uid, [product.id], {
                    'model_package_id': package_ids[0],
                    }, context=context)
                _logger.warning(
                    'Auto assign package: Code 3 "%s" found #%s !' % (
                        search_code, len(package_ids)))
            else:
                _logger.info(
                    'Auto assign package: Code not found %s !' % default_code)
        return True

    _columns = {
        # 'wp_id': fields.integer('Worpress ID'),
        # 'wp_lang_id': fields.integer('Worpress translate ID'),
        'emotional_short_description': fields.text(
            'Emozionale breve', translate=True),
        'emotional_description': fields.text(
            'Emozionale dettagliata', translate=True),
        'model_package_id': fields.many2one(
            'product.product.web.package', 'Package'),
        }


class ProductImageFile(orm.Model):
    """ Model name: ProductImageFile
    """

    _inherit = 'product.image.file'

    _columns = {
        'dropbox_link': fields.char('Dropbox link', size=100),
        }


'''class ProductProductWebServerLang(orm.Model):
    """ Model name: ProductProductWebServer ID for lang
    """

    _name = 'product.product.web.server.lang'
    _description = 'Product published with lang'
    _rec_name = 'lang'    
    
    _columns = {
        'web_id': fields.many2one('product.product.web.server', 'Link'),
        'lang': fields.char('Lang code', size=10, required=True),
        'wp_id': fields.integer('WP ID', required=True),
        }
    
    _defaults = {
        # Default value:
        'wp_type': lambda *x: 'simple',
        }    
'''


class ProductProductWebCategory(orm.Model):
    """ Model name: ProductProductWebPackage
    """

    _name = 'product.product.web.category'
    _description = 'Category template'
    _order = 'name'

    # -------------------------------------------------------------------------
    # Button event:
    # -------------------------------------------------------------------------
    def update_product_category(self, cr, uid, ids, context=None):
        """ Update product category for all selected item of this connector
        """
        line_pool = self.pool.get('product.product.web.server')

        current = self.browse(cr, uid, ids, context=context)[0]
        category_ids = [item.id for item in current.category_ids]

        line_ids = line_pool.search(cr, uid, [
            ('connector_id', '=', current.connection_id.id),
            ('product_id.default_code', '=ilike', '%s%%' % current.name)
            ], context=context)

        if line_ids:
            line_pool.write(cr, uid, line_ids, {
                'wordpress_categ_ids': [(6, 0, category_ids)],
                }, context=context)

            _logger.info('Updated %s records' % len(line_ids))
        return True

    _columns = {
        'connection_id': fields.many2one('connector.server', 'Server',
            required=True),
        'name': fields.char('Codice padre', size=20, required=True),
        'category_ids': fields.many2many(
            'product.public.category', 'template_web_category_rel',
            'product_id', 'category_id',
            'Category', required=True),
        }

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'Nome duplicato!'),
        ]


class ProductProductWebPackage(orm.Model):
    """ Model name: ProductProductWebPackage
    """

    _name = 'product.product.web.package'
    _description = 'Package data'
    _order = 'name'

    # -------------------------------------------------------------------------
    # Button:
    # -------------------------------------------------------------------------
    def auto_package_assign(self, cr, uid, ids, context=None):
        """ Auto assign code
        """
        model_package_id = ids[0]
        current = self.browse(cr, uid, model_package_id, context=context)

        product_pool = self.pool.get('product.product')
        product_ids = product_pool.search(cr, uid, [
            ('default_code', '=ilike', '%s%%' % current.name),
            ], context=context)
        _logger.warning('Updating %s product...' % len(product_ids))
        return product_pool.write(cr, uid, product_ids, {
            'model_package_id': model_package_id,
            }, context=context)

    _columns = {
        'name': fields.char('Codice padre', size=10, required=True),

        'pcs_box': fields.integer('pcs / box'),
        'pcs_pallet': fields.integer('pcs / pallet'),

        'net_weight': fields.integer('Peso netto (gr)'),
        'gross_weight': fields.integer('Peso lordo (gr)'),

        'box_width': fields.integer('Box: larg.'),
        'box_depth': fields.integer('Box: prof..'),
        'box_height': fields.integer('Box: alt.'),

        'pallet_dimension': fields.char('Dim. Pallet', size=30),
        }

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'Nome duplicato!'),
        ]


class ResCompany(orm.Model):
    """ Model name: Company parameters
    """

    _inherit = 'res.company'

    _columns = {
        'wp_existence_mode': fields.selection([
            ('locked', 'Netto - Bloccati'),
            ('ordered', 'Netto - Ordinati (non prev.)'),
            ], 'WP stato prodotto'),
        }

    _defaults = {
        'wp_existence_mode': lambda *x: 'locked',
        }


class ProductProductStockLog(orm.Model):
    """ Model name: Product Product Stock Log
    """

    _name = 'product.product.stock.log'
    _description = 'Manual stock log'
    _order = 'create_date desc'

    _columns = {
        'name': fields.char('Commento', size=40),
        'create_date': fields.datetime('Data'),
        'create_uid': fields.many2one('res.users', 'Da'),
        'web_product_id': fields.many2one(
            'product.product.web.server', 'Web product'),
        'old_qty': fields.float('Vecchia', digits=(10, 2)),
        'new_qty': fields.float('Nuova', digits=(10, 2)),
    }


class ProductProductWebServer(orm.Model):
    """ Model name: ProductProductWebServer
    """

    _inherit = 'product.product.web.server'

    def write(self, cr, uid, ids, vals, context=None):
        """ Update redord(s) comes in {ids}, with new value comes as {vals}
            return True on success, False otherwise
            @param cr: cursor to database
            @param uid: id of current user
            @param ids: list of record ids to be update
            @param vals: dict of new values to be set
            @param context: context arguments, like lang, time zone

            @return: True on success, False otherwise
        """
        if context is None:
            context = {}

        if 'force_this_stock' in vals:
            log_pool = self.pool.get('product.product.stock.log')
            current = self.browse(cr, uid, ids, context=context)[0]
            # if current.force_manual_stock:
            # Always save stock movement record!
            data = {
                'web_product_id': current.id,
                'old_qty': current.force_this_stock,
                'new_qty': vals['force_this_stock'],
                'name': context.get(
                    'forced_manual_stock_comment', 'Modifica manuale'),
            }
            log_pool.create(cr, uid, data, context=context)

        return super(ProductProductWebServer, self).write(
            cr, uid, ids, vals, context=context)

    '''def create(self, cr, uid, vals, context=None):
        """ Create a new record for a model
        ClassName
            @param cr: cursor to database
            @param uid: id of current user
            @param vals: provides a data for new record
            @param context: context arguments, like lang, time zone

            @return: returns a id of new record
        """

        res_id = super(ClassName, self).create(cr, uid, vals, context=context)
        return res_id'''

    # -------------------------------------------------------------------------
    # Utility:
    # -------------------------------------------------------------------------
    def get_existence_for_product(self, cr, uid, line, context=None):
        """ Return real existence for web site
        """
        webproduct_pool = self.pool.get('product.product.web.server')

        # Update stock on if disabled:
        user_pool = self.pool.get('res.users')
        user = user_pool.browse(cr, uid, uid, context=context)
        if user.no_inventory_status:
            user_pool.write(cr, uid, uid, {
                'no_inventory_status': False,
            }, context=context)

        # ---------------------------------------------------------------------
        # Call from external:
        # ---------------------------------------------------------------------
        if type(line) == int:
            line = webproduct_pool.browse(cr, uid, line, context=context)
        product = line.product_id

        # ---------------------------------------------------------------------
        # DB with MRP:
        # ---------------------------------------------------------------------
        company = product.company_id
        force_manual_stock = line.force_manual_stock
        force_this_stock = int(line.force_this_stock)
        force_min_stock = int(line.force_min_stock)
        if force_manual_stock:
            stock_quantity = force_this_stock
            reset_text = 'FIXED'
        else:
            if company.wp_existence_mode == 'locked':
                # Net - locked mode:
                stock_quantity = int(
                    product.mx_net_mrp_qty - product.mx_mrp_b_locked)

            else:
                # Net - ordered mode:
                stock_quantity = int(product.mx_lord_mrp_qty +
                                     product.mx_oc_out_prev - product.mx_of_in)

            # stock_quantity = int(
            # product.mx_lord_mrp_qty + product.mx_oc_out_prev)

            if force_min_stock and stock_quantity < force_min_stock:
                stock_quantity = force_min_stock
                reset_text = 'MIN'

            if stock_quantity < 0:
                reset_text = 'NEG'
                stock_quantity = 0
            else:
                reset_text = ''

        comment = 'Netto - OC: %s + Prev.: %s = %s %s (min. %s) (fisso %s)' % (
            product.mx_lord_mrp_qty,
            product.mx_oc_out_prev,
            stock_quantity,
            reset_text,
            force_min_stock,
            force_this_stock if force_manual_stock else '/',
            )

        # TODO manage q x pack?
        # q_x_pack = product.q_x_pack or 1
        # stock_quantity //= q_x_pack
        return stock_quantity, comment

    def get_category_block_for_publish(self, item, lang):
        """ Get category block for data record WP
        """
        categories = []
        for category in item.wordpress_categ_ids:
            wp_id = eval('category.wp_%s_id' % lang)
            wp_parent_id = eval('category.parent_id.wp_%s_id' % lang)
            if not wp_id:
                continue
            categories.append({'id': wp_id})
            if category.connector_id.wp_all_category and category.parent_id:
                categories.append({'id': wp_parent_id})
        return categories

    # -------------------------------------------------------------------------
    # Button event:
    # -------------------------------------------------------------------------
    '''def clean_reference(self, cr, uid, ids, context=None):
        """ Delete all link
        """
        assert len(ids) == 1, 'Works only with one record a time'
        
        lang_pool = self.pool.get('product.product.web.server.lang')
        lang_ids = lang_pool.search(cr, uid, [
            ('web_id', '=', ids[0]),
            ], context=context)
        return lang_pool.unlink(cr, uid, lang_ids, context=context)    
        '''

    def open_image_list_product(self, cr, uid, ids, context=None):
        """
        """
        model_pool = self.pool.get('ir.model.data')
        view_id = model_pool.get_object_reference(
            cr, uid,
            'wp_connector', 'view_product_product_web_server_form')[1]

        return {
            'type': 'ir.actions.act_window',
            'name': _('Image detail'),
            'view_type': 'form',
            'view_mode': 'form,form',
            'res_id': ids[0],
            'res_model': 'product.product.web.server',
            'view_id': view_id, # False
            'views': [(view_id, 'form'), (False, 'tree')],
            'domain': [],
            'context': context,
            'target': 'new',
            'nodestroy': False,
            }

    def wp_clean_code(self, default_code, destination='wp'):
        """ Return default code for Wordpress
        """
        if destination == 'wp':
            return default_code.replace(' ', '&nbsp;')
        else:  # odoo
            return default_code.replace('&nbsp;', ' ')

    def get_pickle_album_file(self, image, context=None):
        """ Read pickle album and return media ID
        """
        if context is None:
            context = {}
        return_url = context.get('return_url')
        album = image.album_id
        album_path = album.path

        pickle_filename = os.path.join(
            album_path,
            'pickle',
            'wordpress_%s.pickle' % album.code,
        )
        pickle_album = pickle.load(open(pickle_filename, 'rb'))
        image_record = pickle_album.get(
            os.path.join(album_path, image.filename), {})
        if return_url:
            url = image_record.get('url')
            return url
        else:
            media_id = image_record.get('media_id')
            return media_id

    def get_wp_image(self, item, variant=False):
        """ Extract complete list of images (single if variant mode)
        """
        images = []
        for image in item.wp_dropbox_images_ids:
            media_id = self.get_pickle_album_file(image)
            if not media_id:
                _logger.error('Image not published yet: %s' % image.filename)

            src = {'id': media_id, }
            if variant:
                return src  # Variant only one image!
            images.append(src)
        return images

    def get_wp_price_external(self, cr, uid, line_id, context=None):
        """ External call for price
        """
        return self.get_wp_price(
            self.browse(cr, uid, line_id, context=context))

    def get_wp_price(self, line):
        """ Extract price depend on force, discount and VAT
        """
        gap = 0.00000001
        if line.force_price:
            price = line.force_price
        else:
            product = line.product_id
            connector = line.connector_id
            price = product.lst_price

            # Correct price on product:
            price_multi = line.price_multi or 1.0
            price_extra = line.price_extra * price_multi
            price *= price_multi

            # Correct price for this connector:
            price = price * (
                100.0 - connector.discount) / 100.0

            # Add unit input:
            price += price_extra

            # Add input VAT:
            price += connector.add_vat * price / 100.0

            # Approx:
            price = round((price + gap), connector.approx)
            # Use gap correction for float problem in python

            # After check min price:
            if price < line.connector_id.min_price:
                price = line.connector_id.min_price
        return price

    def publish_now(self, cr, uid, ids, context=None):
        """ Publish now button
            Used also for more than one elements (not only button click)
            Note all product must be published on the same web server!
        """
        default_lang = 'it'

        """
        # ---------------------------------------------------------------------
        # LOG WP ID bugfix WP Timeout:
        # ---------------------------------------------------------------------
        wp_files = []  # Used for delete (end of proc.) and fast read

        # Prepare folder:
        wp_path = os.path.expanduser('~/wordpress/log')
        os.system('mkdir -p %s' % wp_path)

        # Read fast all files:
        for root, folders, files in os.walk(wp_path):
            for filename in files:
                if filename[-3:] != 'log':
                    _logger.warning('No WP log file: %s [jump]' % filename)
                wp_files.append(os.path.join(root, filename))
            break  # only this folder

        # TODO manage externally not during thi operation?
        for fullname in wp_files:
            _logger.info('Updating with: %s' % filename)
            this_log = open(fullname, 'r')
            for line in this_log:
                line = line.strip()
                if not line:
                    continue

                # Update ID:
                web_id, lang, wp_id = line.split('|')
                self.write(cr, uid, [int(web_id)], {
                    'wp_%s_id' % lang: int(wp_id),
                }, context=context)
            this_log.close()
            _logger.info('Updating with: %s' % filename)

        # New log file for this session:
        wp_filename = os.path.join(
            wp_path,
            ('%s.log' % datetime.now()).replace('-', '').replace(':', ''),
        )
        wp_files.append(wp_filename)  # Also this in remove list
        wp_file = open(wp_filename, 'w')
        # ---------------------------------------------------------------------
        """

        # Data publish selection (remove this part from publish:
        unpublished = []

        if context is None:
            context = {}

        override_sku = context.get('override_sku', False)
        log_excel = context.get('log_excel', False)

        first_proxy = self.browse(cr, uid, ids, context=context)[0]
        connector = first_proxy.connector_id
        if not connector.wordpress:
            _logger.warning('Not a wordpress proxy, call other')
            return super(ProductProductWebServer, self).publish_now(
                cr, uid, ids, context=context)

        if connector.wp_publish_image:
            _logger.warning('Publish all on wordpress with image')
        else:
            unpublished.append('image')
            _logger.warning('Publish all on wordpress without image')

        # ---------------------------------------------------------------------
        #                         WORDPRESS Publish:
        # ---------------------------------------------------------------------
        product_pool = self.pool.get('product.product')
        server_pool = self.pool.get('connector.server')
        # lang_pool = self.pool.get('product.product.web.server.lang')

        wcapi = server_pool.get_wp_connector(
            cr, uid, [first_proxy.connector_id.id], context=context)

        # Context used here:
        context_lang = context.copy()

        # Read first element only for setup parameters:
        connector = first_proxy.connector_id
        context_lang['album_id'] = first_proxy.connector_id.album_id.id
        context['album_id'] = first_proxy.connector_id.album_id.id

        # ---------------------------------------------------------------------
        # Publish image:
        # ---------------------------------------------------------------------
        # TODO (save link)

        # ---------------------------------------------------------------------
        # Publish product (lang management)
        # ---------------------------------------------------------------------
        translation_lang = {}

        # First lang = original, second translate
        for odoo_lang in ('it_IT', 'en_US'):
            lang = odoo_lang[:2]  # WP lang
            context_lang['lang'] = odoo_lang  # self._lang_db

            for item in self.browse(cr, uid, ids, context=context_lang):

                # Readability:
                product = item.product_id
                default_code = product.default_code or u''
                if override_sku == False:
                    sku = default_code
                else:
                    sku = override_sku

                # Description:
                name = item.force_name or product.name or u''
                description = item.force_description or \
                    product.emotional_description or \
                    product.large_description or u''
                short = product.emotional_short_description or name or u''
                lifetime_warranty = item.lifetime_warranty

                price = u'%s' % self.get_wp_price(item)
                sale_price = u'%s' % (item.wp_web_discounted_net or '')

                # weight = u'%s' % product.weight
                weight = u'%s' % item.wp_volume  # X Used for volume manage
                status = 'publish' if item.published else 'private'
                stock_quantity, stock_comment = \
                    self.get_existence_for_product(
                        cr, uid, item, context=context)
                wp_id = eval('item.wp_%s_id' % lang)
                wp_it_id = item.wp_it_id  # Default product for language
                # fabric, type_of_material

                # -------------------------------------------------------------
                # Linked blocks:
                # -------------------------------------------------------------
                # Upsell:
                wp_upsell_ids = []
                for related in item.linked_ids:
                    related_wp_id = eval('related.wp_%s_id' % lang)
                    if related_wp_id:
                        wp_upsell_ids.append(related_wp_id)

                # Cross sell:
                wp_cross_sell_ids = []
                for related in item.cross_ids:
                    related_wp_id = eval('related.wp_%s_id' % lang)
                    if related_wp_id:
                        wp_cross_sell_ids.append(related_wp_id)

                # -------------------------------------------------------------
                # Images block:
                # -------------------------------------------------------------
                if 'image' not in unpublished:
                    images = self.get_wp_image(item)
                else:
                    images = []

                # -------------------------------------------------------------
                # Category block:
                # -------------------------------------------------------------
                categories = self.get_category_block_for_publish(item, lang)

                # Text data (in lang):
                data = {
                    'name': name,
                    'description': description,
                    'short_description': short,
                    'sku': self.wp_clean_code(sku),  # XXX not needed
                    'lang': lang,
                    'lifetime_warranty': lifetime_warranty,
                    'multipack':
                        str(int(item.price_multi)) if item.price_multi else '',

                    # It doesn't update:
                    'wp_type': item.wp_type,

                    # TODO 'weight': weight,
                    }

                if images:
                    data['images'] = images

                if categories:
                    data['categories'] = categories

                if wp_upsell_ids:
                    data['upsell_ids'] = wp_upsell_ids
                if wp_cross_sell_ids:
                    data['cross_sell_ids'] = wp_cross_sell_ids

                if lang == default_lang:
                    # Numeric data:
                    data.update({
                        'type': item.wp_type,
                        # 'sku': self.wp_clean_code(sku),
                        'regular_price': price,
                        'sale_price': sale_price,
                        'stock_quantity': stock_quantity,
                        'status': status,
                        'catalog_visibility': 'visible',
                        # catalog  search  hidden

                        'weight_aditional_info': item.weight_aditional_info,

                        # Bullet point:
                        'bullet_point_1': item.bullet_point_1,
                        'bullet_point_2': item.bullet_point_2,
                        'bullet_point_3': item.bullet_point_3,
                        'bullet_point_4': item.bullet_point_4,
                        'bullet_point_5': item.bullet_point_5,
                        })

                else:  # Other lang (only translation
                    if not wp_it_id:
                        _logger.error(
                            'Product %s without default IT [%s]' % (
                                lang, default_code))
                        continue

                    # Translation:
                    data.update({
                        'translations': {'it': wp_it_id},
                        })

                # -------------------------------------------------------------
                #                         Update:
                # -------------------------------------------------------------
                if wp_id:
                    try:
                        call = 'products/%s' % wp_id
                        reply = server_pool.wp_loopcall(
                            wcapi, 'put', call, data=data).json()
                        if log_excel != False:
                            log_excel.append((
                                'put', call, u'%s' % (data, ),
                                u'%s' % (reply, ))
                            )
                        _logger.info('%s\n%s' % (call, data))

                        if reply.get('code') in (
                                'product_invalid_sku',
                                'woocommerce_rest_product_invalid_id'):
                            pass  # TODO Manage this case?
                            # wp_id = False # will be created after
                        else:
                            _logger.warning('Product %s lang %s updated!' % (
                                wp_id, lang))
                    except:
                        # TODO manage this error if present
                        _logger.error('Not updated ID %s lang %s [%s]!' % (
                            wp_id, lang, data))

                # -------------------------------------------------------------
                #                         Create:
                # -------------------------------------------------------------
                if not wp_id:
                    # Create (will update wp_id from now)
                    try:
                        if 'image' not in data:
                            images = self.get_wp_image(item)
                        if images:
                            data['images'] = images

                        call = 'products'
                        reply = server_pool.wp_loopcall(
                            wcapi, 'post', call, data=data).json()
                        if log_excel != False:
                            log_excel.append(('post', call, u'%s' % (data, ),
                                u'%s' % (reply, )))
                    except:  # Timeout on server:
                        _logger.error('Server timeout: %s' % (data, ))
                        continue

                    try:
                        if reply.get('code') == 'product_invalid_sku':
                            wp_id = reply['data']['resource_id']
                            _logger.error(
                                'Product %s lang %s duplicated [%s]!' % (
                                    wp_id, lang, reply))

                        else:
                            wp_id = reply['id']
                            _logger.warning('Product %s lang %s created!' % (
                                wp_id, lang))

                            """
                            # -------------------------------------------------
                            # LOG on file WP ID for timeout problem
                            # -------------------------------------------------
                            import pdb; pdb.set_trace()
                            if wp_id:
                                wp_file.write('%s|%s|%s\n' % (
                                    item.id,
                                    lang,
                                    wp_id,
                                ))
                                wp_file.flush()
                            # -------------------------------------------------
                            """
                    except:
                        raise osv.except_osv(
                            _('Error'),
                            _('Reply not managed: %s' % reply),
                            )
                        # continue

                    if wp_id:
                        self.write(cr, uid, [item.id], {
                            'wp_%s_id' % lang: wp_id,
                            }, context=context)

                # Save translation of ID (for language product)
                if default_code not in translation_lang:
                    translation_lang[default_code] = {}
                translation_lang[default_code][lang] = (wp_id, name)

        return translation_lang

    # -------------------------------------------------------------------------
    # Function fields:
    # -------------------------------------------------------------------------
    def _get_album_images(self, cr, uid, ids, fields, args, context=None):
        """ Fields function for calculate
        """
        res = {}
        for current in self.browse(cr, uid, ids, context=context):
            server_album_ids = [
                item.id for item in current.connector_id.album_ids]

            res[current.id] = []
            if current.product_id.image_ids:
                for image in sorted(
                        current.product_id.image_ids,
                        key=lambda x: x.filename[:-4]):
                    if image.status == 'ok' and \
                            image.album_id.id in server_album_ids:
                        res[current.id].append(image.id)
                    # image.id for image in current.product_id.image_ids \
                    #    if image.album_id.id in server_album_ids],
                    #        key=lambda x: '' if not x else x.name)
        return res

    def _get_product_detail_items(
            self, cr, uid, ids, fields, args, context=None):
        """ Fields function for calculate
        """
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id] = {}

            product = line.product_id
            model = product.model_package_id
            if model:
                res[line.id] = {
                    'pack_l': float(model.box_width),
                    'pack_h': float(model.box_height),
                    'pack_p': float(model.box_depth),

                    'weight': float(model.gross_weight) / 1000.0,
                    'weight_net': float(model.net_weight) / 1000.0,

                    'q_x_pack': float(model.pcs_box),
                    'lst_price': product.lst_price,
                    # pallet dimension
                    }
            else:
                res[line.id] = {
                    'pack_l': product.pack_l,
                    'pack_h': product.pack_h,
                    'pack_p': product.pack_p,

                    'weight': product.weight,
                    'weight_net': product.weight_net,

                    'q_x_pack': product.q_x_pack,
                    'lst_price': product.lst_price,
                    }
        return res

    def update_wp_volume(self, cr, uid, ids, context=None):
        """ Update volume field
        """
        for item in self.browse(cr, uid, ids, context=context):
            product = item.product_id
            multi = item.price_multi or 1

            # A. Manual volume:
            if item.wp_manual_volume:
                volume = (
                    item.manual_pack_l *
                    item.manual_pack_p *
                    item.manual_pack_h)
                self.write(cr, uid, [item.id], {
                    'wp_volume': volume / 5000.0,
                }, context=context)
                _logger.warning(
                    'Manual volume updated: %s' % product.default_code)
                continue

            # B. Multipack:
            try:
                has_multipack = product.has_multipack
            except:
                has_multipack = False

            if has_multipack:
                q_x_pack = 1  # alway 1 in multipack
                volume = 0.0
                for pack in product.multi_pack_ids:
                    volume += pack.number * (
                        pack.height * pack.width * pack.length)

            # C. Single pack / template:
            else:
                q_x_pack = item.q_x_pack or 1
                l = item.pack_l
                p = item.pack_p
                h = item.pack_h
                if not all((l, p, h)):
                    _logger.error(
                        'No dimension for: %s' % item.product_id.default_code)
                    continue
                volume = l * p * h

            volume = volume / q_x_pack * multi  # / 1000000.0
            self.write(cr, uid, [item.id], {
                'wp_volume': volume / 5000.0,
                }, context=context)
            _logger.info(
                'Volume %s for: %s' % (
                    volume, item.product_id.default_code))

    _columns = {
        'stock_log_ids': fields.one2many(
            'product.product.stock.log', 'web_product_id', 'Log magazzino',
            help='Log cambi quantità magazzino forzato manualmente', ),
        'wp_it_id': fields.integer('WP it ID'),
        'wp_en_id': fields.integer('WP en ID'),

        'brand_id': fields.many2one('product.product.web.brand', 'Brand'),

        'lifetime_warranty': fields.boolean('Lifetime warranty'),

        # Unit price modify:
        'price_multi': fields.float(
            'Multiplier', digits=(16, 2),
            help='Moltiplica il prezzo di listino attuale'),
        'price_extra': fields.float(
            'Price input (unit.)', digits=(16, 2),
            help='Aggiunto dopo lo sconto l\'input (considerato al pezzo)'),

        'wordpress_categ_ids': fields.many2many(
            'product.public.category', 'product_wp_rel',
            'product_id', 'category_id',
            'Wordpress category'),
        'wp_dropbox_images_ids': fields.function(
            _get_album_images, method=True, obj='product.image.file',
            type='one2many', string='Album images',
            store=False),
        'wordpress': fields.related(
            'connector_id', 'wordpress',
            type='boolean', string='Wordpress'),
        # 'lang_wp_ids': fields.one2many(
        #    'product.product.web.server.lang', 'web_id', 'WD ID'),

        # ---------------------------------------------------------------------
        # Product related/linked fields:
        # ---------------------------------------------------------------------
        'model_package_id': fields.related(
            'product_id', 'model_package_id', readonly=1,
            type='many2one', relation='product.product.web.package',
            string='Modello imballo'),

        'pack_l': fields.function(
            _get_product_detail_items, method=True, readonly=1,
            type='float', string='L. Pack', multi=True, store=False,
            ),
        'pack_h': fields.function(
            _get_product_detail_items, method=True, readonly=1,
            type='float', string='H. Pack', multi=True, store=False,
            ),
        'pack_p': fields.function(
            _get_product_detail_items, method=True, readonly=1,
            type='float', string='P. Pack', multi=True, store=False,
            ),

        'weight': fields.function(
            _get_product_detail_items, method=True, readonly=1,
            type='float', string='Peso lordo', multi=True, store=False,
            ),
        # TODO remove?
        'weight_net': fields.function(
            _get_product_detail_items, method=True, readonly=1,
            type='float', string='Peso netto', multi=True, store=False,
            ),

        'lst_price': fields.function(
            _get_product_detail_items, method=True, readonly=1,
            type='float', string='Listino', multi=True, store=False,
            ),

        'q_x_pack': fields.function(
            _get_product_detail_items, method=True, readonly=1,
            type='float', string='Q. x Pack', multi=True, store=False,
            ),

        # ---------------------------------------------------------------------
        # Linked product
        # ---------------------------------------------------------------------
        'linked_ids': fields.many2many(
            'product.product.web.server', 'web_server_linked_rel',
            'product_id', 'linked_id',
            'Prodotti upsell'),

        'cross_ids': fields.many2many(
            'product.product.web.server', 'web_server_cross_rel',
            'product_id', 'linked_id',
            'Prodotti cross sell'),

        # ---------------------------------------------------------------------
        # Material link
        # ---------------------------------------------------------------------
        'material_ids': fields.many2many(
            'product.product.web.material', 'web_server_material_rel',
            'product_id', 'material_id',
            'Materiali'),

        # ---------------------------------------------------------------------
        # Link related to product
        # ---------------------------------------------------------------------
        'weight_aditional_info': fields.text(
            'Peso e dimensioni', widget='html',
            help='Indicare dimensioni e peso articoli (testo libero)',
            translate=True),

        # Product dimension:
        'product_pack_l': fields.related(
            'product_id', 'pack_l', type='float', string='Pack L prodotto'),
        'product_pack_h': fields.related(
            'product_id', 'pack_h', type='float', string='Pack H prodotto'),
        'product_pack_p': fields.related(
            'product_id', 'pack_p', type='float', string='Pack P prodotto'),

        # Forced manual for volume:
        'manual_pack_l': fields.float('L. pacco manuale', digits=(10, 2)),
        'manual_pack_h': fields.float('H. pacco manuale', digits=(10, 2)),
        'manual_pack_p': fields.float('P. pacco manuale', digits=(10, 2)),

        'emotional_short_description': fields.related(
            'product_id', 'emotional_short_description', type='text',
            string='Emozionale breve', translate=True),
        'emotional_description': fields.related(
            'product_id', 'emotional_description', type='text',
            string='Emozionale lunga', translate=True),

        'product_weight_net': fields.related(
            'product_id', 'weight_net', type='float',
            string='Peso lordo prodotto'),

        'product_weight': fields.related(
            'product_id', 'weight', type='float',
            string='Peso netto prodotto'),
        'product_lst_price': fields.related(
            'product_id', 'lst_price', type='float', string='Listino'),
        'product_q_x_pack': fields.related(
            'product_id', 'q_x_pack', type='float',
            string='Q x pack prodotto'),

        'wp_volume': fields.float(
            'Volume', digits=(16, 3),
            # required=True,
            ),
        'wp_manual_volume': fields.boolean('Volume manuale'),
        # ---------------------------------------------------------------------

        # Amazon data:
        'bullet_point_1': fields.text(
            'Bullet point 1', translate=True, size=100),
        'bullet_point_2': fields.text(
            'Bullet point 2', translate=True, size=100),
        'bullet_point_3': fields.text(
            'Bullet point 3', translate=True, size=100),
        'bullet_point_4': fields.text(
            'Bullet point 4', translate=True, size=100),
        'bullet_point_5': fields.text(
            'Bullet point 5', translate=True, size=100),

        'wp_type': fields.selection([
            ('simple', 'Simple product'),
            ('grouped', 'Grouped product'),
            ('external', 'External product'),
            ('variable', 'Variable product'),
            ], 'Wordpress type'),
        }
