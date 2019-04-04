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

# -----------------------------------------------------------------------------
# Parameters:
# -----------------------------------------------------------------------------
demo = True
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

service = (
    'SPEEDYRIT',
    'DHLAIR',
    'DHLAIRDOC',
    'DHLCAMION',
    'DHLITALIA',
    'GLSITALIA',
    'SDAEXTRALARGE',
    'SDAANDRIT',
    'UPSSTANDARD',
    'UPSSTDMULTI',
    'UPSEXPRESS',
    'UPSEXPRESSSAVER',
    'UPSEXPSAVDOC',
    'UPSEXPEDITED',  
    )
    
if demo:
    call = 'preview'
else:    
    call = 'create'

# -----------------------------------------------------------------------------
# Data exampce:
# -----------------------------------------------------------------------------
payload = {
    'header': {
        'test': demo, # Remove in production
        'codice_servizio': 'DHLAIR',
        'dest_destinatario': 'TEST SRL',
        'dest_via': 'Via di prova, 11',
        'dest_comune': 'BRESCIA',
        'dest_cap': '25100',
        'dest_provincia': 'BS',
        'dest_nazione': 'IT',
        'dest_tel': '3331122333',
        'dest_email': 'test@testme.it',
        'dest_riferimento': 'Mr.Gianni',
        'valore_merce': 0,
        'imp_assicurato': 0,
        'imp_contrassegno': 10,
        'note_spedizioniere': 'Tappi di plastica',
        'service_option_CONTRASSEGNO': True,
        },

    'colli': [{
        'tipo': 'merce',
        'pesodic': 4.5,
        'desc': 'una scatola',
        'p': 20,
        'l': 20,
        'h': 20
        }, {
        'tipo': 'documenti',
        'pesodic': 2.5,
        'desc': 'una busta pesante',
        'p': 25,
        'l': 30,
        'h': 2
        }
        ]
    }

# -----------------------------------------------------------------------------
# Header for calls:
# -----------------------------------------------------------------------------
headers = {
    'Content-Type': 'application/json;charset=utf-8',
    'user-agent': 'odoo/8.0.1',
    }

# -----------------------------------------------------------------------------
# CREATE / TEST
# -----------------------------------------------------------------------------
url = '%s?apitoken=%s' % (
    endpoint_call[call],
    token,
    )

res_json = requests.post(
    url=url,
    headers=headers,
    data=json.dumps(payload),
    )    
res = res_json.json()
print res

if 'error' in res:
    print 'ERROR: ', service, res['error']
else:
    print 'INFO: ', service    
shipping_id = res['shipping']['id']

# -----------------------------------------------------------------------------
# GET LABEL
# -----------------------------------------------------------------------------
if not demo and shipping_id:
    url = '%s?apitoken=%s' % (
        endpoint_call['label'] % shipping_id,
        token,
        )
    res = requests.get(url=url)
    if res.ok:
        #print res.content
        f_pdf = open('label.pdf', 'wb')
        f_pdf.write(res.content)
        f_pdf.close()
        
    
    # -------------------------------------------------------------------------
    # GET LABEL
    # -------------------------------------------------------------------------
    url = '%s?apitoken=%s' % (
        endpoint_call['delete'] % shipping_id,
        token,
        )
    res = requests.get(url=url
    print res.text
    if 'result' in res and res['result']:
        print 'Eliminato'
    else:
        print 'Non Eliminato'
            

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
