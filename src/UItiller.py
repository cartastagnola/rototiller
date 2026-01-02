import os
import traceback
import curses
import time
import threading
import sqlite3

from typing import List, Dict

import src.UIgraph as UIgraph
from src.CONFtiller import (
    debug_logger, logging, DEBUGGING, DB_BLOCKCHAIN_RO,
    DB_WDB, DB_SB, SQL_TIMEOUT)
import src.ELEMENTStiller as ELEMENTS
import src.WDBtiller as WDB

from src.COLORStiller import init_colors
from src.TYPEStiller import (
    FingerState, CoinPriceData, ScreenState, FullNodeState, KeyboardState,
    PkState, Scope, ScopeActions)
import src.SCREENStiller as SCREENS
import src.SERVICEStiller as SERVICES
import src.KEYBOARDtiller as KEYBOARD
import src.RPCtiller as RPC

import src.DEBUGtiller as DEBUGtiller

#### global for debugging
DEBUG_OBJ = DEBUGtiller.DEBUG_OBJ

#### NCURSES CONFIG #####
# set the esc delay to 25 milliseconds
# by default curses use one seconds
os.environ.setdefault('ESCDELAY', '25')


def interFace(stdscr):

    try:
        #### cursor init ####
        key = 0
        curses.curs_set(0)  # set cursor visibility
        stdscr.nodelay(True)
        stdscr.erase()
        stdscr.refresh()
        # Enable mouse events
        curses.mousemask(curses.ALL_MOUSE_EVENTS)


        ### wallets states ###
        data_lock = threading.Lock()
        fingers_state: List[FingerState] = []
        fingers_list: List[int] = []
        finger_active: List[int] = [0]
        count_server = [0]
        coins_data: Dict[str, CoinPriceData] = {}

        ### timing ###
        frame_start = None
        frame_end = None
        frame_time = 0
        frame_time_max = 0
        frame_time_display = 0
        frame_time_total = 0
        frame_time_real_display = 0
        frame_time_real_max = 0
        frame_time_curses_max = 0
        frame_time_curses_display = 0


        ### check full node ###
        node_status = RPC.call_rpc_node('healthz')


        ### wallet data ###
        # load data from WDB
        # create the WDB or load the data
        conn = sqlite3.connect(DB_WDB, timeout=SQL_TIMEOUT)
        WDB.create_wallet_db(conn)
        logging(debug_logger, "DEBUG", f"WDB '{DB_WDB}' initialized successfully.")
        SERVICES.load_WDB_data(conn, fingers_state, fingers_list, coins_data, finger_active)
        conn.close()


        wallet_thread = None
        #wallet_thread = threading.Thread(target=SERVICES.fetch_wallet,
        #                                 args=(data_lock,
        #                                       fingers_state,
        #                                       fingers_list,
        #                                       finger_active,
        #                                       coins_data,
        #                                       count_server),
        #                                 daemon=True)
        ##### WALLET STOPPED
        #wallet_thread.start()

        ### spend_bundles data ###
        conn = sqlite3.connect(DB_SB, timeout=SQL_TIMEOUT)
        WDB.create_spend_bundle_db(conn)
        logging(debug_logger, "DEBUG", f"NODE STATE {DB_SB}' initialized successfully.")
        conn.close()

        screenState = ScreenState()
        screenState.active_pk = [finger_active[0], screenState.active_pk[1]]

        ### TODO to fun
        try:
            fullNodeState: FullNodeState = FullNodeState(DB_BLOCKCHAIN_RO)

            node_state_thread = threading.Thread(target=fullNodeState.update_state,
                                                 args=(screenState,), daemon=True)
            node_state_thread.start()
        except Exception as e:
            print("full node state init failed")
            print(e)
            print(traceback.print_exc())


        # Start colors in curses
        curses.start_color()
        init_colors(screenState)

    except Exception as e:
        print("problems with services starting and colors creation")
        print(e)
        traceback.print_exc()

    # create the intro and the main menu scopes
    scopeIntro = Scope('intro', SCREENS.screen_intro, screenState)
    scopeMainMenu = Scope('main_menu', SCREENS.screen_main_menu, screenState)

    scopeMainMenu.exec = ScopeActions.activate_scope
    scopeIntro.sub_scopes[scopeMainMenu.name] = scopeMainMenu
    screenState.activeScope = scopeIntro

    try:

        frame_start = time.perf_counter()
        while not key:

            # keyboard input processing
            activeScope = screenState.activeScope
            keyboardState = KeyboardState()
            key = KEYBOARD.processing(stdscr, screenState, keyboardState, activeScope)

            stdscr.erase()

            ### check service threads
            if node_status and not node_state_thread.is_alive():
                node_status = False

            ### update wallet data. (ADD A LOCK HERE)
            for fs in fingers_state:
                screenState.public_keys[fs.fingerprint] = fs
            if screenState.active_pk[0] == 0:
                screenState.active_pk = [finger_active[0], screenState.active_pk[1]]

            ### update coin data
            with data_lock:
                screenState.coins_data = coins_data

            height, width = stdscr.getmaxyx()
            screenState.screen_size = UIgraph.Point(width, height)
            windowDim = f"width={width}; height={height}"
            # the 32 and 16 can
            if width < 80 or height < 24:
                if width < 32 or height < 4:
                    print("The window terminal is too small")
                    break
                else:
                    dinky = stdscr.subwin(height, width, 0, 0)
                    dinky.bkgd(' ', curses.color_pair(screenState.colorPairs["nonode"]))

                    #text = "am i a dinky puppy terminal?"
                    #dinky.addstr(height // 2, width // 2 - len(text) // 2, text)
                    p_h = UIgraph.Point(0, height // 2 - 1)
                    text = "What am I, some dinky puppy terminal?"
                    ELEMENTS.create_text_aligned(dinky, p_h, text, screenState.colorPairs["nonode"], bold=True, align_h=1, align_v=0)
                    p_h += UIgraph.Point(0,1)
                    text = "I can't even get these punch cards to fit in!"
                    ELEMENTS.create_text_aligned(dinky, p_h, text, screenState.colorPairs["nonode"], bold=True, align_h=1, align_v=0)
            elif not node_status:
                nonode = stdscr.subwin(height, width, 0, 0)
                nonode.bkgd(' ', curses.color_pair(screenState.colorPairs["footer"]))
                text = "no active full node founded"
                P_color = screenState.colorPairs["nonode"]
                p = UIgraph.Point(width // 2 - len(text) // 2, height // 2)
                ELEMENTS.create_blinking_text(nonode, p, text, P_color, bold=True)

                ### check for the node at least once every 2 seconds
                node_status = RPC.call_rpc_node('healthz')
                if node_status:
                    ### TODO to fun
                    try:
                        fullNodeState: FullNodeState = FullNodeState(DB_BLOCKCHAIN_RO)

                        node_state_thread = threading.Thread(target=fullNodeState.update_state,
                                                             args=(screenState,), daemon=True)
                        node_state_thread.start()
                    except:
                        print("full node not running")
            else:
                header = stdscr.subwin(1, width, 0, 0)
                P_header = screenState.colorPairs["header_W"]
                header.bkgd(' ', curses.color_pair(P_header))
                title = 'rototiller'
                fing_name = ""
                if screenState.active_pk[0] != 0:
                    try:
                        active_finger = screenState.active_pk[0]
                        pk_state: PkState = screenState.public_keys[active_finger]
                        fing_name = str(active_finger) + " - " + pk_state.label
                    except:
                        print("waiting for server data")
                        fing_name = str(active_finger)
                        traceback.print_exc()

                header.addstr(0, 0, f"{title} | {fing_name}")
                # text right aligned on the main screen
                # fps = f"fps: {fps} | second per frame: {frame_time_display}; "
                fps = 0
                fps_real = 0
                curses_percent = 0
                if frame_time_display > 0:
                    fps = 1 / frame_time_display
                    curses_percent = frame_time_curses_display / frame_time_display
                if frame_time_real_display > 0:
                    fps_real = 1 / frame_time_real_display
                fps = f"fps eff./real: {fps:.1f} / {fps_real:.1f} "
                if width > 100:
                    fps = fps + f"| blit time ratio: {curses_percent*100:.1f}% | "
                window_info = fps + windowDim
                y, x = 0, width - len(window_info) - 1
                header.addstr(y, x, window_info)


                nLinesHeader = (len(title) + len(windowDim)) // width + 1
                screenState.headerLines = nLinesHeader

                # helper footer
                footerText = f"Movement: ←↑↓→ or vim | confirm=enter back=esc q=quit {screenState.footer_text}"
                screenState.footer_text = ""
                nLines = int(len(footerText) / width + 1)
                footer = stdscr.subwin(nLines, width, height-nLines, 0)
                P_footer = screenState.colorPairs["footer"]
                P_footer = P_header
                footer.bkgd(' ', curses.color_pair(P_footer))
                footer.addstr(0, 0, footerText)

                # debug footer
                extraLines = 1
                nLinesDebug = 0
                if DEBUGGING:
                    footerTextDebug = f"server count: {count_server[0]}"
                    if len(fingers_list) >= 1:
                        footerTextDebug += f", finger 0: {fingers_list[0]}"
                    if len(fingers_list) >= 2:
                        footerTextDebug += f" finger 1: {fingers_list[1]}"
                    if len(fingers_list) >= 2:
                        footerTextDebug += f" numbers of wallets [0]: {len(fingers_state[0].wallets)}"
                        footerTextDebug += f" numbers of wallets [1]: {len(fingers_state[1].wallets)}"
                    with data_lock:
                        footerTextDebug += f" number of coins_data: {len(coins_data)}"
                    nLinesDebug = int(len(footerTextDebug) / width + 1)

                    # colors count
                    n_curses_colors = len(screenState.cursesColors.colors)
                    n_curses_colors_idx = screenState.cursesColors.colorsIndex
                    n_curses_pairs = len(screenState.cursesColors.pairs)
                    n_curses_pairs_idx = screenState.cursesColors.pairsIndex

                    footer_colors = f'n. of colors: {n_curses_colors}; n. of pairs: {n_curses_pairs}'
                    footer_colors += f' colors n_idx: {n_curses_colors_idx}'
                    footer_colors += f' pairs n_idx: {n_curses_pairs_idx}'

                    DEBUG_TEXT = f"obj: {DEBUG_OBJ.text} and class {DEBUGtiller.DebugGlobals.cc_text}"

                    if len(DEBUG_TEXT) > 0:
                        extraLinesDebug = int(len(DEBUG_TEXT) / width + 1)
                        extraLines += extraLinesDebug

                    footerDebug = stdscr.subwin(nLinesDebug + extraLines, width,
                                                height-nLines-nLinesDebug - extraLines,
                                                0)
                    footerDebug.bkgd(' ', curses.color_pair(screenState.colorPairs["footer"]))
                    footerDebug.addstr(0, 0, footer_colors)
                    footerDebug.addstr(1, 0, footerTextDebug)
                    if len(DEBUG_TEXT) > 0:
                        footerDebug.addstr(2, 0, DEBUG_TEXT)

                    screenState.footerLines = nLines + nLinesDebug


                # screen selection
                activeScope.screen(stdscr, keyboardState,
                                   screenState, fullNodeState)
                KEYBOARD.execution(screenState, keyboardState, activeScope)


            frame_curses_start = time.perf_counter()
            #curses.doupdate()
            stdscr.refresh()
            frame_curses_end = time.perf_counter()

            # curses fps
            frame_time = frame_curses_end - frame_curses_start
            if frame_time > frame_time_max:
                frame_time_curses_max = frame_time


            # effective fps
            frame_end = time.perf_counter()
            frame_time = frame_end - frame_start
            if frame_time > frame_time_max:
                frame_time_max = frame_time

            # cap frame rate
            fps = 30
            sleep_time = 1/fps - frame_time
            if sleep_time > 0:
                time.sleep(sleep_time)

            # real fps
            # frame_time_real_display = 0
            # frame_time_real_max = 0
            frame_end = time.perf_counter()
            frame_time = frame_end - frame_start
            if frame_time > frame_time_real_max:
                frame_time_real_max = frame_time

            # update counter
            if frame_time_total > 0.1:  # update rate
                frame_time_total = 0

                # curses
                frame_time_curses_display = frame_time_curses_max
                frame_time_curses_max = 0

                # effective
                frame_time_display = frame_time_max
                frame_time_max = 0

                # real
                frame_time_real_display = frame_time_real_max
                frame_time_real_max = 0


            frame_time_total += frame_time

            frame_start = time.perf_counter()

    except Exception as e:
        print("Shit happens... in the main loop")
        print(e)
        traceback.print_exc()


def curses_main_loop():
    # start curses
    curses.wrapper(interFace)

