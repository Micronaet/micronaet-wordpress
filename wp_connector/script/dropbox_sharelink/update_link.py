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

#album_id = 9
#dropbox_path = '/home/thebrush/Dropbox/scambio/Wordpress'

# -----------------------------------------------------------------------------
# Read configuration parameter:
# -----------------------------------------------------------------------------
# From config file:
cfg_file = os.path.expanduser('../openerp.cfg')

config = ConfigParser.ConfigParser()
config.read([cfg_file])
dbname = config.get('dbaccess', 'dbname')
user = config.get('dbaccess', 'user')
pwd = config.get('dbaccess', 'pwd')
server = config.get('dbaccess', 'server')
port = config.get('dbaccess', 'port')   # verify if it's necessary: getint

album_id = int(config.get('odoo', 'album_id'))
dropbox_path = config.get('odoo', 'dropbox_path')

print 'Accesso: Server %s Database %s Read folder: %s [album: %s]' % (
    server, dbname, dropbox_path, album_id)

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
image_pool = odoo.model('product.image.file')
image_ids = image_pool.search([('album_id', '=', album_id)])
if not image_ids:
    print 'No image exit in folder, exit'
    sys.exit()

print 'Found %s album image [ID %s]' % (len(image_ids), album_id)
image_db = {}
for image in image_pool.browse(image_ids):
    image_db[image.filename] = image.id

print 'Search image in path %s' % dropbox_path

for root, folders, files in os.walk(dropbox_path):
    for f in files:
        if f not in image_db:
            print 'Not already loaded in ODOO: %s' % f
            continue

        fullname = os.path.join(root, f)    
        command = ['dropbox', 'sharelink', fullname]
        try:
            dropbox_link = subprocess.check_output(command)
            image_pool.write([image_db[f]], {
                'dropbox_link': dropbox_link.strip().rstrip('dl=0') + 'raw=1'
                })
        except:
            print 'Cannot sharelink file %s' % fullname        
    break

