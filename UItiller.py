#!/usr/bin/env python3

import sys, os, traceback
import asyncio
import curses
import time
import threading
import requests
import json

from dataclasses import dataclass
from typing import List, Tuple, Dict

#from chia.wallet.util.tx_config import DEFAULT_TX_CONFIG
from chia.util.default_root import DEFAULT_ROOT_PATH
from chia.util.config import load_config

from chia.rpc.full_node_rpc_client import FullNodeRpcClient
from chia.rpc.wallet_rpc_client import WalletRpcClient
from chia.types.blockchain_format.sized_bytes import bytes32
from chia.util.ints import uint16, uint32, uint64

# setup the node
# config/config.yaml
config = load_config(DEFAULT_ROOT_PATH, "config.yaml")
self_hostname = config["self_hostname"] # localhost
full_node_rpc_port = config["full_node"]["rpc_port"] # 8555
wallet_rpc_port = config["wallet"]["rpc_port"] # 9256

# set the esc delay to 25 milliseconds (the defaul is 1 sec)
os.environ.setdefault('ESCDELAY', '25')

sys.path.append('/home/boon/gitRepos/Chia-Py-RPC/src/')
from chia_py_rpc.wallet import Wallet
from chia_py_rpc.wallet import WalletManagement
from chia_py_rpc.wallet import KeyManagement


sys.path.append('/home/boon/gitRepos/')
import dex as dex

# dexi api
def loadAllTickers():
    r = requests.get('https://api.dexie.space/v2/prices/tickers')
    tickers = json.loads(r.text)["tickers"]
    return tickers

# store elements

######
'''
what could be the temp status of the wallet/
'''
# check the correct size for each property

# store for the cat names
cat_names: Dict[str, Tuple[str, str]]
cat_names = {
    "a628c1c2c6fcb74d53746157e438e108eab5c0bb3e5c80ff9b1910b3e4832913":
    ("SBX", "Spacebucks"),
    "db1a9020d48d9d4ad22631b66ab4b9ebd3637ef7758ad38881348c5d24c38f20":
    ("DBX", "dexie bucks"),
    "e0005928763a7253a9c443d76837bdfab312382fc47cab85dad00be23ae4e82f":
    ("MBX", "Moonbucks")
}

print(cat_names["db1a9020d48d9d4ad22631b66ab4b9ebd3637ef7758ad38881348c5d24c38f20"][1])

@dataclass
class WalletState:
    data: str # it should be byte32 (the data of what?)
    name: str #
    ticker: str #
    block_height: uint32
    addresses: List[str]  # check type and move to pkState
    confirmed_wallet_balance: uint64  # check type
    spendable_balance: uint64  # check type
    unspent_coin_count: int  # check type

    def __init__(self):
        self.data = ""
        self.name = ""
        self.ticker = ""
        self.block_height = 0
        self.addresses = []
        self.confirmed_wallet_balance = 0
        self.spendable_balance = 0
        self.unspent_coin_count = 0


@dataclass
class FingerState:
    fingerprint: int
    wallets: List[WalletState]

    def __init__(self):
        self.fingerprint = 0
        self.wallet = []


@dataclass
class PkState:
    fingerprint: int
    pk: uint64
    wallets: Dict[int, WalletState]

    def __init__(self):
        self.fingerprint = 0
        self.pk = 0
        self.wallets = {}



# wallet fetcher
def fetch_wallet(data_lock, fingers_state, fingers_list, count_server):
    while True:

        count_server[0] += 1
        print(f'loop counting: {count_server[0]}')

        original_logged_finger = asyncio.run(call_rpc_wallet('get_logged_in_fingerprint'))

        fingerprints = []

        ######################### FINGERPRINTS LOADING ################
        try:
            fingerprints = asyncio.run(call_rpc_wallet('get_public_keys'))
            # get logged finger -> to place on a screen variable
            #screenState.active_pk = (False, asyncio.run(call_rpc_wallet('get_logged_in_fingerprint')))
            for finger in fingerprints:
                if finger in fingers_list:
                    continue
                else:
                    new_pk = PkState()
                    new_pk.fingerprint = finger
                    fingers_list.append(finger)
                    fingers_state.append(new_pk)

        except Exception as e:
            print("probably there is no chia node and wallet running")
            print(e)


        #################### LOAD WALLET ########################
        try:

            for finger in fingerprints:

                logged_finger =  asyncio.run(call_rpc_wallet('get_logged_in_fingerprint'))
                if logged_finger != finger:
                    result = asyncio.run(call_rpc_wallet('log_in', finger))
                    print(result)

                idx = fingers_list.index(finger)
                wallets = fingers_state[idx].wallets

                # chia wallet
                chia_wallet: WalletState  = WalletState()
                response = asyncio.run(call_rpc_wallet('get_wallet_balance', 1))
                chia_wallet.confirmed_wallet_balance = response['confirmed_wallet_balance']
                chia_wallet.spendable_balance = response['spendable_balance']
                chia_wallet.unspent_coin_count = response['unspent_coin_count']

                wallets[1] = chia_wallet
                print(chia_wallet)
                print('done')

                # add CATs
                cat_chia_wallets = asyncio.run(call_rpc_wallet('get_wallets', wallet_type=6))
                print('all')
                print(cat_chia_wallets)
                for e, i in enumerate(cat_chia_wallets):
                    cat_wallet = WalletState()
                    balance = asyncio.run(call_rpc_wallet('get_wallet_balance', i['id']))
                    cat_wallet.data = balance['asset_id']
                    cat_wallet.name = cat_names[cat_wallet.data][1]
                    cat_wallet.ticker = cat_names[cat_wallet.data][0]
                    cat_wallet.confirmed_wallet_balance = balance['confirmed_wallet_balance']
                    cat_wallet.spendable_balance = balance['spendable_balance']
                    cat_wallet.unspent_coin_count = balance['unspent_coin_count']
                    wallets[i['id']] = cat_wallet
                    # evaluate if it is better to use the byte32 name

        except Exception as e:
            print("probably there is no chia node and chia_wallet running")
            print(e)

        result = asyncio.run(call_rpc_wallet('log_in', original_logged_finger))

        time.sleep(10)


# UI elements
@dataclass
class KeyboardState:
    moveUp: bool = False
    moveDown: bool = False
    moveLeft: bool = False
    moveRight: bool = False
    enter: bool = False
    esc: bool = False

@dataclass
class ScreenState:
    init: bool
    selection: int
    select_y: int
    screen: str
    menu: List[str]
    active_pk: Tuple[bool, int]  # [is fing selected, fingerprint]
    public_keys: Dict[int, PkState] # check what kind of int is a pk, and change wallets to something that belond to a public key

    def __init__(self):
        self.init = False
        self.selection = 0
        self.select_y = 0
        self.screen = 'intro'
        self.menu = []
        self.active_pk = (False, 0)
        self.public_keys = {}


# UI

def menu_select(stdscr, menu, select, point):
    """Create a menu at given coordinate. Point[y,x]"""
    for i, item in enumerate(menu):
        if select == i:
            stdscr.attron(curses.color_pair(2))
        else:
            stdscr.attron(curses.color_pair(1))
        stdscr.addstr(point[0] + i, point[1], (str(i) + " - " + str(item)))


def main_menu(stdscr, keyboardState, screenState, height, width):

    print(screenState.screen)
    print()
    if not screenState.init:
        screenState.screen = 'main'
        screenState.selection = 0
        screenState.menu = ["wallet", "full node", "harvester analytics", "DEXI"]
        screenState.init = True

    if keyboardState.enter is True:
        screenState.screen = screenState.menu[screenState.selection]
    if keyboardState.moveUp:
        screenState.selection -= 1
    if keyboardState.moveDown:
        screenState.selection += 1

    screenState.selection = screenState.selection % len(screenState.menu)

    # menu dimensino
    yDimMenu = len(screenState.menu)
    xDimMenu = 0
    for i in screenState.menu:
        if len(i) > xDimMenu:
            xDimMenu = len(i)

    xMenu = int(width/2 - xDimMenu / 2)
    yMenu = int(height/2 - yDimMenu / 2)

    menu_select(stdscr, screenState.menu, screenState.selection, [yMenu, xMenu])

    # CUSTOM CHAR test, among them there is the little square and others
    stdscr.attron(curses.color_pair(1))
    stdscr.addstr(2, 4, u'\u1F973'.encode('utf-8'))
    stdscr.addstr(4, 4, u'\u2580'.encode('utf-8'))
    stdscr.addstr(4, 5, u'\u2584'.encode('utf-8'))
    stdscr.addstr(4, 6, u'\u2575'.encode('utf-8'))
    stdscr.addstr(4, 7, u'\u2577'.encode('utf-8'))
    stdscr.addstr(4, 8, u'\u2502'.encode('utf-8'))
    stdscr.addstr(4, 9, u'\u2502'.encode('utf-8'))
    stdscr.addstr(4, 9, u'\u2584'.encode('utf-8'))
    stdscr.addstr(4, 27, "the cube")
    stdscr.addstr(5, 4, u'\u2581'.encode('utf-8'))
    stdscr.addstr(6, 4, u'\u2582'.encode('utf-8'))
    stdscr.addstr(7, 4, u'\u2583'.encode('utf-8'))
    stdscr.addstr(8, 4, u'\u2585'.encode('utf-8'))
    stdscr.addstr(8, 7, "il cinque")
    stdscr.addstr(9, 4, u'\u25C0'.encode('utf-8'))
    stdscr.addstr(10, 4, u'\u26F3'.encode('utf-8'))
    stdscr.addstr(11, 4, u'\u26A1'.encode('utf-8'))
    stdscr.addstr(12, 4, u'\U0001F331'.encode('utf-8'))


def dex(stdscr, keyboardState, height, width):
    pass


def intro(stdscr, keyboardState, screenState, height, width):

    text = 'rototiller'
    textLength = len(text)
    x = (width - textLength) // 2
    y = height // 2

    stdscr.addstr(y, x, text)
    if keyboardState.enter:
        screenState.screen = "main"
        screenState.init = False


def wallet(stdscr, keyboardState, screenState, height, width):

    # select fingerprint
    if screenState.active_pk[0] == False:
        if not screenState.public_keys:
            try:
                fingerprints = asyncio.run(call_rpc_wallet('get_public_keys'))
                screenState.active_pk = (False, asyncio.run(call_rpc_wallet('get_logged_in_fingerprint')))
                for finger in fingerprints:
                    screenState.public_keys[finger] = PkState()
                    screenState.public_keys[finger].fingerprint = finger

            except Exception as e:
                stdscr.addstr(0, 0, "probably there is no chia node and wallet running")
                stdscr.addstr(1, 0, str(e))
                return

        fingers_str = []
        for fin in screenState.public_keys:
            if fin == screenState.active_pk[1]:
                fingers_str.append(str(fin) + ' >')
            else:
                fingers_str.append(str(fin))

        # if no chia node/wallet are active next step give an error
        # implent user message no node. Maybe finally is processed only if no exception arise select = select % len(screenState.public_keys)
        screenState.selection = screenState.selection % len(screenState.public_keys)
        menu_select(stdscr, fingers_str, screenState.selection, [10, 20])

        if keyboardState.enter:
            selected_wallet_fingerprint = list(screenState.public_keys.keys())[screenState.selection]
            if screenState.active_pk != selected_wallet_fingerprint:
                screenState.active_pk = (True, selected_wallet_fingerprint)
                screenState.selection = 0
                try:
                    print("trying log in")
                    fingers = asyncio.run(call_rpc_wallet('log_in', screenState.active_pk[1]))
                    print(fingers)
                except Exception as e:
                    stdscr.addstr(0, 0, "probably there is no chia node and wallet running. We are not logged in")
                    stdscr.addstr(1, 0, str(e))
            else:
                screenState.active_pk[0] = True

        if keyboardState.moveUp:
            screenState.selection -= 1
        if keyboardState.moveDown:
            screenState.selection += 1
        if keyboardState.esc is True:
            screenState.screen = 'main'
    else:
        # wallet
        pk = screenState.public_keys[screenState.active_pk[1]]
        wallets: Dict[int, WalletState] = pk.wallets

        if len(wallets) == 0:
            try:
                # add the chia wallet
                chia_wallet: WalletState  = WalletState()
                response = asyncio.run(call_rpc_wallet('get_wallet_balance', 1))
                chia_wallet.confirmed_wallet_balance = response['confirmed_wallet_balance']
                chia_wallet.spendable_balance = response['spendable_balance']
                chia_wallet.unspent_coin_count = response['unspent_coin_count']

                wallets[1] = chia_wallet
                print(chia_wallet)
                print('done')

                # add CAT
                cat_chia_wallets = asyncio.run(call_rpc_wallet('get_wallets', wallet_type=6))
                print('all')
                print(cat_chia_wallets)
                for e, i in enumerate(cat_chia_wallets):
                    cat_wallet = WalletState()
                    balance = asyncio.run(call_rpc_wallet('get_wallet_balance', i['id']))
                    cat_wallet.data = balance['asset_id']
                    cat_wallet.name = cat_names[cat_wallet.data][1]
                    cat_wallet.ticker = cat_names[cat_wallet.data][0]
                    cat_wallet.confirmed_wallet_balance = balance['confirmed_wallet_balance']
                    cat_wallet.spendable_balance = balance['spendable_balance']
                    cat_wallet.unspent_coin_count = balance['unspent_coin_count']
                    wallets[i['id']] = cat_wallet
                    # evaluate if it is better to use the byte32 name


            except Exception as e:
                stdscr.addstr(0, 0, "probably there is no chia node and chia_wallet running")
                stdscr.addstr(1, 0, str(e))

        chia_wallet = wallets[1]
        chia_wallet.block_height += 1

        stdscr.attron(curses.color_pair(1))
        stdscr.addstr(11, 10, 'WHAT>>>? Chia_Wallet: ' + str(screenState.active_pk))

        y = 13
        stdscr.addstr(y, 10, f"confirmed balance {chia_wallet.confirmed_wallet_balance}")
        y += 1
        stdscr.addstr(y, 10, f"spendable balance {chia_wallet.spendable_balance}")
        y += 1
        stdscr.addstr(y, 10, f"unspent coin count {chia_wallet.unspent_coin_count}")
        y += 1
        stdscr.addstr(y, 10, f"block height {chia_wallet.block_height}")

        if keyboardState.moveLeft:
            screenState.select_y -= 1
        if keyboardState.moveRight:
            screenState.select_y += 1

        print('keys')
        cat_wallet = wallets[list(wallets.keys())[screenState.select_y % len(wallets)]]
        y = 20
        stdscr.addstr(y, 10, f"Ticker: {cat_wallet.ticker} - {cat_wallet.name}")
        y += 1
        stdscr.addstr(y, 10, f"name {cat_wallet.confirmed_wallet_balance}")
        y += 1
        stdscr.addstr(y, 10, f"confirmed balance {cat_wallet.confirmed_wallet_balance}")
        y += 1
        stdscr.addstr(y, 10, f"spendable balance {cat_wallet.spendable_balance}")
        y += 1
        stdscr.addstr(y, 10, f"unspent coin count {cat_wallet.unspent_coin_count}")
        y += 1
        stdscr.addstr(y, 10, f"block height {cat_wallet.block_height}")

        if keyboardState.esc is True:
            screenState.active_pk = (False, screenState.active_pk[1])

        #    {'success': True, 'chia_wallet_balance': {'confirmed_wallet_balance': 130, 'fingerprint': 291595168, 'max_send_amount': 130, 'pending_change': 0, 'pending_coin_removal_count': 0,
        #                                         'spendable_balance': 130, 'unconfirmed_chia_wallet_balance': 130, 'unspent_coin_count': 3, 'wallet_id': 1, 'wallet_type': 0}

# idea about firsts screen
# intro
# main menu
# wallet
# dex
# tibet
# mempool
# node

screenGenerators = {
    'intro': intro,
    'main': main_menu,
    'wallet': wallet,
    'dex': dex
}



def interFace(stdscr):

    data_lock = threading.Lock()
    fingers_state: List[FingerState] = []
    fingers_list: List[int] = []
    count_server = [0]

    wallet_thread = threading.Thread(target=fetch_wallet,
                                     args=(data_lock,
                                           fingers_state,
                                           fingers_list,
                                           count_server),
                                     daemon=True)
    wallet_thread.start()


    key = 0

    stdscr.nodelay(True)
    stdscr.erase()
    stdscr.refresh()
    # trying to stop print
    # curses.noecho()
    # curses.cbreak()

    screenState = ScreenState()

    # Start colors in curses
    curses.start_color()
    curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_CYAN)
    curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_RED)

    begin_x = 38; begin_y = 40
    height = 50; width = 20
    # win = curses.newwin(height, width, begin_y, begin_x)
    while True:
        # intro
        pass
        break

    while key != ord('q'):
        stdscr.erase()
        keyboardState = KeyboardState()

        height, width = stdscr.getmaxyx()
        windowDim = f"height={height}; width={width}"
        header = stdscr.subwin(1, width, 0,0)
        header.bkgd(' ', curses.color_pair(3))
        # y, x = 0, width - len(windowDim)
        # header.addstr(y, x, windowDim, curses.color_pair(3)) # it is not possible to write on the last char of a window
        header.addstr(0, 0, "rototiller", curses.color_pair(3))
        # write on the right but not in the window, but on the main screen
        y, x = 0, width - len(windowDim)
        stdscr.addstr(y, x, windowDim, curses.color_pair(3))

        footerText = "Movement: down=j up=k left=h right=l confirm=enter back=esc q=quit"
        nLines = int(len(footerText) / width + 1)
        footer = stdscr.subwin(nLines, width, height-nLines, 0)
        footer.bkgd(' ', curses.color_pair(3))
        footer.addstr(0, 0, footerText, curses.color_pair(3))

        # debug footer
        footerTextDebug = f"server count: {count_server[0]}"
        if len(fingers_list) >= 1:
            footerTextDebug += f", finger 0: {fingers_list[0]}"
        if len(fingers_list) >= 2:
            footerTextDebug += f" finger 1: {fingers_list[1]}"
        if len(fingers_list) >= 2:
            footerTextDebug += f" numbers of wallets [0]: {len(fingers_state[0].wallets)}"
            footerTextDebug += f" numbers of wallets [1]: {len(fingers_state[1].wallets)}"
        nLinesDebug = 2
        footerDebug = stdscr.subwin(nLinesDebug, width, height-nLines-nLinesDebug, 0)
        footerDebug.bkgd(' ', curses.color_pair(3))
        footerDebug.addstr(0, 0, footerTextDebug, curses.color_pair(3))


        # keyboard
        if key == ord('j'):
            keyboardState.moveDown = True

        if key == ord('k'):
            keyboardState.moveUp = True

        if key == ord('h'):
            keyboardState.moveLeft = True

        if key == ord('l'):
            keyboardState.moveRight = True

        if key == curses.KEY_ENTER or key == 10 or key == 13:
            keyboardState.enter = True

        if key == 27:
            keyboardState.esc = True
            print('brrruu    ')

        # Turning on attributes for title
        stdscr.attron(curses.A_BOLD)

        print(time.time())
        print(screenState.screen)
        print()
        screenGenerators[screenState.screen](stdscr, keyboardState, screenState, height, width)
        # main_menu(stdscr, key, select, menu, height, width)

        # html tables: https://www.w3.org/TR/xml-entity-names/026.html

        curses.doupdate()
        time.sleep(30/1000)
        # stdscr.refresh()
        key = stdscr.getch()


async def get_wallet(coin_id: str):
    try:
        full_node_client = await FullNodeRpcClient.create(
                self_hostname, uint16(full_node_rpc_port), DEFAULT_ROOT_PATH, config)
        coin_record = await full_node_client.get_coin_record_by_name(bytes32.fromhex(coin_id))
        print(coin_record)
        return coin_record.coin
    finally:
        full_node_client.close()
        await full_node_client.await_closed()


async def get_public_keys():
    try:
        wallet_client = await WalletRpcClient.create(
            self_hostname, uint16(wallet_rpc_port), DEFAULT_ROOT_PATH, config
        )
        response = await wallet_client.get_public_keys()
        return response

    finally:
        wallet_client.close()
        await wallet_client.await_closed()


async def get_logged_in_fingerprint():
    try:
        wallet_client = await WalletRpcClient.create(
            self_hostname, uint16(wallet_rpc_port), DEFAULT_ROOT_PATH, config
        )
        response = await wallet_client.get_logged_in_fingerprint()
        return response

    finally:
        wallet_client.close()
        await wallet_client.await_closed()


async def log_in(fingerprint):
    try:
        wallet_client = await WalletRpcClient.create(
            self_hostname, uint16(wallet_rpc_port), DEFAULT_ROOT_PATH, config
        )
        response = await wallet_client.log_in(fingerprint)
        return response

    finally:
        wallet_client.close()
        await wallet_client.await_closed()


async def call_rpc_wallet(method_name, *args, **kwargs):
    try:
        wallet_client = await WalletRpcClient.create(
            self_hostname, uint16(wallet_rpc_port), DEFAULT_ROOT_PATH, config
        )
        rpc_method = getattr(wallet_client, method_name)
        response = await rpc_method(*args, **kwargs)
        return response

    finally:
        wallet_client.close()
        await wallet_client.await_closed()


class StdOutWrapper:
    text = ""

    def write(self, txt):
        self.text += txt
        self.text = '\n'.join(self.text.split('\n')[-300:])

    def get_text(self,beg=0,end=-1):
        """I think it is reversed the order, i should change it"""
        return '\n'.join(self.text.split('\n')[beg:end]) + '\n'

if __name__ == "__main__":

    screen = curses.initscr()
    curses.noecho()
    curses.cbreak()

    # do your stuff here
    # you can also output mystdout.get_text() in a ncurses widget in runtime

    screen.keypad(0)
    curses.nocbreak()
    curses.echo()
    curses.endwin()


def main():

    # start curses
    curses.wrapper(interFace)


if __name__ == "__main__":

    mystdout = StdOutWrapper()
    sys.stdout = mystdout
    sys.stderr = mystdout

    try:
        main()
    except Exception as e:
        screen.keypad(0)
        curses.nocbreak()
        curses.echo()
        curses.endwin()
        print("The exception of main is: ", e)
        print(traceback.format_exc())

    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__
    sys.stdout.write(mystdout.get_text())
