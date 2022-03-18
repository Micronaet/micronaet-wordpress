#!/usr/bin/python
###############################################################################
# Copyright (C) 2001-2015 Micronaet S.r.l. (<https://micronaet.com>)
# Developer: Nicola Riolini @thebrush
#            https://it.linkedin.com/in/thebrush
#            https://linktr.ee/nicolariolini
###############################################################################

import os
import pdb
import requests
import json

# -----------------------------------------------------------------------------
# Authenticate to get Session ID:
# -----------------------------------------------------------------------------
url = 'http://localhost:5000/API/v1.0/micronaet/laucher'
headers = {
    'content-type': 'application/json',
}
payload = {
    'jsonrpc': '2.0',
    'params': {
        'command': 'invoice',
        'parameters': ['filename.csv'],
        }
    }

response = requests.post(url, headers=headers, data=json.dumps(payload))
response_json = response.json()
if response_json['success']:
    print(response_json)

