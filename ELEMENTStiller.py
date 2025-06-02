import sys, os, traceback
import curses
from math import floor

import dex as dex
import UIgraph as UIgraph
import UItext as UItext

from dataclasses import dataclass
from typing import List, Tuple, Dict, Union, Callable
from datetime import datetime, timedelta

from CONFtiller import ScopeMode
from UItiller import Scope, activate_scope, screen_coin_wallet, ScreenState, activate_grandparent_scope, open_coin_wallet
import DEBUGtiller as DEBUGtiller

# unicode box
## light shade  u2591
## medium shade u2592
## dark shade   u2593
## / u2571
## \ u2572
## X u2573
## full block       u2588
## upper half block u2580
## lower half block u2584

#### global for debugging
DEBUG_OBJ = DEBUGtiller.DEBUG_OBJ


def cast_table_items_to_string(table: List[List]):
    """Convert each item of a 2dim list to string"""

    table_str = []
    for col in table:
        col_str = []
        for u in col:
            if isinstance(u, float):
                #if u > 1:
                u = dex.format_and_round_number(u, 5, 10)
                col_str.append(str(u))
            else:
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
                     multiple_selection, x_tab_size):
    """Return max_dims, but it changes also all the data table input to trunkate the tab
    if needed"""

    n_rows = len(data_table)
    n_columns = len(data_table[0])

    ### calculate max dim for columns
    max_dims = [0] * n_columns
    total_dims = 0
    x_col_start = [0]
    x_col_dim = []
    column_separator = 2
    for idx in range(n_rows):
        for idx2, u in enumerate(data_table[idx]):
            if len(str(u)) > max_dims[idx2]:
                max_dims[idx2] = len(u)

    if data_table_legend is not None:
        # assert lenght legend == n_columns
        for idx, i in enumerate(data_table_legend):
            if len(i) > max_dims[idx]:
                max_dims[idx] = len(i)

    # add separator
    for idx in range(n_columns):
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
        delete_table_column(data_table, idx_fix_item)
        delete_table_column(data_table_color, idx_fix_item)
        if data_table_legend is not None:
            data_table_legend.pop(idx_fix_item)
        total_dims -= dim
        scope_x -= 1


    ### remove last column until there is enough space
    if total_dims > max_table_width:
        while total_dims > max_table_width:
            dim = max_dims.pop(-1)
            delete_table_column(data_table, -1)
            delete_table_column(data_table_color, -1)
            print("data table doc")
            print(data_table_legend)
            if data_table_legend is not None:
                data_table_legend.pop(-1)
            total_dims -= dim


    ### calculate the remainder space to distribuite later
    x_remainder = (x_tab_size - total_dims) // n_columns

    ### calculate each col dimension and starting position
    for i in max_dims:
        x_col_dim.append(i + x_remainder)

    for i in range(len(max_dims) - 1):
        x_col_start.append(x_col_start[-1] + max_dims[i] + x_remainder)

    return x_col_dim, x_col_start


def recalcultate_first_and_last_element(scope, idx_first_element, col_len, rows_number):
    """calculate if the current index is in the range of visible rows, if not it 
    correct the range of visible rows"""
    select = scope.cursor % col_len
    idx_last_element = idx_first_element + rows_number
    if select >= (idx_last_element):
        idx_last_element = select + 1
        idx_first_element = idx_last_element - rows_number
    elif idx_first_element > select:
        idx_first_element = select % col_len
        idx_last_element = (idx_first_element + rows_number) % col_len

    return idx_first_element, idx_last_element, select


def create_text(scr, pos: UIgraph.Point, text: str, P_text_color, bold: bool = False):
    """Create normal text."""
    scr.attron(curses.color_pair(P_text_color))
    if bold:
        scr.attron(curses.A_BOLD)
    scr.addstr(pos.y, pos.x, str(text))
    scr.attroff(curses.A_BOLD)


def create_blinking_text(scr, pos: UIgraph.Point, text: str, P_text_color, bold: bool = False):
    """Create blinking text by inverting the colors based on the timestamp."""
    blink = 0.6  # second
    now = datetime.now().timestamp()
    toggle = int(now / blink % 2)
    scr.addstr(pos.y + 5, pos.x, str(toggle))
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


def create_prompt(stdscr, screen_state: ScreenState, parent_scope: Scope, name: str,
                  pos: UIgraph.Point, pre_text: str, P_text_color, bold: bool = False,
                  inverse_color: bool = False):
    """prompt text"""
    # TODO limit text displayed...

    nome_str = name
    name = f"{parent_scope.id}_{name}"

    if name not in screen_state.scopes:
        scope = Scope(name, parent_scope.screen, screen_state)
        scope.parent_scope = parent_scope
        scope.main_scope = parent_scope
        scope.exec = activate_scope
        parent_scope.sub_scopes[name] = scope

        def exit_scope(scope: Scope, screen_state: ScreenState):
            screen_state.activeScope = scope.parent_scope

        scope.exec_own = exit_scope
        scope.data["prompt"] = ""
        scope.data["cursor"] = 0

    scope: Scope = screen_state.scopes[name]
    scope_exec_args = [screen_state]
    prompt = scope.data["prompt"]

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

    stdscr.attron(curses.color_pair(P_text_color))
    if bold:
        stdscr.attron(curses.A_BOLD)
    if inverse_color:
        stdscr.attron(curses.A_REVERSE)
    stdscr.addstr(pos.y, pos.x, pre_text)
    #stdscr.getstr(pos.y, pos.x + len(pre_text), 30)
    #stdscr.attroff(curses.A_BOLD | curses.A_REVERSE)
    LENGHT_PROMPT = 20


    #field = u'\u2580\u2584' * LENGHT_PROMPT
    field = u'\u2591\u2591' * LENGHT_PROMPT

    if scope.selected:
        stdscr.attron(curses.A_REVERSE)
        stdscr.addstr(pos.y, pos.x + len(pre_text), field)
        stdscr.attroff(curses.A_REVERSE)
    else:
        stdscr.addstr(pos.y, pos.x + len(pre_text), field)

    stdscr.addstr(pos.y, pos.x + len(pre_text), prompt)
    stdscr.attroff(curses.A_REVERSE)

    if scope_state:
        idx = scope.data['cursor']
        s = scope.data['prompt']
        if len(s) <= idx:
            stdscr.addstr(pos.y, pos.x + len(pre_text) + idx, u'\u2588')
            cursor_pos = pos + UIgraph.Point(len(pre_text) + idx, 0)
            create_blinking_text(stdscr, cursor_pos, u'\u2588', P_text_color)
        else:
            cursor_pos = pos + UIgraph.Point(len(pre_text) + idx, 0)
            create_blinking_text(stdscr, cursor_pos, prompt[idx], P_text_color)


def create_text_figlet(scr, pos: UIgraph.Point, figlet_font, text: str, P_text_color):
    """Create figlet text."""

    scr.attron(curses.color_pair(P_text_color))
    s = UItext.renderFont(text, figlet_font)
    for n, line in enumerate(s):
        scr.addstr(pos.y + n, pos.x, line)


def create_text_double_space(scr, pos: UIgraph.Point, text: str,
                             P_text_color, P_background_color,
                             edge_type: int, bold: bool = False):
    """What?
    edge_type: 0 firt row, 1 middle row, 2 end row, 3 single row"""

    col = pos.x
    row = pos.y
    text = f" {text} " # add the frame
    text_len = len(text)
    scr.attron(curses.color_pair(P_background_color) | curses.A_BOLD)

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
    scr.attroff(curses.A_REVERSE)
    scr.attron(curses.color_pair(P_text_color))
    scr.addstr(row, col, ' ' * (text_len))
    #if multipleSelection:
    #    scr.addstr(row, col, u' \u25A1 /\u25A0')
    #else:
    #    scr.addstr(row, col, ' ')
    scr.addstr(row, col, str(text))

    # disable bold
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
            print("its bug")
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
               active=False, # what is it?
               multipleSelection=False,
               data_table_legend=None):

    """Create a beautiful and shining tab
    dataTable: 2dim data list
    data_table_keys: key used when something is selected
    position: relative to the parent win
    size: if it fit in the parent win
    active: if we can select elements"""


    ### make empty data_table_color if...
    if data_table_color is None:
        row = len(dataTable)
        col = len(dataTable[0])
        data_table_color = [list([None] * col) for _ in range(row)]


    ### transpose if needed
    # the shape of the data should be like this:
    # [['DBX', '61.0000', '0.0041477', '-0.601%', '0.10754', '-0.601%', '0.25301', '6.55972'],
    # ['MBX', '218853', '8.2087e-07', '-0.226%', '0.000021282', '-0.226%', '0.17965', '4.65769'],
    # [...]]
    if transpose:
        dataTable = transpose_table(dataTable)
        data_table_color = transpose_table(data_table_color)

    ### assert the shape of the data
    assert len(data_table_legend) == len(dataTable[0]), "legend data lenght differ from the data"

    ### name
    tab_name = f"{parent_scope.id}_{tab_name}"

    ### init scope and add to parent
    if tab_name not in screenState.scopes:
        scope = Scope(tab_name, parent_scope.screen, screenState)
        scope.parent_scope = parent_scope
        scope.main_scope = parent_scope
        scope.exec = activate_scope
        parent_scope.sub_scopes[tab_name] = scope

        scope.exec_own = scope_activation_func

    scope = screenState.scopes[tab_name]
    tab_scope_is_active = False
    scope_exec_args = [screenState]
    if scope is screenState.activeScope:
        scope.update_no_sub(len(dataTable))
        screenState.scope_exec_args = scope_exec_args
        tab_scope_is_active = True

    ### end scope stuff ####

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
        y_tabSize = parent_win_dim.y - pos_y -1

    height_low_bar = 1
    height_legend = 3
    if data_table_legend is None:
        height_legend = 0

    ### make data as stirng
    ### probably not necessary anymore
    dataTable = cast_table_items_to_string(dataTable)

    ### curse customs colors
    P_soft = screenState.colorPairs["tab_soft"]
    P_dark = screenState.colorPairs["tab_dark"]
    P_soft_bg = screenState.colorPairs["tab_soft_bg"]
    P_select = screenState.colorPairs["tab_select"]
    P_selected = screenState.colorPairs["tab_selected"]
    P_win_selected = screenState.colorPairs["win_select"]
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
    col_len = len(dataTable)
    rows_number = y_tabSize - height_low_bar - height_legend

    ### recalculate firt and last element
    idx_first_element, idx_last_element, select = recalcultate_first_and_last_element(scope, idx_first_element, col_len, rows_number)
    #### update first element when window is resized
    tab_length = idx_first_element - idx_last_element
    if tab_length < rows_number:
        idx_first_element = max(idx_first_element - (rows_number - tab_length), 0)
        idx_first_element, idx_last_element, select = recalcultate_first_and_last_element(scope, idx_first_element, col_len, rows_number)

    count = 0
    idx_dataTable = range(col_len)

    ### update first element
    scope.data["idx_first_element"] = idx_first_element

    ### max dim for the table
    max_table_width = parent_win_dim.x - position.x - 3  # CONST for borders
    x_tabSize = max_table_width

    table = scr.subwin(y_tabSize, x_tabSize, abs_pos_y, abs_pos_x)
    table.bkgd(' ', curses.color_pair(P_win_background))

    ### highlight scope if selected
    if scope.selected:
        scr.addstr(pos_y + y_tabSize, pos_x, u'\u2580' * x_tabSize,
                   curses.color_pair(P_win_selected))
        scr.addstr(pos_y + y_tabSize, pos_x + x_tabSize, u'\u2598',
                   curses.color_pair(P_win_selected))
        scr.addstr(0, 0, "#!@!@!@!@!@!@!@",
                   curses.color_pair(P_win_selected))
        for i in range(y_tabSize):
            scr.addstr(pos_y + i, pos_x + x_tabSize, u'\u258c',
                       curses.color_pair(P_win_selected))

    # calculate max dim and max number of columns
    x_colSize, x_colStart = calc_size_column(dataTable, data_table_color, data_table_legend,
                                             scope, max_table_width, multipleSelection, 
                                             x_tabSize)

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

    ### data loop ###
    row = height_legend
    for data_row, data_idx in zip(
            dataTable[idx_first_element:idx_last_element],
            idx_dataTable[idx_first_element:idx_last_element]):

        C_custom_bk = table_bk_colors[row % 2]
        P_current_attron = curses.color_pair(table_color_pairs[row % 2]) # colling it P_... is misleading
        if data_idx == select and tab_scope_is_active:
            P_current_attron = curses.color_pair(P_select)
            scope_exec_args.append(data_table_keys[data_idx] if data_table_keys else None)

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

            table.addstr(row, x_colStart[i_col], str(col))
            table.attron(P_current_attron)

        row += 1
        count += 1


    ### position bar
    P_soft = screenState.colorPairs["tab_soft_bg"]
    P_dark = screenState.colorPairs["tab_dark"]
    P_win_selected = screenState.colorPairs["win_select"]

    row_selected = select
    # idx_first_element
    # idx_last_element

    #bar_dim = max(floor(rows_number / col_len * rows_number), 1)
    steps = col_len - rows_number
    if steps > 0:
        bar_dim = max(rows_number - steps, 1)
        bar_pos = floor(idx_first_element / steps * min(steps, rows_number - 1))

        #global DEBUG_OBJ
        #DEBUG_OBJ.text = (
        #    f"steps: {steps}, bar_dim: {bar_dim}, bar_pos: {bar_pos}"
        #    f" rows_number: {rows_number}, tot_elem: {col_len}"
        #    f" ratio idx/step: {idx_first_element / steps}"
        #)

        bar_row = height_legend
        table.attron(curses.color_pair(P_soft))
        for i in range(rows_number):
            if i == bar_pos:
                table.attron(curses.color_pair(P_dark))
            elif i == (bar_pos + bar_dim):
                table.attron(curses.color_pair(P_soft))
            table.addstr(bar_row + i, max_table_width - 1, u'\u2588')
            #table.addstr(bar_row + i, max_table_width - 1, ' ')


    ### end of the window
    while row <= (y_tabSize - height_low_bar):
        table.attron(curses.color_pair(P_soft_bg) | curses.A_BOLD)
        try:
            table.addstr(row, 0, u'\u2571' * (x_tabSize))
        except:
            # last line curses bug
            pass
        row += 1
    table.attroff(curses.A_BOLD)



def create_tab_large(scr, screenState: ScreenState, parent_scope: Scope, name: str,
                     dataTable, data_table_keys: List[str], data_table_color,
                     transpose: bool, pos: UIgraph.Point, size: UIgraph.Point,
                     keyboardState, tabName, row_height, sub_scope_activation, active=False, multipleSelection=False,
                     data_table_legend=None, graph_data=None):
    """Create a beautiful and shining tab
    dataTable: 2dim data list
    data_table_keys: key used when something is selected
    active: if we can select elements"""

    ### to rewrite and integrate with the normal create_tab, keep only the graphic part separeted

    win_width = screenState.screen_size.x
    win_height = screenState.screen_size.y

    if row_height != 2:
        row_height = row_height + (not row_height % 2)

    name = f"{parent_scope.id}_{name}"

    if name not in screenState.scopes:
        scope = Scope(name, parent_scope.screen, screenState)
        scope.parent_scope = parent_scope
        scope.main_scope = parent_scope
        if len(data_table_keys) > 1:
            scope.exec = activate_scope

            # create a child to create another window
            # probably it should be something that we define outside
            # this function because it change every time
            child_name = name + "temp_child"
            child_scope = Scope(child_name, None, screenState)

            child_scope.exec = sub_scope_activation
            child_scope.parent_scope = scope

            scope.sub_scopes[child_name] = child_scope
        else:
            scope.exec = sub_scope_activation
        parent_scope.sub_scopes[name] = scope

    scope = screenState.scopes[name]
    tab_scope_is_active = False
    scope_exec_args = [screenState]
    if scope is screenState.activeScope:
        scope.update_no_sub(len(dataTable[0]))
        screenState.scope_exec_args = scope_exec_args
        tab_scope_is_active = True

    ### end scope stuff ####

    ### tab geometry
    x_tabSize = size.x
    y_tabSize = size.y

    height_low_bar = 1
    height_legend = 3
    if data_table_legend is None:
        height_legend = 0

    # make data as stirng
    data_table_table_str = []
    for col in dataTable:
        col_str = []
        for u in col:
            if isinstance(u, float):
                #if u > 1:
                u = dex.format_and_round_number(u, 5, 10)
                col_str.append(str(u))
            else:
                col_str.append(str(u))
        data_table_table_str.append(col_str)

    dataTable = data_table_table_str

    # curse customs colors
    P_soft = screenState.colorPairs["tab_soft"]
    P_dark = screenState.colorPairs["tab_dark"]
    P_soft_bg = screenState.colorPairs["tab_soft_bg"]
    P_dark_bg = screenState.colorPairs["tab_dark_bg"]
    P_select = screenState.colorPairs["tab_select"]
    P_selected = screenState.colorPairs["tab_selected"]
    P_win_selected = screenState.colorPairs["win_select"]
    if tab_scope_is_active:
        P_win_selected = screenState.colorPairs["body"]
    P_win_background = screenState.colorPairs["tab_soft"]

    # background for custom colors
    C_default_background = screenState.colors["background"]
    C_soft_background = screenState.colors["tab_soft"]
    C_dark_background = screenState.colors["tab_dark"]

    table_bk_colors = [C_soft_background, C_dark_background] # these are not pairs
    table_color_pairs = [P_soft, P_dark]
    table_alternative_bk_pairs = [P_soft_bg, P_dark_bg]

    if data_table_color is None:
        row = len(dataTable)
        col = len(dataTable[0])
        data_table_color = [[None] * col] * row

    # debug
    # scr.addstr(3, 3, f"dim {len(dataTable)} and {len(dataTable[0])}")
    # scr.addstr(4, 3, f"dim {len(data_table_color)} and {len(data_table_color[0])}")
    # scr.addstr(5, 3, f"dim {str(data_table_color)}")

    # TODO eliminate one of the two transpositions
    if transpose:
        transposed_table = [[row[i] for row in dataTable] for i in range(len(dataTable[0]))]

        dataTable = transposed_table

        transposed_table = [[row[i] for row in data_table_color] for i in range(len(data_table_color[0]))]

        data_table_color = transposed_table

    ### tab creation
    # add the scroll logic above

    ## logic for multiple lines
    ## TODO -> move to scopes
    ## add logic to reset or check if the elements changes in any wat
    ## to avoid that the selection change... or find anther way to select it that
    ## is not the index. Maybe a dic with a unique key could be better
    # select pair
    if tabName not in screenState.screen_data:
        screenState.screen_data[tabName] = {}
        if multipleSelection:
            screenState.screen_data[tabName]["idx_selected"] = []
    if "idx_first_element" not in screenState.screen_data:
        screenState.screen_data[tabName]["idx_first_element"] = 0

    select = screenState.selection
    idx_first_element = screenState.screen_data[tabName]["idx_first_element"]

    # here to be clarified if we transpose or not, or how to manage the transposition
    # ideally a togle to transpose and then make the code without any transposition
    # afterward
    col_len = len(dataTable[0])
    rows_number = (y_tabSize - height_low_bar - height_legend) // row_height

    #select = select % col_len
    select = scope.cursor % col_len
    idx_last_element = idx_first_element + rows_number
    if select >= (idx_last_element):
        idx_last_element = select + 1
        idx_first_element = idx_last_element - rows_number
    elif idx_first_element > select:
        idx_first_element = select % col_len
        idx_last_element = (idx_first_element + rows_number) % col_len

    count = 0
    idx_dataTable = range(col_len)

    screenState.screen_data[tabName]["idx_first_element"] = idx_first_element

    # max dim for the table
    max_table_width = win_width - pos.x - 3  # maybe add a global for borders
    x_tabSize = max_table_width

    table = scr.subwin(y_tabSize, x_tabSize, pos.y, pos.x)

    # selection
    if scope.selected:
        scr.addstr(pos.y + y_tabSize - 1, pos.x, u'\u2580' * x_tabSize,
                   curses.color_pair(P_win_selected))
        scr.addstr(pos.y + y_tabSize - 1, pos.x + x_tabSize, u'\u2598',
                   curses.color_pair(P_win_selected))
        for i in range(y_tabSize):
            scr.addstr(pos.y + i - 1, pos.x + x_tabSize, u'\u258c',
                       curses.color_pair(P_win_selected))
    if scope.selected and len(data_table_keys) == 1:
        screenState.scope_exec_args = [screenState, data_table_keys[0]]
    else:
        screenState.scope_exec_args = [screenState]

    # max dim for columns
    max_dims = []
    total_dims = 0
    column_separator = 2
    for idx in range(len(dataTable)):
        max_dim = 0
        for i in dataTable[idx]:
            if len(str(i)) > max_dim:
                max_dim = len(i)
        if data_table_legend is not None:
            for i in data_table_legend[idx]:
                if len(i) > max_dim:
                    max_dim = len(i)
        max_dim += column_separator
        total_dims += max_dim
        max_dims.append(max_dim)

    if total_dims > max_table_width:
        scope_x = scope.cursor_x
        scope.cursor_x = 0
        scr.addstr(25,10, f"the x scope is {scope_x}")
        idx_fix_item = 2
        # remove column based on the cursor value
        while scope_x > 0 and total_dims > max_table_width:
            dim = max_dims.pop(idx_fix_item)
            dataTable.pop(idx_fix_item)
            data_table_color.pop(idx_fix_item)
            if data_table_legend is not None:
                data_table_legend.pop(idx_fix_item)
            total_dims -= dim
            scope_x -= 1
            scope.cursor_x += 1
        # remove last column until there is enough space
        while total_dims > max_table_width:
            dim = max_dims.pop(-1)
            dataTable.pop(-1)
            data_table_color.pop(-1)
            if data_table_legend is not None:
                data_table_legend.pop(-1)
            total_dims -= dim

    x_remainder = 0

    ###### second transposition... ######
    transposed_table = [[row[i] for row in dataTable] for i in range(len(dataTable[0]))]
    dataTable = transposed_table
    transposed_table = [[row[i] for row in data_table_color] for i in range(len(data_table_color[0]))]
    data_table_color = transposed_table
    # example of the shape of the data, per line
    # [['DBX', '61.0000', '0.0041477', '-0.601%', '0.10754', '-0.601%', '0.25301', '6.55972'],
    # ['MBX', '218853', '8.2087e-07', '-0.226%', '0.000021282', '-0.226%', '0.17965', '4.65769'],

    n_columns = len(dataTable[0])
    if multipleSelection:
        n_columns += 1  # add the selection column

    x_remainder = (x_tabSize - total_dims) // n_columns

    x_colDim = []
    for i in max_dims:
        x_colDim.append(i + x_remainder)
        # x_colDim.append(i)

    x_colStart = [0]
    if multipleSelection:
        #x_colStart[0] += 4 # add the selection column
        x_colStart[0] += 7  # add the selection column
    else:
        x_colStart[0] += 1  # add the selection column
    for i in range(len(max_dims) - 1):
        x_colStart.append(x_colStart[-1] + max_dims[i] + x_remainder)

    row = 0
    ### legend loop ###
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
        if row_height == 2:
            table_color_pairs.reverse()  # to begin always with the soft color
            table_bk_colors.reverse()  # to begin always with the soft color
            table_alternative_bk_pairs.reverse()  # to begin always with the soft color

        # disable bold
        table.attroff(curses.A_BOLD)

    ### data loop ###

    row = height_legend
    if row_height == 2:
        row = height_legend - 1

    for data_row, data_idx in zip(
            dataTable[idx_first_element:idx_last_element],
            idx_dataTable[idx_first_element:idx_last_element]):

        C_custom_bk = table_bk_colors[count % 2]
        P_current_attron = curses.color_pair(table_color_pairs[count % 2])
        P_current_bg = curses.color_pair(table_alternative_bk_pairs[count % 2])
        if data_idx == select and tab_scope_is_active:
            P_current_attron = curses.color_pair(P_select)
            scope_exec_args.append(data_table_keys[data_idx] if data_table_keys else None)

            # to highlight the entire row, but not working correctly if the
            # height is odd...
            #P_current_bg= curses.color_pair(table_color_pairs[not count % 2])

        table.attron(P_current_attron)
        #table.addstr(row, 0, ' ' * (x_tabSize))

        text_double_space(table, UIgraph.Point(0, row), ' ' * (x_tabSize),
                          P_current_attron, P_current_bg,
                          0, row_height)

        ##################################################
        #####work around curses bug last char last column
        ##################################################
        #try:
        #    table.addstr(data_idx, 0, ' ' * (x_tabSize))
        #except:
        #    pass
        ###################################################

        if multipleSelection:
            if data_idx in screenState.screen_data[tabName]['idx_selected']:
                P_current_attron = curses.color_pair(P_selected)
                C_custom_bk = screenState.colors["chia_green"]
                table.attron(P_current_attron)
                #table.addstr(data_idx, 0, ' ' * (x_tabSize))
                #table.addstr(row, 1, u' \u25A0')
                P_sel_bg= curses.color_pair(table_color_pairs[not count % 2])
                text_double_space(table, UIgraph.Point(0, row), ' ' * (x_tabSize),
                                  P_current_attron, P_sel_bg,
                                  0, row_height)
                text_double_space(table, UIgraph.Point(1, row), u' \u25A0',
                                  P_current_attron, P_current_bg,
                                  0, row_height)
            else:
                #table.addstr(row, 1, u' \u25A1')
                text_double_space(table, UIgraph.Point(1, row), u' \u25A1',
                                  P_current_attron, P_current_bg,
                                  0, row_height)

        for i_col, col in enumerate(data_row):
            text_color = data_table_color[data_idx][i_col]
            P_mod_attron = P_current_attron
            if text_color is not None and (data_idx != select or not tab_scope_is_active):
                text_c_pair = UIgraph.addCustomColorTuple(
                    (text_color, C_custom_bk),
                    screenState.cursesColors)
                P_mod_attron = curses.color_pair(text_c_pair)
                table.attron(P_mod_attron)

            text_double_space(table, UIgraph.Point(x_colStart[i_col], row), str(col),
                              P_mod_attron, P_current_bg,
                              0, row_height)
            #table.addstr(row, x_colStart[i_col], str(col))
            table.attron(P_current_attron)

        ###row += 2
        row += row_height
        count += 1
        #row = row % height
    ### end of the window
    row += 1
    while row <= (y_tabSize - height_low_bar):
        table.attron(curses.color_pair(P_soft_bg) | curses.A_BOLD)
        try:
            table.addstr(row, 0, u'\u2571' * (x_tabSize))
        except:
            # curses bug last line
            pass
        row += 1
    table.attroff(curses.A_BOLD)

    # create the graphs
    pos += UIgraph.Point(10,3)
    if graph_data is not None:
        color_up = screenState.colors['azure_up']
        color_down = screenState.colors['white_down']
        graph_height = row_height
        graph_width = 20
        count = 0
        for coin_prices in graph_data[idx_first_element:idx_last_element]:
            try:
                C_soft_background = screenState.colors["tab_soft"]
                C_dark_background = screenState.colors["tab_dark"]
                if count % 2:
                    P_graph = UIgraph.addCustomColorTuple(
                        (color_down, C_dark_background),
                        screenState.cursesColors)
                else:
                    P_graph = UIgraph.addCustomColorTuple(
                        (color_up, C_soft_background),
                        screenState.cursesColors)

                # curses BUG: probably it is not possible making subwin of subwin
                #graph_win = table.subwin(graph_height, graph_width, pos.y, pos.x)  # y, x
                graph_win = scr.subwin(graph_height, graph_width, pos.y, pos.x)  # y, x
                #graph_win.bkgd(' ', curses.color_pair(screenState.colorPairs["tab_dark_bg"]))
                graph_win.bkgd(' ', curses.color_pair(P_graph))
                graph_win.erase()
                prices = list(coin_prices.values())
                timestamp = list(coin_prices.keys())
                if len(prices) < 1:
                    print("hahaha")
                    # prices = [chia_current_price_currency]
                    # timestamp = [chia_coins_data.current_price_date]
                #wallet_win.addstr(pos.y, 10, f"the cat is: {prices}")
                #debug_win.addstr(y0 + 1,70, f"len: {len(prices)}; time {timestamp[0]} and prices; {prices[0]}")
                #prices, timestamp = dex.getHistoricPriceFromTail(cat, 7)
                count += 1
                UIgraph.drawPriceGraph(graph_win, screenState, prices, timestamp, 7, P_graph)
                # create chia graph
                pos += UIgraph.Point(0,graph_height)
            except:
                pos += UIgraph.Point(0,graph_height)
                print(f"out of GRAPH {graph_height} {graph_width} y:{pos.y} x:{pos.x}")
                traceback.print_exc()



def create_button(stdscr, screenState: ScreenState, parent_scope: Scope, name: str,
                  point: UIgraph.Point):
    """A real button... """

    name_str = name
    name = f"{parent_scope.id}_{name}"

    if name not in screenState.scopes:
        scope = Scope(name, parent_scope.screen, screenState)
        scope.parent_scope = parent_scope
        scope.main_scope = parent_scope
        parent_scope.sub_scopes[name] = scope

        def change_button_bool(scope: Scope, screenState: ScreenState):
            scope.bool = not scope.bool
            return scope.parent_scope

        scope.exec = change_button_bool

    scope: Scope = screenState.scopes[name]
    scope_exec_args = [screenState]

    if scope is screenState.activeScope:
        scope.update()
        screenState.scope_exec_args = scope_exec_args

    pos_x = point.x
    pos_y = point.y

    but = name_str
    space = 2
    length = len(but) + space * 2

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
        stdscr.addstr(pos_y + 1, x, f"{but}",
                      curses.color_pair(text_dark) | curses.A_BOLD)
        x += length - 2 * space
        stdscr.addstr(pos_y + 1, x, u'\u2588' * space,
                      curses.color_pair(frame_cp_dark) | curses.A_BOLD)

        # lower row
        stdscr.addstr(pos_y + 2, pos_x + 0, u'\u2580' * (length + 1),
                      curses.color_pair(frame_cp_dark))
        frame_selected = UIgraph.addCustomColorTuple(
            (text_color_background_dark, default_selected),
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
        stdscr.addstr(pos_y + 1, x, f"{but}",
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
            (text_color_background_clear, default_selected),
            screenState.cursesColors
        )

    # selection
    if scope.selected:
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
    for i, m in enumerate(menu_list):
        menu_list[i] = f"{i} - {menu_list[i]}"

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

        #DEBUG_OBJ.text += (f"AFTER f_idx: {first_idx} "
        #                   f"l_idx: {last_idx} "
        #                   )
        #DEBUG_OBJ.text += (f"selected: {selected} "
        #                   f"menu: {menu_list} "
        #                   )
        #DEBUG_OBJ.text += f"date: {datetime.now()} "

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


def menu_select(stdscr, menu: str, scope: Scope, point: UIgraph.Point,
                color_pair, color_pair_sel):
    """Create a menu at given coordinate. Point[y,x]"""

    #selected = scope.data['selected']
    #selected = scope.cursor

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
                       name: str, menu: List[str], point: UIgraph.Point):
    """A real menu button... """

    name_str = name
    name = f"{parent_scope.id}_{name}"

    if name not in screenState.scopes:
        #scope = Scope(name, parent_scope.screen, screenState)
        #scope.parent_scope = parent_scope
        #parent_scope.sub_scopes[name] = scope

        #def change_menu_value(scope: Scope, screenState: ScreenState):
        #    pass
        #    #### 
        #    #scope.dict_values = "new value to pass to the function"
        #    #return scope.parent_scope

        ##scope.exec = change_button_bool
        scope = Scope(name, parent_scope.screen, screenState)
        scope.parent_scope = parent_scope
        scope.main_scope = parent_scope
        scope.exec = activate_scope
        scope.cursor = 0
        parent_scope.sub_scopes[name] = scope

#        # create a child to create another window
#        # probably it should be something that we define outside
#        # this function because it change every time
        child_name = name + "temp_child"
        child_scope = Scope(child_name, None, screenState)

        child_scope.exec = activate_grandparent_scope

        child_scope.parent_scope = scope

        scope.sub_scopes[child_name] = child_scope

    scope = screenState.scopes[name]
    scope_is_active = False
    scope_exec_args = [screenState]
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
    print(scope.cursor)
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
    if scope.selected:
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


@dataclass
class BlockState:
    height: int
    infused: bool
    mempool: bool
    transaction: bool
    fullness: float


def create_block_band(stdscr, screenState: ScreenState, parent_scope: Scope,
                      name: str, block_states: list[BlockState], point: UIgraph.Point):
    """Block band navigator mempool.space style..."""

    name_str = name
    name = f"{parent_scope.id}_{name}"

    if name not in screenState.scopes:
        scope = Scope(name, parent_scope.screen, screenState)
        scope.parent_scope = parent_scope
        scope.main_scope = parent_scope
        scope.exec = activate_scope
        scope.cursor = 0
        parent_scope.sub_scopes[name] = scope

        scope.exec_own = activate_grandparent_scope  # da cambiare
        scope.data["first_block"] = None
        scope.data["current_block_height"] = None

    scope: Scope = screenState.scopes[name]
    scope_is_active = False
    scope_exec_args = [screenState]

    if scope is screenState.activeScope:
        scope.update_no_sub(len(block_states), False)
        screenState.scope_exec_args = scope_exec_args
        scope_is_active = True

    win_size = stdscr.getmaxyx()
    win_size = UIgraph.Point(win_size[1], win_size[0])


    # scrolling:
    # block input as hashtable
    # keep: selected block and first block, if next block, out of screen
    ## change first block value
    ## memepool -> possible height, but make it clear it is memepool


    # i need a variable to comunicate with the back end to give me the right block
    # maybe it is better to create a feeder function that use the current idx of 
    # the selected block

    # idea
    # get the dim of the win
    # calculate number of block in the memepool
    # dispaly at least one validated block
    # from the starting point draw the rectangles
    # indicate the beginning of a sub-slot and also of a slot
    # make another graph the show when sub-slot and slot are not
    # the same
    # show when there are 2 block for the same signage point

    P_yellow_bee = screenState.colorPairs["win_selected"]
    P_azzure = screenState.colorPairs["up"]
    P_white = screenState.colorPairs["down"]

    # selected block
    #scope.cursor

    current_block = None
    idx_last_block = None
    n_mempool_block = 0
    for b in block_states:
        if b.mempool:
            n_mempool_block += 1
        else:
            break

    mempool_blocks = block_states[:n_mempool_block]
    block_states = block_states[n_mempool_block:]

    current_block = block_states[0]
    idx_last_block = 0

    name_block_len = len(f'{current_block.height:_}')
    # rectangle block dim
    rec_dim_x = int(name_block_len + name_block_len % 2) + 2
    rec_dim_y = int(rec_dim_x / 2)
    rec_dim = UIgraph.Point(rec_dim_x, rec_dim_y)
    rec_mini = UIgraph.Point(4, 2)

    bp = point

    # memepool blocks
    for n, b in enumerate(mempool_blocks):
        #if n >= idx_last_block:
        #    break

        if bp.x + rec_dim.x > win_size.x:
            break

        p = bp
        create_text(stdscr, p, f'{b.height:_}', P_azzure, True)
        p = p + UIgraph.Point(0, 1)
        create_text(stdscr, p, f'{b.height:,}', P_azzure, True)
        p = p + UIgraph.Point(0, 1)
        draw_rect(stdscr, p, rec_dim, P_azzure)
        bp += UIgraph.Point(rec_dim.x + 2, 0)

    # separation line
#    ## dot line
#    for i in range(rec_dim.y + 3):
#        p = bp
#        create_text(stdscr, p + UIgraph.Point(0, i), u'\u254F', P_white, True)
#    bp += UIgraph.Point(1 + 2, 0)
#
#    ## up arrow
#    for i in range(rec_dim.y + 3):
#        p = bp
#        create_text(stdscr, p + UIgraph.Point(0, i), u'\u2571', P_white, True)
#        create_text(stdscr, p + UIgraph.Point(1, i), u'\u2572', P_white, True)
#    bp += UIgraph.Point(2 + 2, 0)
#
    ## band stripe
    ## it neew to be even the height of the line to be nice
    bp += UIgraph.Point(1, 0)
    for i in range(rec_dim.y + 4):
        p = bp
        if i % 2:
            create_text(stdscr, p + UIgraph.Point(0, i), u'\u25E2', P_white, True)
        else:
            create_text(stdscr, p + UIgraph.Point(0, i), u'\u25E4', P_white, True)
    bp += UIgraph.Point(1 + 3, 0)

#    ## band stripe double
#    for i in range(rec_dim.y + 3):
#        p = bp
#        if i % 2:
#            create_text(stdscr, p + UIgraph.Point(0, i), u'\u25E2', P_white, True)
#            create_text(stdscr, p + UIgraph.Point(1, i), u'\u25E4', P_white, True)
#        else:
#            create_text(stdscr, p + UIgraph.Point(0, i), u'\u25E4', P_white, True)
#            create_text(stdscr, p + UIgraph.Point(1, i), u'\u25E2', P_white, True)
#    bp += UIgraph.Point(2 + 2, 0)

    # chain blocks

    for n, b in enumerate(block_states):
        # select the rec_dim before and then keep only one
        if n < idx_last_block:
            continue
        if b.transaction:
            if bp.x + rec_dim.x > win_size.x:
                break
            p = bp
            create_text(stdscr, p, f'{b.height:_}', P_yellow_bee, True)
            p = p + UIgraph.Point(0, 1)
            create_text(stdscr, p, f'{b.height:,}', P_yellow_bee, True)
            p = p + UIgraph.Point(0, 1)
            draw_rect(stdscr, p, rec_dim, P_yellow_bee)
            bp += UIgraph.Point(rec_dim.x + 2, 0)

            if n == scope.cursor:
                p = p + UIgraph.Point(0, rec_dim.y)
                create_text(stdscr, p, 'bo', P_yellow_bee, True)
        else:
            if bp.x + rec_mini.x > win_size.x:
                break
            p = bp + UIgraph.Point(0, 3)
            create_text(stdscr, p, f'..{str(b.height)[-1:]}', P_yellow_bee, True)
            p = p + UIgraph.Point(0, 1)
            draw_rect(stdscr, p, rec_mini, P_yellow_bee)
            bp += UIgraph.Point(rec_mini.x + 2, 0)

            if n == scope.cursor:
                p = p + UIgraph.Point(0, rec_mini.y)
                create_text(stdscr, p, 'bo', P_yellow_bee, True)

    # scope selection
    # rec_dim.y + 4, height of the separation line, to parametrize...
    edge_size = 2
    x_size = win_size.x - edge_size * 2
    bp = UIgraph.Point(edge_size, rec_dim.y + 4 + 2)
    if scope_is_active:
        create_text(stdscr, bp, u'\u2584' * x_size, P_yellow_bee, True)
    else:
        create_text(stdscr, bp, u'\u2580' * x_size, P_azzure, True)




