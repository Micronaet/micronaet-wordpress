# -*- coding: utf-8 -*-
###############################################################################
#
# ODOO (ex OpenERP) 
# Open Source Management Solution
# Copyright (C) 2001-2015 Micronaet S.r.l. (<http://www.micronaet.it>)
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
import erppeek
import ConfigParser
import subprocess

# -----------------------------------------------------------------------------
# Read configuration parameter (2 Databases): 
# -----------------------------------------------------------------------------
path = os.getcwd()
#os.path.dirname(os.path.realpath(__file__))
for config_file in ('openerp.cfg', 'gpb.openerp.cfg'):
    cfg_file = os.path.expanduser(os.path.join(path, '..', config_file))

    config = ConfigParser.ConfigParser()
    config.read([cfg_file])
    dbname = config.get('dbaccess', 'dbname')
    user = config.get('dbaccess', 'user')
    pwd = config.get('dbaccess', 'pwd')
    server = config.get('dbaccess', 'server')
    port = config.get('dbaccess', 'port')   # verify if it's necessary: getint

    connector_id = int(config.get('odoo', 'connector_id'))
    dropbox_color_path = config.get('odoo', 'dropbox_color_path')
    
    try:
        only_empty = eval(config.get('odoo', 'only_empty'))
    except:
        only_empty = False    
    try:
        verbose = eval(config.get('odoo', 'verbose'))
    except:
        verbose = False

    print 'Accesso: Server %s Database %s Read folder: %s [connector: %s]' % (
        server, dbname, dropbox_color_path, connector_id)

    # -----------------------------------------------------------------------------
    # Connect to ODOO:
    # -----------------------------------------------------------------------------
    odoo = erppeek.Client(
        'http://%s:%s' % (
            server, port), 
        db=dbname,
        user=user,
        password=pwd,
        )    

    # Pool used:
    image_pool = odoo.model('connector.product.color.dot')
    domain = [
        ('connector_id', '=', connector_id),
        ]

    if only_empty:
        domain.append(('dropbox_image', '=', False))

    image_ids = image_pool.search(domain)
    
    if not image_ids:
        print 'No image %s exit in folder, exit' % dbname
        sys.exit()

    print 'Found %s connector [ID %s]' % (len(image_ids), connector_id)
    image_db = {}
    for image in image_pool.browse(image_ids):
        image_db[image.image_name] = image.id

    print '%s Search image in path %s' % (dbname, dropbox_color_path)
    for root, folders, files in os.walk(dropbox_color_path):
        os.chdir(root)
        total = len(files)
        i = 0
        for f in files:
            i += 1
            if f not in image_db:
                if verbose:
                    print '%s. Not on DB/not empty/not load connector: %s [%s/%s]' % (
                        dbname, f, i, total)
                continue

            #fullname = os.path.join(root, f)    
            command = ['dropbox.py', 'sharelink', f]
            try:
                dropbox_link = subprocess.check_output(command)            
                if 'responding' in dropbox_link:
                    print '[ERR] %s Dropbox not responding jump %s [%s/%s]' % (
                        dbname, f, i, total)
                    continue    
                    
                image_pool.write([image_db[f]], {
                    'dropbox_image': 
                        dropbox_link.strip().rstrip('dl=0') + 'raw=1'
                    })
                print '[INFO] %s Dropbox sharelink file %s [%s/%s]' % (
                    dbname, f, i, total)
            except:
                print '[ERR] %s Cannot sharelink file %s [%s/%s]' % (
                    dbname, f, i, total)
        break

