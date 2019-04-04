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
import requests
import json
import base64

# -----------------------------------------------------------------------------
# Parameters:
# -----------------------------------------------------------------------------
token = '3bd65a19c578c8d32f758416b533da3e'

# -----------------------------------------------------------------------------
# End point calls:
# -----------------------------------------------------------------------------
endpoint_call = {
    # POST:
    'preview': 'https://spedizioni.topfly.net/api/shippings/preview',
    'create': 'https://spedizioni.topfly.net/api/shippings/create',
    # GET (Required ID as parameter)
    'label': 'https://spedizioni.topfly.net/api/shippings/%s/label/pdf',
    'delete': 'https://spedizioni.topfly.net/api/shippings/%s',
    }

# -----------------------------------------------------------------------------
# GET LABEL
# -----------------------------------------------------------------------------
shipping_id = '173247' #'00010918' #'2876079168236'
url = '%s?apitoken=%s' % (
    endpoint_call['label'] % shipping_id,
    token,
    )
print 'URL', url    
res = requests.get(url=url)

if not res.ok:
   print 'Error get file'
   sys.exit()
f_pdf = open('label.pdf', 'wb')
f_pdf.write(res.content)
f_pdf.close()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
