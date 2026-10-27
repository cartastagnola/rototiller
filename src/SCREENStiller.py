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
from src.TYPEStiller import (
    FingerState, CoinPriceData, ScreenState, FullNodeState, Scope, KeyboardState,
    FullNodeState, ScreenState, ScopeActions)

from src.CONFtiller import (
    debug_logger, logging, DEBUGGING, DB_BLOCKCHAIN_RO, DB_WDB, DB_SB, DB_BLOCKCHAIN_RO, SQL_TIMEOUT, XCH_FAKETAIL,
    BTC_FAKETAIL, XCH_CUR, USD_CUR, XCH_MOJO, CAT_MOJO, full_node_port, full_node_rpc_port,
    FIGLET, DOOM_FONT, FUTURE_FONT, BLOCK_MAX_COST, SMALL_FONT, FUTURE_FONT)
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
                    align_h=0, align_v=0, prefix=False):

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
        for i, m in enumerate(menu):
            menu[i] = f"{i} - {menu[i]}"

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
    n_rows = height // FUTURE_FONT.height - 2
    bbox = UIgraph.Point(0,0)

    # using figlet or not
    if width > xDimMenu_fig * 2 and FIGLET and n_rows > 3 and width > 100:
        bbox.x = xDimMenu_fig
        figlet = True
    else:
        n_rows = height - 2
        bbox.x = xDimMenu

    margin = UIgraph.Point(6,3)
    n_menu, n_selection = ELEMENTS.normalize_menu(menu, scope, n_rows)

    # recalculate bbox on Y
    if figlet:
        bbox.y = len(n_menu) * FUTURE_FONT.height
    else:
        bbox.y = len(n_menu)

    base_point = ELEMENTS.align_bounding_box(stdscr, bbox, margin, align_h, align_v)
    point = [base_point.y, base_point.x]

    menu_select_figlet(stdscr, n_menu, n_selection, point, color_pairs, color_pairs_sel,
                       figlet=figlet)


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

    # new menu
    menu_select_def(test_win, activeScope, list(activeScope.sub_scopes.keys()),
                    screenState.colorPairs['body'], screenState.colorPairs["body_sel"],
                    align_h=1, align_v=1, prefix=True)


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
            layered_puzzle_type, layered_puzzle_name = PUZ.compare_unrolled_puzzle_to_known_layered_puzzles(puz_hashes)
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
                                outbound: bool = True, uncurry_puzzle: bool = True, update_cache: bool = False):
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
                layered_puzzle_type, layered_puzzle_name = PUZ.compare_unrolled_puzzle_to_known_layered_puzzles(puz_hashes)
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


def screen_address_viewer(stdscr, keyboardState: KeyboardState, screenState: ScreenState, fullNodeState: FullNodeState, figlet=False):

    height = screenState.screen_size.y
    width = screenState.screen_size.x

    active_scope: Scope = screenState.activeScope
    main_scope: Scope = active_scope.main_scope
    screenState.scope_exec_args = [screenState]
    #main_scope.update_2d()
    main_scope.update()


    # tab: inbound, outbound, puzzle
    tab_selected = main_scope.cursor_x % 3

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

    # footer
    screenState.footer_text += "| save_to_watchlist=w "
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
    pos = UIgraph.Point(1,0)
    pos_orig = pos
    max_y = main_win_size.y - pos.y - 3

    address = encode_puzzle_hash(address_loaders.puzzle_hash, CONF.ADD_PREFIX)
    text = f" address: {address} "

    ELEMENTS.create_text_double_space(add_viewer, screenState, pos, text, P_title_selected, C_background,
                                      3, True, inv_color=False)

    path = CONF.USER_ADDX_WATCHLIST
    if path.exists():
        addx_list = WDB.load_csv_no_comments(path)
        only_addx = [[] for _ in range(3)]
        for entry in addx_list:
            if len(entry) > 1:
                #logging(debug_logger, "DEBUG", f"entry {entry[0]} add {str(address_loaders.puzzle_hash)} and xch {address}")
                if str(address_loaders.puzzle_hash) == entry[0] or address == entry[0]:
                    pos_tr = pos + UIgraph.Point(len(text) + 4, 0)
                    name = entry[1]

                    lenght_name = len(name) + 4
                    if pos.x + len(text) + 3 + lenght_name < main_win_size.x:
                        pos_tr = pos + UIgraph.Point(len(text) + 4, 0)
                    else:
                        pos_tr = pos + UIgraph.Point(0, pos.y + 3)
                        pos = pos + UIgraph.Point(0, pos.y + 3)
                    ELEMENTS.create_text_double_space(add_viewer, screenState, pos_tr, name, P_title_selected, C_background,
                                                      3, True, inv_color=False)

    pos += UIgraph.Point(0,4)

    data_table_legend = ["puzzle hash", "total balance"]
    data_table_legend = ["total balance", "unspent", "coins", "unspent hinted", "hinted", "puzzle hash", "address"]  # hinted, unspent hinted,
    # total coin | total unspent coin
    data_table = [[f"{address_loaders.balance / XCH_MOJO:.4f}",
                   address_loaders.unspent_coin_count,
                   address_loaders.total_coin_count,
                   address_loaders.unspent_hinted_coin_count,
                   address_loaders.total_hinted_coin_count,
                   address_loaders.puzzle_hash,
                   address]]

    tab_size = UIgraph.Point(150, 7)


    column_widths = [None, None, None, None, None, 15, 15]
    #formatters = [None, None, None, UTILS.human_amount, None, None, None]
    ELEMENTS.create_tab_large(add_viewer,        # scr
                              screenState,       # screen_state
                              main_scope,        # parent_scope
                              "add_data",        # tab_name
                              data_table,        # list data
                              None,              # data_keys
                              None,              # data_colors
                              False,             # transpose
                              pos,               # pos
                              tab_size,          # size
                              keyboardState,     # keyboardState
                              ScopeActions.exit_scope,              # activation func
                              2,                 # row_height
                              False,             # active
                              False,             # multiple selection
                              data_table_legend, # data_legend
                              column_widths=column_widths)

    pos += UIgraph.Point(0, tab_size.y)
    pos_tab_title = pos
    pos += UIgraph.Point(0,2)
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

    # run copy/paste action or other pending stuffs
    if len(screenState.pending_action) > 0:
        for i, fn in screenState.pending_action:
            fn()
        screenState.pending_action = []


    def blend_selector(selected: bool, pos: UIgraph.Point):
        pos_t = pos + UIgraph.Point(0,2)
        if selected:
            ELEMENTS.create_text(add_viewer, pos_t, u'\u2580' * (len(text) + 2), P_tab_soft, True)
        else:
            ELEMENTS.create_text(add_viewer, pos_t, ' ' * (len(text) + 2), P_used, True)


    pos = pos_tab_title
    with address_loaders.lock:
        layered_puzzle_type = address_loaders.layered_puzzle_type

    title_list = [" INBOUND coins ", " OUTBOUND coins ", f" PUZZLE [{layered_puzzle_type}]"]
    for n, text in enumerate(title_list):
        P_used, blend = (P_title_selected, True) if tab_selected == n else (P_title, False)
        ELEMENTS.create_text_double_space(add_viewer, screenState, pos, text, P_used, C_background, 3, True)
        blend_selector(blend, pos)
        pos += UIgraph.Point(len(text) + 2,0)

    # cache build progress, next to the tabs
    with address_loaders.lock:
        cache_progress = address_loaders.cache_progress
    if cache_progress is not None:
        done, total = cache_progress
        text = "building cache..." if total is None else f"building cache... {done:,} / {total:,} coins"
        ELEMENTS.create_text(add_viewer, pos + UIgraph.Point(2, 1), text, P_text, True)

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

    # --- Type verification (CAT / NFT / XCH) ---
    try:
        coin_record_roto = TYPES.CoinRecordRoto(coin_record[:10])
        type_result = WDB.FetchMaker.verify_coin_type(coin_record_roto, hint=raw_hint if UTILS.is_bytes32(raw_hint) else None)
        labels.append("Verified Type")
        values.append(type_result.get('type', 'UNKNOWN'))
        labels.append("Verified")
        values.append(str(type_result.get('verified', False)))
        labels.append("Type Detail")
        values.append(str(type_result.get('detail', {})))
    except Exception as e:
        logging(debug_logger, "DEBUG", f"verify_coin_type failed: {e}")
        traceback.print_exc()
        labels.append("Verified Type")
        values.append("ERROR")
        labels.append("Verified")
        values.append("False")
        labels.append("Type Detail")
        values.append(str(e))

    if coin_memo is not None:
        labels.append("RPC Spent debug")
        values.append(str(coin_memo))

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


def build_mempool_blocks(fullNodeState: FullNodeState):
    """Split the mempool in blocks, with the items sorted by fee per cost"""
    ## TODO: move the sorting of the mempool outside the UI loop
    mempool_items = fullNodeState.deepcopy_mempool()

    sorted_mempool = sorted(list(mempool_items.values()), key=lambda item: item.fee_per_cost)  # sorted by fee per cost

    # create mempool block
    mempool_blocks = [WDB.MempoolBlock()]
    for item in sorted_mempool:
        current_block: WDB.MempoolBlock = mempool_blocks[-1]
        if current_block.total_cost + item.cost <= BLOCK_MAX_COST:
            current_block.add_item(item)
        else:
            mempool_blocks.append(WDB.MempoolBlock())
    return mempool_blocks


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

    if 'lapper' not in main_scope.data:
        main_scope.data["lapper"] = UTILS.Timer('block_band')
    lapper = main_scope.data["lapper"]
    lapper.start()
    # load blockchain database
    ## TODO: move it on startup

    full_node_meta: FullNodeMeta = fullNodeState.deepcopy_meta()
    #print("size: ", deep_getsizeof(full_node_meta))
    #print("size2: ", asizeof.asizeof(full_node_meta))

    height_last_block = full_node_meta.peak_height

    mempool_blocks = build_mempool_blocks(fullNodeState)

    lapper.clocking('meme')
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

    def to_int(text: str):
        try:
            return int(text)
        except ValueError:
            return None

    ### block band
    lapper.clocking('block loader')
    if blocks_loader is not None:

        block_band_scope = ELEMENTS.create_block_band(stdscr, keyboardState, screenState, main_scope,
                                                      "block_band", pos, block_band_size, mempool_blocks,
                                                      blocks_loader, height_last_block, synced)

        go_to_block(scope_go_to, main_scope, block_band_scope, blocks_loader, height_last_block, screenState)


    pos += UIgraph.Point(0, block_band_size.y + 0)

    lapper.clocking('block band')

    # show data

    if block_band_scope.data['on_peak']:

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
            node_data.addstr(row, col,)
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
        max_y = main_win_size.y - pos.y - 3
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

        # last 10 block
        count = 0
        last_10_blocks = [[],[],[]]
        print(peak_height)
        print("peak")
        peak_height = int(peak_height)
        try:
            while count < 10:
                h = peak_height - count
                curr_block: WDB.BlockState = blocks_loader.get_item_by_idx(h)
                a = curr_block.header_hash
                last_10_blocks[0].append(h)
                last_10_blocks[1].append(curr_block.header_hash)
                if curr_block.is_transaction_block:
                    last_10_blocks[2].append("trx")
                else:
                    last_10_blocks[2].append("")
                count += 1
        except Exception as e:
            print("except last blocks")
            print(e)
            print("height: ", h)
            global DEBUG_OBJ
            DEBUG_OBJ.text += (f"HASHHHH: {count} and {h} exc: {e}")

            none_list = [None] * 10
            #last_10_blocks = [none_list, none_list, none_list]
            while count < 10:
                last_10_blocks[0].append(None)
                last_10_blocks[1].append(None)
                last_10_blocks[2].append(None)
                count += 1

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

        try:
            if main_scope.cursor_x == -1:
                blocks_loader.update_offset(0)
                zero_block: WDB.BlockState = blocks_loader.get_current_item()
                b_block: WDB.BlockState = zero_block.operational_error()
                block_data = b_block.b_block_to_2d_list()
                block_legend = ['property', 'value']
            else:
                current_block: WDB.BlockState = blocks_loader.get_current_item()
                block_data = current_block.block_state_to_2d_list()
                block_legend = ['property', 'value']

            max_y = main_win_size.y - pos.y - 3
            tab_size = UIgraph.Point(80, max_y)

        except:
            print("bug while syncing, current block is None")
            print(f"current block: {current_block}")
            print(f"current offset: {blocks_loader.current_offset}")
            block_states, first_idx = blocks_loader.get_items_hot_chunks()
            for n, i in enumerate(block_states):
                print(n, ' - ', i)
            print("it happens if the peak is updated but the block_loader is still not")
            print("we should show no data untill it is available")
            print("PEND")
            print(main_scope.cursor_x)



        block_scope = ELEMENTS.create_tab(node_data,
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
        # this should be an option of the create tab
        block_scope.exec_esc = ScopeActions.select_prev_scope


    # run copy/paste action or other pending stuffs
    if len(screenState.pending_action) > 0:
        for i, fn in screenState.pending_action:
            fn()
        screenState.pending_action = []


    lapper.clocking('block data')
    lapper.end()
    print(lapper)


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
        # make a func to call only one tx
        tx_cache = {}
        mempool_items = fullNodeState.deepcopy_mempool()
        if spend_bundle_hash in mempool_items:
            tx_cache["tx"] = mempool_items[spend_bundle_hash]
        else:
            mempool_archive = fullNodeState.deepcopy_mempool_archive()
            if spend_bundle_hash in mempool_archive:
                tx_cache["tx"] = mempool_archive[spend_bundle_hash]
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
    P_watch = screenState.colorPairs['error']
    pos = UIgraph.Point(2,2)
    ELEMENTS.create_text(tx_win, pos, str(tx.spend_bundle_hash) + str(tx.additions) + str(tx.addition_amount), P_text, bold=False)

    ###################### WATCH LATER FLAG ################
    if main_scope.data['watch_later']:
        pos = UIgraph.Point(22,2)
        ELEMENTS.create_text(tx_win, pos, "WATCH LATER", P_watch, bold=True)
    else:
        pos = UIgraph.Point(22,2)
        ELEMENTS.create_text(tx_win, pos, "WATCH NOW", P_text, bold=True)
    pos = UIgraph.Point(2,2)
    ########################################################


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

            # unroll puzzle
            c_puzzle_names, _ = PUZ.unroll_puzzle_to_names(c_puzzle)


            pos += UIgraph.Point(0, tab_size.y + 1)
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
    pos += UIgraph.Point(0,3)

    scanner = SCAN.MEMPOOL_SCANNER
    now = time.time()
    # the scanner drops validated txs only at its next scan, hide them here on time
    txs = [tx for tx in scanner.snapshot()
           if tx.validated_at is None or now - tx.validated_at <= CONF.MEMPOOL_VALIDATED_TX_DELAY]
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

    legend = ['tx id', 'type', 'cost', 'fee [XCH]', 'fee/cost', 'coins in', 'coins out', 'age']
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
        rows.append([
            f"0x{tx.tx_id[:16]}...",
            SCAN.tx_type(SCAN.CATALOG, tx.puzzle_keys),
            f"{tx.cost:,}",
            f"{tx.fee / XCH_MOJO:.6f}",
            f"{tx.fee_per_cost:.2f}",
            tx.coins_in,
            tx.coins_out,
            human_age(now - tx.added_at),
        ])
        keys.append(tx.tx_id)

    tab_name = "mempool_txs"
    tab_scope = list_tab_scope(screenState, main_scope, tab_name, scopeAction_nothing)
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
                        scopeAction_nothing,
                        True,
                        False,
                        legend,
                        prepped_scope=tab_scope)


# the two lists of the puzzles screen: status -> label, tab switches between them
PUZZLE_VIEWS = {SCAN.STATUS_NEW: 'unknown', SCAN.STATUS_KNOWN: 'known'}


def scopeAction_open_puzzle(scope: Scope, screenState: ScreenState, puzzle_key: str = None):
    if puzzle_key is None:
        return scope

    new_scope = Scope(f"puzzle_{puzzle_key}", screen_puzzle_detail, screenState)
    new_scope.parent_scope = scope
    new_scope.data['puzzle_key'] = puzzle_key
    new_scope.exec = None
    screenState.activeScope = new_scope
    return new_scope


def screen_puzzles(stdscr, keyboardState, screenState, fullNodeState: FullNodeState, figlet=False):

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

    pos = UIgraph.Point(1,1)
    ELEMENTS.create_text_double_space(win, screenState, pos, 'puzzles', P_title, C_background,
                                      3, True, inv_color=False)
    pos += UIgraph.Point(0,3)

    entries, version = SCAN.CATALOG.snapshot()
    labels = {e.puzzle_key: e.label() for e in entries}
    entries.sort(key=lambda e: -e.seen_count)
    status_count = {status: 0 for status in PUZZLE_VIEWS}
    for name, family, status in labels.values():
        status_count[status] += 1

    # left/right switch between the unknown and the known puzzles (like the address viewer),
    # enter goes into the list and esc comes back. Each list keeps its cursor
    views = list(PUZZLE_VIEWS)
    view = views[main_scope.cursor_x % len(views)]
    tab_name = f"puzzles_{view}"

    chain = SCAN.CHAIN_SCANNER
    mempool = SCAN.MEMPOOL_SCANNER
    put_text(win, pos, (f"chain scan (last {CONF.PUZZLE_SCAN_COIN_LIMIT:,} spent coins): {chain.status} | "
                        f"blocks {chain.blocks_scanned}/{chain.blocks_total} | coins scanned {chain.coins_scanned:,}"), P_text)
    pos += UIgraph.Point(0,1)
    put_text(win, pos, f"mempool scan: {mempool.status} | transactions {len(mempool.txs):,}", P_text)
    pos += UIgraph.Point(0,2)

    # list selector: tabs drawn like the address viewer, touching the table below. They are
    # drawn after the table, so the line under the selected tab joins the table border
    pos_tab_title = pos
    pos += UIgraph.Point(0, 2)
    screenState.footer_text += "| switch list=←→ "

    if view == SCAN.STATUS_KNOWN:
        legend = ['name', 'family', 'layers', 'seen', 'first seen in', 'last seen']
        column_widths = [30, 12, 70, None, None, None]
    else:
        legend = ['layers', 'seen', 'first seen in', 'last seen']
        column_widths = [100, None, None, None]
    rows = []
    keys = []
    for e in entries:
        name, family, status = labels[e.puzzle_key]
        if status != view:
            continue
        row = [
            ' > '.join(e.sub_puzzle_names()),
            f"{e.seen_count:,}",
            e.source,
            UTILS.timestamp_to_date(e.last_seen),
        ]
        if view == SCAN.STATUS_KNOWN:
            row = [name or '-', family or '-'] + row
        rows.append(row)
        keys.append(e.puzzle_key)
    if rows:
        tab_size = UIgraph.Point(main_win_size.x - 2, main_win_size.y - pos.y - 2)
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
                            scopeAction_open_puzzle,
                            True,
                            False,
                            legend,
                            column_widths)
    else:
        put_text(win, pos + UIgraph.Point(0, 1), f"no {PUZZLE_VIEWS[view]} puzzles yet", P_text)

    P_tab_title = screenState.colorPairs["title"]
    P_tab_soft = screenState.colorPairs["tab_soft"]
    pos = pos_tab_title
    for status, label in PUZZLE_VIEWS.items():
        text = f" {label.upper()} puzzles ({status_count[status]}) "
        selected = status == view
        P_used = P_title if selected else P_tab_title
        ELEMENTS.create_text_double_space(win, screenState, pos, text, P_used, C_background, 3, True)
        underline_pos = pos + UIgraph.Point(0, 2)
        if selected:
            ELEMENTS.create_text(win, underline_pos, u'▀' * (len(text) + 2), P_tab_soft, True)
        else:
            ELEMENTS.create_text(win, underline_pos, ' ' * (len(text) + 2), P_used, True)
        pos += UIgraph.Point(len(text) + 2, 0)


def screen_puzzle_detail(stdscr, keyboardState, screenState, fullNodeState: FullNodeState, figlet=False):

    height = screenState.screen_size.y
    width = screenState.screen_size.x

    active_scope: Scope = screenState.activeScope
    main_scope: Scope = active_scope.main_scope
    screenState.scope_exec_args = [screenState]
    main_scope.update_2d()

    win = createFullSubWin(stdscr, screenState, height, width)
    win.bkgd(' ', curses.color_pair(screenState.colorPairs["body"]))
    main_win_size = UIgraph.Point(win.getmaxyx()[1], win.getmaxyx()[0])

    C_background = screenState.colors["background"]
    P_text = screenState.colorPairs["body"]
    P_title = screenState.colorPairs["xch"]

    puzzle_key = main_scope.data['puzzle_key']
    entry = SCAN.CATALOG.get(puzzle_key)
    name, family, status = entry.label()

    pos = UIgraph.Point(1,1)
    ELEMENTS.create_text_double_space(win, screenState, pos, 'puzzle', P_title, C_background,
                                      3, True, inv_color=False)
    pos += UIgraph.Point(0,3)

    lines = [
        f"status: {status} | name: {name or '-'} | family: {family or '-'}",
        f"seen {entry.seen_count:,} times | first seen in: {entry.source} | "
        f"first seen: {UTILS.timestamp_to_date(entry.first_seen)} | last seen: {UTILS.timestamp_to_date(entry.last_seen)}",
        f"example coin: 0x{entry.example_coin_id} | "
        f"{'spent at height ' + format(entry.example_height, ',') if entry.example_height else 'seen in the mempool'}",
        f"puzzle key: {puzzle_key}",
    ]
    for line in lines:
        put_text(win, pos, line, P_text)
        pos += UIgraph.Point(0,1)
    pos += UIgraph.Point(0,1)

    ##### name and family
    name_length = 40
    family_length = 30
    scope_name = ELEMENTS.create_prompt(win, screenState, keyboardState, main_scope, 'puzzle_name', pos,
                                        "Name: ", name_length, P_text, True, False,
                                        custom_scope_function=ScopeActions.press_enter)
    pos_family = pos + UIgraph.Point(name_length + 3, 0)
    if pos_family.x + family_length + 15 > main_win_size.x:
        pos_family = pos + UIgraph.Point(0, 3)
    scope_family = ELEMENTS.create_prompt(win, screenState, keyboardState, main_scope, 'puzzle_family', pos_family,
                                          "Family: ", family_length, P_text, True, False,
                                          custom_scope_function=ScopeActions.press_enter)
    pos_button = pos_family + UIgraph.Point(family_length + 3, -1)  # buttons are drawn one line up
    scope_save = ELEMENTS.create_button(win, screenState, main_scope, 'save', pos_button,
                                        custom_scope_function=ScopeActions.press_enter, button_type='execution')
    pos = UIgraph.Point(pos.x, pos_family.y + 2)

    if not main_scope.data.get('prompts_filled'):
        main_scope.data['prompts_filled'] = True
        scope_name.data['prompt'] = name or ''
        scope_name.data['cursor'] = len(scope_name.data['prompt'])
        scope_family.data['prompt'] = family or ''
        scope_family.data['cursor'] = len(scope_family.data['prompt'])

    # enter on a prompt or on the button saves both values
    save = False
    for scope in (scope_name, scope_family, scope_save):
        if scope.data.get('pressed_enter'):
            scope.data['pressed_enter'] = False
            save = True
    if save:
        new_name = scope_name.data['prompt'].strip()
        new_family = scope_family.data['prompt'].strip().upper()
        scope_family.data['prompt'] = new_family
        try:
            SCAN.CATALOG.set_name(puzzle_key, new_name, new_family)
            if new_name:
                screenState.footer_message = f"saved in layered_puzzles.json: {new_name} | family: {new_family or 'UNKNOWN'}"
            else:
                screenState.footer_message = "removed from layered_puzzles.json"
        except ValueError as e:
            # a catalog file edited by hand is not valid json, it is not overwritten
            screenState.footer_message = f"not saved, fix the json in resources/puzzles first: {e}"

    put_text(win, pos, f"known families: {', '.join(SCAN.CATALOG.families())} | saved in resources/puzzles/layered_puzzles.json, an empty name removes it", P_text)
    pos += UIgraph.Point(0,2)

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

    put_text(win, pos, f"layers and curried puzzles: {len(nodes)}", P_text, bold=True)
    pos += UIgraph.Point(0,1)

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

    put_text(win, pos, f"level {node['level']}: {node['puzz_name']} | select a row and press y to copy", P_text, bold=True)
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

    # run copy/paste action or other pending stuffs
    if len(screenState.pending_action) > 0:
        for i, fn in screenState.pending_action:
            fn()
        screenState.pending_action = []


REORG_VIEWS = ['timeline', 'by depth']
REORG_REFRESH = 30  # sec between two scans of the last blocks
REORG_CHART_MAX_ROWS = 8


def human_age_days(seconds: float) -> str:
    """human_age, with days for the ages over one day"""
    if seconds < 86400:
        return human_age(seconds)
    seconds = int(seconds)
    return f"{seconds // 86400}d {seconds % 86400 // 3600:02d}h"


def reorg_depth_color(screenState: ScreenState, depth: int):
    if depth <= 1:
        return screenState.colorPairs["body"]
    if depth == 2:
        return screenState.colorPairs["xch"]
    return screenState.colorPairs["error"]


def draw_reorg_timeline(win, screenState: ScreenState, pos: UIgraph.Point, width: int, chart_rows: int,
                        forks: list, selected):
    """Forks on a time axis, from the oldest one to now: one column for each time bucket,
    the bar is the depth of the deepest fork in it. A ▼ marks the selected fork.
    Returns the number of lines used"""
    P_text = screenState.colorPairs["body"]
    P_title = screenState.colorPairs["xch"]
    label_width = 5  # depth labels on the left, then the axis
    cols = max(width - label_width - 1, 10)

    now = datetime.now().timestamp()
    timestamps = [f.timestamp for f in forks if f.timestamp is not None]
    start = min(timestamps) if timestamps else now - 86400
    span = max(now - start, 3600) * 1.02  # a small margin before the oldest fork
    start = now - span

    def column(timestamp):
        return min(int((timestamp - start) / span * cols), cols - 1)

    deepest = {}
    for f in forks:
        if f.timestamp is not None:
            c = column(f.timestamp)
            deepest[c] = max(deepest.get(c, 0), f.depth)

    x0 = pos.x + label_width
    # marker row
    if selected is not None and selected.timestamp is not None:
        put_text(win, UIgraph.Point(x0 + column(selected.timestamp), pos.y), '▼', P_title, True)
    # bars, from the top row down
    for r in range(chart_rows):
        level = chart_rows - r
        y = pos.y + 1 + r
        label = f"{level}+" if level == chart_rows and max(deepest.values(), default=0) > chart_rows else str(level)
        put_text(win, UIgraph.Point(pos.x, y), f"{label:>3} │", P_text)
        for c, depth in deepest.items():
            if depth >= level:
                put_text(win, UIgraph.Point(x0 + c, y), '█', reorg_depth_color(screenState, depth))

    # time axis with a tick every few columns
    y_axis = pos.y + 1 + chart_rows
    # dates only when the ticks are at least one day apart
    tick_every = 11
    date_format = '%m-%d'
    if tick_every / cols * span < 86400:
        tick_every = 17
        date_format = '%m-%d %H:%M'
    axis = ['─'] * cols
    for c in range(0, cols - tick_every // 2, tick_every):
        axis[c] = '┬'
        tick_time = datetime.fromtimestamp(start + c / cols * span).strftime(date_format)
        put_text(win, UIgraph.Point(x0 + c, y_axis + 1), tick_time, P_text)
    put_text(win, UIgraph.Point(pos.x, y_axis), '    └' + ''.join(axis), P_text)
    return chart_rows + 3


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
    screenState.footer_text += "| switch view=←→ "

    if view == 'by depth':
        forks.sort(key=lambda f: (f.depth, f.tip_height), reverse=True)

    legend = ['time', 'ago', 'fork at height', 'depth', 'orphaned blocks', 'orphaned tip']
    now = datetime.now().timestamp()
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

    tab_name = f"reorgs_{view.replace(' ', '_')}"
    selected = None
    if view == 'timeline':
        # the line under the tabs, the chart has no border of its own
        put_text(win, pos, '─' * (main_win_size.x - 2), P_text)
        chart_rows = min(max(deepest, 3), REORG_CHART_MAX_ROWS)
        tab_scope = main_scope.sub_scopes.get(f"{main_scope.id}_{tab_name}")  # the name create_tab gives it
        if tab_scope is not None and forks:
            selected = forks[tab_scope.cursor % len(forks)]
        used = draw_reorg_timeline(win, screenState, pos + UIgraph.Point(0, 1), main_win_size.x - 2,
                                   chart_rows, forks, selected)
        pos += UIgraph.Point(0, used + 2)

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
                            legend,
                            [None, None, None, None, None, 70])
    else:
        put_text(win, pos + UIgraph.Point(0, 1), "no fork in the node DB", P_text)

    P_tab_title = screenState.colorPairs["title"]
    P_tab_soft = screenState.colorPairs["tab_soft"]
    pos = pos_tab_title
    for name in REORG_VIEWS:
        text = f" {name.upper()} " if name == 'timeline' else f" {name.upper()} ({len(forks)}) "
        selected_tab = name == view
        P_used = P_title if selected_tab else P_tab_title
        ELEMENTS.create_text_double_space(win, screenState, pos, text, P_used, C_background, 3, True)
        underline_pos = pos + UIgraph.Point(0, 2)
        if selected_tab:
            ELEMENTS.create_text(win, underline_pos, u'▀' * (len(text) + 2), P_tab_soft, True)
        else:
            ELEMENTS.create_text(win, underline_pos, ' ' * (len(text) + 2), P_used, True)
        pos += UIgraph.Point(len(text) + 2, 0)


