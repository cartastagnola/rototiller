import os
import traceback
import curses
import time
import threading
import sqlite3

from typing import List, Dict

from chia.util.bech32m import decode_puzzle_hash, encode_puzzle_hash

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
import src.CONFtiller as CONF
import src.TYPEStiller as TYPES
import src.UTILStiller as UTILS

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

        ####### init daemon client ########

        try:
            daemon_dispatcher = SERVICES.SocketDispatcher()

            def sync_status(data):
                sync = data['data']['blockchain_state']['sync']
                logging(debug_logger, "DEBUG", f"DYSPHER : sync status → {sync}")

            daemon_dispatcher.subscribe(TYPES.DaemonEvent.GET_BLOCKCHAIN_STATE, sync_status)

            # TODO: add shutdown event
            daemon_thread = None
            daemon_thread = threading.Thread(target=SERVICES.DaemonWebSocketClient.create_and_run_client,
                                             args=(daemon_dispatcher, ),
                                             daemon=True)
            daemon_thread.start()
        except Exception as e:
            print("no daemon")
            print(e)
            traceback.print_exc()
            logging(debug_logger, "DEBUG", f"DAEMON exception: {e}")


        ####### init DBs ########
        # watchlist csv
        path = CONF.USER_ADDX_WATCHLIST
        if not path.exists():
            # write and empty file
            empty_line = [('#address', ' name', " 'some notes'")]
            WDB.save_csv(path, empty_line)

        # blockchain cache
        cache_conn = WDB.get_connection(CONF.DB_CACHED_BLOCKCHAIN)
        try:
            WDB.create_cache_blockchain_db(cache_conn)
        except Exception as e:
            print('hole')
            print(e)

        cache_conn.close()

        logging(debug_logger, "DEBUG", f"DB '{CONF.DB_CACHED_BLOCKCHAIN}' initialized successfully.")

        def update_watchlisted_cached_addresses(data):
            """data: websocket data from the daemon"""
            # load the watch list
            path = CONF.USER_ADDX_WATCHLIST
            lines = WDB.load_csv(path)

            logging(debug_logger, "DEBUG", f"DB UPDATING CACHE... ... ... ...")
            logging(debug_logger, "DEBUG", f"DB {data}")
            logging(debug_logger, "DEBUG", f"DB {data['data']['transaction_block']}")
            logging(debug_logger, "DEBUG", f"DB {type(data['data']['transaction_block'])}")

            if not data['data']['transaction_block']:
                logging(debug_logger, "DEBUG", f"DB do nothinggggg")
                return

            ttime = time.perf_counter()

            # TODO: move the whole fun elsewhere
            from chia_rs.sized_bytes import bytes32
            from chia.util.bech32m import decode_puzzle_hash

            db_conn = WDB.get_connection(CONF.DB_BLOCKCHAIN_RO)
            cache_conn = WDB.get_connection(CONF.DB_CACHED_BLOCKCHAIN)
            logging(debug_logger, "DEBUG", f"DB starting cache fetcher for watchlist")
            try:
                for line in lines:
                    add = line[0]
                    try:
                        if add.startswith(CONF.ADD_PREFIX):
                            puzzle_hash = bytes(decode_puzzle_hash(add))
                        else:
                            puzzle_hash = bytes(UTILS.ensure_bytes32(add))

                        # test if the add is correct
                        encode_puzzle_hash(puzzle_hash, CONF.ADD_PREFIX)
                        WDB.FetchMaker.cache_fetcher(db_conn, cache_conn, puzzle_hash)

                        # bacis info
                        balance, unspent_coin_count, total_coin_count, peak_height = WDB.FetchMaker.get_total_amount_and_count_from_puzzle_hash(CONF.DB_BLOCKCHAIN_RO, puzzle_hash)
                        unspent_hinted_coin_count, total_hinted_coin_count = WDB.FetchMaker.get_hinted_amount_and_type_count_from_puzzle_hash(CONF.DB_BLOCKCHAIN_RO, puzzle_hash)
                        WDB.insert_cache_address_info(cache_conn, puzzle_hash, peak_height, balance, total_coin_count, unspent_coin_count, total_hinted_coin_count, unspent_coin_count)
                    except Exception as e:
                        logging(debug_logger, "DEBUG", f"exception decoding {puzzle_hash} - watchlist input: {add}")
                        UTILS.logging_traceback('CACHE LOAD')

            except Exception as e:
                print(e)
                logging(debug_logger, "DEBUG", f"UPDAYTE CACHE TIMO TRHE BIG ONE LOAD OUT exc {e}")
                logging(debug_logger, "DEBUG", f"UPDATE CACHE TIMO LOAD edarbello {line}")
                UTILS.logging_traceback('CACHE LOAD')

            logging(debug_logger, "DEBUG", "DB ENDED cache fetcher for watchlist")
            cache_conn.close()
            db_conn.close()

            new_tttime = time.perf_counter()
            pp = new_tttime - ttime

            logging(debug_logger, "DEBUG", f"DB ENDED cache fetcher for watchlist TOTALLLLL {pp}")

        daemon_dispatcher.subscribe(TYPES.DaemonEvent.NEW_BLOCK, update_watchlisted_cached_addresses)

        def chain_state(data):
            logging(debug_logger, "DEBUG", f"CHAIN STATE update ... ... ... ...")
            logging(debug_logger, "DEBUG", f"CHAIN STATE {data} ")
            peak = data['data']['blockchain_state']['peak']
            peak_height = peak['height']
            peak_hash = peak['header_hash']
            prev_hash = peak['prev_hash']
            prev_tx_hash = peak['prev_transaction_block_hash']
            prev_tx_height = peak['prev_transaction_block_height']
            logging(debug_logger, "DEBUG", f"heihgt {peak_height}, header hash {peak_hash}, previous hash {prev_hash}")

            # TODO: detect REORG
            ## ...

        daemon_dispatcher.subscribe(TYPES.DaemonEvent.GET_BLOCKCHAIN_STATE, chain_state)

        logging(debug_logger, "DEBUG", f"DB ENDEDE without ERRRORSSS")
        logging(debug_logger, "DEBUG", f"DB '{CONF.DB_CACHED_BLOCKCHAIN}' initialized successfully.")

        #### wallet data ###
        ## load data from WDB
        ## create the WDB or load the data
        #conn = sqlite3.connect(DB_WDB, timeout=SQL_TIMEOUT)
        #WDB.create_wallet_db(conn)
        #logging(debug_logger, "DEBUG", f"WDB '{DB_WDB}' initialized successfully.")
        #SERVICES.load_WDB_data(conn, fingers_state, fingers_list, coins_data, finger_active)
        #conn.close()


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
        screenState.daemon_socket_dispatcher = daemon_dispatcher
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
    scopeIntro: Scope = Scope('intro', SCREENS.screen_intro, screenState)
    scopeMainMenu: Scope = Scope('main_menu', SCREENS.screen_main_menu, screenState)

    scopeMainMenu.exec = ScopeActions.activate_scope
    scopeMainMenu.keyboard_exec = KEYBOARD.default_execution
    scopeIntro.sub_scopes[scopeMainMenu.name] = scopeMainMenu
    scopeIntro.keyboard_exec = KEYBOARD.default_execution
    screenState.activeScope = scopeIntro

    try:

        frame_start = time.perf_counter()
        while not key:

            # keyboard input processing
            activeScope: Scope = screenState.activeScope
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

            ### check windows size
            height, width = stdscr.getmaxyx()
            new_size = UIgraph.Point(width, height)
            screenState.screen_resized = False
            if screenState.screen_size != new_size:
                screenState.screen_size = new_size
                screenState.screen_resized = True
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

                # message footer
                if len(screenState.footer_message) > 0:
                    if screenState.footer_message_counter == 0:
                        screenState.footer_message_counter = time.time()
                    footer_message_text = 'MESSAGE: ' + screenState.footer_message
                    nLines_message = int(len(footer_message_text) / width + 1)
                    nLines += nLines_message
                    footer_message = stdscr.subwin(nLines_message, width, height-nLines, 0)
                    footer_message.bkgd(' ', curses.color_pair(P_footer) | curses.A_REVERSE)
                    ELEMENTS.create_text_aligned(footer_message, UIgraph.Point(0,0), footer_message_text, P_footer, bold=False, inv_color=True, align_h=1)

                    #footer_message.addstr(0, 0, footer_message_text)
                    if (time.time() - screenState.footer_message_counter) > 10:
                        screenState.footer_message_counter = 0
                        screenState.footer_message = ''



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

                screenState.footerLines = nLines + nLinesDebug - 1



                # screen selection
                activeScope.screen(stdscr, keyboardState,
                                   screenState, fullNodeState)

                # keyboard execution
                activeScope.keyboard_exec(screenState, keyboardState, activeScope)
                for item_key, item_exec in activeScope.custom_keyboard_exec.items():
                    item_exec(screenState, keyboardState, activeScope)

                # LOADING
                loading = False
                names = []
                names_text = ''
                with screenState.lock:
                    for i in range(len(screenState.running_threads) -1, -1, -1):
                        thr: threading.Thread = screenState.running_threads[i]
                        if thr.is_alive():
                            loading = True
                            names.append(str(thr.name))
                            names.append(str(thr.getName()))
                            names.append(str(thr.native_id))
                            names_text = names_text + ' | ' + thr.getName()
                        else:
                            screenState.running_threads.pop(i)

                if loading:
                    win_loading = stdscr.subwin(2, width, 1, 0)  # height 2 to avoid the bug of the last char of a win
                    P_loading = screenState.colorPairs["footer"]

                    now = int(time.time())
                    n_points = now % 4
                    loading_text = f"{names_text} - loading{'.' * n_points}{' ' * (3 - n_points)}"
                    loading_len = len(loading_text) + 3

                    y, x = 0, width - loading_len
                    win_loading.addstr(y, x, loading_text, curses.color_pair(P_loading))

                    # DEBUG
                    #win_loading.addstr(1, 2, '_|_'.join(names), curses.color_pair(P_loading))

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


            # TODO: on gnome terminal esc is slow, Why? the frame time is alwasy the same, also the frame after the escaped one
            # if keyboardState.esc == True:
            #     logging(debug_logger, "DEBUG", f"ESC: frame rate {frame_time}")
            # else:
            #     logging(debug_logger, "DEBUG", f"N: frame rate {frame_time}")


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
    # reduce the esc delay
    os.environ.setdefault('ESCDELAY', '25')
    curses.set_escdelay(25)  # reduce esc delay

    # if tmux try to reduce the delay
    if "TMUX" in os.environ:
        try:
            import subprocess
            subprocess.run(["tmux", "set-option", "-s", "escape-time", "25"], check=True)
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

    # start curses
    curses.wrapper(interFace)

