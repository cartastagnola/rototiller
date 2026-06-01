from __future__ import annotations
import sys
import os
import traceback
import curses
import sqlite3
import threading
import multiprocessing
from math import floor

import src.UIgraph as UIgraph
import src.TEXTtiller as TEXT

from dataclasses import dataclass
from typing import List, Tuple, Dict, Union, Callable
from datetime import datetime, timedelta

from src.CONFtiller import (
    debug_logger, logging, ScopeMode, SQL_TIMEOUT, BLOCK_MAX_COST, FIGLET)

from src.TYPEStiller import Scope, ScopeActions, ScreenState, KeyboardState
from src.UTILStiller import time_ago, human_mojo, human_int, Timer, truncate
import src.PLATFORMtiller as PLAT
import src.WDBtiller as WDB
import src.DEXtiller as DEX
import src.UTILStiller as UTILS
import src.DEBUGtiller as DEBUGtiller
#### global for debugging
DEBUG_OBJ = DEBUGtiller.DEBUG_OBJ


# unicode box u'\u25xx'
## light shade  u2591
## medium shade u2592
## dark shade   u2593
## / u2571
## \ u2572
## X u2573
## full block       u2588
## upper half block u2580
## lower half block u2584


def cast_table_items_to_string(table: List[List], formatters: List[Callable] = None):
    """Convert each item of a 2dim list to string"""

    if formatters is None:
        formatters = [None] * len(table[0])

    table_str = []
    for col in table:
        col_str = []
        for n, u in enumerate(col):
            if formatters[n] and u != '':
                u = formatters[n](u)
            else:
                if isinstance(u, float):
                    u = DEX.format_and_round_number(u, 5, 10)
            col_str.append(str(u))
        table_str.append(col_str)

    return table_str


def transpose_table(table: List[List]):
    return [[row[i] for row in table] for i in range(len(table[0]))]


def delete_table_column_LEGACY(table, idx_col):
    if idx_col < 0:
        return [row[:idx_col] for row in table]
    else:
        return [row[:idx_col] + row[idx_col + 1:] for row in table]


def delete_table_column(table, idx_col):
    for row in table:
        row.pop(idx_col)


def calc_size_column(data_table, data_table_color, data_table_legend, scope, max_table_width,
                     multiple_selection, x_tab_size, column_widths, formatters):
    """Return max_dims, but it changes also all the data table input to trunkate the tab
    if needed
    column_widths: it is possible to set fixed size to columns
    """

    casted_data_table = cast_table_items_to_string(data_table, formatters)

    n_rows = len(data_table)
    n_columns = len(data_table[0])

    ### calculate max dim for columns
    max_dims_origin = [0] * n_columns
    total_dims = 0
    x_col_start = [0]
    x_col_dim = []
    column_separator = 3
    for idx in range(n_rows):
        for idx2, u in enumerate(casted_data_table[idx]):
            if len(str(u)) > max_dims_origin[idx2]:
                max_dims_origin[idx2] = len(u)

    # trim string too long (if str > 2/3 of the witdh of the table)
    # max_dims[0] is the first columns, it should have more space in some cases
    # but here is not clear... WIP
    max_dims = [0] * n_columns
    max_str_length = int((x_tab_size - max_dims[0]) * (2/3))
    for n, i in enumerate(max_dims_origin):
        if column_widths[n]:
            max_dims[n] = column_widths[n]
        elif i > max_str_length:
            max_dims[n] = max_str_length
        else:
            max_dims[n] = i

    if data_table_legend is not None:
        #assert length legend == n_columns
        for idx, i in enumerate(data_table_legend):
            if len(i) > max_dims[idx]:
                max_dims[idx] = len(i)

    # add separator
    max_dims[0] += column_separator * 2  # first column double space
    total_dims += max_dims[0]
    for idx in range(1, n_columns):
        max_dims[idx] += column_separator
        total_dims += max_dims[idx]

    ### add selection column
    if multiple_selection:
        n_columns += 1  # add the selection column
        x_col_start[0] += 7  # add the selection column
        #max_dims.insert(0, 7)
    else:
        x_col_start[0] += 1  # add CONST, one char before the column

    ### scroll horizontally
    idx_fix_item = 1  # CONST fixed element orizontally
    if scope.cursor_x < 0:
        scope.cursor_x = 0
    elif scope.cursor_x > (n_columns - idx_fix_item - 1):
        scope.cursor_x = (n_columns - idx_fix_item - 1)

    scope_x = scope.cursor_x
    # remove column based on the cursor value
    while scope_x > 0:  # and total_dims > max_table_width:
        dim = max_dims.pop(idx_fix_item)
        max_dims_origin.pop(idx_fix_item)
        delete_table_column(data_table, idx_fix_item)
        delete_table_column(data_table_color, idx_fix_item)
        formatters.pop(idx_fix_item)
        column_widths.pop(idx_fix_item)
        if data_table_legend is not None:
            data_table_legend.pop(idx_fix_item)
        total_dims -= dim
        scope_x -= 1


    ### remove last column until there is enough space
    if total_dims > max_table_width:
        while total_dims > max_table_width:
            dim = max_dims.pop(-1)
            max_dims_origin.pop(-1)
            delete_table_column(data_table, -1)
            delete_table_column(data_table_color, -1)
            formatters.pop(-1)
            column_widths.pop(-1)
            if data_table_legend is not None:
                data_table_legend.pop(-1)
            total_dims -= dim
    else:
        ## WIP: if there are enough space, it enlarge fixed size columns
        count_fix_size_col = 0
        for n in column_widths:
            if n:
                count_fix_size_col += 1
        if count_fix_size_col > 0:
            remainder = max_table_width - total_dims - column_separator * 2
            remainder_per_item = remainder // count_fix_size_col

        total_dims = 0
        for n, i in enumerate(max_dims):
            if column_widths[n]:
                max_dims[n] = min(max_dims[n] + remainder_per_item, max_dims_origin[n] + 2)
            total_dims += max_dims[n]


    ### calculate the remainder space to re-distribuite later
    ### first column is fixed
    if n_columns > 1:
        x_remainder = (x_tab_size - total_dims) // (n_columns - 1)

    ### calculate each col dimension and starting position
    x_col_dim.append(max_dims[0])
    for i in range(1, len(max_dims)):
        x_col_dim.append(i + x_remainder)

    x_col_start.append(x_col_start[-1] + max_dims[0])
    for i in range(1, len(max_dims) - 1):
        x_col_start.append(x_col_start[-1] + max_dims[i] + x_remainder)

    return x_col_dim, x_col_start, max_dims
    #return x_col_dim, x_col_start, max_str_length


def recalcultate_first_and_last_element(select, idx_first_element, rows_number):
    """calculate if the current index is in the range of visible rows, if not it
    correct the range of visible rows """
    idx_last_element = idx_first_element + rows_number
    if select >= (idx_last_element):
        idx_last_element = select + 1
        idx_first_element = idx_last_element - rows_number
    elif idx_first_element > select:
        idx_first_element = select
        idx_last_element = (idx_first_element + rows_number)

    return idx_first_element, idx_last_element, select


def recalcultate_first_and_last_element_BAND(select, idx_last_item, items_count):
    """MOD version for block_band. (inclusive and using the last item) calculate if the current index is in the range of visible rows, if not it
    correct the range of visible rows """
    idx_first_item = idx_last_item - items_count + 1  # the last block is the first
    if select > idx_last_item:
        idx_last_item = select
        idx_first_item = idx_last_item - items_count + 1
    elif select < idx_first_item:
        idx_first_item = select
        idx_last_item = idx_first_item + items_count - 1

    return idx_first_item, idx_last_item, select


def create_text(stdscr, pos: UIgraph.Point, text: str, P_text_color, bold: bool = False,
                align: int = 0, inv_color: bool = False, underline: bool = False):
    """Create normal text."""

    stdscr.attron(curses.color_pair(P_text_color))
    if bold:
        stdscr.attron(curses.A_BOLD)
    if inv_color:
        stdscr.attron(curses.A_REVERSE)
    if underline:
        stdscr.attron(curses.A_UNDERLINE)
    stdscr.addstr(pos.y, pos.x, str(text))
    stdscr.attroff(curses.A_BOLD)
    stdscr.attroff(curses.A_REVERSE)
    stdscr.attroff(curses.A_UNDERLINE)


def get_win_dimension(stdscr):
    temp_vec = stdscr.getmaxyx()
    return UIgraph.Point(temp_vec[1], temp_vec[0])


def align_bounding_box(stdscr, bbox: UIgraph.Point, margin: UIgraph.Point,
                       align_h: int = 0, align_v: int = 0):
    """Give the position of the bounding box aligned according the options,
    align_h: right=0, center=1, left=2
    align_v: top=0, center=1, bottom=2
    the margin.x is used as distance from the margin, both in align right and left
    margin.y is used as distance from the top margin or lower margin"""

    win_dim = get_win_dimension(stdscr)
    assert win_dim.x > bbox.x and win_dim.y > bbox.y

    pos_x = None
    pos_y = None

    match align_h:
        case 0:
            pos_x = margin.x
        case 1:
            pos_x = int((win_dim.x - bbox.x) // 2)
        case 2:
            pos_x = win_dim.x - margin.x - bbox.x

    match align_v:
        case 0:
            pos_y = margin.y
        case 1:
            pos_y = int((win_dim.y - bbox.y) // 2)
        case 2:
            pos_y = win_dim.y - margin.y - bbox.y

    return UIgraph.Point(pos_x, pos_y)


def create_text_aligned(stdscr, margin: UIgraph.Point, text: str, P_text_color,
                        bold: bool = False, inv_color=False, align_h: int = 0,
                        align_v: int = 0):
    """Create normal text with align options,
    align_h: right=0, center=1, left=2
    align_v: top=0, center=1, bottom=2
    the margin.x is used as distance from the margin, both in align right and left
    margin.y is used as distance from the top margin or lower margin"""

    temp_vec = stdscr.getmaxyx()
    box_dim = UIgraph.Point(temp_vec[1], temp_vec[0])

    pos_x = None
    pos_y = None

    text_array = []
    if len(text) > box_dim.x:
        while len(text) > box_dim.x:
            text_array.append(text[:box_dim.x - 8])
            text = text[box_dim.x:]
        else:
            text_array.append(text)
    else:
        text_array.append(text)

    for e, sub_text in enumerate(text_array):
        text_len = len(sub_text)
        match align_h:
            case 0:
                pos_x = margin.x
            case 1:
                pos_x = int((box_dim.x - text_len) // 2)
            case 2:
                pos_x = box_dim.x - margin.x - text_len

        # TODO: add centering multiline text
        match align_v:
            case 0:
                pos_y = margin.y
            case 1:
                pos_y = int((box_dim.y - 1) // 2)
            case 2:
                pos_y = box_dim.y - margin.y - 1

        pos = UIgraph.Point(pos_x, pos_y)
        create_text(stdscr, pos + UIgraph.Point(0,e), sub_text, P_text_color, bold, inv_color=inv_color)


def create_blinking_text(scr, pos: UIgraph.Point, text: str, P_text_color, bold: bool = False):
    """Create blinking text by inverting the colors based on the timestamp."""
    blink = 0.6  # second
    now = datetime.now().timestamp()
    toggle = int(now / blink % 2)
    if toggle:
        scr.attron(curses.A_REVERSE)
    else:
        scr.attroff(curses.A_REVERSE)

    scr.attron(curses.color_pair(P_text_color))
    if bold:
        scr.attron(curses.A_BOLD)
    scr.addstr(pos.y, pos.x, str(text))

    # restore attribute
    scr.attroff(curses.A_BOLD)
    scr.attroff(curses.A_REVERSE)


def create_prompt(stdscr, screen_state: ScreenState, keyboard_state: KeyboardState, parent_scope: Scope, name: str,
                  pos: UIgraph.Point, pre_text: str, total_length: int, P_text_color, bold: bool = False,
                  inverse_color: bool = False, custom_scope_function=None, ui_error_inside_the_prompt=False, prepped_scope=None,
                  P_text_field=None, C_selected=None):
    """prompt text"""
    # TODO limit text displayed...
    # TODO when esc, check the data, or esc and enter should be the same...

    nome_str = name
    name = f"{parent_scope.id}_{name}"

    # selection color
    text_color_pair = UIgraph.customColorsPairs_findByValue(
        screen_state.cursesColors,
        P_text_color)
    text_color_background = text_color_pair[1]
    gray = UIgraph.customColors_findByValue(screen_state.cursesColors, screen_state.colors['gray'])

    P_select = UIgraph.addCustomColorTuple(
        (gray, text_color_background),
        screen_state.cursesColors
    )

    RGB_selected = UIgraph.customColors_findByValue(screen_state.cursesColors, C_selected)
    if C_selected is not None:
        P_selected = UIgraph.addCustomColorTuple(
            (RGB_selected, text_color_background),
            screen_state.cursesColors
        )
    else:
        P_selected = screen_state.colorPairs["tab_dark"]
    P_error = screen_state.colorPairs["error"]
    P_error_white = screen_state.colorPairs["error_white"]
    if P_text_field is None:
        P_text_field = screen_state.colorPairs["text_field"]

    if name not in screen_state.scopes and prepped_scope is None:
        scope = Scope(name, parent_scope.screen, screen_state)
        scope.parent_scope = parent_scope
        scope.main_scope = parent_scope
        scope.exec = ScopeActions.activate_scope
        parent_scope.sub_scopes[name] = scope
        scope.visible = True

        if custom_scope_function is None:
            scope.exec_own = ScopeActions.exit_scope
        else:
            scope.exec_own = custom_scope_function

        scope.data["prompt"] = ""
        scope.data["cursor"] = 0
        scope.data["valid_data"] = True
        scope.data["invalid_data_message"] = 'INV'
        scope.data["short_invalid_data_message"] = 'Invalid'

    scope: Scope = screen_state.scopes[name]
    scope.visible = True
    scope.base_point = pos
    scope_exec_args = [screen_state]
    prompt = scope.data["prompt"]
    invalid_data_message = scope.data['invalid_data_message']

    # check cursor position
    if scope.data['cursor'] < 0:
        scope.data['cursor'] = 0
    elif scope.data['cursor'] > len(scope.data['prompt']):
        scope.data['cursor'] = len(scope.data['prompt'])

    scope_state = False
    if scope is screen_state.activeScope:
        scope.mode = ScopeMode.INSERT
        screen_state.scope_exec_args = scope_exec_args
        scope_state = True
        P_select = P_selected
        scope.data["valid_data"] = True

    # text area
    # field = u'\u2591' * total_length  # old filler
    field = ' ' * total_length
    if scope.selected():
        screen_state.footer_text += "| paste=ctrl-v "
        stdscr.attron(curses.A_REVERSE)
        stdscr.addstr(pos.y, pos.x, field, curses.color_pair(P_text_field))
        stdscr.attroff(curses.A_REVERSE)
        stdscr.addstr(pos.y + 1, pos.x, u'\u2580' * total_length,
                      curses.color_pair(P_select))
        stdscr.addstr(pos.y + 1, pos.x + total_length, u'\u2598',
                      curses.color_pair(P_select))
        for i in range(1):
            stdscr.addstr(pos.y + i, pos.x + total_length, u'\u258c',
                          curses.color_pair(P_select))
        # special keyboard 
        if keyboard_state.delete:
            scope.data['prompt'] = ''
            scope.data['cursor'] = 0

    else:
        stdscr.addstr(pos.y, pos.x, field, curses.color_pair(P_text_field))

    # pre text
    if bold:
        stdscr.attron(curses.A_BOLD)
    if inverse_color:
        stdscr.attron(curses.A_REVERSE)
    stdscr.addstr(pos.y, pos.x, pre_text, curses.color_pair(P_text_color) | curses.A_BOLD)

    # truncate prompt if needed
    field_length = len(field) - len(pre_text) - 1
    prompt_idx = scope.data['cursor']
    local_prompt_idx = prompt_idx
    formatted_prompt = prompt

    if prompt_idx > field_length:
        local_prompt_idx = field_length
        delta_cursor = len(prompt) - prompt_idx
        formatted_prompt = prompt[len(prompt) - field_length - delta_cursor:len(prompt) - delta_cursor]
    else:
        if len(prompt) >= field_length:
            formatted_prompt = prompt[:field_length]

    stdscr.addstr(pos.y, pos.x + len(pre_text), formatted_prompt, curses.color_pair(P_text_field) | curses.A_BOLD)
    stdscr.attroff(curses.A_REVERSE)

    if scope_state:
        if len(prompt) <= prompt_idx:  # check if we are on the peak o the string
            stdscr.addstr(pos.y, pos.x + len(pre_text) + local_prompt_idx, u'\u2588', curses.color_pair(P_text_field))
            cursor_pos = pos + UIgraph.Point(len(pre_text) + local_prompt_idx, 0)
            create_blinking_text(stdscr, cursor_pos, u'\u2588', P_text_field)
        else:
            cursor_pos = pos + UIgraph.Point(len(pre_text) + local_prompt_idx, 0)
            create_blinking_text(stdscr, cursor_pos, prompt[prompt_idx], P_text_field)

    if not scope.data['valid_data']:
        if pos.x + len(field) + len(invalid_data_message) < stdscr.getmaxyx()[1] and ui_error_inside_the_prompt:
            stdscr.addstr(pos.y, pos.x + len(field) + 1, invalid_data_message, curses.color_pair(P_error))
        else:
            mes = scope.data["short_invalid_data_message"]
            stdscr.addstr(pos.y, pos.x + len(field) - len(mes), mes, curses.color_pair(P_error_white))

    # if pasted
    paste_scope = screen_state.scopes['paste']
    if (keyboard_state.paste and scope_state) or (keyboard_state.paste and scope.selected) or screen_state.activeScope == paste_scope:
        # create a new over scope where you can select the bit of info you want
        def paste_action():
            create_paste_banner(stdscr, screen_state, scope, False)
        screen_state.pending_action.append([1, paste_action])

    return scope


def create_text_figlet(scr, pos: UIgraph.Point, figlet_font, text: str, P_text_color):
    """Create figlet text."""

    scr.attron(curses.color_pair(P_text_color))
    s = TEXT.renderFont(text, figlet_font)
    for n, line in enumerate(s):
        scr.addstr(pos.y + n, pos.x, line)


def create_text_double_space(scr, screenState: ScreenState, pos: UIgraph.Point, text: str,
                             P_text_color, C_background_color, edge_type: int,
                             bold: bool = False, inv_color: bool = False):
    """What?
    edge_type: 0 first row, 1 middle row, 2 end row, 3 single row"""
    ### TODO: P_background_color, could be a single color, C_backgroung.
    ### the example is in the screen_wallet

    col = pos.x
    row = pos.y
    text = f" {text} "  # add the frame
    text_len = len(text)

    text_color_pair = UIgraph.customColorsPairs_findByValue(
        screenState.cursesColors,
        P_text_color)
    default_background = UIgraph.customColors_findByValue(
        screenState.cursesColors,
        C_background_color)

    if inv_color:
        text_color_background = text_color_pair[0]
        new_pair = (default_background, text_color_background)
    else:
        text_color_background = text_color_pair[1]
        new_pair = (text_color_background, default_background)

    P_frame = UIgraph.addCustomColorTuple(
        new_pair,
        screenState.cursesColors
    )


    scr.attron(curses.color_pair(P_frame))
    if bold:
        scr.attron(curses.A_BOLD)
    if inv_color:
        scr.attron(curses.A_REVERSE)


    if edge_type == 3:
        scr.addstr(row, col, u'\u2584' * (text_len))
        scr.addstr(row + 2, col, u'\u2580' * (text_len))
    if edge_type == 0:
        scr.addstr(row, col, u'\u2584' * (text_len))
        scr.addstr(row + 2, col, u'\u2588' * (text_len))
    if edge_type == 2:
        #curses.A_REVERSE
        scr.addstr(row, col, u'\u2580' * (text_len))
        scr.addstr(row + 2, col, u'\u2584' * (text_len))
    if edge_type == 1:
        #scr.attroff(curses.A_BOLD)
        #scr.attron(curses.color_pair(P_text_color) | curses.A_BOLD)
        scr.addstr(row, col, u'\u2588' * (text_len))
        #scr.attron(curses.color_pair(P_background_color) | curses.A_BOLD)
        scr.addstr(row + 2, col, u'\u2580' * (text_len))
    row += 1
    scr.attron(curses.color_pair(P_text_color))
    scr.addstr(row, col, ' ' * (text_len))
    scr.addstr(row, col, str(text))

    # disable bold
    scr.attroff(curses.A_REVERSE)
    scr.attroff(curses.A_BOLD)


# double space is not clear
def text_double_space(scr, pos: UIgraph.Point, text: str,
                      P_text_color, P_background_color,
                      edge_type: int, row_height: int):
    """ Create test with some space around...
    edge_type: 1 firt row, 2 middle row, 3 end row, 0 single row
    row_height"""

    col = pos.x
    row = pos.y
    row_end = row + row_height
    text_len = len(text)
    scr.attron(P_background_color | curses.A_BOLD)
    if row_height % 2 == 0:
        scr.addstr(row, col, u'\u2584' * (text_len))
        row += 1
        c = 0
        while row < row_end:
            scr.addstr(row, col, u'\u2588' * (text_len))
            row += 1
        try:
            scr.addstr(row, col, u'\u2580' * (text_len))
        except:
            # curses bug
            print("its a bug")
            pass
        row = pos.y + row_height // 2

    else:
        c = 0
        while row <= row_end:
            scr.addstr(row, col, u'\u2588' * (text_len))
            row += 1
            c += 1
        row = pos.y + row_height // 2

    '''
    if edge_type == 0:
        scr.addstr(row, col, u'\u2584' * (text_len))
        scr.addstr(row + 2, col, u'\u2580' * (text_len))
    if edge_type == 1:
        scr.addstr(row, col, u'\u2584' * (text_len))
        scr.addstr(row + 2, col, u'\u2588' * (text_len))
    if edge_type == 2:
        scr.addstr(row, col, u'\u2588' * (text_len))
        scr.addstr(row + 2, col, u'\u2580' * (text_len))
    if edge_type == 3:
        scr.addstr(row, col, u'\u2580' * (text_len))
        scr.addstr(row + 2, col, u'\u2584' * (text_len))
    '''

    scr.attron(P_text_color)
    scr.addstr(row, col, str(text))

    # disable bold
    scr.attroff(curses.A_BOLD)


### TODO: not sure if it is worth
### TODO: make: selection, total_item_count, as parameter for the create_tab functions
#def create_tab_from_chunk_loader(stdscr,
#                                 screen_state: ScreenState,
#                                 keyboard_state,
#                                 parent_scope: Scope,
#                                 tab_name: str,
#                                 chunk_loader: WDB.DataChunkLoader,
#                                 chunk_data_parser: Callable = None,
#                                 scope_activation_func,
#                                 active=False,  # to implement
#                                 multiple_selection=False,
#                                 data_table_legend=None):
#    """Wrap create_tab to accept chunk_loader"""
#
#    # get the scope.cursor and load the chunks...
#    chunk_size = chunk_loader.chunk_size
#    data_table, first_idx = chunk_loader.get_items_hot_chunks()
#    lapper.clocking("get hot chunk")
#    # remove None elements
#    ## TODO: is it necessary?
#    data_table = [row for row in dataTable if row is not None]
#
#    total_item_count = chunk_loader.total_row_count
#    row_count = len(data_table)
#    circular_selection = False
#
#    if chunk_data_parser is not None:
#        data_table, data_table_keys = chunk_data_parser(data_table)
#
#    # it needs to be after the scope update
#    selected_idx = scope.cursor
#    if chunk_loader:
#        chunk_loader.update_offset(selected_idx)
#
#    # needed for lateral bar
#    original_idx_first_element = idx_first_element
#    if chunk_loader:
#        idx_first_element -= first_idx
#        idx_last_element -= first_idx
#        select -= first_idx
#
#
#    tab = create_tab(
#        stdscr,  # stdscr,
#        screen_state,  # screenState: ScreenState,
#        parent_scope,  # parent_scope: Scope,
#        tab_name,  # tab_name: str,
#        data_table,  # dataTable,
#        data_table_keys,  # data_table_keys: List[str],
#        data_table_color,  # data_table_color,
#        transpose,  # transpose: bool,
#        position,  # position: UIgraph.Point,
#        size,  # size: UIgraph.Point,
#        keyboard_state,  # keyboardState,
#        scope_activation_func,  # scope_activation_func,
#        False,  # active=False,  # to implement
#        False,  # multipleSelection=False,
#        data_table_legend,  # data_table_legend=None,
#        None,  # chunk_loader: WDB.DataChunkLoader=None,
#        None)  # chunk_data_parser=None)
#

def create_tab(scr,
               screenState: ScreenState,
               parent_scope: Scope,
               tab_name: str,
               dataTable,
               data_table_keys: List[str],
               data_table_color,
               transpose: bool,
               position: UIgraph.Point,
               size: UIgraph.Point,
               keyboardState,
               scope_activation_func,
               active=False,  # to implement
               multipleSelection=False,
               data_table_legend=None,
               column_widths=None,
               formatters=None,
               chunk_loader: WDB.DataChunkLoader = None,
               chunk_data_parser=None,
               prepped_scope=None):

    """Create a beautiful and shining tab
    dataTable: 2dim data list
    data_table_keys: key used when something is selected
    position: relative to the parent win
    size: if it fit in the parent win
    active: if we can select elements"""

    ### name
    tab_name = f"{parent_scope.id}_{tab_name}"

    ### init scope and add to parent
    if tab_name not in screenState.scopes and prepped_scope is None:
        scope = Scope(tab_name, parent_scope.screen, screenState)
        scope.parent_scope = parent_scope
        scope.main_scope = parent_scope
        scope.exec = ScopeActions.activate_scope
        parent_scope.sub_scopes[tab_name] = scope
        scope.visible = True

        scope.exec_own = scope_activation_func

    ### end init scope stuff ####

    scope: Scope = screenState.scopes[tab_name]
    scope.set_visible()
    scope.base_point = position

    ## TODO: check if the list is change, if yes reset the 'column_sizes'

    if 'lapper' not in scope.data:
        scope.data["lapper"] = UTILS.Timer('tabba')
    lapper = scope.data["lapper"]
    lapper.start()
    lapper.clocking("begin")

    ### transpose if needed
    # the shape of the data should be like this:
    # [['DBX', '61.0000', '0.0041477', '-0.601%', '0.10754', '-0.601%', '0.25301', '6.55972'],
    # ['MBX', '218853', '8.2087e-07', '-0.226%', '0.000021282', '-0.226%', '0.17965', '4.65769'],
    # [...]]
    ### TODO: traspose is too costly for large dataset, the data should be right from the beginning
    ### or chached it
    #if transpose and dataTable:
    #    if 'transposed' not in scope.data or scope.data['transposed'] is None:
    #        if dataTable:
    #            dataTable = transpose_table(dataTable)
    #            scope.data['cached_data_table'] = dataTable
    #            scope.data['transposed'] = True
    #        if data_table_color:
    #            data_table_color = transpose_table(data_table_color)
    #            scope.data['data_table_color'] = data_table_color

    if transpose:
        dataTable = transpose_table(dataTable)
        if data_table_color:
            data_table_color = transpose_table(data_table_color)

    ### Manage dataloader
    ### TODO: create a different fun the init a loader as a list and then call create_tab
    tab_scope_is_active = False
    scope_exec_args = [screenState]
    chunk_size = None
    chunk_first_idx = None
    total_item_count = None
    row_count = None
    circular_selection = True
    lapper.clocking("if chunk")
    if chunk_loader:
        # get the scope.cursor and load the chunks...
        chunk_size = chunk_loader.chunk_size
        dataTable, first_idx = chunk_loader.get_items_hot_chunks()
        lapper.clocking("get hot chunk")
        # remove None elements
        dataTable = [row for row in dataTable if row is not None]
        lapper.clocking("remove None")

        total_item_count = chunk_loader.total_row_count
        row_count = len(dataTable)
        circular_selection = False

        lapper.clocking("some stuffs")
        if chunk_data_parser is not None:
            dataTable, data_table_keys = chunk_data_parser(dataTable)
        lapper.clocking("parser chunks")
        # update the offset in the loader
        # chunk_loader.update_offset(select)
    elif chunk_loader == []:
        total_item_count = 0
        row_count = 0
        dataTable = []
    elif dataTable is not None:
        total_item_count = len(dataTable)
        row_count = len(dataTable)
    else:
        dataTable = []
        total_item_count = 0
        row_count = 0

    ### end

    ### FRAME CACHE
    if 'cached_data_table' not in scope.data or scope.data['cached_data_table'] is None:
        scope.data['cached_data_table'] = dataTable
        scope.data['cached_data_table_color'] = data_table_color
        scope.data['cached_data_table_legend'] = data_table_legend
        scope.data['cached_column_widths'] = column_widths
        scope.data['cached_formatters'] = formatters
        scope.data['chunk_first_idx'] = chunk_first_idx
    else:
        old_data_table = scope.data['cached_data_table']
        old_first_idx = scope.data['chunk_first_idx']

        # compare only the first element and the first chunk idx
        # TODO: check also size of the windows change
        if (dataTable and
            len(dataTable[0]) == len(old_data_table[0]) and
            dataTable[0] == old_data_table[0] and
            dataTable[-1] == old_data_table[-1] and
            chunk_first_idx == old_first_idx and
            not screenState.screen_resized):

            dataTable = old_data_table
            data_table_color = scope.data['cached_data_table_color']
            data_table_legend = scope.data['cached_data_table_legend']
            column_widths = scope.data['cached_column_widths']
            formatters = scope.data['cached_formatters']
            # TODO: load teh cache?
        else:
            # TODO: implent cache filling later in the code
            scope.data['cached_data_table'] = dataTable
            scope.data['cached_data_table_color'] = data_table_color
            scope.data['cached_data_table_legend'] = data_table_legend
            scope.data['cached_column_widths'] = column_widths
            scope.data['cached_formatters'] = formatters
            # scope.data['transposed'] = None  # NOT IMPL
            # scope.data['casted_data_table'] = None  # we do not cast...
            scope.data['column_sizes'] = None

    lapper.clocking("we chunk")

    ### update scope
    if scope is screenState.activeScope:
        scope.update_no_sub(total_item_count, circular=circular_selection)
        screenState.scope_exec_args = scope_exec_args
        tab_scope_is_active = True
        screenState.footer_text += "| copy=y "
    ### end scope stuff ####

    # it needs to be after the scope update
    selected_idx = scope.cursor
    if chunk_loader:
        chunk_loader.update_offset(selected_idx)


    ### if no data, make an epmty line

    if len(dataTable) == 0:
        if data_table_legend is not None or len(data_table_legend) > 0:
            new_empty_line = []
            for i in data_table_legend:
                new_empty_line.append('')
            new_empty_line[0] = "empty table"
            dataTable.append(new_empty_line)

    lapper.clocking("first color init")

    ### make empty data_table_color if...
    if data_table_color is None or not data_table_color:
        if 'data_table_color' not in scope.data or scope.data['data_table_color'] == None:
            row = len(dataTable)
            col = len(dataTable[0])
            data_table_color = [list([None] * col) for _ in range(row)]
            scope.data['data_table_color'] = data_table_color
        else:
            data_table_color = scope.data['data_table_color']

    if column_widths is None:
        if len(dataTable) > 0:
            column_widths = [None] * len(dataTable[0])
        elif data_table_legend:
            column_widths = [None] * len(data_table_legend)

    if formatters is None:
        if len(dataTable) > 0:
            formatters = [None] * len(dataTable[0])
        elif data_table_legend:
            formatters = [None] * len(data_table_legend)

    lapper.clocking("color_ewnd")

    ### assert the shape of the data
    if data_table_legend:
        if len(dataTable) == 0:
            pass
        else:
            assert len(data_table_legend) == len(dataTable[0]), f"legend data length ({len(data_table_legend)}) differ from the data ({len(dataTable[0])})"
            assert len(data_table_legend) == len(column_widths), f"column widths list lenght ({len(column_widths)}) differ from the data ({len(dataTable[0])})"
            assert len(data_table_legend) == len(formatters), f"formatters list lenght ({len(formatters)}) differ from the data ({len(dataTable[0])})"

    lapper.clocking("first")

    ### tab geometry
    ## get the dimensions and the position of the main window and calculate the pos
    ## relative to those
    temp_vec = scr.getmaxyx()
    parent_win_dim = UIgraph.Point(temp_vec[1], temp_vec[0])
    temp_vec = scr.getbegyx()
    parent_win_pos = UIgraph.Point(temp_vec[1], temp_vec[0])

    main_win_size = screenState.screen_size
    win_width = screenState.screen_size.x
    win_height = screenState.screen_size.y

    abs_pos_x = position.x + parent_win_pos.x
    abs_pos_y = position.y + parent_win_pos.y
    pos_x = position.x
    pos_y = position.y
    x_tabSize = size.x
    y_tabSize = size.y
    if y_tabSize + pos_y + 1 > parent_win_dim.y:
        y_tabSize = parent_win_dim.y - pos_y - 1

    height_low_bar = 1
    height_legend = 3
    if data_table_legend is None:
        height_legend = 0

    ### TODO: remove
    ### make the data as string before, it is wastefull to cast everything every frame
    lapper.clocking("cast init")

    ### curse customs colors
    P_soft = screenState.colorPairs["tab_soft"]
    P_dark = screenState.colorPairs["tab_dark"]
    P_soft_bg = screenState.colorPairs["tab_soft_bg"]
    P_select = screenState.colorPairs["tab_select"]
    P_selected = screenState.colorPairs["tab_selected"]
    P_win_selected = screenState.colorPairs["win_selected"]
    if tab_scope_is_active:
        P_win_selected = screenState.colorPairs["body"]
    P_win_background = screenState.colorPairs["tab_soft"]

    # background for custom colors
    C_default_background = screenState.colors["background"]
    C_soft_background = screenState.colors["tab_soft"]
    C_dark_background = screenState.colors["tab_dark"]

    table_bk_colors = [C_soft_background, C_dark_background]  # these are not pairs
    table_color_pairs = [P_soft, P_dark]


    ### tab creation
    if multipleSelection:
        scope.data["idx_selected"] = []
    if "idx_first_element" not in scope.data:
        scope.data["idx_first_element"] = 0
    idx_first_element = scope.data["idx_first_element"]

    # afterward
    col_len = row_count
    visible_row_count = y_tabSize - height_low_bar - height_legend

    lapper.clocking("first inti alst")
    ### recalculate firt and last element
    idx_first_element, idx_last_element, select = recalcultate_first_and_last_element(selected_idx, idx_first_element, visible_row_count)
    #### update first element when window is resized
    tab_length = idx_last_element - idx_first_element
    if tab_length < visible_row_count:
        idx_first_element = max(idx_first_element - (visible_row_count - tab_length), 0)
        idx_first_element, idx_last_element, select = recalcultate_first_and_last_element(selected_idx, idx_first_element, visible_row_count)

    lapper.clocking("calu first alst")
    ### update first element
    scope.data["idx_first_element"] = idx_first_element

    # needed for lateral bar
    original_idx_first_element = idx_first_element
    if chunk_loader:
        idx_first_element -= first_idx
        idx_last_element -= first_idx
        select -= first_idx


    if chunk_loader:
        global DEBUG_OBJ
        DEBUG_OBJ.text = (
            f"first el: {idx_first_element} | last el: {idx_last_element} | scp.cur; {scope.cursor} | sel: {select} |"
            f" c. off: {chunk_loader.current_offset} | c. arena id: {chunk_loader.main_chunk_pointer} |"
            f" dataT len: {len(dataTable)} | first id {first_idx} | "
            f" firstIdx {idx_first_element}, lastIdx: {idx_last_element}, select {select} count: {visible_row_count}, countEff: {idx_last_element - idx_first_element}"
        )

    count = 0

    ### max dim for the table
    max_table_width = parent_win_dim.x - position.x - 2  # CONST for borders
    x_tabSize = max_table_width

    table = scr.subwin(y_tabSize, x_tabSize, abs_pos_y, abs_pos_x)
    table.bkgd(' ', curses.color_pair(P_win_background))

    ### highlight scope if selected
    if scope.selected():
        scr.addstr(pos_y + y_tabSize, pos_x, u'\u2580' * x_tabSize,
                   curses.color_pair(P_win_selected))
        scr.addstr(pos_y + y_tabSize, pos_x + x_tabSize, u'\u2598',
                   curses.color_pair(P_win_selected))
        for i in range(y_tabSize):
            scr.addstr(pos_y + i, pos_x + x_tabSize, u'\u258c',
                       curses.color_pair(P_win_selected))

    lapper.clocking("second")

    # calculate max dim and max number of columns
    # TODO: calc max size only for the visible columns
    # it is too slow on big list
    # or 
    # move outside as a precalc for all the list
    # or
    # make a persisten data so you do not recalc every time

    #if True:
    # TODO: make it None when the block_loader change of one unit, or calculate in a thread
    if 'column_sizes' not in scope.data or scope.data['column_sizes'] is None:
        x_colSize, x_colStart, max_str_len_columns = calc_size_column(
            dataTable, data_table_color, data_table_legend,
            scope, max_table_width, multipleSelection,
            x_tabSize, column_widths, formatters)
        scope.data['column_sizes'] = (x_colSize, x_colStart, max_str_len_columns)
    else:
        x_colSize, x_colStart, max_str_len_columns = scope.data['column_sizes']

    lapper.clocking("max size")

    ### legend loop ###
    row = 0
    if data_table_legend is not None:

        frame_legend = UIgraph.addCustomColorTuple(
            (C_soft_background, C_default_background),
            screenState.cursesColors)
        table.attron(curses.color_pair(frame_legend) | curses.A_BOLD)

        table.addstr(row, 0, u'\u2584' * (x_tabSize))
        table.addstr(row + 2, 0, u'\u2580' * (x_tabSize))
        row += 1
        table.attron(curses.color_pair(P_soft))
        table.addstr(row, 0, ' ' * (x_tabSize))
        if multipleSelection:
            table.addstr(row, 0, u' \u25A1 /\u25A0')
        else:
            table.addstr(row, 0, ' ')
        for idx, leg_item in enumerate(data_table_legend):
            table.addstr(row, x_colStart[idx], str(leg_item))
        table_color_pairs.reverse()  # to begin always with the soft color
        table_bk_colors.reverse()  # to begin always with the soft color

        # disable bold
        table.attroff(curses.A_BOLD)

    current_selection_data = None
    ### data loop ###
    row = height_legend
    sliced_raw_dataTable = dataTable[idx_first_element:idx_last_element]
    sliced_idx_dataTable = range(idx_first_element, idx_last_element)


    # TODO: test casting only showed data
    sliced_dataTable = cast_table_items_to_string(sliced_raw_dataTable, formatters)

    for data_row, raw_data_row, data_idx in zip(sliced_dataTable, sliced_raw_dataTable, sliced_idx_dataTable):
        C_custom_bk = table_bk_colors[row % 2]
        P_current_attron = curses.color_pair(table_color_pairs[row % 2])  # calling it P_... is misleading
        if data_idx == select and tab_scope_is_active:
            P_current_attron = curses.color_pair(P_select)
            scope_exec_args.append(data_table_keys[data_idx] if data_table_keys else None)
            current_selection_data = raw_data_row
        elif data_idx == select:
            current_selection_data = raw_data_row


        table.attron(P_current_attron)
        table.addstr(row, 0, ' ' * (x_tabSize))
        ##################################################
        #####work around curses bug last char last column
        ##################################################
        #try:
        #    table.addstr(data_idx, 0, ' ' * (x_tabSize))
        #except:
        #    pass
        ###################################################

        if multipleSelection:
            if data_idx in scope.data['idx_selected']:
                P_current_attron = curses.color_pair(P_selected)
                C_custom_bk = screenState.colors["chia_green"]
                table.attron(P_current_attron)
                table.addstr(data_idx, 0, ' ' * (x_tabSize))
                table.addstr(row, 1, u' \u25A0')
            else:
                table.addstr(row, 1, u' \u25A1')

        # check also the colors after the transpose, they could be broken
        for i_col, col in enumerate(data_row):
            text_color = data_table_color[data_idx][i_col]
            if text_color is not None and (data_idx != select or not tab_scope_is_active):
                text_c_pair = UIgraph.addCustomColorTuple(
                    (text_color, C_custom_bk),
                    screenState.cursesColors)
                table.attron(curses.color_pair(text_c_pair))

            max_str_length = max_str_len_columns[i_col] - 2  # free space for columns -> it is the COST column separator in calc_column_width
            if len(col) > max_str_length:
                if max_str_length > 10:
                    col = col[:max_str_length - 10] + "<...>" + col[len(col) - 5:]
                elif max_str_length > 4:
                    col = col[:max_str_length - 4] + "<...>"
                else:
                    col = "." * max_str_length


            table.addstr(row, x_colStart[i_col], str(col))
            table.attron(P_current_attron)


        row += 1
        count += 1


    ### position bar
    P_soft = screenState.colorPairs["tab_soft_bg"]
    P_dark = screenState.colorPairs["tab_dark"]
    P_win_selected = screenState.colorPairs["win_selected"]

    row_selected = select
    # idx_first_element
    # idx_last_element

    lapper.clocking("thirdddd")

    steps = total_item_count - visible_row_count
    if steps > 0:
        bar_dim = max(visible_row_count - steps, 1)
        bar_pos = floor(original_idx_first_element / steps * min(steps, visible_row_count - 1))

        #global DEBUG_OBJ
        #DEBUG_OBJ.text = (
        #    f"steps: {steps}, bar_dim: {bar_dim}, bar_pos: {bar_pos}"
        #    f" visible_row_count: {visible_row_count}, tot_elem: {col_len}"
        #    f" ratio idx/step: {original_idx_first_element / steps}"
        #)

        bar_row = height_legend
        table.attron(curses.color_pair(P_soft))
        for i in range(visible_row_count):
            if i == bar_pos:
                table.attron(curses.color_pair(P_dark))
            elif i == (bar_pos + bar_dim):
                table.attron(curses.color_pair(P_soft))
            table.addstr(bar_row + i, max_table_width - 1, u'\u2588')
            #table.addstr(bar_row + i, max_table_width - 1, ' ')


    ### end of the window
    table.attron(curses.color_pair(P_soft_bg) | curses.A_BOLD)
    while row <= (y_tabSize - height_low_bar):
        try:
            # TODO: default terminal of ubuntu struggles doing a whole screen of this char
            #table.addstr(row, 0, u'\u2571' * (x_tabSize))
            #table.addstr(row, 0, u'\u002F' * (x_tabSize))
            table.addstr(row, 0, '/' * (x_tabSize))
        except:
            ### last line curses bug ###
            pass
        row += 1
    table.attroff(curses.A_BOLD)

    # if yanked
    copy_scope = screenState.scopes['copy']
    if (keyboardState.yank and tab_scope_is_active) or (scope.selected() and screenState.activeScope == copy_scope):
        # create a new over scope where you can select the bit of info you want
        def copy_action():
            create_copy_banner(table, screenState, scope, current_selection_data, False)
        screenState.pending_action.append([1, copy_action])

    lapper.clocking("end inside")
    lapper.end()
    print(lapper)

    return scope


def create_message_banner(stdscr, screenState: ScreenState, parent_scope: Scope,
                          address: str):
    ### name
    scope_name = f"{parent_scope.id}_the_message"

    ### init scope and add to paren
    if scope_name not in screenState.scopes:
        scope = Scope(scope_name, parent_scope.screen, screenState)
        scope.parent_scope = parent_scope
        scope.main_scope = parent_scope.main_scope
        scope.exec = ScopeActions.activate_scope
        #parent_scope.sub_scopes[scope_name] = scope

        scope.exec_esc = ScopeActions.exit_scope
        screenState.activeScope = scope

    scope: Scope = screenState.scopes[scope_name]
    scope.set_visible()
    tab_scope_is_active = False
    scope_exec_args = [screenState, address]

    if scope is screenState.activeScope:
        scope.update()
        screenState.scope_exec_args = scope_exec_args
        tab_scope_is_active = True

    #### end init

    if screenState.activeScope == scope or screenState.activeScope.name in scope.sub_scopes:

        P_body = screenState.colorPairs["body"]
        P_banner = screenState.colorPairs["copy_banner"]  # change with a paste bannnnner
        P_win_sel = screenState.colorPairs["up"]  # change with a paste bannnnner
        P_win_background = screenState.colorPairs["tab_soft"]
        temp_vec = stdscr.getmaxyx()
        win_dim = UIgraph.Point(temp_vec[1], temp_vec[0])
        width = int(win_dim.x * 0.85)
        height = 11
        pos_x = (win_dim.x - width) // 2
        pos_y = win_dim.y // 2 - height // 2

        banner = stdscr.subwin(height, width, pos_y, pos_x)
        banner.bkgd(' ', curses.color_pair(P_banner))

        temp_vec = banner.getmaxyx()
        ban_dim = UIgraph.Point(width, height)

        for i in range(height - 1):
            create_text(banner, UIgraph.Point(0, i), ' ' * ban_dim.x, P_banner, True)

        margin = UIgraph.Point(0,1)
        text = f"Address saved..."
        create_text_aligned(banner, margin, text, P_banner, align_h=1)
        margin += UIgraph.Point(0,1)
        create_text_aligned(banner, margin, f"{address}", P_banner, bold=True, align_h=1)
        pos = UIgraph.Point(1,4)

        button_name = 'ok'
        button_lenght = len(button_name) + 6
        bbox = UIgraph.Point(button_lenght, 1)
        margin += UIgraph.Point(0,2)
        pos = align_bounding_box(banner, bbox, margin, align_h=1)
        scope_search_button: Scope = create_button(banner, screenState, scope, button_name, pos,
                                                   custom_scope_function=ScopeActions.exit_scope_N(2),
                                                   button_type='execution',
                                                   C_background=screenState.colors['tab_softer'],      # background
                                                   C_text=screenState.colors['white'],                    # text
                                                   C_button=screenState.colors['chia_green'],  # button color
                                                   #C_button=screenState.colors['orange_btc'],  # button color
                                                   C_selection=screenState.colors['gray'],           # when selected
                                                   )


def create_save_address_banner(stdscr, screenState: ScreenState, parent_scope: Scope,
                               address: str):
    ### name
    #scope_name = f"{parent_scope.id}_{scope_name}"
    scope_name = "save_address_banner"

    ### init scope and add to paren
    if scope_name not in screenState.scopes:
        scope = Scope(scope_name, parent_scope.screen, screenState)
        scope.parent_scope = parent_scope
        scope.main_scope = parent_scope.main_scope
        scope.exec = ScopeActions.activate_scope
        #parent_scope.sub_scopes[scope_name] = scope

        scope.exec_esc = ScopeActions.exit_scope
        screenState.activeScope = scope

    scope: Scope = screenState.scopes[scope_name]
    scope.set_visible()
    tab_scope_is_active = False
    scope_exec_args = [screenState, address]

    if scope is screenState.activeScope:
        scope.update()
        screenState.scope_exec_args = scope_exec_args
        tab_scope_is_active = True

    #### init

    P_body = screenState.colorPairs["body"]
    P_banner = screenState.colorPairs["copy_banner"]  # change with a paste bannnnner
    P_win_sel = screenState.colorPairs["up"]  # change with a paste bannnnner
    P_win_background = screenState.colorPairs["tab_soft"]
    temp_vec = stdscr.getmaxyx()
    win_dim = UIgraph.Point(temp_vec[1], temp_vec[0])
    width = int(win_dim.x * 0.85)
    height = 11
    pos_x = (win_dim.x - width) // 2
    pos_y = win_dim.y // 2 - height // 2

    banner = stdscr.subwin(height, width, pos_y, pos_x)
    banner.bkgd(' ', curses.color_pair(P_body))

    temp_vec = banner.getmaxyx()
    ban_dim = UIgraph.Point(width, height)

    for i in range(height - 1):
        create_text(banner, UIgraph.Point(0, i), ' ' * ban_dim.x, P_banner, True)

    margin = UIgraph.Point(0,1)
    text = f"Do you want to save the following address?"
    create_text_aligned(banner, margin, text, P_banner, align_h=1)
    margin += UIgraph.Point(0,1)
    create_text_aligned(banner, margin, f"{address}", P_banner, bold=True, align_h=1)
    pos = UIgraph.Point(1,4)

    prompt_name = 'address_name'
    prompt_scope_name = f"{scope.id}_{prompt_name}"

    if prompt_scope_name not in screenState.scopes:
        prompt_scope = Scope(prompt_scope_name, parent_scope.screen, screenState)
        prompt_scope.parent_scope = scope
        prompt_scope.main_scope = scope.main_scope
        prompt_scope.exec = ScopeActions.activate_scope
        scope.sub_scopes[prompt_scope_name] = prompt_scope
        prompt_scope.visible = True

        prompt_scope.exec_own = ScopeActions.select_next_scope

        prompt_scope.data["prompt"] = ""
        prompt_scope.data["cursor"] = 0
        prompt_scope.data["valid_data"] = True
        prompt_scope.data["invalid_data_message"] = 'INV'

    prompt_scope = screenState.scopes[prompt_scope_name]

    pre_text = "Address name: "
    prompt_len = 40
    tot_len = len(pre_text) + prompt_len
    bbox = UIgraph.Point(tot_len, 1)
    margin += UIgraph.Point(0,2)
    pos = align_bounding_box(banner, bbox, margin, align_h=1)
    create_prompt(banner, screenState, KeyboardState, scope, prompt_name, pos,
                  pre_text, tot_len, P_banner, prepped_scope=prompt_scope,
                  ui_error_inside_the_prompt=False,
                  P_text_field=screenState.colorPairs['text_field_banner'],
                  C_selected=screenState.colors['chia_green'])

    scope_exec_args.append(prompt_scope.data['prompt'])
    scope_exec_args.append(prompt_scope)

    button_name = 'save address'
    button_lenght = len(button_name) + 6
    bbox = UIgraph.Point(button_lenght, 1)
    margin += UIgraph.Point(0,2)
    pos = align_bounding_box(banner, bbox, margin, align_h=1)
    scope_search_button: Scope = create_button(banner, screenState, scope, button_name, pos,
                                               custom_scope_function=ScopeActions.save_address,
                                               button_type='execution',
                                               C_background=screenState.colors['tab_softer'],      # background
                                               C_text=screenState.colors['white'],                    # text
                                               C_button=screenState.colors['chia_green'],  # button color
                                               #C_button=screenState.colors['orange_btc'],  # button color
                                               C_selection=screenState.colors['gray'],           # when selected
                                               )


# now we save the banner in screenState.pending_action, so only init should not be neccessary anymore...
def create_paste_banner(stdscr, screenState: ScreenState, parent_scope: Scope, only_init: bool):
    ### name
    tab_name = "paste"

    ### init scope and add to paren
    if screenState.scopes[tab_name] is None:
        scope = Scope(tab_name, parent_scope.screen, screenState)
        scope.parent_scope = parent_scope
        scope.main_scope = parent_scope.main_scope
        scope.exec = ScopeActions.activate_scope
        #parent_scope.sub_scopes[tab_name] = scope

        # retrive text from the clipboard
        os_clip = PLAT.read_clipboard()
        data = [os_clip] + list(screenState.roto_clipboard)
        scope.data['clipboard'] = data

        def paste(scope: Scope, screenState: ScreenState):
            prompt_scope = scope.parent_scope
            clip = scope.data['clipboard'][scope.cursor]
            idx = prompt_scope.data['cursor']
            s = prompt_scope.data['prompt']
            prompt_scope.data['prompt'] = s[:idx] + clip + s[idx:]
            prompt_scope.data['cursor'] += len(clip)
            screenState.activeScope = scope.parent_scope
            screenState.scopes[tab_name] = None
            return scope.parent_scope

        scope.exec_own = paste

        def deactivate_scope(scope: Scope, screenState: ScreenState):
            scope = ScopeActions.exit_scope(scope, screenState)
            screenState.scopes[tab_name] = None

        scope.exec_esc = deactivate_scope
        screenState.activeScope = scope

    scope: Scope = screenState.scopes[tab_name]
    tab_scope_is_active = False
    scope_exec_args = [screenState]
    data = scope.data['clipboard']
    if scope is screenState.activeScope:
        scope.update_no_sub(len(data))
        screenState.scope_exec_args = scope_exec_args
        tab_scope_is_active = True

    if only_init:
        return scope

    P_win_test = screenState.colorPairs["copy_banner"]  # change with a paste bannnnner
    P_win_sel = screenState.colorPairs["up"]  # change with a paste bannnnner
    temp_vec = stdscr.getmaxyx()
    win_dim = UIgraph.Point(temp_vec[1], temp_vec[0])
    width = int(win_dim.x * 0.85)
    height = 10
    pos_x = (win_dim.x - width) // 2
    pos_y = win_dim.y // 2 - height // 2

    banner = stdscr.subwin(height, width, pos_y, pos_x)

    temp_vec = banner.getmaxyx()
    ban_dim = UIgraph.Point(width, height)
    for i in range(height - 1):
        create_text(banner, UIgraph.Point(0, i), ' ' * ban_dim.x, P_win_test, True)

    p = UIgraph.Point(0,0)
    create_text_aligned(banner, p, "PASTE", P_win_test, True, align_h=1)

    p += UIgraph.Point(0,2)

    # formatting distance, truncating if necessary
    description_length = 19  # length of " | system clipboard"
    max_str_length = int((width - description_length) * (2/3))
    max_length = 0
    formatted_data = []
    for i in data:
        if len(i) > max_str_length:
            i = i[:max_str_length - 10] + "<...>" + i[len(i) - 5:]
        if len(i) > max_length:
            max_length = len(i)
        formatted_data.append(i)

    space = 10
    tot_length = max_length + description_length + space
    margin = floor((width - tot_length) / 2)

    selection = scope.cursor

    for i, item in enumerate(formatted_data):
        if i == 0:
            first_item = 0
            pre_fix = "System clipboard"
            p_text = p + UIgraph.Point(0, 1)
            create_text_aligned(banner, p_text, "/" * (max_length + description_length), P_win_test, True, align_h=1)
        else:
            first_item = 1
            pre_fix = "Roto clipboard"
        if selection == i:
            color_pair = P_win_sel
        else:
            color_pair = P_win_test
        p_text = p + UIgraph.Point(margin, i + first_item)
        create_text_aligned(banner, p_text, f"{1 + i} | {str(item)}", color_pair, True, align_h=0)
        create_text_aligned(banner, p_text, f"{pre_fix}", color_pair, True, align_h=2)


def create_copy_banner(stdscr, screenState: ScreenState, parent_scope: Scope, data,
                       only_init: bool):
    ### name
    tab_name = "copy"

    ### init scope and add to paren
    if screenState.scopes[tab_name] is None:
        scope = Scope(tab_name, parent_scope.screen, screenState)
        scope.parent_scope = parent_scope
        scope.main_scope = parent_scope.main_scope
        scope.exec = ScopeActions.activate_scope
        ## not added as sub-scope, or when i delete it, i should delete also from there?
        # parent_scope.sub_scopes[tab_name] = scope

        #scope.data['copied_data'] = data.insert(0, 'all')  # element to select everything
        # cast data
        data = data.copy()
        for idx, i in enumerate(data):
            data[idx] = str(i)

        data.insert(0, 'all')
        scope.data['copied_data'] = data

        def copy_to_clipboard(scope: Scope, screenState: ScreenState):
            if scope.cursor_x == 0:
                copied_item = str(scope.data['copied_data'])
            else:
                copied_item = scope.data['copied_data'][scope.cursor_x]
            PLAT.write_clipboard(copied_item)
            screenState.roto_clipboard.appendleft(copied_item)
            screenState.activeScope = scope.parent_scope
            screenState.scopes[tab_name] = None
            return scope.parent_scope

        scope.exec_own = copy_to_clipboard

        def deactivate_scope(scope: Scope, screenState: ScreenState):
            scope = ScopeActions.exit_scope(scope, screenState)
            screenState.scopes[tab_name] = None

        scope.exec_esc = deactivate_scope
        screenState.activeScope = scope

    scope: Scope = screenState.scopes[tab_name]
    tab_scope_is_active = False
    scope_exec_args = [screenState]
    data = scope.data['copied_data']  # to keep the data consistent

    if scope is screenState.activeScope:
        scope.update_no_sub(len(data))
        screenState.scope_exec_args = scope_exec_args
        tab_scope_is_active = True

    # TODO
    # update cursor_x
    # temp fix for keyboard execution left/right inverted
    # cursor_x = scope.cursor_x * -1 % len(data)
    cursor_x = scope.cursor_x  # % len(data)

    if only_init:
        return scope

    P_win_test = screenState.colorPairs["test"]
    P_win_test = screenState.colorPairs["copy_banner"]

    temp_vec = stdscr.getmaxyx()
    win_dim = UIgraph.Point(temp_vec[1], temp_vec[0])
    temp_vec = stdscr.getbegyx()
    win_pos = UIgraph.Point(temp_vec[1], temp_vec[0])

    width = int(win_dim.x * 0.85)
    height = 10
    pos_x = (win_dim.x - width) // 2
    pos_y = win_pos.y + win_dim.y // 2 - height // 2


    temp_vec = stdscr.getbegyx()
    win_pos = UIgraph.Point(temp_vec[1], temp_vec[0])

    banner = stdscr.subwin(height, width, pos_y, pos_x)

    temp_vec = banner.getmaxyx()
    ban_dim = UIgraph.Point(width, height)
    for i in range(4):
        create_text(banner, UIgraph.Point(0, i), ' ' * ban_dim.x, P_win_test, True)

    p = UIgraph.Point(0,0)
    create_text_aligned(banner, p, "COPY", P_win_test, True, align_h=1)


    # add text alignment to the functions.... and then add the copy title
    p = UIgraph.Point(0,2)
    #create_text_aligned(banner, p, str(data), P_win_test, True, align_h=1)

    # in line selector
    # data should be already in the form of string
    spacing = 3
    overlength_spacer = 10  # len of '<...>' + 5 chars
    separator = '|'

    # format the data in way that everything is always visible, no need for scrolling
    max_str_length = int(width / len(data))
    overlenght_word_count = 0
    other_word_tot_length = 0
    for i in data:
        if len(i) > max_str_length:
            overlenght_word_count += 1
        else:
            other_word_tot_length += len(i)

    if overlenght_word_count == 0:
        max_str_length = floor((width - spacing * len(data)) / len(data))
    else:
        max_str_length = floor((width - spacing * len(data) - other_word_tot_length -
            overlength_spacer * overlenght_word_count) / overlenght_word_count)

    formatted_data = []
    for i in data:
        if len(i) > max_str_length:
            i = i[:max_str_length - 10] + "<...>" + i[len(i) - 5:]
        formatted_data.append(i)



    data_len = []
    total_len = 0

    for i in formatted_data:
        data_len.append(len(i))
        total_len += len(i) + spacing

    if total_len < ban_dim.x:
        pos_x = (ban_dim.x - total_len) // 2
    else:
        pos_x = 2
        # TODO: implement logic to keep elements centererd on a multiline case

    p = UIgraph.Point(pos_x, 2)
    create_text(banner, p, separator, P_win_test, True)
    p += UIgraph.Point(1,0)
    for n, d in enumerate(formatted_data):
        text = f" {d} {separator}"
        if p.x + len(text) >= ban_dim.x:
            p = UIgraph.Point(pos_x, p.y + 2)
            # add also the separator at the beginning of the line
        create_text(banner, p, text, P_win_test, True)
        if cursor_x == 0 or cursor_x == n:
            selection_len = len(text) - len(separator)
            if cursor_x == 0:
                selection_len = len(text)
            create_text(banner, p + UIgraph.Point(0,1), u'\u2580' * selection_len, P_win_test, True)
        p += UIgraph.Point(len(text), 0)


def safe_addstr(win, y: int, x: int, string: str) -> None:
    """
    Safely writes a string to a curses window.
    Prevents crashes caused by curses throwing errors when writing to the 
    bottom-right character of a window.
    """
    try:
        win.addstr(y, x, string)
    except curses.error:
        pass


def create_tab_large(scr,
                     screenState,
                     parent_scope,
                     tab_name: str,
                     dataTable,
                     data_table_keys: List[str],
                     data_table_color,
                     transpose: bool,
                     pos,
                     size,
                     keyboardState,
                     sub_scope_activation,
                     row_height,
                     active=False,
                     multipleSelection=False,
                     data_table_legend=None,
                     column_widths=None,
                     formatters=None,
                     graph_data=None,
                     is_singular_item_table=True):
    """
    Create a beautiful and shining tab for large content blocks with custom row heights.
    - dataTable: 2-dimensional data list
    - data_table_keys: keys used when select actions fire
    - active: selection logic active
    - is_singular_item_table: if single-item, parent navigation is respected
    """
    ### Unique Name Assignment
    tab_name = f"{parent_scope.id}_{tab_name}"

    ### Scope Initialization & Registration
    if tab_name not in screenState.scopes:
        scope = Scope(tab_name, parent_scope.screen, screenState)
        scope.parent_scope = parent_scope
        scope.main_scope = parent_scope
        scope.exec = ScopeActions.activate_scope
        parent_scope.sub_scopes[tab_name] = scope
        scope.visible = True
        scope.exec_own = sub_scope_activation

    scope = screenState.scopes[tab_name]
    scope.set_visible()
    scope.base_point = pos

    ### Transpose if requested
    if transpose and dataTable:
        dataTable = transpose_table(dataTable)
        if data_table_color:
            data_table_color = transpose_table(data_table_color)

    ### Update scope status
    tab_scope_is_active = False
    scope_exec_args = [screenState]
    total_item_count = len(dataTable) if dataTable is not None else 0
    row_count = total_item_count

    if scope is screenState.activeScope:
        if False:  # Reserved fallback path matching your original logic structures
            screenState.activeScope = scope.parent_scope
        else:
            scope.update_no_sub(total_item_count)
            screenState.scope_exec_args = scope_exec_args
            tab_scope_is_active = True
            screenState.footer_text += "| copy=y "

    selected_idx = scope.cursor

    ### If no data, populate a fallback empty representation
    if total_item_count == 0:
        if data_table_legend:
            new_empty_line = [''] * len(data_table_legend)
            new_empty_line[0] = "empty table"
            dataTable = [new_empty_line]
            total_item_count = 1
            row_count = 1

    ### Ensure custom data table colors exist
    if data_table_color is None:
        row = len(dataTable)
        col = len(dataTable[0]) if row > 0 else 0
        data_table_color = [[None] * col for _ in range(row)]
        scope.data['data_table_color'] = data_table_color

    if column_widths is None:
        cols_count = len(dataTable[0]) if len(dataTable) > 0 else (len(data_table_legend) if data_table_legend else 0)
        column_widths = [None] * cols_count

    if formatters is None:
        cols_count = len(dataTable[0]) if len(dataTable) > 0 else (len(data_table_legend) if data_table_legend else 0)
        formatters = [None] * cols_count

    ### Assert basic physical shape integrity
    if data_table_legend and len(dataTable) > 0:
        assert len(data_table_legend) == len(dataTable[0]), \
            f"legend data length ({len(data_table_legend)}) differs from the data ({len(dataTable[0])})"
        assert len(data_table_legend) == len(column_widths), \
            f"column widths list length ({len(column_widths)}) differs from the data ({len(dataTable[0])})"

    ### Geometry & Window boundaries
    win_width = screenState.screen_size.x
    win_height = screenState.screen_size.y

    if row_height != 2:
        row_height = row_height + (not row_height % 2)

    x_tabSize = size.x
    y_tabSize = size.y

    height_low_bar = 1
    height_legend = 3 if data_table_legend is not None else 0
    # Curses color initializations
    P_soft = screenState.colorPairs["tab_soft"]
    P_dark = screenState.colorPairs["tab_dark"]
    P_soft_bg = screenState.colorPairs["tab_soft_bg"]
    P_dark_bg = screenState.colorPairs["tab_dark_bg"]
    P_select = screenState.colorPairs["tab_select"]
    P_selected = screenState.colorPairs["tab_selected"]
    P_win_selected = screenState.colorPairs["win_selected"]
    if tab_scope_is_active:
        P_win_selected = screenState.colorPairs["body"]
    P_win_background = screenState.colorPairs["tab_soft"]

    C_default_background = screenState.colors["background"]
    C_soft_background = screenState.colors["tab_soft"]
    C_dark_background = screenState.colors["tab_dark"]

    table_bk_colors = [C_soft_background, C_dark_background]
    table_color_pairs = [P_soft, P_dark]
    table_alternative_bk_pairs = [P_soft_bg, P_dark_bg]


    if multipleSelection and "idx_selected" not in scope.data:
        scope.data["idx_selected"] = []
    if "idx_first_element" not in scope.data:
        scope.data["idx_first_element"] = 0
    idx_first_element = scope.data["idx_first_element"]

    # Calculate actual row space and correct items fitting inside height boundaries
    col_len = row_count
    visible_row_count = y_tabSize - height_low_bar - height_legend
    visible_item_count = max(visible_row_count // row_height, 1)

    ### Calculate vertical viewport slicing boundaries
    idx_first_element, idx_last_element, select = recalcultate_first_and_last_element(
        selected_idx, idx_first_element, visible_item_count
    )
    
    # Adjust scrolling when resized
    tab_length = idx_last_element - idx_first_element
    if tab_length < visible_item_count:
        idx_first_element = max(idx_first_element - (visible_item_count - tab_length), 0)
        idx_first_element, idx_last_element, select = recalcultate_first_and_last_element(
            selected_idx, idx_first_element, visible_item_count
        )

    scope.data["idx_first_element"] = idx_first_element
    original_idx_first_element = idx_first_element

    # Absolute drawing limits
    max_table_width = win_width - pos.x - 3
    x_tabSize = max_table_width

    y_copy_win = win_height - pos.y - 2
    copy_win = scr.subwin(y_copy_win, x_tabSize, pos.y, pos.x)

    table = scr.subwin(y_tabSize, x_tabSize, pos.y, pos.x)
    table.bkgd(' ', curses.color_pair(P_win_background))

    # Highlight active border frame
    if scope.selected():
        scr.addstr(pos.y + y_tabSize - 1, pos.x, u'\u2580' * x_tabSize, curses.color_pair(P_win_selected))
        scr.addstr(pos.y + y_tabSize - 1, pos.x + x_tabSize, u'\u2598', curses.color_pair(P_win_selected))
        for i in range(y_tabSize):
            scr.addstr(pos.y + i - 1, pos.x + x_tabSize, u'\u258c', curses.color_pair(P_win_selected))

    if scope.selected() and data_table_keys is not None and len(data_table_keys) == 1:
        screenState.scope_exec_args = [screenState, data_table_keys[0]]
    else:
        screenState.scope_exec_args = [screenState]

    # Precalculate column positions
    x_colSize, x_colStart, max_str_len_columns = calc_size_column(
        dataTable, data_table_color, data_table_legend,
        scope, max_table_width, multipleSelection,
        x_tabSize, column_widths, formatters
    )

    row = 0
    if data_table_legend is not None:
        frame_legend = UIgraph.addCustomColorTuple(
            (C_soft_background, C_default_background),
            screenState.cursesColors
        )
        table.attron(curses.color_pair(frame_legend) | curses.A_BOLD)

        table.addstr(row, 0, u'\u2584' * x_tabSize)
        table.addstr(row + 2, 0, u'\u2580' * x_tabSize)
        row += 1

        table.attron(curses.color_pair(P_soft))
        table.addstr(row, 0, ' ' * x_tabSize)

        if multipleSelection:
            table.addstr(row, 0, u' \u25A1 /\u25A0')
        else:
            table.addstr(row, 0, ' ')

        for idx, leg_item in enumerate(data_table_legend):
            table.addstr(row, x_colStart[idx], str(leg_item))

        if row_height == 2:
            table_color_pairs.reverse()
            table_bk_colors.reverse()
            table_alternative_bk_pairs.reverse()

        table.attroff(curses.A_BOLD)








    #if data_table_legend is not None:

    #    frame_legend = UIgraph.addCustomColorTuple(
    #        (C_soft_background, C_default_background),
    #        screenState.cursesColors)
    #    table.attron(curses.color_pair(frame_legend) | curses.A_BOLD)

    #    table.addstr(row, 0, u'\u2584' * (x_tabSize))
    #    table.addstr(row + 2, 0, u'\u2580' * (x_tabSize))
    #    row += 1
    #    table.attron(curses.color_pair(P_soft))
    #    table.addstr(row, 0, ' ' * (x_tabSize))
    #    if multipleSelection:
    #        table.addstr(row, 0, u' \u25A1 /\u25A0')
    #    else:
    #        table.addstr(row, 0, ' ')
    #    for idx, leg_item in enumerate(data_table_legend):
    #        table.addstr(row, x_colStart[idx], str(leg_item))
    #    if row_height == 2:
    #        table_color_pairs.reverse()  # to begin always with the soft color
    #        table_bk_colors.reverse()  # to begin always with the soft color
    #        table_alternative_bk_pairs.reverse()  # to begin always with the soft color

    #    # disable bold
    #    table.attroff(curses.A_BOLD)










    ### Data drawing lifecycle
    current_selection_data = None
    row = height_legend

    # Viewport-sliced elements
    sliced_raw_dataTable = dataTable[idx_first_element:idx_last_element]
    sliced_idx_dataTable = range(idx_first_element, idx_last_element)

    # Cast visible rows on-the-fly to ensure max scroll velocity
    sliced_dataTable = cast_table_items_to_string(sliced_raw_dataTable, formatters)

    count = 0
    for data_row, raw_data_row, data_idx in zip(sliced_dataTable, sliced_raw_dataTable, sliced_idx_dataTable):
        C_custom_bk = table_bk_colors[count % 2]
        P_current_attron = curses.color_pair(table_color_pairs[count % 2])
        P_current_bg = curses.color_pair(table_alternative_bk_pairs[count % 2])

        if data_idx == select and tab_scope_is_active:
            P_current_attron = curses.color_pair(P_select)
            scope_exec_args.append(data_table_keys[data_idx] if data_table_keys else None)
            current_selection_data = raw_data_row
        elif data_idx == select:
            current_selection_data = raw_data_row

        table.attron(P_current_attron)

        # Draw empty spacing background using the custom heights logic
        text_double_space(
            table, UIgraph.Point(0, row), ' ' * x_tabSize,
            P_current_attron, P_current_bg,
            0, row_height
        )

        # Draw selection indicators if multipleSelection is active
        if multipleSelection:
            # Safely check selection list context
            if data_idx in scope.data.get("idx_selected", []):
                P_current_attron = curses.color_pair(P_selected)
                C_custom_bk = screenState.colors["chia_green"]
                table.attron(P_current_attron)
                P_sel_bg = curses.color_pair(table_color_pairs[not count % 2])
                text_double_space(
                    table, UIgraph.Point(0, row), ' ' * x_tabSize,
                    P_current_attron, P_sel_bg,
                    0, row_height
                )
                text_double_space(
                    table, UIgraph.Point(1, row), u' \u25A1',
                    P_current_attron, P_current_bg,
                    0, row_height
                )
            else:
                text_double_space(
                    table, UIgraph.Point(1, row), u' \u25A1',
                    P_current_attron, P_current_bg,
                    0, row_height
                )

        # Draw row strings column-by-column
        for i_col, col_val in enumerate(data_row):
            text_color = data_table_color[data_idx][i_col] if data_idx < len(data_table_color) else None
            P_mod_attron = P_current_attron
            
            if text_color is not None and (data_idx != select or not tab_scope_is_active):
                text_c_pair = UIgraph.addCustomColorTuple(
                    (text_color, C_custom_bk),
                    screenState.cursesColors
                )
                P_mod_attron = curses.color_pair(text_c_pair)
                table.attron(P_mod_attron)

            # Safeguard text overflow limits
            max_str_length = max_str_len_columns[i_col] - 2
            col_str = str(col_val)
            if len(col_str) > max_str_length:
                if max_str_length > 10:
                    col_str = col_str[:max_str_length - 10] + "<...>" + col_str[-5:]
                elif max_str_length > 4:
                    col_str = col_str[:max_str_length - 4] + "<...>"
                else:
                    col_str = "." * max_str_length

            text_double_space(
                table, UIgraph.Point(x_colStart[i_col], row), col_str,
                P_mod_attron, P_current_bg,
                0, row_height
            )
            table.attron(P_current_attron)

        row += row_height
        count += 1

    ### Draw lateral position scrollbar
    steps = total_item_count - visible_item_count
    if steps > 0:
        bar_dim = max(visible_row_count - steps, 1)
        bar_pos = (original_idx_first_element * min(steps, visible_row_count - 1)) // steps

        bar_row = height_legend
        table.attron(curses.color_pair(P_soft))
        for i in range(visible_row_count):
            if i == bar_pos:
                table.attron(curses.color_pair(P_dark))
            elif i == (bar_pos + bar_dim):
                table.attron(curses.color_pair(P_soft))
            table.addstr(bar_row + i, max_table_width - 1, u'\u2588')

    ### Render low margin background filler
    row += 1
    table.attron(curses.color_pair(P_soft_bg) | curses.A_BOLD)
    while row <= (y_tabSize - height_low_bar):
        try:
            table.addstr(row, 0, u'\u2571' * x_tabSize)
        except curses.error:
            pass
        row += 1
    table.attroff(curses.A_BOLD)

    ### Manage Clipboard Action Hook if active
    copy_scope = screenState.scopes.get('copy')
    if (keyboardState.yank and tab_scope_is_active) or (scope.selected() and screenState.activeScope == copy_scope):
        def copy_action():
            create_copy_banner(copy_win, screenState, scope, current_selection_data, False)
        screenState.pending_action.append([1, copy_action])

    return scope


###################################33#########################3
###################################33#########################3
###################################33#########################3
###################################33#########################3
#
#import random
#xx = 25
#yy = 15
#ll = []
#selectable = 25
#for i in range(selectable):
#    x = random.randint(0,xx - 1)
#    y = random.randint(0,yy - 1)
#    ll.append([x,y])
#
## sort
#from collections import defaultdict
#sorted_Y = defaultdict(list)
#for i in ll:
#    sorted_Y[i[1]].append(i)
#
#for key in sorted_Y.keys():
#    sorted_Y[key] = sorted(sorted_Y[key])
#selector = []
#for key in sorted(sorted_Y.keys()):
#    selector.append(sorted_Y[key])
#
#############################################################
#############################################################
#############################################################
#############################################################


def create_selector(stdscr, screenState: ScreenState, parent_scope: Scope, name: str,
                    point: UIgraph.Point):
    """A real button... """

    name_str = name
    name = f"{parent_scope.id}_{name}"

    if name not in screenState.scopes:
        scope = Scope(name, parent_scope.screen, screenState)
        scope.parent_scope = parent_scope
        scope.main_scope = parent_scope
        scope.base_point = point
        parent_scope.sub_scopes[name] = scope
        scope.exec = ScopeActions.activate_scope

    scope: Scope = screenState.scopes[name]
    scope.visible = True
    scope_exec_args = [screenState]

    if scope is screenState.activeScope:
        scope.update()
        screenState.scope_exec_args = scope_exec_args

    sy = scope.cursor % len(selector)
    sx = scope.cursor_x

    row = selector[sy]
    col = row[sx % len(row)]

    sy = sy % len(ll)
    mm = []
    for key in sorted(sorted_Y.keys()):
        for it in sorted_Y[key]:
            mm.append(it)

    pos = point
    for x in range(xx):
        for y in range(yy):
            stdscr.addstr(pos.y + y, pos.x + x, 'A')

    P_sel = screenState.colorPairs['win_selected']
    for n, i in enumerate(ll):
        if i == col:  # n == sy:
            stdscr.addstr(pos.y + i[1], pos.x + i[0], u'\u2588', curses.color_pair(P_sel))
        else:
            stdscr.addstr(pos.y + i[1], pos.x + i[0], u'\u2588')
    if scope.selected():
        stdscr.addstr(pos.y + yy, pos.x, u'\u2588' * xx, curses.color_pair(P_sel))





def create_button(stdscr, screenState: ScreenState, parent_scope: Scope, name: str,
                  point: UIgraph.Point, custom_scope_function=None, button_type: str = None,
                  C_background=None, C_text=None, C_button=None, C_selection=None):
    """A real button... """

    name_str = name
    name = f"{parent_scope.id}_{name}"

    if name not in screenState.scopes:
        scope = Scope(name, parent_scope.screen, screenState)
        scope.parent_scope = parent_scope
        scope.main_scope = parent_scope
        parent_scope.sub_scopes[name] = scope
        scope.exec = custom_scope_function

    scope: Scope = screenState.scopes[name]
    scope.visible = True
    scope.base_point = point + UIgraph.Point(0,1)  # move base point to the text
    scope_exec_args = [screenState]

    if scope is screenState.activeScope:
        scope.update()
        screenState.scope_exec_args = scope_exec_args

    pos_x = point.x
    pos_y = point.y

    #button symbol
    # u'\u25a0 \u25a1 \u25a8' chekcboxes
    symbol_true = ''
    symbol_false = symbol_true
    match button_type:
        case 'boolean':
            symbol_true = u' \u25a0 '
            symbol_false = u' \u25a1 '
        case 'execution':
            symbol_true = u' > '  # \u02c3 \u21f0 \u2794 \u279c \u27a0 \u27a1 \u27ad '
            symbol_false = symbol_true

    but = name_str
    space = 2
    length = len(but) + space * 2 + max(len(symbol_true), len(symbol_false))

    #### colors setup #####
    if C_background is not None and C_button is not None and C_text is not None:
        text_color_background = UIgraph.customColors_findByValue(screenState.cursesColors, C_button)
        text_color = UIgraph.customColors_findByValue(screenState.cursesColors, C_text)
        C_default_background = UIgraph.customColors_findByValue(screenState.cursesColors, C_background)
        C_default_selected = UIgraph.customColors_findByValue(screenState.cursesColors, C_selection)
    else:
        text_color_pair = UIgraph.customColorsPairs_findByValue(
            screenState.cursesColors,
            screenState.colorPairs['xch'])
        text_color_background = text_color_pair[1]
        text_color = text_color_pair[0]
        if button_type == 'boolean':
            text_color = text_color_background
            text_color_background = UIgraph.customColors_findByValue(
                screenState.cursesColors,
                # screenState.colors['mini_block'])
                # screenState.colors['dark_gray'])
                # screenState.colors['light_green'])
                screenState.colors['dark_green'])

        C_default_background = UIgraph.customColors_findByValue(
            screenState.cursesColors,
            screenState.colors["background"])
        C_default_selected = UIgraph.customColors_findByValue(
            screenState.cursesColors,
            screenState.colors["gray"])



    # make the color calculated here as default colors
    if button_type == 'boolean':
        text_color_background_clear = tuple(max(1, min(256, int(i * 1.35))) for i in text_color_background)
        text_color_background_dark = text_color_background
    else:
        text_color_background_clear = tuple(max(1, min(256, int(i * 1.2))) for i in text_color_background)
        text_color_background_dark = tuple(max(1, min(256, int(i * 0.8))) for i in text_color_background)

    UIgraph.addCustomColor(
        text_color_background_clear,
        screenState.cursesColors)
    UIgraph.addCustomColor(
        text_color_background_dark,
        screenState.cursesColors)

    frame_cp_clear = UIgraph.addCustomColorTuple(
        (text_color_background_clear, C_default_background),
        screenState.cursesColors
    )
    frame_cp_dark = UIgraph.addCustomColorTuple(
        (text_color_background_dark, C_default_background),
        screenState.cursesColors
    )
    frame_cp_cl = UIgraph.addCustomColorTuple(
        (text_color_background_dark, text_color_background_clear),
        screenState.cursesColors
    )
    frame_cp_std = UIgraph.addCustomColorTuple(
        (text_color_background, C_default_background),
        screenState.cursesColors
    )
    text_dark = UIgraph.addCustomColorTuple(
        (text_color, text_color_background_dark),
        screenState.cursesColors
    )
    text_clear = UIgraph.addCustomColorTuple(
        (text_color, text_color_background_clear),
        screenState.cursesColors
    )
    frame_selected = UIgraph.addCustomColorTuple(
        (text_color_background_clear, C_default_selected),
        screenState.cursesColors
    )
    frame_selected_2 = UIgraph.addCustomColorTuple(
        (text_color_background_dark, C_default_selected),
        screenState.cursesColors
    )
    frame_selected_backgroung = UIgraph.addCustomColorTuple(
        (C_default_selected, C_default_background),
        screenState.cursesColors
    )
    #### END colors setup #####

    if scope.bool:
        # upper row
        stdscr.addstr(pos_y, pos_x, u'\u2584' * (length + 1),
                      curses.color_pair(frame_cp_dark))

        # text
        x = pos_x
        stdscr.addstr(pos_y + 1, x, u'\u2588',
                      curses.color_pair(frame_cp_dark) | curses.A_BOLD)
        x += 1
        stdscr.addstr(pos_y + 1, x, u'\u2588' * space,
                      curses.color_pair(frame_cp_dark) | curses.A_BOLD)
        x += space
        stdscr.addstr(pos_y + 1, x, f"{but}{symbol_true}",
                      curses.color_pair(text_dark) | curses.A_BOLD)
        x += length - 2 * space
        stdscr.addstr(pos_y + 1, x, u'\u2588' * space,
                      curses.color_pair(frame_cp_dark) | curses.A_BOLD)

        # lower row
        stdscr.addstr(pos_y + 2, pos_x + 0, u'\u2580' * (length + 1),
                      curses.color_pair(frame_cp_dark))
        frame_selected = UIgraph.addCustomColorTuple(
            (text_color_background_dark, C_default_selected),
            screenState.cursesColors
        )

    else:
        # upper row
        stdscr.addstr(pos_y, pos_x, u'\u2584' * (length + 1),
                      curses.color_pair(frame_cp_dark))
        # text
        x = pos_x
        stdscr.addstr(pos_y + 1, x, u'\u2588',
                      curses.color_pair(frame_cp_dark) | curses.A_BOLD)
        x += 1
        stdscr.addstr(pos_y + 1, x, u'\u2588' * space,
                      curses.color_pair(frame_cp_clear) | curses.A_BOLD)
        x += space
        stdscr.addstr(pos_y + 1, x, f"{but}{symbol_false}",
                      curses.color_pair(text_clear) | curses.A_BOLD)
        x += length - 2 * space
        stdscr.addstr(pos_y + 1, x, u'\u2588' * space,
                      curses.color_pair(frame_cp_clear) | curses.A_BOLD)
        # lower row
        stdscr.addstr(pos_y + 2, pos_x + 0, u'\u2580',
                      curses.color_pair(frame_cp_dark))
        stdscr.addstr(pos_y + 2, pos_x + 1, u'\u2580' * (length - 0),
                      curses.color_pair(frame_cp_clear))

        frame_selected = UIgraph.addCustomColorTuple(
            (text_color_background_clear, C_default_selected),
            screenState.cursesColors
        )

    # selection
    if scope.selected():
        stdscr.addstr(pos_y + 2, pos_x, u'\u2580',
                      curses.color_pair(frame_selected_2))
        stdscr.addstr(pos_y + 2, pos_x + 1, u'\u2580' * (length - 0),
                      curses.color_pair(frame_selected))
        x = pos_x + length + 1
        stdscr.addstr(pos_y + 0, x, u'\u2596',
                      curses.color_pair(frame_selected_backgroung))
        stdscr.addstr(pos_y + 1, x, u'\u258c',
                      curses.color_pair(frame_selected_backgroung))
        stdscr.addstr(pos_y + 2, x, u'\u258c',
                      curses.color_pair(frame_selected_backgroung))

    return scope


# i think we can delete it.
def read_bool_button(stdscr, screenState, main_scope, name):
    "Read the bool value of the button called by name"
    name = f"{main_scope.id}_{name}"
    return screenState.scopes[name].bool


def normalize_menu(menu_list: List, scope: Scope, max_size: int) -> Tuple[List[str], int]:
    """Recreate the menu so that it stay in the limit of a max number"""

    len_menu = len(menu_list)
    selected = scope.cursor
    #global DEBUG_OBJ
    #DEBUG_OBJ.text = f"cursor: {scope.cursor} "

    #if selected >= len_menu:
    #    selected = len_menu - 1
    #    scope.cursor = selected

    if len_menu > max_size:
        if 'first_idx' not in scope.data:
            scope.data['first_idx'] = 0

        first_idx = scope.data['first_idx']
        last_idx = first_idx + max_size
        #    DEBUG_OBJ.text += (f"first_idx: {first_idx} "
        #                       f"last_idx: {last_idx} "
        #                       f"sel_orig: {selected} "
        #                       )
        if selected >= last_idx:
            first_idx += 1
            last_idx += 1
        elif selected < first_idx:
            first_idx -= 1
            last_idx -= 1
        if last_idx > len_menu:
            raise 'last idx too big'
        scope.data['first_idx'] = first_idx
        menu_list = menu_list[first_idx:last_idx]
        selected = selected - first_idx

    return menu_list, selected


def normalize_menu_centered(menu_list: List, scope: Scope, max_up: int,
                            max_down: int) -> Tuple[List[str], int, int]:
    """Recreate the menu so that it stay in the limit and the selected element
    stay stationary"""

    len_menu = len(menu_list)
    selected = scope.cursor

    # max menu dimension
    menu_up = selected
    menu_down = len(menu_list) - selected - 1

    # renamej
    for i, m in enumerate(menu_list):
        menu_list[i] = f"{i} - {menu_list[i]}"

    first_y_point = min(menu_up, max_up)
    normalize = False
    first_idx = 0
    if menu_up > max_up:
        first_idx = menu_up - max_up
        normalize = True

    last_idx = len(menu_list)
    if menu_down > max_down:
        last_idx = first_y_point + max_down + 1
        normalize = True


    if normalize:
        menu_list = menu_list[first_idx:last_idx]
        selected = selected - first_idx
        #global DEBUG_OBJ
        #DEBUG_OBJ.text = f"menu: {menu_list}"

    return menu_list, selected, first_y_point


def menu_static(stdscr, menu: str, scope: Scope, point: UIgraph.Point,
                color_pair, color_pair_sel):
    """Create a menu at given coordinate. Point[y,x]"""

    winDim = stdscr.getmaxyx()
    selection = scope.cursor

    for i, item in enumerate(menu):
        if selection == i:
            stdscr.attron(curses.color_pair(color_pair_sel) | curses.A_BOLD)
        else:
            stdscr.attron(curses.color_pair(color_pair) | curses.A_BOLD)
        stdscr.addstr(point.y + i, point.x, str(item))


### TODO: rename to menu_select_stationary!
def menu_select(stdscr, menu: str, scope: Scope, point: UIgraph.Point,
                color_pair, color_pair_sel):
    """Create a menu at given coordinate. Point[y,x]"""

    winDim = stdscr.getmaxyx()

    # max screen dim
    max_up = point.y
    max_down = winDim[0] - point.y - 3  # -3 to take in account the displacement of the text
    # max menu dimension
    #menuUp = selected
    #menuDown = len(menu) - selected - 1

    #global DEBUG_OBJ
    #DEBUG_OBJ.text = f' selection {selected} maxUp: {maxUp} maxDown: {maxDown}'
    #DEBUG_OBJ.text += f' menuUP: {menuUp} menuDown: {menuDown}'
    #maxUp = min(maxUp, menuUp)
    #maxDown = min(maxDown, menuDown)

    #max_dim_menu = maxUp + maxDown + 1

    menu, selection, first_y_point = normalize_menu_centered(menu, scope, max_up, max_down)
    # DEBUG_OBJ.text += f' after min() maxUp: {maxUp} maxDwon: {maxDown}'


    for i, item in enumerate(menu):
        if selection == i:
            stdscr.attron(curses.color_pair(color_pair_sel) | curses.A_BOLD)
        else:
            stdscr.attron(curses.color_pair(color_pair) | curses.A_BOLD)
        stdscr.addstr(point.y + i - first_y_point + 1, point.x + 35, str(item))


def create_button_menu(stdscr, screenState: ScreenState, parent_scope: Scope,
                       name: str, menu: List[str], point: UIgraph.Point, only_init: bool = False):
    """A real menu button...
    only_init: when """

    name_str = name
    name = f"{parent_scope.id}_{name}"

    if name not in screenState.scopes:
        scope = Scope(name, parent_scope.screen, screenState)
        scope.parent_scope = parent_scope
        scope.main_scope = parent_scope
        scope.exec = ScopeActions.activate_scope
        scope.cursor = 0
        parent_scope.sub_scopes[name] = scope

        scope.exec_own = ScopeActions.exit_scope

    scope = screenState.scopes[name]
    scope_is_active = False
    scope_exec_args = [screenState]

    # in case the button needs to be rendered later
    if only_init:
        return scope

    if scope is screenState.activeScope:
        scope.update_no_sub(len(menu), False)
        screenState.scope_exec_args = scope_exec_args
        scope_is_active = True

    winDim = stdscr.getmaxyx()

    stdscr.addstr(10, 10, str(winDim))
    pos_x = point.x
    pos_y = point.y

    # temp
    ppos_x = pos_x
    ppos_y = pos_y

    stdscr.addstr(ppos_y, ppos_x, '#')
    # temp 

    prefix = name_str
    menu_selection = f"{prefix}: {menu[scope.cursor]}"
    space = 2
    length = len(menu_selection) + space * 2

    #### colors setup #####
    text_color_pair = UIgraph.customColorsPairs_findByValue(
        screenState.cursesColors,
        screenState.colorPairs['xch'])
    text_color_background = text_color_pair[1]
    text_color = text_color_pair[0]
    default_background = UIgraph.customColors_findByValue(
        screenState.cursesColors,
        screenState.colors["background"])
    default_selected = UIgraph.customColors_findByValue(
        screenState.cursesColors,
        screenState.colors["yellow_bee"])
    # make the color calculated here as default colors
    text_color_background_clear = tuple(int(i * 1.2) for i in text_color_background)
    text_color_background_dark = tuple(int(i * 0.8) for i in text_color_background)

    UIgraph.addCustomColor(
        text_color_background_clear,
        screenState.cursesColors)
    UIgraph.addCustomColor(
        text_color_background_dark,
        screenState.cursesColors)

    frame_cp_clear = UIgraph.addCustomColorTuple(
        (text_color_background_clear, default_background),
        screenState.cursesColors
    )
    frame_cp_dark = UIgraph.addCustomColorTuple(
        (text_color_background_dark, default_background),
        screenState.cursesColors
    )
    frame_cp_cl = UIgraph.addCustomColorTuple(
        (text_color_background_dark, text_color_background_clear),
        screenState.cursesColors
    )
    frame_cp_std = UIgraph.addCustomColorTuple(
        (text_color_background, default_background),
        screenState.cursesColors
    )
    text_dark = UIgraph.addCustomColorTuple(
        (text_color, text_color_background_dark),
        screenState.cursesColors
    )
    text_clear = UIgraph.addCustomColorTuple(
        (text_color, text_color_background_clear),
        screenState.cursesColors
    )
    frame_selected = UIgraph.addCustomColorTuple(
        (text_color_background_clear, default_selected),
        screenState.cursesColors
    )
    frame_selected_2 = UIgraph.addCustomColorTuple(
        (text_color_background_dark, default_selected),
        screenState.cursesColors
    )
    frame_selected_backgroung = UIgraph.addCustomColorTuple(
        (default_selected, default_background),
        screenState.cursesColors
    )
    #### END colors setup #####

    #if scope.bool:
    if scope_is_active:
        # upper row
        stdscr.addstr(pos_y, pos_x, u'\u2584' * (length + 2),
                      curses.color_pair(frame_cp_dark))

        # text
        x = pos_x
        stdscr.addstr(pos_y + 1, x, u'\u2588',
                      curses.color_pair(frame_cp_dark) | curses.A_BOLD)
        x += 1
        stdscr.addstr(pos_y + 1, x, u'\u2588' * space,
                      curses.color_pair(frame_cp_dark) | curses.A_BOLD)
        x += space
        stdscr.addstr(pos_y + 1, x, f"{menu_selection}",
                      curses.color_pair(text_dark) | curses.A_BOLD)
        x += length - 2 * space
        stdscr.addstr(pos_y + 1, x, u'\u2588' * space,
                      curses.color_pair(frame_cp_dark) | curses.A_BOLD)
        x += 2 * space + 1
        stdscr.addstr(pos_y + 1, x, u'\u2588',
                      curses.color_pair(frame_cp_dark) | curses.A_BOLD)

        # lower row
        stdscr.addstr(pos_y + 2, pos_x + 0, u'\u2580' * (length + 1),
                      curses.color_pair(frame_cp_dark))

        # change color for the selection drawing
        frame_selected = UIgraph.addCustomColorTuple(
            (text_color_background_dark, default_selected),
            screenState.cursesColors
        )


    else:
        # upper row
        stdscr.addstr(pos_y, pos_x, u'\u2584' * (length + 2),
                      curses.color_pair(frame_cp_dark))
        # text
        x = pos_x
        stdscr.addstr(pos_y + 1, x, u'\u2588',
                      curses.color_pair(frame_cp_dark) | curses.A_BOLD)
        x += 1
        stdscr.addstr(pos_y + 1, x, u'\u2588' * space,
                      curses.color_pair(frame_cp_clear) | curses.A_BOLD)
        x += space
        stdscr.addstr(pos_y + 1, x, f"{menu_selection}",
                      curses.color_pair(text_clear) | curses.A_BOLD)
        x += length - 2 * space
        stdscr.addstr(pos_y + 1, x, u'\u2588' * space,
                      curses.color_pair(frame_cp_clear) | curses.A_BOLD)
        x += 2
        stdscr.addstr(pos_y + 1, x, u'\u2588',
                      curses.color_pair(frame_cp_dark) | curses.A_BOLD)
        # lower row
        stdscr.addstr(pos_y + 2, pos_x + 0, u'\u2580',
                      curses.color_pair(frame_cp_dark))
        stdscr.addstr(pos_y + 2, pos_x + 1, u'\u2580' * (length - 0),
                      curses.color_pair(frame_cp_clear))
        stdscr.addstr(pos_y + 2, pos_x + length + 1, u'\u2580',
                      curses.color_pair(frame_cp_dark))

        # change color for the selection drawing
        frame_selected = UIgraph.addCustomColorTuple(
            (text_color_background_clear, default_selected),
            screenState.cursesColors
        )

    # selection
    if scope.selected():
        stdscr.addstr(pos_y + 2, pos_x, u'\u2580',
                      curses.color_pair(frame_selected_2))
        stdscr.addstr(pos_y + 2, pos_x + 1, u'\u2580' * (length + 0),
                      curses.color_pair(frame_selected))
        stdscr.addstr(pos_y + 2, pos_x + length + 1, u'\u2580',
                      curses.color_pair(frame_selected_2))
        x = pos_x + length + 2
        stdscr.addstr(pos_y + 0, x, u'\u2596',
                      curses.color_pair(frame_selected_backgroung))
        stdscr.addstr(pos_y + 1, x, u'\u258c',
                      curses.color_pair(frame_selected_backgroung))
        stdscr.addstr(pos_y + 2, x, u'\u258c',
                      curses.color_pair(frame_selected_backgroung))

    if scope_is_active:

        # draw menu

        stdscr.addstr(ppos_y, ppos_x, '#')
        winDim = stdscr.getmaxyx()
        maxUp = ppos_y
        maxDown = winDim[0] - ppos_y - 3

        for i in range(maxDown):
            stdscr.addstr(pos_y + 2 + i, pos_x + 1 + space, '#' * len(menu_selection),
                          curses.color_pair(frame_cp_dark))
        for i in range(maxUp):
            stdscr.addstr(pos_y - i, pos_x + 1 + space, '#' * len(menu_selection),
                          curses.color_pair(frame_cp_dark))

#######################


        menu_select(stdscr, menu, scope, point, screenState.colorPairs['body'],
                    screenState.colorPairs["body_sel"])

########################



    stdscr.addstr(ppos_y, ppos_x, '#')
    winDim = stdscr.getmaxyx()
    maxUp = ppos_y
    maxDown = winDim[0] - ppos_y - 1

    stdscr.addstr(ppos_y - maxUp, ppos_x, '$')
    stdscr.addstr(ppos_y + maxDown, ppos_x, '&')


    return scope


def draw_rect(stdscr, point: UIgraph.Point, dim: UIgraph.Point, P_color):
    """Draw a rectangle"""

    dim_x = dim.x
    dim_y = dim.y

    # set colors
    stdscr.attron(curses.color_pair(P_color))
    for i in range(dim.y):
        stdscr.addstr(point.y + i, point.x, u'\u2588' * dim.x)



def create_block_band(stdscr,
                      keyboardState: KeyboardState,
                      screenState: ScreenState,
                      parent_scope: Scope,
                      name: str,
                      position: UIgraph.Point,
                      size: UIgraph.Point,
                      mempool_blocks: list[WDB.MempoolBlock],
                      blocks_loader: WDB.DataChunkLoader,
                      current_peak: int,
                      node_synced: bool):
    """Block band navigator mempool.space style..."""
    global DEBUG_OBJ
    DEBUG_OBJ.text = (f" first peak: {current_peak} | ")

    point = position
    win_band = stdscr.subwin(size.y, size.x, position.y, position.x)  # y, x
    base_point = UIgraph.Point(1,1)

    name_str = name
    # the band has a fixed name to reference the scope from other threads

    # last item is not well implemented. The idea was to remove the parameter
    # current_peak
    #last_block = WDB.BlockState(blocks_loader.last_item, False)
    #current_peak = last_block.height

    # precalc indexes of mempool, separator
    # TODO if syncing remove the mempool block
    mempool_blocks_count = len(mempool_blocks)
    separator = 1
    total_elements_count = current_peak + mempool_blocks_count + separator
    mempool_idx = current_peak + separator + min(mempool_blocks_count, 1)

    if name not in screenState.scopes:
        scope = Scope(name, parent_scope.screen, screenState)
        scope.parent_scope = parent_scope
        scope.main_scope = parent_scope
        #scope.exec = ScopeActions.activate_scope
        scope.exec = ScopeActions.activate_scope_next_sibling
        scope.cursor = current_peak + separator  # separator default selection
        parent_scope.cursor_x = current_peak + separator  # separator default selection
        parent_scope.sub_scopes[name] = scope
        scope.visible = True

        ## TODO; activate next scope
        scope.exec_own = ScopeActions.activate_scope_next_sibling

        scope.data["idx_last_item"] = current_peak + separator + min(mempool_blocks_count, 2)  # show max 2 mempool block by default
        scope.data["last_peak"] = current_peak
        scope.data["on_peak"] = True
        scope.data["loader_update_counter"] = 0
        scope.data["prev_idx_selected"] = scope.cursor
        scope.data["thread_update_loader"] = None

    scope: Scope = screenState.scopes[name]
    scope.visible = False  # not selectable...
    scope_is_active = False
    scope_exec_args = [screenState]


    if 'lapper' not in scope.data:
        scope.data["lapper"] = Timer('block_band')
    lapper = scope.data["lapper"]
    lapper.start()


    ### this should not trigger anymore
    if scope is screenState.activeScope:
        scope.update_no_sub(total_elements_count + 1, False)
        screenState.scope_exec_args = scope_exec_args
        scope_is_active = True

    ### keyboard
    screenState.footer_text += "| go to peak=home or 0"
    if keyboardState.home:
        scope.cursor = current_peak + separator
        parent_scope.cursor_x = current_peak + separator
        scope.data["idx_last_item"] = current_peak + separator + min(mempool_blocks_count, 2)  # show max 2 mempool block by default
        blocks_loader.update_offset(current_peak)
        blocks_loader.start_updater_thread()


    lapper.clocking("init")

    #check cursor boundaries
    if parent_scope.cursor_x < -1:
        parent_scope.cursor_x = -1
    elif parent_scope.cursor_x >= total_elements_count:
        parent_scope.cursor_x = total_elements_count

    idx_last_item = scope.data["idx_last_item"]
    last_peak = scope.data["last_peak"]
    selected_idx = scope.cursor
    selected_idx = parent_scope.cursor_x
    #if scope.cursor > (last_peak + separator + mempool_blocks_count):
    if parent_scope.cursor_x > (last_peak + separator + mempool_blocks_count):
        selected_idx = last_peak + separator + mempool_blocks_count

    prev_idx_selected = scope.data["prev_idx_selected"]
    scope.data["prev_idx_selected"] = selected_idx
    DEBUG_OBJ.text += (
        f" mmm... what's up? | current {current_peak}, last {last_peak} | cursor: {scope.cursor} | parent cursor_x: {parent_scope.cursor_x} "
    )

    # check if the peak is moved
    if current_peak > last_peak:
        scope.data['last_peak'] = current_peak
        delta = current_peak - last_peak

        # move selected block if we are at peak
        if selected_idx == (last_peak + separator):

            delta = current_peak - last_peak
            selected_idx += delta
            scope.cursor = selected_idx
            parent_scope.cursor_x = selected_idx
            scope.data['on_peak'] = True

            idx_last_item += delta

            blocks_loader.update_offset(selected_idx - separator)
            logging(debug_logger, "DEBUG", "THREAD - start peak one")
            blocks_loader.start_updater_thread()

        elif selected_idx > (last_peak + separator):
            selected_idx += delta
            scope.cursor = selected_idx
            parent_scope.cursor_x = selected_idx
            scope.data['on_peak'] = True

            blocks_loader.update_offset(selected_idx - separator)
            logging(debug_logger, "DEBUG", "THREAD - on the meme")
            blocks_loader.start_updater_thread()

    # if not at peak
    if selected_idx < (last_peak + separator):
        scope.data['on_peak'] = False
        # with the new peak from the db we do not need it anymore
        loader_offset_update = threading.Thread(target=blocks_loader.update_offset, args=(selected_idx,), daemon=True)
        loader_offset_update.start()

        # update only if you move more then half of the chunk size or if you are close to the peak
        delta = selected_idx - prev_idx_selected
        scope.data["loader_update_counter"] += delta

        # update when:
        # the movement is more then half the chunk size
        # selected is close to the peak
        if (current_peak - last_peak) > blocks_loader.chunk_size:
            logging(debug_logger, "DEBUG", f"JUMPPPP is: {current_peak - last_peak}")
        #if abs(scope.data["loader_update_counter"]) > blocks_loader.chunk_size // 2 or (current_peak - selected_idx) < blocks_loader.chunk_size:
        if abs(scope.data["loader_update_counter"]) > blocks_loader.chunk_size // 2 or (current_peak - selected_idx) < blocks_loader.chunk_size:
            logging(debug_logger, "DEBUG", "THREAD - passed the cound or the chunk size")
            blocks_loader.start_updater_thread()
            scope.data["loader_update_counter"] = 0
    else:
        scope.data['on_peak'] = True


    if mempool_blocks_count == 0:
        pass
        # recalculate first idx item

    win_size = stdscr.getmaxyx()
    win_size = UIgraph.Point(win_size[1], win_size[0])

    # current_height > show block data
    # current height + 1 > show -s stuffs  (DEFAULT)
    # current height + 2 > 1 memepool block
    # current height + 3 > if it exists, show next memepool block

    # i need a variable to comunicate with the back end to give me the right block
    # maybe it is better to create a feeder function that use the current idx of
    # the selected block

    P_text = screenState.colorPairs["body"]  # use for tx block
    P_block = screenState.colorPairs["block_band"]  # use for tx block
    P_block_mini = screenState.colorPairs["block_band_mini"]
    P_selected = screenState.colorPairs["win_selected"]
    P_selected_inactive = screenState.colorPairs["win_selected_inactive"]
    P_tab_active = screenState.colorPairs["tab_dark"]
    P_tab_active = screenState.colorPairs["scope_selected"]
    P_not_selected = screenState.colorPairs["tab_soft_bg"]
    #P_yellow_bee = screenState.colorPairs["block_band"]
    P_azzure = screenState.colorPairs["up"]
    P_white = screenState.colorPairs["down"]
    P_separator = screenState.colorPairs["tab_soft_bg"]
    P_btc = screenState.colorPairs["btc"]
    P_btc_text = screenState.colorPairs["btc_text"]
    P_btc_inv = screenState.colorPairs["btc_inv"]

    #win_band.bkgd(' ', curses.color_pair(P_yellow_bee))

    ### highlight scope if selected
    P_option = P_not_selected
    #P_selected_block = P_selected_inactive
    #P_selected_block_vertical = P_not_selected
    P_selected_block = P_selected
    P_selected_block_vertical = P_selected

    # now it should never be selected
    if scope.selected() & scope_is_active:
        P_option = P_tab_active
        P_selected_block = P_selected
        P_selected_block_vertical = P_selected
    elif scope.selected():
        P_option = P_selected

    stdscr.addstr(position.y + size.y, position.x, u'\u2580' * size.x,
                  curses.color_pair(P_option))
    stdscr.addstr(position.y + size.y, position.x + size.x, u'\u2598',
                  curses.color_pair(P_option))
    for i in range(size.y):
        stdscr.addstr(position.y + i, position.x + size.x, u'\u258c',
                      curses.color_pair(P_option))



    # load blocks
    block_states, first_idx = blocks_loader.get_items_hot_chunks()

    if first_idx == 0:
        first_idx = -1
        if block_states[0]:
            block_states.insert(0, block_states[0].operational_error())


    # calc rectangle block dimension
    name_block_len = len(f'{current_peak}')  # check how big is the block name
    name_block_len = name_block_len + name_block_len // 3 + 2  # add separator and margin
    name_block_len = max(name_block_len, 11)
    rec_dim_x = int(name_block_len + name_block_len % 2)
    rec_dim_y = int(rec_dim_x / 2)
    rec_dim = UIgraph.Point(rec_dim_x, rec_dim_y)
    rec_mini_dim = UIgraph.Point(6, 3)
    block_spacer = 3

    ##############################################
    ### estimate number of block on the screen
    #############################################
    idx_first_block = idx_last_item - first_idx
    local_peak = current_peak - first_idx
    local_idx_mempool = mempool_idx - first_idx
    items_count = 0
    tot_blocks_lenght = base_point.x

    ##### mempool and separator
    while True:
        local_idx_block = idx_first_block - items_count

        if local_idx_block >= local_idx_mempool:
            block_lenght = rec_dim.x
        elif local_idx_block == local_peak + separator:
            block_lenght = 6  # to change if the geometry of the spacer change
        elif local_idx_block < local_peak + separator:
            break

        if size.x < (tot_blocks_lenght + block_lenght + block_spacer):
            break
        else:
            tot_blocks_lenght += block_lenght + block_spacer
            items_count += 1


    ##### blocks
    while True:
        local_idx_block = idx_first_block - items_count
        block = None

        try:
            #if block is None or block.is_transaction_block is True:
            block: WDB.BlockState = block_states[local_idx_block]
            block_lenght = 0
            if block.is_transaction_block is True:
                a = 1
        except Exception as e:
            print(f"exception: {e}")


        if block is None or block.is_transaction_block:
            block_lenght = rec_dim.x
        else:
            block_lenght = rec_mini_dim.x

        if size.x < (tot_blocks_lenght + block_lenght + 2):  # 2 is the selection
            break
        else:
            tot_blocks_lenght += block_lenght + block_spacer
            items_count += 1

    ########################## estimation end #######################
    #lapper.clocking('post loop')

    # indexes

    idx_first_item = idx_last_item - items_count   # the last block is the first
    DEBUG_OBJ.text += ( f" | last item: {idx_last_item} | item count: {items_count} | first_itme: {idx_first_item}")
    ### recalculate firt and last element
    idx_first_item, idx_last_item, selected_idx_local = recalcultate_first_and_last_element_BAND(selected_idx, idx_last_item, items_count)
    DEBUG_OBJ.text += ( f" | after LI: {idx_last_item} | after IC: {items_count} | first_itme: {idx_first_item}")

    ### update first item
    scope.data["idx_last_item"] = idx_last_item

    # normalize selection to the chunk length
    idx_first_item -= first_idx
    idx_last_item -= first_idx
    selected_idx_local -= first_idx
    mempool_idx -= first_idx
    current_peak_global = current_peak
    current_peak -= first_idx

    DEBUG_OBJ.text += (f" | local LI: {idx_last_item} | local IC: {items_count} | first_itme: {idx_first_item}")

    current_idx = idx_last_item

    #lapper.clocking('pre calc posiitons')
    # block blipping
    DEBUG_OBJ.text += (f" | current idx at mem: {current_idx} | actual mem: {mempool_idx} ")
    while current_idx >= mempool_idx:
        if node_synced:
            if base_point.x + rec_dim.x > size.x:
                break
            idx_item_mempool = current_idx - mempool_idx
            if len(mempool_blocks) > 0:
                mempool_block: WDB.MempoolBlock = mempool_blocks[idx_item_mempool]
                total_cost = mempool_block.total_cost

                p = base_point
                create_text(win_band, p, f'mempool_{idx_item_mempool}', P_azzure, True)
                p = p + UIgraph.Point(0, 1)
                draw_rect(win_band, p, rec_dim, P_azzure)
                p = p + UIgraph.Point(0, 1)
                create_text(win_band, p, f'txs: {human_int(len(mempool_block.transactions))}', P_azzure, True, inv_color=True)

                #p = p + UIgraph.Point(0, 1)
                #create_text(win_band, p, f'fee: {human_mojo(block.fees)}', P_azzure, True, inv_color=True)
                p = p + UIgraph.Point(0, 1)
                create_text(win_band, p, f'cost: {human_int(total_cost)}', P_azzure, True, inv_color=True)
                p = p + UIgraph.Point(0, 1)
                fullness = truncate(total_cost / BLOCK_MAX_COST * 100, 2)
                fullness = f"{fullness:.3g}%"
                create_text(win_band, p, f'used: {fullness}', P_azzure, True, inv_color=True)

            else:
                logging(debug_logger, "DEBUG", f"RAISE Mempool empty: ___")
                p = base_point
                create_text(win_band, p, f'mempool_empty', P_azzure, True)
                p = p + UIgraph.Point(0, 1)
                draw_rect(win_band, p, rec_dim, P_azzure)

            if current_idx == selected_idx_local:
                p = base_point
                mem_text = f'mempool_{idx_item_mempool}'
                mem_text = f"{mem_text}{' ' * (rec_dim.x - len(mem_text))}"
                create_text(win_band, p, mem_text, P_selected_block, True, inv_color=True)

                p = p + UIgraph.Point(0, rec_dim.y + 1)
                create_text(win_band, p, ' ' * rec_dim.x, P_selected_block, True, inv_color=True)

                ps = base_point
                for i in range(rec_dim.y + 2):
                    pp = ps + UIgraph.Point(rec_dim.x, i)
                    create_text(win_band, pp, u'\u258c', P_selected_block_vertical, True, inv_color=False)

            base_point += UIgraph.Point(rec_dim.x + 2, 0)

        current_idx -= 1

    #lapper.clocking('memepool')
    if current_idx == current_peak + separator:
        ############### separation line #####################################
        #    ## dot line
        #    for i in range(rec_dim.y + 3):
        #        p = base_point
        #        create_text(win_band, p + UIgraph.Point(0, i), u'\u254F', P_white, True)
        #    base_point += UIgraph.Point(1 + 2, 0)
        #
        #    ## up arrow
        #    for i in range(rec_dim.y + 3):
        #        p = base_point
        #        create_text(win_band, p + UIgraph.Point(0, i), u'\u2571', P_white, True)
        #        create_text(win_band, p + UIgraph.Point(1, i), u'\u2572', P_white, True)
        #    base_point += UIgraph.Point(2 + 2, 0)

        ##################### band stripe ##############################

        P_option = P_separator
        if current_idx == selected_idx_local:
            P_option = P_selected

        base_point += UIgraph.Point(1, 0)
        for i in range(rec_dim.y + 3):
            p = base_point
            if i % 2:
                create_text(win_band, p + UIgraph.Point(0, i), u'\u25E2', P_option, True)
                create_text(win_band, p + UIgraph.Point(1, i), u'\u25E4', P_option, True)
                create_text(win_band, p + UIgraph.Point(2, i), u'\u25E2', P_option, True)
            else:
                create_text(win_band, p + UIgraph.Point(0, i), u'\u25E4', P_option, True)
                create_text(win_band, p + UIgraph.Point(1, i), u'\u25E2', P_option, True)
                create_text(win_band, p + UIgraph.Point(2, i), u'\u25E4', P_option, True)

        base_point += UIgraph.Point(6, 0)

        ##################### band stripe double ##############################
        #    for i in range(rec_dim.y + 3):
        #        p = base_point
        #        if i % 2:
        #            create_text(win_band, p + UIgraph.Point(0, i), u'\u25E2', P_white, True)
        #            create_text(win_band, p + UIgraph.Point(1, i), u'\u25E4', P_white, True)
        #        else:
        #            create_text(win_band, p + UIgraph.Point(0, i), u'\u25E4', P_white, True)
        #            create_text(win_band, p + UIgraph.Point(1, i), u'\u25E2', P_white, True)
        #    base_point += UIgraph.Point(2 + 2, 0)


        current_idx -= 1

    ######### blocks ###############

    #lapper.clocking("blocks")
    count = 0
    DEBUG_OBJ.text += (f" | idx block : {current_idx} ")

    if current_idx > len(block_states):
        ## implement logic to brake the loop and load the data, or skip it and wait for the upodate of the cache
        print(f"current_idx; {current_idx}")
        print(f"len block states: {len(block_states)}")
        pass
        #raise Exception("The block idx asked is outside the cache. Increase the cache")

    while current_idx >= 0:

        count += 1
        block = None

        if current_idx < len(block_states):
            block: WDB.BlockState = block_states[current_idx]

        ######## DEBUG ONLY
        #with open('block_loader.txt', 'w') as f:
        #    for n, i in enumerate(block_states):
        #        if i is not None:
        #            i = str(i)[:35]
        #        f.write(f'{n} - {i} \n')

        if block is None:

            if base_point.x + rec_dim.x > size.x:
                break
            p = base_point
            p = p + UIgraph.Point(0, 1)
            draw_rect(win_band, p, rec_dim, P_text)
            p = p + UIgraph.Point(0, 3)
            create_text(win_band, p, f'No data...', P_text, True, inv_color=True)
            p = p + UIgraph.Point(0, 1)
            create_text(win_band, p, f'idx: {current_idx}', P_text, True, inv_color=True)

            p1 = base_point
            P_option = P_text
            if current_idx == selected_idx_local:
                P_option = P_selected_block

                b_height = f'No data...'
                b_height = f"{b_height}{' ' * (rec_dim.x - len(b_height))}"
                create_text(win_band, p1, b_height, P_option, True, inv_color=True)
                p1 += UIgraph.Point(0, rec_dim.y + 1)

                time_passed = f"No data..."
                create_text(win_band, p1, f'{time_passed}', P_option, True, inv_color=True)

                ps = base_point
                for i in range(rec_dim.y + 2):
                    pp = ps + UIgraph.Point(rec_dim.x, i)
                    create_text(win_band, pp, u'\u258c', P_selected_block_vertical, True, inv_color=False)

            base_point += UIgraph.Point(rec_dim.x + 2, 0)

        elif block.height == 675317 and selected_idx < 675317:
            if base_point.x + rec_dim.x > size.x:
                break

            p = base_point
            p = p + UIgraph.Point(0, 1)
            draw_rect(win_band, p, rec_dim, P_btc_inv)

            time_passed = time_ago(datetime.fromtimestamp(block.timestamp))
            p1 = base_point
            P_option = P_btc_text
            if current_idx == selected_idx_local:
                P_option = P_selected_block

                b_height = f'{block.height:_}'
                b_height = f"{b_height}{' ' * (rec_dim.x - len(b_height))}"
                time_passed = f"{time_passed}{' ' * (rec_dim.x - len(time_passed))}"

                create_text(win_band, p1, b_height, P_option, True, inv_color=True)
                p1 += UIgraph.Point(0, rec_dim.y + 1)
                create_text(win_band, p1, f'{time_passed}', P_option, True, inv_color=True)
                ps = base_point
                for i in range(rec_dim.y + 2):
                    pp = ps + UIgraph.Point(rec_dim.x, i)
                    create_text(win_band, pp, u'\u258c', P_selected_block_vertical, True, inv_color=False)
            else:
                b_height = f'{block.height:_}'
                create_text(win_band, p1, b_height, P_option, True)
                p1 += UIgraph.Point(0, rec_dim.y + 1)
                create_text(win_band, p1, f'{time_passed}', P_option, True)

            base_point += UIgraph.Point(rec_dim.x + 2, 0)

        elif block.is_transaction_block is True:
            if base_point.x + rec_dim.x > size.x:
                break

            p = base_point
            p = p + UIgraph.Point(0, 1)
            draw_rect(win_band, p, rec_dim, P_text)
            p = p + UIgraph.Point(0, 1)
            create_text(win_band, p, f'sp: {block.signage_point_index}', P_text, True, inv_color=True)
            p = p + UIgraph.Point(0, 1)
            create_text(win_band, p, f'fee: {human_mojo(block.fees)}', P_text, True, inv_color=True)
            p = p + UIgraph.Point(0, 1)
            create_text(win_band, p, f'cost: {human_int(block.cost)}', P_text, True, inv_color=True)
            p = p + UIgraph.Point(0, 1)
            fullness = truncate(block.cost / BLOCK_MAX_COST * 100, 2)
            fullness = f"{fullness:.3g}%"
            create_text(win_band, p, f'used: {fullness}', P_text, True, inv_color=True)

            # block debugging
            #create_text(win_band, p, f'idx: {current_idx}', P_text, True, inv_color=True)

            time_passed = time_ago(datetime.fromtimestamp(block.timestamp))
            p1 = base_point
            P_option = P_text
            if current_idx == selected_idx_local:
                P_option = P_selected_block

                b_height = f'{block.height:_}'
                b_height = f"{b_height}{' ' * (rec_dim.x - len(b_height))}"
                time_passed = f"{time_passed}{' ' * (rec_dim.x - len(time_passed))}"

                create_text(win_band, p1, b_height, P_option, True, inv_color=True)
                p1 += UIgraph.Point(0, rec_dim.y + 1)
                create_text(win_band, p1, f'{time_passed}', P_option, True, inv_color=True)
                ps = base_point
                for i in range(rec_dim.y + 2):
                    pp = ps + UIgraph.Point(rec_dim.x, i)
                    create_text(win_band, pp, u'\u258c', P_selected_block_vertical, True, inv_color=False)
            else:
                b_height = f'{block.height:_}'
                create_text(win_band, p1, b_height, P_option, True)
                p1 += UIgraph.Point(0, rec_dim.y + 1)
                create_text(win_band, p1, f'{time_passed}', P_option, True)

            base_point += UIgraph.Point(rec_dim.x + 2, 0)
        else:
            if base_point.x + rec_mini_dim.x > size.x:
                break
            p = base_point + UIgraph.Point(0, 3)
            b_height = f'...{str(block.height)[-2:]}'
            create_text(win_band, p, b_height, P_block_mini, True)
            p = p + UIgraph.Point(0, 1)
            draw_rect(win_band, p, rec_mini_dim, P_block_mini)
            create_text(win_band, p, f'sp{block.signage_point_index}', P_block_mini, True, inv_color=True)
            # debugging local_idx
            #p = p + UIgraph.Point(0, 1)
            #create_text(win_band, p, f'x{current_idx}', P_block_mini, True, inv_color=True)


            p1 = base_point + UIgraph.Point(0, 3)
            if current_idx == selected_idx_local:
                P_option = P_selected_block
                b_height = f"{b_height}{' ' * (rec_mini_dim.x - len(b_height))}"
                create_text(win_band, p1, b_height, P_option, True, inv_color=True)
                p1 += UIgraph.Point(0, 4)
                create_text(win_band, p1, ' ' * rec_mini_dim.x, P_option, True, inv_color=True)
                pp = base_point + UIgraph.Point(0, 3)
                for i in range(rec_mini_dim.y + 2):
                    ps = pp + UIgraph.Point(rec_mini_dim.x, i)
                    create_text(win_band, ps, u'\u258c', P_selected_block_vertical, True, inv_color=False)

            base_point += UIgraph.Point(rec_mini_dim.x + 2, 0)

        current_idx -= 1

    lapper.clocking('the very end')
    lapper.end()

    return scope

