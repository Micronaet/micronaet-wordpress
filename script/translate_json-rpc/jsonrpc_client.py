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
lang = 'en'
url = 'http://127.0.0.1:5000/API/v1.0/micronaet/translate'
headers = {
    'content-type': 'application/json',
}
payload = {
    'jsonrpc': '2.0',
    'params': {
        'command': 'translate',
        'parameters': {
            'text': '',
            'from': 'it',
            'to': lang,
        },
        }
    }

text_list = [
    "Set 2 sedie pieghevoli Atena  struttura acciaio  verniciato tessuto plastificato microforato",
    "Le cinghie di ricambio per la poltrona Linda sono un prodotto  Fiam e sono utilizzabili esclusivamente sull’originale. All’ interno della confezione sono inclusi  i ganci in metallo. Fiam ha deciso di commercializzare i ricambi per dare un valore aggiunto ai propri prodotti in quanto duraturi nel tempo ed essendo attenta al tema ambientale.",
    "Set 4 Tovagliette rettangolari in tessuto microforato cm. 50x40",
    "Il telo di ricambio per il lettino Amigo è un prodotto Fiam ed è utilizzabile esclusivamente sull’ originale.  Tela di ricambio realizzata in tessuto microforato realizzato con filato di poliestere rivestito da PVC e termosaldato per garantire un'ottima stabilità della maglia ed un'elevata resistenza al carico. Il rivestimento in materiale plastico conferisce al tessuto resistenza fisica e tenacità del colore anche contro l'esposizione continua al sole ed alle intemperie.  Fiam ha deciso di commercializzare i ricambi per dare un valore aggiunto ai propri prodotti in quanto duraturi nel tempo ed essendo attenta al tema ambientale.       E' particolarmente adatto all'utilizzo esterno. E' lavabile semplicemente con acqua e sapone.",
]
for text in text_list:
    payload['params']['parameters']['text'] = text
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    response_json = response.json()
    if response_json['success']:
        print(text)
        print(response_json.get('reply', {}).get('translate'))

