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
import pdb
import erppeek
import xlsxwriter
import xlrd
import ConfigParser
from excel_export.excel_wrapper import ExcelWriter

# -----------------------------------------------------------------------------
# Read configuration parameter:
# -----------------------------------------------------------------------------
cfg_file = os.path.expanduser('./openerp.cfg')

config = ConfigParser.ConfigParser()
config.read([cfg_file])
root = os.path.expanduser(config.get('folder', 'root'))

path = {
    'input': os.path.join(root, 'data'),
    'output': root,
}

filename_out = os.path.join(path['output'], 'odoo_vs_wordpress.xlsx')
wb_out = ExcelWriter(filename_out)

# Format:
wb_out.set_format()
excel_format = {
    'title': wb_out.get_format('title'),
    'header': wb_out.get_format('header'),
    'text': wb_out.get_format('text'),
}

ws_out_name = 'Prodotti'
out_row = 0

wb_out.create_worksheet(ws_out_name)
wb_out.write_xls_line(ws_out_name, out_row, [
    'Padre', 'Disatt.', 'Codice prodotto',
    'Nome prodotto [IT]', 'Nome prodotto [EN]',
    'Brand', 'Codice colore', 'Categorie',
    'Listino', 'Garanzia vita', 'Moltiplicatore', 'Prezzo extra', 'Materiale',

    # Package:
    'L', 'H', 'Q',

    'Box dimensioni [IT]', 'Box dimensioni [EN]',
    'Peso lordo', 'Peso netto', 'Q x pack',

    # Force:
    'Nome [IT]', 'Nome [EN]', 'Descrizione [IT]', 'Descrizione [EN]',
    'Q x pack', 'EAN', 'Prezzo', 'Stock minimo',

    'Estesa [IT]', 'Estesa [EN]',
    'Emozionale breve [IT]', 'Emozionale breve [EN]',
    'Emozionale dettagliata [IT]', 'Emozionale dettagliata [EN]',
    ], default_format=excel_format['header'])

wb_out.column_width(ws_out_name, [
    6, 6, 15,
    30, 30,
    25, 25, 25,
    20, 5, 5, 15, 20,

    # Package:
    5, 5, 5,

    10, 10,
    10, 10, 10,

    # Force:
    30, 30, 40, 40,
    10, 12, 15, 15,

    30, 30,
    35, 35,
    40, 40,
])
# -----------------------------------------------------------------------------
# Read Excel file:
# -----------------------------------------------------------------------------
# Get list of files:
wb_input = {}
for root, folders, files in os.walk(path['input']):
    for file in files:
        if file[-4:].lower() == 'xlsx':
            fullname = os.path.join(root, file)
            try:
                wb = xlrd.open_workbook(fullname)
            except:
                print('[ERROR] Cannot read XLS file: %s' % fullname)
                sys.exit()
            wb_input[wb] = [fullname, {}]  # Sheet code position

# -----------------------------------------------------------------------------
# Read all Excel files:
# -----------------------------------------------------------------------------
data = {
    'code': {},  # Product selected (Dict because save row in output file)
    'linked': {},  # Linked product
}
field_name = ['codice', 'esistenza', 'abbinamenti']  # Check correct field name

# -----------------------------------------------------------------------------
# A. First read for get selection:
# -----------------------------------------------------------------------------
for wb in wb_input:
    filename = wb_input[wb][0]
    for ws_name in wb.sheet_names():
        ws = wb.sheet_by_name(ws_name)
        print('Read XLS file: %s [%s]' % (fullname, ws_name))
        with_link = start = False

        for row in range(ws.nrows):
            if not row:  # First
                # -------------------------------------------------------------
                # Read field line:
                # -------------------------------------------------------------
                field_position = {}

                for col in range(1, ws.ncols):
                    name = (ws.cell(row, col).value or '').lower()
                    if not name:
                        continue
                    if name in field_name:
                        field_position[name] = col
                    else:
                        print('%s [%s] %s. Field name non in %s: %s' % (
                            fullname, ws_name, row, name, field_name
                        ))

                # Check mandatory fields:
                if 'esistenza' not in field_position:
                    print('%s [%s] %s. Not a sheet for product selection' % (
                          fullname, ws_name, row))
                    break
                if 'codice' not in field_position:
                    print('%s [%s] %s. Not present key field: codice' % (
                          fullname, ws_name, row))
                    break
                if 'abbinamenti' in field_position:
                    with_link = True
                wb_input[wb][1][ws_name] = field_position['codice']

            # Read other lined:
            cell = ws.cell(row, 0).value

            cell_code = ws.cell(row, field_position['codice']).value
            if cell_code:
                default_code = str(cell_code)
                if type(cell_code) == float and default_code[-2:] == '.0':
                    default_code = default_code[:-2]

            if not start and cell == 'start':
                start = True

            cell_qty = ws.cell(row, field_position['esistenza']).value
            if not cell_qty:
                continue  # Not used

            # Linked product:
            if with_link:
                linked = ws.cell(
                    row, field_position['abbinamenti']).value
                # (ver. 1) Check data line
                if not start or not (default_code or linked):
                    print('%s [%s] %s. Line not imported (no code or link)' % (
                          fullname, ws_name, row))
                    continue

                if default_code not in data['linked']:
                    data['linked'][default_code] = []
                    if linked not in data['linked'][default_code]:
                        data['linked'][default_code].append(linked)
            else:
                # (ver. 2) Check data line
                if not start or not default_code:
                    print('%s [%s] %s. Line not imported (no code)' % (
                          fullname, ws_name, row))
                    continue

            # Selected product:
            out_row += 1
            if default_code not in data['code']:
                data['code'][default_code] = out_row
                print('%s [%s] %s. Used row' % (
                    wb_out, ws_name, row))
                wb_out.write_xls_line(
                    ws_out_name, out_row, [
                        'X',
                        '',
                        default_code
                    ], default_format=excel_format['text'])

# -----------------------------------------------------------------------------
# A. First read for get selection:
# -----------------------------------------------------------------------------
for wb in wb_input:
    fullname = wb_input[wb][0]
    for ws_name in wb.sheet_names():
        ws = wb.sheet_by_name(ws_name)
        start = False
        output_col = {}

        code_position = wb_input[wb][1].get(ws_name)
        if not code_position:
            print('%s [%s]. No code position in this sheet' % (
                fullname, ws_name))
        else:
            print('Data import from XLS file: %s [%s]' % (
                fullname, ws_name))

        for row in range(1, ws.nrows):
            # -----------------------------------------------------------------
            # Position row:
            # -----------------------------------------------------------------
            if row == 1:  # First
                for col in range(1, ws.ncols):
                    try:
                        name = int(ws.cell(row, col).value)
                    except:
                        continue
                    if name and code_position != name:  # Code not written
                        output_col[col] = name

            # Read other lined:
            cell = ws.cell(row, 0).value
            if not start and cell == 'start':
                start = True
            if not start:
                continue

            default_code = str(ws.cell(row, code_position).value)
            if type(cell_code) == float and default_code[-2:] == '.0':
                default_code = default_code[:-2]

            row_out = data['code'].get(default_code)
            if not row_out:
                continue  # Code not used

            for col in output_col:
                col_out = output_col[col]  # position on output file

                wb_out.write_xls_line(
                    ws_out_name, out_row, [
                        ws.cell(row, 0).value,  # This cell
                    ], default_format=excel_format['text'], col=col_out - 1)

wb_out.close_workbook()
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
