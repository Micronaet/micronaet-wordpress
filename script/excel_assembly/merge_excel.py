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
import xlsxwriter
import xlrd
import ConfigParser

# -----------------------------------------------------------------------------
# Read configuration parameter:
# -----------------------------------------------------------------------------
cfg_file = os.path.expanduser('./openerp.cfg')

config = ConfigParser.ConfigParser()
config.read([cfg_file])
data = config.get('folder', 'data')

path = {
    'output': os.path.join(data, 'output'),
    'input': os.path.join(data, 'input'),
}

filename_out = os.path.join(path['output'], 'odoo_vs_wordpress.xlsx')
WB_out = xlsxwriter.Workbook(filename_out)
WS_out = WB_out.add_worksheet('Prodotti')
# WS1.write(0, 0, 'Nome')
# WS1.write(0, 1, 'Mail')

# -----------------------------------------------------------------------------
# Read Excel file:
# -----------------------------------------------------------------------------
# Get list of files:
excel_input = []
for root, folders, files in os.path.walk(path['input']):
    for file in files:
        if file[-4:].lower() == 'xlsx':
            excel_input.append(os.path.join(root, file))

# -----------------------------------------------------------------------------
# Read all Excel files:
# -----------------------------------------------------------------------------
data = {
    'code': {},  # Product selected
    'linked': {},  # Linked product
}  # Dict because save row in output file
field_name = ['codice', 'esistenza', 'abbinamenti']  # Check correct field name

# A. First read for get selection:
for fullname in excel_input:
    try:
        WB = xlrd.open_workbook(fullname)
    except:
        print('[ERROR] Cannot read XLS file: %s' % fullname)
        sys.exit()

    for ws_name in WB.sheet_names():
        WS = WB.sheet_by_name(ws_name)
        print('Read XLS file: %s [%s]' % (fullname, ws_name))

        for row in range(WS.nrows):
            if not row:  # First
                # -------------------------------------------------------------
                # Read field line:
                # -------------------------------------------------------------
                field_position = {}
                for col in range(WS.cols):
                    name = WS.cell(row, col).value
                    if name not in field_name:
                        print('%s [%s] %s. Nome campo non corretto: %s' % (
                            fullname, ws_name, row, name,
                        ))
                    field_position[name] = col





"""
# Extract Excel columns:
is_master = ws.cell(row, 0).value.upper() in 'SX'
published = not (ws.cell(row, 1).value.strip())
default_code = number_to_text(ws.cell(row, 2).value.upper())
ean = ''  # TODO number_to_text(ws.cell(row, 3).value)
lang_text[IT]['name'] = ws.cell(row, 4).value
lang_text[EN]['name'] = ws.cell(row, 5).value \
                        or lang_text[IT]['name']
brand_code = ws.cell(row, 6).value
color_code = ws.cell(row, 7).value
category_code = ws.cell(row, 8).value
pricelist = ws.cell(row, 9).value or 0.0
lifetime_warranty = ws.cell(row, 10).value.upper() in 'SX'
multiply = ws.cell(row, 11).value or 1
extra_price = ws.cell(row, 12).value or 0.0
material_code = ws.cell(row, 13).value
pack_l = ws.cell(row, 14).value or 0.0
pack_h = ws.cell(row, 15).value or 0.0
pack_p = ws.cell(row, 16).value or 0.0
lang_text[IT]['box_dimension'] = ws.cell(row, 17).value
lang_text[EN]['box_dimension'] = ws.cell(row, 18).value \
                                 or lang_text[IT]['box_dimension']

weight = ws.cell(row, 19).value or 0.0
weight_net = ws.cell(row, 20).value or 0.0
q_x_pack = ws.cell(row, 21).value or 1

# Force:
lang_text[IT]['force_name'] = ws.cell(row, 22).value
lang_text[EN]['force_name'] = ws.cell(row, 23).value \
                              or lang_text[IT]['force_name']
lang_text[IT]['force_description'] = ws.cell(row, 24).value
lang_text[EN]['force_description'] = ws.cell(row, 25).value \
                                     or lang_text[IT]['force_description']
force_q_x_pack = ws.cell(row, 26).value or False
force_ean = number_to_text(ws.cell(row, 27).value) or ''
force_price = ws.cell(row, 28).value or 0.0
force_discounted = ws.cell(row, 29).value or 0.0
force_min_stock = ws.cell(row, 30).value or 0.0

lang_text[IT]['large_description'] = ws.cell(row, 31).value
lang_text[EN]['large_description'] = ws.cell(row, 32).value \
                                     or lang_text[IT]['large_description']
lang_text[IT]['emotional_short_description'] = \
    ws.cell(row, 33).value
lang_text[EN]['emotional_short_description'] = \
    ws.cell(row, 34).value or \
    lang_text[IT]['emotional_short_description']
lang_text[IT]['emotional_description'] = ws.cell(row, 35).value
lang_text[EN]['emotional_description'] = ws.cell(row, 36).value \
                                         or lang_text[IT][
                                             'emotional_description']

"""
