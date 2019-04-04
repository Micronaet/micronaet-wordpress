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

token = '3bd65a19c578c8d32f758416b533da3e'
endpoint_call = {
    # POST:
    'preview': 'https://spedizioni.topfly.net/api/shippings/preview',
    'create': 'https://spedizioni.topfly.net/api/shippings/create',
    # GET (Required ID as parameter)
    'label': 'https://spedizioni.topfly.net/api/shippings/%s/label/pdf',
    'delete': 'https://spedizioni.topfly.net/api/shippings/%s',
    }

payload = {
    "header": {
        "test": True,
        "codice_servizio": "DHLAIR",
        "dest_destinatario": "TEST SRL",
        "dest_via": "Via di prova, 11",
        "dest_comune": "BRESCIA",
        "dest_cap": "25100",
        "dest_provincia": "BS",
        "dest_nazione": "IT",
        "dest_tel": "3331122333",
        "dest_email": "test@testme.it",
        "dest_riferimento": "Mr.Gianni",
        "valore_merce": 0,
        "imp_assicurato": 0,
        "imp_contrassegno": 10,
        "note_spedizioniere": "Tappi di plastica",
        "service_option_CONTRASSEGNO": True,
        },
    "colli": [{
            "tipo": "merce",
            "pesodic": 4.5,
            "desc": "una scatola",
            "p": 20,
            "l": 20,
            "h": 20
            },{
            "tipo": "documenti",
            "pesodic": 2.5,
            "desc": "una busta pesante",
            "p": 25,
            "l": 30,
            "h": 2
            }
            ]
    }
"""    
headers = {
    'user-agent': 'odoo/8.0.1',
    'access_token': token,
    'accept': 'application/json',
    'content-type':  'application/json;charset=utf-8',
    }
#headers = json.dumps(headers, ensure_ascii=False).encode('utf-8')
#headers["content-type"] = "application/json;charset=utf-8"

#res = request(
#    method='POST',
#    url=request_url,
#    params=payload,
#    data=
#    ) 
json_payload = {
    'Authorization': 'access_token %s' % token,
    'json_payload': json.dumps(payload),
    }
    """
request_url = endpoint_call['preview']
request_url_token = '%s?apitoken=%s' % (
    endpoint_call['preview'],
    token,
    )
import pdb; pdb.set_trace()
headers = {
    'Content-Type': 'application/json',
    }
res = requests.post(
    url=request_url_token,
    headers=headers,
    data=json.dumps(payload),
    )
print res.text
sys.exit()



# Like Woocommerce;
endpoint = 'shippings/preview'
topfly_web = 'https://spedizioni.topfly.net/api/'
url = '%s%s' % (
    topfly_web,
    endpoint,
    )
auth = ('utente', 'password')    
data = payload
res = requests.post(
    #method='GET',
    url=request_url_token,
    #verify=self.verify_ssl,
    #auth=auth,
    #params=params,
    data=data,
    #timeout=self.timeout,
    headers=headers,
    #**kwargs,
    )
print res.text
sys.exit()


#headers = {'Authorization': 'access_token %s' % token}
res = requests.post(request_url_token, headers=headers)    
print 'Con token: ', res.text
res = requests.post(request_url, headers=headers)    
print 'Senza token: ', res.text
sys.exit()
    
#res = requests.post(request_url, json={})    
#res = requests.post(request_url_token, headers=headers, params=json_payload) 
res = requests.post(request_url_token, data=payload) 
print 'Con token: ', res.text
res = requests.post(request_url, data=payload) 
print 'Senza token: ', res.text

#import requests
#myToken = '<token>'
#myUrl = '<website>'
#head = {'Authorization': 'token {}'.format(myToken)}
#response = requests.get(myUrl, headers=head)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
