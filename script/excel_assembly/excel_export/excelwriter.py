# -*- coding: utf-8 -*-
###############################################################################
#
#    Copyright (C) 2001-2014 Micronaet SRL (<http://www.micronaet.it>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
import xlsxwriter
from xlsxwriter.utility import xl_rowcol_to_cell

from datetime import datetime, timedelta


class ExcelWriter:
    """ Class for manage creation of Excel document
    """
    # -------------------------------------------------------------------------
    #                            CONSTRUCTOR:
    # -------------------------------------------------------------------------
    def __init__(self, filename, verbose=True):
        """ Create new instance of the Object:
        """
        self._filename = filename
        self._verbose = verbose

        self._create_workbook()

    # -------------------------------------------------------------------------
    #                             PRIVATE METHOD, UTILITY:
    # -------------------------------------------------------------------------
    def _log_operation(self, message, mode='INFO'):
        """ Log operation for the class
        """
        if self._verbose:
            print('%s. [%s] %s' % (
                datetime.now(),
                mode.upper(),
                message,
                ))

    def _create_workbook(self):
        """ Create workbook in a temp file
        """
        self._log_operation('Start create file %s' % self._filename)
        self._WB = xlsxwriter.Workbook(self._filename)
        self._WS = {}
        self._log_operation('Created WB and file: %s' % self._filename)

        self.set_format() # setup default format for text used
        self.get_format() # Load database of formats

    # -------------------------------------------------------------------------
    #                           PUBLIC METHOD:
    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------
    # Format utility:
    # -------------------------------------------------------------------------
    def rowcol_to_cell(self, row, col, row_abs=False, col_abs=False):
        """ Return row, col format in "A1" notation
        """
        return xl_rowcol_to_cell(row, col, row_abs=row_abs, col_abs=col_abs)

    def format_date(self, value):
        """ Format hour DD:MM:YYYY
        """
        if not value:
            return ''
        return '%s/%s/%s' % (
            value[8:10],
            value[5:7],
            value[:4],
            )

    def format_hour(self, value, hhmm_format=True, approx=0.001,
            zero_value='0:00'):
        """ Format hour HH:MM
        """
        if not hhmm_format:
            return value

        if not value:
            return zero_value

        value += approx
        hour = int(value)
        minute = int((value - hour) * 60)
        return '%d:%02d' % (hour, minute)

    def close_workbook(self, ):
        """ Close workbook
        """
        self._WS = {}
        self._wb_format = False

        try:
            self._WB.close()
            self._log_operation('Closed WB %s' % self._filename)
        except:
            self._log_operation(
                'Error closing WB %s' % self._filename, 'error')
        self._WB = False # remove object in instance

    def create_worksheet(self, name=False):
        """ Create database for WS in this module
        """
        try:
            if not self._WB:
                self._create_workbook()
        except:
            self._create_workbook()

        self._WS[name] = self._WB.add_worksheet(name)
        self._log_operation('New WS: %s' % name)

    def merge_cell(self, ws_name, rectangle, default_format=False, data=''):
        """ Merge cell procedure:
            WS: Worksheet where work
            rectangle: list for 2 corners xy data: [0, 0, 10, 5]
            default_format: setup format for cells
        """
        rectangle.append(data)
        if default_format:
            rectangle.append(default_format)
        self._WS[ws_name].merge_range(*rectangle)
        return

    def write_xls_line(self, ws_name, row, line, default_format=False, col=0):
        """ Write line in excel file:
            WS: Worksheet where find
            row: position where write
            line: Row passed is a list of element or tuple (element, format)
            default_format: if present replace when format is not present

            @return: nothing
        """
        for record in line:
            if type(record) == bool:
                record = ''
            if type(record) not in (list, tuple):
                if default_format:
                    self._WS[ws_name].write(row, col, record, default_format)
                else:
                    self._WS[ws_name].write(row, col, record)
            elif len(record) == 2: # Normal text, format
                self._WS[ws_name].write(row, col, *record)
            else: # Rich format TODO
                self._WS[ws_name].write_rich_string(row, col, *record)
            col += 1
        return True

    def write_xls_data(self, ws_name, row, col, data, default_format=False):
        """ Write data in row col position with default_format

            @return: nothing
        """
        if default_format:
            self._WS[ws_name].write(row, col, data, default_format)
        else:
            self._WS[ws_name].write(row, col, data, default_format)
        return True

    def column_width(self, ws_name, columns_w, col=0):
        """ WS: Worksheet passed
            columns_w: list of dimension for the columns
        """
        for w in columns_w:
            self._WS[ws_name].set_column(col, col, w)
            col += 1
        return True

    def row_height(self, ws_name, row_list, height=10):
        """ WS: Worksheet passed
            columns_w: list of dimension for the columns
        """
        if type(row_list) in (list, tuple):
            for row in row_list:
                self._WS[ws_name].set_row(row, height)
        else:
            self._WS[ws_name].set_row(row_list, height)
        return True

    def write_formula(self, ws_name, row, col, formula, default_format, value):
        """ Write formula in cell passed
        """
        return self._WS[ws_name].write_formula(
            row, col, formula, default_format, value)

    def set_format(
            self,
            # Title:
            title_font='Courier 10 pitch', title_size=11, title_fg='black',
            # Header:
            header_font='Courier 10 pitch', header_size=9, header_fg='black',
            # Text:
            text_font='Courier 10 pitch', text_size=9, text_fg='black',
            # Number:
            number_format='#,##0.###0',
            # Layout:
            border=1,
            ):
        """ Setup 4 element used in normal reporting
            Every time replace format setup with new database
        """
        self._default_format = {
            'title': (title_font, title_size, title_fg),
            'header': (header_font, header_size, header_fg),
            'text': (text_font, text_size, text_fg),
            'number': number_format,
            'border': border,
            }
        self._log_operation('Set format variables: %s' % self._default_format)

    def get_format(self, key=False):
        """ Database for format cells
            key: mode of format
            if not passed load database only
        """
        self._log_operation('Get format WB type')
        WB = self._WB

        F = self._default_format  # readability

        # Save database in self:
        create = False
        try:
            if not self._wb_format:  # raise error if not present
                create = True
        except:
            create = True

        if create:
            self._wb_format = {
                # -------------------------------------------------------------
                # Used when key not present:
                # -------------------------------------------------------------
                'default': WB.add_format({  # Usually text format
                    'font_name': F['text'][0],
                    'font_size': F['text'][1],
                    'font_color': F['text'][2],
                    'align': 'left',
                    }),

                # -------------------------------------------------------------
                #                       TITLE:
                # -------------------------------------------------------------
                'title': WB.add_format({
                    'bold': True,
                    'font_name': F['title'][0],
                    'font_size': F['title'][1],
                    'font_color': F['title'][2],
                    'align': 'left',
                    }),

                # -------------------------------------------------------------
                #                       HEADER:
                # -------------------------------------------------------------
                'header': WB.add_format({
                    'bold': True,
                    'font_name': F['header'][0],
                    'font_size': F['header'][1],
                    'font_color': F['header'][2],
                    'align': 'center',
                    'valign': 'vcenter',
                    'bg_color': '#849bff',  # '#cfcfcf', # grey
                    'border': F['border'],
                    # 'text_wrap': True,
                    }),

                # -------------------------------------------------------------
                #                       TEXT BOLD:
                # -------------------------------------------------------------
                'bold_wrap': WB.add_format({
                    'bold': True,
                    'font_name': F['text'][0],
                    'font_size': F['text'][1],
                    'font_color': F['text'][2],
                    'border': F['border'],
                    'bg_color': '#9e9e9e',
                    'align': 'left',
                    'valign': 'top',
                    'text_wrap': True,
                    }),

                'bold': WB.add_format({
                    'bold': True,
                    'font_name': F['text'][0],
                    'font_size': F['text'][1],
                    'font_color': F['text'][2],
                    'border': F['border'],
                    'align': 'left',
                    'valign': 'top',
                    }),

                'bold_blue': WB.add_format({
                    'bold': True,
                    'font_name': F['text'][0],
                    'font_size': F['text'][1],
                    'font_color': F['text'][2],
                    'border': F['border'],
                    'bg_color': '#e0eaff',
                    'align': 'left',
                    'valign': 'top',
                    }),
                'bold_dark_blue': WB.add_format({
                    'bold': True,
                    'font_name': F['text'][0],
                    'font_size': F['text'][1],
                    'font_color': F['text'][2],
                    'border': F['border'],
                    'bg_color': '#8ca1e2',
                    'align': 'left',
                    'valign': 'top',
                    }),
                'bold_grey': WB.add_format({
                    'bold': True,
                    'font_name': F['text'][0],
                    'font_size': F['text'][1],
                    'font_color': F['text'][2],
                    'border': F['border'],
                    'bg_color': '#ffffff',
                    'align': 'left',
                    'valign': 'top',
                    }),

                # -------------------------------------------------------------
                #                       TEXT NORMAL:
                # -------------------------------------------------------------
                'text': WB.add_format({
                    'font_name': F['text'][0],
                    'font_size': F['text'][1],
                    'font_color': F['text'][2],
                    'border': F['border'],
                    'align': 'left',
                    # 'valign': 'vcenter',
                    }),
                'text_center': WB.add_format({
                    'font_name': F['text'][0],
                    'font_size': F['text'][1],
                    'font_color': F['text'][2],
                    'border': F['border'],
                    'align': 'center',
                    # 'valign': 'vcenter',
                    }),
                'text_right': WB.add_format({
                    'font_name': F['text'][0],
                    'font_size': F['text'][1],
                    'font_color': F['text'][2],
                    'border': F['border'],
                    'align': 'right',
                    # 'valign': 'vcenter',
                    }),

                'text_total': WB.add_format({
                    'bold': True,
                    'font_name': F['text'][0],
                    'font_size': F['text'][1],
                    'font_color': F['text'][2],
                    'border': F['border'],
                    'bg_color': '#DDDDDD',
                    'align': 'left',
                    'valign': 'vcenter',
                    #'text_wrap': True,
                    }),

                # --------------
                # Text BG color:
                # --------------
                'bg_white': WB.add_format({
                    'bold': True,
                    'font_name': F['text'][0],
                    'font_size': F['text'][1],
                    'font_color': F['text'][2],
                    'border': F['border'],
                    'bg_color': '#FFFFFF',
                    'align': 'left',
                    # 'valign': 'vcenter',
                    }),
                'bg_blue': WB.add_format({
                    'bold': True,
                    'font_name': F['text'][0],
                    'font_size': F['text'][1],
                    'font_color': F['text'][2],
                    'border': F['border'],
                    'bg_color': '#c4daff',
                    'align': 'left',
                    # 'valign': 'vcenter',
                    }),
                'bg_red': WB.add_format({
                    'bold': True,
                    'font_name': F['text'][0],
                    'font_size': F['text'][1],
                    'font_color': F['text'][2],
                    'border': F['border'],
                    'bg_color': '#ffc6af',
                    'align': 'left',
                    #'valign': 'vcenter',
                    }),
                'bg_green': WB.add_format({
                    'bold': True,
                    'font_name': F['text'][0],
                    'font_size': F['text'][1],
                    'font_color': F['text'][2],
                    'border': F['border'],
                    'bg_color': '#b1f9c1',
                    'align': 'left',
                    # 'valign': 'vcenter',
                    }),
                'bg_yellow': WB.add_format({
                    'bold': True,
                    'font_name': F['text'][0],
                    'font_size': F['text'][1],
                    'border': F['border'],
                    'font_color': 'black',
                    'bg_color': '#fffec1',
                    'align': 'left',
                    # 'valign': 'vcenter',
                    }),
                'bg_orange': WB.add_format({
                    'bold': True,
                    'font_name': F['text'][0],
                    'font_size': F['text'][1],
                    'border': F['border'],
                    'font_color': 'black',
                    'bg_color': '#fcdebd',
                    'align': 'left',
                    # 'valign': 'vcenter',
                    }),
                'bg_red_number': WB.add_format({
                    'bold': True,
                    'font_name': F['text'][0],
                    'font_size': F['text'][1],
                    'font_color': F['text'][2],
                    'border': F['border'],
                    'bg_color': '#ffc6af',
                    'align': 'right',
                    # 'valign': 'vcenter',
                    }),
                'bg_green_number': WB.add_format({
                    'bold': True,
                    'font_name': F['text'][0],
                    'font_size': F['text'][1],
                    'font_color': F['text'][2],
                    'border': F['border'],
                    'bg_color': '#b1f9c1',
                    'align': 'right',
                    # 'valign': 'vcenter',
                    }),
                'bg_yellow_number': WB.add_format({
                    'bold': True,
                    'font_name': F['text'][0],
                    'font_size': F['text'][1],
                    'border': F['border'],
                    'font_color': 'black',
                    'bg_color': '#fffec1',  # #ffff99',
                    'align': 'right',
                    # 'valign': 'vcenter',
                    }),
                'bg_orange_number': WB.add_format({
                    'bold': True,
                    'font_name': F['text'][0],
                    'font_size': F['text'][1],
                    'border': F['border'],
                    'font_color': 'black',
                    'bg_color': '#fcdebd',
                    'align': 'right',
                    # 'valign': 'vcenter',
                    }),
                'bg_white_number': WB.add_format({
                    'bold': True,
                    'font_name': F['text'][0],
                    'font_size': F['text'][1],
                    'border': F['border'],
                    'font_color': 'black',
                    'bg_color': '#FFFFFF',
                    'align': 'right',
                    # 'valign': 'vcenter',
                    }),
                'bg_blue_number': WB.add_format({
                    'bold': True,
                    'font_name': F['text'][0],
                    'font_size': F['text'][1],
                    'border': F['border'],
                    'font_color': 'black',
                    'bg_color': '#c4daff',  # #ffff99',
                    'align': 'right',
                    # 'valign': 'vcenter',
                    }),

                # TODO remove?
                'bg_order': WB.add_format({
                    'bold': True,
                    'bg_color': '#cc9900',
                    'font_name': F['text'][0],
                    'font_size': F['text'][1],
                    'font_color': F['text'][2],
                    'border': F['border'],
                    'num_format': F['number'],
                    'align': 'right',
                    # 'valign': 'vcenter',
                    }),

                # --------------
                # Text FG color:
                # --------------
                'text_black': WB.add_format({
                    'font_name': F['text'][0],
                    'font_size': F['text'][1],
                    'font_color': 'black',
                    'border': F['border'],
                    'align': 'left',
                    'valign': 'vcenter',
                    # 'text_wrap': True
                    }),
                'text_blue': WB.add_format({
                    'font_name': F['text'][0],
                    'font_size': F['text'][1],
                    'font_color': 'blue',
                    'border': F['border'],
                    'align': 'left',
                    'valign': 'vcenter',
                    # 'text_wrap': True
                    }),
                'text_red': WB.add_format({
                    'font_name': F['text'][0],
                    'font_size': F['text'][1],
                    'font_color': '#ff420e',
                    'border': F['border'],
                    'align': 'left',
                    'valign': 'vcenter',
                    # 'text_wrap': True
                    }),
                'text_green': WB.add_format({
                    'font_color': '#328238', ##99cc66
                    'font_name': F['text'][0],
                    'font_size': F['text'][1],
                    'border': F['border'],
                    'align': 'left',
                    'valign': 'vcenter',
                    # 'text_wrap': True
                    }),
                'text_grey': WB.add_format({
                    'font_color': '#eeeeee',
                    'font_name': F['text'][0],
                    'font_size': F['text'][1],
                    'border': F['border'],
                    'align': 'left',
                    'valign': 'vcenter',
                    # 'text_wrap': True
                    }),
                'text_wrap': WB.add_format({
                    'font_color': 'black',
                    'font_name': F['text'][0],
                    'font_size': F['text'][1],
                    'border': F['border'],
                    'align': 'left',
                    'valign': 'vcenter',
                    # 'text_wrap': True,
                    }),

                # -------------------------------------------------------------
                #                       NUMBER:
                # -------------------------------------------------------------
                'number': WB.add_format({
                    'font_name': F['text'][0],
                    'font_size': F['text'][1],
                    'border': F['border'],
                    'num_format': F['number'],
                    'align': 'right',
                    # 'valign': 'vcenter',
                    }),

                # ----------------
                # Number FG color:
                # ----------------
                'number_black': WB.add_format({
                    'font_name': F['text'][0],
                    'font_size': F['text'][1],
                    'border': F['border'],
                    'num_format': F['number'],
                    'font_color': 'black',
                    'align': 'right',
                    # 'valign': 'vcenter',
                    }),
                'number_blue': WB.add_format({
                    'font_name': F['text'][0],
                    'font_size': F['text'][1],
                    'border': F['border'],
                    'num_format': F['number'],
                    'font_color': 'blue',
                    'align': 'right',
                    # 'valign': 'vcenter',
                    }),
                'number_grey': WB.add_format({
                    'font_name': F['text'][0],
                    'font_size': F['text'][1],
                    'border': F['border'],
                    'num_format': F['number'],
                    'font_color': 'grey',
                    'align': 'right',
                    # 'valign': 'vcenter',
                    }),
                'number_red': WB.add_format({
                    'font_name': F['text'][0],
                    'font_size': F['text'][1],
                    'border': F['border'],
                    'num_format': F['number'],
                    'font_color': 'red',
                    'align': 'right',
                    # 'valign': 'vcenter',
                    }),
                'number_green': WB.add_format({
                    'font_name': F['text'][0],
                    'font_size': F['text'][1],
                    'border': F['border'],
                    'num_format': F['number'],
                    'font_color': 'green',
                    'align': 'right',
                    # 'valign': 'vcenter',
                    }),

                'number_total': WB.add_format({
                    'bold': True,
                    'font_name': F['text'][0],
                    'font_size': F['text'][1],
                    'font_color': F['text'][2],
                    'border': F['border'],
                    'num_format': F['number'],
                    'bg_color': '#DDDDDD',
                    'align': 'right',
                    # 'valign': 'vcenter',
                    }),
                }

        # Return format or default one's
        if key:
            return self._wb_format.get(
                key,
                self._wb_format.get('default'),
                )
        else:
            return True
