import sys
import ast
import sqlite3  # remove it
from typing import List, Tuple, Dict, Union, Callable
from types import SimpleNamespace
import curses
from datetime import datetime
import threading
import time
import traceback
import json
import os

#from chia.rpc.full_node_rpc_client import FullNodeRpcClient
#from chia.rpc.rpc_server import RpcServer
#from chia.rpc.wallet_rpc_client import WalletRpcClient
#from chia.daemon.client import connect_to_daemon_and_validate
#from chia_rs.sized_bytes import bytes32, bytes48
#from chia.types.blockchain_format.program import Program
#from chia.types.spend_bundle import SpendBundle
#from clvm_tools.binutils import disassemble
from chia.util.bech32m import decode_puzzle_hash, encode_puzzle_hash
from chia_rs import SpendBundle
from chia_rs.sized_bytes import bytes32, bytes48
from chia_rs.sized_ints import uint16, uint32, uint64, uint128
from chia.types.blockchain_format.program import Program as PyProgram
from chia.types.condition_opcodes import ConditionOpcode
from clvm_tools.binutils import assemble, disassemble

import src.UIgraph as UIgraph
import src.KEYBOARDtiller as KEYBOARD
import src.ELEMENTStiller as ELEMENTS
import src.TEXTtiller as TEXT
import src.WDBtiller as WDB
import src.UTILStiller as UTILS
import src.RPCtiller as RPC
import src.PUZZLEtiller as PUZ
import src.TYPEStiller as TYPES
import src.SCANtiller as SCAN
import src.HEATMAPtiller as HEAT
import src.CHIALOGtiller as CHIALOG
import src.PLATFORMtiller as PLAT
from src.TYPEStiller import (
    FingerState, CoinPriceData, ScreenState, FullNodeState, Scope, KeyboardState,
    FullNodeState, ScreenState, ScopeActions)

from src.CONFtiller import (
    debug_logger, logging, DEBUGGING, DB_BLOCKCHAIN_RO, DB_WDB, DB_SB, DB_BLOCKCHAIN_RO, SQL_TIMEOUT, XCH_FAKETAIL,
    BTC_FAKETAIL, XCH_CUR, USD_CUR, XCH_MOJO, CAT_MOJO, full_node_port, full_node_rpc_port,
    DOOM_FONT, FUTURE_FONT, BLOCK_MAX_COST, SMALL_FONT, FUTURE_FONT)
import src.CONFtiller as CONF

import src.DEBUGtiller as DEBUGtiller
DEBUG_OBJ = DEBUGtiller.DEBUG_OBJ

# UI
def deep_getsizeof(object, seen=None):
    if seen is None:
        seen = set()
    object_id = id(object)
    if object_id in seen:
        return 0

    seen.add(object_id)
    size = sys.getsizeof(object)

    if isinstance(object, dict):
        size += sum(deep_getsizeof(k, seen) + deep_getsizeof(v, seen) for k, v in object.items())
    elif isinstance(object, (list, tuple, set, frozenset)):
        size += sum(deep_getsizeof(i, seen) for i in object)

    return size


def createFullSubWin(stdscr, screenState, height, width):
    """Create a subwindow for curses considering header and footer"""
    nLinesUsed = screenState.headerLines + screenState.footerLines
    return stdscr.subwin(height - nLinesUsed, width, screenState.headerLines, 0)


def menu_select(stdscr, menu, select, point, color_pairs, color_pairs_sel,
                figlet=False):
    ##### legacy, to replace with menu_select_figlet
    """Create a menu at given coordinate. Point[y,x]"""

    if figlet:

        s_height = FUTURE_FONT.height

        for i, item in enumerate(menu):
            if select == i:
                stdscr.attron(curses.color_pair(color_pairs_sel))
            else:
                stdscr.attron(curses.color_pair(color_pairs))
            text = (str(i) + " - " + str(item))
            s = TEXT.renderFont(text, FUTURE_FONT)
            for n, line in enumerate(s):
                stdscr.addstr(point[0] + i * s_height + n, point[1], line)
    else:
        for i, item in enumerate(menu):
            if select == i:
                stdscr.attron(curses.color_pair(color_pairs_sel) | curses.A_BOLD)
            else:
                stdscr.attron(curses.color_pair(color_pairs) | curses.A_BOLD)
            stdscr.addstr(point[0] + i, point[1], (str(i) + " - " + str(item)))


def menu_select_figlet(stdscr, menu, select, point, color_pairs, color_pairs_sel,
                       figlet=False):
    ### move to ELEMENTStiller
    """Create a menu at given coordinate. Point[y,x]"""

    if figlet:

        s_height = FUTURE_FONT.height

        for i, item in enumerate(menu):
            if select == i:
                stdscr.attron(curses.color_pair(color_pairs_sel))
            else:
                stdscr.attron(curses.color_pair(color_pairs))
            text = str(item)
            s = TEXT.renderFont(text, FUTURE_FONT)
            for n, line in enumerate(s):
                stdscr.addstr(point[0] + i * s_height + n, point[1], line)
    else:
        for i, item in enumerate(menu):
            if select == i:
                stdscr.attron(curses.color_pair(color_pairs_sel) | curses.A_BOLD)
            else:
                stdscr.attron(curses.color_pair(color_pairs) | curses.A_BOLD)
            stdscr.addstr(point[0] + i, point[1], str(item))


def menu_select_def(stdscr, scope, menu, color_pairs, color_pairs_sel,
                    align_h=0, align_v=0, prefix=False, title=None, P_title=None):
    """title: where the menu is (e.g. "puzzles › lists"), above its top left corner, in P_title"""

    if "idxFirst" not in scope.data:
        scope.data["idxFirst"] = 0

    select = scope.cursor
    idxFirst = scope.data["idxFirst"]

    # aligining
    ## menu dimension
    win_size = stdscr.getmaxyx()
    height = win_size[0]
    width = win_size[1]

    if prefix:
        # the numbers right aligned (" 9 - …", "10 - …"): a space is as wide as a digit, also in
        # the figlet font
        digits = len(str(len(menu) - 1))
        for i, m in enumerate(menu):
            menu[i] = f"{i:>{digits}} - {menu[i]}"

    # precalc for the bounding box
    yDimMenu = len(menu)
    yDimMenu_fig = yDimMenu * FUTURE_FONT.height  # generalized the FUTURE_FONT

    longestLine = ''
    xDimMenu = 0
    for i in menu:
        if len(i) > xDimMenu:
            xDimMenu = len(i)
            longestLine = i

    xDimMenu_fig, a = TEXT.sizeText(longestLine, FUTURE_FONT)
    figlet = False
    # the title's rows (an item and an empty line) are kept free, so it is always in the size
    # of the items; the rows of the ▲ ▼ marks are the empty line under the title and a margin
    title_rows = FUTURE_FONT.height + 1 if title else 0
    n_rows = (height - title_rows) // FUTURE_FONT.height - 2
    bbox = UIgraph.Point(0,0)

    # using figlet or not
    if width > xDimMenu_fig * 2 and CONF.FIGLET and n_rows > 3 and width > 100:
        bbox.x = xDimMenu_fig
        figlet = True
    else:
        n_rows = height - 2 - (2 if title else 0) - 2
        bbox.x = xDimMenu

    margin = UIgraph.Point(6,3)
    n_menu, n_selection = ELEMENTS.normalize_menu(menu, scope, n_rows)

    # recalculate bbox on Y: only the items are centered
    if figlet:
        bbox.y = len(n_menu) * FUTURE_FONT.height
    else:
        bbox.y = len(n_menu)

    base_point = ELEMENTS.align_bounding_box(stdscr, bbox, margin, align_h, align_v)
    point = [base_point.y, base_point.x]

    # items out of view: ▲ above the first one, ▼ under the last one, with how many
    if len(n_menu) < len(menu):
        first = scope.data.get('first_idx', 0)
        above, below = first, len(menu) - first - len(n_menu)
        if above and base_point.y >= 1:
            put_text(stdscr, UIgraph.Point(base_point.x, base_point.y - 1), f"▲ {above} more", P_title or color_pairs,
                     bold=True)
        if below and base_point.y + bbox.y < height - 1:
            put_text(stdscr, UIgraph.Point(base_point.x, base_point.y + bbox.y), f"▼ {below} more",
                     P_title or color_pairs, bold=True)

    if title:
        # above the items, in their size (the figlet font has no ›: /), 9 columns to their left;
        # the small font when the big one does not fit above or on the right, none without room
        x = max(0, base_point.x - 9)
        candidates = ([TEXT.renderFont(title.replace('›', '/'), FUTURE_FONT)] if figlet else []) + [[title]]
        for lines in candidates:
            y = base_point.y - len(lines) - 1
            if y >= 0 and x + max(len(line) for line in lines) < width - 1:
                for n, line in enumerate(lines):
                    put_text(stdscr, UIgraph.Point(x, y + n), line, P_title, bold=True)
                break

    menu_select_figlet(stdscr, n_menu, n_selection, point, color_pairs, color_pairs_sel,
                       figlet=figlet)

    # when the visible items move, ncurses sees the same lines on other rows and scrolls the
    # terminal, which flashes a band in the selection color: redrawln makes it send the lines
    # again instead (docs/ui-rules.md, rule 13)
    first = scope.data.get('first_idx', 0)
    if scope.data.get('drawn_first_idx', first) != first:
        stdscr.redrawln(0, height)
    scope.data['drawn_first_idx'] = first


def screen_main_menu(stdscr, keyboardState: KeyboardState, screenState: ScreenState, fullNodeState: FullNodeState,
                     figlet=False):

    width = screenState.screen_size.x
    height = screenState.screen_size.y

    menu_win = createFullSubWin(stdscr, screenState, height, width)
    menu_win.bkgd(' ', curses.color_pair(screenState.colorPairs["body"]))

    activeScope: Scope = screenState.activeScope
    screenState.scope_exec_args = [screenState]

    menu_items = []
    if len(activeScope.sub_scopes) == 0:
        menu_items = [
            ('full node', screen_full_node, ScopeActions.activate_scope, None),
            ('cacheDB', screen_cache_db, ScopeActions.activate_scope, None),
            ('puzzles', screen_puzzles, ScopeActions.activate_scope, None),
            ('menu test', screen_menu_test, ScopeActions.activate_scope, None),  # TEST: remove (PLAN)
        ]
        print("indiddiie")
        if DEBUGGING:
            menu_items += [
                ('wallet', screen_fingers, ScopeActions.activate_scope, None),
                ('harvester analytics', screen_harvester, ScopeActions.activate_scope, None),
                ('dex', screen_dex, ScopeActions.activate_scope, None),
                ("tabs", screen_tabs, ScopeActions.activate_scope, None),
                #('debugging screen', DEBUGtiller.screen_debugging, ScopeActions.activate_scope),
            ]

        ## TODO: move it back in factory_menu?
        for name, handler, exec_fun, exec_key in menu_items:
            new_scope: Scope = Scope(name, handler, screenState)
            new_scope.exec = exec_fun
            new_scope.parent_scope = activeScope
            activeScope.sub_scopes[name] = new_scope
            if exec_key:
                new_scope.keyboard_exec = exec_key

    print(f"menu items {menu_items}")
    print(f"scopes: {activeScope.sub_scopes}")
    print(f"scopes name main: {activeScope.name}")
    factory_menu(menu_items, stdscr, keyboardState, screenState, fullNodeState, figlet=False)


def screen_dex(stdscr, keyboardState: KeyboardState, screenState: ScreenState, fullNodeState: FullNodeState, figlet=False):

    width = screenState.screen_size.x
    height = screenState.screen_size.y

    # select pair
    make_pair_tickers_all()
    if 'dex' not in screenState.screen_data:
        screenState.screen_data["dex"] = {}
        screenState.screen_data["dex"]["tickers"] = loadAllTickers()
    if "idxFirst" not in screenState.screen_data:
        screenState.screen_data["dex"]["idxFirst"] = 0

    tickers = screenState.screen_data["dex"]["tickers"]
    select = screenState.activeScope.cursor
    idxFirst = screenState.screen_data["dex"]["idxFirst"]

    stdscr.attron(curses.color_pair(1))
    stdscr.addstr(11, 10, 'WHAT>>>? ' + str(tickers[0]))

    ymin = 22
    y = ymin
    yMax = 32
    yLines = yMax - ymin
    select = select % len(tickers)
    idxLast = idxFirst + yLines
    if select >= (idxLast):
        idxLast = select + 1
        idxFirst = idxLast - yLines
    elif idxFirst > select:
        idxFirst = select % len(tickers)
        idxLast = (idxFirst + yLines) % len(tickers)
    count = 0
    idTickers = range(len(tickers))
    dd = idTickers[idxFirst:idxLast]

    screenState.screen_data["dex"]["idxFirst"] = idxFirst

    for ticker, idCount in zip(tickers[idxFirst:idxLast], idTickers[idxFirst:idxLast]):
        # print(
        # propably string func is not capable of join emoji? no because it is working on WHAT>>>>
        if idCount == select:
            stdscr.attron(curses.color_pair(2))
            selTicker = ticker
        else:
            stdscr.attron(curses.color_pair(1))

        stdscr.addstr(y, 10, 'WHAT>>>? ' + str(idCount) + ' ' + ticker["base_name"] + "/" + ticker["target_name"])

        y += 1
        count += 1
        y = y % height

    stdscr.addstr(50, 10, 'WHAT>>>? ' + str(select) + ' / idxLast ' + str(idxLast) + 'idx first ' + str(idxFirst) + ' ' + str(dd))

#    if key == curses.KEY_ENTER or key == 10 or key == 13:
#        screen = "TradePair"
#        select = 0
    if keyboardState.enter is True:
        screenState.screen = screenState.menu[screenState.selection]
    if keyboardState.moveUp:
        screenState.selection -= 1
    if keyboardState.moveDown:
        screenState.selection += 1
    if keyboardState.esc is True:
        screenState.screen = 'main'


def screen_intro(stdscr, keyboardState, screenState: ScreenState, fullNodeState: FullNodeState):
    """Intro screen"""

    width = screenState.screen_size.x
    height = screenState.screen_size.y

    # intro
    text = 'rototiller'

    sizeX, sizeY = TEXT.sizeText(text, DOOM_FONT)
    stdscr.bkgd(' ', curses.color_pair(screenState.colorPairs["intro"]))

    screenState.scope_exec_args = [screenState]
    active_scope = screenState.activeScope
    active_scope.update(False)

    if height > sizeY * 2 and width > sizeX * 2:

        s = TEXT.renderFont(text, DOOM_FONT)
        s_height = len(s)
        s_length = len(s[0])

        x = (width - s_length) // 2
        y = (height - s_height) // 2
        for n, line in enumerate(s):
            stdscr.addstr(y + n, x, line, curses.A_BOLD)

    else:
        textLength = len(text)
        x = (width - textLength) // 2
        y = height // 2

        stdscr.addstr(y, x, text, curses.A_BOLD)


def menu_select_s(stdscr, screenState: ScreenState, name: str, menu_list: list, point: UIgraph.Point,
                  color_pairs, color_pairs_sel, parent_scope: Scope,
                  figlet=False):
    """Create a menu at given coordinate.
    point is a UIgraph.Point(x,y)
    """

    name = f"{parent_scope.id}_{name}"

    if name not in screenState.screen_data["scopes"]:
        scope = Scope()
        scope.parent_scope = parent_scope
        parent_scope.sub_scopes[name] = scope
        screenState.screen_data["scopes"][name] = scope

    scope = screenState.screen_data["scopes"][name]
    if scope.active:
        scope.update_no_sub(len(menu_list))

    select = scope.cursor

    if figlet:

        s_height = FUTURE_FONT.height

        if scope.active:
            stdscr.addstr(point.y + len(menu_list) * s_height + 1, point.x, "H" * 10)
        elif scope.selected():
            stdscr.addstr(point.y + len(menu_list) * s_height + 1, point.x, "-" * 10)

        for i, item in enumerate(menu_list):
            if select == i:
                stdscr.attron(curses.color_pair(color_pairs_sel))
            else:
                stdscr.attron(curses.color_pair(color_pairs))
            text = (str(i) + " - " + str(item))
            s = TEXT.renderFont(text, FUTURE_FONT)
            for n, line in enumerate(s):
                stdscr.addstr(point.y + i * s_height + n, point.x, line)
    else:

        if scope.active:
            stdscr.addstr(point.y + len(menu_list) + 1, point.x, "H" * 10)
        elif scope.selected():
            stdscr.addstr(point.y + len(menu_list) + 1, point.x, "-" * 10)

        for i, item in enumerate(menu_list):
            if select == i:
                stdscr.attron(curses.color_pair(color_pairs_sel) | curses.A_BOLD)
            else:
                stdscr.attron(curses.color_pair(color_pairs) | curses.A_BOLD)
            stdscr.addstr(point.y + i, point.x, (str(i) + " - " + str(item)))


def screen_coin_wallet(stdscr, keyboardState, screenState: ScreenState, fullNodeState: FullNodeState):
    """ waooolllet """
    # rename Token wallet

    width = screenState.screen_size.x
    height = screenState.screen_size.y

    wallet_win = createFullSubWin(stdscr, screenState, height, width)
    wallet_win.bkgd(' ', curses.color_pair(screenState.colorPairs["body"]))

    # wallet
    pk: PkState = screenState.public_keys[screenState.active_pk[0]]
    wallets: Dict[int, WalletState] = pk.wallets
    finger = pk.fingerprint

    active_scope: Scope = screenState.activeScope
    main_scope = active_scope.main_scope
    tail = main_scope.data['tail']

    coin_wallet: WalletState = wallets[tail]
    pos = UIgraph.Point(0,0)
    P_text = screenState.colorPairs["body"]
    ELEMENTS.create_text_figlet(wallet_win, pos, SMALL_FONT, f"{coin_wallet.name} - {coin_wallet.ticker}", P_text)
    #ELEMENTS.create_text_figlet(wallet_win, pos, SMALL_FONT, f"Ticker: {coin_wallet.ticker} - {coin_wallet.name}", P_text)
    #pos += UIgraph.Point(0, SMALL_FONT.height + 1)
    #ELEMENTS.create_text_figlet(wallet_win, pos, STANDARD_FONT, f"Ticker: {coin_wallet.ticker} - {coin_wallet.name}", P_text)
    #pos += UIgraph.Point(0, STANDARD_FONT.height + 1)
    #ELEMENTS.create_text_figlet(wallet_win, pos, SMBLOCK_FONT, f"Ticker: {coin_wallet.ticker} - {coin_wallet.name}", P_text)
    tail_str = str(tail)
    if tail == XCH_FAKETAIL:
        tail_str = 'chia'

    tags = ['Ticker', 'Name', 'tail', 'confirmed balance', 'spendable balance', 'upnspent coin count', 'wallet block height']
    values = [
        coin_wallet.ticker,
        coin_wallet.name,
        tail_str,
        coin_wallet.confirmed_wallet_balance,
        coin_wallet.spendable_balance,
        coin_wallet.unspent_coin_count,
        coin_wallet.block_height]

    length1 = 30
    length2 = 20

    pos += UIgraph.Point(1, SMALL_FONT.height + 1)
    sel_col = (screenState.colorPairs['tab_soft'], screenState.colorPairs['tab_dark'])
    for i in range(len(tags)):
        P_col = sel_col[i % 2]
        text = ' ' + str(tags[i]) + (length1 - len(str(tags[i]))) * ' '
        ELEMENTS.create_text(wallet_win, pos, text, P_col, True)
        pos_t = pos + UIgraph.Point(20,0)
        text = ' ' + str(values[i]) + (length2 - len(str(values[i]))) * ' '
        #wallet_win.attron(curses.A_REVERSE)
        ELEMENTS.create_text(wallet_win, pos_t, text, P_col, True)
        pos += UIgraph.Point(0,1)
        #wallet_win.attroff(curses.A_REVERSE)

    # show coins by coin
    # coin record data
    #      "coin": {
    #    "amount": 1100,
    #    "parent_coin_info": "0x9cf871f0c36acda6f98f791fac46530267531d87b854d5b9165aeba0b6e68eda",
    #    "puzzle_hash": "0x3672ba488b54541bb2e3a4ba7f9bdcb31def750e07f584244d73e224b462f60e"
    #  },
    #  "coinbase": false,
    #  "confirmed_block_index": 6388435,
    #  "spent_block_index": 0,
    #  "timestamp": 1734944921

    screenState.scope_exec_args = [screenState]
    main_scope.update()

    menu_actions = ['contemplate', 'receive', 'send', 'manage']
    pos += UIgraph.Point(0,2)
    pos_menu_actions_button = pos.deepcopy()

    def menu_actions_button(only_init):
        return ELEMENTS.create_button_menu(stdscr, screenState, main_scope,
                                           "action menu", menu_actions.copy(),
                                           pos_menu_actions_button, only_init)

    menu_actions_scope: Scope = menu_actions_button(True)
    active_action = menu_actions[menu_actions_scope.cursor]

    # pos += UIgraph.Point(0,3)

    match active_action:
        case 'contemplate':
            ELEMENTS.create_text(wallet_win, UIgraph.Point(20,30), "booeeee", P_text, True)
            pos_buttons = pos + UIgraph.Point(len("action menu: ") + len(active_action) + 8, 0)
            menu_coins = ['coin by coin', 'by address', 'by transaction']

            def menu_coins_button(only_init):
                return ELEMENTS.create_button_menu(stdscr, screenState, main_scope,
                                                   "coin menu", menu_coins.copy(),
                                                   pos_buttons, only_init)

            menu_coins_scope: Scope = menu_coins_button(True)

            active_coin_view = menu_coins[menu_coins_scope.cursor]

            pos += UIgraph.Point(0,3)

            #ELEMENTS.create_text(wallet_win, UIgraph.Point(20,20), str(active_coin_view), P_text, True)
            #ELEMENTS.create_text(wallet_win, UIgraph.Point(10,20), "mono", P_text, True)

            match active_coin_view:
                case 'coin by coin':

                    coins_table_legend = [
                        'coin id',
                        'amount',
                        'address',
                        'confirmed block index',
                        'timestamp'
                    ]


                    ELEMENTS.create_text(wallet_win, pos, 'coin by coin', P_text, True)
                    coins_table = []
                    for c in coin_wallet.coins:
                        new_coin = []
                        coin = c['coin']
                        coin_id = 0
                        new_coin.append(coin_id)
                        new_coin.append(coin['amount'])
                        address = coin['puzzle_hash']
                        new_coin.append(address)
                        confirmed_block = c['confirmed_block_index']
                        new_coin.append(confirmed_block)
                        timestamp = datetime.fromtimestamp(c['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
                        new_coin.append(timestamp)

                        coins_table.append(new_coin)

                    if len(coin_wallet.coins) == 0:
                        coins_table.append([' '] * len(coins_table_legend))

                    tab_size = UIgraph.Point(width - 2, height - pos.y - 6)

                    ELEMENTS.create_tab(wallet_win,
                                        screenState,
                                        main_scope,
                                        "spendable_coins",
                                        coins_table,
                                        None,
                                        None,
                                        False,
                                        pos,
                                        tab_size,
                                        keyboardState,
                                        ScopeActions.exit_scope,
                                        False,
                                        False,
                                        coins_table_legend)

                case 'by address':
                    ELEMENTS.create_text(wallet_win, pos, 'coin by address', P_text, True)
                    pos += UIgraph.Point(0,1)
                    #for c in coin_wallet.coins:
                    #    c = c['coin']
                    #    c_text = f"pop coin {c['amount'] / mojo}, {c['puzzle_hash']}"
                    #    #c_text = f"coin {c.coin.amount}, {c.coin.puzzle_hash.hex()}"
                    #    ELEMENTS.create_text(wallet_win, pos, c_text, P_text, True)
                    #    #wallet_win.addstr(y, 10, c_text)
                    #    pos += UIgraph.Point(0,1)
                    #    ELEMENTS.create_text(wallet_win, pos, str(c), P_text, True)
                    #    pos += UIgraph.Point(0,1)
                    #    ELEMENTS.create_text(wallet_win, pos, str(c.keys()), P_text, True)
                    #    print("keys")
                    #    print(c)
                    #    print(c.keys())

                    # show coins by address
                    addresses_table_legend = [
                        'address',
                        'amount',
                        'number of coins',
                    ]

                    ELEMENTS.create_text(wallet_win, pos, 'list coins by address', P_text, True)
                    pos += UIgraph.Point(0,1)
                    addresses = {}
                    for c in coin_wallet.coins:
                        c = c['coin']
                        adx = c['puzzle_hash']
                        if adx in addresses:
                            addresses[adx].append(c['amount'])
                        else:
                            addresses[adx] = [c['amount']]
                    addresses_table = []
                    for i in addresses:
                        new_add = []
                        new_add.append(i)
                        new_add.append(sum(addresses[i]))
                        new_add.append(len(addresses[i]))

                        addresses_table.append(new_add)

                    if len(coin_wallet.coins) == 0:
                        addresses_table.append([' '] * len(addresses_table_legend))

                    ELEMENTS.create_tab(wallet_win,
                                        screenState,
                                        main_scope,
                                        "spendable_coins_add",
                                        addresses_table,
                                        None,
                                        None,
                                        False,
                                        pos,
                                        UIgraph.Point(60,10),
                                        keyboardState,
                                        ScopeActions.exit_scope,
                                        False,
                                        False,
                                        addresses_table_legend)
                case 'by transactions':
                    # for each tx:
                    # transaction id
                    # show to address: (real and not for cats)
                    # show amount
                    # show all addittion and removals

                    # show somewhere that transaction history is not deterministic and info can change
                    # if wallet is resynced. keep offer and transaction data somewhere

                    # we need nested table, to show all the inner data in a clear way 



                    # maybe later
                    # Transaction 7c0a73de82b4b0bffdbaef64a3c53064dede8b2fa9cad43fdb19a4c7179aa979
                    # Status: Confirmed
                    # Amount sent: 98 Spacebucks
                    # To address: xch1plygqsuv78z4fvqem2j5y34ja8q43sf0yy485qtlr7cjeyrcf4yqjun3jk
                    # Created at: 2025-05-01 11:50:12

                    # Transaction 6fec42dff0732393e80d5c91482acaced606a28ccd356f0456a883fef6502a03
                    # Status: Confirmed
                    # Amount sent: 99 Spacebucks
                    # To address: xch1plygqsuv78z4fvqem2j5y34ja8q43sf0yy485qtlr7cjeyrcf4yqjun3jk
                    # Created at: 2025-05-01 11:25:30

                    # Transaction aab16c799071bcf742684a626a5fa0a43319ef4d5cdc73ce6fd1a4899508590f
                    # Status: Confirmed
                    # Amount sent: 64000 Spacebucks
                    # To address: xch1ts9vg2fruyfqqasr0zyzlc3hzsajwhukvslcxpq999dnzwnswkqqsq8sej
                    # Created at: 2025-01-09 12:01:20
                    pass

            menu_coins_scope: Scope = menu_coins_button(False)

        case 'receive':
            #1 show last address
            # address | times used this asset | active coins | times used by any asset
            # address | times used | active coins
            text = "Last address: "
            ELEMENTS.create_text(wallet_win, pos, text, P_col, True)
            pos += UIgraph.Point(0,1)

            # load addresses using the chunkloader
            # the addressses it could be shared with all other cats and xch...
            # so what...?
            if 'address_loader' not in main_scope.data:
                conn = sqlite3.connect(DB_WDB, timeout=SQL_TIMEOUT)
                table_name = 'addresses'
                chunk_size = 12  # height * 2  # to be sure to have at least 2 full screen of data
                offset = 0  # start from 0
                finger = screenState.active_pk[0]
                pk_state_id = WDB.retrive_pk(conn, finger)[0]
                filters = {'pk_state_id': pk_state_id, 'hardened': False}
                main_scope.data['address_loader'] = WDB.DataChunkLoader(DB_WDB, table_name, chunk_size, offset, filters=filters)
                conn.close()

            data_chunk_loader: WDB.DataChunkLoader = main_scope.data['address_loader']

            ELEMENTS.create_tab(wallet_win,
                                screenState,
                                main_scope,
                                "addresses",
                                None,  # data_table => using chunk loader
                                None,
                                None,
                                False,
                                pos,
                                UIgraph.Point(60,10),
                                keyboardState,
                                ScopeActions.exit_scope,
                                False,
                                False,
                                None,  # addresses_table_legend,
                                data_chunk_loader)

            # conn creation should be more logic inside the update, so i can be 
            # created only when needed
            data_chunk_loader.update_loader()

            #2 show all address
            pass
        case 'send':
            text = "Reciving address: "
            ELEMENTS.create_text(wallet_win, pos, text, P_text, True)
            pos_ins = pos + UIgraph.Point(len(text), 5)
            pre_text = "add address: "
            ELEMENTS.create_prompt(wallet_win, screenState, keyboardState, main_scope, 'add', pos_ins,
                                   pre_text, 60, P_text, True, False)
            pos_ins += UIgraph.Point(0,1)
            pre_text = "add amount:  "
            ELEMENTS.create_prompt(wallet_win, screenState, keyboardState, main_scope, 'amount', pos_ins,
                                   pre_text, 60, P_text, True, False)
            pos_ins += UIgraph.Point(0,1)
            pre_text = "add fee:     "
            ELEMENTS.create_prompt(wallet_win, screenState, keyboardState, main_scope, 'fee', pos_ins,
                                   pre_text, 60, P_text, True, False)
            pos_ins += UIgraph.Point(0,3)


            ## test double
            text = "Reciving address: "
            ELEMENTS.create_text(wallet_win, pos_ins, text, 60, P_text, True)
            pos_ins = pos_ins + UIgraph.Point(len(text), 0)
            pre_text = "add address: "
            ELEMENTS.create_prompt(wallet_win, screenState, keyboardState, main_scope, 'addd', pos_ins,
                                   pre_text, 60, P_text, True, False)
            pos_ins += UIgraph.Point(0,2)
            pre_text = "add amount:  "
            ELEMENTS.create_prompt(wallet_win, screenState, keyboardState, main_scope, 'amountt', pos_ins,
                                   pre_text, 60, P_text, True, False)
            pos_ins += UIgraph.Point(0,2)
            pre_text = "add fee:     "
            ELEMENTS.create_prompt(wallet_win, screenState, keyboardState, main_scope, 'feee', pos_ins,
                                   pre_text, 60, P_text, True, False)
            pos_ins += UIgraph.Point(0,2)
            pass
            # show the filling fields
            # add menu to chose auto or manual coin selection toggle
            # if manual, add two tables, one for selection and one for selected
        case 'manage':
            pass
            # option to split or merge

    menu_actions_scope: Scope = menu_actions_button(False)



    #send_button_text = "Send"
    #send_button = ELEMENTS.create_button(stdscr, screenState, main_scope, send_button_text, pos)

    #pos_buttons = pos + UIgraph.Point(len(send_button_text) + 8, 0)
    #receive_button_text = "Receive"
    #receive_button = ELEMENTS.create_button(stdscr, screenState, main_scope, receive_button_text, pos_buttons)

    #pos_buttons += UIgraph.Point(len(receive_button_text) + 8, 0)
    #transactions_button_text = "Transactions"
    #transactions_button = ELEMENTS.create_button(stdscr, screenState, main_scope, 
    #                                            transactions_button_text, pos_buttons)






    #ELEMENTS.create_text(wallet_win, pos, f"len of the adds: {len(addresses)}", P_text, True)
    pos += UIgraph.Point(0,1)
    #for k, amounts in addresses.items():
    #    add_text = f"address: {k}, amount: {sum(amounts) / mojo}, n. coins: {len(amounts)}"
    #    ELEMENTS.create_text(wallet_win, pos, add_text, P_text, True)
    #    pos += UIgraph.Point(0,1)

    #ELEMENTS.create_text(wallet_win, pos, f"list of transactions", P_text, True)
    pos += UIgraph.Point(0,1)
    # show coins by address
    for t in coin_wallet.transactions:
        #wallet_win.addstr(y, 10, f"address: {t.to_puzzle_hash}, amount: {str(t.amount)}, n. type: {t.name}")
        pass
    # interface
    # button to select the visualization: transactions, coins, addresses


def screen_fingers(stdscr, keyboardState, screenState, fullNodeState: FullNodeState):

    width = screenState.screen_size.x
    height = screenState.screen_size.y

    wallet_win = createFullSubWin(stdscr, screenState, height, width)
    wallet_win.bkgd(' ', curses.color_pair(screenState.colorPairs["body"]))

    activeScope = screenState.activeScope
    screenState.scope_exec_args = [screenState]

    handler = screen_wallet
    for finger in screenState.public_keys:
        if finger not in screenState.scopes:
            newScope = Scope(finger, handler, screenState)
            newScope.exec = ScopeActions.activate_scope_and_set_pk
            newScope.parent_scope = activeScope
            activeScope.sub_scopes[finger] = newScope

    fingers_str = []
    for finger in activeScope.sub_scopes:
        pk_state: PkState = screenState.public_keys[finger]
        fing_name = str(finger) + " - " + pk_state.label
        if finger == screenState.active_pk[0]:
            fingers_str.append(f"{fing_name} >")
        else:
            fingers_str.append(fing_name)

    activeScope.update()

    menu_size_xy = [0, 0]
    for f in fingers_str:
        sizeX, sizeY = TEXT.sizeText(f, FUTURE_FONT)
        menu_size_xy[1] += sizeY
        if menu_size_xy[0] < sizeX:
            menu_size_xy[0] = sizeX

    # base_point_menu: UIgraph.Point = None
    figlet_bool = None
    if menu_size_xy[0] < width / 2 and menu_size_xy[1] < height / 2:
        figlet_bool = True
    else:
        figlet_bool = False

    # change immision point to Point
    wallet_win.addstr(8, 10, "select fingerprint:")
    wallet_win.addstr(9, 10, u'\u2594' * 19)
    menu_select(wallet_win, fingers_str, activeScope.cursor,
                [10, 10], screenState.colorPairs['body'], screenState.colorPairs["body_sel"],
                figlet_bool)

    # if no chia node/wallet are active next step give an error
    # implent user message no node. Maybe finally is processed only if no exception
    # arise select = select % len(screenState.public_keys)


def screen_wallet(stdscr, keyboardState, screenState: ScreenState, fullNodeState: FullNodeState):

    width = screenState.screen_size.x
    height = screenState.screen_size.y

    wallet_win = createFullSubWin(stdscr, screenState, height, width)
    wallet_win.bkgd(' ', curses.color_pair(screenState.colorPairs["body"]))

    #spacescan query
    #https://api-fin.spacescan.io/cats?version=0.1.0&network=mainnet&page=2&count=100

    try:
        active_scope: Scope = screenState.activeScope
        main_scope: Scope = active_scope.main_scope
        screenState.scope_exec_args = [screenState]

        # wallet
        finger = main_scope.name
        pk: PkState = screenState.public_keys[finger]
        wallets: Dict[int, WalletState] = pk.wallets
        finger = pk.fingerprint

        #info to dispaly
        #ifnger public key and to right, totatal value of the wallet, usd, xch
        #new all the coin, short name | graph | balance | usd value | xch value |
        #SINGLE -> red or green price with the variation of the week

        margin = 3
        pos = UIgraph.Point(margin, 1)

        # WALLET VALUE
        xch_amount = "xch 1230.43"
        btc_amount = "BTC 0.44321"
        usd_amount = "$ 23.234.38"

        items = [xch_amount, btc_amount, usd_amount]
        item_colors = ['xch', 'btc', 'dollar']
        spaces = 2
        pre_text = "Total wallet value: "

        P_text = screenState.colorPairs["body"]
        ELEMENTS.create_text(wallet_win, pos, pre_text, P_text, True)

        pos_values = pos + UIgraph.Point(len(pre_text) + 2 * spaces, 0)
        length = 0
        for item in items:
            length += len(item) + 2 * spaces

        for item, item_color in zip(items, item_colors):
            length = len(item) + 2 * spaces

            text_color_pair = UIgraph.customColorsPairs_findByValue(
                screenState.cursesColors,
                screenState.colorPairs[item_color])
            text_color_background = text_color_pair[1]
            default_background = UIgraph.customColors_findByValue(
                screenState.cursesColors,
                screenState.colors["background"])

            new_pair = (text_color_background, default_background)
            P_frame = UIgraph.addCustomColorTuple(
                new_pair,
                screenState.cursesColors
            )
            P_text = screenState.colorPairs[item_color]

            if False:
                ELEMENTS.create_text_double_space(
                    wallet_win, pos_values, f"  {item}  ", P_text,
                    P_frame, 3, True)
                pos_values += UIgraph.Point(length + 2, 0)
            else:
                #pos_t = pos_values + UIgraph.Point(0, 1)
                ELEMENTS.create_text(wallet_win, pos_values, f"  {item}  ", P_text, True)
                pos_values += UIgraph.Point(length, 0)

        # OPTION BURTONS

        # pos += UIgraph.Point(0,2)
        #button_graph = ELEMENTS.create_button(stdscr, screenState, main_scope,
        #                                      "Graph mode", pos)

        # CHIA WALLET DATA
        chia_wallet = wallets[XCH_FAKETAIL]
        chia_ticker = chia_wallet.ticker
        chia_balance = chia_wallet.confirmed_wallet_balance
        chia_coins_data: CoinPriceData = CoinPriceData()
        try:
            chia_coins_data = screenState.coins_data[XCH_FAKETAIL]
        except:
            logging(debug_logger, "DEBUG", f'still no coin data for {chia_ticker}')
        chia_current_price_currency = chia_coins_data.current_price_currency
        chia_historic_price_currency = chia_coins_data.historic_price_currency

        pre_text = "Chia wallet:"
        pos += UIgraph.Point(0,2)
        P_text = screenState.colorPairs["body"]
        ELEMENTS.create_text(wallet_win, pos, pre_text, P_text, True)

        P_chia = screenState.colorPairs["tab_soft"]
        P_chia_bg = screenState.colorPairs["tab_soft_bg"]
        data_table_legend = [
            "XCH Balance",
            "BTC price",
            "BTC 7d %",
            "USD price",
            "USD 7d %",
            "BTC value",
            "USD value"]

        btc_coin_data: CoinPriceData = screenState.coins_data[BTC_FAKETAIL]
        btc_current_price_currency = btc_coin_data.current_price_currency
        btc_historic_price_currency = btc_coin_data.historic_price_currency
        chia_current_price_btc = chia_current_price_currency / btc_current_price_currency

        chia_historic_price_btc = convert_historic_price_to_currency(
            list(btc_historic_price_currency.keys()), list(btc_historic_price_currency.values()),
            list(chia_historic_price_currency.keys()), list(chia_historic_price_currency.values()),
            True)

        hpc_keys = list(chia_historic_price_currency.keys())  # timestamps
        hpb_keys = list(chia_historic_price_btc.keys())  # timestamps
        chia_historic_price_currency_graph = []
        chia_historic_price_currency_table = [1,0]
        if len(hpc_keys) > 0:
            chia_historic_price_currency_graph = chia_historic_price_currency.copy()
            chia_historic_price_currency_table = [
                chia_historic_price_currency[hpc_keys[0]],
                chia_historic_price_currency[hpc_keys[-1]]]
            chia_historic_price_btc_table = [
                chia_historic_price_btc[hpb_keys[0]],
                chia_historic_price_btc[hpb_keys[-1]]]
        data_table = [[
            chia_balance,
            chia_current_price_btc,  # btc
            chia_historic_price_btc_table,  # btc
            chia_current_price_currency,
            chia_historic_price_currency_table,
            chia_balance * chia_current_price_btc,
            chia_balance * chia_current_price_currency]]

        transposed_table = [[row[i] for row in data_table] for i in range(len(data_table[0]))]
        data_table = transposed_table

        color_up = screenState.colors['azure_up']
        color_down = screenState.colors['white_down']
        format_funcs = [
            [(ft_standar_number_format, [], {'sig_digits': 5, 'max_size': 10})],
            [(ft_standar_number_format, [5,10], {})],
            [
                (ft_price_trend, [], {}),
                (ft_percentage_move, [color_up, color_down], {})
            ],
            [(ft_standar_number_format, [], {'sig_digits': 5, 'max_size': 10})],
            [
                (ft_price_trend, [], {}),
                (ft_percentage_move, [color_up, color_down], {})
            ],
            [(ft_standar_number_format, [], {'sig_digits': 5, 'max_size': 10})],
            [(ft_standar_number_format, [], {'sig_digits': 5, 'max_size': 10})],
        ]
        data_table, data_table_color = format_tab(data_table, format_funcs)

        # chia tab
        pos += UIgraph.Point(0,2)
        ELEMENTS.create_tab_large(
            wallet_win, screenState, main_scope,
            "chia_data", data_table, [XCH_FAKETAIL], data_table_color, False,
            pos, UIgraph.Point(150,6), keyboardState, "chia_data", 2,
            open_coin_wallet, False, False, data_table_legend)

        #if button_graph.bool and False: # never graph
        if False:

            pos += UIgraph.Point(0,7)
            graph_height = 8
            graph_win = wallet_win.subwin(graph_height, width - 8, pos.y, pos.x)  # y, x
            graph_win.bkgd(' ', curses.color_pair(screenState.colorPairs["tab_dark_bg"]))
            graph_win.erase()
            prices = list(chia_historic_price_currency_graph.values())
            timestamp = list(chia_historic_price_currency_graph.keys())
            if len(prices) < 1:
                prices = [chia_current_price_currency]
                timestamp = [chia_coins_data.current_price_date]
            #wallet_win.addstr(pos.y, 10, f"the cat is: {prices}")
            #debug_win.addstr(y0 + 1,70, f"len: {len(prices)}; time {timestamp[0]} and prices; {prices[0]}")
            #prices, timestamp = DEX.getHistoricPriceFromTail(cat, 7)
            C_soft_background = screenState.colors["tab_soft"]
            C_dark_background = screenState.colors["tab_dark"]
            C_graph = UIgraph.addCustomColorTuple(
                (color_up, C_soft_background),
                screenState.cursesColors)
            UIgraph.drawPriceGraph(graph_win, screenState, prices, timestamp, 7, C_graph)
            # create chia graph
            pos += UIgraph.Point(0,graph_height)
        else:
            pos += UIgraph.Point(0,6)

        # CAT WALLET DATA
        tickers = []
        balances = []
        current_prices_xch = []
        historic_prices_xch = []
        current_prices_currency = []
        historic_prices_currency = []
        total_values_xch = []
        total_values_currency = []

        for wallet_dicKey in wallets:
            if wallet_dicKey == XCH_FAKETAIL:
                continue
            wallet = wallets[wallet_dicKey]
            tickers.append(wallet.ticker)
            balances.append(wallet.confirmed_wallet_balance)
            cat_coins_data: CoinPriceData = CoinPriceData()
            try:
                cat_coins_data = screenState.coins_data[wallet_dicKey]
            except:
                logging(debug_logger, "DEBUG", f'still no coin data for {wallet.ticker}')
            current_prices_xch.append(cat_coins_data.current_price)
            historic_prices_xch.append(cat_coins_data.historic_price)
            current_prices_currency.append(cat_coins_data.current_price_currency)
            historic_prices_currency.append(cat_coins_data.historic_price_currency)
            try:
                xch_value = wallet.confirmed_wallet_balance * cat_coins_data.current_price
                total_values_xch.append(xch_value)
                total_values_currency.append(xch_value * chia_current_price_currency)
            except:
                logging(debug_logger, "DEBUG", f'still no coin data for {wallet.ticker} or {chia_ticker}')
                total_values_xch.append(None)
                total_values_currency.append(None)

        ###### TEMP mod to have only first and last value if the history #####
        # next we have to create the alternarive view with the full graph or
        # simple number
        # make only the first and the last value for the hisotric data
        # maybe it was better to have 2 list for the historic prices
        historic_prices_xch_graph = historic_prices_xch.copy()
        historic_prices_xch_tab = []  # prices for the 7d percentage move
        historic_ts_xch_tab = []

        # prepare data for the percentage move
        for hpx in historic_prices_xch:
            if hpx is not None and len(hpx) > 1:
                hpx_keys = list(hpx.keys())
                hpx = [hpx[hpx_keys[0]], hpx[hpx_keys[-1]]]
                historic_prices_xch_tab.append(hpx)
                historic_ts_xch_tab.append([hpx_keys[0], hpx_keys[-1]])
            else:
                historic_prices_xch_tab.append([])
                historic_ts_xch_tab.append([])

        historic_prices_currency_tab = []  # prices for the 7d percentage move
        historic_prices_currency_graph = historic_prices_currency.copy()
        historic_ts_currency_tab = []

        for hpc in historic_prices_currency:
            if hpc is not None and len(hpc) > 1:
                hpc_keys = list(hpc.keys())
                hpc = [hpc[hpc_keys[0]], hpc[hpc_keys[-1]]]
                historic_prices_currency_tab.append(hpc)
                historic_ts_currency_tab.append([hpc_keys[0], hpc_keys[-1]])
            else:
                historic_prices_currency_tab.append([])
                historic_ts_currency_tab.append([])

        ### CAT TABLE FORMATTING
        dataTable = [tickers, balances, current_prices_xch, historic_prices_xch_tab,
                     current_prices_currency, historic_prices_currency_tab,
                     total_values_xch, total_values_currency]

        color_up = screenState.colors['azure_up']
        color_down = screenState.colors['white_down']
        format_funcs = [
            [(ft_standar_number_format, [], {'sig_digits': 5, 'max_size': 10})],
            [(ft_standar_number_format, [], {'sig_digits': 5, 'max_size': 10})],
            [(ft_standar_number_format, [5,10], {})],
            [
                (ft_price_trend, [], {}),
                (ft_percentage_move, [color_up, color_down], {})
            ],
            [(ft_standar_number_format, [], {'sig_digits': 5, 'max_size': 10})],
            [
                (ft_price_trend, [], {}),
                (ft_percentage_move, [color_up, color_down], {})
            ],
            [(ft_standar_number_format, [], {'sig_digits': 5, 'max_size': 10})],
            [(ft_standar_number_format, [], {'sig_digits': 5, 'max_size': 10})],
        ]
        dataTable, data_table_color = format_tab(dataTable, format_funcs)

        data_table_legend = ["Symbol",
                             "Balance",
                             "XCH price",
                             "XCH 7d %",
                             "USD price",
                             "USD 7d %",
                             "XCH value",
                             "USD value"]
        pre_text = "CAT wallets:"
        wallet_win.addstr(pos.y + 1, pos.x, pre_text, curses.A_BOLD)

        try:
            ### add row with all the value of the portfolio, btc, xch, usd
            ### create some frame for it?
            ###
            ### add button to chose currency BTC or USD and
            ### visualization (auto, small, big)
            ###
            ### add chia line with frame
            ###
            ### add tab with frame
            data_table_keys = list(wallets.keys())
            # pop 'chia', it should the first one
            data_table_keys.pop(0)
            main_scope.update()

            pos += UIgraph.Point(0,3)
            tab_size = UIgraph.Point(width - 2, height - pos.y - 6)
            #if not button_graph.bool:
            if True:
                ELEMENTS.create_tab(wallet_win,
                                    screenState,
                                    main_scope,
                                    "coins_data",
                                    dataTable,
                                    data_table_keys,
                                    data_table_color,
                                    True,
                                    pos,
                                    tab_size,
                                    keyboardState,
                                    ScopeActions.open_coin_wallet,
                                    True,
                                    False,
                                    data_table_legend)
            else:
                row_size = 5
                ELEMENTS.create_tab_large(
                    wallet_win, screenState, main_scope, "coins_data", dataTable,
                    data_table_keys, data_table_color, False, pos,
                    tab_size, keyboardState, "coins_data", row_size, open_coin_wallet,
                    True, False, data_table_legend, historic_prices_currency_graph)

            #debug
            #wallet_win.addstr(31, 10, f"cursor: {str(active_scope.cursor)}")
            #wallet_win.addstr(32, 10, f"altro: {str(active_scope.cursor)}")
            #wallet_win.addstr(33, 10, f"fine keybot: {str(active_scope.cursor)}")
            #wallet_win.addstr(34, 10, f"n. sub scopes: {str(len(main_scope.sub_scopes))}")

        except Exception as e:
            wallet_win.addstr(0, 0, "still loading wallet data")
            print("wallet tab creation failed")
            print(e)
            traceback.print_exc()

    except Exception as e:
        print("wallet failed")
        print(e)
        traceback.print_exc()

        #    {'success': True, 'chia_wallet_balance': {'confirmed_wallet_balance': 130, 'fingerprint': 291595168, 'max_send_amount': 130, 'pending_change': 0, 'pending_coin_removal_count': 0,
        #                                         'spendable_balance': 130, 'unconfirmed_chia_wallet_balance': 130, 'unspent_coin_count': 3, 'wallet_id': 1, 'wallet_type': 0}


def ft_standar_number_format(num, sig_digits, max_size):
    """Function to format a number. It gives None for the color info"""
    if isinstance(num, float):
        num = DEX.format_and_round_number(num, sig_digits, max_size)
        return str(num), None
    return str(num), None


def ft_percentage_move(move, color_up, color_down):
    """Function to format price variation"""
    if isinstance(move, float) or isinstance(move, int):
        move_str = DEX.format_and_round_number(move * 100, 3, 4)
        if move < 0:
            return f"{str(move_str)}%", color_down
        return f"{str(move_str)}%", color_up
    return f"{str(move)}%", color_down


def ft_price_trend(prices):
    """Take a list of two price and calculate the diff %"""
    if len(prices) > 1:
        move = (prices[1] - prices[0]) / prices[0]
        return move, None
    return "--", None


def format_tab(data_table, column_format_function):
    """To format some data in a column. The list column_format_function is a list
    compose of a list of tuples: [(function1, [args], {kwargs}), (function2, ...)]
    The data_table is organized in column
    It return the data change and also a table with the colors for each cell"""
    data_table_color = []
    data_table_new = []
    cc = 0
    for col, funcs in zip(data_table, column_format_function):
        col_color = [None] * len(col)
        col_new = [None] * len(col)
        for func, args, kwargs in funcs:
            for i, data in enumerate(col):
                data_new, color = func(data, *args, **kwargs)
                col_color[i] = color
                col_new[i] = data_new
            col = col_new
        data_table_color.append(col_color)
        data_table_new.append(col_new)
        cc += 1

    return data_table_new, data_table_color


def create_tab(scr, screenState: ScreenState, parent_scope: Scope, name: str,
               dataTable, data_table_keys: List[str], data_table_color,
               transpose: bool, position: UIgraph.Point, size: UIgraph.Point,
               keyboardState, tabName, sub_scope_activation, active=False, multipleSelection=False,
               data_table_legend=None):
    """Create a beautiful and shining tab
    dataTable: 2dim data list
    data_table_keys: key used when something is selected
    active: if we can select elements"""

    win_width = screenState.screen_size.x
    win_height = screenState.screen_size.y

    name = f"{parent_scope.id}_{name}"

    if name not in screenState.scopes:
        scope = Scope(name, parent_scope.screen, screenState)
        scope.parent_scope = parent_scope
        scope.main_scope = parent_scope
        scope.exec = ScopeActions.activate_scope
        scope.base_point = position
        parent_scope.sub_scopes[name] = scope

#        # create a child to create another window
#        # probably it should be something that we define outside
#        # this function because it change every time
        child_name = name + "temp_child"
        child_scope = Scope(child_name, None, screenState)

        child_scope.exec = open_coin_wallet
        child_scope.parent_scope = scope

        scope.sub_scopes[child_name] = child_scope

    scope = screenState.scopes[name]
    tab_scope_is_active = False
    scope_exec_args = [screenState]
    if scope is screenState.activeScope:
        scope.update_no_sub(len(dataTable[0]))
        screenState.scope_exec_args = scope_exec_args
        tab_scope_is_active = True

    ### end scope stuff ####

    ### tab geometry
    pos_x = position.x
    pos_y = position.y
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
                u = DEX.format_and_round_number(u, 5, 10)
                col_str.append(str(u))
            else:
                col_str.append(str(u))
        data_table_table_str.append(col_str)

    dataTable = data_table_table_str

    # curse customs colors
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

    table_bk_colors = [C_soft_background, C_dark_background]  # these is not a pair
    table_color_pairs = [P_soft, P_dark]


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
    rows_number = y_tabSize - height_low_bar - height_legend

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
    max_table_width = win_width - position.x - 3  # maybe add a global for borders
    x_tabSize = max_table_width

    table = scr.subwin(y_tabSize, x_tabSize, pos_y, pos_x)
    table.bkgd(' ', curses.color_pair(P_win_background))

    # selection
    if scope.selected():
        scr.addstr(pos_y + y_tabSize - 1, pos_x, u'\u2580' * x_tabSize,
                   curses.color_pair(P_win_selected))
        scr.addstr(pos_y + y_tabSize - 1, pos_x + x_tabSize, u'\u2598',
                   curses.color_pair(P_win_selected))
        for i in range(y_tabSize):
            scr.addstr(pos_y + i - 1, pos_x + x_tabSize, u'\u258c',
                       curses.color_pair(P_win_selected))

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
        P_current_attron = curses.color_pair(table_color_pairs[row % 2])
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
            if data_idx in screenState.screen_data[tabName]['idx_selected']:
                P_current_attron = curses.color_pair(P_selected)
                C_custom_bk = screenState.colors["chia_green"]
                table.attron(P_current_attron)
                table.addstr(data_idx, 0, ' ' * (x_tabSize))
                table.addstr(row, 1, u' \u25A0')
            else:
                table.addstr(row, 1, u' \u25A1')

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


def screen_tabs(stdscr, keyboardState, screenState: ScreenState, fullNodeState: FullNodeState, figlet=False):

    width = screenState.screen_size.x
    height = screenState.screen_size.y

    debug_win = createFullSubWin(stdscr, screenState, height, width)
    debug_win.bkgd(' ', curses.color_pair(screenState.colorPairs["body"]))

    active_scope: Scope = screenState.activeScope
    main_scope: Scope = active_scope.main_scope
    screenState.scope_exec_args = [screenState]
    main_scope.update()

    legend = ["bab", "okment", "t-1"]

    color_up = screenState.colors['azure_up']
    color_down = screenState.colors['white_down']
    format_funcs = [
        [(ft_standar_number_format, [], {'sig_digits': 5, 'max_size': 10})],
        [(ft_percentage_move, [color_up, color_down], {})],
        [(ft_standar_number_format, [], {'sig_digits': 5, 'max_size': 10})]
    ]
    theListTranspose = [[row[i] for row in theList]
                        for i in range(len(theList[0]))]
    theListTranspose, theListTransposeColor = format_tab(theListTranspose, format_funcs)

    theListColor = [[row[i] for row in theListTransposeColor]
                    for i in range(len(theListTransposeColor[0]))]

    active = False
    create_tab(debug_win, screenState, main_scope,
               "tab_a", theList, None, theListColor, True,
               UIgraph.Point(10,5), UIgraph.Point(150,10),
               keyboardState, "test_tabs", active, False, legend)

    create_tab(debug_win, screenState, main_scope,
               "tab_b", theList2, None, None, True,
               UIgraph.Point(15,19), UIgraph.Point(100,8),
               keyboardState, "test_tabs_small", active, False, legend)

    create_tab(debug_win, screenState, main_scope,
               "tab_c", theList2, None, None, True,
               UIgraph.Point(20,30), UIgraph.Point(50,8),
               keyboardState, "test_tabs_small", active, False, legend)


def screen_harvester():
    pass


def factory_menu(menu_items, stdscr, keyboardState, screenState, fullNodeState: FullNodeState, figlet=False):
    """TODO: move scope creation here? -> menu_items: is a list of tuple (name: str, called_function: callable,
    scope_action callable(scope), keyboard_exec callable)"""
    # use dexy logic for infine loop
    width = screenState.screen_size.x
    height = screenState.screen_size.y

    factory_win = createFullSubWin(stdscr, screenState, height, width)
    factory_win.bkgd(' ', curses.color_pair(screenState.colorPairs["body"]))

    #test_win = createFullSubWin(stdscr, screenState, height // 2, width // 2)
    test_win = createFullSubWin(stdscr, screenState, height, width)
    test_win.bkgd(' ', curses.color_pair(screenState.colorPairs["header"]))


    activeScope: Scope = screenState.activeScope
    screenState.scope_exec_args = [screenState]

    # TODO it always active?
    if activeScope is screenState.activeScope:
        activeScope.update(visibility_filter=False)
    screenState.selection = activeScope.cursor

    # where we are: the name of this menu with its number in the parent menu, as the item is
    # written there ("2 - lists"), in a mid gray; none on the main menu
    title = ''
    if activeScope.name not in ('main_menu', 'intro'):
        siblings = list(activeScope.parent_scope.sub_scopes) if activeScope.parent_scope is not None else []
        title = (f"{siblings.index(activeScope.name)} - {activeScope.name}" if activeScope.name in siblings
                 else activeScope.name)
    C_mid_gray = UIgraph.addCustomColor((140, 141, 137), screenState.cursesColors)  # between gray and dark_gray
    P_title = UIgraph.addCustomColorTuple((C_mid_gray, screenState.colors['background']), screenState.cursesColors)

    # new menu
    menu_select_def(test_win, activeScope, list(activeScope.sub_scopes.keys()),
                    screenState.colorPairs['body'], screenState.colorPairs["body_sel"],
                    align_h=1, align_v=1, prefix=True, title=title, P_title=P_title)


def screen_sb_watch_later(stdscr, keyboardState, screenState, fullNodeState: FullNodeState, figlet=False):

    # delete screenState size dimension? and get them from stdscr? why two places?
    width = screenState.screen_size.x
    height = screenState.screen_size.y

    sb_win = createFullSubWin(stdscr, screenState, height, width)
    sb_win.bkgd(' ', curses.color_pair(screenState.colorPairs["body"]))

    active_scope: Scope = screenState.activeScope
    main_scope: Scope = active_scope.main_scope
    screenState.scope_exec_args = [screenState]

    P_text = screenState.colorPairs['tab_soft']
    P_watch = screenState.colorPairs['error']
    pos = UIgraph.Point(12,2)
    ELEMENTS.create_text(sb_win, pos, "WATCH LATER", P_watch, bold=True)

    ### test to load asyncronusly with a thread launched locally
    if 'watch_later_cache' not in main_scope.data:
        main_scope.data['watch_later_cache'] = []

    def load_watch_later(thread_db_lock, sleep=0):
        time.sleep(sleep)
        conn = sqlite3.connect(DB_SB, timeout=SQL_TIMEOUT)
        bundles = WDB.load_spend_bundles(conn, group_name='watch later') or []
        # a pending bundle can be confirmed or lost since the last check
        for bundle in bundles:
            if bundle.status == 'pending':
                result = WDB.refresh_bundle_status(conn, bundle.id)
                if result:
                    bundle.status, bundle.block_height = result
        with thread_db_lock:
            main_scope.data['watch_later_cache'] = bundles
        conn.close()

    if 'thread_db_lock' not in main_scope.data:
        main_scope.data['thread_db_lock'] = threading.Lock()
    thread_db_lock = main_scope.data['thread_db_lock']

    if 'thread_db' not in main_scope.data:
        main_scope.data['thread_db'] = threading.Thread(target=load_watch_later, args=(thread_db_lock,), daemon=True)
        main_scope.data['thread_db'].start()
    thread_db = main_scope.data['thread_db']

    if not thread_db.is_alive():
        sleep = 10  # seconds
        main_scope.data['thread_db'] = threading.Thread(target=load_watch_later, args=(thread_db_lock, sleep), daemon=True)
        main_scope.data['thread_db'].start()
        screenState.running_threads.append(main_scope.data['thread_db'])


    with thread_db_lock:
        watch_later_bundles = main_scope.data['watch_later_cache']

    legend = ["id", "sql-id", "transaction id", "saved at", "status", "height"]


    P_text = screenState.colorPairs['tab_soft']
    pos = UIgraph.Point(3,23)
    tab_size = UIgraph.Point(width - 2, height - pos.y - 6)


    def bundle_state_to_table(bundle_states: list[WDB.BundleState]):

        if len(bundle_states) == 0:
            return [], None

        sps = []
        sb_names = []

        for n, sp in enumerate(bundle_states):
            sp_t = []
            sp_t.append(n)
            sp_t.append(sp.id)
            sp_t.append(sp.spend_bundle_hash)
            sp_t.append(datetime.fromtimestamp(sp.timestamp))
            sp_t.append(sp.status)
            sp_t.append('' if sp.block_height is None else f"{sp.block_height:,}")
            sps.append(sp_t)
            sb_names.append(sp.spend_bundle_hash)

        return sps, sb_names


    watch_later_bundles, sb_names = bundle_state_to_table(watch_later_bundles)


    main_scope.update()
    tab_scope = ELEMENTS.create_tab(sb_win,
                                    screenState,
                                    main_scope,  # main_scope
                                    "sb_watch_later",
                                    watch_later_bundles,
                                    sb_names,
                                    None,
                                    False,
                                    pos,
                                    tab_size,
                                    keyboardState,
                                    ScopeActions.open_transaction,
                                    True,
                                    False,
                                    legend)




def screen_sb_archive(stdscr, keyboardState, screenState, fullNodeState: FullNodeState, figlet=False):

    # delete screenState size dimension? and get them from stdscr? why two places?
    width = screenState.screen_size.x
    height = screenState.screen_size.y

    sb_win = createFullSubWin(stdscr, screenState, height, width)
    sb_win.bkgd(' ', curses.color_pair(screenState.colorPairs["body"]))

    active_scope: Scope = screenState.activeScope
    main_scope: Scope = active_scope.main_scope
    screenState.scope_exec_args = [screenState]

    archive_loader = fullNodeState.spend_bundle_archive_loader

    attrs = {
        "id": "id",
        "sql-id": "id",
        "transaction id": "spend_bundle_hash",
        "timestamp": "timestamp"
    }

    legend = []
    for key, attribute in attrs.items():
        legend.append(key)


    P_text = screenState.colorPairs['tab_soft']
    pos = UIgraph.Point(3,23)
    tab_size = UIgraph.Point(width - 2, height - pos.y - 6)

    def bundle_state_to_table(bundle_states: list[WDB.BundleState]):
        sps = []
        sp_names = []

        for n, sp in enumerate(bundle_states):
            sp_t = []
            sp_t.append(n)
            sp_t.append(sp.id)
            sp_t.append(sp.spend_bundle_hash)
            sp_t.append(datetime.fromtimestamp(sp.timestamp))
            sps.append(sp_t)
            sp_names.append(sp.spend_bundle_hash)

        return sps, sp_names



    main_scope.update()
    tab_scope = ELEMENTS.create_tab(sb_win,
                                    screenState,
                                    main_scope,  # main_scope
                                    "sb_archive",
                                    None,
                                    None,
                                    None,
                                    False,
                                    pos,
                                    tab_size,
                                    keyboardState,
                                    ScopeActions.open_transaction,
                                    True,
                                    False,
                                    legend,
                                    archive_loader,
                                    bundle_state_to_table)

    #archive_loader.update_offset(tab_scope.cursor)
    archive_loader.start_updater_thread()


def screen_spend_bundles(stdscr, keyboardState, screenState, fullNodeState: FullNodeState, figlet=False):
    menu_items = [
        ('watch later', screen_sb_watch_later, ScopeActions.activate_scope, None),
        # archive: off until FullNodeState creates spend_bundle_archive_loader again
        # ('archive', screen_sb_archive, ScopeActions.activate_scope, None),
        ('mempool', screen_mempool, ScopeActions.activate_scope, None)
    ]

    active_scope: Scope = screenState.activeScope
    if len(active_scope.sub_scopes) == 0:
        for name, handler, exec_fun, exec_key in menu_items:
            new_scope: Scope = Scope(name, handler, screenState)
            new_scope.exec = exec_fun
            new_scope.parent_scope = active_scope
            active_scope.sub_scopes[name] = new_scope
            if exec_key:
                new_scope.keyboard_exec = exec_key

    factory_menu(menu_items, stdscr, keyboardState, screenState, fullNodeState, figlet=False)


def screen_full_node(stdscr, keyboardState, screenState, fullNodeState: FullNodeState, figlet=False):

    if DEBUGGING:
        menu_items = [
            ('blocks', screen_blocks, ScopeActions.activate_scope, None),
            ('mempool', screen_mempool, ScopeActions.activate_scope, None),
            ('spend bundles', screen_spend_bundles, ScopeActions.activate_scope, None)
        ]
    else:
        menu_items = [
            ('blocks', screen_blocks, ScopeActions.activate_scope, KEYBOARD.block_band_execution),
            ('blocks and vdf chains', screen_blocks_vdf, ScopeActions.activate_scope, KEYBOARD.block_band_execution),
            ('mempool', screen_mempool, ScopeActions.activate_scope, None),
            ('search puzzles and addresses', screen_full_node_search, ScopeActions.activate_scope, None),
            ('address_watchlist', screen_address_watchlist, ScopeActions.activate_scope, None),
            ('reorgs', screen_reorgs, ScopeActions.activate_scope, None),
            ('log heat map', screen_log_heatmap, ScopeActions.activate_scope, None),
        ]

    active_scope: Scope = screenState.activeScope
    if len(active_scope.sub_scopes) == 0:
        for name, handler, exec_fun, exec_key in menu_items:
            new_scope: Scope = Scope(name, handler, screenState)
            new_scope.exec = exec_fun
            new_scope.parent_scope = active_scope
            active_scope.sub_scopes[name] = new_scope
            if exec_key:
                new_scope.keyboard_exec = exec_key

    factory_menu(menu_items, stdscr, keyboardState, screenState, fullNodeState, figlet=False)


class AddressLoaders():
    def __init__(self):
        self.lock = threading.Lock()
        self.puzzle_hash: bytes32 = None
        self.start_height: uint32 = uint32(0)
        self.end_height: uint32 = uint32(2**32 - 1)
        self.remove_spent_coins: bool = False
        self.remove_self_transactions: bool = False
        self.show_phantom_coin_outputs: bool = False
        self.address_loader: WDB.DataChunkLoader = None
        self.address_loader_outbound: WDB.DataChunkLoader = None
        self.puzzle_and_sol_rpc = None
        self.puzzle_disassembled = None
        self.unrolled_puzzles = []
        self.balance = -1
        self.unspent_coin_count = -1
        self.total_coin_count = -1
        self.unspent_hinted_coin_count = -1
        self.total_hinted_coin_count = -1
        self.layered_puzzle_type = 'No data'
        self.layered_puzzle_name = 'No data'
        self.cache_progress = None  # (coins done, total coins or None) while the cache is building
        # coins hinted to the address, by the puzzle hash they use (load_hinted_groups)
        self.hinted_groups = None  # list of WDB.FetchMaker.get_hinted_groups dicts, None while loading
        self.hinted_types = {}  # puzzle_hash -> (puzzle_type, metadata, layered_name, verified)
        self.hinted_progress = None  # (classified, to classify) while the types are classified
        self.hinted_show_spent = False  # also the puzzle hashes with no unspent coin


### WHERE should i go?
def load_the_loaders(address_loaders: AddressLoaders):
    # TODO: make a class from the address_loaders
    logging(debug_logger, "DEBUG", "LOAD the loader init")
    table_name = 'coin_record'
    chunk_size = 1000  # 120  # height * 2  # to be sure to have at least 2 full screen of data
    offset = 0
    sorting_column = 'confirmed_index'
    filters = None  # {'in_main_chain': 1}

    with address_loaders.lock:
        search_value = address_loaders.puzzle_hash
        start_height = address_loaders.start_height
        start_height = address_loaders.start_height
        end_height = address_loaders.end_height
        remove_spent_coins = address_loaders.remove_spent_coins
        remove_self_transactions = address_loaders.remove_self_transactions

    # basic address stats
    balance, unspent_coin_count, total_coin_count, unspent_hinted_coin_count, total_hinted_coin_count = WDB.FetchMaker.get_total_amount_and_type_count_from_puzzle_hash(DB_BLOCKCHAIN_RO, search_value)
    with address_loaders.lock:
        address_loaders.balance = balance
        address_loaders.unspent_coin_count = unspent_coin_count
        address_loaders.total_coin_count = total_coin_count
        address_loaders.unspent_hinted_coin_count = unspent_hinted_coin_count
        address_loaders.total_hinted_coin_count = total_hinted_coin_count

    logging(debug_logger, "DEBUG", "LOAD the loader param")

    # Inbound
    fetcher = WDB.FetchMaker.puzzle_hash_fetcher(search_value, sorting_column, start_height, end_height, remove_spent_coins, remove_self_transactions)
    fetcher_first_last = WDB.FetchMaker.puzzle_hash_first_last_count_fetcher(search_value, sorting_column, start_height, end_height, remove_spent_coins, remove_self_transactions)

    add_loader = WDB.DataChunkLoader(
        DB_BLOCKCHAIN_RO, table_name, chunk_size, fetcher, fetcher_first_last, offset,
        filters=filters, sorting_column=sorting_column, data_struct=TYPES.CoinRecordRoto.to_list_inbound)
    with address_loaders.lock:
        address_loaders.address_loader = add_loader

    logging(debug_logger, "DEBUG", "LOAD the loader INbound")

    # Outbound
    fetcher = WDB.FetchMaker.puzzle_hash_outbound_fetcher(search_value, sorting_column, start_height, end_height, remove_spent_coins)
    fetcher_first_last = WDB.FetchMaker.puzzle_hash_outbound_first_last_count_fetcher(search_value, sorting_column, start_height, end_height, remove_spent_coins)

    try:
        add_loader_out: WDB.DataChunkLoader = WDB.DataChunkLoader(
            DB_BLOCKCHAIN_RO, table_name, chunk_size, fetcher, fetcher_first_last, offset,
            filters=filters, sorting_column=sorting_column, data_struct=TYPES.CoinRecordRoto.to_list_outbound)
        with address_loaders.lock:
            address_loaders.address_loader_outbound = add_loader_out
    except Exception as e:
        logging(debug_logger, "DEBUG", f"LOAD OUT exc {e}")
        logging(debug_logger, "DEBUG", f"LOAD edarbello")
        text = traceback.format_exc()
        text = text.replace("\n", "")
        logging(debug_logger, "DEBUG", f"LOAD irogram exc {text}")
        import time
        time.sleep(2)

    logging(debug_logger, "DEBUG", "LOAD the loader OUT obu")

    # Uncurry puzzle
    if add_loader_out.total_row_count > 0:
        try:
            parent = None
            puzzle = None
            amount = None
            coin_id = None
            spent_height = None
            logging(debug_logger, "DEBUG", f"LOAD pre coin: {search_value}")
            fetcher = WDB.FetchMaker.puzzle_hash_fetcher(search_value, 'spent_index', 0, uint32((2**32) - 1), True, order='DESC')

            ### TODO: when importing from the db, i convert to xch and there is the possibility to lose some precision, remove this
            conn = sqlite3.connect(DB_BLOCKCHAIN_RO, uri=True)
            with conn:
                spent_coin: TYPES.CoinRecordRoto = fetcher(conn, 0, 2)[1]
                logging(debug_logger, "DEBUG", f"LOAD i fetcher a check THIS: {spent_coin}")
                #spent_height = int(spent_coin[1])
                spent_height = spent_coin.spent_block_index
                #parent = spent_coin[4]
                parent = spent_coin.coin.parent_coin_info.hex()
                #puzzle = decode_puzzle_hash(spent_coin[3]).hex()
                puzzle = spent_coin.coin.puzzle_hash.hex()
                #amount = int(spent_coin[5] * XCH_MOJO)
                amount = spent_coin.coin.amount
            conn.close()

            logging(debug_logger, "DEBUG", f"LOAD i fetcher parenty: {parent}")
            logging(debug_logger, "DEBUG", f"LOAD i fetcher puzz: {puzzle}")
            logging(debug_logger, "DEBUG", f"LOAD i fetcher amo: {amount}")
            coin_name = UTILS.calc_coin_id(parent, puzzle, amount)  # we already have the coin_name
            logging(debug_logger, "DEBUG", f"LOAD i fetcher coin NAME: {coin_name}")

            logging(debug_logger, "DEBUG", f"LOAD i here the COIN NAMEEEEE: {coin_name}")
            logging(debug_logger, "DEBUG", f"LOAD i SPENRT NAMEEEEE: {spent_coin.coin_name}")
            out = RPC.call_rpc_node('get_puzzle_and_solution', coin_id=spent_coin.coin_name.hex(), height=spent_height)
            program = PyProgram.fromhex(out['puzzle_reveal'])
            puzzle_disassembled = disassemble(program)
            logging(debug_logger, "DEBUG", f"LOAD i fetcher program: {program}")
            unroll_puzzles = PUZ.unroll_puzzle_to_nodes(program)
            puz_names, puz_hashes = PUZ.unroll_puzzle_to_names(program)
            layered_puzzle_type, layered_puzzle_name = PUZ.compare_unrolled_puzzle_to_known_layered_puzzles(puz_hashes, program)
            logging(debug_logger, "DEBUG", f"LOAD puz_hashes: {puz_hashes}")

            with address_loaders.lock:
                address_loaders.puzzle_and_sol_rpc = out
                address_loaders.puzzle_disassembled = puzzle_disassembled
                address_loaders.unrolled_puzzles = unroll_puzzles
                address_loaders.layered_puzzle_type = layered_puzzle_type
                address_loaders.layered_puzzle_name = layered_puzzle_name

            logging(debug_logger, "DEBUG", f"LOAD loaders ENDED")

        except Exception as e:
            logging(debug_logger, "DEBUG", f"LOAD program exc {e}")
            logging(debug_logger, "DEBUG", f"LOAD program exc erbello")
            text = traceback.format_exc()
            s_text = text.split('\n')
            text = text.replace("\n", "")
            logging(debug_logger, "DEBUG", f"LOAD irogram exc {text}")
            for n, i in enumerate(s_text):
                logging(debug_logger, "DEBUG", f"LOAD i{n}-{i}")


    else:
        with address_loaders.lock:
            address_loaders.unrolled_puzzles = None  # no spent coins



    logging(debug_logger, "DEBUG", "LOAD the loader end")


###################### CACHE MODE #######################################
###################### CACHE MODE #######################################
###################### CACHE MODE #######################################
def load_the_loaders_cache_mode(screenState: ScreenState, address_loaders: AddressLoaders, inbound: bool = True,
                                outbound: bool = True, uncurry_puzzle: bool = True, update_cache: bool = False,
                                follow: bool = True):
    """follow: with update_cache, the cache updater follows the address after its build. False for
    a puzzle hash opened from a hinted row: it is built again (it is small) each time it is opened"""
    # TODO: make a class from the address_loaders
    logging(debug_logger, "DEBUG", "LOAD the loader init")
    table_name = 'coin_record'
    chunk_size = 200  # 120  # height * 2  # to be sure to have at least 2 full screen of data
    offset = 0
    sorting_column = 'confirmed_index'
    filters = None  # {'in_main_chain': 1}

    timo = UTILS.Timer()
    timo.start()
    timo.clocking('start')

    with address_loaders.lock:
        search_value = address_loaders.puzzle_hash
        start_height = address_loaders.start_height
        start_height = address_loaders.start_height
        end_height = address_loaders.end_height
        remove_spent_coins = address_loaders.remove_spent_coins
        remove_self_transactions = address_loaders.remove_self_transactions
        show_phantom_coin_outputs = address_loaders.show_phantom_coin_outputs
        logging(debug_logger, "DEBUG", f"LOAD remove SPENT: {remove_spent_coins}")
        logging(debug_logger, "DEBUG", f"LOAD remove SELF: {remove_self_transactions}")


    if update_cache:
        # basic address stats
        def main_info_puzzle():
            balance, unspent_coin_count, total_coin_count, peak_height = WDB.FetchMaker.get_total_amount_and_count_from_puzzle_hash(DB_BLOCKCHAIN_RO, search_value)
            with address_loaders.lock:
                address_loaders.balance = balance
                address_loaders.unspent_coin_count = unspent_coin_count
                address_loaders.total_coin_count = total_coin_count
            unspent_hinted_coin_count, total_hinted_coin_count = WDB.FetchMaker.get_hinted_amount_and_type_count_from_puzzle_hash(DB_BLOCKCHAIN_RO, search_value)
            with address_loaders.lock:
                address_loaders.unspent_hinted_coin_count = unspent_hinted_coin_count
                address_loaders.total_hinted_coin_count = total_hinted_coin_count

            cache_conn = WDB.get_connection(CONF.DB_CACHED_BLOCKCHAIN)
            try:
                WDB.insert_cache_address_info(cache_conn, search_value, peak_height, balance, total_coin_count, unspent_coin_count, total_hinted_coin_count, unspent_hinted_coin_count)
                logging(debug_logger, "DEBUG", f"LOAD INFOO INDDDDDDERST")
            except Exception as e:
                logging(debug_logger, "DEBUG", f"LOAD INFOO exc {e}")
                logging(debug_logger, "DEBUG", f"LOAD INFOOO edarbello")
                text = traceback.format_exc()
                text = text.replace("\n", "")
                logging(debug_logger, "DEBUG", f"LOAD irogram exc {text}")
                import time
                time.sleep(2)
            finally:
                cache_conn.close()

        timo.clocking('init lock')
        main_info_thread = threading.Thread(target=main_info_puzzle, daemon=True)
        main_info_thread.start()
        main_info_thread.setName('puzzle info')
        with screenState.lock:
            screenState.running_threads.append(main_info_thread)

        logging(debug_logger, "DEBUG", "LOAD the loader param")
        # start a thread the build the cache or update if alredy there
        timo.clocking('init amount type count')


        def update_cache_db_for_address(puzzle_hash):
            aa_timo = UTILS.Timer()
            aa_timo.start()
            aa_timo.clocking('start')
            cache_conn = WDB.get_connection(CONF.DB_CACHED_BLOCKCHAIN)
            db_conn = WDB.get_connection(CONF.DB_BLOCKCHAIN_RO)

            cache_updater = screenState.cache_updater
            if cache_updater.is_followed(puzzle_hash):
                # already kept up to date by the cache updater, nothing to build
                logging(debug_logger, "DEBUG", f"DB LOAD address already followed by the cache updater")
            else:
                logging(debug_logger, "DEBUG", f"DB LOAD starting cache fetcher")

                def show_cache_progress(done, total):
                    # reload the tables on the coins already cached
                    with address_loaders.lock:
                        address_loaders.cache_progress = (done, total)
                    load_the_loaders_cache_mode(screenState, address_loaders, inbound, outbound, uncurry_puzzle=False)

                with address_loaders.lock:
                    address_loaders.cache_progress = (0, None)  # total not known yet
                built_height = cache_updater.node_peak(db_conn)[0]
                try:
                    WDB.FetchMaker.cache_fetcher(db_conn, cache_conn, puzzle_hash, callback=show_cache_progress)
                finally:
                    with address_loaders.lock:
                        address_loaders.cache_progress = None
                if follow:
                    cache_updater.follow(puzzle_hash, built_height)
                logging(debug_logger, "DEBUG", f"DB LOAD ENDED cache fetcher")

                # the loaders were built while the cache was still updating, rebuild them on the fresh cache
                load_the_loaders_cache_mode(screenState, address_loaders, inbound, outbound, uncurry_puzzle)

            logging(debug_logger, "DEBUG", f"DB LOAD starting memo fetcher")
            WDB.FetchMaker.memo_fetcher(cache_conn, puzzle_hash, sleep_between_calls=0.05)
            logging(debug_logger, "DEBUG", f"DB LOAD ENDED memo fetcher")

            # reload to show the memos
            load_the_loaders_cache_mode(screenState, address_loaders, inbound, outbound, uncurry_puzzle=False)

            aa_timo.clocking('fetch')

            cache_conn.close()
            db_conn.close()
            logging(debug_logger, "DEBUG", f"DB LOAD ENDEDE without ERRRORSSS")
            aa_timo.clocking('end cache')

            aa_timo.clocking('end')
            aa_timo.end()
            aa_timo_s = f"{aa_timo}"
            aa_timo_ss = aa_timo_s.split('\n')
            logging(debug_logger, "DEBUG", "DB TIMO LOAD fetch: ")
            for n, i in enumerate(aa_timo_ss):
                logging(debug_logger, "DEBUG", f"DB TIMO LOAD i{n}-{i}")
            # logica cache DB
            # 1 create classe DB with:
            ## - fun to create the cache DB
            ## - fun to populate the cache DB from: puzz_hash (others? it could scan for tails or mints and keep track)
            ## - update puzz_hash -> check for unspent coins, then recheck the DB from last height
            ## - when running it? -> start up for watchlist, every time you watch an address, and update it every 10 sec while you are watching something?
            ## - connect to the daemon to now when to update, also for the block part

        timo.clocking('init')
        # start thread to build the cache
        update_cache_thread = threading.Thread(target=update_cache_db_for_address, args=(search_value,), daemon=True)
        update_cache_thread.start()
        update_cache_thread.setName("updating cache")
        with screenState.lock:
            screenState.running_threads.append(update_cache_thread)
        #update_cache_db_for_address(search_value)

    timo.clocking('cache update')
    logging(debug_logger, "DEBUG", "LOAD updated the cache")

    # coin_info
    cache_conn = WDB.get_connection(CONF.DB_CACHED_BLOCKCHAIN)
    try:
        add_info = WDB.retrive_cache_address_info(cache_conn, search_value)
        if add_info:
            with address_loaders.lock:
                address_loaders.balance = add_info[1]
                address_loaders.unspent_coin_count = add_info[3]
                address_loaders.total_coin_count = add_info[2]
                address_loaders.unspent_hinted_coin_count = add_info[5]
                address_loaders.total_hinted_coin_count = add_info[4]
    except Exception as e:
        logging(debug_logger, "DEBUG", f"LOAD INFO ERROR{e}")
        UTILS.logging_traceback("LOAD INFO")
    finally:
        cache_conn.close()

    # Inbound from cache
    def inbound_call():
        fetcher = WDB.FetchMaker.CACHE_puzzle_hash_fetcher(search_value, sorting_column, start_height, end_height, remove_spent_coins, remove_self_transactions)
        fetcher_first_last = WDB.FetchMaker.CACHE_puzzle_hash_fetcher(search_value, sorting_column, start_height, end_height,
                                                                      remove_spent_coins, remove_self_transactions, first_last_count=True)

        logging(debug_logger, "DEBUG", "LOAD fetcher DONE")

        timo.clocking('fetch_maker')
        try:
            add_loader = WDB.DataChunkLoader(
                CONF.DB_CACHED_BLOCKCHAIN, table_name, chunk_size, fetcher, fetcher_first_last, offset,
                filters=filters, sorting_column=sorting_column, data_struct=TYPES.CoinRecordRoto.to_list_inbound)
            with address_loaders.lock:
                address_loaders.address_loader = add_loader
        except Exception as e:
            logging(debug_logger, "DEBUG", f"LOAD OUT exc {e}")
            logging(debug_logger, "DEBUG", f"LOAD edarbello")
            text = traceback.format_exc()
            text = text.replace("\n", "")
            logging(debug_logger, "DEBUG", f"LOAD irogram exc {text}")
            import time
            time.sleep(2)

        timo.clocking('inbound')
        logging(debug_logger, "DEBUG", "LOAD the loader INbound")
        logging(debug_logger, "DEBUG", "LOAD eeeeeeeeeeeeeeeeeenddhe loader INbound")

    # Outbound
    def outbound_call():
        fetcher = WDB.FetchMaker.CACHE_puzzle_hash_outbound_fetcher(search_value, sorting_column, start_height, end_height, remove_spent_coins, remove_self_transactions, show_phantom_coin_outputs)
        fetcher_first_last = WDB.FetchMaker.CACHE_puzzle_hash_outbound_fetcher(search_value, sorting_column, start_height, end_height, remove_spent_coins,
                                                                               remove_self_transactions, show_phantom_coin_outputs, first_last_count=True)

        timo.clocking('fetch_maker out')
        try:
            add_loader_out: WDB.DataChunkLoader = WDB.DataChunkLoader(
                CONF.DB_CACHED_BLOCKCHAIN, table_name, chunk_size, fetcher, fetcher_first_last, offset,
                filters=filters, sorting_column=sorting_column, data_struct=TYPES.CoinRecordRoto.to_list_outbound)
            with address_loaders.lock:
                address_loaders.address_loader_outbound = add_loader_out
        except Exception as e:
            logging(debug_logger, "DEBUG", f"LOAD OUT exc {e}")
            logging(debug_logger, "DEBUG", f"LOAD edarbello")
            text = traceback.format_exc()
            text = text.replace("\n", "")
            logging(debug_logger, "DEBUG", f"LOAD irogram exc {text}")
            import time
            time.sleep(2)

        timo.clocking('outbound')

        logging(debug_logger, "DEBUG", "LOAD the loader OUT OUT OUT")

    if inbound:
        inbound_call()
        outbound_call()
    else:
        outbound_call()
        inbound_call()

    logging(debug_logger, "DEBUG", "LOAD the loader PUTPUTPUTPUTPUTPUTPTU")

    # Uncurry puzzle
    logging(debug_logger, "DEBUG", f"LOAD the bool {uncurry_puzzle}")
    with address_loaders.lock:
        add_loader_out = address_loaders.address_loader_outbound
        puzzle_unknown = address_loaders.puzzle_and_sol_rpc is None
    logging(debug_logger, "DEBUG", f"LOAD row count {add_loader_out.total_row_count}")
    # also when the first spent coin appears after the first load (spent in a new block)
    if uncurry_puzzle or (puzzle_unknown and add_loader_out.total_row_count > 0):
        if add_loader_out.total_row_count > 0:
            try:
                parent = None
                puzzle = None
                amount = None
                coin_id = None
                spent_height = None
                logging(debug_logger, "DEBUG", f"LOAD pre coin: {search_value}")

                # any spent coin has the puzzle reveal of the puzzle hash
                conn = sqlite3.connect(CONF.DB_CACHED_BLOCKCHAIN, uri=True)
                with conn:
                    spent_coin: TYPES.CoinRecordRoto = WDB.FetchMaker.CACHE_one_spent_coin(conn, search_value)
                conn.close()

                logging(debug_logger, "DEBUG", f"LOAD i fetcher a check THIS: {spent_coin}")
                #spent_height = int(spent_coin[1])
                spent_height = spent_coin.spent_block_index
                #parent = spent_coin[4]
                parent = spent_coin.coin.parent_coin_info.hex()
                #puzzle = decode_puzzle_hash(spent_coin[3]).hex()
                puzzle = spent_coin.coin.puzzle_hash.hex()
                #amount = int(spent_coin[5] * XCH_MOJO)
                amount = spent_coin.coin.amount

                logging(debug_logger, "DEBUG", f"LOAD i fetcher parenty: {parent}")
                logging(debug_logger, "DEBUG", f"LOAD i fetcher puzz: {puzzle}")
                logging(debug_logger, "DEBUG", f"LOAD i fetcher amo: {amount}")
                coin_name = UTILS.calc_coin_id(parent, puzzle, amount)  # we already have the coin_name
                logging(debug_logger, "DEBUG", f"LOAD i fetcher coin NAME: {coin_name}")

                logging(debug_logger, "DEBUG", f"LOAD i here the COIN NAMEEEEE: {coin_name}")
                logging(debug_logger, "DEBUG", f"LOAD i SPENRT NAMEEEEE: {spent_coin.coin_name}")
                logging(debug_logger, "DEBUG", f"LOAD i SPENRT NAMEEEEE: {spent_coin.coin_name.hex()}")
                logging(debug_logger, "DEBUG", f"LOAD i SPENRT height: {spent_height}")
                out = RPC.call_rpc_node('get_puzzle_and_solution', coin_id=spent_coin.coin_name.hex(), height=spent_height)
                program = PyProgram.fromhex(out['puzzle_reveal'])
                puzzle_disassembled = disassemble(program)
                logging(debug_logger, "DEBUG", f"LOAD i fetcher program: {program}")
                unroll_puzzles = PUZ.unroll_puzzle_to_nodes(program)
                puz_names, puz_hashes = PUZ.unroll_puzzle_to_names(program)
                layered_puzzle_type, layered_puzzle_name = PUZ.compare_unrolled_puzzle_to_known_layered_puzzles(puz_hashes, program)
                logging(debug_logger, "DEBUG", f"LOAD puz_hashes: {puz_hashes}")

                with address_loaders.lock:
                    address_loaders.puzzle_and_sol_rpc = out
                    address_loaders.puzzle_disassembled = puzzle_disassembled
                    address_loaders.unrolled_puzzles = unroll_puzzles
                    address_loaders.layered_puzzle_type = layered_puzzle_type
                    address_loaders.layered_puzzle_name = layered_puzzle_name

                logging(debug_logger, "DEBUG", f"LOAD loaders ENDED")

            except Exception as e:
                logging(debug_logger, "DEBUG", f"LOAD program exc {e}")
                logging(debug_logger, "DEBUG", f"LOAD program exc erbello")
                text = traceback.format_exc()
                s_text = text.split('\n')
                text = text.replace("\n", "")
                logging(debug_logger, "DEBUG", f"LOAD irogram exc {text}")
                for n, i in enumerate(s_text):
                    logging(debug_logger, "DEBUG", f"LOAD i{n}-{i}")


        else:
            with address_loaders.lock:
                address_loaders.unrolled_puzzles = None  # no spent coins
            logging(debug_logger, "DEBUG", f"LOAD NOOOOO SPENT COIN")

        logging(debug_logger, "DEBUG", f"LOAD NOOOOO UNVURRY")
        logging(debug_logger, "DEBUG", f"LOAD NOOOOO UNVURRY")
        logging(debug_logger, "DEBUG", f"LOAD NOOOOO UNVURRY")

    logging(debug_logger, "DEBUG", "DB TIMO LOAD fetch: ")
    timo.clocking('end')
    timo.end()
    timo_s = f"{timo}"
    timo_ss = timo_s.split('\n')
    logging(debug_logger, "DEBUG", "DB TIMO LOAD fetch: ")
    for n, i in enumerate(timo_ss):
        logging(debug_logger, "DEBUG", f"DB TIMO LOAD i{n}-{i}")


    logging(debug_logger, "DEBUG", "LOAD TIMO the loader ENNNNNNNNNDDDDDDDDDD")
    logging(debug_logger, "DEBUG", "LOAD TIMO the loader ENNNNNNNNNDDDDDDDDDD")
    logging(debug_logger, "DEBUG", "LOAD TIMO the loader ENNNNNNNNNDDDDDDDDDD")


load_the_loaders = load_the_loaders_cache_mode


def scopeAction_address_loader(scope: Scope, screenState: ScreenState, search_value: str):

    if search_value is None:
        return scope

    new_name = f"{scope.parent_scope.name}_{search_value}"
    new_scope = Scope(new_name, screen_address_viewer, screenState)
    new_scope.parent_scope = scope  # parent_scope
    search_value = UTILS.string_to_bytes32(search_value)

    logging(debug_logger, "DEBUG", f'LOAD type {type(search_value)}')
    address_loaders: AddressLoaders = AddressLoaders()
    address_loaders.puzzle_hash = search_value
    new_scope.exec = None

    start_height = uint32(0)
    end_height = uint32((2**32) - 1)
    remove_spent_coins = False
    remove_self_transactions = False

    # load_the_loaders(address_loaders)  # DEBUG
    loaders_thread = threading.Thread(target=load_the_loaders, args=(screenState, address_loaders,), daemon=True)
    loaders_thread.start()
    loaders_thread.setName("loading address")
    with screenState.lock:
        screenState.running_threads.append(loaders_thread)

    new_scope.data['address_loaders'] = address_loaders
    screenState.activeScope = new_scope

    return new_scope


HINTED_TAB_TYPES = {'CAT': ('CAT', 'REVOCABLE_CAT'), 'NFT': ('NFT',)}  # the rest goes in OTHER


def load_hinted_groups(address_loaders: AddressLoaders):
    """The puzzle hashes of the coins hinted to the address, then the type of the ones not
    classified yet, one RPC call each (WDB.classify_hinted_group), saved in the cache DB.
    Run it in a thread; a second call while one classifies only reloads the groups"""
    with address_loaders.lock:
        hint = address_loaders.puzzle_hash
    try:
        groups = WDB.FetchMaker.get_hinted_groups(DB_BLOCKCHAIN_RO, hint)
    except Exception:
        UTILS.logging_traceback("HINTED GROUPS")
        return
    cache_conn = WDB.get_connection(CONF.DB_CACHED_BLOCKCHAIN)
    try:
        known = WDB.load_hinted_puzzle_types(cache_conn)
        types = {g['puzzle_hash']: known[g['puzzle_hash']] for g in groups if g['puzzle_hash'] in known}
        todo = [g for g in groups if g['puzzle_hash'] not in types]
        with address_loaders.lock:
            address_loaders.hinted_groups = groups
            address_loaders.hinted_types = types
            if not todo or address_loaders.hinted_progress is not None:
                return  # nothing to classify, or another thread is classifying
            address_loaders.hinted_progress = (0, len(todo))
        try:
            for n, g in enumerate(todo):
                try:
                    result = WDB.classify_hinted_group(hint, g)
                except Exception:
                    # not saved: tried again the next time the address is opened
                    UTILS.logging_traceback("HINTED CLASSIFY")
                else:
                    WDB.save_hinted_puzzle_type(cache_conn, g['puzzle_hash'], *result)
                    with address_loaders.lock:
                        address_loaders.hinted_types[g['puzzle_hash']] = result
                with address_loaders.lock:
                    address_loaders.hinted_progress = (n + 1, len(todo))
        finally:
            with address_loaders.lock:
                address_loaders.hinted_progress = None
    finally:
        cache_conn.close()


def start_hinted_groups_load(screenState: ScreenState, address_loaders: AddressLoaders):
    thread = threading.Thread(target=load_hinted_groups, args=(address_loaders,), daemon=True)
    thread.start()
    thread.setName("hinted groups")
    with screenState.lock:
        screenState.running_threads.append(thread)


def short_hex(value: bytes, side: int = 6) -> str:
    h = bytes(value).hex()
    return h if len(h) <= 2 * side + 1 else f"{h[:side]}…{h[-4:]}"


def scopeAction_hinted_address(scope: Scope, screenState: ScreenState, key):
    """enter on a hinted row: the address viewer of its puzzle hash, with a banner that says to
    which address it is hinted. Its cache is built but not followed (WDB.CacheUpdater)"""
    if key is None:
        return scope
    row = scope.main_scope.data.get('hinted_rows', {}).get(key)

    new_scope = Scope(f"{scope.parent_scope.name}_{key}", screen_address_viewer, screenState)
    new_scope.parent_scope = scope
    new_scope.exec = None
    address_loaders = AddressLoaders()
    address_loaders.puzzle_hash = UTILS.string_to_bytes32(key)
    new_scope.data['address_loaders'] = address_loaders
    new_scope.data['hinted_from'] = row
    if row is not None and row['puzzle_type'] is not None:
        # its PUZZLE tab knows the puzzle only from a spent coin: an NFT held now has none
        with address_loaders.lock:
            address_loaders.layered_puzzle_type = PUZ.value_label('puzzle_type', row['puzzle_type'])

    thread = threading.Thread(target=load_the_loaders, args=(screenState, address_loaders),
                              kwargs={'update_cache': True, 'follow': False}, daemon=True)
    thread.start()
    thread.setName("loading hinted address")
    with screenState.lock:
        screenState.running_threads.append(thread)

    screenState.activeScope = new_scope
    return new_scope


def screen_address_watchlist(stdscr, keyboardState: KeyboardState, screenState: ScreenState, fullNodeState: FullNodeState, figlet=False):

    path = CONF.USER_ADDX_WATCHLIST

    if path.exists():
        addx = WDB.load_csv_no_comments(path)
    else:
        # write and empty file
        empty_line = [('#address', ' name', " 'some notes'")]
        WDB.save_csv(path, empty_line)
        addx = []

    new_addx = [[] for _ in range(3)]
    swap_col = [1,0,2]
    for u, add in enumerate(addx):
        for i in range(3):
            new_addx[i].append('')
        for n, a in enumerate(add):
            new_addx[swap_col[n]][u] = a

    C_background = screenState.colors["background"]
    P_text = screenState.colorPairs["body"]
    P_error = screenState.colorPairs["error_white"]
    P_title = screenState.colorPairs["title"]
    P_title_selected = screenState.colorPairs["xch"]
    P_tab_soft = screenState.colorPairs["tab_soft"]

    # init color table
    data_table_colors = [[None] * len(new_addx[0]) for _ in range(3)]

    # parse for watchlist error
    for n, add in enumerate(new_addx[1]):
        add_value = UTILS.string_to_bytes32(add)
        try:
            encode_puzzle_hash(add_value, CONF.ADD_PREFIX)
        except:
            new_addx[2][n] = 'ERROR: DECODING ADDRESS - ' + new_addx[2][n]
            logging(debug_logger, "DEBUG", f"exception decoding watchlist address: {add}")
            new_addx[1][n] = None
            for i in range(3):
                data_table_colors[i][n] = P_error


    height = screenState.screen_size.y
    width = screenState.screen_size.x

    active_scope: Scope = screenState.activeScope
    main_scope: Scope = active_scope.main_scope
    screenState.scope_exec_args = [screenState]
    #main_scope.update_2d()
    main_scope.update()

    # sub win
    win = createFullSubWin(stdscr, screenState, height, width)
    win.bkgd(' ', curses.color_pair(screenState.colorPairs["body"]))

    main_win_size = win.getmaxyx()
    main_win_size = UIgraph.Point(main_win_size[1], main_win_size[0])
    pos = UIgraph.Point(1,1)
    pos_orig = pos
    max_y = main_win_size.y - pos.y - 3

    text = 'watchlist'
    ELEMENTS.create_text_double_space(win, screenState, pos, text, P_title_selected, C_background,
                                      3, True, inv_color=False)


    pos += UIgraph.Point(0,3)

    tab_legend = ['name', 'address', 'notes']

    max_y = main_win_size.y - pos.y - 3
    min_y = max(15, len(new_addx[0]) + 1)
    tab_size = UIgraph.Point(80, min_y)
    tab_size = UIgraph.Point(80, max_y)



    ### custom init scope and add to parent
    tab_name = "address_watchlist"
    scope_name = f"{main_scope.id}_{tab_name}"
    if scope_name not in screenState.scopes:
        tab_scope = Scope(scope_name, main_scope.screen, screenState)
        tab_scope.parent_scope = main_scope
        tab_scope.main_scope = main_scope
        tab_scope.exec = ScopeActions.activate_scope
        tab_scope.exec_esc = TYPES.ScopeActions.exit_scope_N(2)
        main_scope.sub_scopes[tab_name] = tab_scope
        tab_scope.visible = True

        tab_scope.exec_own = scopeAction_address_loader
    else:
        tab_scope = screenState.scopes[scope_name]

    # make the tab active
    screenState.activeScope = tab_scope
    print('new-addx')
    print(new_addx)
    tab_scope = ELEMENTS.create_tab(win,
                                    screenState,
                                    main_scope,
                                    tab_name,
                                    new_addx,
                                    new_addx[1],
                                    data_table_colors,
                                    True,
                                    pos,
                                    tab_size,
                                    keyboardState,
                                    scopeAction_address_loader,  # TODO? already defined in tab_scope
                                    False,
                                    False,
                                    tab_legend,
                                    prepped_scope=tab_scope)



def screen_cache_db(stdscr, keyboardState: KeyboardState, screenState: ScreenState, fullNodeState: FullNodeState, figlet=False):
    """Addresses saved in the cache DB, the space they take and the size of the DB"""

    height = screenState.screen_size.y
    width = screenState.screen_size.x

    active_scope: Scope = screenState.activeScope
    main_scope: Scope = active_scope.main_scope
    screenState.scope_exec_args = [screenState]
    main_scope.update_2d()

    C_background = screenState.colors["background"]
    P_text = screenState.colorPairs["body"]
    P_error = screenState.colorPairs["error"]
    P_title_selected = screenState.colorPairs["xch"]
    data = main_scope.data

    # sub win
    win = createFullSubWin(stdscr, screenState, height, width)
    win.bkgd(' ', curses.color_pair(screenState.colorPairs["body"]))

    main_win_size = win.getmaxyx()
    main_win_size = UIgraph.Point(main_win_size[1], main_win_size[0])
    pos = UIgraph.Point(1, 1)

    ELEMENTS.create_text_double_space(win, screenState, pos, 'cache DB', P_title_selected, C_background,
                                      3, True, inv_color=False)
    pos += UIgraph.Point(0, 3)

    # load the stats in background, the counts can take some seconds on a big cache
    # reload them when they are older than 30 sec
    now = datetime.now().timestamp()
    if (not data.get('cache_stats_loading') and not data.get('cache_job')
            and now - data.get('cache_stats_time', 0) > 30):
        data['cache_stats_loading'] = True

        def load_cache_stats():
            cache_conn = WDB.get_connection(CONF.DB_CACHED_BLOCKCHAIN)
            try:
                data['cache_stats'] = WDB.retrive_cache_db_stats(cache_conn, CONF.DB_CACHED_BLOCKCHAIN)
                data['cache_stats_error'] = None
            except Exception as e:
                logging(debug_logger, "DEBUG", f"cache stats ERROR {e}")
                UTILS.logging_traceback("CACHE STATS")
                data['cache_stats_error'] = f"cache stats error: {e}"
            finally:
                cache_conn.close()
                data['cache_stats_time'] = datetime.now().timestamp()
                data['cache_stats_loading'] = False

        stats_thread = threading.Thread(target=load_cache_stats, daemon=True)
        stats_thread.start()
        stats_thread.setName("loading cache stats")
        with screenState.lock:
            screenState.running_threads.append(stats_thread)

    stats = data.get('cache_stats')
    if data.get('cache_stats_error'):
        ELEMENTS.create_text(win, pos, data['cache_stats_error'], P_error, bold=True)
        pos += UIgraph.Point(0, 2)
    elif stats is None:
        ELEMENTS.create_text(win, pos, "loading cache stats...", P_text, bold=True)
        pos += UIgraph.Point(0, 2)

    if stats is not None:
        text = (f"file: {CONF.DB_CACHED_BLOCKCHAIN}  |  total size: {UTILS.human_bytes(stats['file_size'])} "
                f"(wal {UTILS.human_bytes(stats['wal_size'])})  |  coin rows: {UTILS.human_int(stats['total_rows'])}")
        ELEMENTS.create_text(win, pos, text, P_text, bold=True)
        pos += UIgraph.Point(0, 1)

        # clear the whole cache, after a confirmation
        if data.get('cache_job'):
            ELEMENTS.create_text(win, pos + UIgraph.Point(0, 1), f"{data['cache_job']}...", P_text, bold=True)
        else:
            clear_button = ELEMENTS.create_button(win, screenState, main_scope, 'clear cache', pos,
                                                  custom_scope_function=ScopeActions.press_enter,
                                                  button_type='execution')
            if clear_button.data.get('pressed_enter'):
                clear_button.data['pressed_enter'] = False
                banner_scope = ELEMENTS.confirm_banner_scope(screenState, main_scope, 'clear_cache_banner')
                banner_scope.cursor_x = 1  # cancel is selected when the banner opens
                screenState.activeScope = banner_scope
        if data.get('cache_job_message'):
            ELEMENTS.create_text(win, pos + UIgraph.Point(22, 1), data['cache_job_message'], P_text)
        pos += UIgraph.Point(0, 3)

        if len(stats['addresses']) == 0:
            ELEMENTS.create_text(win, pos, "no address in the cache", P_text)
        else:
            rows = []
            for add in stats['addresses']:
                rows.append([encode_puzzle_hash(add['puzzle_hash'], CONF.ADD_PREFIX),
                             add['coins'], add['created'], add['size'], add['last_height']])

            legend = ['address', 'coins', 'created coins', '~ size', 'last height']
            column_widths = [None, None, None, None, None]
            formatters = [None, UTILS.human_int, UTILS.human_int, UTILS.human_bytes, None]
            max_y = main_win_size.y - pos.y - 3
            tab_size = UIgraph.Point(min(130, main_win_size.x - 4), max(5, max_y))

            tab_scope = ELEMENTS.create_tab(win,
                                            screenState,
                                            main_scope,
                                            "cache_db",
                                            rows,
                                            None,
                                            None,
                                            False,
                                            pos,
                                            tab_size,
                                            keyboardState,
                                            ScopeActions.exit_scope,
                                            False,
                                            False,
                                            legend,
                                            column_widths,
                                            formatters)

            # d (or delete) on the selected address asks to delete it from the cache
            if tab_scope is screenState.activeScope and not data.get('cache_job'):
                screenState.footer_text += "| delete address=d "
                if keyboardState.delete:
                    data['address_to_delete'] = stats['addresses'][tab_scope.cursor % len(stats['addresses'])]
                    banner_scope = ELEMENTS.confirm_banner_scope(screenState, tab_scope, 'delete_address_banner')
                    banner_scope.cursor_x = 1  # cancel is selected when the banner opens
                    screenState.activeScope = banner_scope

            add = data.get('address_to_delete')
            if add is not None:
                lines = ["Delete this address from the cache DB?",
                         encode_puzzle_hash(add['puzzle_hash'], CONF.ADD_PREFIX),
                         f"{UTILS.human_int(add['coins'])} coins and {UTILS.human_int(add['created'])} created coins, "
                         f"~ {UTILS.human_bytes(add['size'])}. It is not followed anymore: open it to build it again."]
                if ELEMENTS.create_confirm_banner(win, screenState, tab_scope, 'delete_address_banner',
                                                  lines, 'delete address'):
                    address = encode_puzzle_hash(add['puzzle_hash'], CONF.ADD_PREFIX)
                    start_cache_job(screenState, data, f"deleting {address}", f"deleted {address}",
                                    screenState.cache_updater.remove, add['puzzle_hash'])

        lines = ["Clear the whole cache DB?",
                 f"{len(stats['addresses'])} addresses and {UTILS.human_int(stats['total_rows'])} coin rows "
                 f"are deleted, the file ({UTILS.human_bytes(stats['file_size'])}) shrinks.",
                 "No address is followed anymore: open an address to build it again, "
                 "the watchlist addresses are built again at the next start."]
        if ELEMENTS.create_confirm_banner(win, screenState, main_scope, 'clear_cache_banner',
                                          lines, 'clear the cache'):
            start_cache_job(screenState, data, "clearing the cache", "cache cleared",
                            screenState.cache_updater.clear)


def start_cache_job(screenState: ScreenState, data: dict, job: str, done_message: str, fn, *args):
    """Run a change of the cache DB (clear, delete an address) in a thread, one at a time.
    The cacheDB screen shows the job while it runs, then reloads the stats"""
    data['cache_job'] = job
    data['cache_job_message'] = None

    def run():
        try:
            fn(*args)
            data['cache_job_message'] = done_message
        except Exception as e:
            logging(debug_logger, "DEBUG", f"cache job ERROR {job}: {e}")
            UTILS.logging_traceback("CACHE JOB")
            data['cache_job_message'] = f"{job} error: {e}"
        finally:
            data['cache_stats_time'] = 0  # reload the stats
            data['cache_job'] = None

    job_thread = threading.Thread(target=run, daemon=True)
    job_thread.start()
    job_thread.setName(job)
    with screenState.lock:
        screenState.running_threads.append(job_thread)


def hinted_tab_of(puzzle_type) -> str:
    """The hinted tab of a catalog type id: CAT, NFT, else OTHER (also not classified yet)"""
    return next((tab for tab, types in HINTED_TAB_TYPES.items() if puzzle_type in types), 'OTHER')


def hinted_rows_by_tab(address_loaders: AddressLoaders) -> dict:
    """{'CAT': [...], 'NFT': [...], 'OTHER': [...]}: a dict per hinted puzzle hash, with what the
    tables and the redirect banner show. Without hinted_show_spent, only the ones with unspent
    coins (what the address holds now)"""
    with address_loaders.lock:
        groups = address_loaders.hinted_groups or []
        types = dict(address_loaders.hinted_types)
        show_spent = address_loaders.hinted_show_spent
    rows = {'CAT': [], 'NFT': [], 'OTHER': []}
    for g in groups:
        if not show_spent and g['unspent'] == 0:
            continue
        classified = g['puzzle_hash'] in types
        puzzle_type, metadata, layered_name, verified = types.get(g['puzzle_hash'], (None, None, None, False))
        tab = hinted_tab_of(puzzle_type)
        if tab == 'OTHER':
            label = PUZ.value_label('puzzle_type', puzzle_type) if puzzle_type else (layered_name or '?')
        else:
            label = f"{PUZ.value_label('puzzle_type', puzzle_type)} {short_hex(metadata) if metadata else '?'}"
        rows[tab].append(dict(g, puzzle_type=puzzle_type, metadata=metadata, classified=classified,
                              layered_name=layered_name, verified=verified, label=label))
    return rows


def hinted_table(win, screenState: ScreenState, keyboardState: KeyboardState, main_scope: Scope,
                 address_loaders: AddressLoaders, address: str, name, tab: str,
                 pos: UIgraph.Point, size: UIgraph.Point):
    """A hinted tab of the address viewer: CAT (one row per tail), NFT (one row per NFT), OTHER.
    Enter opens the address viewer of the row's puzzle hash (scopeAction_hinted_address)"""
    with address_loaders.lock:
        loading = address_loaders.hinted_groups is None
    if loading:
        put_text(win, pos + UIgraph.Point(1, 1), "reading the hinted coins...", screenState.colorPairs["body"], True)
        return

    rows = hinted_rows_by_tab(address_loaders)[tab]
    # what the redirect needs, by the row key
    main_scope.data['hinted_rows'] = {
        r['puzzle_hash'].hex(): {'address': address, 'name': name, 'puzzle_type': r['puzzle_type'],
                                 'label': r['label']}
        for tab_rows in hinted_rows_by_tab(address_loaders).values() for r in tab_rows}

    def last(r):
        return f"{r['last_height']:,}"

    match tab:
        case 'CAT':
            # 1 CAT = 1000 mojos
            legend = ['asset', 'coins', 'unspent', 'amount', 'hint', 'last height']
            table = [[short_hex(r['metadata']) if r['metadata'] else '?', f"{r['coins']:,}", f"{r['unspent']:,}",
                      f"{r['unspent_amount'] / 1000:,.3f}", 'checked' if r['verified'] else 'not checked', last(r)]
                     for r in rows]
            column_widths = [15, None, None, None, None, None]
        case 'NFT':
            legend = ['launcher', 'held', 'coins', 'last height']
            table = [[short_hex(r['metadata']) if r['metadata'] else '?', 'yes' if r['unspent'] else 'no',
                      f"{r['coins']:,}", last(r)] for r in rows]
            column_widths = [15, None, None, None]
        case _:
            legend = ['puzzle type', 'coins', 'unspent', 'mojos', 'last height']
            table = [[r['label'] if r['classified'] else '?', f"{r['coins']:,}", f"{r['unspent']:,}",
                      f"{r['unspent_amount']:,}", last(r)] for r in rows]
            column_widths = [25, None, None, None, None]
    keys = [r['puzzle_hash'].hex() for r in rows]

    # a CAT whose hint was not checked (or not true) in gray: anyone can hint a coin to any address
    colors = fresh_table_colors(table)
    for i, r in enumerate(rows):
        if tab == 'CAT' and not r['verified']:
            colors[i] = [screenState.colors["gray"]] * len(legend)

    tab_name = f"hinted_{tab.lower()}"
    full_name = f"{main_scope.id}_{tab_name}"
    if full_name in screenState.scopes:
        # the columns are sized on the rows: again when they change
        tab_scope = screenState.scopes[full_name]
        shape = (len(table), tuple(tuple(row) for row in table))
        if tab_scope.data.get('rows_shape') != shape:
            tab_scope.data['rows_shape'] = shape
            tab_scope.data['column_sizes'] = tab_scope.data['cached_data_table'] = None
    ELEMENTS.create_tab(win, screenState, main_scope, tab_name, table, keys, colors, False, pos, size,
                        keyboardState, scopeAction_hinted_address, False, False, legend, column_widths,
                        no_cache=True)


def screen_address_viewer(stdscr, keyboardState: KeyboardState, screenState: ScreenState, fullNodeState: FullNodeState, figlet=False):

    height = screenState.screen_size.y
    width = screenState.screen_size.x

    active_scope: Scope = screenState.activeScope
    main_scope: Scope = active_scope.main_scope
    screenState.scope_exec_args = [screenState]
    #main_scope.update_2d()
    main_scope.update()


    # tab: inbound, outbound, puzzle, then the coins hinted to the address: CAT, NFT, other
    tab_selected = main_scope.cursor_x % 6

    # sub win
    add_viewer = createFullSubWin(stdscr, screenState, height, width)
    add_viewer.bkgd(' ', curses.color_pair(screenState.colorPairs["body"]))

    # add loaders
    address_loaders: AddressLoaders = main_scope.data['address_loaders']


    # subscribe once 
    def update_address_loaders():
        # update only the current address_loader without triggering the cache update
        logging(debug_logger, "DEBUG", f"reoloading the chunk for {address_loaders.puzzle_hash}")
        loaders_thread = threading.Thread(target=load_the_loaders,
                                          args=(screenState, address_loaders,),
                                          kwargs={'uncurry_puzzle': False},
                                          daemon=True)
        loaders_thread.start()
        loaders_thread.setName("re-loading loaders")
        with screenState.lock:
            screenState.running_threads.append(loaders_thread)

    #logging(debug_logger, "DEBUG", f"FUN ID {id(update_address_loaders)}")

    # after the cache updater wrote the new blocks, so the reload sees them
    screenState.cache_updater.after_sync[f'update_loaders_{address_loaders.puzzle_hash}'] = update_address_loaders

    # the hinted puzzle hashes: read from the node DB when the screen opens, then on every new block
    if 'hinted_loaded' not in main_scope.data:
        main_scope.data['hinted_loaded'] = True
        start_hinted_groups_load(screenState, address_loaders)
    screenState.cache_updater.after_sync[f'update_hinted_{address_loaders.puzzle_hash}'] = \
        lambda: start_hinted_groups_load(screenState, address_loaders)

    # footer
    screenState.footer_text += "| save_to_watchlist=w "
    if tab_selected >= 3:
        screenState.footer_text += f"| show spent=s ({str(address_loaders.hinted_show_spent).upper()}) "
    else:
        screenState.footer_text += f"| remove_spent_coins=s ({str(address_loaders.remove_spent_coins).upper()}), remove_self_txs=t ({str(address_loaders.remove_self_transactions).upper()})"
    if tab_selected == 1:
        screenState.footer_text += f" | show_sibling_coins ({str(address_loaders.show_phantom_coin_outputs).upper()})"

    ### keyboard
    ### create a virtual fun and the add it to this and to the tab scope

    toggle_coin_keys = 'toggle_keys'
    #if toggle_coin_keys not in main_scope.custom_keyboard_exec:

    def toggle_coin_visibility(address_loaders: AddressLoaders, tab_sel: bool):
        def custom_keyboard_execution(screenState: TYPES.ScreenState, keyboardState: TYPES.KeyboardState,
                                      active_scope: TYPES.Scope):

            if tab_sel >= 3:
                # the hinted tabs: s shows also the puzzle hashes with no unspent coin
                if 's' in keyboardState.keys:
                    with address_loaders.lock:
                        address_loaders.hinted_show_spent = not address_loaders.hinted_show_spent
                return

            inbound_first = True
            if tab_sel== 1:
                inbound_first = False

            # TODO: add update order according to inbound outbound
            if 's' in keyboardState.keys:
                with address_loaders.lock:
                    address_loaders.remove_spent_coins = not address_loaders.remove_spent_coins
                loaders_thread = threading.Thread(target=load_the_loaders,
                                                  args=(screenState, address_loaders, inbound_first, True, False),
                                                  daemon=True)
                loaders_thread.start()
                loaders_thread.setName("re-loading address")
                with screenState.lock:
                    screenState.running_threads.append(loaders_thread)

            if 't' in keyboardState.keys:
                with address_loaders.lock:
                    address_loaders.remove_self_transactions = not address_loaders.remove_self_transactions
                loaders_thread = threading.Thread(target=load_the_loaders,
                                                  args=(screenState, address_loaders, inbound_first, True, False),
                                                  daemon=True)
                loaders_thread.start()
                loaders_thread.setName("re-loading address")
                with screenState.lock:
                    screenState.running_threads.append(loaders_thread)

            if 'i' in keyboardState.keys and tab_sel == 1:
                with address_loaders.lock:
                    address_loaders.show_phantom_coin_outputs = not address_loaders.show_phantom_coin_outputs
                loaders_thread = threading.Thread(target=load_the_loaders,
                                                  args=(screenState, address_loaders, inbound_first, True, False),
                                                  daemon=True)
                loaders_thread.start()
                loaders_thread.setName("re-loading address")
                with screenState.lock:
                    screenState.running_threads.append(loaders_thread)


        return custom_keyboard_execution

    # TODO: find a way to pass tab_selected without redefining every time the toggle?
    toggle_coin_keyboard = toggle_coin_visibility(address_loaders, tab_selected)
    main_scope.custom_keyboard_exec[toggle_coin_keys] = toggle_coin_keyboard

    toggle_coin_keyboard = main_scope.custom_keyboard_exec[toggle_coin_keys]

    # colors
    C_background = screenState.colors["background"]
    P_text = screenState.colorPairs["body"]
    P_error = screenState.colorPairs["error_white"]
    P_title = screenState.colorPairs["title"]
    P_title_selected = screenState.colorPairs["xch"]
    P_tab_soft = screenState.colorPairs["tab_soft"]

    main_win_size = add_viewer.getmaxyx()
    main_win_size = UIgraph.Point(main_win_size[1], main_win_size[0])
    pos_orig = UIgraph.Point(1, 1)
    max_x = main_win_size.x - 2

    address = encode_puzzle_hash(address_loaders.puzzle_hash, CONF.ADD_PREFIX)
    name = None
    path = CONF.USER_ADDX_WATCHLIST
    if path.exists():
        for entry in WDB.load_csv_no_comments(path):
            if len(entry) > 1 and (str(address_loaders.puzzle_hash) == entry[0] or address == entry[0]):
                name = entry[1]
                break

    ##### title (rule 1): the watchlist name or "address", the address on its row when it fits
    title = name or "address"
    ELEMENTS.create_text_double_space(add_viewer, screenState, pos_orig, title, P_title_selected, C_background,
                                      3, True)
    pos = pos_orig + UIgraph.Point(0, 3)
    address_x = pos_orig.x + len(title) + 4 + 2
    if address_x + len(address) <= max_x:
        put_text(add_viewer, UIgraph.Point(address_x, pos_orig.y + 1), address, P_text, True)
    else:
        put_text(add_viewer, pos, address, P_text, True)
        pos += UIgraph.Point(0, 1)

    ##### status lines: the counts, the puzzle hash, to which address it is hinted
    def count(value):
        return '...' if value is None or value < 0 else f"{value:,}"
    hinted_from = main_scope.data.get('hinted_from')
    if address_loaders.balance < 0:
        balance = '...'
    elif hinted_from is not None and hinted_tab_of(hinted_from['puzzle_type']) == 'CAT':
        balance = f"{address_loaders.balance / 1000:,.3f} CAT"  # 1 CAT = 1000 mojos
    else:
        balance = f"{address_loaders.balance / XCH_MOJO:,.4f} XCH"
    # the hinted counts from the hinted groups, so they match the tabs (the cached ones are
    # from the cache build, and count also the coins the address hints to itself)
    with address_loaders.lock:
        groups = address_loaders.hinted_groups
    hinted_unspent = None if groups is None else sum(g['unspent'] for g in groups)
    hinted_total = None if groups is None else sum(g['coins'] for g in groups)
    status = (f"balance {balance} | coins {count(address_loaders.unspent_coin_count)} unspent / "
              f"{count(address_loaders.total_coin_count)} | hinted {count(hinted_unspent)} "
              f"unspent / {count(hinted_total)}")
    put_text(add_viewer, pos, status, P_text, True)
    pos += UIgraph.Point(0, 1)
    put_text(add_viewer, pos, f"puzzle hash 0x{bytes(address_loaders.puzzle_hash).hex()}", P_text)
    pos += UIgraph.Point(0, 1)

    if hinted_from is not None:
        to = hinted_from['address']
        to = f"{hinted_from['name']} ({to[:10]}…{to[-5:]})" if hinted_from['name'] else to
        text = f" hinted to {to} · {hinted_from['label']} "
        put_text(add_viewer, pos, text, screenState.colorPairs["header"], True)
        pos += UIgraph.Point(0, 1)

    # copy the address while no element is entered (the tables copy their cell with y)
    if screenState.activeScope is main_scope:
        screenState.footer_text += "| copy address=y "
        if keyboardState.yank:
            PLAT.write_clipboard(address)
            screenState.roto_clipboard.appendleft(address)

    pos += UIgraph.Point(0, 1)
    pos_tab_title = pos
    pos += UIgraph.Point(0, 2)
    max_y = main_win_size.y - pos.y - 2

    def coin_record_key_parser(dataTable):
        # coin_id is at index 4 in both inbound/outbound formats
        keys = [row[4] for row in dataTable]
        return dataTable, keys

    match tab_selected:
        ### INBOUND coins ###
        case 0:
            tab_size = UIgraph.Point(80, max_y)

            data_loader: WDB.DataChunkLoader = main_scope.data['address_loaders'].address_loader
            #loader_legend = ["confirmed_index", "spent_index", "from_add", "coin_parent", "amount", "timestamp", "parent add"]
            # TODO: coin_id is in reality the coin_parent_id -> change when createing the cache db
            loader_legend = ["confirmed_index", "spent_index", "from", "amount", "coin_id", "coin_parent_id", "timestamp"]
            column_widths = [None, None, 15, None, 15, 15, None]
            formatters = [None, None, None, UTILS.human_amount, None, None, None]
            inbound_scope = ELEMENTS.create_tab(add_viewer,
                                                screenState,
                                                main_scope,
                                                "puzzle_hash_viewer",
                                                None,
                                                None,
                                                None,
                                                False,
                                                pos,
                                                tab_size,
                                                keyboardState,
                                                ScopeActions.open_coin_record,
                                                False,
                                                False,
                                                loader_legend,
                                                column_widths,
                                                formatters,
                                                data_loader,
                                                chunk_data_parser=coin_record_key_parser)

            if toggle_coin_keys not in inbound_scope.custom_keyboard_exec:
                inbound_scope.custom_keyboard_exec[toggle_coin_keys] = toggle_coin_keyboard

        ### OUTBOUND coins ###
        case 1:
            tab_size = UIgraph.Point(80, max_y)

            data_loader: WDB.DataChunkLoader = main_scope.data['address_loaders'].address_loader_outbound
                           #["confirmed_index", "spent_index",  "puzzle_hash", "coin_parent", "amount", "timestamp"]
            loader_legend = ["confirmed_index", "spent_index", "to", "amount", "coin_id", "coin_parent_id", "timestamp"]
            column_widths = [None, None, 15, None, 15, 15, None]
            formatters = [None, None, None, UTILS.human_amount, None, None, None]
            outbound_scope = ELEMENTS.create_tab(add_viewer,
                                                  screenState,
                                                  main_scope,
                                                  "puzzle_hash_outbound_viewer",
                                                  None,
                                                  None,
                                                  None,
                                                  False,
                                                  pos,
                                                  tab_size,
                                                  keyboardState,
                                                  ScopeActions.open_coin_record,
                                                  False,
                                                  False,
                                                  loader_legend,
                                                  column_widths,
                                                  formatters,
                                                  data_loader,
                                                  chunk_data_parser=coin_record_key_parser)

            if toggle_coin_keys not in outbound_scope.custom_keyboard_exec:
                outbound_scope.custom_keyboard_exec[toggle_coin_keys] = toggle_coin_keyboard

    ### puzzle ###
        case 2:
            #text = "puzzle composition: "
            #pos += UIgraph.Point(0,2)
            #ELEMENTS.create_text(add_viewer, pos, text, P_text, True)
            #pos += UIgraph.Point(0,2)


            address_loaders: AddressLoaders = main_scope.data['address_loaders']
            with address_loaders.lock:
                puz_and_sol = address_loaders.puzzle_and_sol_rpc
                puzzle_disassembled = address_loaders.puzzle_disassembled
                unrolled_puzzles = address_loaders.unrolled_puzzles
                layered_puzzle_type = address_loaders.layered_puzzle_type
                layered_puzzle_name = address_loaders.layered_puzzle_name

            if unrolled_puzzles is None:
                # no spent coins
                pos += UIgraph.Point(0,2)
                text = "no spent coins founded"
                ELEMENTS.create_text(add_viewer, pos, text, P_text, True)

            else:
                labels = []
                data = []

                labels.append('LAYERED_PUZZLE')
                data.append('')

                labels.append('-puzzle_type')
                data.append(layered_puzzle_type)
                labels.append('-puzzle_name')
                data.append(layered_puzzle_name)


                labels.append('-sub_puzzle_list')
                data.append('')
                for n, puz in enumerate(unrolled_puzzles):
                    value = f"({n}) {puz['puzz_name']}"
                    if n == 0:
                        data[-1] = value
                    else:
                        labels.append('')
                        data.append(value)

                labels.append('-clvm')
                if puz_and_sol:
                    data.append(puz_and_sol['puzzle_reveal'])
                else:
                    data.append(None)
                labels.append('-disassembled_clvm')
                data.append(puzzle_disassembled)

                lev = 0
                labels.append('')
                data.append('')
                labels.append('UNCURRIED_PUZZLEs')
                data.append('')

                # formattin unrolled puzzles
                for puz in unrolled_puzzles:
                    labels.append('-sub_puzzle_name')
                    data.append(puz['puzz_name'])

                    labels.append('--path:')
                    data.append(puz['path'])

                    labels.append('--puzzle_disassembled')
                    data.append(puz['disassembly'])

                    labels.append('--args:')
                    data.append('')
                    # args
                    for n, arg in enumerate(puz['args']):
                        value = f"<...>(R, {n}) | {arg} "
                        if n == 0:
                            data[-1] = value
                        else:
                            labels.append('')
                            data.append(value)

                    labels.append('')
                    data.append('')



                tab_legend = ['property', 'value']
                tab_data = [labels, data]

                max_y = main_win_size.y - pos.y - 3
                min_y = max(15, len(data) + 1)
                tab_size = UIgraph.Point(80, min_y)
                tab_size = UIgraph.Point(80, max_y)

                ELEMENTS.create_tab(add_viewer,
                                    screenState,
                                    main_scope,
                                    "puzzle_data",
                                    tab_data,
                                    None,
                                    None,
                                    True,
                                    pos,
                                    tab_size,
                                    keyboardState,
                                    ScopeActions.exit_scope,
                                    False,
                                    False,
                                    tab_legend)

        ### the coins hinted to the address: one row per puzzle hash they use ###
        case 3 | 4 | 5:
            hinted_table(add_viewer, screenState, keyboardState, main_scope, address_loaders, address, name,
                         ('CAT', 'NFT', 'OTHER')[tab_selected - 3], pos, UIgraph.Point(main_win_size.x - 2, max_y))

    # run copy/paste action or other pending stuffs
    if len(screenState.pending_action) > 0:
        for i, fn in screenState.pending_action:
            fn()
        screenState.pending_action = []


    pos = pos_tab_title
    with address_loaders.lock:
        layered_puzzle_type = address_loaders.layered_puzzle_type
        cache_progress = address_loaders.cache_progress
        hinted_progress = address_loaders.hinted_progress
        hinted_loading = address_loaders.hinted_groups is None
    hinted_rows = hinted_rows_by_tab(address_loaders)

    def hinted_count(tab):
        return '...' if hinted_loading else f"{len(hinted_rows[tab]):,}"

    title_list = [" INBOUND coins ", " OUTBOUND coins ", f" PUZZLE [{layered_puzzle_type}] ",
                  f" CAT ({hinted_count('CAT')}) ", f" NFT ({hinted_count('NFT')}) ",
                  f" OTHER ({hinted_count('OTHER')}) "]
    x_end = ELEMENTS.create_tab_titles(add_viewer, screenState, main_scope, pos, title_list, tab_selected,
                                       max_x - pos.x)

    # what is still loading, next to the tabs
    texts = []
    if cache_progress is not None:
        done, total = cache_progress
        texts.append("building cache..." if total is None else f"building cache... {done:,} / {total:,} coins")
    if hinted_progress is not None:
        texts.append(f"classifying {hinted_progress[0]:,} of {hinted_progress[1]:,}")
    if texts:
        put_text(add_viewer, UIgraph.Point(x_end + 2, pos.y + 1), ' | '.join(texts), P_text, True)

    pos = UIgraph.Point(pos_orig.x, pos.y + 2)

    # save address
    banner_name = 'save_address_banner'
    save_scope: TYPES.Scope = None
    if banner_name in screenState.scopes:
        save_scope = screenState.scopes[banner_name]
    # TODO:
    # change the way the banner is drawn, checking if it is the main scope is not optimal if there are subscope inside
    if 'w' in keyboardState.keys:
        screenState.activeScope = save_scope

    if screenState.activeScope == save_scope or save_scope is not None and screenState.activeScope.name in save_scope.sub_scopes:
        ELEMENTS.create_save_address_banner(add_viewer, screenState, main_scope, address)



def screen_coin_record(stdscr, keyboardState, screenState: ScreenState, fullNodeState: FullNodeState, figlet=False):

    width = screenState.screen_size.x
    height = screenState.screen_size.y

    coin_win = createFullSubWin(stdscr, screenState, height, width)
    coin_win.bkgd(' ', curses.color_pair(screenState.colorPairs["body"]))

    active_scope: Scope = screenState.activeScope
    main_scope: Scope = active_scope.main_scope
    screenState.scope_exec_args = [screenState]
    main_scope.update()

    coin_name_hex = main_scope.data['coin_name']
    coin_name_bytes = bytes32.fromhex(coin_name_hex[2:])

    # --- load from cache db ---
    def query_db():
        with screenState.lock:
            main_scope.data['coin_loading'] = True
        try:
            cache_conn = WDB.get_connection(CONF.DB_CACHED_BLOCKCHAIN)
            db_conn = WDB.get_connection(CONF.DB_BLOCKCHAIN_RO)
            cache_cursor = cache_conn.cursor()
            row = WDB.FetchMaker.get_cached_coin_record(cache_cursor, coin_name_bytes)
            if row is None:
                db_cursor = db_conn.cursor()
                coin_row = WDB.FetchMaker.get_coin_record_by_name(db_cursor, coin_name_bytes)
                if coin_row is not None:
                    WDB.FetchMaker.cache_coin_record(db_cursor, cache_cursor, coin_row, coin_row[4])
                    cache_conn.commit()
                    row = WDB.FetchMaker.get_cached_coin_record(cache_cursor, coin_name_bytes)

            with screenState.lock:
                main_scope.data['coin_cache'] = row

            # --- check memo in cache, fetch if missing ---
            # row[13]=full_memo
            if row and row[13] is None:
                try:
                    WDB.FetchMaker.fetch_and_cache_coin_memo(cache_conn, coin_name_hex, row)
                except Exception as e:
                    logging(debug_logger, "DEBUG", f"memo cache fetch failed: {e}")
                    UTILS.logging_traceback("fetching coin memo")

                row = WDB.FetchMaker.get_cached_coin_record(cache_cursor, coin_name_bytes)

                with screenState.lock:
                    main_scope.data['coin_cache'] = row

            # hint owner and puzzle data: they call the node, so they are read here
            if row is not None:
                try:
                    raw_hint = row[14]
                    hint = bytes32(raw_hint) if UTILS.is_bytes32(raw_hint) else None
                    puzzle_info = PUZ.coin_puzzle_data(TYPES.CoinRecordRoto(row[:10]), hint)
                except Exception as e:
                    logging(debug_logger, "DEBUG", f"coin puzzle data failed: {e}")
                    UTILS.logging_traceback("coin puzzle data")
                    puzzle_info = (f"error: {e}", [], None)
                with screenState.lock:
                    main_scope.data['coin_puzzle_data'] = puzzle_info

            with screenState.lock:
                main_scope.data['coin_loading'] = False
            logging(debug_logger, "DEBUG", f"THREAD FINISHED!!!!!!!!!!!!")

        except Exception as e:
            logging(debug_logger, "DEBUG", f"coin cache load failed: {e}")
            UTILS.logging_traceback("COIN_CACHE")
            with screenState.lock:
                main_scope.data['coin_cache'] = None
        finally:
            cache_conn.close()
            db_conn.close()

    # --- cache logic ---
    def load_coin_cache():
        t = threading.Thread(target=query_db, daemon=True)
        logging(debug_logger, "DEBUG", f"THREAD START !!!!!!!!!!!!")
        t.start()

    # invalidate cache if coin changed
    if main_scope.data.get('coin_cache_name') != coin_name_hex:
        with screenState.lock:
            main_scope.data['coin_loading'] = True
            main_scope.data['coin_cache_name'] = coin_name_hex
            main_scope.data['coin_puzzle_data'] = None
        load_coin_cache()
        cache_conn = WDB.get_connection(CONF.DB_CACHED_BLOCKCHAIN)
        cache_cursor = cache_conn.cursor()
        coin_record = WDB.FetchMaker.get_cached_coin_record(cache_cursor, coin_name_bytes)
        main_scope.data['coin_cache'] = coin_record

    # subscribe once to refresh cache on new block
    def refresh_coin_cache(data):
        load_coin_cache()

    screenState.daemon_socket_dispatcher.subscribe_once(
        f'update_coin_{coin_name_hex}',
        TYPES.DaemonEvent.NEW_BLOCK,
        refresh_coin_cache
    )

    # --- end cache logic ---
    P_error = screenState.colorPairs["error_white"]
    pos = UIgraph.Point(1, 1)

    C_background = screenState.colors["background"]
    P_title_selected = screenState.colorPairs["xch"]

    with screenState.lock:
        coin_record = main_scope.data.get('coin_cache')

    text = f"coin: {coin_name_hex}"
    ELEMENTS.create_text_double_space(coin_win, screenState, pos, text, P_title_selected, C_background,
                                      3, True, inv_color=False)
    pos += UIgraph.Point(0, 4)

    if coin_record is None:
        if main_scope.data.get('coin_loading', False):
            ELEMENTS.create_text(coin_win, pos, f"Loading coin data... {main_scope.data['coin_loading']}", P_error, bold=False)
        else:
            ELEMENTS.create_text(coin_win, pos, f"Coin record not found {main_scope.data['coin_loading']}", P_error, bold=False)
        return

    labels = [
        "Coin_id / coin_name",
        "Confirmed Index",
        "Spent Index",
        "Coinbase",
        "Puzzle Hash",
        "Address",
        "Parent Coin Info / Coin_id",
        "Parent Puzzle Hash",
        "Parent Address",
        "Amount XCH",
        "Amount mojo",
        "Timestamp",
        "Record Type",
        "Child Count",
        "Coin Type",
        "Full Memo",
        "Raw Hint",
        "Hint",
    ]

    # --- Memo from cache ---
    _memo = coin_record[13]
    _memo_display = "None"
    if _memo is not None:
        try:
            raw_memo = bytes(_memo).decode('utf-8')
            if raw_memo.startswith('['):
                try:
                    parsed = json.loads(raw_memo)
                    if isinstance(parsed, list):
                        _memo_display = ", ".join(parsed)
                    else:
                        _memo_display = raw_memo
                except json.JSONDecodeError:
                    _memo_display = raw_memo
            else:
                _memo_display = raw_memo
        except UnicodeDecodeError:
            _memo_display = f"0x{bytes(_memo).hex()}"

    ## only for DEBUG
    coin_memo = WDB.FetchMaker.fetch_rpc_coin_memo(coin_name_hex, coin_record)
    coin_memo_de = ''
    if coin_memo:
        for i in json.loads(coin_memo):
            try:
                parsed = ast.literal_eval(i)
                if isinstance(parsed, bytes) and len(parsed) == 32:
                    item = encode_puzzle_hash(bytes32(parsed), CONF.ADD_PREFIX)
                else:
                    item = str(parsed)
            except Exception:
                item = i
            coin_memo_de = coin_memo_de + item + ', '
    coin_memo = coin_memo_de

    # --- Hint from cache (coin_record[14]) ---
    raw_hint = coin_record[14]
    hint = encode_puzzle_hash(bytes32(raw_hint), CONF.ADD_PREFIX) if UTILS.is_bytes32(raw_hint) else None

    values = [
        str(bytes32(coin_record[0]).hex()),
        str(coin_record[1]),
        str(coin_record[2]),
        str(bool(coin_record[3])),
        f"0x{bytes32(coin_record[4])}",
        encode_puzzle_hash(bytes32(coin_record[4]), CONF.ADD_PREFIX),
        f"0x{bytes32(coin_record[5])}", # parent coin_id
        f"0x{bytes32(coin_record[9])}",
        encode_puzzle_hash(bytes32(coin_record[9]), CONF.ADD_PREFIX) if coin_record[9] else "None",
        UTILS.xch_amount(int.from_bytes(coin_record[6], 'big') if isinstance(coin_record[6], bytes) else coin_record[6]),
        int.from_bytes(coin_record[6], 'big') if isinstance(coin_record[6], bytes) else coin_record[6],
        str(coin_record[7]),
        TYPES.CacheCoinRecordType(coin_record[8]).name if coin_record[8] is not None else "None",
        str(coin_record[10]),
        str(coin_record[11]),
        _memo_display,
        raw_hint,
        hint,
    ]

    # --- Hint owner and puzzle data (read by query_db) ---
    with screenState.lock:
        puzzle_info = main_scope.data.get('coin_puzzle_data')
    labels.append("Hint Owner")
    values.append("loading..." if puzzle_info is None else puzzle_info[0])

    if coin_memo is not None:
        labels.append("RPC Spent debug")
        values.append(str(coin_memo))

    if puzzle_info is not None and puzzle_info[1]:
        _, pairs, source = puzzle_info
        labels.append('')
        values.append('')
        # an unspent coin is read from its parent's puzzle: the data are the parent's
        labels.append('PUZZLE_DATA' if source == 'coin' else 'PUZZLE_DATA (parent coin)')
        values.append('')
        for key, value in pairs:
            labels.append(f'-{key}')
            values.append(value)

    # --- Unrolled Puzzle ---
    # Construct a temporary CoinRecordRoto from the cached row so we can reuse the new helper.
    # The raw cached table already returns columns in the expected order:
    # coin_name, confirmed_index, spent_index, coinbase, puzzle_hash,
    # coin_parent, amount, timestamp, record_type, parent_puzzle_hash
    try:
        coin_record_roto = TYPES.CoinRecordRoto(coin_record[:10])
        puzzle_record = PUZ.unroll_puzzle_from_coin_id(coin_record_roto)
    except Exception as e:
        logging(debug_logger, "DEBUG", f"unroll puzzle failed: {e}")
        UTILS.logging_traceback("unroll puzzle")
        puzzle_record = None

    if puzzle_record is not None and puzzle_record.unrolled_puzzles is not None:
        labels.append('')
        values.append('')
        labels.append('LAYERED_PUZZLE')
        values.append('')

        labels.append('-puzzle_type')
        values.append(puzzle_record.layered_puzzle_type)
        labels.append('-puzzle_name')
        values.append(puzzle_record.layered_puzzle_name)
        labels.append('-puzzle_status')
        values.append(puzzle_record.layered_puzzle_status)

        labels.append('-sub_puzzle_list')
        values.append('')
        for n, puz in enumerate(puzzle_record.unrolled_puzzles):
            value = f"({n}) {puz['puzz_name']}"
            if n == 0:
                values[-1] = value
            else:
                labels.append('')
                values.append(value)

        labels.append('-clvm')
        if puzzle_record.puzzle_and_sol_rpc:
            values.append(puzzle_record.puzzle_and_sol_rpc['puzzle_reveal'])
        else:
            values.append(None)
        labels.append('-disassembled_clvm')
        values.append(puzzle_record.puzzle_disassembled)

        labels.append('')
        values.append('')
        labels.append('UNCURRIED_PUZZLEs')
        values.append('')

        for puz in puzzle_record.unrolled_puzzles:
            labels.append('-sub_puzzle_name')
            values.append(puz['puzz_name'])

            labels.append('--path:')
            values.append(puz['path'])

            labels.append('--puzzle_disassembled')
            values.append(puz['disassembly'])

            labels.append('--args:')
            values.append('')
            for n, arg in enumerate(puz['args']):
                value = f"<...>(R, {n}) | {arg} "
                if n == 0:
                    values[-1] = value
                else:
                    labels.append('')
                    values.append(value)

            labels.append('')
            values.append('')
    # --- end unrolled puzzle ---








    # --- unrolled solution ---


    # an unspent coin has no solution yet: the node refuses the call and roto stopped
    unrolled = None
    if coin_record_roto.spent_block_index > 0:
        puzzle, solution = WDB.FetchMaker._fetch_puzzle_and_solution(coin_record_roto)
        unrolled = PUZ.unroll_puzzle_to_nodes(solution)


    if puzzle_record is not None and unrolled is not None:
        labels.append('')
        values.append('')
        labels.append('SOLUTION')
        values.append('')


        labels.append('-sub_puzzle_list')
        values.append('')
        for n, puz in enumerate(unrolled):
            value = f"({n}) {puz['puzz_name']}"
            if n == 0:
                values[-1] = value
            else:
                labels.append('')
                values.append(value)


        labels.append('')
        values.append('')
        labels.append('UNCURRIED_PUZZLEs')
        values.append('')

        for puz in unrolled:
            labels.append('-sub_puzzle_name')
            values.append(puz['puzz_name'])

            labels.append('--path:')
            values.append(puz['path'])

            labels.append('--puzzle_disassembled')
            values.append(puz['disassembly'])

            labels.append('--args:')
            values.append('')
            for n, arg in enumerate(puz['args']):
                value = f"<...>(R, {n}) | {arg} "
                if n == 0:
                    values[-1] = value
                else:
                    labels.append('')
                    values.append(value)

            labels.append('')
            values.append('')















    # --- end unrolled solution ---



    tab_legend = ['property', 'value']
    tab_data = [labels, values]

    max_y = height - pos.y - 3
    tab_size = UIgraph.Point(min(120, width - 4), max_y)

    ELEMENTS.create_tab(coin_win,
                        screenState,
                        main_scope,
                        "coin_data_tab",
                        tab_data,
                        None,
                        None,
                        True,      # transpose
                        pos,
                        tab_size,
                        keyboardState,
                        ScopeActions.exit_scope,
                        False,
                        False,
                        tab_legend,
                        no_cache=True)


def screen_full_node_search(stdscr, keyboardState: KeyboardState, screenState: ScreenState, fullNodeState: FullNodeState, figlet=False):

    # search for anything.
    # At the moment only puzzle are supported

    # warm US: xch12pc7qk46t8aktdsd7ss96pctdp0236sexakfsdvsqefuqyyll3hqzhnldc
    # ACH: xch1lv34uumcyg892zrv35rhrx87hu5nx87em7zcag5nc2vjecupkdzspc9xn6

    height = screenState.screen_size.y
    width = screenState.screen_size.x

    active_scope: Scope = screenState.activeScope
    main_scope: Scope = active_scope.main_scope
    screenState.scope_exec_args = [screenState]
    main_scope.update_2d()

    if 'lapper' not in main_scope.data:
        main_scope.data["lapper"] = UTILS.Timer('block_band')
    lapper = main_scope.data["lapper"]
    lapper.start()
    lapper.clocking("begin")

    # sub win
    node_data = createFullSubWin(stdscr, screenState, height, width)
    node_data.bkgd(' ', curses.color_pair(screenState.colorPairs["body"]))

    # colors
    P_text = screenState.colorPairs["body"]
    P_error = screenState.colorPairs["error"]

    # address loaders init

    if 'address_loaders' not in main_scope.data:
        address_loaders = AddressLoaders()
        main_scope.data['address_loaders'] = address_loaders

    #### prompts
    pos = UIgraph.Point(2,1)
    pos_original_x = pos.x
    pre_text = "Search: "
    prompt_lenght = min(80, width - 4)
    scope_search = ELEMENTS.create_prompt(node_data, screenState, keyboardState, main_scope, 'search', pos,
                                          pre_text, prompt_lenght, P_text, True, False, custom_scope_function=ScopeActions.press_enter)

    new_prompt_lenght = 30
    if pos.x + prompt_lenght + 3 + new_prompt_lenght < width:
        pos += UIgraph.Point(prompt_lenght + 3,0)
    else:
        pos = UIgraph.Point(pos_original_x, pos.y + 3)

    prompt_lenght = new_prompt_lenght
    pre_text = "Start height: "
    scope_start_height = ELEMENTS.create_prompt(node_data, screenState, keyboardState, main_scope, 'start_height', pos,
                                                pre_text, new_prompt_lenght, P_text, True, False, custom_scope_function=ScopeActions.press_enter)

    new_prompt_lenght = 30
    if pos.x + prompt_lenght + 3 + new_prompt_lenght < width:
        pos += UIgraph.Point(prompt_lenght + 3,0)
    else:
        pos = UIgraph.Point(pos_original_x, pos.y + 3)

    prompt_lenght = new_prompt_lenght
    pre_text = "End height: "
    scope_end_height = ELEMENTS.create_prompt(node_data, screenState, keyboardState, main_scope, 'end_height', pos,
                                              pre_text, prompt_lenght, P_text, True, False, custom_scope_function=ScopeActions.press_enter)

    button_name = u'remove_spent_coins'
    button_lenght = len(button_name) + 6
    pos += UIgraph.Point(0,-1)  # move buttons up
    if pos.x + prompt_lenght + 3 + button_lenght < width:
        pos += UIgraph.Point(prompt_lenght + 3,0)
    else:
        pos = UIgraph.Point(pos_original_x, pos.y + 3)

    scope_remove_spent_coins: Scope = ELEMENTS.create_button(node_data, screenState, main_scope, button_name, pos, custom_scope_function=ScopeActions.change_button_bool, button_type='boolean')
    address_loaders: AddressLoaders = main_scope.data['address_loaders']

    button_name = u'remove_self_transactions'
    old_button_length = button_lenght
    button_lenght = len(button_name) + 6
    if pos.x + prompt_lenght + 3 + button_lenght < width:
        pos += UIgraph.Point(old_button_length + 5,0)
    else:
        pos = UIgraph.Point(pos_original_x, pos.y + 3)

    scope_remove_self_transactions: Scope = ELEMENTS.create_button(node_data, screenState, main_scope, button_name, pos, custom_scope_function=ScopeActions.change_button_bool, button_type='boolean')

    pos = UIgraph.Point(pos_original_x, pos.y + 3)

    button_name = 'search_button'
    button_lenght = len(button_name) + 6
    scope_search_button: Scope = ELEMENTS.create_button(node_data, screenState, main_scope, button_name, pos, custom_scope_function=ScopeActions.press_enter, button_type='execution')
    pos_search_err = pos.deepcopy() + UIgraph.Point(button_lenght + 3, 1)
    pos += UIgraph.Point(0,4)


    # the prompt shuuld avtivate the sql query, that create the list.
    # i will not go with chunks, i will try to handle them in a list. or not?
    # prompot > hash, spent coin, min and max height on the advanced

    # we need chunks, the chunks loader have to update.

    ########################

    lapper.clocking("pre_init")

    # parse data
    # parse halways start, end and bool and check the data on esc and enter
    # save on scope.data and check for change
    # if change start counter for one sec, before updating or waiting for enter???????????


    #if 'parameters' not in main_scope.data:
    #    main_scope.data['parameters'] = [None, uint32(0), uint32((2**32) - 1), False, False]
    #    # search_value, start, end, remove_spent_coins

    run_loader = False
    if 'is_address' not in main_scope.data:
        main_scope.data['is_address'] = False
    is_address = main_scope.data['is_address']

    if 'invalid_data_err' not in main_scope.data:
        main_scope.data['invalid_data_err'] = {}
    invalid_data_err = main_scope.data['invalid_data_err']

    if 'pressed_enter' in scope_start_height.data and scope_start_height.data['pressed_enter']:
        scope_start_height.data['pressed_enter'] = False
        prompt = scope_start_height.data['prompt']
        input_type = UTILS.classify_number(prompt)
        if len(prompt) == 0:
            invalid_data_err.pop('start', None)
            address_loaders.start_height = uint32(0)
            if is_address:
                run_loader = True
        elif input_type != 'int':
            invalid_data_err['start'] = "start_height must be a valid int | "
            scope_start_height.data['valid_data'] = False
        else:
            invalid_data_err.pop('start', None)
            height = int(prompt)
            address_loaders.start_height = height
            if is_address:
                run_loader = True

    if 'pressed_enter' in scope_end_height.data and scope_end_height.data['pressed_enter']:
        scope_end_height.data['pressed_enter'] = False
        prompt = scope_end_height.data['prompt']
        input_type = UTILS.classify_number(prompt)
        if len(prompt) == 0:
            invalid_data_err.pop('end', None)
            address_loaders.end_height = uint32(2**32 - 1)
            if is_address:
                run_loader = True
        elif input_type != 'int':
            invalid_data_err['end'] = "end_height must be a valid int | "
            scope_end_height.data['valid_data'] = False
        else:
            invalid_data_err.pop('end', None)
            height = int(prompt)
            address_loaders.end_height = height
            if is_address:
                run_loader = True

    if 'pressed_enter' in scope_search.data and scope_search.data['pressed_enter']:

        scope_search.data['pressed_enter'] = False
        prompt = scope_search.data['prompt']

        # check if it an hex value, an check the length
        # what could be? coin_id or address
        # if it is not an hex value it could be an address?
        # if it is 

        search_value: bytes32 = UTILS.string_to_bytes32(prompt)
        if search_value is not None:
            # Check if it's a coin_id
            is_coin_id = False
            db_conn = WDB.get_connection(CONF.DB_BLOCKCHAIN_RO)
            try:
                cursor = db_conn.cursor()
                cursor.execute("SELECT coin_name FROM coin_record WHERE coin_name = ?", (search_value,))
                coin_record = cursor.fetchone()
                logging(debug_logger, "DEBUG", f"COIN RECORDDDDD: {coin_record}")
                if coin_record:
                    is_coin_id = True
                    main_scope.data['is_address'] = False
            except Exception as e:
                logging(debug_logger, "ERROR", f"Coin ID check failed: {e}")
            finally:
                db_conn.close()
 
            if is_coin_id:
                coin_name = f"0x{bytes(search_value).hex()}"
                new_scope = Scope(f"coin_{coin_name}", screen_coin_record, screenState)
                new_scope.parent_scope = main_scope
                new_scope.data['coin_name'] = coin_name
                new_scope.exec = None
                screenState.activeScope = new_scope
                return
            else:
                invalid_data_err.pop('add', None)
                address_loaders.puzzle_hash = search_value
                run_loader = True
                main_scope.data['is_address'] = True
                main_scope.select_sub_scope_2d(scope_search_button)
 
        else:
            invalid_data_err['add'] = "the address or the hex string is not valid | "
            scope_search.data['valid_data'] = False


    if scope_remove_spent_coins.changed:
        scope_remove_spent_coins.changed = False
        address_loaders.remove_spent_coins = scope_remove_spent_coins.bool
        run_loader = True
    else:
        if scope_remove_spent_coins.bool != address_loaders.remove_spent_coins:
            scope_remove_spent_coins.bool = not scope_remove_spent_coins


    if scope_remove_self_transactions.changed:
        scope_remove_self_transactions.changed = False
        address_loaders.remove_self_transactions = scope_remove_self_transactions.bool
        run_loader = True
    else:
        if scope_remove_self_transactions.bool != address_loaders.remove_self_transactions:
            scope_remove_self_transactions.bool = not scope_remove_self_transactions


    # pharsing errors message
    err_msg = ''
    for lab, text in invalid_data_err.items():
        err_msg += text
    ELEMENTS.create_text(node_data, pos_search_err, err_msg, P_error, bold=True)
    main_scope.data['invalid_data_err'] = invalid_data_err

    ###########################
    # implemnt chunk support

    #if 'address_loader' not in main_scope.data:
    if run_loader:

        address_loaders = main_scope.data['address_loaders']

        main_scope.data['address_loaders'] = address_loaders

        #load_the_loaders(address_loaders)  # DEBUG
        loaders_thread: threading.Thread = threading.Thread(target=load_the_loaders,
                                                            args=(screenState, address_loaders,),
                                                            kwargs={'update_cache': True},
                                                            daemon=True)
        loaders_thread.start()
        loaders_thread.setName("loading address")
        with screenState.lock:
            screenState.running_threads.append(loaders_thread)


        # load the preview in background, it can be slow for big puzzle hashes
        # TODO: the preview should be light, simplify it (see WDB.FetchMaker.puzzle_hash_preview)
        # each search has its own id, an old preview thread stops when a new search starts
        preview_id = main_scope.data.get('preview_id', 0) + 1
        main_scope.data['preview_id'] = preview_id
        main_scope.data['tab_preview'] = None
        main_scope.data['preview_status'] = "loading preview..."

        def load_preview(puzzle_hash, start_height, end_height, remove_spent_coins, remove_self_transactions):
            def is_old():
                return main_scope.data.get('preview_id') != preview_id

            def progress(height):
                if not is_old():
                    main_scope.data['preview_status'] = f"loading preview... scanning height {height:,}"

            db_conn = WDB.get_connection(CONF.DB_BLOCKCHAIN_RO)
            try:
                preview = WDB.FetchMaker.puzzle_hash_preview(
                    db_conn, puzzle_hash, 100,
                    start_height=start_height,
                    end_height=end_height,
                    remove_spent_coins=remove_spent_coins,
                    remove_self_transactions=remove_self_transactions,
                    progress=progress,
                    stop=is_old)
                if preview is not None and not is_old():
                    main_scope.data['tab_preview'] = preview
                    main_scope.data['preview_status'] = None
            except Exception as e:
                logging(debug_logger, "DEBUG", f"preview ERROR{e}")
                UTILS.logging_traceback("TAB_PREV")
                if not is_old():
                    main_scope.data['preview_status'] = f"preview error: {e}"
            finally:
                db_conn.close()

        with address_loaders.lock:
            preview_args = (address_loaders.puzzle_hash, address_loaders.start_height, address_loaders.end_height,
                            address_loaders.remove_spent_coins, address_loaders.remove_self_transactions)
        preview_thread = threading.Thread(target=load_preview, args=preview_args, daemon=True)
        preview_thread.start()
        preview_thread.setName("loading preview")
        with screenState.lock:
            screenState.running_threads.append(preview_thread)



    lapper.clocking("pressed enter")
    if main_scope.data.get('preview_status'):
        ELEMENTS.create_text(node_data, pos, main_scope.data['preview_status'], P_text, bold=True)
        pos += UIgraph.Point(0, 2)

    if 'tab_preview' in main_scope.data and main_scope.data['tab_preview'] is not None:

        ELEMENTS.create_text(node_data, pos, 'preview', P_text, bold=True, underline=True)
        pos += UIgraph.Point(0, 2)

        tab_size = UIgraph.Point(80, 15)

        preview_coin_record = main_scope.data['tab_preview']
        preview_data = []
        for i in preview_coin_record:
            coin_data = i.to_list_inbound()
            del coin_data[2]  # remove 'from' data,
            preview_data.append(coin_data)

        loader_legend = ["confirmed_index", "spent_index", "amount", "coin_id", "coin_parent_id", "timestamp"]
        column_widths = [None, None, None, 15, 15, None]
        formatters = [None, None, UTILS.human_amount, None, None, None]
        print(preview_data)

        ELEMENTS.create_tab(node_data,
                            screenState,
                            main_scope,
                            "preview",
                            preview_data,
                            None,
                            None,
                            False,
                            pos,
                            tab_size,
                            keyboardState,
                            ScopeActions.exit_scope,
                            False,
                            False,
                            loader_legend,
                            column_widths,
                            formatters)
        pos += UIgraph.Point(0, tab_size.y + 2)


    #block_legend = ['height', 'header hash', 'block type']
    main_win_size = node_data.getmaxyx()
    main_win_size = UIgraph.Point(main_win_size[1], main_win_size[0])

    #preview
    pos += UIgraph.Point(0, 2)

    max_y = main_win_size.y - pos.y - 3
    tab_size = UIgraph.Point(100, max_y)



    if 'address_loaders' in main_scope.data and main_scope.data['address_loaders'].address_loader is not None:
        lapper.clocking("init tab")
        tab_size = UIgraph.Point(80, max_y)

        lapper.clocking("into coin rec")
        data_loader: WDB.DataChunkLoader = main_scope.data['address_loaders'].address_loader
        lapper.clocking("coin rec loaded")

        loader_legend = ["confirmed_index", "spent_index", "from", "amount", "coin_id", "coin_parent_id", "timestamp"]
        column_widths = [None, None, 15, None, 15, 15, None]
        formatters = [None, None, None, UTILS.human_amount, None, None, None]

        #ELEMENTS.create_tab(node_data,
        #                    screenState,
        #                    main_scope,
        #                    "puzzle_hash_viewer",
        #                    None,
        #                    None,
        #                    None,
        #                    False,
        #                    pos,
        #                    tab_size,
        #                    keyboardState,
        #                    ScopeActions.exit_scope,
        #                    False,
        #                    False,
        #                    loader_legend,
        #                    column_widths,
        #                    formatters,
        #                    data_loader)
        lapper.clocking("iend tab")

    lapper.clocking('end tab')
    #records = RPC.call_rpc_node('get_coin_records_by_puzzle_hash')

    # run copy/paste action or other pending stuffs
    if len(screenState.pending_action) > 0:
        for i, fn in screenState.pending_action:
            fn()
        screenState.pending_action = []
    lapper.clocking('end end')
    lapper.end()
    print(lapper)

    if 'pressed_enter' in scope_search_button.data and scope_search_button.data['pressed_enter']:
        # open a new win

        scope_add_viewer: Scope = Scope("add_viewer", screen_address_viewer, screenState)
        scope_add_viewer.parent_scope = main_scope
        scope_add_viewer.data['address_loaders'] = main_scope.data['address_loaders']
        scope_add_viewer.exec = None
        screenState.activeScope = scope_add_viewer

        scope_search_button.data['pressed_enter'] = False


# tabs of a selected block: title, name of the table
BLOCK_TABS = [('DETAILS', 'current_bloc'),
              ('COINS ADDED', 'block_coins_added'),
              ('COINS REMOVED', 'block_coins_removed'),
              ('PUZZLE TYPES', 'block_puzzle_types'),
              ('SPEND BUNDLES', 'block_spend_bundles')]  # only if the block has some
BLOCK_TABS_WITH_COUNT = ('block_coins_added', 'block_coins_removed', 'block_spend_bundles')
BLOCK_COINS_LEGEND = {'block_coins_added': ['coin id', 'amount [mojo]', 'origin', 'spent at', 'puzzle hash'],
                      'block_coins_removed': ['coin id', 'amount [mojo]', 'puzzle type', 'created at', 'puzzle hash']}
BLOCK_BUNDLES_LEGEND = ['bundle id', 'coins', 'cost', 'fee [XCH]', 'seen in']
BLOCK_PUZZLE_TYPES_LEGEND = ['puzzle type', 'coins', 'execution cost', 'condition cost', 'byte cost (estimate)', 'total cost', 'of the block']
MEMPOOL_BLOCK_TXS_TAB = 'mempool_block_txs'
BLOCK_DATA_CACHE_SIZE = 8  # blocks kept in memory
BLOCK_DATA_MAX_AGE = 60  # s, a coin added to a block can be spent later: read it again
BLOCK_DATA_ERROR_MAX_AGE = 5  # s, try again after an error


def tab_count_text(count: int = None) -> str:
    """Count for a tab title, always 4 characters aligned on the right: 10k from 10,000.
    Blank if the count is not known yet."""
    if count is None:
        return ' ' * 4
    return f"{count if count < 10_000 else f'{count // 1000}k':>4}"


def block_tab_rows(block: WDB.BlockState) -> dict:
    """Rows of the coin tabs of a block. Slow: the node DB and the node RPC"""
    added, removed = WDB.block_coins(DB_BLOCKCHAIN_RO, block.height)
    kinds, coin_puzzles, bundles = [], {}, []
    if block.is_transaction_block and removed:
        kinds, coin_puzzles, coin_solutions = SCAN.block_spends_by_puzzle(SCAN.CATALOG, block.header_hash,
                                                                          block.height, block.cost)
        bundles = SCAN.block_spend_bundles(SCAN.MEMPOOL_SCANNER, coin_solutions)

    added.sort(key=lambda coin: -coin[1])
    removed.sort(key=lambda coin: -coin[1])

    def height_text(height):
        return f"{height:,}" if height > 0 else 'unspent'

    added_rows = [[f"0x{c[0]}", f"{c[1]:,}", 'reward' if c[3] else 'spend', height_text(c[5]), f"0x{c[2]}"]
                  for c in added]
    removed_rows = [[f"0x{c[0]}", f"{c[1]:,}", coin_puzzles.get(c[0], ''), height_text(c[4]), f"0x{c[2]}"]
                    for c in removed]

    def total_cost(kind):
        return sum(kind[2:]) if kind[2] is not None else 0

    def number(value):
        return f"{value:,}" if value is not None else '-'

    def share(cost):
        return f"{cost / block.cost * 100:.1f}%" if block.cost else '-'

    kinds_rows = [[k[0], k[1], number(k[2]), number(k[3]), number(k[4]),
                   number(total_cost(k)) if k[2] is not None else '-',
                   share(total_cost(k)) if k[2] is not None else '-']
                  for k in sorted(kinds, key=lambda k: (-total_cost(k), -k[1]))]
    if kinds_rows:
        kinds_rows.append(['total', sum(k[1] for k in kinds), number(sum(k[2] or 0 for k in kinds)),
                           number(sum(k[3] or 0 for k in kinds)), number(sum(k[4] or 0 for k in kinds)),
                           number(sum(total_cost(k) for k in kinds)), share(sum(total_cost(k) for k in kinds))])

    bundles_rows = [[f"0x{b[0]}", b[1], number(b[2]), f"{b[3] / XCH_MOJO:.6f}" if b[3] is not None else '-', b[4]]
                    for b in bundles]

    return {'block_spend_bundles': (bundles_rows, [b[0] for b in bundles]),
            'block_coins_added': (added_rows, [row[0] for row in added_rows]),
            'block_coins_removed': (removed_rows, [row[0] for row in removed_rows]),
            'block_puzzle_types': (kinds_rows, None)}


def selected_block_tab_rows(main_scope: Scope, screenState: ScreenState, block: WDB.BlockState):
    """Rows of the coin tabs of a block, read in a thread: None until they are there, or an
    {'error': text}. Moving along the band, only the block selected when the thread ends is
    read next."""
    cache = main_scope.data.setdefault('block_tab_rows', {})
    key = block.header_hash
    cached = cache.get(key)
    max_age = BLOCK_DATA_ERROR_MAX_AGE if cached and 'error' in cached['rows'] else BLOCK_DATA_MAX_AGE
    if cached and time.time() - cached['read_at'] < max_age:
        return cached['rows']

    thread = main_scope.data.get('block_tab_rows_thread')
    if thread is None or not thread.is_alive():

        def read_rows():
            try:
                rows = block_tab_rows(block)
            except Exception as e:
                rows = {'error': str(e)}
                logging(debug_logger, "DEBUG", f"BLOCK TABS error on block {block.height}: {e}")
            cache.pop(key, None)
            while len(cache) >= BLOCK_DATA_CACHE_SIZE:
                cache.pop(next(iter(cache)))
            cache[key] = {'rows': rows, 'read_at': time.time()}

        thread = threading.Thread(target=read_rows, daemon=True, name='block tab rows')
        thread.start()
        main_scope.data['block_tab_rows_thread'] = thread
        screenState.running_threads.append(thread)

    return cached['rows'] if cached else None


def table_for_tab(main_scope: Scope, screenState: ScreenState, tab_name: str, signature, rows: list):
    """The table to give to create_tab for rows that are kept between frames. create_tab removes
    from its table the columns that do not fit, and its frame cache compares only the first and
    the last row: a new copy and an empty frame cache, only when the rows or the width change."""
    shown = main_scope.data.setdefault('tables_shown', {})
    name = f"{main_scope.id}_{tab_name}"
    signature = (signature, screenState.screen_size.x)
    if name not in shown or shown[name][0] != signature:
        shown[name] = (signature, [list(row) for row in rows])
        if name in screenState.scopes:
            screenState.scopes[name].data['cached_data_table'] = None
            screenState.scopes[name].data['column_sizes'] = None
    return shown[name][1]


def open_block_coin(scope: Scope, screenState: ScreenState, coin_name: str = None):
    if coin_name:
        ScopeActions.open_coin_record(scope, screenState, coin_name)


def open_spend_bundle(scope: Scope, screenState: ScreenState, tx_id: str = None):
    if tx_id:
        ScopeActions.open_transaction(scope, screenState, tx_id)


def go_to_block(scope_go_to: Scope, main_scope: Scope, block_band_scope: Scope, blocks_loader: WDB.DataChunkLoader,
                height_last_block: int, screenState: ScreenState):
    """When enter is pressed in the go to block prompt, select the height or the hash written
    (main_scope.cursor_x), and move the block band there if there is one (block_band_scope)"""
    if not scope_go_to.data.get('pressed_enter'):
        return
    scope_go_to.data['pressed_enter'] = False
    prompt = scope_go_to.data['prompt']
    input_type = UTILS.classify_number(prompt)
    height = None

    match input_type:
        case 'int':
            input = int(prompt)
            if input <= height_last_block and input >= 0:
                height = input
            else:
                scope_go_to.data['valid_data'] = False
                scope_go_to.data["invalid_data_message"] = 'height out of range'

        case 'hex':

            prompt = prompt.removeprefix("0x").removeprefix("0X")
            if len(prompt) == 64:
                hash = bytes32.fromhex(prompt)
                conn = blocks_loader.create_sql_conneciton()
                try:
                    table = 'full_blocks'
                    fetcher = WDB.make_sql_fetcher(table)
                    block = fetcher(conn, 0, 1, filters={'header_hash':hash})
                    if len(block) < 1:
                        scope_go_to.data['valid_data'] = False
                        scope_go_to.data["invalid_data_message"] = 'hash not found'
                    else:
                        height = block[0][2]  # from the tuple select the third element > block_height
                except Exception as e:
                    logging(debug_logger, "DEBUG", f"block band validate input{e}")
                    UTILS.logging_traceback("BLOCK_BAND")
                finally:
                    conn.close()
            else:
                scope_go_to.data['valid_data'] = False
                scope_go_to.data["invalid_data_message"] = 'hash must be 32 bytes'

        case 'invalid':
            scope_go_to.data['valid_data'] = False
            scope_go_to.data["invalid_data_message"] = 'invalid input. Use int or hash'

    if height or height == 0:
        scope_go_to.data['prompt'] = ''
        scope_go_to.data['cursor'] = 0
        main_scope.cursor_x = height
        if block_band_scope is not None:
            blocks_loader.update_offset(height)
            blocks_loader.start_updater_thread()

            # offset selected block on the right if possible
            right_block_offset = 2
            if height_last_block - height < right_block_offset:
                right_block_offset = 0
            block_band_scope.data["idx_last_item"] = height + right_block_offset
        ScopeActions.select_next_scope(scope_go_to, screenState)


def screen_blocks(stdscr, keyboardState: KeyboardState, screenState: ScreenState, fullNodeState: FullNodeState, figlet=False):

    active_scope: Scope = screenState.activeScope
    main_scope: Scope = active_scope.main_scope
    screenState.scope_exec_args = [screenState]
    main_scope.update()

    # load blockchain database
    ## TODO: move it on startup

    full_node_meta: FullNodeMeta = fullNodeState.deepcopy_meta()
    #print("size: ", deep_getsizeof(full_node_meta))
    #print("size2: ", asizeof.asizeof(full_node_meta))

    height_last_block = full_node_meta.peak_height

    SCAN.MEMPOOL_SCANNER.want_fast()
    mempool_blocks = SCAN.mempool_blocks(SCAN.MEMPOOL_SCANNER.snapshot())

    # load blocks
    with fullNodeState.lock:
        blocks_loader: WDB.DataChunkLoader = fullNodeState.blocks_loader

    ### colors
    P_text = screenState.colorPairs["body"]
    P_foot = screenState.colorPairs["footer"]
    P_synced = screenState.colorPairs["block_band_synced"]
    P_syncing = screenState.colorPairs["block_band_syncing"]
    P_no_sync = screenState.colorPairs["block_band_no_sync"]

    ### sub win
    height = screenState.screen_size.y
    width = screenState.screen_size.x

    if 'peak_timestamp' not in main_scope.data:
        main_scope.data["peak_timestamp"] = "None"


    # nLinesUsed = screenState.headerLines + screenState.footerLines
    # node_data = stdscr.subwin(height - nLinesUsed, width, screenState.headerLines, 0)
    node_data = createFullSubWin(stdscr, screenState, height, width)
    node_data.bkgd(' ', curses.color_pair(screenState.colorPairs["body"]))

    pos = UIgraph.Point(2,1)
    main_win_size = node_data.getmaxyx()
    main_win_size = UIgraph.Point(main_win_size[1], main_win_size[0])
    block_band_size = UIgraph.Point(main_win_size.x - pos.x * 2, 10)

    # node data
    genesis_challenge = full_node_meta.genesis_challenge
    network_name = full_node_meta.network_name
    difficulty = full_node_meta.difficulty
    synced = full_node_meta.synced
    sync_mode = full_node_meta.sync_mode
    sub_slot_iters = full_node_meta.sub_slot_iters
    space = full_node_meta.net_space
    node_id = full_node_meta.node_id
    peak_height = full_node_meta.peak_height
    peak_timestamp = full_node_meta.peak_timestamp
    if peak_timestamp:
        peak_timestamp = datetime.fromtimestamp(peak_timestamp).strftime('%Y-%m-%d %H:%M:%S')
        #main_scope.data["peak_timestamp"]
    #else:
    #    peak_timestamp = main_scope.data["peak_timestamp"]

    ### node summary
    local = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    sync_status = "synced"
    peak_height_header = peak_height

    P_header = P_synced
    if not synced:
        if sync_mode:
            P_header = P_syncing
            sync_status = "syncing"
        else:
            P_header = P_no_sync
            sync_status = "not syncing"

        sync_max_block = full_node_meta.sync_tip_height
        sync_current_block = full_node_meta.sync_progress_height
        peak_height_header = f"{sync_current_block}/{sync_max_block} ({sync_max_block - sync_current_block} behind)"


    local_time = f"local time: {local}"
    chain_time = f"chain time: {peak_timestamp}"

    text_list = []
    text_list.append(f"network: {network_name}")
    text_list.append(f"sync status: {sync_status}")
    text_list.append(f"peak: {peak_height}")
    text_list.append(f"netspace: {space[0]:.3f}{space[1]}")

    spacing = ' ' * 4
    tot_len = len(local_time + spacing)
    text = ''
    for i in text_list:
        tot_len += len(str(i))
        if tot_len < block_band_size.x:
            text = text + str(i) + spacing

    ELEMENTS.create_text(node_data, pos, ' ' * block_band_size.x, P_header, True, inv_color=True)
    ELEMENTS.create_text(node_data, pos, text, P_header, True, inv_color=True)
    ELEMENTS.create_text_aligned(node_data, pos, f"chain time: {peak_timestamp}", P_header, align_h=2, bold=True, inv_color=True)
    # local/chain time superimposition
    pos_local = pos + UIgraph.Point(0, 1)
    #ELEMENTS.create_text(node_data, pos_local, ' ' * block_band_size.x, P_text, True, inv_color=True)
    ELEMENTS.create_text_aligned(node_data, pos_local, f"local time: {local}", P_text, align_h=2, bold=True, inv_color=False)
    pos += UIgraph.Point(0, 2)

    pre_text = "Go to block: "
    prompt_lenght = min(80, width - 4)
    scope_go_to = ELEMENTS.create_prompt(node_data, screenState, keyboardState, main_scope, 'go to block', pos,
                                         pre_text, prompt_lenght, P_text, True, False, custom_scope_function=ScopeActions.press_enter)
    pos += UIgraph.Point(0,3)

    ### ←→ move the band only from the band and the go to block prompt, on the tabs they switch
    ### the tab. The keys are applied after the screen: take them away from main_scope.cursor_x
    block_tab_names = [name for _, name in BLOCK_TABS]
    tab_was_selected = False
    tab_step = 0
    selected_scope = main_scope.sub_scope_selected
    if (screenState.activeScope is main_scope and selected_scope is not None
            and selected_scope is not scope_go_to and selected_scope.name != 'block_band'):
        if selected_scope.name.removeprefix(f"{main_scope.id}_") in block_tab_names:
            tab_was_selected = True
            tab_step = int(keyboardState.moveRight) - int(keyboardState.moveLeft)
        keyboardState.moveLeft = False
        keyboardState.moveRight = False

    ### block band
    block_band_scope = None
    if blocks_loader is not None:

        block_band_scope = ELEMENTS.create_block_band(stdscr, keyboardState, screenState, main_scope,
                                                      "block_band", pos, block_band_size, mempool_blocks,
                                                      blocks_loader, height_last_block, synced)

        go_to_block(scope_go_to, main_scope, block_band_scope, blocks_loader, height_last_block, screenState)


    pos += UIgraph.Point(0, block_band_size.y + 0)

    # show data

    tables_drawn = []
    idx_mempool_block = main_scope.cursor_x - (height_last_block + 2)  # after the peak and the separator

    if block_band_scope is None:
        pass  # no blocks DB
    elif synced and 0 <= idx_mempool_block < len(mempool_blocks):
        mempool_block: WDB.MempoolBlock = mempool_blocks[idx_mempool_block]
        now = time.time()
        put_text(node_data, pos + UIgraph.Point(1, 0),
                 f"mempool_{idx_mempool_block}: {len(mempool_block.transactions):,} transactions, highest fee per cost first",
                 P_text)
        pos += UIgraph.Point(0, 1)
        max_y = main_win_size.y - pos.y - 3
        if max_y > 4:
            tx_ids = [tx.tx_id for tx in mempool_block.transactions]
            rows = [mempool_tx_row(tx, now) for tx in mempool_block.transactions]
            table = table_for_tab(main_scope, screenState, MEMPOOL_BLOCK_TXS_TAB, (tx_ids, int(now)), rows)
            txs_scope = ELEMENTS.create_tab(node_data,
                                            screenState,
                                            main_scope,
                                            MEMPOOL_BLOCK_TXS_TAB,
                                            table,
                                            tx_ids or None,
                                            None,
                                            False,
                                            pos,
                                            UIgraph.Point(80, max_y),
                                            keyboardState,
                                            open_spend_bundle,
                                            True,
                                            False,
                                            list(MEMPOOL_TX_LEGEND))
            txs_scope.exec_esc = ScopeActions.exit_scope
            tables_drawn.append(txs_scope)

    elif block_band_scope.data['on_peak']:

        #ELEMENTS.create_text(node_data, pos, "chia show -s       ", P_text, True, inv_color=True)
        #pos += UIgraph.Point(0, 2)

        # chia show data
        chia_show_data = []
        chia_show_label = []

        chia_show_label.append("Node ID")
        chia_show_data.append(node_id)

        chia_show_label.append("Port")
        chia_show_data.append(full_node_port)

        chia_show_label.append("RPC port")
        chia_show_data.append(full_node_rpc_port)

        chia_show_label.append("Genesis Challenge")
        chia_show_data.append(genesis_challenge)

        peak_hash = full_node_meta.peak_header_hash
        #peak_height = full_node_meta.peak_height
        #peak_timestamp = full_node_meta.peak_timestamp

        if synced:
            chia_show_label.append(f"Current Blockchain Status: Full Node Synced. Height")
            chia_show_data.append(peak_height)

            #chia_show_label.append(f"Peak: Hash")
            #chia_show_data.append(peak_hash)

        elif peak_height is not None and sync_mode:
            sync_max_block = full_node_meta.sync_tip_height
            sync_current_block = full_node_meta.sync_progress_height

            chia_show_label.append(f"Current Blockchain Status: Syncing")
            chia_show_data.append(f"{sync_current_block}/{sync_max_block}")

            chia_show_label.append("behind")
            chia_show_data.append(f"{sync_max_block - sync_current_block}")

        elif peak_height is not None:
            chia_show_label.append(f"Current Blockchain Status: Not Synced. Peak height")
            chia_show_data.append(peak_height)

        else:
            chia_show_label.append("Searching for an initial chain")
            chia_show_data.append("You may be able to expedite with 'chia peer full_node -a host:port' using a known node.")

            chia_show_label.append(f"Finished challenge")
            chia_show_data.append(full_node_meta.finished_challenge_slot_hashes)

            chia_show_label.append("infused")
            chia_show_data.append(full_node_meta.finished_infused_challenge_slot_hashes)

            chia_show_label.append("Reward")
            chia_show_data.append(full_node_meta.finished_reward_slot_hashes)

            chia_show_label.append(f"prev hash")
            chia_show_data.append(full_node_meta.prev_hash)

            chia_show_label.append(f"prev transaction hash")
            chia_show_data.append(full_node_meta.prev_transaction_block_hash)

        if peak_height is not None:
            chia_show_label.append(f"Peak - Hash")
            chia_show_data.append(peak_hash)

            chia_show_label.append("Peak - Time")
            chia_show_data.append(peak_timestamp)

            chia_show_label.append("Peak - Height")
            chia_show_data.append(peak_height)

            chia_show_label.append(f"Estimated network space {space[1]}")
            chia_show_data.append(f"{space[0]:.4f}")


            chia_show_label.append(f"Current difficulty")
            chia_show_data.append(difficulty)

            chia_show_label.append("Current VDF sub_slot_iters")
            chia_show_data.append(sub_slot_iters)

        chia_show = [chia_show_label, chia_show_data]
        legend = ["chia show -s", ""]
        tab_size = UIgraph.Point(80, len(chia_show_data) + 1)

        ELEMENTS.create_tab(node_data,
                            screenState,
                            main_scope,
                            "chia_show_s",
                            chia_show,
                            None,
                            None,
                            True,
                            pos,
                            tab_size,
                            keyboardState,
                            ScopeActions.exit_scope,
                            False,
                            False,)

        pos += UIgraph.Point(0, len(chia_show_data) + 2)

        # last 10 block; None for the ones not loaded yet
        last_10_blocks = [[],[],[]]
        for h in range(int(peak_height), int(peak_height) - 10, -1):
            curr_block: WDB.BlockState = blocks_loader.get_item_by_idx(h) if h >= 0 else None
            last_10_blocks[0].append(h if curr_block is not None else None)
            last_10_blocks[1].append(curr_block.header_hash if curr_block is not None else None)
            if curr_block is None:
                last_10_blocks[2].append(None)
            else:
                last_10_blocks[2].append("trx" if curr_block.is_transaction_block else "")

        block_legend = ['height', 'header hash', 'block type']
        max_y = main_win_size.y - pos.y - 3
        if max_y > 4:
            tab_size = UIgraph.Point(80, max_y)

            ELEMENTS.create_tab(node_data,
                                screenState,
                                main_scope,
                                "last_blocks",
                                last_10_blocks,
                                None,
                                None,
                                True,
                                pos,
                                tab_size,
                                keyboardState,
                                ScopeActions.exit_scope,
                                False,
                                False,
                                block_legend)

    else:

        block_legend = ['property', 'value']
        pos_tab_title = pos
        pos += UIgraph.Point(0, 2)  # the tab titles touch the table
        max_y = main_win_size.y - pos.y - 3
        tab_size = UIgraph.Point(80, max_y)
        if main_scope.cursor_x == -1:
            blocks_loader.update_offset(0)
            zero_block: WDB.BlockState = blocks_loader.get_current_item()
            current_block = zero_block.operational_error() if zero_block is not None else None
        else:
            current_block: WDB.BlockState = blocks_loader.get_current_item()

        if current_block is None:
            # the loader has not read the selected block yet (e.g. after a jump or a new peak)
            block_data = [['block'], ['loading...']]
        elif main_scope.cursor_x == -1:
            block_data = current_block.b_block_to_2d_list()
        else:
            block_data = current_block.block_state_to_2d_list()

        # the block before the first has no coins (cursor -1)
        coins_block = current_block if main_scope.cursor_x != -1 else None
        if main_scope.cursor_x == -1:
            tab_rows = {}
        elif current_block is None:
            tab_rows = None  # still loading
        else:
            tab_rows = selected_block_tab_rows(main_scope, screenState, coins_block)

        ### tabs: ←→ when they are selected, tab also from inside the table. The spend bundles
        ### tab is only for a block that has some: the choice stays for the next block with some
        visible_tabs = [(title, name) for title, name in BLOCK_TABS
                        if name != 'block_spend_bundles' or (tab_rows and tab_rows.get(name, ([],))[0])]
        tab_names = [name for _, name in visible_tabs]
        table_name = main_scope.data.get('block_tab', 'current_bloc')
        if table_name not in tab_names:
            table_name = 'current_bloc'
        previous_table = screenState.scopes.get(f"{main_scope.id}_{table_name}")
        in_previous_table = previous_table is not None and screenState.activeScope is previous_table
        if in_previous_table:
            screenState.footer_text += "| switch tab=tab "
        if tab_was_selected:
            screenState.footer_text += "| switch tab=←→ "
        if '\t' in keyboardState.keys and screenState.activeScope.mode != TYPES.ScopeMode.INSERT:
            tab_step = 1
        if tab_step:
            table_name = tab_names[(tab_names.index(table_name) + tab_step) % len(tab_names)]
            main_scope.data['block_tab'] = table_name

        tab_scope = None
        if max_y <= 4:
            pass  # no room for a table
        elif table_name == 'current_bloc':
            tab_scope = ELEMENTS.create_tab(node_data,
                                            screenState,
                                            main_scope,
                                            "current_bloc",
                                            block_data,
                                            None,
                                            None,
                                            True,
                                            pos,
                                            tab_size,
                                            keyboardState,
                                            ScopeActions.exit_scope,
                                            False,
                                            False,
                                            block_legend)
        else:
            legend = BLOCK_BUNDLES_LEGEND if table_name == 'block_spend_bundles' else BLOCK_COINS_LEGEND.get(table_name, BLOCK_PUZZLE_TYPES_LEGEND)
            keys = None
            if tab_rows is None:
                rows = [['loading...'] + [''] * (len(legend) - 1)]
                signature = 'loading'
            elif 'error' in tab_rows:
                rows = [[f"error: {tab_rows['error']}"] + [''] * (len(legend) - 1)]
                signature = 'error'
            else:
                rows, keys = tab_rows.get(table_name, ([], None))
                # the rows are read again from time to time, a coin can be spent later
                signature = (coins_block.header_hash, id(rows)) if coins_block else 'no coins'
            table = table_for_tab(main_scope, screenState, table_name, signature, rows)
            tab_scope = ELEMENTS.create_tab(node_data,
                                            screenState,
                                            main_scope,
                                            table_name,
                                            table,
                                            keys or None,
                                            None,
                                            False,
                                            pos,
                                            tab_size,
                                            keyboardState,
                                            {'block_puzzle_types': ScopeActions.exit_scope,
                                             'block_spend_bundles': open_spend_bundle}.get(table_name, open_block_coin),
                                            True,
                                            False,
                                            list(legend))

        if tab_scope is not None:
            # esc keeps the table selected, so ←→ go on switching the tabs
            tab_scope.exec_esc = ScopeActions.exit_scope
            tables_drawn.append(tab_scope)
            if in_previous_table:
                screenState.activeScope = tab_scope
            if tab_was_selected:
                main_scope.sub_scope_selected = tab_scope  # the table of the tab just opened

        ### tab titles, after the table: the line under the selected one replaces its top border
        C_background = screenState.colors["background"]
        P_tab_selected = screenState.colorPairs["xch"]
        P_tab_title = screenState.colorPairs["title"]
        P_tab_soft = screenState.colorPairs["tab_soft"]
        title_pos = pos_tab_title
        for title, name in visible_tabs:
            text = f" {title} "
            if name in BLOCK_TABS_WITH_COUNT:
                # a fixed width, also while loading: the titles do not move from block to block
                count = len(tab_rows[name][0]) if tab_rows and name in tab_rows else None
                text = f" {title} {tab_count_text(count)} "
            selected_tab = name == table_name
            P_used = P_tab_selected if selected_tab else P_tab_title
            if title_pos.x + len(text) + 2 >= main_win_size.x:
                break
            ELEMENTS.create_text_double_space(node_data, screenState, title_pos, text, P_used, C_background, 3, True)
            underline_pos = title_pos + UIgraph.Point(0, 2)
            if selected_tab:
                ELEMENTS.create_text(node_data, underline_pos, u'\u2580' * (len(text) + 2), P_tab_soft, True)
            else:
                ELEMENTS.create_text(node_data, underline_pos, ' ' * (len(text) + 2), P_used, True)
            title_pos += UIgraph.Point(len(text) + 2, 0)

    # a table that is not drawn anymore (a new block took the mempool block, another view of the
    # band) can not stay active: nothing would show it and the keys would go nowhere
    block_tables = [f"{main_scope.id}_{name}" for _, name in BLOCK_TABS] + [f"{main_scope.id}_{MEMPOOL_BLOCK_TXS_TAB}"]
    if screenState.activeScope.name in block_tables and screenState.activeScope not in tables_drawn:
        screenState.activeScope = main_scope


    # run copy/paste action or other pending stuffs
    if len(screenState.pending_action) > 0:
        for i, fn in screenState.pending_action:
            fn()
        screenState.pending_action = []


VDF_BLOCKS_AROUND = 160  # blocks loaded on each side of the selected one, about 5 sub-slots
VDF_FULL_FROM_ROWS = 52  # terminal rows for the full graph (it needs 44, the tabs some more); below, the compact one
VDF_TABS_FROM_ROWS = 33  # terminal rows for the tabs under the compact graph; below, enter on the graph shows them
VDF_DETAILS_AROUND = 3  # VDFs loaded also for the blocks next to the selected one, so ←→ find them ready
VDF_DETAILS_KEPT = 200  # VDFs of blocks kept in memory


def start_vdf_chains_load(main_scope: Scope, screenState: ScreenState, blocks_loader: WDB.DataChunkLoader,
                          center_height: int, selected_height, peak_height: int):
    """Load in a thread the blocks around center_height (block records only) and the VDFs of the
    selected block and of the VDF_DETAILS_AROUND blocks on each side (data['vdf_details']: height ->
    WDB.load_block_vdfs). Nothing to do if they are loaded already, or if a load is running."""
    data = main_scope.data
    if data.get('vdf_loading'):
        return

    points = data.get('vdf_points', {})
    details = data.get('vdf_details', {})
    if data.get('vdf_peak') != peak_height:
        # the last blocks can change with a reorg, load them again
        points = {h: p for h, p in points.items() if h < peak_height - 10}
        details = {h: d for h, d in details.items() if h < peak_height - 10}
        data['vdf_points'] = points
        data['vdf_details'] = details
        data['vdf_peak'] = peak_height

    start = max(0, center_height - VDF_BLOCKS_AROUND)
    end = min(peak_height, center_height + VDF_BLOCKS_AROUND)
    missing = [h for h in range(start, end + 1) if h not in points]

    missing_details = []
    if selected_height is not None:
        # the selected block first
        around = sorted(range(max(0, selected_height - VDF_DETAILS_AROUND),
                              min(peak_height, selected_height + VDF_DETAILS_AROUND) + 1),
                        key=lambda h: abs(h - selected_height))
        missing_details = [h for h in around if h not in details]

    if not missing and not missing_details:
        return
    data['vdf_loading'] = True

    def load():
        conn = blocks_loader.create_sql_conneciton()
        try:
            new_points = dict(points) if len(points) < 5000 else {}
            if missing:
                new_points.update(WDB.load_vdf_block_points(conn, min(missing), max(missing)))
                data['vdf_points'] = new_points

            if missing_details:
                new_details = dict(details)
                if len(new_details) > VDF_DETAILS_KEPT:
                    new_details = {h: d for h, d in new_details.items()
                                   if abs(h - selected_height) <= VDF_DETAILS_KEPT // 2}
                for h in missing_details:
                    new_details[h] = WDB.load_block_vdfs(conn, h)
                    data['vdf_details'] = dict(new_details)  # the selected one is shown before the others load
            data['vdf_error'] = None
        except Exception as e:
            logging(debug_logger, "DEBUG", f"vdf chains ERROR {e}")
            UTILS.logging_traceback("VDF CHAINS")
            data['vdf_error'] = f"vdf chains error: {e}"
        finally:
            conn.close()
            data['vdf_loading'] = False

    load_thread = threading.Thread(target=load, daemon=True)
    load_thread.start()
    load_thread.name = "loading vdf chains"
    with screenState.lock:
        screenState.running_threads.append(load_thread)


VDF_SEARCH_NAMES = {'overflow': "overflow block", 'long_slot': "slot of 2+ sub-slots"}


def open_vdf_tabs(scope: Scope, screen_state: ScreenState, *args):
    """Enter on the graph when the tabs are hidden: the VDF and legend tabs in its place, the vdf one selected"""
    main_scope = scope.main_scope
    main_scope.data['vdf_tabs_open'] = True
    main_scope.data['vdf_select'] = f"{main_scope.id}_vdf_{('table', 'legend')[main_scope.data.get('vdf_tab', 0)]}"
    screen_state.activeScope = main_scope


def close_vdf_tabs(scope: Scope, screen_state: ScreenState, *args):
    """Esc on the screen while the tabs are open: back to the graph, selected"""
    scope.data['vdf_tabs_open'] = False
    scope.data['vdf_select'] = f"{scope.id}_vdf_graph"
    screen_state.activeScope = scope


def start_vdf_search(data: dict, screenState: ScreenState, blocks_loader: WDB.DataChunkLoader, kind: str,
                     before_height: int):
    """Find in a thread the newest block of kind (WDB.find_previous_vdf_block) under before_height.
    data['vdf_search']: the kind while it runs; data['vdf_found']: the height found, the screen
    selects it; data['vdf_search_msg']: what to show when nothing is found or on error."""
    data['vdf_search'] = kind
    data['vdf_search_msg'] = None
    max_blocks = 50_000

    def search():
        conn = blocks_loader.create_sql_conneciton()
        try:
            height = WDB.find_previous_vdf_block(conn, before_height, kind, max_blocks)
            if height is None:
                data['vdf_search_msg'] = f"no {VDF_SEARCH_NAMES[kind]} in the {max_blocks:,} blocks before {before_height:,}"
            else:
                data['vdf_found'] = height
        except Exception as e:
            logging(debug_logger, "DEBUG", f"vdf search ERROR {e}")
            UTILS.logging_traceback("VDF SEARCH")
            data['vdf_search_msg'] = f"search error: {e}"
        finally:
            conn.close()
            data['vdf_search'] = None

    search_thread = threading.Thread(target=search, daemon=True)
    search_thread.start()
    search_thread.name = "vdf search"
    with screenState.lock:
        screenState.running_threads.append(search_thread)


def vdf_sub_slots_around(points: dict, center_height: int, peak_height: int):
    """Sub-slots of the consecutive loaded blocks around center_height. The first and last
    sub-slots can miss some blocks, so they are removed (the last one is kept at the peak)."""
    if center_height not in points:
        return []
    first = center_height
    while first - 1 in points:
        first -= 1
    last = center_height
    while last + 1 in points:
        last += 1
    sub_slots = WDB.build_vdf_sub_slots([points[h] for h in range(first, last + 1)])
    if first > 0 and len(sub_slots) > 1:
        sub_slots = sub_slots[1:]
    if last < peak_height and len(sub_slots) > 1:
        sub_slots = sub_slots[:-1]
    return sub_slots


def screen_blocks_vdf(stdscr, keyboardState: KeyboardState, screenState: ScreenState, fullNodeState: FullNodeState, figlet=False):
    """The blocks on a real time axis, the slots, the sub-slots and the three VDF chains (challenge,
    infused challenge and reward), and the VDFs of the selected block.
    main_scope.cursor_x is the height of the selected block; on the peak it follows the new peaks.
    Below VDF_FULL_FROM_ROWS terminal rows the graph is compact, below VDF_TABS_FROM_ROWS also the
    VDF and legend tabs are hidden: enter on the graph shows
    them in its place, esc goes back to the graph"""

    active_scope: Scope = screenState.activeScope
    main_scope: Scope = active_scope.main_scope
    screenState.scope_exec_args = [screenState]
    main_scope.update()
    data = main_scope.data

    full_node_meta: FullNodeMeta = fullNodeState.deepcopy_meta()
    height_last_block = full_node_meta.peak_height
    with fullNodeState.lock:
        blocks_loader: WDB.DataChunkLoader = fullNodeState.blocks_loader  # only for its DB connection

    C_background = screenState.colors["background"]
    P_text = screenState.colorPairs["body"]
    P_error = screenState.colorPairs["error"]
    P_title_selected = screenState.colorPairs["xch"]
    P_overflow = screenState.colorPairs["vdf_overflow"]

    height = screenState.screen_size.y
    width = screenState.screen_size.x
    win = createFullSubWin(stdscr, screenState, height, width)
    win.bkgd(' ', curses.color_pair(P_text))

    main_win_size = win.getmaxyx()
    main_win_size = UIgraph.Point(main_win_size[1], main_win_size[0])
    pos = UIgraph.Point(1, 1)

    ELEMENTS.create_text_double_space(win, screenState, pos, 'blocks and vdf chains', P_title_selected, C_background,
                                      3, True, inv_color=False)
    pos += UIgraph.Point(0, 3)

    if blocks_loader is None or height_last_block is None:
        ELEMENTS.create_text(win, pos, "no blocks: the node is not reachable", P_error, bold=True)
        return

    pre_text = "Go to block: "
    prompt_lenght = min(80, width - 4)
    scope_go_to = ELEMENTS.create_prompt(win, screenState, keyboardState, main_scope, 'go to block vdf', pos,
                                         pre_text, prompt_lenght, P_text, True, False,
                                         custom_scope_function=ScopeActions.press_enter)
    pos += UIgraph.Point(0, 2)  # a row for the frame of the selected prompt

    # the graph is an element of its own: enter goes into it, then ←→ select a block (newest on
    # the left) and home goes back to the peak; graph_scope.cursor_x is the selected height.
    # A block is always selected: on the peak it follows the new peaks, elsewhere it stays
    graph_name = f"{main_scope.id}_vdf_graph"
    if graph_name not in screenState.scopes:
        graph_scope = Scope(graph_name, main_scope.screen, screenState)
        graph_scope.parent_scope = main_scope
        graph_scope.main_scope = main_scope
        graph_scope.exec = ScopeActions.activate_scope
        graph_scope.exec_own = ScopeActions.activate_scope
        graph_scope.keyboard_exec = KEYBOARD.block_band_execution
        graph_scope.cursor_x = height_last_block
        main_scope.cursor = 1  # the graph is selected when the screen opens
    graph_scope: Scope = screenState.scopes[graph_name]
    compact = stdscr.getmaxyx()[0] < VDF_FULL_FROM_ROWS
    tabs_hidden = stdscr.getmaxyx()[0] < VDF_TABS_FROM_ROWS
    if not tabs_hidden or screenState.activeScope is graph_scope:
        data['vdf_tabs_open'] = False
    tabs_open = data.get('vdf_tabs_open', False)
    # tabs hidden: enter on the graph (selected or entered) opens the tabs, esc on the screen closes
    # them; ←→ select the block also with the graph only selected
    graph_scope.exec = graph_scope.exec_own = open_vdf_tabs if tabs_hidden else ScopeActions.activate_scope
    if 'vdf_main_esc' not in data:
        data['vdf_main_esc'] = main_scope.exec_esc
    main_scope.exec_esc = close_vdf_tabs if tabs_open else data['vdf_main_esc']
    # the scope to select after opening or closing the tabs, once main_scope.update() has dropped
    # the ones hidden by the switch (a frame later), so its index does not change
    if data.get('vdf_select') in main_scope.sub_scopes:
        main_scope.cursor = list(main_scope.sub_scopes).index(data.pop('vdf_select'))
    if not tabs_open:
        graph_scope.set_visible()
    graph_scope.base_point = pos

    # ←→ move the selection also from outside the graph: main_scope.cursor_x follows it
    # (main_scope has the same flipped ←→ of the graph). When the vdf and legend tables are tabs
    # and one is selected, ←→ switch them instead
    tab_names = (f"{main_scope.id}_vdf_table", f"{main_scope.id}_vdf_legend")
    tab_is_selected = (data.get('vdf_tabs_toggle', False) and screenState.activeScope is main_scope
                       and main_scope.sub_scope_selected is not None
                       and main_scope.sub_scope_selected.name in tab_names)
    if screenState.activeScope is main_scope and 'vdf_main_x' in data:
        delta = main_scope.cursor_x - data['vdf_main_x']
        if tab_is_selected:
            data['vdf_tab'] = (data.get('vdf_tab', 0) + delta) % 2
        else:
            graph_scope.cursor_x += delta
    if tab_is_selected:
        screenState.footer_text += "| vdf / legend=←→ "
    elif screenState.activeScope in (main_scope, graph_scope):
        screenState.footer_text += "| select block=←→ | go to peak=home "
        if keyboardState.home:
            graph_scope.cursor_x = height_last_block
    if compact:
        screenState.footer_text += f"| full view from {VDF_FULL_FROM_ROWS} rows "
    if tabs_open and screenState.activeScope is main_scope:
        screenState.footer_text += "| back to the graph=esc "
    elif tabs_hidden and (screenState.activeScope is graph_scope
                      or (screenState.activeScope is main_scope and graph_scope.selected())):
        screenState.footer_text += "| vdf tables=enter "

    # o / s: go to the previous overflow block, or to the previous slot of 2 or more sub-slots,
    # older than the selected block; found in a thread, it can take some seconds
    if screenState.activeScope in (main_scope, graph_scope):
        screenState.footer_text += "| last overflow=o | last slot of 2+ sub-slots=s "
        for key, kind in (('o', 'overflow'), ('s', 'long_slot')):
            if key in keyboardState.keys and not data.get('vdf_search'):
                data['vdf_search_at'] = graph_scope.cursor_x
                start_vdf_search(data, screenState, blocks_loader, kind, graph_scope.cursor_x)
    if data.get('vdf_found') is not None:
        graph_scope.cursor_x = data.pop('vdf_found')
    elif data.get('vdf_search_msg') and graph_scope.cursor_x != data.get('vdf_search_at'):
        data['vdf_search_msg'] = None  # another block selected
    if data.get('vdf_last_peak') is not None and graph_scope.cursor_x == data['vdf_last_peak']:
        graph_scope.cursor_x = height_last_block  # it was on the peak: follow the new peak
    data['vdf_last_peak'] = height_last_block
    graph_scope.cursor_x = max(0, min(graph_scope.cursor_x, height_last_block))
    height_before = graph_scope.cursor_x
    go_to_block(scope_go_to, graph_scope, None, blocks_loader, height_last_block, screenState)
    if graph_scope.cursor_x != height_before:
        # a block was found: go into the graph, to move from there
        main_scope.cursor = list(main_scope.sub_scopes).index(graph_name)
        screenState.activeScope = graph_scope

    main_scope.cursor_x = data['vdf_main_x'] = graph_scope.cursor_x
    selected_height = center_height = graph_scope.cursor_x

    start_vdf_chains_load(main_scope, screenState, blocks_loader, center_height, selected_height, height_last_block)

    points = data.get('vdf_points', {})
    sub_slots = vdf_sub_slots_around(points, center_height, height_last_block)
    selected = points.get(selected_height)

    # speed of the VDFs, around the selected block or at the tip
    vdf_speed = ""
    if sub_slots:
        all_points = [b for sub_slot in sub_slots for b in sub_slot.blocks]
        around = selected if selected is not None else all_points[-1]
        clock = WDB.VdfClock.fit(all_points, around.sp_total_iters - around.sub_slot_iters,
                                 around.sp_total_iters + around.sub_slot_iters)
        if clock is not None:
            vdf_speed = f"~{clock.speed / 1000:,.0f}k it/s"

    # header of the graph: the selected block
    graph_top = pos.y
    if data.get('vdf_error'):
        header = [(data['vdf_error'], screenState.colors["red"])]
    elif not sub_slots:
        header = [("loading vdf chains...", None)]
    elif selected is None:
        header = [(f"block {selected_height:,}  |  loading...", None)]
    else:
        sp_interval = selected.sub_slot_iters / 64
        header = [(f"block {selected.height:,}  |  signage point {selected.signage_point_index}  |  "
                   f"infusion point sp {selected.ip_iters / sp_interval:.1f}  |  deficit {selected.deficit}", None)]
        if selected.is_challenge_block:
            header.append(("  |  challenge block", None))
        if selected.overflow:
            header.append(("  |  ", None))
            header.append(("overflow block", screenState.colors["yellow_bee"]))
    if vdf_speed and sub_slots:
        header.append((f"  |  vdf speed {vdf_speed}", None))
    if data.get('vdf_search'):
        header.append((f"  |  searching the last {VDF_SEARCH_NAMES[data['vdf_search']]}...", None))
    elif data.get('vdf_search_msg'):
        header.append((f"  |  {data['vdf_search_msg']}", screenState.colors["red"]))
    header_height = ELEMENTS.create_vdf_header(win, screenState, pos, main_win_size.x - 3, header, compact)
    pos += UIgraph.Point(0, header_height + 1)

    graph_width = main_win_size.x - 3
    graph_start = pos
    table, legend_active = [], set()
    graph_lines = 0
    block_vdfs = None
    if sub_slots:
        peak_point = points.get(height_last_block)
        peak_total_iters = peak_point.ip_total_iters if peak_point is not None else None
        if selected is not None:
            block_vdfs = data.get('vdf_details', {}).get(selected.height)
        max_lines = main_win_size.y - pos.y - 1
        # graph_width - 1: an empty column between the chains and the frame on the right
        graph_lines, table, legend_active = ELEMENTS.create_vdf_chains(
            win, screenState, pos, graph_width - 1, max_lines, sub_slots, peak_total_iters, selected, block_vdfs,
            compact=compact)
    pos += UIgraph.Point(0, graph_lines)

    # a frame on the right and the bottom of the graph, like the block band: grey, highlighted
    # when the graph is selected, in the active color when it is entered
    P_frame = screenState.colorPairs["tab_soft_bg"]
    if screenState.activeScope is graph_scope:
        P_frame = screenState.colorPairs["scope_selected"]
    elif graph_scope.selected():
        P_frame = screenState.colorPairs["win_selected"]
    if tabs_open:
        # the tabs in place of the graph (drawn for its VDF table), under the header of the block
        for y in range(graph_start.y, main_win_size.y - 1):
            ELEMENTS.create_text(win, UIgraph.Point(0, y), ' ' * (main_win_size.x - 1), P_text)
        pos = graph_start
    else:
        for y in range(graph_top, min(pos.y, main_win_size.y - 2)):
            ELEMENTS.create_text(win, UIgraph.Point(pos.x + graph_width, y), '▌', P_frame)
        if pos.y < main_win_size.y - 1:
            ELEMENTS.create_text(win, UIgraph.Point(pos.x, pos.y), '▀' * graph_width + '▘', P_frame)
        pos += UIgraph.Point(0, 2)

    # vdf data and legend: one on top of the other, or tabs switched with ←→; in a very small
    # window hidden until enter is pressed on the graph
    if (tabs_open or not tabs_hidden) and pos.y + 2 < main_win_size.y - 2:
        data['vdf_tabs_toggle'] = ELEMENTS.create_vdf_tabs(win, screenState, keyboardState, main_scope, pos,
                                                           main_win_size.y - 2, table, legend_active,
                                                           data.get('vdf_tab', 0))

    # run copy/paste action or other pending stuffs
    if len(screenState.pending_action) > 0:
        for i, fn in screenState.pending_action:
            fn()
        screenState.pending_action = []


TX_DEBUG_MAX_SOLUTION = 20_000  # bytes: disassembling and running a bigger spend every frame is too slow


def screen_transaction(stdscr, keyboardState, screenState, fullNodeState: FullNodeState, figlet=False):

    # Steve transaction f3cf5c97a1e84186
    # https://xchplorer.com/blocks/2bb5c71a62a7ddce42565f922126fe2866b9ae79249654bec983229d882ba18b#f3cf5c97a1e84186


    # delete screenState size dimension? and get them from stdscr? why two places?
    width = screenState.screen_size.x
    height = screenState.screen_size.y

    tx_win = createFullSubWin(stdscr, screenState, height, width)
    tx_win.bkgd(' ', curses.color_pair(screenState.colorPairs["body"]))

    active_scope: Scope = screenState.activeScope
    main_scope: Scope = active_scope.main_scope
    screenState.scope_exec_args = [screenState]

    spend_bundle_hash = main_scope.data['spend_bundle_hash']

    if "watch_later" not in main_scope.data:
        conn = sqlite3.connect(DB_SB, timeout=SQL_TIMEOUT)
        if WDB.load_spend_bundle(conn, spend_bundle_hash, "watch later") is None:
            main_scope.data["watch_later"] = False
        else:
            main_scope.data["watch_later"] = True
        conn.close()


    if "tx_cache" not in main_scope.data:
        main_scope.data["tx_cache"] = None

    tx_cache = main_scope.data["tx_cache"]

    if tx_cache is None:
        tx_cache = {}
        mempool_tx = SCAN.MEMPOOL_SCANNER.get(spend_bundle_hash)
        if mempool_tx is not None:
            tx_cache["tx"] = WDB.MempoolItem(raw_json_spendbundle=mempool_tx.spend_bundle,
                                             timestamp=mempool_tx.added_at)
            tx_cache["mempool_tx"] = mempool_tx
        else:
            # not in the mempool anymore: the saved copy (e.g. a watched bundle)
            conn = sqlite3.connect(DB_SB, timeout=SQL_TIMEOUT)
            saved = WDB.load_spend_bundle(conn, spend_bundle_hash)
            conn.close()
            if saved:
                sp: SpendBundle = SpendBundle.from_bytes(saved[0].raw_spend_bundle)
                tx_cache["tx"] = WDB.MempoolItem(raw_json_spendbundle=sp.to_json_dict(),
                                                 timestamp=saved[0].timestamp)
            else:
                tx_cache["tx"] = None

    main_scope.data["tx_cache"] = tx_cache

    tx = tx_cache["tx"]
    if tx is None:
        ELEMENTS.create_text(tx_win, UIgraph.Point(2, 2), f"bundle {spend_bundle_hash} not found: "
                             "it left the mempool and it was not saved", screenState.colorPairs['tab_soft'])
        return

    # save the bundle, then add it to the group: the group only references saved bundles
    if keyboardState.key == 'w' and not main_scope.data['watch_later']:
        conn = sqlite3.connect(DB_SB, timeout=SQL_TIMEOUT)
        WDB.insert_spend_bundle(conn, SpendBundle.from_json_dict(tx.spend_bundle))
        main_scope.data['watch_later'] = WDB.add_spend_bundles_to_watch_later(conn, spend_bundle_hash)
        conn.close()
    P_text = screenState.colorPairs['tab_soft']
    P_body = screenState.colorPairs['body']

    pos = UIgraph.Point(1,1)
    ELEMENTS.create_text_double_space(tx_win, screenState, pos, 'spend bundle', screenState.colorPairs['xch'],
                                      screenState.colors['background'], 3, True, inv_color=False)
    pos += UIgraph.Point(0,3)
    mempool_tx = tx_cache.get("mempool_tx")
    if mempool_tx is None:
        where = 'saved copy, not in the mempool'
    elif mempool_tx.validated_at is not None:
        where = 'in a block'
    elif mempool_tx.gone_at is not None:
        where = 'left the mempool'
    else:
        where = f'in the mempool for {human_age(time.time() - mempool_tx.added_at)}'
    put_text(tx_win, pos, f"id: {spend_bundle_hash.removeprefix('0x')} | {where} | fee: {tx.fee / XCH_MOJO:.6f} XCH | "
             f"cost: {tx.cost:,} | coins in/out: {tx.removed_coins_count} / {tx.added_coins_count}", P_body)
    pos += UIgraph.Point(0,1)
    put_text(tx_win, pos, 'in watch later' if main_scope.data['watch_later'] else 'not saved', P_text)
    if not main_scope.data['watch_later']:
        screenState.footer_text += "| watch later=w "
    pos += UIgraph.Point(0,1)


    legend = ['action', 'coin id', 'amount', 'parent coin info', 'puzzle hash']
    coins = []
    # removals
    for rem in tx.removals:
        #pos += UIgraph.Point(0,2)
        #ELEMENTS.create_text(tx_win, pos, str(rem), P_text, bold=False)

        coin_id = UTILS.calc_coin_id(rem['parent_coin_info'], rem['puzzle_hash'], uint64(rem['amount']))
        rem = ['removal', coin_id, rem['amount'], rem['parent_coin_info'], rem['puzzle_hash']]
        coins.append(rem)

    coins.append([''] * len(legend))

    # additions
    for add in tx.additions:
        coin_id = UTILS.calc_coin_id(add['parent_coin_info'], add['puzzle_hash'], uint64(add['amount']))
        add = ['addition', coin_id, add['amount'], add['parent_coin_info'], add['puzzle_hash']]
        coins.append(add)


    pos += UIgraph.Point(0,2)
    tab_size = UIgraph.Point(width - 2, (height - pos.y - 6) // 2)
    main_scope.update()
    coin_tab_scope = ELEMENTS.create_tab(tx_win,
                                         screenState,
                                         main_scope,
                                         "coins_selection",
                                         coins,
                                         None,
                                         None,
                                         False,
                                         pos,
                                         tab_size,
                                         keyboardState,
                                         ScopeActions.exit_scope,
                                         True,
                                         False,
                                         legend,
                                         # fixed widths: create_tab would drop the columns
                                         # that do not fit, but not from its cached colors
                                         column_widths=[9, 64, 16, 40, 40])

    sp = tx.spend_bundle

    sp_coins = sp['coin_spends']

    selected_id = coins[coin_tab_scope.cursor][1]

    c_puzzle = "not found"
    c_solution = "not found"
    for c in sp_coins:
        c_coin = c['coin']
        c_id = UTILS.calc_coin_id(c_coin['parent_coin_info'], c_coin['puzzle_hash'], uint64(c_coin['amount']))
        if c_id == selected_id:
            c_puzzle = PyProgram.fromhex(c['puzzle_reveal'])
            c_solution = PyProgram.fromhex(c['solution'])

            pos += UIgraph.Point(0, tab_size.y + 1)
            solution_size = len(c['solution']) // 2
            if solution_size > TX_DEBUG_MAX_SOLUTION:
                put_text(tx_win, pos, f"this spend is too big to show here: {solution_size:,} bytes of solution", P_text)
                break

            # the text below is the old debug layout (see PLAN.md): it can be longer than the screen
            try:
                # unroll puzzle
                c_puzzle_names, _ = PUZ.unroll_puzzle_to_names(c_puzzle)


                ELEMENTS.create_text(tx_win, pos, str(c_puzzle)[:150], P_text, bold=False)
                pos += UIgraph.Point(0,2)
                ELEMENTS.create_text(tx_win, pos, str(c_puzzle_names), P_text, bold=False)
                pos += UIgraph.Point(0,2)
                ELEMENTS.create_text(tx_win, pos, str(c_solution)[:150], P_text, bold=False)
                pos += UIgraph.Point(0,2)
                ELEMENTS.create_text(tx_win, pos, disassemble(c_solution), P_text, bold=False)
                # run program
                result = c_puzzle.run(c_solution)
                pos += UIgraph.Point(0,3)
                result_list = list(result.as_iter())
                ELEMENTS.create_text(tx_win, pos, "result = " + disassemble(result), P_text, bold=False)
                pos += UIgraph.Point(0,2)
                result_list = list(result.as_iter())
                res = []
                for rr in result.as_iter():
                    res.append(disassemble(rr))

                ELEMENTS.create_text(tx_win, pos, f"result -----", P_text, bold=False)
                for i in res:
                    pos += UIgraph.Point(0,1)
                    i = i.replace(' ', ',')
                    i = ast.literal_eval(i)
                    code = PUZ.get_opcode_name(i[0])
                    ELEMENTS.create_text(tx_win, pos, f"{code}: {i} and type f{type(i)}", P_text, bold=False)
            except (curses.error, RecursionError) as e:
                logging(debug_logger, "DEBUG", f"TRANSACTION spend does not fit on the screen: {e}")

    pos += UIgraph.Point(0,2)
    #ELEMENTS.create_text(tx_win, pos, "spend_bundle_hash: " + str(tx.spend_bundle_hash)[:20], P_text, bold=False)


    ### saved spendbundle -> folder with the spend save clearly
    ### save all the mempool...
    ### make sqlite for mempool and puzzle_reveal


def fit_text(text, max_len: int) -> str:
    text = str(text)
    if len(text) <= max_len:
        return text
    return text[:max(max_len - 3, 0)] + '...'


def put_text(win, pos: UIgraph.Point, text, P_color, bold=False):
    """create_text that cuts the text at the window border"""
    max_y, max_x = win.getmaxyx()
    if pos.y >= max_y - 1 or pos.x >= max_x - 1:
        return
    ELEMENTS.create_text(win, pos, fit_text(text, max_x - pos.x - 1), P_color, bold)


def human_age(seconds: float) -> str:
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m {seconds % 60:02d}s"
    return f"{seconds // 3600}h {seconds % 3600 // 60:02d}m"


def fresh_table_colors(rows: list):
    """create_tab trims the columns that do not fit also in its cached color table, a table
    that changes every frame needs a new color table every frame"""
    return [[None] * len(row) for row in rows]


def scopeAction_nothing(scope: Scope, screenState: ScreenState, *args):
    return scope


def list_tab_scope(screenState: ScreenState, main_scope: Scope, tab_name: str, scope_activation_func):
    """Scope of a tab that is the only element of the screen. It is active as soon as the
    screen opens and esc goes back to the menu"""
    scope_name = f"{main_scope.id}_{tab_name}"
    if scope_name not in screenState.scopes:
        tab_scope = Scope(scope_name, main_scope.screen, screenState)
        tab_scope.parent_scope = main_scope
        tab_scope.main_scope = main_scope
        tab_scope.exec = ScopeActions.activate_scope
        tab_scope.exec_esc = ScopeActions.exit_scope_N(2)
        tab_scope.exec_own = scope_activation_func
        main_scope.sub_scopes[scope_name] = tab_scope
        tab_scope.visible = True

    tab_scope = screenState.scopes[scope_name]
    if screenState.activeScope is main_scope:
        screenState.activeScope = tab_scope
    return tab_scope


def screen_mempool(stdscr, keyboardState, screenState, fullNodeState: FullNodeState, figlet=False):

    height = screenState.screen_size.y
    width = screenState.screen_size.x

    active_scope: Scope = screenState.activeScope
    main_scope: Scope = active_scope.main_scope
    screenState.scope_exec_args = [screenState]
    main_scope.update()

    win = createFullSubWin(stdscr, screenState, height, width)
    win.bkgd(' ', curses.color_pair(screenState.colorPairs["body"]))
    main_win_size = UIgraph.Point(win.getmaxyx()[1], win.getmaxyx()[0])

    C_background = screenState.colors["background"]
    P_text = screenState.colorPairs["body"]
    P_title = screenState.colorPairs["xch"]
    P_error = screenState.colorPairs["error"]

    pos = UIgraph.Point(1,1)
    ELEMENTS.create_text_double_space(win, screenState, pos, 'mempool', P_title, C_background,
                                      3, True, inv_color=False)
    timer_text, block_late = next_transaction_block_text(main_scope, screenState, fullNodeState)
    put_text(win, UIgraph.Point(pos.x + len('mempool') + 6, pos.y + 1), timer_text,
             P_error if block_late else P_text, bold=block_late)
    pos += UIgraph.Point(0,3)

    scanner = SCAN.MEMPOOL_SCANNER
    scanner.want_fast()
    now = time.time()
    # the scanner drops validated txs only at its next scan, hide them here on time; it keeps
    # for a while the txs that left the mempool without a block yet, hide them
    txs = [tx for tx in scanner.snapshot()
           if (tx.validated_at is None and tx.gone_at is None)
           or (tx.validated_at is not None and now - tx.validated_at <= CONF.MEMPOOL_VALIDATED_TX_DELAY)]
    pending_txs = [tx for tx in txs if tx.validated_at is None]
    total_cost = sum(tx.cost for tx in pending_txs)
    total_fee = sum(tx.fee for tx in pending_txs)
    info = (f"transactions: {len(pending_txs):,} | total cost: {total_cost:,} ({total_cost / BLOCK_MAX_COST:.2f} blocks) | "
            f"total fees: {total_fee / XCH_MOJO:.6f} XCH | just validated: {len(txs) - len(pending_txs)} | "
            f"scanner: {scanner.status}")
    put_text(win, pos, info, P_text)
    pos += UIgraph.Point(0,1)
    if fullNodeState.full_node_meta.synced is False:
        put_text(win, pos, "the node is syncing, the mempool stays empty until it is synced", P_error, bold=True)
    pos += UIgraph.Point(0,2)

    legend = list(MEMPOOL_TX_LEGEND)
    C_validated = screenState.colors["light_azure"]

    def validated_color(tx):
        if tx.validated_at is None:
            return None
        remaining = CONF.MEMPOOL_VALIDATED_TX_DELAY - (now - tx.validated_at)
        if remaining <= CONF.MEMPOOL_VALIDATED_TX_FLASH and int(now * 2) % 2:
            return None  # blink off: back to the normal color
        return C_validated

    rows = []
    keys = []
    colors = []
    for tx in txs:
        colors.append([validated_color(tx)] * len(legend))
        rows.append(mempool_tx_row(tx, now))
        keys.append(tx.tx_id)

    tab_name = "mempool_txs"
    tab_scope = list_tab_scope(screenState, main_scope, tab_name, ScopeActions.open_transaction)
    tab_size = UIgraph.Point(main_win_size.x - 2, main_win_size.y - pos.y - 1)
    ELEMENTS.create_tab(win,
                        screenState,
                        main_scope,
                        tab_name,
                        rows,
                        keys,
                        colors,
                        False,
                        pos,
                        tab_size,
                        keyboardState,
                        ScopeActions.open_transaction,
                        True,
                        False,
                        legend,
                        prepped_scope=tab_scope)


MEMPOOL_TX_LEGEND = ['tx id', 'type', 'cost', 'fee [XCH]', 'fee/cost', 'coins in', 'coins out', 'age']


def mempool_tx_row(tx, now: float) -> list:
    """Row of a mempool transaction (SCAN.MempoolTx), with the columns of MEMPOOL_TX_LEGEND"""
    return [
        f"0x{tx.tx_id[:16]}...",
        SCAN.tx_type(SCAN.CATALOG, tx.layered_puzzle_fingerprints),
        f"{tx.cost:,}",
        f"{tx.fee / XCH_MOJO:.6f}",
        f"{tx.fee_per_cost:.2f}",
        tx.coins_in,
        tx.coins_out,
        human_age(now - tx.added_at),
    ]


def next_transaction_block_text(main_scope: Scope, screenState: ScreenState, fullNodeState: FullNodeState):
    """When the next transaction block should come (only those take mempool transactions):
    the last one + the average gap of the recent ones. Times are arrivals: a timestamp +
    WDB.BLOCK_INFUSION_DELAY. The timestamps are read in a thread, again at every new peak.
    Returns (text, late)."""
    data = main_scope.data
    peak = fullNodeState.full_node_meta.peak_height
    thread = data.get('tx_block_times_thread')
    if data.get('tx_block_times_peak') != peak and (thread is None or not thread.is_alive()):
        data['tx_block_times_peak'] = peak

        def load_times():
            try:
                data['tx_block_times'] = WDB.recent_transaction_block_timestamps(DB_BLOCKCHAIN_RO)
            except Exception as e:
                data['tx_block_times'] = None
                logging(debug_logger, "DEBUG", f"MEMPOOL tx block times error: {e}")

        thread = threading.Thread(target=load_times, daemon=True, name='tx block times')
        thread.start()
        data['tx_block_times_thread'] = thread
        screenState.running_threads.append(thread)

    times = data.get('tx_block_times')
    if times is None:
        return 'next transaction block: reading the chain...', False
    if len(times) < 2:
        return 'next transaction block: not enough blocks to estimate', False
    average_gap = (times[-1] - times[0]) / (len(times) - 1)
    since_last = time.time() - (times[-1] + WDB.BLOCK_INFUSION_DELAY)
    remaining = average_gap - since_last
    last = f"last {human_age(max(since_last, 0))} ago, every ~{average_gap:.0f}s"
    if remaining >= 0:
        return f"next transaction block in ~{human_age(remaining)} ({last})", False
    return f"next transaction block late by {human_age(-remaining)} ({last})", True


# the two lists of the puzzles screen: status -> label, tab switches between them
def scopeAction_open_puzzle(scope: Scope, screenState: ScreenState, layered_puzzle_fingerprint: str = None):
    if layered_puzzle_fingerprint is None:
        return scope

    new_scope = Scope(f"puzzle_{layered_puzzle_fingerprint}", screen_puzzle_detail, screenState)
    new_scope.parent_scope = scope
    new_scope.data['layered_puzzle_fingerprint'] = layered_puzzle_fingerprint
    new_scope.exec = None
    screenState.activeScope = new_scope
    return new_scope


def puzzle_submenu(stdscr, keyboardState, screenState, fullNodeState: FullNodeState, items: list):
    """A menu of puzzle views, like the main menu: items is a list of (name, screen)"""
    activeScope: Scope = screenState.activeScope
    screenState.scope_exec_args = [screenState]
    menu_items = []
    if len(activeScope.sub_scopes) == 0:
        menu_items = [(name, handler, ScopeActions.activate_scope, None) for name, handler in items]
        for name, handler, exec_fun, exec_key in menu_items:
            new_scope: Scope = Scope(name, handler, screenState)
            new_scope.exec = exec_fun
            new_scope.parent_scope = activeScope
            activeScope.sub_scopes[name] = new_scope
    factory_menu(menu_items, stdscr, keyboardState, screenState, fullNodeState, figlet=False)


def screen_menu_test(stdscr, keyboardState, screenState, fullNodeState: FullNodeState, figlet=False):
    """TEST ONLY (remove, see PLAN): a menu with 20 items, to see a long menu scroll"""
    puzzle_submenu(stdscr, keyboardState, screenState, fullNodeState,
                   [(f"sub menu {i}", screen_puzzles) for i in range(20)])


def screen_puzzles(stdscr, keyboardState, screenState, fullNodeState: FullNodeState, figlet=False):
    """The puzzles menu: the scanner, all the puzzles seen, the lists that classify them"""
    puzzle_submenu(stdscr, keyboardState, screenState, fullNodeState,
                   [('puzzle scanner', screen_puzzle_scanner), ('all puzzles', screen_puzzles_all),
                    ('lists', screen_puzzle_lists)])


def puzzle_screen_win(stdscr, screenState: ScreenState, title: str):
    """The window of a puzzle view with its title; returns (win, main_win_size, pos under the title)"""
    win = createFullSubWin(stdscr, screenState, screenState.screen_size.y, screenState.screen_size.x)
    win.bkgd(' ', curses.color_pair(screenState.colorPairs["body"]))
    main_win_size = UIgraph.Point(win.getmaxyx()[1], win.getmaxyx()[0])
    pos = UIgraph.Point(1, 1)
    ELEMENTS.create_text_double_space(win, screenState, pos, title, screenState.colorPairs["xch"],
                                      screenState.colors["background"], 3, True, inv_color=False)
    return win, main_win_size, pos + UIgraph.Point(0, 3)


def format_duration(seconds: float) -> str:
    minutes = int(seconds // 60)
    return f"{minutes // 60}h {minutes % 60:02d}m" if minutes >= 60 else f"{minutes} min"


def screen_puzzle_scanner(stdscr, keyboardState, screenState, fullNodeState: FullNodeState, figlet=False):
    """The scans of the puzzles: how much of the chain is counted, the full scan (start, stop,
    resume), the live and mempool scanners"""
    active_scope: Scope = screenState.activeScope
    main_scope: Scope = active_scope.main_scope
    screenState.scope_exec_args = [screenState]
    main_scope.update_2d()
    data = main_scope.data

    win, main_win_size, pos = puzzle_screen_win(stdscr, screenState, 'puzzle scanner')
    P_text = screenState.colorPairs["body"]
    P_error = screenState.colorPairs["error"]

    # coverage and full scan state: DB queries, in a thread every few seconds
    if not data.get('coverage_loading') and time.time() - data.get('coverage_time', 0) > 5:
        data['coverage_loading'] = True

        def load_coverage():
            try:
                tip = SCAN.CHAIN_SCANNER.tip
                if tip is None:
                    node_conn = SCAN.node_connection()
                    try:
                        tip = SCAN.chain_tip(node_conn)
                    finally:
                        node_conn.close()
                data['coverage'] = SCAN.coverage(SCAN.CATALOG, tip)
                data['coverage_error'] = None
            except Exception as e:
                logging(debug_logger, "DEBUG", f"PUZZLE SCANNER coverage error: {e}")
                UTILS.logging_traceback('PUZZLE SCANNER')
                data['coverage_error'] = f"coverage not read: {e}"
            finally:
                data['coverage_time'] = time.time()
                data['coverage_loading'] = False

        coverage_thread = threading.Thread(target=load_coverage, daemon=True, name='puzzle coverage')
        coverage_thread.start()
        with screenState.lock:
            screenState.running_threads.append(coverage_thread)

    cov = data.get('coverage')
    if data.get('coverage_error'):
        put_text(win, pos, data['coverage_error'], P_error, bold=True)
        pos += UIgraph.Point(0, 2)
    if cov is None:
        put_text(win, pos, "loading the coverage...", P_text, bold=True)
        return

    tip, full = cov['tip'], cov['full']
    heights = tip + 1
    put_text(win, pos, f"coverage: {cov['covered']:,} of {heights:,} heights ({cov['covered'] / heights:.2%}) | "
                       f"spends counted: {cov['spends']:,} | puzzles: {cov['puzzles']:,}", P_text, bold=True)
    pos += UIgraph.Point(0, 1)
    gaps = cov['gaps']
    gap_text = ', '.join(f"{s:,}-{e - 1:,}" for s, e in gaps[:3]) + (f" and {len(gaps) - 3} more" if len(gaps) > 3 else '')
    put_text(win, pos, f"not scanned: {gap_text or 'none'}", P_text)
    pos += UIgraph.Point(0, 2)

    if full['end'] is None:
        full_text = "full scan: never run"
    else:
        info = full['info']
        state = 'running' if full['running'] else ('done' if full['chunks_done'] >= full['chunks_total'] else 'stopped')
        full_text = (f"full scan: {state} | chunks {full['chunks_done']}/{full['chunks_total']} | heights 0-{full['end'] - 1:,} | "
                     f"{info.get('workers', '?')} workers | started {UTILS.timestamp_to_date(info.get('started_at', 0))}")
        if full['eta'] is not None:
            full_text += f" | time left ~{format_duration(full['eta'])}"
        elif state == 'done' and full['last_done']:
            full_text += f" | finished {UTILS.timestamp_to_date(full['last_done'])}"
    put_text(win, pos, full_text, P_text)
    pos += UIgraph.Point(0, 1)
    live = cov['live'] or {}
    put_text(win, pos, f"live scan: {SCAN.CHAIN_SCANNER.status}"
                       + (f" | from height {live['start_height']:,}" if live.get('start_height') is not None else ''), P_text)
    pos += UIgraph.Point(0, 1)
    put_text(win, pos, f"mempool scan: {SCAN.MEMPOOL_SCANNER.status} | transactions {len(SCAN.MEMPOOL_SCANNER.txs):,}", P_text)
    pos += UIgraph.Point(0, 2)

    # the buttons: not drawn while their job runs (it can not start twice)
    if data.get('scan_job'):
        put_text(win, pos + UIgraph.Point(0, 1), f"{data['scan_job']}...", P_text, bold=True)
    elif full['running']:
        stop_button = ELEMENTS.create_button(win, screenState, main_scope, 'stop full scan', pos,
                                             custom_scope_function=ScopeActions.press_enter, button_type='execution')
        if stop_button.data.get('pressed_enter'):
            stop_button.data['pressed_enter'] = False
            start_puzzle_scan_job(screenState, data, 'stopping the full scan', SCAN.FULL_SCAN.stop, SCAN.CATALOG)
    else:
        scan_button = ELEMENTS.create_button(win, screenState, main_scope, 'scan everything', pos,
                                             custom_scope_function=ScopeActions.press_enter, button_type='execution')
        if scan_button.data.get('pressed_enter'):
            scan_button.data['pressed_enter'] = False
            banner_scope = ELEMENTS.confirm_banner_scope(screenState, main_scope, 'scan_everything_banner')
            banner_scope.cursor_x = 1  # cancel is selected when the banner opens
            screenState.activeScope = banner_scope
        if full['end'] is not None and full['chunks_done'] < full['chunks_total']:
            resume_button = ELEMENTS.create_button(win, screenState, main_scope, 'resume full scan',
                                                   pos + UIgraph.Point(len('scan everything') + 12, 0),
                                                   custom_scope_function=ScopeActions.press_enter,
                                                   button_type='execution')
            if resume_button.data.get('pressed_enter'):
                resume_button.data['pressed_enter'] = False
                start_puzzle_scan_job(screenState, data, 'starting the full scan', SCAN.FULL_SCAN.start,
                                      SCAN.CATALOG, False, CONF.PUZZLE_SCAN_WORKERS)
    message = data.get('scan_job_message') or SCAN.FULL_SCAN.message
    if message:
        put_text(win, pos + UIgraph.Point(0, 3), message, P_text)

    lines = ["Scan the whole chain again?",
             f"The counts of {cov['puzzles']:,} puzzles ({cov['spends']:,} spends) are deleted and counted again from "
             f"height 0 to {tip:,}, with {CONF.PUZZLE_SCAN_WORKERS} worker processes: it takes one or two hours.",
             "The names and the catalog files are kept; the live scan goes on from the tip meanwhile."]
    if ELEMENTS.create_confirm_banner(win, screenState, main_scope, 'scan_everything_banner', lines, 'scan everything'):
        start_puzzle_scan_job(screenState, data, 'starting the full scan', SCAN.FULL_SCAN.start,
                              SCAN.CATALOG, True, CONF.PUZZLE_SCAN_WORKERS)


def start_puzzle_scan_job(screenState: ScreenState, data: dict, job: str, fn, *args):
    """Run fn (start or stop the full scan) in a thread; the scanner view shows the job while it runs"""
    data['scan_job'] = job
    data['scan_job_message'] = None

    def run():
        try:
            fn(*args)
        except Exception as e:
            logging(debug_logger, "DEBUG", f"PUZZLE SCAN job ERROR {job}: {e}")
            UTILS.logging_traceback("PUZZLE SCAN JOB")
            data['scan_job_message'] = f"{job} error: {e}"
        finally:
            data['coverage_time'] = 0  # read the coverage again
            data['scan_job'] = None

    job_thread = threading.Thread(target=run, daemon=True, name=job)
    job_thread.start()
    with screenState.lock:
        screenState.running_threads.append(job_thread)


# the filters of the all puzzles view: (field, label). A list field keeps an id; a text field
# keeps the text searched (lowercase)
PUZZLE_FILTER_FIELDS = [('family', 'family'), ('puzzle_type', 'puzzle type'), ('custody', 'custody'),
                        ('project', 'project'), ('status', 'status'), ('behaviour', 'behaviour'),
                        ('name', 'name contains'),
                        ('layers', 'layers contain'), ('fingerprint', 'fingerprint contains')]
PUZZLE_TEXT_FILTERS = ('name', 'layers', 'fingerprint')
PUZZLE_STATUSES = [s.value for s in TYPES.PuzzleStatus]


def puzzle_filter_values(field: str) -> list:
    """(id, label) of the values a list field can be filtered on"""
    if field == 'status':
        return [(v, v) for v in PUZZLE_STATUSES]
    if field == 'behaviour':
        return [(v, v) for v in SCAN.BEHAVIOUR_CLASSES + [SCAN.BEHAVIOUR_NOT_RUN]]
    return [(v, PUZ.value_label(field, v)) for v in PUZ.field_values(field)]


def puzzle_filter_text(field: str, value: str) -> str:
    label = dict(PUZZLE_FILTER_FIELDS)[field]
    if field in PUZZLE_TEXT_FILTERS:
        return f"{label} '{value}'"
    return f"{label} = {value if field in ('status', 'behaviour') else PUZ.value_label(field, value)}"


def behaviour_cell(layered_puzzle_fingerprint: str) -> str:
    """The behaviour column of the all puzzles view: the class, the spends run after it (9k:
    it fits 19 columns)"""
    h = SCAN.BEHAVIOUR_HINTS.get(layered_puzzle_fingerprint)
    if h is None:
        return '-'
    runs = h['runs']
    return f"{h['custody_hint']} {runs if runs < 1000 else f'{runs // 1000}k'}"


BEHAVIOUR_TEMPLATE_ROWS = 3  # the modes of the template shown on the puzzle detail screen


def behaviour_rows(layered_puzzle_fingerprint: str, custody: str, outputs: bool = True) -> list:
    """The behaviour hint of the puzzle detail view (docs/classification.md, step 4): what the
    spends of the fingerprint output once run. A hint, never saved. [field, value] rows"""
    h = SCAN.BEHAVIOUR_HINTS.get(layered_puzzle_fingerprint)
    if h is None:
        return [['behaviour', SCAN.BEHAVIOUR_NOT_RUN]]
    rows = [['behaviour', f"{h['custody_hint']} ({h['runs']:,} {'spend' if h['runs'] == 1 else 'spends'} run)"]]
    suggest = SCAN.behaviour_custody_hint(layered_puzzle_fingerprint, custody)
    if suggest:
        rows.append(['custody hint', ' or '.join(PUZ.value_label('custody', v) or v for v in suggest)])
    if h['behaves_like']:
        rows.append(['like', ', '.join(f"{label} {s:.0%}" for label, s, _ in h['behaves_like'])])
    if h['disagrees']:
        rows.append(['disagrees', f"with the catalog: {h['disagrees']}"])
    t = h['template']
    if t['same']:
        rows.append(['same template', f"{t['same']:,} other {'puzzle' if t['same'] == 1 else 'puzzles'}"])
    if outputs:
        # the template (behaviour.py, step 6): a row per mode, its core then [the optional kinds]
        modes = t['modes'][:BEHAVIOUR_TEMPLATE_ROWS]
        rows += [['template' if i == 0 else '', SCAN.template_mode_text(m)] for i, m in enumerate(modes)]
        more = len(t['modes']) - len(modes)
        if more or t['rare']:
            rows.append(['', ' | '.join(([f"{more} more {'mode' if more == 1 else 'modes'}"] if more else [])
                                        + ([f"rare: {'<1%' if t['rare'] < 0.005 else format(t['rare'], '.0%')}"] if t['rare'] else []))])
    return rows


def puzzle_matches(entry, c: dict, layers: str, filters: list) -> bool:
    """The filters of the same field are alternatives (any), the fields must all match"""
    by_field = {}
    for field, value in filters:
        by_field.setdefault(field, []).append(value)
    for field, values in by_field.items():
        if field == 'status':
            ok = c['status'] in values
        elif field == 'behaviour':
            ok = SCAN.behaviour_class(entry.layered_puzzle_fingerprint) in values
        elif field == 'project':
            projects = set((c['project'][0] or '').split(' + ')) | set(c['project_dependencies'][0])
            ok = any(v in projects for v in values)
        elif field == 'name':
            ok = any(v in (c['label'] or '').lower() for v in values)
        elif field == 'layers':
            ok = any(v in layers for v in values)
        elif field == 'fingerprint':
            ok = any(v in entry.layered_puzzle_fingerprint for v in values)
        else:
            ok = c[field][0] in values
        if not ok:
            return False
    return True


def screen_puzzles_all(stdscr, keyboardState, screenState, fullNodeState: FullNodeState, figlet=False):
    """Every puzzle seen, with the spends in a time window, filtered by its fields"""
    active_scope: Scope = screenState.activeScope
    main_scope: Scope = active_scope.main_scope
    screenState.scope_exec_args = [screenState]
    main_scope.update_2d()
    data = main_scope.data
    filters = data.setdefault('filters', [])
    # c clears the filters, but not while typing a filter value
    if filters and screenState.activeScope.mode != TYPES.ScopeMode.INSERT:
        if keyboardState.key == 'c':
            filters.clear()
        else:
            screenState.footer_text += "| clear filters=c "

    title = 'all puzzles'
    win, main_win_size, pos = puzzle_screen_win(stdscr, screenState, title)
    P_text = screenState.colorPairs["body"]
    # the counts go next to the title, on its text row
    status_pos = UIgraph.Point(1 + len(title) + 2 + 3, 2)

    entries, version = SCAN.CATALOG.snapshot()
    windows = list(SCAN.TIME_WINDOWS)

    # controls: the time window, under it the filters button with the filters in use; with the
    # filters on, a panel under them with the buttons to add one
    menus = []  # drawn last: an open list goes over the rest
    draw_window = lambda only_init, pos=pos: ELEMENTS.create_button_menu(win, screenState, main_scope, 'time window',
                                                                         windows, pos, only_init, value_width=3)
    window_scope = draw_window(True)
    menus.append(draw_window)
    window = windows[window_scope.cursor]
    pos += UIgraph.Point(0, 3)
    filters_button = ELEMENTS.create_button(win, screenState, main_scope, 'filters', pos,
                                            custom_scope_function=ScopeActions.press_enter, button_type='boolean')
    if filters_button.data.get('pressed_enter'):
        filters_button.data['pressed_enter'] = False
        data['show_filters'] = not data.get('show_filters')
    filters_button.bool = bool(data.get('show_filters'))
    # the filters in use: a strip in the color of the button, after a gap, as long as its text
    # and one column (before it)
    filters_text = ' · '.join(puzzle_filter_text(f, v) for f, v in filters)
    strip_x = pos.x + len('filters') + 4 + 3 + 3
    P_strip = UIgraph.addCustomColorTuple((screenState.colors["chia_green"], screenState.colors["dark_green"]),
                                          screenState.cursesColors)
    put_text(win, UIgraph.Point(strip_x, pos.y + 1), f" {filters_text or 'no filters'}", P_strip, bold=True)
    pos += UIgraph.Point(0, 3)

    if data.get('show_filters'):
        # the panel: one background under all its buttons, the color of a boolean button that is
        # on (the filters button), as high as the buttons
        C_panel = screenState.colors["dark_green"]
        P_panel = UIgraph.addCustomColorTuple((screenState.colors["chia_green"], C_panel), screenState.cursesColors)
        if not filters_button.selected():
            # the button goes on into the panel: its lower row in the panel color (when it is
            # selected, its selection line stays there)
            button_width = len('filters') + 2 * 2 + 3 + 1
            put_text(win, pos + UIgraph.Point(0, -1), ' ' * button_width, P_panel)
        P_panel_field = UIgraph.addCustomColorTuple((screenState.colors["chia_green"], screenState.colors["background"]),
                                                    screenState.cursesColors)
        panel_width = main_win_size.x - 2
        for i in range(3):
            put_text(win, pos + UIgraph.Point(0, i), ' ' * panel_width, P_panel)
        panel_buttons = dict(C_background=C_panel, C_button=screenState.colors["chia_green"],
                             C_text=screenState.colors["white"], C_selection=screenState.colors["gray"])
        row = pos + UIgraph.Point(2, 0)
        field_labels = [label for _, label in PUZZLE_FILTER_FIELDS]
        field_width = max(len(label) for label in field_labels)
        draw_field = lambda only_init, row=row: ELEMENTS.create_button_menu(win, screenState, main_scope, 'filter',
                                                                            field_labels, row, only_init,
                                                                            value_width=field_width,
                                                                            C_background=C_panel)
        field_scope = draw_field(True)
        menus.append(draw_field)
        field = PUZZLE_FILTER_FIELDS[field_scope.cursor][0]
        x = row.x + len('filter') + 2 + field_width + 7 + 2
        if field in PUZZLE_TEXT_FILTERS:
            text_scope = ELEMENTS.create_prompt(win, screenState, keyboardState, main_scope, 'filter_text',
                                                UIgraph.Point(x, row.y + 1), "text: ", 30, P_panel, True, False,
                                                custom_scope_function=ScopeActions.press_enter,
                                                P_text_field=P_panel_field)
            add_value = text_scope.data.get('prompt', '').strip().lower()
            add_pressed = text_scope.data.pop('pressed_enter', False)
            x += len("text: ") + 30 + 4
        else:
            values = puzzle_filter_values(field)
            value_labels = [label for _, label in values] or ['-']
            value_width = max(len(label) for label in value_labels)
            draw_value = lambda only_init, value_labels=value_labels, point=UIgraph.Point(x, row.y), \
                value_width=value_width: ELEMENTS.create_button_menu(win, screenState, main_scope, 'value',
                                                                     value_labels, point, only_init,
                                                                     value_width=value_width,
                                                                     C_background=C_panel)
            value_scope = draw_value(True)
            menus.append(draw_value)
            add_value = values[value_scope.cursor % len(values)][0] if values else ''
            add_pressed = False
            x += len('value') + 2 + value_width + 7 + 2
        add_button = ELEMENTS.create_button(win, screenState, main_scope, 'add', UIgraph.Point(x, row.y),
                                            custom_scope_function=ScopeActions.press_enter, button_type='execution',
                                            **panel_buttons)
        if add_button.data.pop('pressed_enter', False) or add_pressed:
            if add_value and (field, add_value) not in filters:
                filters.append((field, add_value))
        x += len('add') + 4 + 3 + 4
        for name, action in (('remove last', lambda: filters.pop() if filters else None), ('clear', filters.clear)):
            button = ELEMENTS.create_button(win, screenState, main_scope, name, UIgraph.Point(x, row.y),
                                            custom_scope_function=ScopeActions.press_enter, button_type='execution',
                                            **panel_buttons)
            if button.data.pop('pressed_enter', False):
                action()
            x += len(name) + 4 + 3 + 4
        pos += UIgraph.Point(0, 3)
    pos += UIgraph.Point(0, 1)

    # the rows: cached until the catalog, the window, the filters or the counts change
    counts = SCAN.WINDOW_COUNTS.get(window) if window != 'all' else None
    key = (version, PUZ.catalog_generation(), SCAN.BEHAVIOUR_GENERATION, window, tuple(filters), id(counts))
    working = None  # what is being computed, at the top right; the table is empty meanwhile
    classes = None
    if data.get('rows_key') != key:
        classes = SCAN.CATALOG.classifications_ready(entries, screenState.running_threads, screenState.lock)
        if classes is None:
            working = f"classifying the puzzles: {SCAN.CATALOG.classifications_progress():,} of {len(entries):,}"
        elif window != 'all' and counts is None:
            working = f"counting the spends in the last {window}..."
    if data.get('rows_key') != key and working is None:
        found = []
        for e in entries:
            c = classes[e.layered_puzzle_fingerprint]
            layers = ' > '.join(e.sub_puzzle_names())
            if filters and not puzzle_matches(e, c, layers.lower(), filters):
                continue
            n = e.seen_count if window == 'all' else counts.get(e.layered_puzzle_fingerprint, 0)
            if window != 'all' and n == 0:
                continue
            found.append((n, e, c, layers))
        found.sort(key=lambda r: -r[0])
        rows = [[c['label'] or '-',
                 PUZ.value_label('family', c['family'][0]) or '-',
                 PUZ.value_label('puzzle_type', c['puzzle_type'][0]) or '-',
                 PUZ.value_label('custody', c['custody'][0]) or '-',
                 behaviour_cell(e.layered_puzzle_fingerprint),
                 PUZ.project_label(c['project'][0]) or '-',
                 layers, str(c['depth'] or '-'), f"{n:,}", UTILS.timestamp_to_date(e.last_seen) if e.last_seen else '-',
                 c['status']]
                for n, e, c, layers in found]
        data['rows'], data['row_keys'], data['rows_key'] = rows, [r[1].layered_puzzle_fingerprint for r in found], key
        data['rows_spends'] = sum(r[0] for r in found)
    ready = data.get('rows_key') == key
    rows, keys = (data.get('rows', []), data.get('row_keys', [])) if ready else ([], [])

    window_text = 'all time' if window == 'all' else f"the last {window}"
    if ready:
        status = f"{len(rows):,} of {len(entries):,} puzzles | {data.get('rows_spends', 0):,} spends in {window_text}"
    else:
        status = f"{len(entries):,} puzzles"
    put_text(win, status_pos, status, P_text, bold=True)
    if working:
        put_text(win, UIgraph.Point(max(status_pos.x + len(status) + 3, main_win_size.x - len(working) - 3),
                                    status_pos.y), working, P_text, bold=True)

    legend = ['name', 'family', 'puzzle type', 'custody', 'behaviour', 'project', 'layers', 'depth', f'spends {window}',
              'last seen', 'status']
    column_widths = [28, 9, 14, 9, 19, 16, 29, None, None, None, None]
    if rows or (entries and not ready):
        tab_scope = screenState.scopes.get(f"{main_scope.id}_all_puzzles")
        if tab_scope is not None and tab_scope.data.get('rows_key') != data.get('rows_key'):
            # new rows: create_tab compares only the first and the last row with its cache
            tab_scope.data['cached_data_table'] = tab_scope.data['column_sizes'] = None
            tab_scope.data['rows_key'] = data.get('rows_key')
        tab_size = UIgraph.Point(main_win_size.x - 2, main_win_size.y - pos.y - 2)
        ELEMENTS.create_tab(win, screenState, main_scope, 'all_puzzles', rows, keys, fresh_table_colors(rows),
                            False, pos, tab_size, keyboardState, scopeAction_open_puzzle, True, False,
                            legend, column_widths)
    else:
        put_text(win, pos + UIgraph.Point(0, 1),
                 "no puzzles: scan the chain in the puzzle scanner view" if not entries else "no puzzles match", P_text)

    for draw in sorted(menus, key=lambda draw: draw(True) is screenState.activeScope):
        draw(False)


# the lists of puzzle_types.json: menu name -> field
PUZZLE_LISTS = {'families': 'family', 'puzzle types': 'puzzle_type', 'custodies': 'custody', 'projects': 'project'}
NEW_LIST_VALUE = '(new)'


def screen_puzzle_lists(stdscr, keyboardState, screenState, fullNodeState: FullNodeState, figlet=False):
    """The lists that classify the puzzles, one view each"""
    puzzle_submenu(stdscr, keyboardState, screenState, fullNodeState,
                   [(name, lambda *args, field=field, **kwargs: screen_puzzle_list(field, *args, **kwargs))
                    for name, field in PUZZLE_LISTS.items()])


LIST_EDIT_ACTIONS = ('save', 'cancel')


def press_list_row(scope: Scope, screenState: ScreenState, *args):
    """enter on a row of a list table: the screen reads data['pressed'] (modify or delete it)"""
    scope.data['pressed'] = True
    return scope


def list_value_lock(field: str, value: str, seen: int):
    """Why the value can not be deleted, None if it can"""
    if value == NEW_LIST_VALUE:
        return "it is not saved yet"
    if value in PUZ.CODE_VALUES.get(field, ()):
        return "the code uses it"
    uses = PUZ.value_uses(field, value)
    if uses:
        return f"{uses:,} catalog entries use it" if uses > 1 else "a catalog entry uses it"
    if seen:
        return f"{seen:,} puzzles seen are classified with it" if seen > 1 else "a puzzle seen is classified with it"
    if value not in PUZ.field_entries(field):
        return "it is a source of the catalog, not a value of the list"
    return None


def screen_puzzle_list(field: str, stdscr, keyboardState, screenState, fullNodeState: FullNodeState, figlet=False):
    """A list of puzzle_types.json: the new value and delete buttons, the values in a table, a
    strip under it (what happens, save / cancel of an edit). Enter on a row opens it in the
    table (an empty line above and below it): ←→ choose a cell (a frame on it), enter edits it,
    ↓ goes to save / cancel, esc cancels. delete goes into the table with a red selection: enter
    on a row asks to delete it. A value used by the code, the catalog or the puzzles seen can
    not be deleted (gray)"""
    active_scope: Scope = screenState.activeScope
    main_scope: Scope = active_scope.main_scope
    screenState.scope_exec_args = [screenState]
    main_scope.update_2d()
    data = main_scope.data
    title = next(name for name, f in PUZZLE_LISTS.items() if f == field)

    win, main_win_size, pos = puzzle_screen_win(stdscr, screenState, title)

    entries_by_id = PUZ.field_entries(field)
    values = PUZ.field_values(field)  # projects: also the ones only named by the sources
    entries, _ = SCAN.CATALOG.snapshot()
    # the puzzles seen of each value (and so if it can be deleted): the table waits for them
    classes = SCAN.CATALOG.classifications_ready(entries, screenState.running_threads, screenState.lock)
    working = None if classes is not None else \
        f"classifying the puzzles: {SCAN.CATALOG.classifications_progress():,} of {len(entries):,}"
    if working:
        put_text(win, UIgraph.Point(main_win_size.x - len(working) - 3, 2), working,
                 screenState.colorPairs["body"], bold=True)
        values = []
        data['edit'] = None
    seen = {}
    for c in (classes or {}).values():
        if field == 'project':
            for p in set((c['project'][0] or '').split(' + ')):
                seen[p] = seen.get(p, 0) + 1
        else:
            seen[c[field][0]] = seen.get(c[field][0], 0) + 1

    cells = ['label', 'description'] + (['role', 'sources'] if field == 'project' else [])
    legend = cells + ['catalog entries', 'puzzles seen', 'used by']
    column_widths = [24, 60] + ([10, 40] if field == 'project' else []) + [None, None, None]

    def cell_texts(v):
        e = {} if v == NEW_LIST_VALUE else (entries_by_id.get(v) or {})
        return {'label': e.get('label', '' if v == NEW_LIST_VALUE else v), 'description': e.get('description', ''),
                'role': e.get('role', 'app'), 'sources': ', '.join(e.get('sources', []))}

    # the scopes: the new value and delete buttons and the table, elements of the screen; the
    # edit of a row, a child of the table: esc goes back to it
    tab_name = f'list_{field}'
    if f"{main_scope.id}_{tab_name}" not in screenState.scopes:
        scope = Scope(f"{main_scope.id}_{tab_name}", main_scope.screen, screenState)
        scope.parent_scope = scope.main_scope = main_scope
        scope.exec = ScopeActions.activate_scope
        scope.exec_own = press_list_row
        scope.base_point = pos + UIgraph.Point(0, 3)
        main_scope.sub_scopes[scope.name] = scope
    tab_scope = screenState.scopes[f"{main_scope.id}_{tab_name}"]
    edit_scope = ELEMENTS.action_strip_scope(screenState, tab_scope, 'edit')
    # enter runs its own action, never a sub scope (the cell prompt is one)
    edit_scope.sub_scope_selected = None
    banner_scope = ELEMENTS.confirm_banner_scope(screenState, main_scope, 'delete_value_banner')
    typing_scope = screenState.scopes.get(f"{edit_scope.id}_cell")

    edit = data.get('edit')  # {'value': id or NEW_LIST_VALUE, 'draft': {cell: text}, 'typing': cell or None}
    active = screenState.activeScope
    if edit and active not in (edit_scope, typing_scope) and active.parent_scope is not typing_scope:
        # esc out of the edit: nothing is saved
        data['edit'] = edit = None
    if data.get('delete_mode') and active is not tab_scope and banner_scope not in (active, active.parent_scope):
        data['delete_mode'] = False  # esc out of the table, or the banner closed
    delete_mode = data.get('delete_mode', False)

    def message(text, error=False):
        data['list_message'], data['list_error'] = text, error

    def current_value():
        if edit:
            return edit['value']
        n = len(values) + (1 if edit and edit['value'] == NEW_LIST_VALUE else 0)
        if not n:
            return None
        return NEW_LIST_VALUE if tab_scope.cursor % n == len(values) else values[tab_scope.cursor % n]

    # enter on a row: open it for an edit, or (delete mode) ask to delete it
    current = current_value()
    if tab_scope.data.pop('pressed', False) and current is not None and not edit:
        message('')
        if not delete_mode:
            data['edit'] = edit = dict(value=current, draft=cell_texts(current), typing=None)
            edit_scope.cursor, edit_scope.cursor_x = 0, 0
            screenState.activeScope = edit_scope
        elif (lock := list_value_lock(field, current, seen.get(current, 0))):
            message(f"can not delete it: {lock}", True)
        else:
            data['delete_value'] = current
            banner_scope.cursor_x = 1  # cancel is selected when the banner opens
            screenState.activeScope = banner_scope

    # the buttons above the table: new value (a new row at the end of the table, in edit),
    # delete (into the table, enter deletes the row)
    new_button = ELEMENTS.create_button(win, screenState, main_scope, 'new value', pos,
                                        custom_scope_function=ScopeActions.press_enter, button_type='execution')
    delete_button = ELEMENTS.create_button(win, screenState, main_scope, 'delete',
                                           pos + UIgraph.Point(len('new value') + 9 + 2, 0),
                                           custom_scope_function=ScopeActions.press_enter, button_type='execution')
    pos += UIgraph.Point(0, 3)
    if new_button.data.pop('pressed_enter', False) and not working:
        message('')
        data['edit'] = edit = dict(value=NEW_LIST_VALUE, draft=cell_texts(NEW_LIST_VALUE), typing='label')
        edit_scope.cursor, edit_scope.cursor_x = 0, 0
        screenState.activeScope = edit_scope
    if delete_button.data.pop('pressed_enter', False) and not working:
        message('')
        data['delete_mode'] = delete_mode = True
        main_scope.select_sub_scope_2d(tab_scope)  # the table is the selected element: its frame
        main_scope.update_2d()
        screenState.activeScope = tab_scope

    # the edit: row 0 the cells of the row, row 1 save / cancel in the strip
    if edit:
        if typing_scope is not None and typing_scope.data.pop('pressed_enter', False):
            edit['draft'][edit['typing']] = typing_scope.data['prompt']
            edit['typing'] = edit['typing_open'] = None
            if edit['value'] == NEW_LIST_VALUE:
                # a new value is filled cell after cell: the next one (a role is not typed: the
                # frame goes on it), after the last one save
                if edit_scope.cursor_x + 1 < len(cells):
                    edit_scope.cursor_x += 1
                    if cells[edit_scope.cursor_x] != 'role':
                        edit['typing'] = cells[edit_scope.cursor_x]
                else:
                    edit_scope.cursor = 1
        elif edit['typing'] and edit.get('typing_open') and screenState.activeScope is edit_scope:
            edit['typing'] = edit['typing_open'] = None  # esc in the cell: its new text is not kept
        edit_scope.cursor %= 2
        if edit.get('row') != edit_scope.cursor:
            # the strip starts at save, the cells at the cell left there
            edit['row'], edit['cell'] = edit_scope.cursor, edit_scope.cursor_x if edit_scope.cursor == 1 else edit.get('cell', 0)
            edit_scope.cursor_x = 0 if edit_scope.cursor == 1 else edit['cell']
        n = len(cells) if edit_scope.cursor == 0 else len(LIST_EDIT_ACTIONS)
        edit_scope.cursor_x = max(0, min(edit_scope.cursor_x, n - 1))
        if edit_scope.data.pop('pressed', False):
            if edit_scope.cursor == 0:
                cell = cells[edit_scope.cursor_x]
                if cell == 'role':
                    roles = list(PUZ.PROJECT_ROLES)
                    edit['draft']['role'] = roles[(roles.index(edit['draft']['role']) + 1) % len(roles)]
                else:
                    edit['typing'] = cell
            elif LIST_EDIT_ACTIONS[edit_scope.cursor_x] == 'cancel':
                data['edit'] = edit = None
                screenState.activeScope = tab_scope
            else:
                d = edit['draft']
                sources = [x.strip() for x in d['sources'].split(',') if x.strip()] if field == 'project' else None
                try:
                    value = PUZ.save_list_value(field, None if edit['value'] == NEW_LIST_VALUE else edit['value'],
                                                d['label'], d['description'],
                                                d['role'] if field == 'project' else None, sources)
                    message(f"saved in puzzle_types.json: {PUZ.value_label(field, value)}")
                    data['edit'] = edit = None
                    entries_by_id, values = PUZ.field_entries(field), PUZ.field_values(field)
                    if value in values:
                        data['edit_was_open'] = values.index(value)
                    screenState.activeScope = tab_scope
                except ValueError as e:
                    message(f"not saved: {e}", True)

    if not edit and 'edit_was_open' in data:
        # the edit closed: the cursor back on the row (the empty line above it is gone)
        tab_scope.cursor = data.pop('edit_was_open')

    # a message is about the row it was given on
    current = current_value()
    if data.get('message_row') != current:
        data['message_row'] = current
        message('')

    rows, keys = [], []
    for v in values + ([NEW_LIST_VALUE] if edit and edit['value'] == NEW_LIST_VALUE else []):
        texts = dict(cell_texts(v), **(edit['draft'] if edit and edit['value'] == v else {}))
        row = [texts[c] for c in cells] + \
              ['' if v == NEW_LIST_VALUE else f"{PUZ.value_uses(field, v):,}",
               '' if v == NEW_LIST_VALUE else f"{seen.get(v, 0):,}",
               'code' if v in PUZ.CODE_VALUES.get(field, ()) else '']
        if edit and edit['value'] == v:
            # the row in edit opens: an empty line above and below it, the cursor on it
            empty = [''] * len(row)
            rows += [empty, row, empty]
            keys += [None, v, None]
            tab_scope.cursor = len(rows) - 2
        else:
            rows.append(row)
            keys.append(v)
    if edit:
        data['edit_was_open'] = values.index(edit['value']) if edit['value'] in values else max(0, len(values) - 1)

    # the table leaves 2 lines: its selection line and the strip
    tab_pos = pos
    tab_size = UIgraph.Point(main_win_size.x - 2, max(6, min(len(rows) + 4, main_win_size.y - pos.y - 4)))
    colors = fresh_table_colors(rows)
    background_like = None
    if edit:
        # the opened row on the background of its empty lines (the other one: the rows
        # alternate), the columns it can not change gray
        open_idx = tab_scope.cursor
        background_like = {open_idx: open_idx + 1}
        for j in range(len(cells), len(legend)):
            colors[open_idx][j] = screenState.colors["gray"]
    if delete_mode:
        # the rows that can not be deleted are gray
        for i, v in enumerate(keys):
            if v is not None and list_value_lock(field, v, seen.get(v, 0)):
                colors[i] = [screenState.colors["gray"]] * len(legend)
    if tab_scope.data.get('rows_shape') != (working is None, len(rows)):
        # the columns are sized on the rows: again when they arrive (empty while classifying)
        tab_scope.data['rows_shape'] = (working is None, len(rows))
        tab_scope.data['column_sizes'] = tab_scope.data['cached_data_table'] = None
    ELEMENTS.create_tab(win, screenState, main_scope, tab_name, rows, keys, colors,
                        False, tab_pos, tab_size, keyboardState, press_list_row, True, False,
                        legend, column_widths, no_cache=True, background_like=background_like,
                        P_frame=screenState.colorPairs["error"] if delete_mode else None,
                        P_row_select=screenState.colorPairs["error_white"] if delete_mode else None)

    # the opened row: its cells are text fields (the color of the prompts), a frame
    # on the selected one, the text field of create_prompt while it is edited
    x_starts = (tab_scope.data.get('column_sizes') or (None, None, None))[1]
    line = 3 + tab_scope.cursor - tab_scope.data.get('idx_first_element', 0)  # 3: the legend
    row_y = tab_pos.y + line
    if edit and x_starts and len(x_starts) >= len(cells) and tab_pos.y + 3 <= row_y < tab_pos.y + tab_size.y:
        soft_row = line % 2 == 1  # the rows alternate from the soft background (before the inversion)
        C_row = screenState.colors["tab_dark" if soft_row else "tab_soft"]
        # the cells that can be changed: the text field of the prompts (not typed in: green on dark green)
        P_cell = screenState.colorPairs["text_field"]

        # the opened row is wider than the table's columns: each column 2 more (grow) and moved
        # 1 + grow * its index to the right, less if the last column would go past the right edge
        n_cols = len(x_starts)
        row_texts = [str(t) for t in rows[tab_scope.cursor]] if tab_scope.cursor < len(rows) else [''] * n_cols
        table_end = tab_size.x - 2  # the last column of the table before its scroll bar
        room = table_end - (x_starts[-1] + len(row_texts[-1]) + 1)
        grow = max(0, min(2, (room - 1) // max(1, n_cols - 1)))

        def cell_box(c):
            x = tab_pos.x + x_starts[c] + 1 + grow * c
            end = tab_pos.x + (x_starts[c + 1] + 1 + grow * (c + 1) if c + 1 < n_cols else table_end)
            return UIgraph.Point(x, row_y), max(4, end - x - 2)

        # the row drawn again with the wider columns: the background, the columns that can not
        # be changed in gray, then the fields
        P_row = UIgraph.addCustomColorTuple((screenState.colors["chia_green"], C_row), screenState.cursesColors)
        P_row_gray = UIgraph.addCustomColorTuple((screenState.colors["gray"], C_row), screenState.cursesColors)
        ELEMENTS.create_text(win, UIgraph.Point(tab_pos.x, row_y), ' ' * (table_end + 1), P_row)
        for c in range(len(cells), min(n_cols, len(row_texts))):
            cell_pos, width = cell_box(c)
            ELEMENTS.create_text(win, cell_pos, ' ' + row_texts[c][:width - 1], P_row_gray)

        for c, cell in enumerate(cells):
            if cell == edit['typing'] and edit_scope.cursor == 0 and c == edit_scope.cursor_x:
                continue  # create_prompt draws it
            cell_pos, width = cell_box(c)
            text = edit['draft'][cell]
            text = text if len(text) < width else text[:width - 4] + '...'
            ELEMENTS.create_text(win, cell_pos, ' ' + text.ljust(width - 1), P_cell, True)
        if edit_scope.cursor == 0 and edit_scope.cursor_x < len(cells):
            cell_pos, width = cell_box(edit_scope.cursor_x)
            if edit['typing']:
                # the text field of the other prompts (e.g. the search of the full node view): it
                # is drawn as selected (only for this frame: enter on the edit is not sent to it)
                typing_scope = screenState.scopes.get(f"{edit_scope.id}_cell")
                edit_scope.sub_scope_selected = typing_scope
                typing_scope = ELEMENTS.create_prompt(win, screenState, keyboardState, edit_scope, 'cell',
                                                      cell_pos + UIgraph.Point(1, 0), '', width - 1, P_cell,
                                                      False, False, custom_scope_function=ScopeActions.press_enter)
                edit_scope.sub_scope_selected = typing_scope
                # the column before the field (the text of the other cells starts after a space)
                win.addstr(cell_pos.y, cell_pos.x, ' ',
                           curses.color_pair(screenState.colorPairs["text_field"]) | curses.A_REVERSE)
                typing_scope.main_scope = main_scope  # create_prompt makes its parent the main scope
                if screenState.activeScope is not typing_scope:
                    typing_scope.data['prompt'] = edit['draft'][edit['typing']]
                    typing_scope.data['cursor'] = len(typing_scope.data['prompt'])
                    typing_scope.mode = TYPES.ScopeMode.INSERT  # the next key is already text
                    screenState.activeScope = typing_scope
                    edit['typing_open'] = True
            ELEMENTS.draw_cell_frame(win, screenState, cell_pos, width, bool(edit['typing']), C_row)

    # the strip under the table
    strip_pos = tab_pos + UIgraph.Point(0, tab_size.y + 1)
    active = screenState.activeScope
    info, info_error = data.get('list_message') or '', data.get('list_error', False)
    if edit:
        selected = edit_scope.cursor_x if active is edit_scope and edit_scope.cursor == 1 else None
        if not info:
            what = 'new value' if edit['value'] == NEW_LIST_VALUE else 'modify'
            info = f"{what}: {edit['draft']['label'] or '(no label yet)'}"
        ELEMENTS.create_action_strip(win, screenState, strip_pos, tab_size.x, LIST_EDIT_ACTIONS, selected,
                                     info=info, info_error=info_error)
        if active is edit_scope:
            if edit_scope.cursor == 0:
                screenState.footer_text += "| next role=enter " if cells[edit_scope.cursor_x] == 'role' \
                    else "| edit cell=enter "
                screenState.footer_text += "| save=↓ "
            screenState.footer_text += "| cancel=esc "
        elif active is typing_scope:
            screenState.footer_text += "| keep=enter | undo=esc "
    else:
        if delete_mode and not info and current is not None:
            label = PUZ.value_label(field, current)
            lock = list_value_lock(field, current, seen.get(current, 0))
            info = f"{label}: can not be deleted, {lock}" if lock else f"{label}: not used, it can be deleted"
        ELEMENTS.create_action_strip(win, screenState, strip_pos, tab_size.x, (), info=info, info_error=info_error)
        if active is tab_scope:
            screenState.footer_text += "| delete=enter | stop deleting=esc " if delete_mode else "| modify=enter "

    value = data.get('delete_value')
    if value is not None:
        lines = [f"Delete \"{PUZ.value_label(field, value)}\" from the {title}?",
                 "It is removed from catalog/puzzle_types.json: no code, catalog entry or puzzle seen uses it."]
        if ELEMENTS.create_confirm_banner(win, screenState, main_scope, 'delete_value_banner', lines, 'delete it'):
            try:
                label = PUZ.value_label(field, value)
                PUZ.delete_list_value(field, value)
                message(f"deleted: {label}")
                values = PUZ.field_values(field)
                tab_scope.cursor = min(tab_scope.cursor, max(0, len(values) - 1))
                data['message_row'] = values[tab_scope.cursor] if values else None
            except ValueError as e:
                message(f"not deleted: {e}", True)
            data['delete_value'] = None
            screenState.activeScope = main_scope


FROM_THE_LAYERS = '(from the layers)'  # the first value of a list: no override


PUZZLE_DETAIL_PAGES = ['structure', 'spends', 'example spend', 'edit']


def screen_puzzle_detail(stdscr, keyboardState, screenState, fullNodeState: FullNodeState, figlet=False):
    """One layered puzzle fingerprint: what it is on the title row, and a page for each tab
    (PUZZLE_DETAIL_PAGES, ←→ on the screen): the layers, the spends, the example spend run, the
    name and the values to edit"""

    height = screenState.screen_size.y
    width = screenState.screen_size.x

    active_scope: Scope = screenState.activeScope
    main_scope: Scope = active_scope.main_scope
    screenState.scope_exec_args = [screenState]
    # ←→ switch the page (cursor_x), ↑↓ go through the elements of the page
    main_scope.update()

    win = createFullSubWin(stdscr, screenState, height, width)
    win.bkgd(' ', curses.color_pair(screenState.colorPairs["body"]))
    main_win_size = UIgraph.Point(win.getmaxyx()[1], win.getmaxyx()[0])

    C_background = screenState.colors["background"]
    P_text = screenState.colorPairs["body"]
    P_title = screenState.colorPairs["xch"]

    layered_puzzle_fingerprint = main_scope.data['layered_puzzle_fingerprint']
    entry = SCAN.CATALOG.get(layered_puzzle_fingerprint)
    if entry is None:
        # the counts were deleted (scan everything) since the view was opened
        put_text(win, UIgraph.Point(1, 1), "this puzzle is not in the catalog any more: go back (esc)", P_text)
        return
    c = entry.classification()

    ##### title, and what the puzzle is on its row (rule 1)
    pos = UIgraph.Point(1, 1)
    ELEMENTS.create_text_double_space(win, screenState, pos, 'puzzle', P_title, C_background,
                                      3, True, inv_color=False)
    values = ' · '.join(PUZ.value_label(field, c[field][0]) or '-'
                        for field in ('family', 'puzzle_type', 'custody', 'project'))
    put_text(win, pos + UIgraph.Point(len('puzzle') + 4, 1), f"{c['label']} | {c['status']} | {values}", P_text)
    pos += UIgraph.Point(0, 4)

    page = PUZZLE_DETAIL_PAGES[main_scope.cursor_x % len(PUZZLE_DETAIL_PAGES)]
    pos_tab_title = pos
    if screenState.activeScope is main_scope:
        screenState.footer_text += "| switch page=←→ "
    tabs_width = sum(len(f" {name.upper()} ") + 2 for name in PUZZLE_DETAIL_PAGES)
    menu_draws = []
    match page:
        case 'structure':
            puzzle_detail_layers(win, screenState, keyboardState, main_scope, entry, pos + UIgraph.Point(0, 2), main_win_size)
        case 'spends':
            puzzle_detail_spends(win, screenState, keyboardState, main_scope, entry, c, pos, main_win_size,
                                 pos.x + tabs_width + HEAT_TOP_GAP)
        case 'example spend':
            puzzle_detail_example(win, screenState, keyboardState, main_scope, entry, pos + UIgraph.Point(0, 2), main_win_size)
        case 'edit':
            menu_draws = puzzle_detail_edit(win, screenState, keyboardState, main_scope, entry, c,
                                            pos + UIgraph.Point(0, 4), main_win_size)

    ##### the tabs, after the page: the ▀ under the selected one is the top border of the table (rule 2)
    P_tab_title = screenState.colorPairs["title"]
    P_tab_soft = screenState.colorPairs["tab_soft"]
    pos = pos_tab_title
    for name in PUZZLE_DETAIL_PAGES:
        text = f" {name.upper()} "
        selected = name == page
        P_used = P_title if selected else P_tab_title
        ELEMENTS.create_text_double_space(win, screenState, pos, text, P_used, C_background, 3, True)
        underline_pos = pos + UIgraph.Point(0, 2)
        if selected:
            ELEMENTS.create_text(win, underline_pos, u'▀' * (len(text) + 2), P_tab_soft, True)
        else:
            ELEMENTS.create_text(win, underline_pos, ' ' * (len(text) + 2), P_used, True)
        pos += UIgraph.Point(len(text) + 2, 0)

    # run copy/paste action or other pending stuffs (the copy banner of a table)
    if len(screenState.pending_action) > 0:
        for i, fn in screenState.pending_action:
            fn()
        screenState.pending_action = []
    # last, the open one at the end: its list is drawn over the rest
    for draw in sorted(menu_draws, key=lambda draw: draw(True) is screenState.activeScope):
        draw(False)


def field_pairs_table(win, screenState: ScreenState, keyboardState, main_scope: Scope, name: str,
                      left: list, right: list, legend: list, pos: UIgraph.Point, max_y: int) -> int:
    """A table of two field / value pairs a row ([field, value] rows on the left and on the
    right), the right pair from the middle; it scrolls when it is taller than max_y - pos.y.
    y copies a value of the selected row. Return its height"""
    rows = [(left[n] if n < len(left) else ['', '']) + (right[n] if n < len(right) else ['', ''])
            for n in range(max(len(left), len(right)))] or [['', '', '', '']]
    size = UIgraph.Point(win.getmaxyx()[1] - 2, min(len(rows) + 4, max(max_y - pos.y, 6)))
    # two field columns of 13, the values share the rest (the separators and the frame take 44).
    # create_tab shrinks a column to its text and gives the space left to all the columns: the
    # formatters pad the left value and the right field, so the right pair starts at the middle
    # (a formatter changes only the width, y copies the value without the spaces)
    left_width = max((size.x - 44) // 2, 10)
    right_width = max(size.x - 44 - left_width, 10)
    # the right value is padded too: short values would leave space to the other columns
    ELEMENTS.create_tab(win, screenState, main_scope, name, rows,
                        [str(n) for n in range(len(rows))], fresh_table_colors(rows), False,
                        pos, size, keyboardState, scopeAction_nothing, True, False, legend,
                        column_widths=[13, left_width, 13, right_width],
                        formatters=[None, lambda v: v.ljust(left_width), lambda v: v.ljust(13),
                                    lambda v: v.ljust(right_width)],
                        no_cache=True)
    return size.y


PUZZLE_SPENDS_STYLE = None  # count_style('spends'), made when the screen is first drawn


def puzzle_spends_series(fingerprint: str, first_seen: float):
    """The spends of a fingerprint for the heat map, each at the time of its block
    (puzzle_spends_blocks; DB_PUZZLES, a few seconds for the busiest puzzles: run it in a thread)"""
    conn = SCAN.CATALOG.connection()
    try:
        pairs = conn.execute(
            "SELECT t.timestamp, b.spends FROM puzzles p JOIN puzzle_spends_blocks b ON b.puzzle_id = p.id "
            "JOIN block_times t ON t.height = b.height WHERE p.layered_puzzle_fingerprint = ?",
            (fingerprint,)).fetchall()
    finally:
        conn.close()
    # before the first spend there is nothing to count: no data
    start = (first_seen // SCAN.DAY) * SCAN.DAY if first_seen else 0
    return HEAT.CountSeries(pairs, start)


def puzzle_detail_spends(win, screenState: ScreenState, keyboardState, main_scope: Scope, entry, c: dict,
                         pos: UIgraph.Point, main_win_size: UIgraph.Point, top_left: int):
    """The spends page: the spends in time (a heat map right under the tabs, rule 10), then the
    counts and the behaviour of its spends"""
    global PUZZLE_SPENDS_STYLE
    P_text = screenState.colorPairs["body"]
    P_error = screenState.colorPairs["error"]
    data = main_scope.data

    left = [['spent', f"{entry.seen_count:,} times"],
            ['first seen in', entry.source],
            ['first seen', UTILS.timestamp_to_date(entry.first_seen)],
            ['last seen', UTILS.timestamp_to_date(entry.last_seen)]]
    if entry.first_height is not None:
        left.append(['heights', f"{entry.first_height:,}-{entry.last_height:,}"])
    left += [['example coin', f"0x{entry.example_coin_id}"],
             ['example spend', f"at height {entry.example_height:,}" if entry.example_height else 'seen in the mempool'],
             ['fingerprint', entry.layered_puzzle_fingerprint]]
    right = behaviour_rows(entry.layered_puzzle_fingerprint, c['custody'][0])
    table_rows = max(len(left), len(right)) + 4

    # the graph gets the rows the table does not need, at least GRAPH_MIN; the table scrolls
    GRAPH_MIN = 8
    graph_top = pos.y + 3  # the tab titles, then the half line
    space = main_win_size.y - graph_top - 2  # the footer, and the line between the two
    table_h = min(table_rows, max(space - GRAPH_MIN - 1, 6))
    graph_h = space - table_h - 1

    # the series, read in a thread when the page is opened (a second for the busiest puzzles)
    if 'spends_series' not in data:
        data['spends_series'] = None
        data['spends_error'] = None

        def load():
            try:
                data['spends_series'] = puzzle_spends_series(entry.layered_puzzle_fingerprint, entry.first_seen)
            except Exception as e:
                logging(debug_logger, "DEBUG", f"PUZZLE DETAIL spends not read: {e}")
                data['spends_error'] = str(e)
        thread = threading.Thread(target=load, daemon=True)
        thread.start()
        screenState.running_threads.append(thread)

    if graph_h >= 4:
        # the half line under the tabs goes on to the right end of the graph, which starts right under it
        put_text(win, UIgraph.Point(pos.x, graph_top - 1), '▀' * (main_win_size.x - 2), screenState.colorPairs["tab_dark_bg"])
        graph_pos = UIgraph.Point(pos.x, graph_top)
        series = data['spends_series']
        if series is not None:
            if PUZZLE_SPENDS_STYLE is None:
                PUZZLE_SPENDS_STYLE = count_style('spends')
            view = data.setdefault('spends_view', HEAT.HeatmapView(HEAT.SCALE_INDEX['24h']))
            ELEMENTS.create_time_heatmap(win, screenState, keyboardState, main_scope, "puzzle_spends_graph",
                                         graph_pos, UIgraph.Point(main_win_size.x - 2, graph_h),
                                         series, view, PUZZLE_SPENDS_STYLE, top_left=top_left)
        elif data['spends_error']:
            put_text(win, graph_pos + UIgraph.Point(0, 1), f"the spends were not read: {data['spends_error']}", P_error, bold=True)
        else:
            put_text(win, graph_pos + UIgraph.Point(0, 1), "reading the spends...", P_text, bold=True)
        table_pos = UIgraph.Point(pos.x, graph_top + graph_h + 1)
    else:
        table_pos = UIgraph.Point(pos.x, pos.y + 2)  # no room for the graph: the table under the tabs
    field_pairs_table(win, screenState, keyboardState, main_scope, "puzzle_spends_info", left, right,
                      ['spends', '', 'behaviour', ''], table_pos, main_win_size.y - 2)


def example_spend_job(coin_id: str, height: int) -> dict:
    """The example spend, from the node (run it in a thread): the coin, its solution and the
    conditions the puzzle outputs with it"""
    out = RPC.call_rpc_node('get_puzzle_and_solution', coin_id=coin_id, height=height)
    if not out:
        return {'error': 'the node did not answer (is it running?)'}
    puzzle = PyProgram.fromhex(out['puzzle_reveal'].removeprefix('0x'))
    solution = PyProgram.fromhex(out['solution'].removeprefix('0x'))
    cost, result = puzzle.run_with_cost(EXAMPLE_SPEND_MAX_COST, solution)
    conditions = []
    for condition in result.as_iter():
        items = list(condition.as_iter())
        if not items or items[0].atom is None:
            continue
        opcode = int.from_bytes(items[0].atom, 'big')
        try:
            name = PUZ.get_opcode_name(opcode)
        except ValueError:
            name = f"opcode {opcode}"
        args = [disassemble(arg) for arg in items[1:]]
        meaning = ''
        if opcode == 51 and len(items) >= 3:  # CREATE_COIN: puzzle hash, amount, memos
            meaning = f"{PUZ.puzzle_hash_to_address(items[1].atom)} gets {mojos(items[2].as_int())}"
        conditions.append([name, ' '.join(args), meaning])
    # only text and numbers leave the thread: a Program (a chia_rs LazyNode) can not be used in
    # another thread, the app panics
    return {'coin': out['coin'], 'solution': disassemble(solution), 'solution_hex': out['solution'].removeprefix('0x'),
            'cost': int(cost), 'conditions': conditions}


EXAMPLE_SPEND_MAX_COST = 11_000_000_000  # a block


def mojos(amount: int) -> str:
    return f"{amount:,} {'mojo' if amount == 1 else 'mojos'}"


def puzzle_detail_example(win, screenState: ScreenState, keyboardState, main_scope: Scope, entry,
                          pos: UIgraph.Point, main_win_size: UIgraph.Point):
    """The example spend page: the example coin spent on chain, with its solution, run: the
    conditions it outputs (the delegated puzzle of a standard coin is in the solution)"""
    P_text = screenState.colorPairs["body"]
    P_error = screenState.colorPairs["error"]
    data = main_scope.data
    if not entry.example_height:
        put_text(win, pos + UIgraph.Point(0, 1), "the example was seen in the mempool, it is not spent on chain yet", P_text, bold=True)
        return
    # from the node, in a thread, once (rule 6)
    if 'example_spend' not in data:
        data['example_spend'] = None

        def load():
            try:
                data['example_spend'] = example_spend_job(entry.example_coin_id, entry.example_height)
            except Exception as e:
                logging(debug_logger, "DEBUG", f"PUZZLE DETAIL example spend: {e}")
                data['example_spend'] = {'error': str(e)}
        thread = threading.Thread(target=load, daemon=True)
        thread.start()
        screenState.running_threads.append(thread)
    spend = data['example_spend']
    if spend is None:
        put_text(win, pos + UIgraph.Point(0, 1), "asking the node for the example spend...", P_text, bold=True)
        return
    if 'error' in spend:
        put_text(win, pos + UIgraph.Point(0, 1), f"the example spend was not read: {spend['error']}", P_error, bold=True)
        return

    coin = spend['coin']
    puzzle_hash = coin['puzzle_hash'].removeprefix('0x')
    left = [['coin', f"0x{entry.example_coin_id}"],
            ['parent', coin['parent_coin_info']],
            ['puzzle hash', f"0x{puzzle_hash}"],
            ['address', PUZ.puzzle_hash_to_address(bytes.fromhex(puzzle_hash))]]
    right = [['amount', mojos(coin['amount'])],
             ['spent at', f"height {entry.example_height:,}"],
             ['cost', f"{spend['cost']:,}"],
             ['conditions', f"{len(spend['conditions']):,}"]]
    left.append(['solution', spend['solution']])
    right.append(['solution hex', spend['solution_hex']])
    max_y = main_win_size.y - 2
    used = field_pairs_table(win, screenState, keyboardState, main_scope, "puzzle_example_info", left, right,
                             ['spend', '', '', ''], pos, max_y)
    pos += UIgraph.Point(0, used + 2)

    if pos.y + 7 > max_y:
        return  # no room for the conditions
    rows = [[str(n)] + row for n, row in enumerate(spend['conditions'])] or [['', 'no conditions', '', '']]
    size = UIgraph.Point(main_win_size.x - 2, max(min(len(rows) + 4, max_y - pos.y), 6))
    # args and meaning share what the number and the condition name leave (with the separators)
    free = size.x - 3 - 6 - 26 - 3 - 3 - 3 - 3
    args_width = max(free * 45 // 100, 10)
    meaning_width = max(free - args_width, 10)
    ELEMENTS.create_tab(win, screenState, main_scope, "puzzle_example_conditions", rows,
                        [str(n) for n in range(len(rows))], fresh_table_colors(rows), False,
                        pos, size, keyboardState, scopeAction_nothing, True, False,
                        ['#', 'condition', 'args', 'meaning'],
                        column_widths=[3, 26, args_width, meaning_width], no_cache=True)


def puzzle_detail_edit(win, screenState: ScreenState, keyboardState, main_scope: Scope, entry, c: dict,
                       pos: UIgraph.Point, main_win_size: UIgraph.Point) -> list:
    """The edit page: the name, and the values of the lists of catalog/puzzle_types.json (edited
    there, reloaded by rototiller) as drop-down buttons, in one column. Return the draws of the
    drop-downs: they go last, so an open list is on top of the rest"""
    P_text = screenState.colorPairs["body"]
    layered_puzzle_fingerprint = entry.layered_puzzle_fingerprint
    name = c['name']

    name_length = 40
    scope_name = ELEMENTS.create_prompt(win, screenState, keyboardState, main_scope, 'puzzle_name', pos,
                                        "Name: ", name_length, P_text, True, False,
                                        custom_scope_function=ScopeActions.press_enter)
    pos_button = pos + UIgraph.Point(len("Name: ") + name_length + 3, -1)  # buttons are drawn one line up
    scope_save = ELEMENTS.create_button(win, screenState, main_scope, 'save', pos_button,
                                        custom_scope_function=ScopeActions.press_enter, button_type='execution')
    pos += UIgraph.Point(0, 3)

    # drop-down buttons, one a row; the first value of each list is the one the layers give (no override)
    overrides_now = CONF.KNOWN_LAYERED_PUZZLES.get(layered_puzzle_fingerprint, {})
    derived = PUZ.classify_fingerprint(layered_puzzle_fingerprint, None, overrides=False)
    menus = []
    for field, label in (('family', 'family'), ('puzzle_type', 'puzzle type'), ('custody', 'custody'),
                         ('project', 'project')):
        values = PUZ.field_values(field)
        if overrides_now.get(field) and overrides_now[field] not in values:
            values = values + [overrides_now[field]]  # set by hand, not in the list: kept
        # the menu shows the labels, the id is saved
        values, first = [PUZ.value_label(field, v) for v in values], PUZ.value_label(field, derived[field][0])
        menus.append((field, label, [f"{first or 'none'} {FROM_THE_LAYERS}"] + values))
    value_width = max(len(option) for _, _, options in menus for option in options)
    # 4 rows a button (an empty line between them), 3 on a short terminal (the half blocks of
    # the borders still leave a line between them); a button past the window is not drawn
    max_y = main_win_size.y - 1
    step = 4 if pos.y + 4 * len(menus) - 1 <= max_y else 3
    menu_scopes, menu_draws = {}, []
    for n, (field, label, options) in enumerate(menus):
        point = UIgraph.Point(pos.x, pos.y + step * n)
        if point.y + 3 > max_y:
            break
        draw = lambda only_init, label=label, options=options, point=point: ELEMENTS.create_button_menu(
            win, screenState, main_scope, label, options, point, only_init, ScopeActions.press_enter, value_width)
        menu_scopes[field] = (draw(True), options)
        menu_draws.append(draw)
    if any(scope.selected() or scope is screenState.activeScope for scope, _ in menu_scopes.values()):
        screenState.footer_text += "| lists: catalog/puzzle_types.json "

    if not main_scope.data.get('prompts_filled'):
        main_scope.data['prompts_filled'] = True
        scope_name.data['prompt'] = name or ''
        scope_name.data['cursor'] = len(scope_name.data['prompt'])
    # each list on its saved value when it is made (a button not drawn on a short terminal is
    # made later, when the terminal is taller)
    for field, (scope, options) in menu_scopes.items():
        if not scope.data.get('filled'):
            scope.data['filled'] = True
            now = PUZ.value_label(field, overrides_now.get(field))
            scope.cursor = options.index(now, 1) if now in options[1:] else 0

    # enter on the name, on the button or on a list saves everything
    save = False
    for scope in (scope_name, scope_save, *(scope for scope, _ in menu_scopes.values())):
        if scope.data.get('pressed_enter'):
            scope.data['pressed_enter'] = False
            save = True
    if save:
        new_name = scope_name.data['prompt'].strip()
        # the fields without a button (not drawn) keep their saved value
        overrides = {field: overrides_now.get(field) for field, _, _ in menus}
        overrides.update({field: PUZ.value_id(field, options[scope.cursor]) if scope.cursor else None
                          for field, (scope, options) in menu_scopes.items()})
        try:
            SCAN.CATALOG.set_classification(layered_puzzle_fingerprint, new_name, overrides)
            # a value is saved only when it is not the one the layers give
            set_fields = [f for f, v in overrides.items() if v and v != derived[f][0]]
            screenState.footer_message = (f"saved in layered_puzzles.json: {new_name or '(no name)'}"
                                          + (f" | set: {', '.join(set_fields)}" if set_fields else ''))
        except ValueError as e:
            # a catalog file edited by hand is not valid json, it is not overwritten
            screenState.footer_message = f"not saved, fix the json in resources/puzzles/catalog first: {e}"
    return menu_draws


def puzzle_detail_layers(win, screenState: ScreenState, keyboardState, main_scope: Scope, entry,
                         pos: UIgraph.Point, main_win_size: UIgraph.Point):
    """The layers of the puzzle detail screen, from pos: the uncurried puzzle and the data of
    the selected layer"""
    P_text = screenState.colorPairs["body"]

    ##### layers: the puzzle uncurried
    if 'nodes' not in main_scope.data:
        try:
            puzzle = PyProgram.from_bytes(entry.example_puzzle_reveal)
            main_scope.data['nodes'] = PUZ.unroll_puzzle_to_nodes(puzzle)
        except Exception as e:
            logging(debug_logger, "DEBUG", f"PUZZLE DETAIL unroll error: {e}")
            UTILS.logging_traceback('PUZZLE DETAIL')
            main_scope.data['nodes'] = []
    nodes = main_scope.data['nodes']

    # a table that does not fit is not drawn (a short terminal): its title, its 6 rows and the
    # frame under it; curses can not make a window past the screen
    def fits(y):
        return y + 1 + 6 + 1 <= main_win_size.y - 1
    if not fits(pos.y):
        return

    legend = ['level', 'curried', 'puzzle', 'mod hash', 'curried args']
    rows = []
    keys = []
    for n, node in enumerate(nodes):
        args = ', '.join(fit_text(arg, 30) for arg in node['args'])
        rows.append([node['level'], 'yes' if node['is_curried'] else 'no', node['puzz_name'], node['hash'], args])
        keys.append(str(n))

    space_left = main_win_size.y - pos.y - 1
    tab_size = UIgraph.Point(main_win_size.x - 2, min(len(rows) + 5, max(space_left // 3, 6)))
    tab_scope = ELEMENTS.create_tab(win,
                                    screenState,
                                    main_scope,
                                    "puzzle_layers",
                                    rows,
                                    keys,
                                    fresh_table_colors(rows),
                                    False,
                                    pos,
                                    tab_size,
                                    keyboardState,
                                    scopeAction_nothing,
                                    True,
                                    False,
                                    legend)
    pos += UIgraph.Point(0, tab_size.y + 1)

    ##### selected layer: its data in a tab, select a row and press y to copy a value
    # (ctrl-c can not be used to copy, see the comment on yank in KEYBOARDtiller)
    if not nodes:
        return
    node = nodes[tab_scope.cursor % len(nodes)]
    reveal = bytes(entry.example_puzzle_reveal or b'')
    if 'clvm' not in main_scope.data:
        main_scope.data['clvm'] = PUZ.rs_disassemble(reveal) if reveal else ''

    if 'cat_names' not in main_scope.data:
        main_scope.data['cat_names'] = WDB.retrive_asset_names(CONF.DB_WDB)
    cat_names = main_scope.data['cat_names']

    # the 32 byte args that are not a known puzzle or CAT: look them up on chain, once, in a
    # thread (a coin id, a puzzle hash with coins, a hint). None while it runs, '' if not found
    if 'chain_lookup' not in main_scope.data:
        chain_lookup = {}
        for n_node in nodes:
            for arg_hex in n_node.get('arg_hex', []):
                try:
                    for h in PUZ.unknown_hashes_in_arg(PyProgram.fromhex(arg_hex), cat_names):
                        chain_lookup[h] = None
                except Exception as e:
                    logging(debug_logger, "DEBUG", f"PUZZLE DETAIL arg not read: {e}")
        main_scope.data['chain_lookup'] = chain_lookup

        def lookup_hashes():
            for h in list(chain_lookup):
                try:
                    chain_lookup[h] = PUZ.chain_lookup_hash(h)
                except Exception as e:
                    logging(debug_logger, "DEBUG", f"PUZZLE DETAIL chain lookup of {h} failed: {e}")
                    chain_lookup[h] = ''
        if chain_lookup:
            lookup_thread = threading.Thread(target=lookup_hashes, daemon=True)
            lookup_thread.start()
            screenState.running_threads.append(lookup_thread)
    chain_lookup = main_scope.data['chain_lookup']

    # columns: field, type, meaning, value
    puzzle_hash = node.get('puzzle_hash') or ''
    data_rows = [
        ['path', '', '', node['path'] or ''],
        ['puzzle', '', '', node['puzz_name'] or ''],
        ['mod hash', 'hash 32', node['puzz_name'] or '', node['hash'] or ''],
        # for the STD layer inside a CAT or an NFT, this is the owner's address
        ['puzzle hash', 'hash 32',
         f"address: {PUZ.puzzle_hash_to_address(bytes.fromhex(puzzle_hash))}" if puzzle_hash else '',
         puzzle_hash],
    ]
    for n, arg in enumerate(node['args']):
        arg_type, meaning = '', ''
        if n < len(node.get('arg_hex', [])):
            try:
                arg_type, meaning = PUZ.describe_curried_arg(
                    PyProgram.fromhex(node['arg_hex'][n]), cat_names, chain_lookup)
            except Exception as e:
                logging(debug_logger, "DEBUG", f"PUZZLE DETAIL arg {n} not described: {e}")
        data_rows.append([f"arg {n}", arg_type, meaning, arg])
    data_rows.append(['mod clvm', '', '', node['disassembly'] or ''])
    data_rows.append(['whole puzzle hex', '', '', reveal.hex()])
    data_rows.append(['whole puzzle clvm', '', '', main_scope.data['clvm']])
    data_keys = [str(n) for n in range(len(data_rows))]

    if not fits(pos.y):
        return
    put_text(win, pos, f"level {node['level']}: {node['puzz_name']}", P_text, bold=True)
    pos += UIgraph.Point(0,1)
    space_left = main_win_size.y - pos.y - 1
    data_tab_size = UIgraph.Point(main_win_size.x - 2, min(len(data_rows) + 5, max(space_left // 2, 6)))
    # the value takes the width left (create_tab drops the columns that do not fit, from
    # the rows it gets: it gets a copy, the rows are used again below)
    value_width = max(data_tab_size.x - 102, 10)
    # no frame cache (the chain lookups change rows in the middle): new column sizes when
    # the rows change (another layer, a lookup done) or the screen is resized
    data_tab_name = f"{main_scope.id}_puzzle_layer_data"
    if data_tab_name in screenState.scopes and (screenState.screen_resized or
                                                main_scope.data.get('data_rows_shown') != data_rows):
        screenState.scopes[data_tab_name].data['column_sizes'] = None
    main_scope.data['data_rows_shown'] = data_rows
    data_scope = ELEMENTS.create_tab(win,
                                     screenState,
                                     main_scope,
                                     "puzzle_layer_data",
                                     [list(row) for row in data_rows],
                                     data_keys,
                                     fresh_table_colors(data_rows),
                                     False,
                                     pos,
                                     data_tab_size,
                                     keyboardState,
                                     scopeAction_nothing,
                                     True,
                                     False,
                                     ['field', 'type', 'meaning', 'value'],
                                     column_widths=[18, 14, 50, value_width],
                                     no_cache=True)
    pos += UIgraph.Point(0, data_tab_size.y + 1)

    ##### the whole value of the selected row
    field, arg_type, meaning, value = data_rows[data_scope.cursor % len(data_rows)]
    max_y = main_win_size.y - 1
    put_text(win, pos, f"{field} ({len(value):,} chars):", P_text, bold=True)
    pos += UIgraph.Point(0,1)
    if meaning:
        put_text(win, pos, f"{arg_type} | {meaning}", P_text)
        pos += UIgraph.Point(0,1)
    text_width = max(main_win_size.x - pos.x - 3, 10)
    for i in range(0, len(value), text_width):
        if pos.y >= max_y:
            break
        put_text(win, pos, value[i:i + text_width], P_text)
        pos += UIgraph.Point(0,1)


REORG_VIEWS = ['forks', 'depth', 'by depth']
HEAT_TOP_GAP = 2  # the columns between the tabs and the texts of a heat map on their row


def reorg_tab_text(name: str, forks) -> str:
    count = f" ({len(forks)})" if name in ('forks', 'by depth') else ''
    return f" {name.upper()}{count} "


def reorg_tabs_width(forks) -> int:
    """The columns of the tab titles (create_text_double_space adds a space on each side)"""
    return sum(len(reorg_tab_text(name, forks)) + 2 for name in REORG_VIEWS)
REORG_REFRESH = 30  # sec between two scans of the last blocks
REORG_SCALE = '6h'  # column scale when a heat map opens: a month of forks in ~120 columns
REORG_TABLE_LEGEND = ['time', 'ago', 'fork at height', 'depth', 'orphaned blocks', 'orphaned tip']
REORG_TABLE_WIDTHS = [None, None, None, None, None, 70]

REORG_FORK_RAMP = HEAT.ramp_from_seed((230, 120, 50), 7, (0, 10, 45))
REORG_FORK_STYLE = HEAT.HeatmapStyle(
    REORG_FORK_RAMP,
    zero=(20, 30, 65),
    count_name='forks',
    names=[((20, 30, 65), 'no fork'), (REORG_FORK_RAMP[len(REORG_FORK_RAMP) // 2], '½ busiest'),
           (REORG_FORK_RAMP[-1], 'busiest {max}')])
# depth 1 is the common fork, so the colors are on a fixed scale: 3 blocks and more is deep
REORG_DEPTH_RAMP = HEAT.make_ramp([(70, 130, 200), (240, 170, 40), (235, 75, 45)], 7)
REORG_DEPTH_STYLE = HEAT.HeatmapStyle(
    REORG_DEPTH_RAMP,
    fixed_max=3,
    zero=(20, 30, 65),
    over=(245, 245, 238),
    count_name='deepest depth',
    names=[((20, 30, 65), 'no fork'), (REORG_DEPTH_RAMP[2], 'depth 1'),
           (REORG_DEPTH_RAMP[-1], 'depth 3'), ((245, 245, 238), '4+')])


def human_age_days(seconds: float) -> str:
    """human_age, with days for the ages over one day"""
    if seconds < 86400:
        return human_age(seconds)
    seconds = int(seconds)
    return f"{seconds // 86400}d {seconds % 86400 // 3600:02d}h"


def reorg_table_rows(forks, now: float):
    """Rows and keys of the fork table, the same columns in the screen and in a heat map cell"""
    rows = []
    keys = []
    for f in forks:
        rows.append([
            UTILS.timestamp_to_date(f.timestamp) if f.timestamp else '-',
            human_age_days(now - f.timestamp) if f.timestamp else '-',
            f"{f.fork_height:,}",
            f.depth,
            f.orphaned_blocks,
            '0x' + f.tip_hash.hex(),
        ])
        keys.append(f.tip_hash.hex())
    return rows, keys


def reorg_time_series(main_scope: Scope):
    """The forks as a time series (time, depth), rebuilt after each scan of the node DB"""
    scanner = WDB.REORG_SCANNER
    data = main_scope.data
    key = (scanner.last_scan, len(scanner.forks))
    if data.get('reorg_series_key') != key:
        pairs = [(f.timestamp, f.depth) for f in scanner.forks if f.timestamp is not None]
        # the first scan reads the whole DB, so the series has data from the beginning
        data['reorg_series'] = HEAT.TimeSeries(pairs, start=0)
        data['reorg_series_key'] = key
    return data['reorg_series']


def scopeAction_open_reorg_cell(scope: Scope, screenState: ScreenState, *args):
    """enter on a cell of a reorg heat map: the forks of the cell"""
    t0, t1 = scope.data['cell']
    new_scope = Scope(f"reorg_cell_{int(t0)}_{int(t1)}", screen_reorg_cell, screenState)
    new_scope.parent_scope = scope
    new_scope.data['cell'] = (t0, t1)
    new_scope.exec = None
    screenState.activeScope = new_scope
    return new_scope


def screen_reorgs(stdscr, keyboardState, screenState, fullNodeState: FullNodeState, figlet=False):
    """Forks seen by the node, from the blocks of its DB that are not in the main chain"""

    height = screenState.screen_size.y
    width = screenState.screen_size.x

    active_scope: Scope = screenState.activeScope
    main_scope: Scope = active_scope.main_scope
    screenState.scope_exec_args = [screenState]
    main_scope.update()

    win = createFullSubWin(stdscr, screenState, height, width)
    win.bkgd(' ', curses.color_pair(screenState.colorPairs["body"]))
    main_win_size = UIgraph.Point(win.getmaxyx()[1], win.getmaxyx()[0])

    C_background = screenState.colors["background"]
    P_text = screenState.colorPairs["body"]
    P_error = screenState.colorPairs["error"]
    P_title = screenState.colorPairs["xch"]

    pos = UIgraph.Point(1,1)
    ELEMENTS.create_text_double_space(win, screenState, pos, 'reorgs', P_title, C_background,
                                      3, True, inv_color=False)
    pos += UIgraph.Point(0,3)

    # the first scan reads the whole node DB, the next ones only the last blocks
    scanner = WDB.REORG_SCANNER
    if not scanner.lock.locked() and time.time() - scanner.last_scan > REORG_REFRESH:
        scan_thread = threading.Thread(target=scanner.refresh, daemon=True)
        scan_thread.start()
        scan_thread.setName("scanning reorgs")
        with screenState.lock:
            screenState.running_threads.append(scan_thread)

    if scanner.scanned_height is None:
        if scanner.error:
            put_text(win, pos, scanner.error, P_error, bold=True)
        else:
            put_text(win, pos, "scanning the whole node DB for blocks out of the main chain...", P_text, bold=True)
        return

    forks = list(scanner.forks)
    deepest = max((f.depth for f in forks), default=0)
    text = (f"{len(scanner.orphans)} blocks out of the main chain in {len(forks)} forks | "
            f"deepest: {deepest} blocks | scanned up to height {scanner.scanned_height:,}")
    if scanner.lock.locked():
        text += " | scanning..."
    put_text(win, pos, text, P_text)
    pos += UIgraph.Point(0,1)
    if scanner.error:
        put_text(win, pos, scanner.error, P_error)
    else:
        put_text(win, pos, "a fork of depth 1 can also be a block that lost the race and was never the peak", P_text)
    pos += UIgraph.Point(0,2)

    view = REORG_VIEWS[main_scope.cursor_x % len(REORG_VIEWS)]
    pos_tab_title = pos
    pos += UIgraph.Point(0, 2)
    if screenState.activeScope is main_scope:
        screenState.footer_text += "| switch view=←→ "

    now = datetime.now().timestamp()
    tab_name = f"reorgs_{view.replace(' ', '_')}"
    if view in ('forks', 'depth'):
        # the half line under the tabs goes on to the right end of the heat map, which starts right under it
        put_text(win, pos, '▀' * (main_win_size.x - 2), screenState.colorPairs["tab_dark_bg"])
        pos += UIgraph.Point(0, 1)
        views = main_scope.data.setdefault('views', {})
        if view not in views:
            views[view] = HEAT.HeatmapView(HEAT.SCALE_INDEX[REORG_SCALE])
        style = REORG_FORK_STYLE if view == 'forks' else REORG_DEPTH_STYLE
        value_method = 'count' if view == 'forks' else 'max_value'
        ELEMENTS.create_time_heatmap(
            win, screenState, keyboardState, main_scope, tab_name, pos,
            UIgraph.Point(main_win_size.x - 2, main_win_size.y - pos.y - 2),
            reorg_time_series(main_scope), views[view], style, scopeAction_open_reorg_cell,
            value_method=value_method, top_left=pos.x + reorg_tabs_width(forks) + HEAT_TOP_GAP)
    else:
        forks.sort(key=lambda f: (f.depth, f.tip_height), reverse=True)
        rows, keys = reorg_table_rows(forks, now)
        if rows:
            tab_size = UIgraph.Point(main_win_size.x - 2, max(main_win_size.y - pos.y - 2, 5))
            ELEMENTS.create_tab(win,
                                screenState,
                                main_scope,
                                tab_name,
                                rows,
                                keys,
                                fresh_table_colors(rows),
                                False,
                                pos,
                                tab_size,
                                keyboardState,
                                scopeAction_nothing,
                                True,
                                False,
                                list(REORG_TABLE_LEGEND),
                                column_widths=list(REORG_TABLE_WIDTHS))
        else:
            put_text(win, pos + UIgraph.Point(0, 1), "no fork in the node DB", P_text)

    P_tab_title = screenState.colorPairs["title"]
    P_tab_soft = screenState.colorPairs["tab_soft"]
    pos = pos_tab_title
    for name in REORG_VIEWS:
        text = reorg_tab_text(name, forks)
        selected_tab = name == view
        P_used = P_title if selected_tab else P_tab_title
        ELEMENTS.create_text_double_space(win, screenState, pos, text, P_used, C_background, 3, True)
        underline_pos = pos + UIgraph.Point(0, 2)
        if selected_tab:
            ELEMENTS.create_text(win, underline_pos, u'▀' * (len(text) + 2), P_tab_soft, True)
        else:
            ELEMENTS.create_text(win, underline_pos, ' ' * (len(text) + 2), P_used, True)
        pos += UIgraph.Point(len(text) + 2, 0)


def screen_reorg_cell(stdscr, keyboardState, screenState, fullNodeState: FullNodeState, figlet=False):
    """The forks of a heat map cell, from the blocks of the node DB that are not in the main chain"""

    height = screenState.screen_size.y
    width = screenState.screen_size.x

    active_scope: Scope = screenState.activeScope
    main_scope: Scope = active_scope.main_scope
    screenState.scope_exec_args = [screenState]
    main_scope.update()

    win = createFullSubWin(stdscr, screenState, height, width)
    win.bkgd(' ', curses.color_pair(screenState.colorPairs["body"]))
    main_win_size = UIgraph.Point(win.getmaxyx()[1], win.getmaxyx()[0])

    C_background = screenState.colors["background"]
    P_text = screenState.colorPairs["body"]
    P_title = screenState.colorPairs["xch"]

    pos = UIgraph.Point(1, 1)
    ELEMENTS.create_text_double_space(win, screenState, pos, 'reorgs in a cell', P_title, C_background,
                                      3, True, inv_color=False)
    pos += UIgraph.Point(0, 3)

    t0, t1 = main_scope.data['cell']
    scanner = WDB.REORG_SCANNER
    forks = [f for f in scanner.forks if f.timestamp is not None and t0 <= f.timestamp < t1]
    forks.sort(key=lambda f: f.timestamp)
    deepest = max((f.depth for f in forks), default=0)
    text = (f"{ELEMENTS.heatmap_time_text(t0, t1 - t0)} → {ELEMENTS.heatmap_time_text(t1, t1 - t0)}"
            f" | {len(forks)} forks | deepest depth: {deepest}")
    put_text(win, pos, text, P_text)
    pos += UIgraph.Point(0, 1)
    missing = sum(1 for f in scanner.forks if f.timestamp is None)
    if missing:
        put_text(win, pos, f"{missing} forks have no block time and are only in the by depth table", P_text)
        pos += UIgraph.Point(0, 1)
    pos += UIgraph.Point(0, 1)

    now = datetime.now().timestamp()
    rows, keys = reorg_table_rows(forks, now)
    tab_name = 'reorg_cell_forks'
    tab_scope = list_tab_scope(screenState, main_scope, tab_name, scopeAction_nothing)
    if rows:
        ELEMENTS.create_tab(win,
                            screenState,
                            main_scope,
                            tab_name,
                            rows,
                            keys,
                            fresh_table_colors(rows),
                            False,
                            pos,
                            UIgraph.Point(main_win_size.x - 2, max(main_win_size.y - pos.y - 2, 5)),
                            keyboardState,
                            scopeAction_nothing,
                            True,
                            False,
                            list(REORG_TABLE_LEGEND),
                            column_widths=list(REORG_TABLE_WIDTHS),
                            prepped_scope=tab_scope)
    else:
        put_text(win, pos + UIgraph.Point(0, 1), "no fork in this cell", P_text)


# the chia log: debug.log and its rotated files (debug.log.1 is the newest of them)
CHIA_LOG = CHIALOG.CHIA_LOG
CHIA_LOG_PATHS = CHIALOG.CHIA_LOG_PATHS
HEATMAP_REFRESH = 5  # seconds between two reads of the new log lines
LOG_LINES_MAX = 5000  # most log lines shown for each filter of a selection

# the harvester checks its plots once for each signage point, every 9.375 s; the colors are the
# ones of chiaharvestgraph: red none, orange too few, yellow as expected, white more
HARVEST_STYLE = HEAT.HeatmapStyle(
    HEAT.make_ramp([(224, 50, 44), (240, 140, 26), (242, 211, 60)], 7),
    expected_rate=1 / 9.375, over=(245, 245, 238))
COUNT_RAMP = HEAT.ramp_from_seed((80, 150, 210), 7, (0, 10, 45))


def count_style(count_name: str):
    """A heat map style that counts lines, named count_name (e.g. 'no warnings' on the legend)"""
    return HEAT.HeatmapStyle(COUNT_RAMP, zero=(20, 30, 65), count_name=count_name)

# (tab name, regex of the lines that are events, style, column scale when the tab opens)
LOG_HEATMAP_FILTERS = [
    ('harvester', r'eligible for farming', HARVEST_STYLE, HEAT.SCALE_INDEX['15m']),
    ('errors', r': ERROR ', count_style('errors'), HEAT.SCALE_INDEX['24h']),
    ('warnings', r': WARNING ', count_style('warnings'), HEAT.SCALE_INDEX['24h']),
    ('all lines', None, count_style('lines'), HEAT.SCALE_INDEX['6h']),
]
LOG_HEATMAP_SOURCES = {}  # tab name -> HEAT.LogFileSource, kept while the app runs


def heatmap_source_job(screenState: ScreenState, source: HEAT.LogFileSource):
    """Load the source, or read its new lines, in a thread; one job at a time"""
    if source.lock.locked():
        return
    if source.loaded and time.time() - source.last_refresh < HEATMAP_REFRESH:
        return
    job = source.refresh if source.loaded else source.load
    source.last_refresh = time.time()  # do not start it again in the next frames
    thread = threading.Thread(target=job, daemon=True)
    thread.start()
    thread.setName(f"reading {source.name} log")
    if not source.loaded:
        with screenState.lock:
            screenState.running_threads.append(thread)


def all_lines_source():
    """The source of every log line (the filter without a regex), for the lines of a selection"""
    name = next(name for name, regex, *_ in LOG_HEATMAP_FILTERS if regex is None)
    if name not in LOG_HEATMAP_SOURCES:
        LOG_HEATMAP_SOURCES[name] = HEAT.LogFileSource(name, CHIA_LOG_PATHS, None)
    return LOG_HEATMAP_SOURCES[name]


def scopeAction_open_heatmap_cell(scope: Scope, screenState: ScreenState, *args):
    """enter on the log heat map: the log lines of the selected time, on the tab of all the lines"""
    t0, t1 = scope.data['cell']
    new_scope = Scope(f"log_lines_{t0}_{t1}", screen_log_lines, screenState)
    new_scope.parent_scope = scope
    new_scope.data['cell'] = (t0, t1)
    new_scope.cursor_x = next(i for i, (_, regex, *_) in enumerate(LOG_HEATMAP_FILTERS) if regex is None)
    new_scope.exec = None
    screenState.activeScope = new_scope
    return new_scope


def screen_log_heatmap(stdscr, keyboardState, screenState, fullNodeState: FullNodeState, figlet=False):
    """The lines of the chia log as a time heat map (ELEMENTS.create_time_heatmap), one tab for
    each kind of line (LOG_HEATMAP_FILTERS). Enter on a cell shows its lines"""

    height = screenState.screen_size.y
    width = screenState.screen_size.x

    active_scope: Scope = screenState.activeScope
    main_scope: Scope = active_scope.main_scope
    screenState.scope_exec_args = [screenState]
    main_scope.update()
    data = main_scope.data

    win = createFullSubWin(stdscr, screenState, height, width)
    win.bkgd(' ', curses.color_pair(screenState.colorPairs["body"]))
    main_win_size = UIgraph.Point(win.getmaxyx()[1], win.getmaxyx()[0])

    C_background = screenState.colors["background"]
    P_text = screenState.colorPairs["body"]
    P_error = screenState.colorPairs["error"]
    P_title = screenState.colorPairs["xch"]

    pos = UIgraph.Point(1, 1)
    ELEMENTS.create_text_double_space(win, screenState, pos, 'log heat map', P_title, C_background,
                                      3, True, inv_color=False)
    pos += UIgraph.Point(0, 3)

    # ←→ on the screen switch the tab, each tab keeps its source and its view
    tab_index = main_scope.cursor_x % len(LOG_HEATMAP_FILTERS)
    tab_name, regex, style, scale_idx = LOG_HEATMAP_FILTERS[tab_index]
    if tab_name not in LOG_HEATMAP_SOURCES:
        LOG_HEATMAP_SOURCES[tab_name] = HEAT.LogFileSource(tab_name, CHIA_LOG_PATHS, regex)
    source = LOG_HEATMAP_SOURCES[tab_name]
    views = data.setdefault('views', {})
    if tab_name not in views:
        views[tab_name] = HEAT.HeatmapView(scale_idx)
    view = views[tab_name]
    heatmap_source_job(screenState, source)

    series = source.series
    files = len(source.files)
    text = f"{CHIA_LOG}"
    if files > 1:
        text += f" and {files - 1} rotated files"
    if source.loaded:
        text += f" | {len(series):,} lines"
        if series.start:
            text += f" since {UTILS.timestamp_to_date(series.start)}"
    if source.status != 'loaded':
        text += f" | {source.status}..."
    put_text(win, pos, text, P_text)
    pos += UIgraph.Point(0, 1)
    if source.error:
        put_text(win, pos, source.error, P_error, bold=True)
    elif regex:
        put_text(win, pos, f"lines with: {regex}", P_text)
    pos += UIgraph.Point(0, 1)
    archive = CHIALOG.ArchiveState
    if archive.error:
        put_text(win, pos, f"archive: {archive.error}", P_error, bold=True)
    else:
        text = f"archive: {archive.files} files, {UTILS.human_bytes(archive.size)} in {CHIALOG.ARCHIVE_DIR}"
        if archive.oldest:
            text += f", since {archive.oldest[6:16]}"
        put_text(win, pos, text, P_text)
    pos += UIgraph.Point(0, 2)

    pos_tab_title = pos
    pos += UIgraph.Point(0, 2)
    if screenState.activeScope is main_scope:
        screenState.footer_text += "| switch log lines=←→ "

    # the half line under the tabs goes on to the right end of the graph, which starts right under it
    put_text(win, pos, '▀' * (main_win_size.x - 2), screenState.colorPairs["tab_dark_bg"])
    pos += UIgraph.Point(0, 1)
    if source.loaded:
        graph_scope, used = ELEMENTS.create_time_heatmap(
            win, screenState, keyboardState, main_scope, f"log_heatmap_{tab_name}", pos,
            UIgraph.Point(main_win_size.x - 2, main_win_size.y - pos.y - 2),
            series, view, style, scopeAction_open_heatmap_cell,
            top_left=pos.x + sum(len(f" {name.upper()} ") + 2 for name, *_ in LOG_HEATMAP_FILTERS) + HEAT_TOP_GAP)
    elif not source.error:
        put_text(win, pos + UIgraph.Point(0, 1), "reading the log...", P_text, bold=True)

    P_tab_title = screenState.colorPairs["title"]
    P_tab_soft = screenState.colorPairs["tab_soft"]
    pos = pos_tab_title
    for name, *_ in LOG_HEATMAP_FILTERS:
        text = f" {name.upper()} "
        selected = name == tab_name
        P_used = P_title if selected else P_tab_title
        ELEMENTS.create_text_double_space(win, screenState, pos, text, P_used, C_background, 3, True)
        underline_pos = pos + UIgraph.Point(0, 2)
        if selected:
            ELEMENTS.create_text(win, underline_pos, u'▀' * (len(text) + 2), P_tab_soft, True)
        else:
            ELEMENTS.create_text(win, underline_pos, ' ' * (len(text) + 2), P_used, True)
        pos += UIgraph.Point(len(text) + 2, 0)


def screen_log_lines(stdscr, keyboardState, screenState, fullNodeState: FullNodeState, figlet=False):
    """The chia log lines of a time selected on the log heat map: a tab for each filter of
    LOG_HEATMAP_FILTERS (all lines, errors, warnings, ...), and a button that copies the lines
    of the tab"""

    height = screenState.screen_size.y
    width = screenState.screen_size.x

    active_scope: Scope = screenState.activeScope
    main_scope: Scope = active_scope.main_scope
    screenState.scope_exec_args = [screenState]
    main_scope.update()
    data = main_scope.data
    t0, t1 = data['cell']

    win = createFullSubWin(stdscr, screenState, height, width)
    win.bkgd(' ', curses.color_pair(screenState.colorPairs["body"]))
    main_win_size = UIgraph.Point(win.getmaxyx()[1], win.getmaxyx()[0])

    C_background = screenState.colors["background"]
    P_text = screenState.colorPairs["body"]
    P_error = screenState.colorPairs["error"]
    P_title = screenState.colorPairs["xch"]

    pos = UIgraph.Point(1, 1)
    ELEMENTS.create_text_double_space(win, screenState, pos, 'log lines', P_title, C_background,
                                      3, True, inv_color=False)
    pos += UIgraph.Point(0, 3)
    step = t1 - t0
    put_text(win, pos, f"{ELEMENTS.heatmap_time_text(t0, step)} → {ELEMENTS.heatmap_time_text(t1, step)}", P_text)
    pos += UIgraph.Point(0, 1)

    # read the lines once, in a thread: the files of all the lines, filtered in one pass
    if 'loading' not in data:
        data['loading'] = True

        def load():
            try:
                source = all_lines_source()
                if not source.loaded:
                    source.load()
                if source.error:
                    raise RuntimeError(source.error)
                filters = [(name, regex) for name, regex, *_ in LOG_HEATMAP_FILTERS]
                data['lines'] = source.lines_between(t0, t1, filters, LOG_LINES_MAX)
            except Exception as e:
                UTILS.logging_traceback("LOG LINES")
                data['error'] = f"reading the log: {e}"
            finally:
                data['loading'] = False

        thread = threading.Thread(target=load, daemon=True)
        thread.start()
        thread.setName("reading log lines")
        with screenState.lock:
            screenState.running_threads.append(thread)

    if data.get('error'):
        put_text(win, pos, data['error'], P_error, bold=True)
        return
    if data['loading']:
        put_text(win, pos, "reading the log lines...", P_text, bold=True)
        return

    names = [name for name, *_ in LOG_HEATMAP_FILTERS]
    tab_name = names[main_scope.cursor_x % len(names)]
    rows, total = data['lines'][tab_name]
    text = f"{total:,} lines" if tab_name == 'all lines' else f"{total:,} lines in {tab_name}"
    if total > len(rows):
        text += f", the first {len(rows):,} are shown"
    put_text(win, pos, text, P_text)
    pos += UIgraph.Point(0, 2)

    # copy the lines of the tab, in a thread (the clipboard tool can be slow)
    if data.get('copy_job'):
        put_text(win, pos + UIgraph.Point(0, 1), "copying...", P_text, bold=True)
    else:
        copy_button = ELEMENTS.create_button(win, screenState, main_scope, 'copy', pos,
                                             custom_scope_function=ScopeActions.press_enter,
                                             button_type='execution')
        if copy_button.data.get('pressed_enter'):
            copy_button.data['pressed_enter'] = False
            data['copy_job'] = True
            lines = [line for _, _, line in rows]

            def copy():
                try:
                    if PLAT.write_clipboard('\n'.join(lines)):
                        data['copy_message'] = f"{len(lines):,} lines copied ({tab_name})"
                    else:
                        data['copy_message'] = "copy failed: no clipboard tool (wl-copy, xclip or xsel)"
                except Exception as e:
                    data['copy_message'] = f"copy failed: {e}"
                finally:
                    data['copy_job'] = False

            thread = threading.Thread(target=copy, daemon=True)
            thread.start()
            thread.setName("copying log lines")
            with screenState.lock:
                screenState.running_threads.append(thread)
    if data.get('copy_message'):
        put_text(win, pos + UIgraph.Point(14, 1), data['copy_message'], P_text)
    pos += UIgraph.Point(0, 3)

    pos_tab_title = pos
    pos += UIgraph.Point(0, 2)
    if screenState.activeScope is main_scope:
        screenState.footer_text += "| switch filter=←→ "

    tab_size = UIgraph.Point(main_win_size.x - 2, max(main_win_size.y - pos.y - 2, 5))
    if rows:
        ELEMENTS.create_tab(win,
                            screenState,
                            main_scope,
                            f"log_lines_{tab_name.replace(' ', '_')}",
                            [list(row) for row in rows],
                            None,
                            None,
                            False,
                            pos,
                            tab_size,
                            keyboardState,
                            scopeAction_nothing,
                            True,
                            False,
                            ['file', 'line', 'text'],
                            [None, None, max(main_win_size.x - 30, 20)])
    else:
        put_text(win, pos + UIgraph.Point(0, 1), "no line", P_text)

    P_tab_title = screenState.colorPairs["title"]
    P_tab_soft = screenState.colorPairs["tab_soft"]
    pos = pos_tab_title
    for name in names:
        text = f" {name.upper()} ({data['lines'][name][1]:,}) "
        selected = name == tab_name
        P_used = P_title if selected else P_tab_title
        ELEMENTS.create_text_double_space(win, screenState, pos, text, P_used, C_background, 3, True)
        underline_pos = pos + UIgraph.Point(0, 2)
        if selected:
            ELEMENTS.create_text(win, underline_pos, u'▀' * (len(text) + 2), P_tab_soft, True)
        else:
            ELEMENTS.create_text(win, underline_pos, ' ' * (len(text) + 2), P_used, True)
        pos += UIgraph.Point(len(text) + 2, 0)
