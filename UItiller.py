#!/usr/bin/env python3

import sys, os, traceback
import asyncio
import curses
import time
import threading
import requests
import json
from pathlib import Path
import sqlite3
import csv
from collections import deque

from dataclasses import dataclass
from typing import List, Tuple, Dict, Union, Callable
from datetime import datetime, timedelta

#from chia.wallet.util.tx_config import DEFAULT_TX_CONFIG

from chia.rpc.full_node_rpc_client import FullNodeRpcClient
from chia.rpc.rpc_server import RpcServer
from chia.rpc.wallet_rpc_client import WalletRpcClient
from chia.daemon.client import connect_to_daemon_and_validate
from chia.types.blockchain_format.sized_bytes import bytes32, bytes48
from chia.util.ints import uint16, uint32, uint64

import UItext as UItext
import UIgraph as UIgraph
import LOGtiller as LOGtiller
from CONFtiller import (
    server_logger, ui_logger, logging, ScopeMode, DEBUGGING, DB_WDB, SQL_TIMEOUT,
    XCH_FAKETAIL, BTC_FAKETAIL, XCH_CUR, USD_CUR, XCH_MOJO, CAT_MOJO,
    config, self_hostname, full_node_rpc_port, wallet_rpc_port,
    DEFAULT_ROOT_PATH)
import DEBUGtiller as DEBUGtiller
import ELEMENTStiller as ELEMENTS
import WDBtiller as WDB
import DEXtiller as DEX
from RPCtiller import call_rpc_node, call_rpc_daemon
from UTILITYtiller import binary_search_l


#### global for debugging
DEBUG_OBJ = DEBUGtiller.DEBUG_OBJ
DEBUG_TEXT = 'mempty'

#### NCURSES CONFIG #####
# set the esc delay to 25 milliseconds
# by default curses use one seconds
os.environ.setdefault('ESCDELAY', '25')


### only for block states testing
BLOCK_STATES = None

# dexi api
def loadAllTickers():
    r = requests.get('https://api.dexie.space/v2/prices/tickers')
    tickers = json.loads(r.text)["tickers"]
    return tickers


# store elements
cat_test = {
    "a628c1c2c6fcb74d53746157e438e108eab5c0bb3e5c80ff9b1910b3e4832913":
    ("SBX", "Spacebucks"),
    "db1a9020d48d9d4ad22631b66ab4b9ebd3637ef7758ad38881348c5d24c38f20":
    ("DBX", "dexie bucks"),
    "e0005928763a7253a9c443d76837bdfab312382fc47cab85dad00be23ae4e82f":
    ("MBX", "Moonbucks"),
    "b8edcc6a7cf3738a3806fdbadb1bbcfc2540ec37f6732ab3a6a4bbcd2dbec105":
    ("MZ", "Monkeyzoo Token"),
    "e816ee18ce2337c4128449bc539fbbe2ecfdd2098c4e7cab4667e223c3bdc23d":
    ("HOA", "HOA COIN"),
    "ccda69ff6c44d687994efdbee30689be51d2347f739287ab4bb7b52344f8bf1d":
    ("BEPE", "BEPE"),
    "8ebf855de6eb146db5602f0456d2f0cbe750d57f821b6f91a8592ee9f1d4cf31":
    ("MRMT", "Marmot Coin"),
    "fa4a180ac326e67ea289b869e3448256f6af05721f7cf934cb9901baa6b7a99d":
    ("wUSDC.b", "Base warp.green USDC"),
    "e233f9c0ebc092f083aaacf6295402ed0a0bb1f9acb1b56500d8a4f5a5e4c957":
    ("MWIF", "MWIF"),
    "d1adf97f603cdec4998a63eb8ffdd19480a60e20751c8ec8386283b1d86bf3f9":
    ("MOG", "MOG"),
    "4cb15a8ecc85068fb1f98c09a5e489d1ad61b2af79690ce00f9fc4803c8b597f":
    ("wmilliETH", "Ethereum warp.green milliETH"),
    "70010d83542594dd44314efbae75d82b3d9ae7d946921ed981a6cd08f0549e50":
    ("LOVE", "LOVE"),
    "a66ce97b58a748b3bb2a8224713620cca0ca00cb87e75837b1f04e3a543aaa40":
    ("BANANA", "BANANA"),
    "ec9d874e152e888231024c72e391fc484e8b6a1cf744430a322a0544e207bf46":
    ("PEPE", "PepeCoin"),
    "ea830317f831a23b178aa653e50484568d30d2c5b34d8140e71247ead05961c7":
    ("CC", "Caesar Coin"),
    "b0495abe70851d43d8444f785daa4fb2aaa8dae6312d596ee318d2b5834cc987":
    ("DBW", "DBW"),
    "509deafe3cd8bbfbb9ccce1d930e3d7b57b40c964fa33379b18d628175eb7a8f":
    ("CH21", "Chia Holiday 2021")
}

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
class TransactionRecordRoto:
    confirmed_at_height: uint32
    created_at_time: uint64
    to_puzzle_hash: bytes32
    amount: uint64
    fee_amount: uint64
    confirmed: bool
    ###sent: uint32
    ###spend_bundle: Optional[SpendBundle]
    ###additions: List[Coin]
    ###removals: List[Coin]
    ###wallet_id: uint32

    # Represents the list of peers that we sent the transaction to, whether each one
    # included it in the mempool, and what the error message (if any) was
    ###sent_to: List[Tuple[str, uint8, Optional[str]]]
    trade_id: bytes32 #Optional[bytes32]
    type: uint32  # TransactionType

    # name is also called bundle_id and tx_id
    name: bytes32
    ###memos: List[Tuple[bytes32, List[bytes]]]

# Transaction type
TRANSACTION_TYPE_DESCRIPTIONS = [
    "received",
    "sent",
    "rewarded (coinbase)",
    "rewarded (fee)",
    "received in trade",
    "sent in trade",
    "received in clawback as recipient",
    "received in clawback as sender",
    "claim/clawback",
]

TRANSACTION_TYPE_SIGN = [
    1,
    -1,
    1,
    1,
    1,
    -1,
    1,
    1,
    1,
]


@dataclass
class WalletState:
    data: str  # it should be byte32 (the data of what?)
    name: str  #
    ticker: str  #
    block_height: uint32
    addresses: List[str]  # check type and move to pkState
    coins: List  # coinrecords, but it could be also coins
    transactions: List[TransactionRecordRoto]
    confirmed_wallet_balance: uint64  # check type
    spendable_balance: uint64  # check type
    unspent_coin_count: int  # check type

    def __init__(self):
        self.data = ""
        self.name = ""
        self.ticker = ""
        self.block_height = 0
        self.addresses = []
        self.coins = []
        self.transactions = []
        self.confirmed_wallet_balance = 0
        self.spendable_balance = 0
        self.unspent_coin_count = 0


@dataclass
class CoinPriceData:
    coin_tail: str  # for chia is "chia"
    local_timestamp: int  # timestamp milliseconds
    current_price: float
    current_price_currency: float
    current_price_date: int  # timestamp milliseconds
    historic_price: Dict[int, float]  # [timestamp, price]
    historic_price_currency: Dict[int, float]  # [timestamp, price]
    historic_range_price_data: Tuple[int, int]  # [timestamp (begin period), timestamp (end period)]

    def __init__(self):
        self.coin_tail = None
        self.local_timestamp = None
        self.current_price = None
        self.current_price_currency = None
        self.current_price_date = None
        self.historic_price = None
        self.historic_price_currency = {}
        self.historic_range_price_data = {}


@dataclass
class FingerState:
    fingerprint: int
    label: str
    public_key: uint64
    wallets: List[WalletState]

    def __init__(self):
        self.fingerprint = 0
        self.label = ""
        self.public_key = 0
        self.wallet = []


@dataclass
class PkState:
    fingerprint: int
    label: str
    pk: uint64
    wallets: Dict[int, WalletState]

    def __init__(self):
        self.fingerprint = 0
        self.label = ""
        self.pk = 0
        self.wallets = {}


# UI elements
@dataclass
class KeyboardState:
    moveUp: bool = False
    moveDown: bool = False
    moveLeft: bool = False
    moveRight: bool = False
    yank: bool = False
    paste: bool = False
    mouse: bool = False
    enter: bool = False
    esc: bool = False


@dataclass
class ScreenState:
    init: bool
    screen_size: UIgraph.Point
    selection: int  # delete?
    select_y: int  # delete?
    screen: str  # delete?
    cursesColors: UIgraph.CustomColors
    colors: Dict[str, int]
    colorPairs: Dict[str, int]
    menu: List[str]
    nLinesUsed: int
    headerLines: int
    footerLines: int
    active_pk: List[Union[int, bool]]  # [is fing selected, fingerprint] TODO: make it only fingerprint without bool
    public_keys: Dict[int, PkState]  # check what kind of int is a pk, and change wallets to something that belond to a public key
    activeScope: 'Scope'  # active scope
    scopes: Dict[str, 'Scope']
    scope_exec_args: List  # args that are used when executing scope.exec_child
    screen_data: Dict[str, str]  # it should be a dic of lists of anything
    coins_data: Dict[str, CoinPriceData]
    roto_clipboard: deque

    def __init__(self):
        self.init = False
        self.screen_size = None
        self.selection = 0
        self.select_y = 0
        self.screen = 'intro'  # da eliminare TODO
        self.cursesColors = None
        self.colors = {}
        self.colorPairs = {}
        self.menu = []
        self.headerLines = 0
        self.footerLines = 0
        self.active_pk = (0, False)
        self.public_keys = {}
        self.activeScope = None
        self.scopes = {}
        self.scope_exec_args = []
        self.screen_data = {}
        self.coins_data = {}

        # init copy
        self.roto_clipboard = deque(maxlen=5)
        self.scopes['copy'] = None
        self.scopes['paste'] = None


class Scope():
    gen_id = 0

    def __init__(self, name: str, screen_handler: Callable[..., None],
                 screenState: ScreenState):
        self.name = name
        self.selected = False
        self.mode = ScopeMode.VISUAL
        self.parent_scope = None
        self.main_scope = self
        self.sub_scopes = {}
        self.cursor = 0
        self.cursor_x = 0
        self.bool = False  # eel bool de che?
        self.data = {}  # is it a good place here. Or should i use screenState
        self.id = Scope.gen_id
        self.exec = None  # funcion executed when activated
        self.exec_own = None  # to rename to exec
        self.exec_init = None  # to swapp with .exec
        self.exec_esc = None  # used when exiting
        self.screen = screen_handler
        # add the variable that keep the info of what screen to print
        Scope.gen_id += 1
        screenState.scopes[name] = self
        # default esc behaviuor
        self.exec_esc = exit_scope

    ### consider to move this logic in each elements, should be more flexible
    def update(self):
        """Update the counter using the number of sub scopes"""
        for key, item in self.sub_scopes.items():
            item.selected = False
        if len(self.sub_scopes) != 0:
            self.cursor = self.cursor % len(self.sub_scopes)
            sel_scope = list(self.sub_scopes.keys())[self.cursor]
            self.sub_scopes[sel_scope].selected = True

    def update_no_sub(self, row_count, circular=True):
        """Update the counter using an arbitrary number: row_count"""
        if row_count == 0:
            pass
        else:
            if circular:
                self.cursor = self.cursor % row_count
            else:
                if self.cursor < 0:
                    self.cursor = 0
                elif self.cursor >= row_count:
                    self.cursor = row_count - 1

    # ONGOING change.........
    # exec_child is not right as name, better exec_when pressed, if there are
    # child the child is executed, if there are no child the own is executed
    # AND
    # need 2 exec function:
    # INIT -> create the scope (exec)
    # EXEC -> execute if needed (exec_own)
    # AND
    # create a new method to execute both INIT and EXEC
    def exec_child(self, *args):
        if len(self.sub_scopes) > 0:
            idx = self.cursor % len(self.sub_scopes)  # i could delete the modulus
            # on the scope part? we need this when the child scope are less then
            # the element you can navigate in the same scope
            child_scope_key = list(self.sub_scopes.keys())[idx]
            child_scope = self.sub_scopes[child_scope_key]
            child_scope.exec_self(*args)
        else:
            self.exec_own(self, *args)

    # we can delete this method i think... when we refactor the exec_own exec_init
    def exec_self(self, *args):
        """Execute the function stored in the self.exec"""
        self.exec(self, *args)


#### Scope executions for exec
def activate_scope(scope: Scope, screenState: ScreenState):
    screenState.activeScope = scope
    return scope


def activate_pk(scope: Scope, screenState: ScreenState):
    """Acvtivate the scope and set the active pk in the ScreenState"""
    screenState.activeScope = scope
    return scope


def activate_grandparent_scope(scope: Scope, screenState: ScreenState):
    screenState.activeScope = scope.parent_scope.parent_scope
    return scope.parent_scope.parent_scope


def get_N_scope(scope: Scope, screenState):
    scope.active = False
    active_scope_key = list(scope.sub_scopes.keys())[scope.cursor]

    new_scope = scope.sub_scopes[active_scope_key]
    new_scope.active = True
    return new_scope


def activate_scope_and_set_pk(scope: Scope, screenState):
    """Activate both active and main scope and set the active finger"""
    screenState.activeScope = scope
    screenState.active_pk[0] = int(scope.name)  # Maibe use the possibility to
    # change the args input of the scope exec
    return scope


# used to open a coin view from a tab
def open_coin_wallet(scope: Scope, screenState: ScreenState, tail):
    new_name = f"{scope.parent_scope.name}_{tail}"
    new_scope = Scope(new_name, screen_coin_wallet, screenState)
    new_scope.parent_scope = scope.parent_scope
    new_scope.data['tail'] = tail
    new_scope.exec = None
    screenState.activeScope = new_scope
    return new_scope


def exit_scope(scope: Scope, screen_state: ScreenState, *args):
    if scope.parent_scope:
        screen_state.activeScope = scope.parent_scope
        return scope.parent_scope

# to remove it as global
tickers = 0


def convert_ts_to_date(ts):
    """Convert a timestamp to a date, with ts in milliseconds"""
    return datetime.fromtimestamp(ts/1000).strftime('%Y-%m-%d %H:%M:%S')


def write_prices(name, prices):
    name += '.csv'
    with open(name, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(['timestamps', 'value'])
        writer.writerows([[convert_ts_to_date(key), value] for key, value in prices.items()])


def convert_historic_price_to_currency(historic_timestamp_ref_coin, historic_price_ref_coin,
                                       historic_timestamp_target_coin, historic_price_target_coin,
                                       invert_target_coin=False):
    """Convert historic price of a pair using another pair with a coin in common.
    EG:
    ref_coin= BTC_USD
    target_coin = XCH_USD
    convert the the XCH_USD pair to XCH_BTC
    """

    # TODO: set a threshold for the time diff, for which, if exceeded discard the data
    # TODO: use bisect instead of the while to find the best insertion point

    len_ref_coin_ts = len(historic_timestamp_ref_coin)
    u = 0
    new_historic_price_target_coin = []
    new_timestamps = []
    for n, i in enumerate(historic_timestamp_target_coin):
        #diff = abs(i - historic_timestamp_ref_coin[u])
        #while u < (len_ref_coin_ts - 1):
        #    next_diff = abs(i - historic_timestamp_ref_coin[u + 1])
        #    if next_diff >= diff:
        #        break
        #    u += 1

        u = binary_search_l(historic_timestamp_ref_coin, i)
        if u >= len_ref_coin_ts - 1:
            u = len_ref_coin_ts - 1
        elif abs(i - historic_timestamp_ref_coin[u]) < abs(i - historic_timestamp_ref_coin[u + 1]):
            pass
        else:
            u += 1

        price_ref_coin = historic_price_ref_coin[u]
        if invert_target_coin:
            price_ref_coin = 1 / historic_price_ref_coin[u]

        new_historic_price_target_coin.append(historic_price_target_coin[n] * price_ref_coin)
        new_timestamps.append(historic_timestamp_target_coin[n])

    return dict(zip(new_timestamps, new_historic_price_target_coin))


def convert_historic_price_to_currency_DEB(historic_timestamp_ref_coin, historic_price_ref_coin,
                                           historic_timestamp_target_coin, historic_price_target_coin,
                                           invert_target_coin=False, name="memento"):
    """Convert historic price of a pair using another pair with a coin in common.
    EG:
    ref_coin= BTC_USD
    target_coin = XCH_USD
    convert the the XCH_USD pair to XCH_BTC
    """

    # TODO: set a threshold for the time diff, for which, if exceeded discard the data
    # TODO: use bisect instead of the while to find the best insertion point

    len_ref_coin_ts = len(historic_timestamp_ref_coin)
    u = 0
    new_historic_price_target_coin = []
    new_timestamps = []
    name += '.csv'
    with open(name, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(['target', 'target', 'ref', 'ref', 'ref', 'calculated'])
        writer.writerow(['date', 'price', 'date', 'price', 'original price', 'calculated price'])
        for n, i in enumerate(historic_timestamp_target_coin):
            u = binary_search_l(historic_timestamp_ref_coin, i)
            if u >= len_ref_coin_ts - 1:
                u = len_ref_coin_ts - 1
            elif abs(i - historic_timestamp_ref_coin[u]) < abs(i - historic_timestamp_ref_coin[u + 1]):
                pass
            else:
                u += 1

            price_ref_coin = historic_price_ref_coin[u]
            if invert_target_coin:
                price_ref_coin = 1 / historic_price_ref_coin[u]

            new_historic_price_target_coin.append(historic_price_target_coin[n] * price_ref_coin)
            new_timestamps.append(historic_timestamp_target_coin[n])
            the_row = [convert_ts_to_date(historic_timestamp_target_coin[n]), historic_price_target_coin[n], convert_ts_to_date(historic_timestamp_ref_coin[u]), price_ref_coin, historic_price_ref_coin[u], historic_price_target_coin[n] * price_ref_coin]
            writer.writerow(the_row)

        writer.writerow([])
        ts = [[convert_ts_to_date(i), 'empty'] for i in historic_timestamp_ref_coin]

        writer.writerows(ts)

    return dict(zip(new_timestamps, new_historic_price_target_coin))


# fetch coin data
def fetch_coin_data(data_lock, coins_data, tail):
    "fetch data for a coin"

    logging(server_logger, "DEBUG", f"fetching CAT's data with tail: {tail}")

    try:

        if tail in coins_data:
            last_update = coins_data[tail].local_timestamp
            if not last_update:
                last_update = 0
            diff = datetime.now().timestamp() * 1000 - last_update
            if diff < (60 * 1000):
                logging(server_logger, "DEBUG", f"fetching CAT's data with tail: {tail}, already recorded")
                return

        current_price = DEX.get_current_price_from_tail(tail)
        historic_price, historic_timestamp = DEX.getHistoricPriceFromTail(tail, 7)
        end = datetime.now()
        begin = int((end - timedelta(days=7)).timestamp())
        conn = sqlite3.connect(DB_WDB, timeout=SQL_TIMEOUT)

        for price, ts in zip(historic_price, historic_timestamp):
            WDB.insert_price(conn, tail, ts, price, XCH_CUR)
        conn.close()

        if len(historic_price) == 0:
            historic_price.append(current_price)
            historic_timestamp.append(int(datetime.now().timestamp() * 1000))

        with data_lock:
            if tail not in coins_data:
                coins_data[tail] = CoinPriceData()
                coins_data[tail].tail = tail
            current_price_chia = coins_data[XCH_FAKETAIL].current_price_currency
            historic_timestamp_chia = list(coins_data[XCH_FAKETAIL].historic_price_currency.keys())
            historic_price_chia = list(coins_data[XCH_FAKETAIL].historic_price_currency.values())

            coins_data[tail].local_timestamp = datetime.now().timestamp() * 1000
            coins_data[tail].current_price = current_price
            coins_data[tail].current_price_currency = current_price * current_price_chia
            coins_data[tail].current_price_date = int(datetime.now().timestamp() * 1000)
            coins_data[tail].historic_price = dict(zip(historic_timestamp, historic_price))


            # DEBUGGING PRICES XCH
            #try:
            #    write_prices(f"{tail}-XCH", coins_data[tail].historic_price)
            #except Exception as e:
            #    print("type of var: ", type(coins_data[tail].historic_price))
            #    print(e)
            #    traceback.print_exc()

            historic_price_currency = convert_historic_price_to_currency(
                historic_timestamp_chia, historic_price_chia,
                historic_timestamp, historic_price)
            ### DEBUG BY SAVING THE CONVERSION
            #historic_price_currency = convert_historic_price_to_currency_DEB(
            #    historic_timestamp_chia, historic_price_chia,
            #    historic_timestamp, historic_price, name=f"DEB_{tail}")

            # DEBUGGING PRICES USD
            #try:
            #    write_prices(f"{tail}-USD", historic_price_currency)
            #except Exception as e:
            #    print("type of var: ", type(historic_price_currency))
            #    print(e)
            #    traceback.print_exc()

            coins_data[tail].historic_price_currency = historic_price_currency
            coins_data[tail].historic_range_price_data = (begin, end)

    except Exception as e:
        logging(server_logger, "DEBUG", f"fetching coindata error {tail}")
        logging(server_logger, "DEBUG", f"Balance error. Exception: {e}")
        logging(server_logger, "DEBUG", f"Traceback: {traceback.format_exc()}")
        traceback.print_exc()


def fetch_btc_data(data_lock, coins_data):
    "fetch btc price"
    logging(server_logger, "DEBUG", "fetching btc's price")

    with data_lock:
        if BTC_FAKETAIL in coins_data:
            last_update = coins_data[BTC_FAKETAIL].local_timestamp
            if not last_update:
                last_update = 0
            diff = datetime.now().timestamp() * 1000 - last_update
            if diff < (60 * 1000):
                logging(server_logger, "DEBUG", "fetching btc's data: already in")
                return

        # retrive last 7 days
        currency = 'usd'
        days = '7'
        btc_cg_id = 'bitcoin'

        # Construct the API URL
        url = f"https://api.coingecko.com/api/v3/coins/{btc_cg_id}/market_chart?vs_currency={currency}&days={days}"

        # Send the request to CoinGecko API
        response = requests.get(url)

        # Parse the JSON response
        data = response.json()

        # Extract relevant information (e.g., prices over the last 7 days)
        prices = data['prices']
        current_price = prices[-1]
        historic_timestamp = []
        historic_price = []
        conn = sqlite3.connect(DB_WDB, timeout=SQL_TIMEOUT)
        for i in prices:
            ts = i[0]
            p = i[1]
            historic_timestamp.append(ts)
            historic_price.append(p)
            # save on the DB
            WDB.insert_price(conn, BTC_FAKETAIL, ts, p, USD_CUR)
        conn.close()

        if BTC_FAKETAIL not in coins_data:
            coins_data[BTC_FAKETAIL] = CoinPriceData()
            coins_data[BTC_FAKETAIL].tail = BTC_FAKETAIL

        coins_data[BTC_FAKETAIL].local_timestamp = datetime.now().timestamp() * 1000
        coins_data[BTC_FAKETAIL].current_price = 1
        coins_data[BTC_FAKETAIL].current_price_currency = current_price[1]
        coins_data[BTC_FAKETAIL].current_price_date = current_price[0]
        coins_data[BTC_FAKETAIL].historic_price = dict(zip(historic_timestamp,
                                                       [1] * len(historic_price)))
        coins_data[BTC_FAKETAIL].historic_price_currency = dict(zip(historic_timestamp,
                                                                historic_price))
        end = datetime.now()
        begin = int((end - timedelta(days=7)).timestamp())
        coins_data[BTC_FAKETAIL].historic_range_price_data = (begin, end)


def fetch_chia_data(data_lock, coins_data):
    "fetch data for a coin"

    logging(server_logger, "DEBUG", "fetching chia's data")

    try:
        # lock now to be sure chia is the first entry and it is available for later entries
        with data_lock:

            chia_id = XCH_FAKETAIL

            if chia_id in coins_data:
                last_update = coins_data[chia_id].local_timestamp
                diff = datetime.now().timestamp() * 1000 - last_update
                if diff < (60 * 1000):
                    logging(server_logger, "DEBUG", "fetching chia's data: already in")
                    return

            # retrive last 7 days
            currency = 'usd'
            days = '7'
            chia_cg_id = 'chia'

            # Construct the API URL
            url = f"https://api.coingecko.com/api/v3/coins/{chia_cg_id}/market_chart?vs_currency={currency}&days={days}"

            # Send the request to CoinGecko API
            response = requests.get(url)

            # Parse the JSON response
            data = response.json()

            # Extract relevant information (e.g., prices over the last 7 days)
            prices = data['prices']
            current_price = prices[-1]
            historic_timestamp = []
            historic_price = []
            conn = sqlite3.connect(DB_WDB, timeout=SQL_TIMEOUT)
            for i in prices:
                ts = i[0]
                p = i[1]
                historic_timestamp.append(ts)
                historic_price.append(p)
                # save on the DB
                WDB.insert_price(conn, XCH_FAKETAIL, ts, p, USD_CUR)
            conn.close()

            if chia_id not in coins_data:
                coins_data[chia_id] = CoinPriceData()
                coins_data[chia_id].tail = chia_id

            coins_data[chia_id].local_timestamp = datetime.now().timestamp() * 1000
            coins_data[chia_id].current_price = 1
            coins_data[chia_id].current_price_currency = current_price[1]
            coins_data[chia_id].current_price_date = current_price[0]
            coins_data[chia_id].historic_price = dict(zip(historic_timestamp,
                                                          [1] * len(historic_price)))
            coins_data[chia_id].historic_price_currency = dict(zip(historic_timestamp,
                                                                   historic_price))
            end = datetime.now()
            begin = int((end - timedelta(days=7)).timestamp())
            coins_data[chia_id].historic_range_price_data = (begin, end)

    except Exception as e:
        logging(server_logger, "DEBUG", f"fetching chia coindata error from coin geko")
        logging(server_logger, "DEBUG", f"Balance error. Exception: {e}")
        logging(server_logger, "DEBUG", f"Traceback: {traceback.format_exc()}")
        traceback.print_exc()


def fetch_addresses(data_lock, fingerprint: int, pk_state_id: int):
    """Fetch addresses for each fingerprints until the last FREE_ADD addresses are unused"""
    ### to implement the logic to load until last unused
    conn = sqlite3.connect(DB_WDB, timeout=SQL_TIMEOUT)
    non_observer = False
    logging(server_logger, "DEBUG", "fetching addresses from daemon")
    response = call_rpc_daemon("get_wallet_addresses", fingerprints=[fingerprint], index=0, count=1000, non_observer_derivation=non_observer)
    adds = response[str(fingerprint)]
    # pk_state_id = WDB.retrive_pk(conn, fingerprint)[0]

    for a in adds:
        WDB.insert_address(conn, pk_state_id, a['hd_path'], a['address'], non_observer)
        logging(server_logger, "DEBUG", f"added adx with path {a['hd_path']} of finger: {fingerprint} to the db")


def load_WDB_data(conn, fingers_state, fingers_list, coins_data, finger_active):
    """Load all wallet and asset data from the db"""
    #### laod key ####
    pk_states = WDB.retrive_all_pks(conn)

    for state in pk_states:
        new_pk = PkState()
        new_pk.fingerprint = state['fingerprint']
        new_pk.pk = state['public_key']
        new_pk.label = state["label"]
        fingers_list.append(new_pk.fingerprint)
        fingers_state.append(new_pk)

    #### load wallets ####

    for finger in fingers_list:

        pk_state_id = WDB.retrive_pk(conn, finger)[0]
        logging(server_logger, "DEBUG", f"finger {finger}")
        idx = fingers_list.index(finger)
        wallets = fingers_state[idx].wallets

        db_wallets = WDB.retrive_wallets_by_pk_state_id(conn, pk_state_id)

        for db_w in db_wallets:
            tail = db_w['tail']
            mojo = CAT_MOJO
            if tail == XCH_FAKETAIL:
                mojo = XCH_MOJO
            wallet: WalletState = WalletState()
            wallet.confirmed_wallet_balance = db_w['confirmed_wallet_balance'] / mojo
            wallet.spendable_balance = db_w['spendable_balance'] / mojo
            wallet.unspent_coin_count = db_w['unspent_coin_count']
            # load asset data
            asset = WDB.retrive_asset(conn, tail)
            if asset:
                wallet.name = asset['name']
                wallet.ticker = asset['ticker']
                wallets[tail] = wallet

            #### load used tails ####
            if tail not in coins_data:
                coins_data[tail] = CoinPriceData()
                coins_data[tail].tail = tail


        # load btc prices
        tail = BTC_FAKETAIL
        coins_data[tail] = CoinPriceData()
        coins_data[tail].tail = tail
        prices = WDB.retrive_price_tail_currency(conn, tail, USD_CUR)
        if prices:
            prices = sorted(prices, key=lambda x: x[0])
            last_prices = prices[0]
            coins_data[tail].local_timestamp = last_prices[0]
            coins_data[tail].current_price_currency = last_prices[2]
            coins_data[tail].historic_price_currency = {
                timestamp: price for timestamp, _, price, _ in prices}

        # load chia prices
        tail = XCH_FAKETAIL
        prices = WDB.retrive_price_tail_currency(conn, tail, USD_CUR)
        if prices:
            prices = sorted(prices, key=lambda x: x[0])
            last_prices = prices[0]
            coins_data[tail].local_timestamp = last_prices[0]
            coins_data[tail].current_price_currency = last_prices[2]
            coins_data[tail].historic_price_currency = {
                timestamp: price for timestamp, _, price, _ in prices}

            timestamp_price_chia = last_prices[0]
            current_price_chia = last_prices[2]
            historic_timestamp_chia = list(coins_data[tail].historic_price_currency.keys())
            historic_price_chia = list(coins_data[tail].historic_price_currency.values())


        # laod CAT price data
        fifteen_minutes = 15 * 60  # CONST for limit price convertion from XCH to currency
        for tail in coins_data:
            if tail == XCH_FAKETAIL or BTC_FAKETAIL:
                continue

            # retrive CAT price in XCH
            prices = WDB.retrive_price_tail_currency(conn, tail, XCH_CUR)
            if not prices:
                continue
            prices = sorted(prices, key=lambda x: x[0])
            last_prices = prices[0]
            coins_data[tail].local_timestamp = last_prices[0]
            coins_data[tail].current_price = last_prices[2]
            #coins_data[tail].historic_price = {}
            #for p in prices:
            #    coins_data[tail].historic_price[p[0]] = p[2]
            coins_data[tail].historic_price = {
                timestamp: price for timestamp, _, price, _ in prices}

            # here i should use the convert_historic_price_to_currency function
            if abs(timestamp_price_chia - coins_data[tail].local_timestamp) > fifteen_minutes:
                coins_data[tail].current_price_currency = coins_data[tail].current_price * current_price_chia
                coins_data[tail].current_price_date = timestamp_price_chia

            historic_timestamp = list(coins_data[tail].historic_price.keys())
            historic_price = list(coins_data[tail].historic_price.values())
            historic_price_currency = convert_historic_price_to_currency(
                historic_timestamp_chia, historic_price_chia,
                historic_timestamp, historic_price)
            coins_data[tail].historic_price_currency = historic_price_currency
            #coins_data[tail].historic_price_currency = dict(zip(historic_timestamp,
            #                                                    historic_price_currency))
            begin = historic_timestamp[0]
            end = historic_timestamp[-1]
            coins_data[tail].historic_range_price_data = (begin, end)


def get_spendable_coin(wallet_id):
    """Get spendable coins by waiting for the wallet to be ready"""
    coins = False
    count = 0
    #while not coins or count == 10:
    while not coins:
        coins = asyncio.run(
            call_rpc_wallet('get_spendable_coins', wallet_id=wallet_id))
        logging(server_logger, "DEBUG", f"Coin retrive form: {coins}")
        if not coins:
            # temp workaround about not synced wallet
            time.sleep(5)
            count += 1
            continue
        else:
            return coins["confirmed_records"]
    return False


def fetch_cat_assets():

    conn = sqlite3.connect(DB_WDB, timeout=SQL_TIMEOUT)
    last_update = WDB.retrive_table_timestamp(conn, 'asset_name')
    cats_data = None
    min_time_elapsed = 1 * 60 * 60
    now = datetime.now().timestamp()
    if (now - last_update) > min_time_elapsed:
        # insert the chia asset on
        cats_data = DEX.fetch_all_CAT_names_from_spacescan()

    if cats_data:
        for cat in cats_data:
            WDB.insert_asset(conn, cat['asset_id'], cat['name'], cat['symbol'])
        WDB.insert_table_timestamp(conn, 'asset_name')


# wallet fetcher
# TODO: finger_list: List[int] is rendundant of fingers_state, List[FingerState]
def fetch_wallet(data_lock, fingers_state, fingers_list, finger_active,
                 coins_data, count_server):
    """Fetch wallet data."""

    logging(server_logger, "DEBUG", "wallet fetcher started.")

    while True:

        count_server[0] += 1
        logging(server_logger, "DEBUG", f'wallet fetcher loop counting: {count_server[0]}')

        original_logged_finger = asyncio.run(call_rpc_wallet('get_logged_in_fingerprint'))['fingerprint']
        finger_active[0] = original_logged_finger

        fingerprints = []
        ######################### LOAD CAT DATA #####################
        cat_data = threading.Thread(target=fetch_cat_assets, daemon=True)
        cat_data.start()

        ######################### FINGERPRINTS LOADING ################
        try:
            logging(server_logger, "DEBUG", f'loading fingerprints.\n\n')
            fingerprints = asyncio.run(call_rpc_wallet('get_public_keys'))
            logging(server_logger, "DEBUG", f'fingerprints: {fingerprints}')

            if fingerprints["success"]:
                fingerprints = fingerprints["public_key_fingerprints"]
            else:
                raise ConnectionError("The rpc call failed.")

            # get logged finger -> to place on a screen variable
            #screenState.active_pk = (False, asyncio.run(call_rpc_wallet('get_logged_in_fingerprint')))
            conn = sqlite3.connect(DB_WDB, timeout=SQL_TIMEOUT)
            for finger in fingerprints:
                if finger in fingers_list:
                    continue
                else:
                    new_pk = PkState()
                    new_pk.fingerprint = finger
                    key = call_rpc_daemon("get_key", fingerprint=finger)
                    new_pk.pk = key["public_key"]
                    new_pk.label = key["label"]
                    fingers_list.append(finger)
                    fingers_state.append(new_pk)

                    # store the fingerprints
                    logging(server_logger, "DEBUG", 'WDB insert PK starting')

                    try:
                        pk_state_id = WDB.insert_pk(conn, finger, key["label"], key["public_key"])
                    except Exception as e:
                        logging(server_logger, "DEBUG", f'WDB insert_pk error: {e}')

                    if pk_state_id:
                        add_addresses_thread = threading.Thread(target=fetch_addresses,
                                                                args=(data_lock,
                                                                      finger,
                                                                      pk_state_id),
                                                                daemon=True)
                        add_addresses_thread.start()

                    logging(server_logger, "DEBUG", 'WDB insert PK ended')

            logging(server_logger, "DEBUG", 'fingerprint loading ended')
            conn.close()

        except Exception as e:
            logging(server_logger, "DEBUG", "probably there is no chia node and wallet running")
            logging(server_logger, "DEBUG", f"Exception: {e}")


        #################### LOAD WALLET ########################
        try:
            logging(server_logger, "DEBUG", 'loading wallet.\n\n')

            conn = sqlite3.connect(DB_WDB, timeout=SQL_TIMEOUT)
            for finger in fingerprints:

                pk_state_id = WDB.retrive_pk(conn, finger)[0]
                logging(server_logger, "DEBUG", f"SQL {pk_state_id}")
                logged_finger = asyncio.run(call_rpc_wallet('get_logged_in_fingerprint'))
                if logged_finger != finger:
                    result = asyncio.run(call_rpc_wallet('log_in', fingerprint=finger))

                #time.sleep(15)

                logging(server_logger, "DEBUG", f"finger {finger}")
                logging(server_logger, "DEBUG", f"finger list {fingers_list}")
                idx = fingers_list.index(finger)
                wallets = fingers_state[idx].wallets

                # chia wallet
                chia_wallet: WalletState = WalletState()
                chia_wallet_id = 1
                response = asyncio.run(call_rpc_wallet('get_wallet_balance', wallet_id=chia_wallet_id))
                logging(server_logger, "DEBUG", f"rpc balance {response}")

                if response:
                    response = response["wallet_balance"]
                else:
                    raise ConnectionError("The rpc call failed.")
                    logging(server_logger, "DEBUG", f'get balance did not get anything for the chia wallet. Finger; {finger}')
                chia_wallet.confirmed_wallet_balance = response['confirmed_wallet_balance'] / XCH_MOJO
                chia_wallet.spendable_balance = response['spendable_balance'] / XCH_MOJO
                chia_wallet.unspent_coin_count = response['unspent_coin_count']
                chia_wallet.name = "Chia"
                chia_wallet.ticker = "XCH"
                WDB.insert_wallet(conn, pk_state_id, XCH_FAKETAIL, chia_wallet)
                btc_data_thread = threading.Thread(target=fetch_btc_data,
                                                   args=(data_lock,
                                                         coins_data),
                                                   daemon=True)
                btc_data_thread.start()
                chia_data_thread = threading.Thread(target=fetch_chia_data,
                                                    args=(data_lock,
                                                          coins_data),
                                                    daemon=True)
                chia_data_thread.start()

                coins = get_spendable_coin(chia_wallet_id)
                #if coins:
                #    if len(coins) > 4:
                #        chia_wallet.coins.extend(coins[:4])
                #    else:
                #        chia_wallet.coins.extend(coins)
                chia_wallet.coins.extend(coins)
                wallets[XCH_FAKETAIL] = chia_wallet

                # add CATs
                cat_chia_wallets = asyncio.run(
                    call_rpc_wallet('get_wallets', type=6))["wallets"]

                logging(server_logger, "DEBUG", f"chia cat wallet {cat_chia_wallets}")
                for e, i in enumerate(cat_chia_wallets):
                    cat_wallet = WalletState()
                    balance = None
                    coins = []
                    try:
                        balance = asyncio.run(
                            call_rpc_wallet('get_wallet_balance', wallet_id=i['id']))["wallet_balance"]
                        logging(server_logger, "DEBUG", f"rpc balance for a cat {balance}")
                    except Exception as e:
                        logging(server_logger, "DEBUG", f"Balance error. Exception: {e}")
                        logging(server_logger, "DEBUG", f"Traceback: {traceback.format_exc()}")
                        traceback.print_exc()

                    coins = get_spendable_coin(i['id'])
                    if coins:
                        cat_wallet.coins.extend(coins)
                    else:
                        logging(server_logger, "DEBUG", f"Error while retriving spendable coins for {i['id']} asset and for the finger")

                    try:
                        transactions = asyncio.run(call_rpc_wallet('get_transactions',
                                                                   wallet_id=i['id']))["transactions"]
                    except Exception as e:
                        logging(server_logger, "DEBUG", f"Coin retrive error for get_transaction. Probably wallet not synced? Exception: {e}")
                        logging(server_logger, "DEBUG", f"Traceback: {traceback.format_exc()}")
                        logging(server_logger, "DEBUG", f"Error for the {i['id']} asset and for the finger {finger}")
                        traceback.print_exc()
                    transactions_roto = []
                    for t in transactions:
                        transactions_roto.append(TransactionRecordRoto(
                                                 t["confirmed_at_height"],
                                                 t["created_at_time"],
                                                 t["to_puzzle_hash"],
                                                 t["amount"],
                                                 t["fee_amount"],
                                                 t["confirmed"],
                                                 t["trade_id"],
                                                 t["type"],
                                                 t["name"])
                                                 )

                    try:
                        cat_wallet.transactions = transactions_roto
                    except Exception as e:
                        logging(server_logger, "DEBUG", f"Exception: {e}")
                        logging(server_logger, "DEBUG", f"Traceback: {traceback.format_exc()}")
                        traceback.print_exc()

                    tail = balance['asset_id']  # it is the tail...
                    cat_wallet.data = tail
                    #print(f'cata wallet data: ', cat_wallet.data)
                    cat_name_sym = DEX.fetchDexiNameFromTail(cat_wallet.data)
                    #print(f"dexi data: ", cat_name_sym)
                    # fetch prices from dexi
                    WDB.insert_asset(conn, cat_wallet.data,
                                     cat_name_sym['name'],
                                     cat_name_sym['symbol'])
                    coin_data_thread = threading.Thread(target=fetch_coin_data,
                                                        args=(data_lock,
                                                              coins_data,
                                                              cat_wallet.data),
                                                        daemon=True)
                    coin_data_thread.start()

                    cat_wallet.name = cat_name_sym['name']
                    cat_wallet.ticker = cat_name_sym['symbol']
                    cat_wallet.confirmed_wallet_balance = balance['confirmed_wallet_balance'] // CAT_MOJO
                    cat_wallet.spendable_balance = balance['spendable_balance'] // CAT_MOJO
                    cat_wallet.unspent_coin_count = balance['unspent_coin_count']
                    # bedore i was using the wallet id of the cat wallet.
                    # now i am using the cat tail
                    #wallets[i['id']] = cat_wallet
                    wallets[cat_wallet.data] = cat_wallet
                    # evaluate if it is better to use the byte32 name

                    # store
                    WDB.insert_wallet(conn, pk_state_id, tail, cat_wallet)

                # add fake coins for testing
                for e, cat_tail in enumerate(cat_test):
                    if cat_tail in wallets:
                        continue
                    cat_wallet = WalletState()
                    balance = 999
                    cat_wallet.data = cat_tail
                    dexi_name = DEX.fetchDexiNameFromTail(cat_wallet.data)
                    cat_wallet.name = dexi_name['name']
                    cat_wallet.ticker = dexi_name['symbol']
                    cat_wallet.confirmed_wallet_balance = 111
                    cat_wallet.spendable_balance = 222
                    cat_wallet.unspent_coin_count = 333
                    wallets[cat_tail] = cat_wallet
                    # fetch prices from dexi
                    coin_data_thread = threading.Thread(target=fetch_coin_data,
                                                        args=(data_lock,
                                                              coins_data,
                                                              cat_wallet.data),
                                                        daemon=True)
                    coin_data_thread.start()
                    # evaluate if it is better to use the byte32 name

            conn.close()

            logging(server_logger, "DEBUG", "loading wallet ended")

        except Exception as e:
            logging(server_logger, "DEBUG", "probably there is no chia node and wallet running")
            logging(server_logger, "DEBUG", f"Exception: {e}")
            traceback.print_exc()
            logging(server_logger, "DEBUG", f"Traceback: {traceback.format_exc()}")

        try:
            result = asyncio.run(
                call_rpc_wallet('log_in', fingerprint=original_logged_finger))#["fingerprint"]
            logging(server_logger, "DEBUG", f"original fingerprint: {original_logged_finger}")
            logging(server_logger, "DEBUG", f"call output log in: {result}")
            if not result:
                result = result['fingerprint']
            else:
                print("no come back")
        except Exception as e:
            logging(server_logger, "DEBUG", "logging back to the main fingerprint")
            logging(server_logger, "DEBUG", f"Exception: {e}")
            traceback.print_exc()
            logging(server_logger, "DEBUG", f"Traceback: {traceback.format_exc()}")

        logging(server_logger, "DEBUG", "begin sleep")
        time.sleep(10)
        logging(server_logger, "DEBUG", "end sleep")


# UI

def createFullSubWin(stdscr, screenState, height, width):
    """Create a subwindow for curses considering header and footer"""
    nLinesUsed = screenState.headerLines + screenState.footerLines
    return stdscr.subwin(height - nLinesUsed, width, screenState.headerLines, 0)


def menu_select(stdscr, menu, select, point, color_pairs, color_pairs_sel, figlet=False):
    """Create a menu at given coordinate. Point[y,x]"""
    if figlet:

        s_height = FUTURE_FONT.height

        for i, item in enumerate(menu):
            if select == i:
                stdscr.attron(curses.color_pair(color_pairs_sel))
            else:
                stdscr.attron(curses.color_pair(color_pairs))
            text = (str(i) + " - " + str(item))
            s = UItext.renderFont(text, FUTURE_FONT)
            for n, line in enumerate(s):
                stdscr.addstr(point[0] + i * s_height + n, point[1], line)
    else:
        for i, item in enumerate(menu):
            if select == i:
                stdscr.attron(curses.color_pair(color_pairs_sel) | curses.A_BOLD)
            else:
                stdscr.attron(curses.color_pair(color_pairs) | curses.A_BOLD)
            stdscr.addstr(point[0] + i, point[1], (str(i) + " - " + str(item)))


def screen_main_menu(stdscr, keyboardState, screenState: ScreenState,
                     figlet=False):

    width = screenState.screen_size.x
    height = screenState.screen_size.y

    menu_win = createFullSubWin(stdscr, screenState, height, width)
    menu_win.bkgd(' ', curses.color_pair(screenState.colorPairs["body"]))

    activeScope: Scope = screenState.activeScope
    screenState.scope_exec_args = [screenState]

    if len(activeScope.sub_scopes) == 0:
        menu_items = [
            ('wallet', screen_fingers, activate_scope),
            ('full node', screen_full_node, activate_scope),
            ('harvester analytics', screen_harvester, activate_scope),
            ('dex', screen_dex, activate_scope)
        ]
        if DEBUGGING:
            menu_items += [
                ("tabs", screen_tabs, activate_scope),
                ('debugging screen', screen_debugging, activate_scope)
            ]

        for name, handler, exec_fun in menu_items:
            newScope = Scope(name, handler, screenState)
            newScope.exec = exec_fun
            newScope.parent_scope = activeScope
            activeScope.sub_scopes[name] = newScope

    # TODO it always active?
    if activeScope is screenState.activeScope:
        activeScope.update()
    screenState.selection = activeScope.cursor

    # menu dimension
    yDimMenu = len(activeScope.sub_scopes) * FUTURE_FONT.height
    longestLine = ''
    xDimMenu = 0
    for i in activeScope.sub_scopes.keys():
        if len(i) > xDimMenu:
            xDimMenu = len(i)
            longestLine = i

    xDimMenu, a = UItext.sizeText(longestLine, FUTURE_FONT)

    if height > yDimMenu * 2 and width > xDimMenu * 2:

        xMenu = int(width / 2 - xDimMenu / 2)
        yMenu = int(height / 2 - yDimMenu / 2)

        menu_select(menu_win, list(activeScope.sub_scopes.keys()), screenState.selection, [yMenu, xMenu],
                    screenState.colorPairs['body'], screenState.colorPairs["body_sel"],
                    True)
    else:
        # menu dimension
        yDimMenu = len(activeScope.sub_scopes)
        xDimMenu = 0
        for i in activeScope.sub_scopes.keys():
            if len(i) > xDimMenu:
                xDimMenu = len(i)

        xMenu = int(width/2 - xDimMenu / 2)
        yMenu = int(height/2 - yDimMenu / 2)

        menu_select(menu_win, list(activeScope.sub_scopes.keys()), screenState.selection, [yMenu, xMenu],
                    screenState.colorPairs['body'], screenState.colorPairs["body_sel"],
                    False)

    # CUSTOM CHAR test, among them there is the little square and others
    menu_win.attron(curses.color_pair(1))
    menu_win.addstr(2, 4, u'\u1F973'.encode('utf-8'))
    menu_win.addstr(4, 4, u'\u2580'.encode('utf-8'))
    menu_win.addstr(4, 5, u'\u2584'.encode('utf-8'))
    menu_win.addstr(4, 6, u'\u2575'.encode('utf-8'))
    menu_win.addstr(4, 7, u'\u2577'.encode('utf-8'))
    menu_win.addstr(4, 8, u'\u2502'.encode('utf-8'))
    menu_win.addstr(4, 9, u'\u2502'.encode('utf-8'))
    menu_win.addstr(4, 9, u'\u2584'.encode('utf-8'))
    menu_win.addstr(4, 27, "the cube")
    menu_win.addstr(5, 4, u'\u2581'.encode('utf-8'))
    menu_win.addstr(6, 4, u'\u2582'.encode('utf-8'))
    menu_win.addstr(7, 4, u'\u2583'.encode('utf-8'))
    menu_win.addstr(8, 4, u'\u2585'.encode('utf-8'))
    menu_win.addstr(8, 7, "il cinque")
    menu_win.addstr(9, 4, u'\u25C0'.encode('utf-8'))
    menu_win.addstr(10, 4, u'\u26F3'.encode('utf-8'))
    menu_win.addstr(11, 4, u'\u26A1'.encode('utf-8'))
    menu_win.addstr(12, 4, u'\U0001F331'.encode('utf-8'))


def screen_dex(stdscr, keyboardState, screenState: ScreenState, figlet=False):

    width = screenState.screen_size.x
    height = screenState.screen_size.y

    # select pair
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
    # define as globla
    ## selTicker = {}


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


# init fingletfont
DOOM_FONT = UItext.Font()
# import Path or do something else
pathA = Path("figlet_fonts/doom.flf")
UItext.loadFontFTL(pathA, DOOM_FONT)

FUTURE_FONT = UItext.Font()
# import Path or do something else
pathA = Path("figlet_fonts/future.tlf")
UItext.loadFontFTL(pathA, FUTURE_FONT)

SMALL_FONT = UItext.Font()
# import Path or do something else
pathA = Path("figlet_fonts/small.flf")
UItext.loadFontFTL(pathA, SMALL_FONT)

STANDARD_FONT = UItext.Font()
# import Path or do something else
pathA = Path("figlet_fonts/standard.flf")
UItext.loadFontFTL(pathA, STANDARD_FONT)

SMBLOCK_FONT = UItext.Font()
# import Path or do something else
pathA = Path("figlet_fonts/smblock.tlf")
UItext.loadFontFTL(pathA, SMBLOCK_FONT)


def screen_intro(stdscr, keyboardState, screenState: ScreenState):
    """Intro screen"""

    width = screenState.screen_size.x
    height = screenState.screen_size.y

    # intro
    text = 'rototiller'

    sizeX, sizeY = UItext.sizeText(text, DOOM_FONT)
    stdscr.bkgd(' ', curses.color_pair(screenState.colorPairs["intro"]))

    screenState.scope_exec_args = [screenState]

    if height > sizeY * 2 and width > sizeX * 2:

        s = UItext.renderFont(text, DOOM_FONT)
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
            s = UItext.renderFont(text, FUTURE_FONT)
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


def screen_debugging_insert(stdscr, keyboardState, screenState: ScreenState):

    width = screenState.screen_size.x
    height = screenState.screen_size.y

    debug_win = createFullSubWin(stdscr, screenState, height, width)
    debug_win.erase()  # delete if not using newwin, it flicker
    debug_win.bkgd(' ', curses.color_pair(screenState.colorPairs["body"]))

    active_scope: Scope = screenState.activeScope
    main_scope = active_scope.main_scope
    screenState.scope_exec_args = [screenState]

    def get_N_scope_mod(scope: Scope):
        scope.active = False
        active_scope_key = list(scope.sub_scopes.keys())[scope.cursor]

        new_scope = scope.sub_scopes[active_scope_key]
        if len(new_scope.sub_scopes) > 0:
            new_scope.active = True
            return new_scope
        else:
            new_scope.bool = not new_scope.bool
            scope.active = True
            return scope

    main_scope.update()


def screen_debugging(stdscr, keyboardState, screenState: ScreenState):

    width = screenState.screen_size.x
    height = screenState.screen_size.y

    #debug_win = createFullSubWin(stdscr, screenState, height, width)
    #debug_win = curses.newwin(height // 2,
    debug_win = stdscr.subwin(height // 2,
                              width // 2,
                              height // 4,
                              width // 4)
    debug_win.erase()  # delete if not using newwin, it flicker
    debug_win.bkgd(' ', curses.color_pair(screenState.colorPairs["body"]))


    #dub_win = stdscr.subwin(20, 30, 13, 5)
    #dub_win.erase()  # delete if not using newwin, it flicker
    #dub_win.bkgd(' ', curses.color_pair(screenState.colorPairs["footer"]))

    #rub_win = dub_win.subwin(14, 20, 13, 7)
    #rub_win.erase()  # delete if not using newwin, it flicker
    #rub_win.bkgd(' ', curses.color_pair(screenState.colorPairs["header"]))


    #rub_win.addstr(0,2, "poins")

    active_scope: Scope = screenState.activeScope
    main_scope = active_scope.main_scope
    screenState.scope_exec_args = [screenState]

    def get_N_scope_mod(scope: Scope):
        scope.active = False
        active_scope_key = list(scope.sub_scopes.keys())[scope.cursor]

        new_scope = scope.sub_scopes[active_scope_key]
        if len(new_scope.sub_scopes) > 0:
            new_scope.active = True
            return new_scope
        else:
            new_scope.bool = not new_scope.bool
            scope.active = True
            return scope

    main_scope.update()

    # asset view
    if False:
        try:
            pass
        except Exception as e:
            print("exception while testing the asset view")
            print("The exception: ", e)
            traceback.print_exc()

    ###################### coins #########################
    if False:

        debug_win.addstr(3,8, f"coins")
        result = asyncio.run(call_rpc_wallet('log_in', fingerprint=291595168))["fingerprint"]
        debug_win.addstr(3,9, "logged in")
        coins = asyncio.run(
            call_rpc_wallet('get_spendable_coins', wallet_id=2))
        if coins:
            coins = coins["confirmed_records"]
            debug_win.addstr(3, 10, f"coins are :{str(coins)}")
            for i, c in enumerate(coins):
                debug_win.addstr(3 + i,10, f"coins are :{str(c['coin']['amount'])}")
        else:
            debug_win.addstr(3,10, f"no coins to show, rpc failed")

    ######################################################
    ###################### scope #########################
    if False:
        list01 = ["rosso", "lbu", "orao", "tempera"]
        list02 = ["cane", "orso", "ramarro"]
        list03 = ["birillo", "finestra", "catamarano"]

        gen_id = 0
        debug_win.addstr(3,10, f"scope is {main_scope.id}, cursor: {main_scope.cursor}")
        debug_win.addstr(2,10, f"scope is {active_scope.id}, cursor: {active_scope.cursor}")

        point_xy = UIgraph.Point(30, 5)
        menu_select_s(debug_win, screenState, "list_A", list01, point_xy,
                    screenState.colorPairs['body'], screenState.colorPairs["body_sel"],
                    main_scope, False)

        point_xy = UIgraph.Point(30, 15)
        menu_select_s(debug_win, screenState, "list_B", list02, point_xy,
                    screenState.colorPairs['body'], screenState.colorPairs["body_sel"],
                    main_scope, False)

        point_xy = UIgraph.Point(30, 25)
        menu_select_s(debug_win, screenState, "list_C", list03, point_xy,
                    screenState.colorPairs['body'], screenState.colorPairs["body_sel"],
                    main_scope, False)

        point_xy = UIgraph.Point(30, 30)
        #def create_button(stdscr, screenState, name: str, point: UIgraph.Point, active: bool):
        ELEMENTS.create_button(stdscr, screenState, main_scope, "button_1", point_xy, False)


        if keyboardState.enter is True:
            screenState.screen_data["active_scope"] = active_scope.exe(active_scope)
            #screenState.screen = screenState.menu[screenState.selection]
        if keyboardState.moveUp:
            active_scope.cursor -= 1
        if keyboardState.moveDown:
            active_scope.cursor += 1
        if keyboardState.esc is True:
            # call back the old scope
            active_scope.active = False
            screenState.screen_data["active_scope"]  = active_scope.parent_scope
            print(type(screenState.screen_data["active_scope"]))
            screenState.screen_data["active_scope"].active = True

        #screenState.screen_data["active_scope"] = active_scope

    ###################### drawing lines #########################
    if False:
        pt1 = UIgraph.Point(100, 20)

        if "DW" not in screenState.screen_data:
            screenState.screen_data["DW"] = {}
            screenState.screen_data["DW"]["pt2"] = UIgraph.Point(30, 30)

        pt2 = screenState.screen_data["DW"]["pt2"]

        if keyboardState.mouse:
            _, mx, my, _, _ = curses.getmouse()
            pt2 = UIgraph.Point(mx, my)
            screenState.screen_data["DW"]["pt2"] = pt2

        try:
            print("poin")
            UIgraph.drawPointBox(debug_win, screenState, pt1, screenState.colorPairs['test'])
            UIgraph.drawPointBox(debug_win, screenState, pt2, screenState.colorPairs['test'])
            print("int")
        except Exception as e:
            print("except point")
            print(e)
            traceback.print_exc()

        try:
            pass
            #UIgraph.drawLine2pts(debug_win, pt1, pt2)
        except Exception as e:
            print("aaaaaa")
            print(e)

        pp = UIgraph.Point(3,3)
        pp2 = UIgraph.Point(1,4)
        try:
            #UIgraph.drawLine2pts_subpixel(debug_win, pt1, pt2)
            #UIgraph.drawLine2pts_subpixel(debug_win, pt1 + pp, pt2 + pp2)
            for i in range(0):
                pp = UIgraph.Point(i,i)
                pp2 = UIgraph.Point(i+1,i+1)
                UIgraph.drawLine2pts_subpixel(debug_win, pt1 + pp, pt2 + pp2)
        except Exception as e:
            print("new aaaaaaaaaa")
            print(e)
            traceback.print_exc()

        pt3 = UIgraph.Point(90, 22)

    #    pt4 = UIgraph.Point(pt2.x + 5, pt2.y + 10)
        pt4 = UIgraph.Point(pt2.x, pt2.y)


        try:
            #UIgraph.drawLine2pts_aliasing(debug_win, screenState, pt3, pt4, screenState.colorPairs['body'])
            #UIgraph.drawLine2pts(debug_win, pt3, pt4)
            pass
        except Exception as e:
            print("aaaaaa")
            print(e)
            traceback.print_exc()
        deltaP = UIgraph.Point(5,5)
        deltaP = UIgraph.Point(0,0)
        p_bug = UIgraph.Point(58,12)
        try:
            UIgraph.drawLine2pts_aliasing_sub(debug_win, screenState, pt3 + deltaP,
                                            pt4 + deltaP, screenState.colorPairs['body'])
            #UIgraph.drawLine2pts(debug_win, pt3, pt4)
        except Exception as e:
            print(e)
            traceback.print_exc()

        ppp = [UIgraph.Point(10,20), UIgraph.Point(30,40)]
        for p in ppp:
            UIgraph.drawPointBox(debug_win, screenState, p, screenState.colorPairs['test'])

        for idx,p in enumerate(ppp):
            ppp[idx] = UIgraph.Point(p.x, p.y * 2)


        try:
            pass
            #UIgraph.drawPoints_sub(debug_win, screenState, ppp, (200,0,200))
            #UIgraph.drawLine2pts(debug_win, pt3, pt4)
        except Exception as e:
            print("aaaaaaaaaa sub")
            print(e)
            traceback.print_exc()

    ######################### graph ##################33333333
    if False:
        #for cat in cat_test.keys():
        #    a = DEX.fetchDexiNameFromTail(cat)
        #    print(a)
        #    DEX.getHistoricPriceFromTail(cat, 7)
        print(cat_test.keys())
        cat = list(cat_test.keys())[0]
        #prices, timestamp = DEX.getHistoricPriceFromTail(cat, 7)
        #UIgraph.drawPriceGraph(stdscr, screenState, prices, timestamp, 7)
        y0 = 2
        for i in range(7):
            graph_win = debug_win.subwin(5, 20, y0, 40)
            graph_win.bkgd(' ', curses.color_pair(screenState.colorPairs["body"]))
            graph_win.erase()
            cat = list(cat_test.keys())[i]
            if cat not in screenState.coins_data:
                y0 += 6
                continue
            coin_data = screenState.coins_data[cat]
            prices = list(coin_data.historic_price.values())
            timestamp = list(coin_data.historic_price.keys())
            if len(prices) < 1:
                prices = [coin_data.current_price]
                timestamp = [coin_data.current_price_date]
            debug_win.addstr(y0,70, f"the cat is: {cat}")
            debug_win.addstr(y0 + 1,70, f"len: {len(prices)}; time {timestamp[0]} and prices; {prices[0]}")
            #prices, timestamp = DEX.getHistoricPriceFromTail(cat, 7)
            UIgraph.drawPriceGraph(graph_win, screenState, prices, timestamp, 7)
            y0 += 6

        #graph_win = stdscr.subwin(10, 20, 8, 30)
        #graph_win.bkgd(' ', curses.color_pair(screenState.colorPairs["test_red"]))
        #cat = list(cat_test.keys())[0]
        #prices, timestamp = DEX.getHistoricPriceFromTail(cat, 7)
        #UIgraph.drawPriceGraph(graph_win, screenState, prices, timestamp, 7)


    ###################### buttons ###################33
    if False:

        try:

            pos_x = 2
            pos_y = 2

            size_x = 70
            size_y = 1

            xch_amount = "xch 1230.43"
            btc_amount = "BTC 0.44321"
            usd_amount = "$ 23.234.38"

            items = [xch_amount, btc_amount, usd_amount]
            item_colors = ['xch', 'btc', 'dollar']
            spaces = 2
            pre_text = "Total wallet value: "

            debug_win.addstr(pos_y + 1, pos_x, pre_text, curses.A_BOLD)

            pos_x += len(pre_text) + 2 * spaces


            length = 0

            for item in items:
                length += len(item) + 2 * spaces

            for item, item_color in zip(items, item_colors):
                length = len(item) + 2 * spaces
                y = pos_y
                x = pos_x
                text_color_pair = UIgraph.customColorsPairs_findByValue(
                    screenState.cursesColors,
                    screenState.colorPairs[item_color])
                text_color_background = text_color_pair[1]
                default_background = UIgraph.customColors_findByValue(
                    screenState.cursesColors,
                    screenState.colors["background"])

                # upper row

                new_pair = (text_color_background, default_background)
                print('new pair ', new_pair)
                frame_color_pair = UIgraph.addCustomColorTuple(
                    new_pair,
                    screenState.cursesColors
                )


                debug_win.addstr(y,x, u'\u2584' * length,
                                    curses.color_pair(frame_color_pair))

                # text
                debug_win.addstr(y + 1,x, f"  {item}  ",
                                 curses.color_pair(
                                    screenState.colorPairs[item_color]) |
                                 curses.A_BOLD)

                # lower row
                debug_win.addstr(y + 2,x, u'\u2580' * length,
                                 curses.color_pair(frame_color_pair))
                pos_x += length




            ### press the button

            pos_x = 2
            pos_y = 5

            but = 'press the button'
            space = 2
            length = len(but) + space * 2

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
            multiplier = 1.2
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


            # upper row
            debug_win.addstr(pos_y, pos_x, u'\u2588' * length,
                                curses.color_pair(frame_cp_clear))
            x = pos_x + length - 1
            debug_win.addstr(pos_y, x, u'\u25E2',
                                curses.color_pair(frame_cp_cl))

            # text
            x = pos_x
            debug_win.addstr(pos_y + 1, x, u'\u2588',
                                curses.color_pair(frame_cp_clear) |
                                curses.A_BOLD)
            x += 1
            debug_win.addstr(pos_y + 1, x, f" {but} ",
                                curses.color_pair(
                                    screenState.colorPairs['xch']) |
                                curses.A_BOLD)
            x += length - 2
            debug_win.addstr(pos_y + 1, x, u'\u2588',
                                curses.color_pair(frame_cp_dark) |
                                curses.A_BOLD)

            # lower row
            debug_win.addstr(pos_y + 2, pos_x, u'\u2588' * length,
                                curses.color_pair(frame_cp_dark))
            debug_win.addstr(pos_y + 2, pos_x, u'\u25E2',
                                curses.color_pair(frame_cp_cl))


            #raise


            ########## test 2 ###############3
            pos_x += length + 2

            # upper row
            debug_win.addstr(pos_y, pos_x, u'\u2584' * length,
                                curses.color_pair(frame_cp_clear))

            # text
            x = pos_x
            debug_win.addstr(pos_y + 1, x, u'\u2588',
                                curses.color_pair(frame_cp_clear) |
                                curses.A_BOLD)
            x += 1
            debug_win.addstr(pos_y + 1, x, f" {but} ",
                                curses.color_pair(
                                    screenState.colorPairs['xch']) |
                                curses.A_BOLD)
            x += length - 2
            debug_win.addstr(pos_y + 1, x, u'\u2588',
                                curses.color_pair(frame_cp_dark) |
                                curses.A_BOLD)

            # lower row
            debug_win.addstr(pos_y + 2, pos_x, u'\u2580' * length,
                                curses.color_pair(frame_cp_dark))

            ########## test 3 ###############3
            pos_x += length + 2

            # upper row
            debug_win.addstr(pos_y, pos_x, u'\u2584' * (length - 1),
                                curses.color_pair(frame_cp_clear))

            # text
            x = pos_x
            debug_win.addstr(pos_y + 1, x, u'\u2588',
                                curses.color_pair(frame_cp_clear) |
                                curses.A_BOLD)
            x += 1
            debug_win.addstr(pos_y + 1, x, f" {but} ",
                                curses.color_pair(
                                    screenState.colorPairs['xch']) |
                                curses.A_BOLD)
            x += length - 2
            debug_win.addstr(pos_y + 1, x, u'\u2588',
                                curses.color_pair(frame_cp_dark) |
                                curses.A_BOLD)

            # lower row
            debug_win.addstr(pos_y + 2, pos_x + 1, u'\u2580' * (length - 1),
                                curses.color_pair(frame_cp_dark))


            ########## test 4 ###############3
            pos_x += length + 2

            # upper row
            debug_win.addstr(pos_y, pos_x, u'\u2584' * (length - 1),
                                curses.color_pair(frame_cp_dark))

            # text
            x = pos_x
            debug_win.addstr(pos_y + 1, x, u'\u2588',
                                curses.color_pair(frame_cp_dark) |
                                curses.A_BOLD)
            x += 1
            debug_win.addstr(pos_y + 1, x, f" {but} ",
                                curses.color_pair(
                                    screenState.colorPairs['xch']) |
                                curses.A_BOLD)
            #x += length - 2
            #debug_win.addstr(pos_y + 1, x, u'\u2588',
            #                    curses.color_pair(frame_cp_dark) |
            #                    curses.A_BOLD)

            # lower row
            #debug_win.addstr(pos_y + 2, pos_x + 1, u'\u2580' * (length - 1),
            #                    curses.color_pair(frame_cp_dark))


            pos_x += length + 2
            if "test_wallet" not in screenState.screen_data:
                screenState.screen_data["test_wallet"] = False
            if keyboardState.moveLeft is True:
                screenState.screen_data["test_wallet"] = True
            if keyboardState.moveRight is True:
                screenState.screen_data["test_wallet"] = False

            if screenState.screen_data["test_wallet"]:
                # upper row
                debug_win.addstr(pos_y, pos_x, u'\u2584' * (length - 1),
                                    curses.color_pair(frame_cp_dark))

                # text
                x = pos_x
                debug_win.addstr(pos_y + 1, x, u'\u2588',
                                    curses.color_pair(frame_cp_dark) |
                                    curses.A_BOLD)
                x += 1
                debug_win.addstr(pos_y + 1, x, f" {but} ",
                                    curses.color_pair(
                                        screenState.colorPairs['xch']) |
                                    curses.A_BOLD)
                x += length - 2
                debug_win.addstr(pos_y + 1, x, u'\u2588',
                                    curses.color_pair(frame_cp_dark) |
                                    curses.A_BOLD)

                # lower row
                debug_win.addstr(pos_y + 2, pos_x + 1, u'\u2580' * (length - 1),
                                    curses.color_pair(frame_cp_dark))
            else:
                # upper row
                debug_win.addstr(pos_y, pos_x, u'\u2584' * (length - 1),
                                    curses.color_pair(frame_cp_clear))

                # text
                x = pos_x
                debug_win.addstr(pos_y + 1, x, u'\u2588',
                                    curses.color_pair(frame_cp_clear) |
                                    curses.A_BOLD)
                x += 1
                debug_win.addstr(pos_y + 1, x, f" {but} ",
                                    curses.color_pair(
                                        screenState.colorPairs['xch']) |
                                    curses.A_BOLD)
                x += length - 2
                debug_win.addstr(pos_y + 1, x, u'\u2588',
                                    curses.color_pair(frame_cp_dark) |
                                    curses.A_BOLD)

                # lower row
                debug_win.addstr(pos_y + 2, pos_x + 1, u'\u2580' * (length - 1),
                                    curses.color_pair(frame_cp_dark))

            ##################################################################

            pos_x += length + 2

            if screenState.screen_data["test_wallet"]:
                # upper row
                debug_win.addstr(pos_y, pos_x, u'\u2584' * (length - 0),
                                    curses.color_pair(frame_cp_dark))

                # text
                x = pos_x
                debug_win.addstr(pos_y + 1, x, u'\u2588',
                                    curses.color_pair(frame_cp_dark) |
                                    curses.A_BOLD)
                x += 1
                debug_win.addstr(pos_y + 1, x, f" {but} ",
                                    curses.color_pair(
                                        screenState.colorPairs['xch']) |
                                    curses.A_BOLD)
                x += length - 2
                debug_win.addstr(pos_y + 1, x, u'\u2588',
                                    curses.color_pair(frame_cp_dark) |
                                    curses.A_BOLD)

                # lower row
                debug_win.addstr(pos_y + 2, pos_x + 0, u'\u2580' * (length - 0),
                                    curses.color_pair(frame_cp_dark))
            else:
                # upper row
                debug_win.addstr(pos_y, pos_x, u'\u2584' * (length - 0),
                                    curses.color_pair(frame_cp_clear))

                # text
                x = pos_x
                debug_win.addstr(pos_y + 1, x, u'\u2588',
                                    curses.color_pair(frame_cp_clear) |
                                    curses.A_BOLD)
                x += 1
                debug_win.addstr(pos_y + 1, x, f" {but} ",
                                    curses.color_pair(
                                        screenState.colorPairs['xch']) |
                                    curses.A_BOLD)
                x += length - 2
                debug_win.addstr(pos_y + 1, x, u'\u2588',
                                    curses.color_pair(frame_cp_clear) |
                                    curses.A_BOLD)

                # lower row
                debug_win.addstr(pos_y + 2, pos_x + 0, u'\u2580' * (length - 0),
                                    curses.color_pair(frame_cp_clear))



            ##################################################################
            pos_x += length + 2

            if screenState.screen_data["test_wallet"]:
                # upper row
                debug_win.addstr(pos_y, pos_x, u'\u2584' * (length - 0),
                                    curses.color_pair(frame_cp_dark))

                # text
                x = pos_x
                debug_win.addstr(pos_y + 1, x, u'\u2588',
                                    curses.color_pair(frame_cp_dark) |
                                    curses.A_BOLD)
                x += 1
                debug_win.addstr(pos_y + 1, x, f" {but} ",
                                    curses.color_pair(text_dark) |
                                    curses.A_BOLD)
                x += length - 2
                debug_win.addstr(pos_y + 1, x, u'\u2588',
                                    curses.color_pair(frame_cp_dark) |
                                    curses.A_BOLD)

                # lower row
                debug_win.addstr(pos_y + 2, pos_x + 0, u'\u2580' * (length - 0),
                                    curses.color_pair(frame_cp_dark))
            else:
                # upper row
                debug_win.addstr(pos_y, pos_x, u'\u2584' * (length - 0),
                                    curses.color_pair(frame_cp_dark))

                # text
                x = pos_x
                debug_win.addstr(pos_y + 1, x, u'\u2588',
                                    curses.color_pair(frame_cp_dark) |
                                    curses.A_BOLD)
                x += 1
                debug_win.addstr(pos_y + 1, x, f" {but} ",
                                    curses.color_pair(text_clear) |
                                    curses.A_BOLD)
                x += length - 2
                debug_win.addstr(pos_y + 1, x, u'\u2588',
                                    curses.color_pair(frame_cp_clear) |
                                    curses.A_BOLD)

                # lower row
                debug_win.addstr(pos_y + 2, pos_x + 0, u'\u2580',
                                    curses.color_pair(frame_cp_dark))
                debug_win.addstr(pos_y + 2, pos_x + 1, u'\u2580' * (length - 1),
                                    curses.color_pair(frame_cp_clear))



            ########## test 8 ###############3
            pos_x += length + 2

            # upper row
            debug_win.addstr(pos_y, pos_x, u'\u2584' * (length - 0),
                                curses.color_pair(frame_cp_dark))
            # text
            x = pos_x
            debug_win.addstr(pos_y + 1, x, u'\u2588',
                                curses.color_pair(frame_cp_dark) |
                                curses.A_BOLD)
            x += 1
            debug_win.addstr(pos_y + 1, x, f" {but} ",
                                curses.color_pair(text_clear) |
                                curses.A_BOLD)
            x += length - 2
            debug_win.addstr(pos_y + 1, x, u'\u2588',
                                curses.color_pair(frame_cp_clear) |
                                curses.A_BOLD)
            # lower row
            debug_win.addstr(pos_y + 2, pos_x + 0, u'\u2580',
                                curses.color_pair(frame_cp_dark))

            # selection
            debug_win.addstr(pos_y + 2, pos_x + 1, u'\u2580' * (length - 1),
                                curses.color_pair(frame_selected))
            debug_win.addstr(pos_y + 1, pos_x + length, u'\u258c',
                                curses.color_pair(frame_selected_backgroung))
            debug_win.addstr(pos_y + 2, pos_x + length, u'\u258c',
                                curses.color_pair(frame_selected_backgroung))

            ########## test 9 ###############3
            pos_x += length + 2

            # upper row
            debug_win.addstr(pos_y, pos_x, u'\u2584' * (length - 0),
                                curses.color_pair(frame_cp_dark))
            # text
            x = pos_x
            debug_win.addstr(pos_y + 1, x, u'\u2588',
                                curses.color_pair(frame_cp_dark) |
                                curses.A_BOLD)
            x += 1
            debug_win.addstr(pos_y + 1, x, f" {but} ",
                                curses.color_pair(text_clear) |
                                curses.A_BOLD)
            x += length - 2
            debug_win.addstr(pos_y + 1, x, u'\u2588',
                                curses.color_pair(frame_cp_clear) |
                                curses.A_BOLD)
            # lower row
            debug_win.addstr(pos_y + 2, pos_x + 0, u'\u2580',
                                curses.color_pair(frame_cp_dark))

            # selection
            debug_win.addstr(pos_y + 2, pos_x, u'\u2580',
                                curses.color_pair(frame_selected_2))
            debug_win.addstr(pos_y + 2, pos_x + 1, u'\u2580' * (length - 1),
                                curses.color_pair(frame_selected))
            debug_win.addstr(pos_y + 0, pos_x + length, u'\u2596',
                                curses.color_pair(frame_selected_backgroung))
            debug_win.addstr(pos_y + 1, pos_x + length, u'\u258c',
                                curses.color_pair(frame_selected_backgroung))
            debug_win.addstr(pos_y + 2, pos_x + length, u'\u258c',
                                curses.color_pair(frame_selected_backgroung))

        except:
            print("cazzi amazzi")
            traceback.print_exc()

    if False:

        try:
            # menu button
            er_menu = ['steakkk', 'proof of steak', 'salad', 'cheese', 'pizza']
            ELEMENTS.create_button_menu(stdscr, screenState, main_scope, "burton menu", er_menu,
                          UIgraph.Point(5,8))

            menu_select(stdscr, er_menu, screenState.selection, [5, 50],
                        screenState.colorPairs['body'], screenState.colorPairs["body_sel"],
                        False)

            ELEMENTS.menu_select(stdscr, er_menu, main_scope, UIgraph.Point(60, 10),
                        screenState.colorPairs['body'], screenState.colorPairs["body_sel"])

            # normal button
            ELEMENTS.create_button(stdscr, screenState, main_scope, "burton",
                          UIgraph.Point(30,10))


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

            active = True
            if ELEMENTS.read_bool_button(stdscr, screenState, main_scope, "burton"):

                ELEMENTS.create_tab_large(debug_win, screenState, main_scope,
                           "tab_a", theList2, None, theListColor, True,
                           UIgraph.Point(10,20), UIgraph.Point(150,25),
                           keyboardState, "test_tabs", 2, None, active, True, legend)
            else:
                create_tab(debug_win, screenState, main_scope,
                           "tab_b", theList2, None, None, True,
                           UIgraph.Point(10,25), UIgraph.Point(100,8),
                           keyboardState, "test_tabs_small", open_coin_wallet, active, False)

        except:
            print("cazzi amazzi")
            traceback.print_exc()

    if True:

        try:
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



            # menu button
            er_menu = ['yougurt', 'steak', 'proof of steak', 'salad', 'cheese',
                       'pizza', 'gizza', 'terrazza', 'melgalta', 'irpensum']
            turt_scope: Scope = ELEMENTS.create_button_menu(debug_win, screenState, main_scope, "turton menu", er_menu.copy(),
                          UIgraph.Point(3,21))
            ELEMENTS.create_button_menu(debug_win, screenState, main_scope, "burton menu", er_menu,
                          UIgraph.Point(10,5))

            active_text = er_menu[turt_scope.cursor]
            ELEMENTS.text_double_space(debug_win, UIgraph.Point(7, 15), active_text,
                                       screenState.colorPairs["body"],
                                       screenState.colorPairs["tab_soft"],
                                       1, False)

            active_tab = er_menu[turt_scope.cursor]

            ttl = [[row[i] for row in theList]
                        for i in range(len(theList[0]))]

            ELEMENTS.create_tab(debug_win, screenState, main_scope,
                                "tab_aa", ttl, None, None, True,
                                UIgraph.Point(2,1), UIgraph.Point(80,10),
                                keyboardState, None, active, True, legend)
            ELEMENTS.create_tab(debug_win, screenState, main_scope,
                                "tab_c", theList2, None, None, False,
                                UIgraph.Point(2,15), UIgraph.Point(50,8),
                                keyboardState, None, active, False, legend)
            #match active_tab:
            match False:
                case 'steak':
                    ELEMENTS.create_tab(debug_win, screenState, main_scope,
                                        "tab_a", theList, None, None, False,
                                        UIgraph.Point(2,9), UIgraph.Point(80,10),
                                        keyboardState, "test_tabs", active, False, legend)
                case 'yougurt':
                    ELEMENTS.create_tab(debug_win, screenState, main_scope,
                                        "tab_aa", ttl, None, None, True,
                                        UIgraph.Point(2,9), UIgraph.Point(80,10),
                                        keyboardState, "test_tabs_aa", active, False, legend)
                case 'proof of steak':
                    ELEMENTS.create_tab(debug_win, screenState, main_scope,
                                        "tab_b", theList2, None, None, False,
                                        UIgraph.Point(2,9), UIgraph.Point(50, 6),
                                        keyboardState, "test_tabs_small_bat",
                                        active, False, legend)

                case 'salad':
                    ELEMENTS.create_tab(debug_win, screenState, main_scope,
                                        "tab_c", theList2, None, None, False,
                                        UIgraph.Point(2,15), UIgraph.Point(50,8),
                                        keyboardState, "test_tabs_small_ee", active, False, legend)

        except:
            print("cazzi amazzi")
            traceback.print_exc()
    debug_win.refresh()  # delete if not using newwin. It flickers...


def screen_coin_wallet(stdscr, keyboardState, screenState: ScreenState):
    """ waooolllet """

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
                                        exit_scope,
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
                                        exit_scope,
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
            if main_scope.data['addresses_loader'] is None:

                conn = sqlite3.connect(DB_WDB, timeout=SQL_TIMEOUT)
                table_name = 'addresses'
                chunk_size = height * 2  # to be sure to have at least 2 full screen of data
                offset = 0  # start from 0
                pk_state_id = WDB.retrive_pk(conn, screenState.active_pk)[0]
                filters = {'pk_state_id': pk_state_id, 'hardened': False}
                data_chunk_loader = WDB.DataChunkLoader(conn, table_name, chunk_size, offset, filters)
                conn.close()

            data_chunk_loader = main_scope.data['address_loader']

            #2 show all address
            pass
        case 'send':
            text = "Reciving address: "
            ELEMENTS.create_text(wallet_win, pos, text, P_col, True)
            pos_ins = pos + UIgraph.Point(len(text), 0)
            pre_text = "add address: "
            ELEMENTS.create_prompt(wallet_win, screenState, keyboardState, main_scope, 'add', pos_ins,
                                   pre_text, P_col, True, False)
            pos_ins += UIgraph.Point(0,1)
            pre_text = "add amount:  "
            ELEMENTS.create_prompt(wallet_win, screenState, keyboardState, main_scope, 'amount', pos_ins,
                                   pre_text, P_col, True, False)
            pos_ins += UIgraph.Point(0,1)
            pre_text = "add fee: "
            ELEMENTS.create_prompt(wallet_win, screenState, keyboardState, main_scope, 'fee', pos_ins,
                                   pre_text, P_col, True, False)
            pos_ins += UIgraph.Point(0,1)
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


def screen_fingers(stdscr, keyboardState, screenState):

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
            newScope.exec = activate_scope_and_set_pk
            newScope.parent_scope = activeScope
            activeScope.sub_scopes[finger] = newScope

    fingers_str = []
    for finger in activeScope.sub_scopes:
        pk_state: PkState = screenState.public_keys[finger]
        fing_name = str(finger) + " - " + pk_state.label
        # logging(ui_logger, "DEBUG", f"check finger, active {screenState.active_pk}")
        # logging(ui_logger, "DEBUG", f"check finger, finger {finger}")
        if finger == screenState.active_pk[0]:
            fingers_str.append(f"{fing_name} >")
        else:
            fingers_str.append(fing_name)

    activeScope.update()

    menu_size_xy = [0, 0]
    for f in fingers_str:
        sizeX, sizeY = UItext.sizeText(f, FUTURE_FONT)
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


def screen_wallet(stdscr, keyboardState, screenState: ScreenState):

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
            logging(ui_logger, "DEBUG", f'still no coin data for {chia_ticker}')
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
                logging(ui_logger, "DEBUG", f'still no coin data for {wallet.ticker}')
            current_prices_xch.append(cat_coins_data.current_price)
            historic_prices_xch.append(cat_coins_data.historic_price)
            current_prices_currency.append(cat_coins_data.current_price_currency)
            historic_prices_currency.append(cat_coins_data.historic_price_currency)
            try:
                xch_value = wallet.confirmed_wallet_balance * cat_coins_data.current_price
                total_values_xch.append(xch_value)
                total_values_currency.append(xch_value * chia_current_price_currency)
            except:
                logging(ui_logger, "DEBUG", f'still no coin data for {wallet.ticker} or {chia_ticker}')
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

        # DEBUG
        debug_cursor = active_scope.cursor
        try:
            global DEBUG_TEXT
            print(historic_prices_xch_tab)
            if len(historic_prices_xch_tab) > 1:
                DEBUG_TEXT = (f"ticker: {tickers[debug_cursor]} "
                              f"prices [1] xch: {historic_prices_xch_tab[debug_cursor][0]} "
                              f"{datetime.fromtimestamp(historic_ts_xch_tab[debug_cursor][0] / 1000).strftime('%Y-%m-%d')} // "
                              f"prices [2] xch: {historic_prices_xch_tab[debug_cursor][1]} "
                              f"{datetime.fromtimestamp(historic_ts_xch_tab[debug_cursor][1] / 1000).strftime('%Y-%m-%d')} ////"
                              f"prices [1] cur: {historic_prices_currency_tab[debug_cursor][0]} "
                              f"data: {datetime.fromtimestamp(historic_ts_xch_tab[debug_cursor][0] / 1000).strftime('%Y-%m-%d')} // "
                              f"prices [2] cur: {historic_prices_currency_tab[debug_cursor][1]} "
                              f"{datetime.fromtimestamp(historic_ts_xch_tab[debug_cursor][1] / 1000).strftime('%Y-%m-%d')}"
                              )
        except Exception as e:
            print(e)
            print("debugging is not for everyone...")

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
                print("leg")
                print(data_table_legend)
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

# idea about firsts screen
# intro
# main menu
# wallet
# dex
# tibet
# mempool
# node

dumbList = ["cedro", "boom", "toomabcdefghilmnopq", "broom", "LAgremmo",
            "magro", "tewo", "faiehr", "fegpq", "Pqntwr", "Kista", "eiuallo",
            "gest", "qqq"]
dumbList2 = [1, -2, 3, 32223333333333, -5, 6, -7, 8, 9, 10, -11, -12, -13, 14]
dumbList3 = [987, 782, 433, 904, 3459092348, 3890, 2903, 8812, 3, 34, 11343, 139, 22, 438]
dumbList4 = ["cedro", "boom", "toomabcdefghilmnopq", "broom", "LAgremmo",
            "magro", "tewo", "faiehr", "fegpq", "Pqntwr", "Kista", "eiuallo",
            "gest", "qqq"]

theList = []
for n, i in enumerate(dumbList):
    theList.append([dumbList[n], dumbList2[n], dumbList3[n]])

dumbList = dumbList[0:5]
dumbList2 = dumbList2[0:5]
dumbList3 = dumbList3[0:5]

theList2 = []
for n, i in enumerate(dumbList):
    theList2.append([dumbList[n], dumbList2[n], dumbList3[n], dumbList4[n]])


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
        scope.exec = activate_scope
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
    P_win_selected = screenState.colorPairs["win_select"]
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


white_darkBlue = None
def screen_tabs(stdscr, keyboardState, screenState: ScreenState, figlet=False):

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


def screen_full_node(stdscr, keyboardState, screenState, figlet=False):
    width = screenState.screen_size.x
    height = screenState.screen_size.y

    full_win = createFullSubWin(stdscr, screenState, height, width)
    full_win.bkgd(' ', curses.color_pair(screenState.colorPairs["body"]))

    activeScope: Scope = screenState.activeScope
    screenState.scope_exec_args = [screenState]

    if len(activeScope.sub_scopes) == 0:
        menu_items = [
            ('blocks', screen_blocks, activate_scope),
            ('memepool', screen_memepool, activate_scope)
        ]

        for name, handler, exec_fun in menu_items:
            newScope = Scope(name, handler, screenState)
            newScope.exec = exec_fun
            newScope.parent_scope = activeScope
            activeScope.sub_scopes[name] = newScope

    # TODO it always active?
    if activeScope is screenState.activeScope:
        activeScope.update()
    screenState.selection = activeScope.cursor

    # menu dimension
    yDimMenu = len(activeScope.sub_scopes) * FUTURE_FONT.height
    longestLine = ''
    xDimMenu = 0
    for i in activeScope.sub_scopes.keys():
        if len(i) > xDimMenu:
            xDimMenu = len(i)
            longestLine = i

    xDimMenu, a = UItext.sizeText(longestLine, FUTURE_FONT)

    if height > yDimMenu * 2 and width > xDimMenu * 2:

        xMenu = int(width / 2 - xDimMenu / 2)
        yMenu = int(height / 2 - yDimMenu / 2)

        menu_select(full_win, list(activeScope.sub_scopes.keys()), screenState.selection, [yMenu, xMenu],
                    screenState.colorPairs['body'], screenState.colorPairs["body_sel"],
                    True)
    else:
        # menu dimension
        yDimMenu = len(activeScope.sub_scopes)
        xDimMenu = 0
        for i in activeScope.sub_scopes.keys():
            if len(i) > xDimMenu:
                xDimMenu = len(i)

        xMenu = int(width/2 - xDimMenu / 2)
        yMenu = int(height/2 - yDimMenu / 2)

        menu_select(full_win, list(activeScope.sub_scopes.keys()), screenState.selection, [yMenu, xMenu],
                    screenState.colorPairs['body'], screenState.colorPairs["body_sel"],
                    False)



def screen_blocks(stdscr, keyboardState, screenState, figlet=False):
# Network: mainnet    Port: 8444   RPC Port: 8555
# Node ID: dab6ea4ed2076b13c3c15998aeb5dd0e4d7e5779aeef973beaf6147063e19629
# Genesis Challenge: ccd5bb71183532bff220ba46c268991a3ff07eb358e8255a65c30a2dce0e5fbb
# Current Blockchain Status: Full Node Synced
#
# Peak: Hash: 98b826e0132724f0895f0252f8894047b6baa0e63e27231bd7f31e3ce46424a6
#       Time: Wed Jul 17 2024 17:03:51 CEST                  Height:    5656246
#
# Estimated network space: 22.902 EiB
# Current difficulty: 16640
# Current VDF sub_slot_iters: 578813952
#
#   Height: |   Hash:
#   5656246 | 98b826e0132724f0895f0252f8894047b6baa0e63e27231bd7f31e3ce46424a6
#   5656245 | b9f3e73a7e1c7fbc2b163ad450a57a2d631f541a1ead30d6d39c2b819454ed26
#   5656244 | be621f7003ce70bff6d6d41566e4b510b2550c994ba091e772c4c6883bbcff95
#   5656243 | 99035b60fc332dd4de20bae9bfe32302e69fe5ca21c57f14bb46c845ae0821a5
#   5656242 | 477131b5d0e8cd6f38909753549356399068db3896a5bc70c8014275fa9919fc
#   5656241 | 500c1e6d3f0c351c6809bac71a826f1c6d2f3b04b73e7e6fad598017a942dc1b
#   5656240 | 2ce0809ed02d30e9108881c1e9197ca1b4b29e741b24cefb50108218fb09ef91
#   5656239 | 5e07d8fd677030a7217fcafe98d77982adae4d90d8e410432180d84590d21580
#   5656238 | 72335e955d4ed42451e87a3903855ae9d4a91d622f6a1107552f12baff602e44
#   5656237 | 0e4cfc51ac936b939cd6dbb7853efbad4c4260f5db8d37f0716ab3c766ca53d3

    active_scope: Scope = screenState.activeScope
    main_scope: Scope = active_scope.main_scope
    screenState.scope_exec_args = [screenState]
    main_scope.update()

    global BLOCK_STATES
    if BLOCK_STATES is None:
        import random

        height = 7052463
        block_states = []
        for i in range(30):
            tx_bool = True if random.random() < 0.35 else False
            block_states.append(ELEMENTS.BlockState(height + i, True, False, tx_bool, 0.2))
        block_states[-1].infused = False
        block_states.append(ELEMENTS.BlockState(-1, False, True, True, 0.8))
        block_states.reverse()
        BLOCK_STATES = block_states

    block_states = BLOCK_STATES  # only for testing

    if block_states is not None:
        ELEMENTS.create_block_band(stdscr, screenState, main_scope,
                                   "block band", block_states, UIgraph.Point(15, 2))

    width = screenState.screen_size.x
    height = screenState.screen_size.y

    if 'full_node_data' not in screenState.screen_data:
        screenState.screen_data['full_node_data'] = {}
        screenState.screen_data['full_node_data']['timestamp'] = time.time()
    timestamp_time = datetime.fromtimestamp(screenState.screen_data['full_node_data']['timestamp'])
    nLinesUsed = screenState.headerLines + screenState.footerLines
    node_data = stdscr.subwin(height - nLinesUsed, width, screenState.headerLines, 0)
    node_data.bkgd(' ', curses.color_pair(screenState.colorPairs["body"]))
    node_data.addstr(4, 4, "Timestamp: " + timestamp_time.strftime('%Y-%m-%d %H:%M:%S'))

    network_info = asyncio.run(call_rpc_fetch('get_network_info'))
    genesis_challenge = network_info["genesis_challenge"]
    network_name = network_info["network_name"]

    full_node_port = "8444"
    full_node_rpc_port = "8555"

    blockchain_state = call_rpc_node('get_blockchain_state')
    difficulty = blockchain_state["difficulty"]
    synced = blockchain_state["sync"]["synced"]
    sync_mode = blockchain_state["sync"]["sync_mode"]
    sub_slot_iters = blockchain_state["sub_slot_iters"]
    space = blockchain_state["space"]
    space = blockchain_state["space"] / (1024**6), ' Eib'
    node_id = blockchain_state["node_id"]

    try:
        row = 15
        col = 4
        node_data.addstr(row, col, f"Network: {network_name}    Port: {full_node_port}   RPC Port: {full_node_rpc_port}")
        row += 1
        node_data.addstr(row, col, f"Node ID: {node_id}")
        row += 1
        node_data.addstr(row, col, f"Genesis Challenge: {genesis_challenge}")
        row += 1

        peak = blockchain_state["peak"]
        peak_hash = peak['header_hash']
        peak_height = peak['height']
        peak_timestamp = peak['timestamp']

        if synced:
            node_data.addstr(row, col, f"Current Blockchain Status: Full Node Synced. Height: {peak['height']}")
            row += 1
            node_data.addstr(row, col, f"Peak: Hash: {peak['header_hash']}")
            # what kind of object is peak? block i suppose
            # check that the challenge block info hash is the header hash
            #node_data.addstr(row, col, f"Peak: Hash: {peak.header_hash}")
            row += 1
        elif peak is not None and sync_mode:
            sync_max_block = blockchain_state["sync"]["sync_tip_height"]
            sync_current_block = blockchain_state["sync"]["sync_progress_height"]
            node_data.addstr(row, col, f"Current Blockchain Status: Syncing {sync_current_block}/{sync_max_block} ({sync_max_block - sync_current_block} behind)."
            )
            row += 1
            node_data.addstr(row, col, f"Peak: Hash:  {peak['header_hash']}")
            row += 1
        elif peak is not None:
            node_data.addstr(row, col, f"Current Blockchain Status: Not Synced. Peak height: {peak['height']}")
            row += 1
        else:
            node_data.addstr(row, col, "Searching for an initial chain")
            row += 1
            node_data.addstr(row, col, "You may be able to expedite with 'chia peer full_node -a host:port' using a known node.\n")
            row += 1

        node_data.addstr(row, col, f"finished challenge: {peak['finished_challenge_slot_hashes']}, "
                                   f"infused: {peak['finished_infused_challenge_slot_hashes']}, "
                                   f"reward: {peak['finished_reward_slot_hashes']}")

        row += 1
        node_data.addstr(row, col, f"prev hash: {peak['prev_hash']}")
        row += 1
        node_data.addstr(row, col, f"prev transaction hash: {peak['prev_transaction_block_hash']}")
        row += 1

        if peak is not None:
            if peak['timestamp']:
                peak_time = peak['timestamp']
            else:
                curr_block_record = call_rpc_node('get_block_record', header_hash=peak['prev_hash'])
                while curr_block_record is not None and curr_block_record['timestamp'] is None:
                    curr_block_record = call_rpc_node('get_block_record', header_hash=curr_block_record['prev_hash'])
                if curr_block_record is not None:
                    peak_time = curr_block_record['timestamp']
                else:
                    peak_time = uint64(0)

            peak_time_struct = time.struct_time(time.localtime(peak_time))

            node_data.addstr(row, col, f"      Time: {time.strftime('%a %b %d %Y %T %Z', peak_time_struct)}                 Height: {peak_height:>10}")
            row += 1

            node_data.addstr(row, col, f"Estimated network space: {space}")
            row += 1
            #node_data.addstr(row, col, format_bytes(blockchain_state["space"]))
            node_data.addstr(row, col, f"Current difficulty: {difficulty}")
            row += 1
            node_data.addstr(row, col, f"Current VDF sub_slot_iters: {sub_slot_iters}")
            row += 1
            #node_data.addstr(row, col, "\n  Height: |   Hash:")

        row += 2
        # show last 7 blocks
        last_block_records = call_rpc_node('get_block_records', start=peak_height - 7, end=peak_height)

        for br in reversed(last_block_records):
            br_hash = br['header_hash']
            br_height = br['height']
            br_timestamp = br['timestamp']
            node_data.addstr(row, col, f"{br_height} | {br_hash} | is_tx: {br_timestamp}")
            row += 1

    except Exception as e:
        print(e)
        print("except what?")

    if keyboardState.esc is True:
        screenState.screen = 'main'

def screen_memepool(stdscr, keyboardState, screenState, figlet=False):
    pass

if True:
    #screenGenerators["debugging window"] = debugging_window
    pass


# move this part in a funciton to process input, and then run this inside the
# scope execution. Easier to change a scope behaviuor if needed.
# EG: func_input_proces_visual, func_input_process_insert
# and call it when the scope is active
def keyboard_processing(screen_state: ScreenState, keyboard_state: KeyboardState,
                     active_scope: Scope, key):


    if key == curses.KEY_ENTER or key == 10 or key == 13:
        keyboard_state.enter = True
    if key == 27:
        keyboard_state.esc = True

    match active_scope.mode:
        case ScopeMode.INSERT:
            match key:
                case curses.KEY_BACKSPACE:
                    idx = active_scope.data['cursor'] - 1
                    if idx < 0:
                        pass
                    else:
                        s = active_scope.data['prompt']
                        active_scope.data['prompt'] = s[:idx] + s[idx + 1:]
                        active_scope.data['cursor'] -= 1
                case curses.KEY_DC:
                    idx = active_scope.data['cursor']
                    s = active_scope.data['prompt']
                    if idx > len(s):
                        pass
                    else:
                        active_scope.data['prompt'] = s[:idx] + s[idx + 1:]
                case curses.KEY_LEFT:
                    active_scope.data['cursor'] -= 1
                case curses.KEY_RIGHT:
                    active_scope.data['cursor'] += 1
                case 22:  # ctrl-v
                    keyboard_state.paste = True
                    print('key paste')
                case (-1):
                    pass
                case _:
                    idx = active_scope.data['cursor']
                    s = active_scope.data['prompt']
                    active_scope.data['prompt'] = s[:idx] + chr(key) + s[idx:]
                    active_scope.data['cursor'] += 1

        case ScopeMode.VISUAL:
            print('visula')

            if key == ord('j') or key == curses.KEY_DOWN:
                keyboard_state.moveDown = True
            if key == ord('k') or key == curses.KEY_UP:
                keyboard_state.moveUp = True
            if key == ord('h') or key == curses.KEY_LEFT:
                keyboard_state.moveLeft = True
            if key == ord('l') or key == curses.KEY_RIGHT:
                keyboard_state.moveRight = True
            if key == curses.KEY_MOUSE:
                keyboard_state.mouse = True
            if key == ord('y'):
                keyboard_state.yank = True
                print('key yank')
            if key == ord('p'):
                keyboard_state.paste = True
                print('key paste')


def keyboard_execution(screen_state: ScreenState, keyboard_state: KeyboardState,
                       active_scope: Scope):

    if keyboard_state.enter is True:
        active_scope.exec_child(*screen_state.scope_exec_args)
        return
    if keyboard_state.esc is True:
        # exec_esc is not a method but a property
        # should i create a method to call it?
        active_scope.exec_esc(active_scope, *screen_state.scope_exec_args)
        return

    if keyboard_state.moveUp:
        active_scope.cursor -= 1
        screen_state.selection = -1
    if keyboard_state.moveDown:
        active_scope.cursor += 1
        screen_state.selection = 1
    if keyboard_state.moveLeft:
        active_scope.cursor_x -= 1
    if keyboard_state.moveRight:
        active_scope.cursor_x += 1


def interFace(stdscr):

    try:
        data_lock = threading.Lock()
        fingers_state: List[FingerState] = []
        fingers_list: List[int] = []
        finger_active: List[int] = [0]
        count_server = [0]
        coins_data: Dict[str, CoinPriceData] = {}

        frame_start = None
        frame_end = None
        frame_time = 0
        frame_time_max = 0
        frame_time_display = 0
        frame_count = 0

        # load data from WDB
        # create the WDB or load the data
        conn = sqlite3.connect(DB_WDB, timeout=SQL_TIMEOUT)
        WDB.create_wallet_db(conn)
        logging(server_logger, "DEBUG", f"WDB '{DB_WDB}' initialized successfully.")
        load_WDB_data(conn, fingers_state, fingers_list, coins_data, finger_active)
        conn.close()

        wallet_thread = threading.Thread(target=fetch_wallet,
                                         args=(data_lock,
                                               fingers_state,
                                               fingers_list,
                                               finger_active,
                                               coins_data,
                                               count_server),
                                         daemon=True)
        wallet_thread.start()


        key = 0

        curses.curs_set(0)  # set cursor visibility
        stdscr.nodelay(True)
        stdscr.erase()
        stdscr.refresh()
        # Enable mouse events
        curses.mousemask(curses.ALL_MOUSE_EVENTS)

        # trying to stop print
        # curses.noecho()
        # curses.cbreak()

        screenState = ScreenState()
        screenState.active_pk = [finger_active[0], screenState.active_pk[1]]

        # Start colors in curses
        curses.start_color()
        curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_CYAN)
        curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_RED)
        curses.init_pair(4, curses.COLOR_BLACK, curses.COLOR_YELLOW)
        curses.init_pair(5, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(6, curses.COLOR_BLACK, curses.COLOR_GREEN)
        curses.init_pair(7, curses.COLOR_GREEN, curses.COLOR_BLACK)

        # curse customs colors
        screenState.cursesColors = UIgraph.CustomColors(10)
        white = (254, 250, 250)
        darkBlue = (60, 70, 120)

        # creare nomi delle cose da colorare piu che il nome del colore
        # riservare altri n. colori per la palette dell'interfacci e poi altri colori

        white_id = UIgraph.addCustomColor(white, screenState.cursesColors)
        darkBlue_id = UIgraph.addCustomColor(darkBlue, screenState.cursesColors)
        # colors: header, footer, main_screen

        global white_darkBlue  # avoid using a global for colors
        white_darkBlue = UIgraph.addCustomColorTuple(
            (white_id, darkBlue_id),
            screenState.cursesColors)
        darkBlue_white = UIgraph.addCustomColorTuple(
            (darkBlue_id, white_id),
            screenState.cursesColors)

        # screenState.colors["chia_green"] = UIgraph.addCustomColor([92, 206, 113],
        # screenState.colors["chia_green"] = UIgraph.addCustomColor([0, 165, 37],
        screenState.colors["chia_green"] = UIgraph.addCustomColor(
            (47, 165, 67),
            screenState.cursesColors)
        screenState.colors["yellow_bee"] = UIgraph.addCustomColor(
            (255, 190, 0),
            screenState.cursesColors)
        screenState.colors["orange_red"] = UIgraph.addCustomColor(
            (244, 43, 3),
            screenState.cursesColors)
        screenState.colors["orange_ee"] = UIgraph.addCustomColor(
            (244, 143, 3),
            screenState.cursesColors)
        screenState.colors["background"] = UIgraph.addCustomColor(
            (0, 10, 45),
            screenState.cursesColors)
        screenState.colors["azure_up"] = UIgraph.addCustomColor(
            (80, 150, 210),
            screenState.cursesColors)
        screenState.colors["white_down"] = UIgraph.addCustomColor(
            (250, 245, 245),
            screenState.cursesColors)
        screenState.colors["tab_dark"] = UIgraph.addCustomColor(
            (0, 10, 45),
            screenState.cursesColors)
        screenState.colors["tab_soft"] = UIgraph.addCustomColor(
            (28, 36, 68),
            screenState.cursesColors)
        screenState.colors["tab_softer"] = UIgraph.addCustomColor(
            (38, 46, 78),
            screenState.cursesColors)
        screenState.colors["tab_selected"] = UIgraph.addCustomColor(
            (244, 43, 3),
            screenState.cursesColors)
        screenState.colors["bar_dark"] = UIgraph.addCustomColor(
            (20, 25, 50),
            screenState.cursesColors)
        screenState.colors["bar_soft"] = UIgraph.addCustomColor(
            (35, 40, 80),
            screenState.cursesColors)
        screenState.colors["orange_btc"] = UIgraph.addCustomColor(
            (247, 148, 19),
            screenState.cursesColors)
        screenState.colors["white"] = UIgraph.addCustomColor(
            (244, 245, 250),
            screenState.cursesColors)
        screenState.colors["blue_dollar"] = UIgraph.addCustomColor(
            (46, 121, 204),
            screenState.cursesColors)
        screenState.colors["green_dollar"] = UIgraph.addCustomColor(
            (107, 128, 104),
            screenState.cursesColors)

        screenState.colorPairs["intro"] = UIgraph.addCustomColorTuple(
            (curses.COLOR_WHITE, screenState.colors["chia_green"]),
            screenState.cursesColors)
        screenState.colorPairs["chia_wallet"] = UIgraph.addCustomColorTuple(
            (curses.COLOR_WHITE, screenState.colors["chia_green"]),
            screenState.cursesColors)
        screenState.colorPairs["chia_wallet_bg"] = UIgraph.addCustomColorTuple(
            (screenState.colors["chia_green"], screenState.colors["background"]),
            screenState.cursesColors)
        screenState.colorPairs["header"] = UIgraph.addCustomColorTuple(
            (curses.COLOR_BLACK, screenState.colors["yellow_bee"]),
            screenState.cursesColors)
        screenState.colorPairs["body"] = UIgraph.addCustomColorTuple(
            (screenState.colors["chia_green"], screenState.colors["background"]),
            screenState.cursesColors)
        screenState.colorPairs["body_sel"] = UIgraph.addCustomColorTuple(
            (screenState.colors["background"], screenState.colors["chia_green"]),
            screenState.cursesColors)
        screenState.colorPairs["footer"] = UIgraph.addCustomColorTuple(
            (curses.COLOR_BLACK, screenState.colors["orange_red"]),
            screenState.cursesColors)
        screenState.colorPairs["test"] = UIgraph.addCustomColorTuple(
            (screenState.colors["yellow_bee"], screenState.colors["orange_red"]),
            screenState.cursesColors)
        screenState.colorPairs["test_red"] = UIgraph.addCustomColorTuple(
            (screenState.colors["orange_red"], screenState.colors["orange_red"]),
            screenState.cursesColors)
        screenState.colorPairs["up"] = UIgraph.addCustomColorTuple(
            (screenState.colors["azure_up"], screenState.colors["background"]),
            screenState.cursesColors)
        screenState.colorPairs["down"] = UIgraph.addCustomColorTuple(
            (screenState.colors["white_down"], screenState.colors["background"]),
            screenState.cursesColors)
        screenState.colorPairs["tab_dark"] = UIgraph.addCustomColorTuple(
            (screenState.colors["chia_green"], screenState.colors["tab_dark"]),
            screenState.cursesColors)
        screenState.colorPairs["tab_soft"] = UIgraph.addCustomColorTuple(
            (screenState.colors["chia_green"], screenState.colors["tab_soft"]),
            screenState.cursesColors)
        screenState.colorPairs["tab_soft_bg"] = UIgraph.addCustomColorTuple(
            (screenState.colors["tab_soft"], screenState.colors["tab_dark"]),
            screenState.cursesColors)
        screenState.colorPairs["tab_dark_bg"] = UIgraph.addCustomColorTuple(
            (screenState.colors["tab_dark"], screenState.colors["tab_soft"]),
            screenState.cursesColors)
        screenState.colorPairs["tab_select"] = UIgraph.addCustomColorTuple(
            (screenState.colors["background"], screenState.colors["chia_green"]),
            screenState.cursesColors)
        screenState.colorPairs["tab_selected"] = UIgraph.addCustomColorTuple(
            (screenState.colors["chia_green"], screenState.colors["tab_selected"]),
            screenState.cursesColors)
        screenState.colorPairs["win_select"] = UIgraph.addCustomColorTuple(
            (screenState.colors["yellow_bee"], screenState.colors["background"]),
            screenState.cursesColors)
        screenState.colorPairs["bar_dark"] = UIgraph.addCustomColorTuple(
            (screenState.colors["chia_green"], screenState.colors["bar_dark"]),
            screenState.cursesColors)
        screenState.colorPairs["bar_soft"] = UIgraph.addCustomColorTuple(
            (screenState.colors["chia_green"], screenState.colors["bar_soft"]),
            screenState.cursesColors)
        screenState.colorPairs["xch"] = UIgraph.addCustomColorTuple(
            (screenState.colors["white"], screenState.colors["chia_green"]),
            screenState.cursesColors)
        screenState.colorPairs["btc"] = UIgraph.addCustomColorTuple(
            (screenState.colors["white"], screenState.colors["orange_btc"]),
            screenState.cursesColors)
        screenState.colorPairs["dollar"] = UIgraph.addCustomColorTuple(
            (screenState.colors["white"], screenState.colors["green_dollar"]),
            screenState.cursesColors)
        screenState.colorPairs["win_selected"] = UIgraph.addCustomColorTuple(
            (screenState.colors["yellow_bee"], screenState.colors["background"]),
            screenState.cursesColors)
        screenState.colorPairs["copy_banner"] = UIgraph.addCustomColorTuple(
            (screenState.colors["white"], screenState.colors["tab_softer"]),
            screenState.cursesColors)

    except Exception as e:
        print("color creation")
        print(e)
        traceback.print_exc()

    # create the intro and the main menu scopes
    scopeIntro = Scope('intro', screen_intro, screenState)
    scopeMainMenu = Scope('main_menu', screen_main_menu, screenState)

    scopeMainMenu.exec = activate_scope
    scopeIntro.sub_scopes[scopeMainMenu.name] = scopeMainMenu
    screenState.activeScope = scopeIntro

    try:

        # begin_x = 38
        # begin_y = 40
        height = 50
        width = 20

        # win = curses.newwin(height, width, begin_y, begin_x)
        frame_start = time.perf_counter()
        while key != ord('q'):
            stdscr.erase()
            keyboardState = KeyboardState()

            # update wallet data. (ADD A LOCK HERE)
            for fs in fingers_state:
                screenState.public_keys[fs.fingerprint] = fs
            if screenState.active_pk[0] == 0:
                screenState.active_pk = [finger_active[0], screenState.active_pk[1]]

            # update coin data
            with data_lock:
                screenState.coins_data = coins_data

            height, width = stdscr.getmaxyx()
            screenState.screen_size = UIgraph.Point(width, height)
            windowDim = f"width={width}; height={height}"
            # the 32 and 16 can
            if width < 32 or height < 16:
                if width < 32 or height < 4:
                    print("The window terminal is too small")
                    break
                    # don use curse and print too small
                else:
                    dinky = stdscr.subwin(height, width, 0, 0)
                    dinky.bkgd(' ', curses.color_pair(screenState.colorPairs["footer"]))
                    text = "am i a dinky puppy terminal?"
                    dinky.addstr(height // 2, width // 2 - len(text) // 2, text)
            else:
                header = stdscr.subwin(1, width, 0, 0)
                header.bkgd(' ', curses.color_pair(screenState.colorPairs["header"]))
                # y, x = 0, width - len(windowDim)
                # header.addstr(y, x, windowDim, curses.color_pair(3)) # it is not possible to write on the last char of a window
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
                # write on the right but not in the window, but on the main screen
                # fps = f"fps: {fps} | second per frame: {frame_time_display}; "
                fps = f"second per frame: {frame_time_display:.5f}; "
                window_info = fps + windowDim
                y, x = 0, width - len(window_info) - 1
                header.addstr(y, x, window_info)


                nLinesHeader = (len(title) + len(windowDim)) // width + 1
                screenState.headerLines = nLinesHeader

                # debug footer
                # helper
                footerText = "Movement: down=j up=k left=h right=l confirm=enter back=esc q=quit"
                nLines = int(len(footerText) / width + 1)
                footer = stdscr.subwin(nLines, width, height-nLines, 0)
                footer.bkgd(' ', curses.color_pair(screenState.colorPairs["footer"]))
                footer.addstr(0, 0, footerText)

                # server wallet monitor
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
                extraLines = 1

                global DEBUG_TEXT
                #DEBUG_TEXT = f"{DEBUG_TEXT} --- {DEBUG_OBJ.text}"
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
                activeScope = screenState.activeScope
                keyboard_processing(screenState, keyboardState, activeScope, key)
                activeScope.screen(stdscr, keyboardState,
                                   screenState)
                keyboard_execution(screenState, keyboardState, activeScope)


            # html tables: https://www.w3.org/TR/xml-entity-names/026.html

            curses.doupdate()
            frame_end = time.perf_counter()
            frame_time = frame_end - frame_start
            if frame_time > frame_time_max:
                frame_time_max = frame_time
            frame_count += 1
            if frame_count == 20:
                frame_count = 0
                frame_time_display = frame_time_max
                frame_time_max = 0

            # cap frame rate
            fps = 30
            sleep_time = 1/fps - frame_time
            if sleep_time > 0:
                time.sleep(sleep_time)
            frame_start = time.perf_counter()
            # stdscr.refresh()
            key = stdscr.getch()

    except Exception as e:
        print("error in the loop")
        print(e)
        traceback.print_exc()


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
        response = await wallet_client.fetch(method_name, kwargs)
        return response

    except Exception:
        logging(server_logger, "DEBUG", f"sometime wrong with a wallet rpc call.")
        logging(server_logger, "DEBUG", f"the rpc call was {str(kwargs)} and {str(args)}")
        logging(server_logger, "DEBUG", f"traceback: {traceback.format_exc()}")
        wallet_client.close()
        await wallet_client.await_closed()
        return False

    finally:
        wallet_client.close()
        await wallet_client.await_closed()


async def call_rpc_wallet_legacy(method_name, *args, **kwargs):
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


async def call_rpc_fetch(method_name, *args, **kwargs):
    """Arguments has to be passed as json with the name of the
    parameter {"block_header:0xa892ef029.."}"""
    try:
        full_node_client = await FullNodeRpcClient.create(
            self_hostname, uint16(full_node_rpc_port), DEFAULT_ROOT_PATH, config
        )
        #rpc_method = getattr(full_node_client, method_name)
        #response = await rpc_method(*args, **kwargs)
        response = await full_node_client.fetch(method_name, kwargs)
        return response
    except Exception as e:
        print("sometime wrong with an rpc call using the fetch method")
        print(e)

    finally:
        full_node_client.close()
        await full_node_client.await_closed()


class StdOutWrapper:
    text = ""

    def write(self, txt):
        self.text += txt
        self.text = '\n'.join(self.text.split('\n')[-300:])

    def get_text(self,beg=0,end=-1):
        """I think it is reversed the order, i should change it"""
        return '\n'.join(self.text.split('\n')[beg:end]) + '\n'

#if __name__ == "__main__":
#
#    screen = curses.initscr()
#    curses.noecho()
#    curses.cbreak()
#
#    # do your stuff here
#    # you can also output mystdout.get_text() in a ncurses widget in runtime
#
#    screen.keypad(0)
#    curses.nocbreak()
#    curses.echo()
#    curses.endwin()


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
        curses.nocbreak()
        curses.echo()
        curses.endwin()
        print("The exception of main is: ", e)
        print(traceback.format_exc())

    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__
    sys.stdout.write(mystdout.get_text())
