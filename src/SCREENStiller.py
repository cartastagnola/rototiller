import sys
from typing import List, Tuple, Dict, Union, Callable
import curses
from datetime import datetime

#from chia.rpc.full_node_rpc_client import FullNodeRpcClient
#from chia.rpc.rpc_server import RpcServer
#from chia.rpc.wallet_rpc_client import WalletRpcClient
#from chia.daemon.client import connect_to_daemon_and_validate
#from chia_rs.sized_bytes import bytes32, bytes48
#from chia.types.blockchain_format.program import Program
#from chia.types.spend_bundle import SpendBundle
#from clvm_tools.binutils import disassemble

import src.UIgraph as UIgraph
import src.ELEMENTStiller as ELEMENTS
import src.TEXTtiller as TEXT
import src.WDBtiller as WDB
import src.UTILStiller as UTILS
from src.PUZZLEtiller import compare_to_known_puzzle, unroll_coin_puzzle, get_opcode_name
from src.TYPEStiller import (
    FingerState, CoinPriceData, ScreenState, FullNodeState, Scope, KeyboardState,
    FullNodeState, ScreenState, ScopeActions)

from src.CONFtiller import (
    debug_logger, logging, DEBUGGING, DB_WDB, DB_SB, SQL_TIMEOUT, XCH_FAKETAIL,
    BTC_FAKETAIL, XCH_CUR, USD_CUR, XCH_MOJO, CAT_MOJO, full_node_port, full_node_rpc_port,
    FIGLET, DOOM_FONT, FUTURE_FONT, BLOCK_MAX_COST)

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
            ('full node', screen_full_node, ScopeActions.activate_scope),
        ]
        if DEBUGGING:
            menu_items += [
                ('wallet', screen_fingers, ScopeActions.activate_scope),
                ('harvester analytics', screen_harvester, ScopeActions.activate_scope),
                ('dex', screen_dex, ScopeActions.activate_scope),
                ("tabs", screen_tabs, ScopeActions.activate_scope),
                #('debugging screen', DEBUGtiller.screen_debugging, ScopeActions.activate_scope),
            ]

        for name, handler, exec_fun in menu_items:
            newScope = Scope(name, handler, screenState)
            newScope.exec = exec_fun
            newScope.parent_scope = activeScope
            activeScope.sub_scopes[name] = newScope

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

    # keyboard controller
    if keyboardState.enter:
        screenState.screen = "main"
        screenState.init = False


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
        screenState.screen_data["scopes"][name]  = scope

    scope = screenState.screen_data["scopes"][name]
    if scope.active:
        scope.update_no_sub(len(menu_list))

    select = scope.cursor

    if figlet:

        s_height = FUTURE_FONT.height

        if scope.active:
            stdscr.addstr(point.y + len(menu_list) * s_height + 1, point.x, "H" * 10)
        elif scope.selected:
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
        elif scope.selected:
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
                                    open_coin_wallet,
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
    if scope.selected:
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
    """menu_items: is a list of tuple (name: str, called_function: callable, scope_action callable(scope))"""
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

    if len(activeScope.sub_scopes) == 0:
        for name, handler, exec_fun in menu_items:
            newScope = Scope(name, handler, screenState)
            newScope.exec = exec_fun
            newScope.parent_scope = activeScope
            activeScope.sub_scopes[name] = newScope

    # TODO it always active?
    if activeScope is screenState.activeScope:
        activeScope.update_legacy()
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
        bundles = WDB.load_spend_bundles(conn, group_name='watch later')
        print("load watch")
        print(bundles)
        print(len(bundles))
        with thread_db_lock:
            main_scope.data['watch_later_cache'] = bundles

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


    with thread_db_lock:
        watch_later_bundles = main_scope.data['watch_later_cache']

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
                                    open_transaction,
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
                                    open_transaction,
                                    True,
                                    False,
                                    legend,
                                    archive_loader,
                                    bundle_state_to_table)

    #archive_loader.update_offset(tab_scope.cursor)
    archive_loader.start_updater_thread()


def screen_spend_bundles(stdscr, keyboardState, screenState, fullNodeState: FullNodeState, figlet=False):
    menu_items = [
        ('watch later', screen_sb_watch_later, ScopeActions.activate_scope),
        ('archive', screen_sb_archive, ScopeActions.activate_scope),
        ('memepool', screen_memepool, ScopeActions.activate_scope)
    ]

    factory_menu(menu_items, stdscr, keyboardState, screenState, fullNodeState, figlet=False)


def screen_full_node(stdscr, keyboardState, screenState, fullNodeState: FullNodeState, figlet=False):

    if DEBUGGING:
        menu_items = [
            ('blocks', screen_blocks, ScopeActions.activate_scope),
            ('memepool', screen_memepool, ScopeActions.activate_scope),
            ('spend bundles', screen_spend_bundles, ScopeActions.activate_scope)
        ]
    else:
        menu_items = [
            ('blocks', screen_blocks, ScopeActions.activate_scope),
        ]

    factory_menu(menu_items, stdscr, keyboardState, screenState, fullNodeState, figlet=False)



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

    # load memepool
    ## TODO: move the sorting of the mempool outside the UI loop
    mempool_items = fullNodeState.deepcopy_mempool()

    sorted_mempool = sorted(list(mempool_items.values()), key=lambda item: item.fee_per_cost)  # sorted by fee per cost

    # create mempool block
    max_cost = 0
    mempool_blocks = [WDB.MempoolBlock()]
    for item in sorted_mempool:
        current_block: WDB.MempoolBlock = mempool_blocks[-1]
        if max_cost < item.cost:
            max_cost = item.cost
        if current_block.total_cost + item.cost <= BLOCK_MAX_COST:
            current_block.add_item(item)
        else:
            mempool_blocks.append(WDB.MempoolBlock())

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

    ### go to block
    def go_to_block(scope: Scope, screen_state: ScreenState, *args):
        if scope.parent_scope:
            scope.data['pressed_enter'] = True
            screen_state.activeScope = scope.parent_scope
            return scope.parent_scope

    pre_text = "Go to block: "
    prompt_lenght = min(80, width - 4)
    scope_go_to = ELEMENTS.create_prompt(node_data, screenState, keyboardState, main_scope, 'go to block', pos,
                                         pre_text, prompt_lenght, P_text, True, False, custom_scope_function=go_to_block)
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

        if 'pressed_enter' in scope_go_to.data and scope_go_to.data['pressed_enter']:
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
                        table = 'full_blocks'
                        fetcher = WDB.make_sql_fetcher(table)
                        block = fetcher(conn, 0, 1, filters={'header_hash':hash})
                        if len(block) < 1:
                            scope_go_to.data['valid_data'] = False
                            scope_go_to.data["invalid_data_message"] = 'hash not found'
                        else:
                            height = block[0][2]  # from the tuple select the third element > block_height
                    else:
                        scope_go_to.data['valid_data'] = False
                        scope_go_to.data["invalid_data_message"] = 'hash must be 32 bytes'

                case 'invalid':
                    scope_go_to.data['valid_data'] = False
                    scope_go_to.data["invalid_data_message"] = 'invalid input. Use int or hash'

            if height:
                scope_go_to.data['prompt'] = ''
                scope_go_to.data['cursor'] = 0
                blocks_loader.update_offset(height)
                blocks_loader.start_updater_thread()
                #block_band_scope.cursor = height
                main_scope.cursor_x = height

                # offset selected block on the right if possible
                right_block_offset = 2
                if height_last_block - height < right_block_offset:
                    right_block_offset = 0
                block_band_scope.data["idx_last_item"] = height + right_block_offset
                ScopeActions.select_next_scope(scope_go_to, screenState)


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


    if keyboardState.key == 'w':
        conn = sqlite3.connect(DB_SB, timeout=SQL_TIMEOUT)
        if WDB.load_spend_bundle(conn, spend_bundle_hash, "watch later") is None:
            WDB.add_spend_bundles_to_watch_later(conn, spend_bundle_hash)
            main_scope.data['watch_later'] = True
        else:
            pass
            # remove


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
                archive_loader = fullNodeState.spend_bundle_archive_loader
                items, first_idx = archive_loader.get_items_hot_chunks()
                transactions = {}
                for i in items:
                    if i is None:
                        continue
                    name = i.spend_bundle_hash
                    try:
                        sp: SpendBundle = SpendBundle.from_bytes(i.raw_spend_bundle)
                        sp_json = sp.to_json_dict()
                        print(sp_json)
                        transactions[i.spend_bundle_hash] = WDB.MempoolItem(raw_json_spendbundle=sp_json, timestamp=i.timestamp)
                    except Exception as e:
                        print('except_')
                        print('except_')
                        print('except_')
                        print('except_')
                        print('except_')
                        print('except_')
                        print('except_')
                        print('except_')
                        print('except_')
                        print(e)
                        traceback.print_exc()
                        rpc = call_rpc_node('get_all_mempool_items')
                        #for k, i in rpc.items():
                        #    print(k)
                        #    WDB.print_json(i)

                tx_cache["tx"] = transactions[spend_bundle_hash]

    main_scope.data["tx_cache"] = tx_cache

    tx = tx_cache["tx"]
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

        coin_id = calc_coin_id(uint64(rem['amount']), rem['parent_coin_info'], rem['puzzle_hash'])
        rem = ['removal', coin_id, rem['amount'], rem['parent_coin_info'], rem['puzzle_hash']]
        coins.append(rem)

    coins.append([''] * len(legend))

    # additions
    print('addddditions')
    print(tx.additions)
    for add in tx.additions:
        coin_id = calc_coin_id(uint64(add['amount']), add['parent_coin_info'], add['puzzle_hash'])
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
                                         legend)

    sp = tx.spend_bundle

    sp_coins = sp['coin_spends']

    selected_id = coins[coin_tab_scope.cursor][1]

    c_puzzle = "not found"
    c_solution = "not found"
    for c in sp_coins:
        c_coin = c['coin']
        c_id = calc_coin_id(uint64(c_coin['amount']), c_coin['parent_coin_info'], c_coin['puzzle_hash'])
        if c_id == selected_id:
            c_puzzle = Program.fromhex(c['puzzle_reveal'])
            c_solution = Program.fromhex(c['solution'])

            # unroll puzzle
            c_puzzle_unrolled = unroll_coin_puzzle(c_puzzle)
            c_puzzle_names = []
            for p in c_puzzle_unrolled:
                c_puzzle_names.append(compare_to_known_puzzle(p))


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
                code = get_opcode_name(i[0])
                ELEMENTS.create_text(tx_win, pos, f"{code}: {i} and type f{type(i)}", P_text, bold=False)

    pos += UIgraph.Point(0,2)
    #ELEMENTS.create_text(tx_win, pos, "spend_bundle_hash: " + str(tx.spend_bundle_hash)[:20], P_text, bold=False)


    ### saved spendbundle -> folder with the spend save clearly
    ### save all the mempool...
    ### make sqlite for mempool and puzzle_reveal

def screen_memepool(stdscr, keyboardState, screenState, fullNodeState: FullNodeState, figlet=False):

    ### view
    # transaction id
    # coin selector
    # coin viewer


    # delete screenState size dimension? and get them from stdscr? why two places?
    width = screenState.screen_size.x
    height = screenState.screen_size.y

    meme_win = createFullSubWin(stdscr, screenState, height, width)
    meme_win.bkgd(' ', curses.color_pair(screenState.colorPairs["body"]))

    active_scope: Scope = screenState.activeScope
    main_scope: Scope = active_scope.main_scope
    screenState.scope_exec_args = [screenState]

    # load memepool
    ## TODO: move the sorting of the mempool outside the UI loop

    mempool_items = fullNodeState.deepcopy_mempool()
    print()
    print(mempool_items)
    for i in mempool_items:
        print(i)


        # self.spend_bundle_hash = spend_bundle_hash
        # self.cost = json_item['cost']
        # self.fee = json_item['fee']

        # self.addition_amount = json_item['npc_result']['conds']['addition_amount']
        # self.removal_amount = json_item['npc_result']['conds']['removal_amount']
        # self.additions = json_item['additions']
        # self.removals = json_item['removals']
        # self.spend_bundle = json_item['spend_bundle']
        # self.added_coins_count = len(self.additions)
        # self.removed_coins_count = len(self.removals)
        # self.fee_per_cost = self.fee / self.cost

    attrs = {
        "transaction id": "spend_bundle_hash",
        "cost": "cost",
        "fee": "fee",
        "fee per cost": "fee_per_cost"
    }

    ## tx_ID  -- INPUT coins -- amount --- OUTPUT coins -- amount --

    legend = []
    for key, attribute in attrs.items():
        legend.append(key)

    txs_data = []
    txs_keys = []
    for spend_bundle_hash, tx in mempool_items.items():
        data = []
        for key, attribute in attrs.items():
            data.append(getattr(tx, attribute))

        txs_data.append(data)
        txs_keys.append(spend_bundle_hash)

    P_text = screenState.colorPairs['tab_soft']
    #key = list(mempool_items.keys())[0]
    #spend_bundle = mempool_items[key].spend_bundle
    pos = UIgraph.Point(2,3)
    #ELEMENTS.create_text(meme_win, pos, str(spend_bundle)[:200], P_text, bold=False)

    #with open('sb.json', 'w') as f:
    #    f.write(json.dumps(spend_bundle, indent=4))

    #print(json.dumps(spend_bundle, indent=4))
    pos = UIgraph.Point(3,23)
    tab_size = UIgraph.Point(width - 2, height - pos.y - 6)

    print(txs_data)

    main_scope.update()
    ELEMENTS.create_tab(meme_win,
                        screenState,
                        main_scope,  # main_scope
                        "mempool",
                        txs_data,
                        txs_keys,
                        None,
                        False,
                        pos,
                        tab_size,
                        keyboardState,
                        open_transaction,
                        True,
                        False,
                        legend)

