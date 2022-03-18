#!/usr/bin/python
###############################################################################
# Copyright (C) 2001-2015 Micronaet S.r.l. (<https://micronaet.com>)
# Developer: Nicola Riolini @thebrush
#            https://it.linkedin.com/in/thebrush
#            https://linktr.ee/nicolariolini
###############################################################################

import os
import sys
import pdb
from flask import Flask, request
from datetime import datetime
from googletrans import Translator

translator = Translator()

try:
    import ConfigParser
except:
    pass
try:
    import configparser as ConfigParser
except:
    pass


# -----------------------------------------------------------------------------
# Utility:
# -----------------------------------------------------------------------------
def write_log(log_f, message, mode='INFO', verbose=True):
    """ Write log file
    """
    complete_message = '%s [%s]: %s' % (
        str(datetime.now())[:19],
        mode,
        message,
    )
    if verbose:
        print(' * {}'.format(complete_message))
    log_f.write('{}\n'.format(complete_message))
    log_f.flush()


# -----------------------------------------------------------------------------
# Read configuration parameter from external file:
# -----------------------------------------------------------------------------
current_path = os.path.dirname(__file__)
log_file = os.path.join(current_path, 'flask.log')
log_f = open(log_file, 'a')
write_log(log_f, 'Start Micronaet Translator')
write_log(log_f, 'Flask log file: {}'.format(log_file))

config_files = [
    os.path.join(current_path, 'flask.cfg'),
]
for config_file in config_files:
    if not os.path.isfile(config_file):
        continue
    cfg_file = os.path.expanduser(config_file)

    config = ConfigParser.ConfigParser()
    config.read([cfg_file])
    host = config.get('flask', 'host')
    port = config.get('flask', 'port')
    write_log(log_f, 'Read config file: {}'.format(config_file))
    break
else:
    write_log(log_f, 'Read default parameter [0.0.0.0:5000]')
    host = '0.0.0.0'
    port = '5000'

# -----------------------------------------------------------------------------
# End point definition:
# -----------------------------------------------------------------------------
app = Flask(__name__)


@app.route('/API/v1.0/micronaet/translate', methods=['POST'])
def MicronaetCall():
    """ Master function for Micronaet Call

    """
    # -------------------------------------------------------------------------
    # Get parameters from call:
    # -------------------------------------------------------------------------
    params = request.get_json()
    rpc_call = params['params']
    command = rpc_call['command']
    parameter = rpc_call['parameters']

    # -------------------------------------------------------------------------
    #                             Execute call:
    # -------------------------------------------------------------------------
    # Start reply payload:
    payload = {
        'success': False,
        'reply': {},
    }
    # -------------------------------------------------------------------------
    #                       Import invoice procedure:
    # -------------------------------------------------------------------------
    if command == 'translate':
        text = parameter.get('text')  # account command
        from_lang = parameter.get('from', 'it')
        to_lang = parameter.get('to', 'en')

        try:
            translate = translator.translate(text, src=to_lang, dest=to_lang)
            payload['reply'].update({
                    'translate': translate,
                })
            payload['success'] = True  # Invoice generated (not sure print)
        except:
            payload['reply'].update({
                'error': str(sys.exc_info()),
            })
    else:  # Bad call:
        # ---------------------------------------------------------------------
        message = '[ERROR] ODOO is calling wrong command {}\n'.format(
            command)
        payload['reply'].update({
            'error': message.strip(),
        })

    # Prepare response
    return payload


app.run(debug=True, host=host, port=port)
write_log(log_f, 'End Micronaet Flask agent')
