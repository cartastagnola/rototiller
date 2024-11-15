#!/usr/bin/env python3

import sys, os, traceback
import asyncio
import curses
import time
import threading
import requests
import json

from dataclasses import dataclass
from typing import List, Tuple, Dict, Union, Callable
from datetime import datetime, timedelta

#from chia.wallet.util.tx_config import DEFAULT_TX_CONFIG
from chia.util.default_root import DEFAULT_ROOT_PATH
from chia.util.config import load_config

from chia.rpc.full_node_rpc_client import FullNodeRpcClient
from chia.rpc.rpc_server import RpcServer
from chia.rpc.wallet_rpc_client import WalletRpcClient
from chia.daemon.client import connect_to_daemon_and_validate
from chia.types.blockchain_format.sized_bytes import bytes32, bytes48
from chia.util.ints import uint16, uint32, uint64

# setup the node
# config/config.yaml
config = load_config(DEFAULT_ROOT_PATH, "config.yaml")
self_hostname = config["self_hostname"]  # localhost
full_node_rpc_port = config["full_node"]["rpc_port"]  # 8555
wallet_rpc_port = config["wallet"]["rpc_port"]  # 9256

# test temp for cats

# set the esc delay to 25 milliseconds (the defaul is 1 sec)
# by default curses use one seconds
os.environ.setdefault('ESCDELAY', '25')

sys.path.append('/home/boon/gitRepos/Chia-Py-RPC/src/')
from chia_py_rpc.wallet import Wallet
from chia_py_rpc.wallet import WalletManagement
from chia_py_rpc.wallet import KeyManagement


sys.path.append('/home/boon/gitRepos/')
import dex as dex
import UItext as UItext
import UIgraph as UIgraph
import LOGtiller as LOGtiller

DEBUGGING = True
LOGGING_LEVEL = "DEBUG"
a = LOGtiller.LoggingLevels.INFO
server_logger = LOGtiller.AsyncLogger("./server_log.log", LOGGING_LEVEL)
server_logger_thread = LOGtiller.launchLoggerThread(server_logger, "hole")
logging = LOGtiller.logging


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
    data: str # it should be byte32 (the data of what?)
    name: str #
    ticker: str #
    block_height: uint32
    addresses: List[str]  # check type and move to pkState
    coins: List #coinrecords, but it could be also coins
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
    coin_tail: str # for chia is "chia"
    current_price: float
    current_price_currency: float
    current_price_date: int  # timestamp milliseconds
    historic_price: Dict[int, float]  #[timestamp, price]
    historic_price_currency: Dict[int, float]  #[timestamp, price]
    historic_price_date: Tuple[int, int]  # [timestamp (begin period), timestamp (end period)]

    def __init__(self):
        self.coin_tail = None
        self.current_price = None
        self.current_price_currency = None
        self.current_price_date = None
        self.historic_price = None
        self.historic_price_currency = None
        self.historic_price_date = None

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
    mouse: bool = False
    enter: bool = False
    esc: bool = False


@dataclass
class ScreenState:
    init: bool
    selection: int
    select_y: int
    screen: str
    cursesColors: UIgraph.CustomColors
    colors: Dict[str, int]
    colorPairs: Dict[str, int]
    menu: List[str]
    nLinesUsed: int
    headerLines: int
    footerLines: int
    active_pk: List[Union[int, bool]]  # [is fing selected, fingerprint]
    public_keys: Dict[int, PkState]  # check what kind of int is a pk, and change wallets to something that belond to a public key
    activeScope: 'Scope'  # active scope
    scopes: Dict[str, 'Scope']
    screen_data: Dict[str, str]  # it should be a dic of lists of anything
    coins_data: Dict[str, CoinPriceData]

    def __init__(self):
        self.init = False
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
        self.active_scope = None
        self.scopes = {}
        self.screen_data = {}
        self.coins_data = {}


class Scope():
    gen_id = 0

    def __init__(self, name: str, screen_handler: Callable[..., None],
                 screenState: ScreenState):
        self.name = name
        self.selected = False
        self.parent_scope = None
        self.sub_scopes = {}
        self.cursor = 0
        self.bool = False
        self.state = None
        self.id = Scope.gen_id
        self.exec = None
        self.screen = screen_handler
        # add the variable that keep the info of what screen to print
        Scope.gen_id += 1
        screenState.scopes[name] = self

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
        if self.active:
            if circular:
                self.cursor = self.cursor % row_count
            else:
                if self.cursor < 0:
                    self.cursor = 0
                elif self.cursor >= row_count:
                    self.cursor = row_count - 1

    def exec_child(self, *args):
        idx = self.cursor % len(self.sub_scopes)  # i could delete the modulus
        # on the scope part? we need this when the child scope are less then
        # the element you can navigate in the same scope
        child_scope_key = list(self.sub_scopes.keys())[idx]
        child_scope = self.sub_scopes[child_scope_key]
        child_scope.exec_self(*args)

    def exec_self(self, *args):
        """Execute the function stored in the self.exec"""
        self.exec(self, *args)


# to remove it as global
tickers = 0


def convert_historic_price_to_currency(historic_timestamp_chia, historic_price_chia,
                                       historic_timestamp_cat, historic_price_cat):
    """Convert historic price of a pair with xch to another currency.
    'historic_price_chia are the historic price of chia mesured in another currency"""

    len_chia_ts = len(historic_timestamp_chia)
    u = 0
    new_historic_price_cat = []
    for n, i in enumerate(historic_timestamp_cat):
        diff = abs(i - historic_timestamp_chia[u])
        while u < len_chia_ts:
            next_diff = abs(i - historic_timestamp_chia[u])
            if next_diff >= diff:
                break
            u += 1
        new_historic_price_cat.append(historic_price_cat[n] * historic_price_chia[u])

    return new_historic_price_cat


# fetch coin data
def fetch_coin_data(data_lock, coins_data, tail):
    "fetch data for a coin"

    logging(server_logger, "DEBUG", f"fetching CAT's data with tail: {tail}")

    try:
        current_price = dex.get_current_price_from_tail(tail)
        historic_price, historic_timestamp = dex.getHistoricPriceFromTail(tail, 7)

        if len(historic_price) == 0:
            historic_price.append(current_price)
            historic_timestamp.append(int(datetime.now().timestamp() * 1000))

        with data_lock:
            if tail not in coins_data:
                coins_data[tail] = CoinPriceData()
                coins_data[tail].tail = tail
            current_price_chia = coins_data['chia'].current_price_currency
            historic_timestamp_chia = list(coins_data['chia'].historic_price.keys())
            historic_price_chia = list(coins_data['chia'].historic_price.values())

            coins_data[tail].current_price = current_price
            coins_data[tail].current_price_currency = current_price * current_price_chia
            coins_data[tail].current_price_date = int(datetime.now().timestamp() * 1000)
            coins_data[tail].historic_price = dict(zip(historic_timestamp, historic_price))
            historic_price_currency = convert_historic_price_to_currency(
                historic_timestamp_chia, historic_price_chia,
                historic_timestamp, historic_price)
            coins_data[tail].historic_price_currency = dict(zip(historic_timestamp,
                                                                historic_price_currency))
            end = datetime.now()
            begin = int((end - timedelta(days=7)).timestamp())
            coins_data[tail].historic_price_date = (begin, end)

    except Exception as e:
        logging(server_logger, "DEBUG", f"fetching coindata error {tail}")
        logging(server_logger, "DEBUG", f"Balance error. Exception: {e}")
        logging(server_logger, "DEBUG", f"Traceback: {traceback.format_exc()}")
        traceback.print_exc()

def fetch_chia_data(data_lock, coins_data):
    "fetch data for a coin"

    logging(server_logger, "DEBUG", "fetching chia's data")

    try:
        # lock now to be sure chia is the first entry and it is available for later entries
        with data_lock:
            # retrive last 7 days
            chia_id = 'chia' # will be use as 'tail' reference for the price data
            currency = 'usd'
            days = '7'

            # Construct the API URL
            url = f"https://api.coingecko.com/api/v3/coins/{chia_id}/market_chart?vs_currency={currency}&days={days}"

            # Send the request to CoinGecko API
            response = requests.get(url)

            # Parse the JSON response
            data = response.json()

            # Extract relevant information (e.g., prices over the last 7 days)
            prices = data['prices']
            current_price = prices[-1]
            historic_timestamp = []
            historic_price = []
            for i in prices:
                historic_timestamp.append(i[0])
                historic_price.append(i[1])

            if chia_id not in coins_data:
                coins_data[chia_id] = CoinPriceData()
                coins_data[chia_id].tail = chia_id
            coins_data[chia_id].current_price= 1
            coins_data[chia_id].current_price_currency = current_price[1]
            coins_data[chia_id].current_price_date = current_price[0]
            coins_data[chia_id].historic_price = dict(zip(historic_timestamp,
                                                          [1] * len(historic_price)))
            coins_data[chia_id].historic_price_currency = dict(zip(historic_timestamp,
                                                                   historic_price))
            end = datetime.now()
            begin = int((end - timedelta(days=7)).timestamp())
            coins_data[chia_id].historic_price_date = (begin, end)

    except Exception as e:
        logging(server_logger, "DEBUG", f"fetching chia coindata error from coin geko")
        logging(server_logger, "DEBUG", f"Balance error. Exception: {e}")
        logging(server_logger, "DEBUG", f"Traceback: {traceback.format_exc()}")
        traceback.print_exc()


# wallet fetcher
def fetch_wallet(data_lock, fingers_state, fingers_list, finger_active,
                 coins_data, count_server):

    logging(server_logger, "DEBUG", "wallet fetcher started.")

    while True:

        count_server[0] += 1
        logging(server_logger, "DEBUG", f'wallet fetcher loop counting: {count_server[0]}')

        original_logged_finger = asyncio.run(call_rpc_wallet('get_logged_in_fingerprint'))#['fingerprint']
        finger_active[0] = original_logged_finger

        fingerprints = []

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
            for finger in fingerprints:
                if finger in fingers_list:
                    continue
                else:
                    new_pk = PkState()
                    new_pk.fingerprint = finger
                    key = asyncio.run(call_daemon_rpc("get_key",
                                                      fingerprint=finger))['key']
                    new_pk.pk = key["public_key"]
                    new_pk.label = key["label"]
                    fingers_list.append(finger)
                    fingers_state.append(new_pk)

            logging(server_logger, "DEBUG", f'fingerprint loading ended')

        except Exception as e:
            logging(server_logger, "DEBUG", "probably there is no chia node and wallet running")
            logging(server_logger, "DEBUG", f"Exception: {e}")


        #################### LOAD WALLET ########################
        try:
            logging(server_logger, "DEBUG", f'loading wallet.\n\n')

            for finger in fingerprints:

                logged_finger = asyncio.run(call_rpc_wallet('get_logged_in_fingerprint'))
                if logged_finger != finger:
                    result = asyncio.run(call_rpc_wallet('log_in', fingerprint=finger))
                    print(result)

                idx = fingers_list.index(finger)
                wallets = fingers_state[idx].wallets

                # chia wallet
                chia_wallet: WalletState  = WalletState()
                response = asyncio.run(call_rpc_wallet('get_wallet_balance', wallet_id=1))
                print(response)

                if response["success"]:
                    response = response["wallet_balance"]
                else:
                    raise ConnectionError("The rpc call failed.")
                chia_wallet.confirmed_wallet_balance = response['confirmed_wallet_balance']
                chia_wallet.spendable_balance = response['spendable_balance']
                chia_wallet.unspent_coin_count = response['unspent_coin_count']
                chia_wallet.name = "Chia"
                chia_wallet.ticker = "XCH"
                chia_data_thread = threading.Thread(target=fetch_chia_data,
                                                    args=(data_lock,
                                                            coins_data),
                                                    daemon=True)
                chia_data_thread.start()

                wallets["chia"] = chia_wallet
                print(chia_wallet)
                print('done')

                # add CATs
                cat_chia_wallets = asyncio.run(
                    call_rpc_wallet('get_wallets', type=6))["wallets"]
                print('all wallets')
                print(cat_chia_wallets)
                for e, i in enumerate(cat_chia_wallets):
                    cat_wallet = WalletState()
                    balance = None
                    coins = []
                    try:
                        balance = asyncio.run(
                            call_rpc_wallet('get_wallet_balance', wallet_id=i['id']))["wallet_balance"]
                    except Exception as e:
                        logging(server_logger, "DEBUG", f"Balance error. Exception: {e}")
                        logging(server_logger, "DEBUG", f"Traceback: {traceback.format_exc()}")
                        traceback.print_exc()

                    try:
                        for u in range(10):
                            coins = asyncio.run(
                                call_rpc_wallet('get_spendable_coins', wallet_id=i['id']))
                            if not coins:
                                time.sleep(5)
                                continue
                            coins = coins["confirmed_records"]
                            cat_wallet.coins = coins[0]
                    except Exception as e:
                        logging(server_logger, "DEBUG", f"Coin retrive error. Exception: {e}")
                        logging(server_logger, "DEBUG", f"Traceback: {traceback.format_exc()}")
                        traceback.print_exc()

                    transactions = asyncio.run(call_rpc_wallet('get_transactions',
                                                               wallet_id=i['id']))["transactions"]
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
                                                    t["name"]
                        ))
                    print('something')
                    try:
                        cat_wallet.transactions = transactions_roto
                    except Exception as e:
                        logging(server_logger, "DEBUG", f"Exception: {e}")
                        logging(server_logger, "DEBUG", f"Traceback: {traceback.format_exc()}")
                        traceback.print_exc()

                    print(balance)
                    cat_wallet.data = balance['asset_id'] # it is the tail...
                    #print(f'cata wallet data: ', cat_wallet.data)
                    dexi_name = dex.fetchDexiNameFromTail(cat_wallet.data)
                    #print(f"dexi data: ", dexi_name)
                    # fetch prices from dexi
                    coin_data_thread = threading.Thread(target=fetch_coin_data,
                                                        args=(data_lock,
                                                              coins_data,
                                                              cat_wallet.data),
                                                        daemon=True)
                    coin_data_thread.start()

                    CAT_COST = 1000
                    cat_wallet.name = dexi_name['name']
                    cat_wallet.ticker = dexi_name['symbol']
                    cat_wallet.confirmed_wallet_balance = balance['confirmed_wallet_balance'] / CAT_COST
                    cat_wallet.spendable_balance = balance['spendable_balance'] / CAT_COST
                    cat_wallet.unspent_coin_count = balance['unspent_coin_count'] / CAT_COST
                    # bedore i was using the wallet id of the cat wallet.
                    # now i am using the cat tail
                    #wallets[i['id']] = cat_wallet
                    wallets[cat_wallet.data] = cat_wallet
                    # evaluate if it is better to use the byte32 name


                # add fake coins for testing
                for e, cat_tail in enumerate(cat_test):
                    if cat_tail in wallets:
                        continue
                    cat_wallet = WalletState()
                    balance = 999
                    cat_wallet.data = cat_tail
                    dexi_name = dex.fetchDexiNameFromTail(cat_wallet.data)
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


def screen_main_menu(stdscr, keyboardState, screenState, height, width, figlet=False):

    menu_win = createFullSubWin(stdscr, screenState, height, width)
    menu_win.bkgd(' ', curses.color_pair(screenState.colorPairs["body"]))

    activeScope: Scope = screenState.activeScope

    if len(activeScope.sub_scopes) == 0:
        menu_items = [
            ('wallet', screen_fingers),
            ('full node', screen_full_node),
            ('harvester analytics', screen_harvester),
            ('dex', screen_dex)
        ]
        if DEBUGGING:
            menu_items += [
                ("tabs", screen_tabs),
                ('debugging screen', screen_debugging)
            ]

        def activate_scope(scope: Scope, screenState):
            screenState.activeScope = scope
            return scope

        for name, handler in menu_items:
            newScope = Scope(name, handler, screenState)
            newScope.exec = activate_scope
            newScope.parent_scope = activeScope
            activeScope.sub_scopes[name] = newScope

    # creare il menu usando i subscope come guida

    #if not screenState.init:
    #    screenState.screen = 'main'
    #    screenState.selection = 0
    #    screenState.menu = ["wallet", "full node", "harvester analytics", "dexi", "tabs", "debugging window"]
    #    screenState.init = True

    #if keyboardState.enter is True:
    #    screenState.screen = screenState.menu[screenState.selection]
    #    screenState.selection = 0
    #if keyboardState.moveUp:
    #    screenState.selection -= 1
    #if keyboardState.moveDown:
    #    screenState.selection += 1

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

        xMenu = int(width/2 - xDimMenu / 2)
        yMenu = int(height/2 - yDimMenu / 2)

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


def screen_dex(stdscr, keyboardState, screenState, height, width, figlet=False):

    # select pair
    if 'dex' not in screenState.screen_data:
        screenState.screen_data["dex"] = {}
        screenState.screen_data["dex"]["tickers"] = loadAllTickers()
    if "idxFirst" not in screenState.screen_data:
        screenState.screen_data["dex"]["idxFirst"] = 0

    tickers = screenState.screen_data["dex"]["tickers"]
    select = screenState.selection
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
doomFont = UItext.Font()
# import Path or do something else
pathA = UItext.Path("/home/boon/gitRepos/pyfiglet/pyfiglet/fonts-standard/doom.flf")
UItext.loadFontFTL(pathA, doomFont)

FUTURE_FONT = UItext.Font()
# import Path or do something else
pathA = UItext.Path("/home/boon/gitRepos/pyfiglet/pyfiglet/fonts-standard/future.tlf")
UItext.loadFontFTL(pathA, FUTURE_FONT)

def screen_intro(stdscr, keyboardState, screenState, height, width):
    """Intro screen"""

    # intro
    text = 'rototiller'

    sizeX, sizeY = UItext.sizeText(text, doomFont)
    stdscr.bkgd(' ', curses.color_pair(screenState.colorPairs["intro"]))
    print('screen color pairs')
    print(screenState.colorPairs["intro"])
    print(UIgraph.customColorsPairs_findByValue(
        screenState.cursesColors,
        screenState.colorPairs["intro"]))

    if height > sizeY * 2 and width > sizeX * 2:

        s = UItext.renderFont(text, doomFont)
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

def screen_debugging(stdscr, keyboardState, screenState, height, width):

    debug_win = createFullSubWin(stdscr, screenState, height, width)
    debug_win.bkgd(' ', curses.color_pair(screenState.colorPairs["body"]))
    if "scopes" not in screenState.screen_data:
        screenState.screen_data["scopes"] = {}
        screenState.screen_data["active_scope"] = None
    if "deb_win" not in screenState.screen_data["scopes"]:
        main_scope = Scope()

        def get_N_scope(scope: Scope):
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

        main_scope.exe = get_N_scope
        main_scope.active = True

        screenState.screen_data["scopes"]["deb_win"] = main_scope
        screenState.screen_data["active_scope"] = main_scope

    main_scope = screenState.screen_data["scopes"]["deb_win"]
    main_scope.update()
    active_scope = screenState.screen_data["active_scope"]

    # asset view
    if True:
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
            call_rpc_wallet('get_spendable_coins', wallet_id=2))["confirmed_records"][0]
        debug_win.addstr(3, 10, f"coins are :{str(coins)}")
        print(coins)
        for i, c in enumerate(coins):
            print('loop')
            print(c)
            print(type(c))
            debug_win.addstr(3,10 + i, f"coins are :{str(c.coin.amount)}")


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
        create_button(stdscr, screenState, main_scope, "button_1", point_xy, False)

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
        print("full char  done")
        deltaP = UIgraph.Point(5,5)
        deltaP = UIgraph.Point(0,0)
        p_bug = UIgraph.Point(58,12)
        try:
            UIgraph.drawLine2pts_aliasing_sub(debug_win, screenState, pt3 + deltaP,
                                            pt4 + deltaP, screenState.colorPairs['body'])
            #UIgraph.drawLine2pts(debug_win, pt3, pt4)
        except Exception as e:
            print("aaaaaaaaaa sub")
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
        #    a = dex.fetchDexiNameFromTail(cat)
        #    print(a)
        #    dex.getHistoricPriceFromTail(cat, 7)
        print(cat_test.keys())
        cat = list(cat_test.keys())[0]
        #prices, timestamp = dex.getHistoricPriceFromTail(cat, 7)
        #UIgraph.drawPriceGraph(stdscr, screenState, prices, timestamp, 7)
        y0 = 2
        for i in range(7):
            graph_win = stdscr.subwin(5, 20, y0, 40)
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
            #prices, timestamp = dex.getHistoricPriceFromTail(cat, 7)
            UIgraph.drawPriceGraph(graph_win, screenState, prices, timestamp, 7)
            y0 += 6

        #graph_win = stdscr.subwin(10, 20, 8, 30)
        #graph_win.bkgd(' ', curses.color_pair(screenState.colorPairs["test_red"]))
        #cat = list(cat_test.keys())[0]
        #prices, timestamp = dex.getHistoricPriceFromTail(cat, 7)
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
                #screenState.screen_data[tabName]["tickers"] = loadAllTickers()
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

def screen_coin_wallet(stdscr, keyboardState, screenState, height, width):

    wallet_win = createFullSubWin(stdscr, screenState, height, width)
    wallet_win.bkgd(' ', curses.color_pair(screenState.colorPairs["body"]))

    # wallet
    pk: PkState = screenState.public_keys[screenState.active_pk[0]]
    wallets: Dict[int, WalletState] = pk.wallets
    finger = pk.fingerprint

    active_scope = screenState.screen_data["active_scope"]

    cat_wallet: WalletState = wallets[active_scope.state]
    y = 20
    wallet_win.addstr(y, 10, f"Ticker: {cat_wallet.ticker} - {cat_wallet.name}")
    y += 1
    wallet_win.addstr(y, 10, f"name {cat_wallet.confirmed_wallet_balance}")
    y += 1
    wallet_win.addstr(y, 10, f"confirmed balance {cat_wallet.confirmed_wallet_balance}")
    y += 1
    wallet_win.addstr(y, 10, f"spendable balance {cat_wallet.spendable_balance}")
    y += 1
    wallet_win.addstr(y, 10, f"unspent coin count {cat_wallet.unspent_coin_count}")
    y += 1
    wallet_win.addstr(y, 10, f"block height {cat_wallet.block_height}")

    # show coins by address

    # show coins by coin
    wallet_win.addstr(y, 10, f"coins...")
    y += 1
    for c in cat_wallet.coins:
        wallet_win.addstr(y, 10, f"coin {c.coin.amount}, {c.coin.puzzle_hash.hex()}")
        y += 1
        pass

    addresses = {}
    for c in cat_wallet.coins:
        adx = c.coin.puzzle_hash.hex()
        if adx in addresses:
            addresses[adx].append(c.coin.amount)
        else:
            addresses[adx] = [c.coin.amount]

    wallet_win.addstr(y, 10, f"len of the adds: {len(addresses)}")
    y += 1
    wallet_win.addstr(y, 10, f"addresses...")
    y += 1
    for k, amounts in addresses.items():
        wallet_win.addstr(y, 10, f"address: {k}, amount: {c.coin.puzzle_hash.hex()}, n. coins: {len(amounts)}")
        y += 1

    wallet_win.addstr(y, 10, f"transactions...")
    y += 1
    for t in cat_wallet.transactions:
        wallet_win.addstr(y, 10, f"address: {t.to_puzzle_hash}, amount: {t.amount}, n. type: {t.name}")
        y += 1

    # interface
    # button to select the visualization: transactions, coins, addresses


    #if finger not in wallet_data["fingers"]:
    #
    #    wallet_data["fingers"][finger] = {}
    #    wallet_data["fingers"][finger]["cursor"] = 0

    #cursor = wallet_data["fingers"][finger]["cursor"]

    #info to dispaly
    #ifnger public key and to right, totatal value of the wallet, usd, xch
    #new all the coin, short name | graph | balance | usd value | xch value |
    #SINGLE -> red or green price with the variation of the week


    # coins: ticker, balance, actual_price, history_price, usd_value, xch_value
    #
    chia_wallet = wallets['chia']
    chia_ticker = chia_wallet.ticker
    chia_balance = chia_wallet.confirmed_wallet_balance
    chia_coins_data: CoinPriceData = CoinPriceData()
    try:
        chia_coins_data = screenState.coins_data['chia']
    except:
        print(f'still no coin data for {chia_ticker}')
    chia_current_price_currency = chia_coins_data.current_price_currency
    chia_historic_price_currency = chia_coins_data.historic_price_currency
    chia_xch_current_price = chia_coins_data.current_price
    chia_xch_historic_price = chia_coins_data.historic_price


    tickers = []
    balances = []
    current_prices_xch = []
    historic_prices_xch = []
    current_prices_currency = []
    historic_prices_currency = []
    total_values_xch = []
    total_values_currency = []

    for wallet_key in wallets:
        if wallet_key == 'chia':
            continue
        wallet = wallets[wallet_key]
        tickers.append(wallet.ticker)
        balances.append(wallet.confirmed_wallet_balance)
        cat_coins_data: CoinPriceData = CoinPriceData()
        try:
            cat_coins_data = screenState.coins_data[wallet_key]
        except:
            print(f'still no coin data for {wallet.ticker}')
        current_prices_xch.append(cat_coins_data.current_price)
        historic_prices_xch.append(cat_coins_data.historic_price)
        current_prices_currency.append(cat_coins_data.current_price_currency)
        historic_prices_currency.append(cat_coins_data.historic_price_currency)
        try:
            xch_value = wallet.confirmed_wallet_balance * cat_coins_data.current_price
            total_values_xch.append(xch_value)
            total_values_currency.append(xch_value * chia_current_price_currency)
        except:
            print(f'still no coin data for {wallet.ticker} or {chia_ticker}')
            total_values_xch.append(None)
            total_values_currency.append(None)

    # make only the first and the last value for the hisotric data
    # maybe it was better to have 2 list for the historic prices

    if keyboardState.enter is True:
        active_scope.exec_child(screenState)
        #screenState.screen_data["active_scope"] = active_scope.exe(active_scope)
        #screenState.screen = screenState.menu[screenState.selection]
    if keyboardState.moveUp:
        active_scope.cursor -= 1
    if keyboardState.moveDown:
        active_scope.cursor += 1
    if keyboardState.esc is True:
        # call back the old scope
        active_scope.active = False
        screenState.screen_data["active_scope"] = active_scope.parent_scope
        screenState.screen_data["active_scope"].active = True
        screenState.screen = 'wallet'

def screen_fingers(stdscr, keyboardState, screenState, height, width):

    wallet_win = createFullSubWin(stdscr, screenState, height, width)
    wallet_win.bkgd(' ', curses.color_pair(screenState.colorPairs["body"]))

    activeScope = screenState.activeScope

    def activate_scope(scope: Scope, screenState):
        screenState.activeScope = scope
        return scope

    handler = screen_wallet
    for finger in screenState.public_keys:
        if finger not in screenState.scopes:
            newScope = Scope(finger, handler, screenState)
            newScope.exec = activate_scope
            newScope.parent_scope = activeScope
            activeScope.sub_scopes[finger] = newScope

    fingers_str = []
    for finger in activeScope.sub_scopes:
        pk_state: PkState = screenState.public_keys[finger]
        fing_name = str(finger) + " - " + pk_state.label
        if finger == screenState.active_pk[0]:
            fingers_str.append(fing_name + ' >')
        else:
            fingers_str.append(fing_name)

    activeScope.update()
    # change immision point to Point
    menu_select(wallet_win, fingers_str, activeScope.cursor,
                [10, 20], screenState.colorPairs['body'], screenState.colorPairs["body_sel"],
                True)

    # if no chia node/wallet are active next step give an error
    # implent user message no node. Maybe finally is processed only if no exception
    # arise select = select % len(screenState.public_keys)

    wallet_win.addstr(20, 10, f"selected: {str(screenState.active_pk[0])}")

    # if keyboardState.enter:
    #     selected_wallet_fingerprint = list(
    #         screenState.public_keys.keys())[cursor]
    #     print("pk active")
    #     print(screenState.active_pk)
    #     print("meto")
    #     print(screenState.public_keys.keys())
    #     print(screenState.public_keys)
    #     print('selected')
    #     print(selected_wallet_fingerprint)

    #     if screenState.active_pk[0] != selected_wallet_fingerprint:
    #         print('changing')
    #         screenState.active_pk = [selected_wallet_fingerprint, True]
    #         cursor = 0
    #         print(screenState.active_pk)
    #         # select a fingerprints
    #         #try:
    #         #    print("trying log in")
    #         #    fingers = asyncio.run(call_rpc_wallet('log_in', screenState.active_pk[0]))
    #         #    print(fingers)
    #         #except Exception as e:
    #         #    wallet_win.addstr(0, 0, "probably there is no chia node and wallet running. We are not logged in")
    #         #    wallet_win.addstr(1, 0, str(e))
    #     else:
    #         print('NOT changing')
    #         screenState.active_pk[1] = True

    # if keyboardState.moveUp:
    #     cursor -= 1
    # if keyboardState.moveDown:
    #     cursor += 1
    # if keyboardState.esc is True:
    #     screenState.screen = 'main'
    # wallet_data["finger_selection"] = cursor

def screen_wallet(stdscr, keyboardState, screenState, height, width):

    wallet_win = createFullSubWin(stdscr, screenState, height, width)
    wallet_win.bkgd(' ', curses.color_pair(screenState.colorPairs["body"]))

    if "wallet" not in screenState.screen_data:
        screenState.screen_data["wallet"] = {}
        screenState.screen_data["wallet"]['finger_selection'] = 0
        screenState.screen_data["wallet"]['fingers'] = {}
    wallet_data = screenState.screen_data["wallet"]
    # it is used for tracking the cursor - so it will be replkaced by the scope

    #spacescan query
    #https://api-fin.spacescan.io/cats?version=0.1.0&network=mainnet&page=2&count=100

    # select fingerprint
    try:
        #if screenState.active_pk[1] is False:
        if False:

            cursor = wallet_data["finger_selection"]
            fingers_str = []
            for finger in screenState.public_keys:
                pk_state = screenState.public_keys[finger]
                fing_name = str(finger) + " - " + pk_state.label
                if finger == screenState.active_pk[0]:
                    fingers_str.append(fing_name + ' >')
                else:
                    fingers_str.append(fing_name)

            # if no chia node/wallet are active next step give an error
            # implent user message no node. Maybe finally is processed only if no exception
            # arise select = select % len(screenState.public_keys)
            cursor = cursor % len(screenState.public_keys)
            menu_select(wallet_win, fingers_str, cursor, [10, 20],
                        screenState.colorPairs['body'], screenState.colorPairs["body_sel"],
                        True)

            wallet_win.addstr(20, 10, f"selected: {str(screenState.active_pk[0])}")
            wallet_win.addstr(21, 10, f"selection: {str(cursor)}")

            if keyboardState.enter:
                selected_wallet_fingerprint = list(
                    screenState.public_keys.keys())[cursor]
                print("pk active")
                print(screenState.active_pk)
                print("meto")
                print(screenState.public_keys.keys())
                print(screenState.public_keys)
                print('selected')
                print(selected_wallet_fingerprint)

                if screenState.active_pk[0] != selected_wallet_fingerprint:
                    print('changing')
                    screenState.active_pk = [selected_wallet_fingerprint, True]
                    cursor = 0
                    print(screenState.active_pk)
                    # select a fingerprints
                    #try:
                    #    print("trying log in")
                    #    fingers = asyncio.run(call_rpc_wallet('log_in', screenState.active_pk[0]))
                    #    print(fingers)
                    #except Exception as e:
                    #    wallet_win.addstr(0, 0, "probably there is no chia node and wallet running. We are not logged in")
                    #    wallet_win.addstr(1, 0, str(e))
                else:
                    print('NOT changing')
                    screenState.active_pk[1] = True

            if keyboardState.moveUp:
                cursor -= 1
            if keyboardState.moveDown:
                cursor += 1
            if keyboardState.esc is True:
                screenState.screen = 'main'
            wallet_data["finger_selection"] = cursor
        else:
            # wallet
            pk: PkState = screenState.public_keys[screenState.active_pk[0]]
            wallets: Dict[int, WalletState] = pk.wallets
            finger = pk.fingerprint


            if finger not in wallet_data["fingers"]:
                wallet_data["fingers"][finger] = {}
                wallet_data["fingers"][finger]["cursor"] = 0

            cursor = wallet_data["fingers"][finger]["cursor"]

            #info to dispaly
            #ifnger public key and to right, totatal value of the wallet, usd, xch
            #new all the coin, short name | graph | balance | usd value | xch value |
            #SINGLE -> red or green price with the variation of the week


            # coins: ticker, balance, actual_price, history_price, usd_value, xch_value
            #
            chia_wallet = wallets['chia']
            chia_ticker = chia_wallet.ticker
            chia_balance = chia_wallet.confirmed_wallet_balance
            chia_coins_data: CoinPriceData = CoinPriceData()
            try:
                chia_coins_data = screenState.coins_data['chia']
            except:
                print(f'still no coin data for {chia_ticker}')
            chia_current_price_currency = chia_coins_data.current_price_currency
            chia_historic_price_currency = chia_coins_data.historic_price_currency
            chia_xch_current_price = chia_coins_data.current_price
            chia_xch_historic_price = chia_coins_data.historic_price


            tickers = []
            balances = []
            current_prices_xch = []
            historic_prices_xch = []
            current_prices_currency = []
            historic_prices_currency = []
            total_values_xch = []
            total_values_currency = []

            for wallet_key in wallets:
                if wallet_key == 'chia':
                    continue
                wallet = wallets[wallet_key]
                tickers.append(wallet.ticker)
                balances.append(wallet.confirmed_wallet_balance)
                cat_coins_data: CoinPriceData = CoinPriceData()
                try:
                    cat_coins_data = screenState.coins_data[wallet_key]
                except:
                    print(f'still no coin data for {wallet.ticker}')
                current_prices_xch.append(cat_coins_data.current_price)
                historic_prices_xch.append(cat_coins_data.historic_price)
                current_prices_currency.append(cat_coins_data.current_price_currency)
                historic_prices_currency.append(cat_coins_data.historic_price_currency)
                try:
                    xch_value = wallet.confirmed_wallet_balance * cat_coins_data.current_price
                    total_values_xch.append(xch_value)
                    total_values_currency.append(xch_value * chia_current_price_currency)
                except:
                    print(f'still no coin data for {wallet.ticker} or {chia_ticker}')
                    total_values_xch.append(None)
                    total_values_currency.append(None)

            # make only the first and the last value for the hisotric data
            # maybe it was better to have 2 list for the historic prices
            print("len prices bef ", len(historic_prices_xch))
            hpsx_temp = []
            for hpx in historic_prices_xch:

                if hpx is not None and len(hpx) > 1:
                    hpx_keys = list(hpx.keys())
                    print("hpx ", hpx)
                    hpx = [hpx[hpx_keys[0]], hpx[hpx_keys[-1]]]
                    hpsx_temp.append(hpx)
                else:
                    print("hpx empyt ", hpx)
                    hpsx_temp.append([])

            hpsc_temp = []
            for hpc in historic_prices_currency:
                if  hpc is not None and len(hpc) > 1:
                    hpc_keys = list(hpc.keys())
                    hpc = [hpc[hpc_keys[0]], hpc[hpc_keys[-1]]]
                    hpsc_temp.append(hpc)
                else:
                    print("hpc empty ", hpc)
                    hpsc_temp.append([])


            historic_prices_xch = hpsc_temp
            historic_prices_currency = hpsc_temp

            print("len prices aff", len(historic_prices_xch))
            #########################
            ## temp variation to have only one entry
            #hpsx_temp = []
            #for hpx in historic_prices_xch:
            #    if hpx is not None and len(hpx) > 1:
            #        hpsx_temp.append([hpx[0]])
            #    else:
            #        hpsx_temp.append([])

            #hpsc_temp = []
            #for hpc in historic_prices_currency:
            #    if  hpc is not None and len(hpc) > 1:
            #        hpsc_temp.append([hpc[0]])
            #    else:
            #        hpsc_temp.append([])

            #historic_prices_xch = hpsx_temp
            #historic_prices_currency = hpsc_temp
            #########################

            dataTable = [tickers, balances, current_prices_xch, historic_prices_xch,
                     current_prices_currency, historic_prices_currency,
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

                #scope_name = "wallet_view"
                #if scope_name not in screenState.scopes:
                #    main_scope = Scope(scope_name, screen_wallet, screenState)
                #    main_scope.exec = None
                #    main_scope.active = True
                #    screenState.screen_data["scopes"]["wallet_view"]  = main_scope
                #    screenState.screen_data["active_scope"]  = main_scope

                main_scope = screenState.scopes['wallet']  # to replace with a new entry, main scope in the gen function?
                main_scope.update()
                active_scope = screenState.activeScope

                create_tab(wallet_win, screenState, main_scope, "coins_data", dataTable,
                           data_table_keys, data_table_color, False,
                           UIgraph.Point(20,10), UIgraph.Point(150,10),
                           keyboardState, "coins_data", True, False, data_table_legend)

                wallet_win.addstr(31, 10, f"cursor: {str(active_scope.cursor)}")
                wallet_win.addstr(32, 10, f"altro: {str(active_scope.cursor)}")

                if keyboardState.enter is True:
                    active_scope.exec_child(screenState)
                    #screenState.screen_data["active_scope"] = active_scope.exe(active_scope)
                    #screenState.screen = screenState.menu[screenState.selection]
                if keyboardState.moveUp:
                    active_scope.cursor -= 1
                    screenState.selection = -1
                if keyboardState.moveDown:
                    active_scope.cursor += 1
                    screenState.selection = 1
                if keyboardState.esc is True:
                    # call back the old scope
                    active_scope.active = False
                    screenState.screen_data["active_scope"]  = active_scope.parent_scope
                    print(type(screenState.screen_data["active_scope"]))
                    screenState.screen_data["active_scope"].active = True

                wallet_win.addstr(33, 10, f"fine keybot: {str(active_scope.cursor)}")
                #chia_wallet = wallets['chia']
                #chia_wallet.block_height += 1

                #wallet_win.attron(curses.color_pair(1))
                #wallet_win.addstr(11, 10, 'WHAT>>>? Chia_Wallet: ' + str(screenState.active_pk))

                #y = 13
                #wallet_win.addstr(y, 10, f"confirmed balance {chia_wallet.confirmed_wallet_balance}")
                #y += 1
                #wallet_win.addstr(y, 10, f"spendable balance {chia_wallet.spendable_balance}")
                #y += 1
                #wallet_win.addstr(y, 10, f"unspent coin count {chia_wallet.unspent_coin_count}")
                #y += 1
                #wallet_win.addstr(y, 10, f"block height {chia_wallet.block_height}")

                #if keyboardState.moveLeft:
                #    screenState.select_y -= 1
                #if keyboardState.moveRight:
                #    screenState.select_y += 1

                #print('keys')
            except Exception as e:
                wallet_win.addstr(0, 0, f"still loading wallet data")
                print("wallet tab creation failed")
                print(e)
                traceback.print_exc()


        if keyboardState.esc is True:
            screenState.active_pk = [screenState.active_pk[0], False]

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

dumbList = ["cedro", "boom", "toom", "broom", "LAgremmo", "magro", "tewo", "faiehr",
            "fegpq", "Pqntwr", "Kista", "eiuallo", "gest", "qqq"]
dumbList2 = [1, -2, 3, -4, -5, 6, -7, 8, 9, 10, -11, -12, -13, 14]
dumbList3 = [987, 782, 433, 904, 3459, 3890, 2903, 8812, 3, 34, 11343, 139, 22, 438]

theList = []
for n, i in enumerate(dumbList):
    theList.append([dumbList[n], dumbList2[n], dumbList3[n]])

dumbList = dumbList[0:5]
dumbList2 = dumbList2[0:5]
dumbList3 = dumbList3[0:5]

theList2 = []
for n, i in enumerate(dumbList):
    theList2.append([dumbList[n], dumbList2[n], dumbList3[n]])

def create_button(stdscr, screenState, parent_scope: Scope, name: str,
                  point: UIgraph.Point, active: bool):
    """A real button... """

    name = f"{parent_scope.id}_{name}"

    if name not in screenState.screen_data["scopes"]:
        scope = Scope()
        scope.parent_scope = parent_scope
        parent_scope.sub_scopes[name] = scope
        screenState.screen_data["scopes"][name]  = scope

    scope = screenState.screen_data["scopes"][name]

    pos_x = point.x
    pos_y = point.y

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

    if scope.bool:
        # upper row
        stdscr.addstr(pos_y, pos_x, u'\u2584' * (length - 0),
                            curses.color_pair(frame_cp_dark))

        # text
        x = pos_x
        stdscr.addstr(pos_y + 1, x, u'\u2588',
                            curses.color_pair(frame_cp_dark) |
                            curses.A_BOLD)
        x += 1
        stdscr.addstr(pos_y + 1, x, f" {but} ",
                            curses.color_pair(text_dark) |
                            curses.A_BOLD)
        x += length - 2
        stdscr.addstr(pos_y + 1, x, u'\u2588',
                            curses.color_pair(frame_cp_dark) |
                            curses.A_BOLD)

        # lower row
        stdscr.addstr(pos_y + 2, pos_x + 0, u'\u2580' * (length - 0),
                            curses.color_pair(frame_cp_dark))
        frame_selected = UIgraph.addCustomColorTuple(
            (text_color_background_dark, default_selected),
            screenState.cursesColors
        )

    else:
        # upper row
        stdscr.addstr(pos_y, pos_x, u'\u2584' * (length - 0),
                            curses.color_pair(frame_cp_dark))
        # text
        x = pos_x
        stdscr.addstr(pos_y + 1, x, u'\u2588',
                            curses.color_pair(frame_cp_dark) |
                            curses.A_BOLD)
        x += 1
        stdscr.addstr(pos_y + 1, x, f" {but} ",
                            curses.color_pair(text_clear) |
                            curses.A_BOLD)
        x += length - 2
        stdscr.addstr(pos_y + 1, x, u'\u2588',
                            curses.color_pair(frame_cp_clear) |
                            curses.A_BOLD)
        # lower row
        stdscr.addstr(pos_y + 2, pos_x + 0, u'\u2580',
                            curses.color_pair(frame_cp_dark))
        stdscr.addstr(pos_y + 2, pos_x + 1, u'\u2580' * (length - 1),
                            curses.color_pair(frame_cp_clear))

        frame_selected = UIgraph.addCustomColorTuple(
            (text_color_background_clear, default_selected),
            screenState.cursesColors
        )


    # selection
    if scope.selected:
        stdscr.addstr(pos_y + 2, pos_x, u'\u2580',
                            curses.color_pair(frame_selected_2))
        stdscr.addstr(pos_y + 2, pos_x + 1, u'\u2580' * (length - 1),
                            curses.color_pair(frame_selected))
        stdscr.addstr(pos_y + 0, pos_x + length, u'\u2596',
                            curses.color_pair(frame_selected_backgroung))
        stdscr.addstr(pos_y + 1, pos_x + length, u'\u258c',
                            curses.color_pair(frame_selected_backgroung))
        stdscr.addstr(pos_y + 2, pos_x + length, u'\u258c',
                            curses.color_pair(frame_selected_backgroung))


def text_with_frame():
    pass

def ft_standar_number_format(num, sig_digits, max_size):
    """Function to format a number. It gives None for the color info"""
    if isinstance(num, float):
        num = dex.format_and_round_number(num, sig_digits, max_size)
        return str(num), None
    return str(num), None

def ft_percentage_move(move, color_up, color_down):
    """Function to format price variation"""
    if isinstance(move, float) or isinstance(move, int):
        move_str = dex.format_and_round_number(move, 3, 4)
        if move < 0:
            return f"{str(move_str)}%", color_down
        return f"{str(move_str)}%", color_up
    return f"{str(move)}%", color_down

def ft_price_trend(prices):
    """Take a list of two price and calculate the diff %"""
    if len(prices) > 1:
        move = (prices[0] - prices[1]) / prices[0]
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


def create_tab(scr, screenState, parent_scope: Scope, name: str, dataTable,
               data_table_keys: List[str], data_table_color,
               transpose: bool, position: UIgraph.Point, size: UIgraph.Point,
               keyboardState, tabName, active= False, multipleSelection= False,
               data_table_legend= None):
    """Create a beautiful and shining tab"""

    name = f"{parent_scope.id}_{name}"

    if name not in screenState.scopes:
        scope = Scope(name, screen_wallet, screenState)
        scope.parent_scope = parent_scope

        def activate_scope(scope: Scope, screenState):
            screenState.activeScope = scope
            return scope

        scope.exec = activate_scope

        # create a child to create another window
        # probably it should be something that we define outside
        # this function because it change every time
        child_name = name + "selected_child"
        child_scope = Scope(child_name, screen_coin_wallet, screenState)
        def open_coin_wallet(scope: Scope, screenState):
            screenState.activeScope = scope
            return scope
        child_scope.exec = activate_scope
        child_scope.parent_scope = scope

        parent_scope.sub_scopes[name] = scope # TODO should i put it in the __init__?


    scope = screenState.scopes[name]
    # remove the active properties from Scope, and check every time if the scope
    # is the one active
    scope_active = False
    if scope is screenState.activeScope:
        scope.update_no_sub(len(dataTable))
        scope_active = True

    pos_x = position.x
    pos_y = position.y

    # tab size, to make as a parameter
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
            print("type ", type(u))
            if isinstance(u, float):
                #if u > 1:
                u = dex.format_and_round_number(u, 5, 10)
                col_str.append(str(u))
            else:
                col_str.append(str(u))
        data_table_table_str.append(col_str)

    dataTable = data_table_table_str

    # curse customs colors

    soft_color = screenState.colorPairs["tab_soft"]
    dark_color= screenState.colorPairs["tab_dark"]
    select_color = screenState.colorPairs["tab_select"]
    selected_color = screenState.colorPairs["tab_selected"]
    win_selected_color = screenState.colorPairs["win_select"]
    if scope_active:
        win_selected_color = screenState.colorPairs["body"]
    background_color = screenState.colorPairs["footer"]

    if data_table_color is None:
        row = len(dataTable)
        col = len(dataTable[0])
        data_table_color = [[None] * col] * row

    # debug
    scr.addstr(3, 3, f"dim {len(dataTable)} and {len(dataTable[0])}")
    scr.addstr(4, 3, f"dim {len(data_table_color)} and {len(data_table_color[0])}")
    scr.addstr(5, 3, f"dim {str(data_table_color)}")

    # TODO eliminate one of the two transpositions
    if transpose:
        transposed_table = [[row[i] for row in dataTable] for i in range(len(dataTable[0]))]

        dataTable = transposed_table

        transposed_table = [[row[i] for row in data_table_color] for i in range(len(data_table_color[0]))]

        data_table_color = transposed_table

    # selection
    if scope.selected:
        scr.addstr(pos_y + y_tabSize -1, pos_x, u'\u2580' * x_tabSize,
                   curses.color_pair(win_selected_color))
        scr.addstr(pos_y + y_tabSize -1, pos_x + x_tabSize, u'\u2598',
                   curses.color_pair(win_selected_color))
        for i in range(y_tabSize):
            scr.addstr(pos_y + i -1, pos_x + x_tabSize, u'\u258c',
                       curses.color_pair(win_selected_color))


    ### tab creation
    # add the scroll logic above

    table = scr.subwin(y_tabSize, x_tabSize, pos_y, pos_x)
    table.bkgd(' ', curses.color_pair(background_color))

    # background for custom colors
    default_background = screenState.colors["background"]
    soft_background = screenState.colors["tab_soft"]
    dark_background = screenState.colors["tab_dark"]

    table_bk_colors = [soft_background, dark_background] # these are not pairs
    table_color_pairs = [soft_color, dark_color]

    ## logic for multiple lines
    # select pair
    if tabName not in screenState.screen_data:
        screenState.screen_data[tabName] = {}
        #screenState.screen_data[tabName]["tickers"] = loadAllTickers()
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


    # max dim for columns
    max_dims = []
    total_dims = 0
    print(dataTable)
    for l in dataTable:
        max_dim = 0
        for i in l:
            print(i)
            if len(str(i)) > max_dim:
                max_dim = len(i)
        max_dims.append(max_dim)
    for i in max_dims:
        total_dims += i

    # max dim for legend
    if data_table_legend is not None:
        for idx, (max_dim, leg_item) in enumerate(zip(max_dims, data_table_legend)):
            if len(leg_item) > max_dim:
                max_dims[idx] = len(leg_item)

    x_remainder = 0

    # transpose if needed, a list should be a row of data
    print(dataTable)
    transposed_table = []
    for i in range(len(dataTable[0])):
        new_row = []
        for row in dataTable:
            new_row.append(row[i])
        transposed_table.append(new_row)

    n_r = transposed_table

    ###### second transposition... ######
    transposed_table = [[row[i] for row in dataTable] for i in range(len(dataTable[0]))]
    dataTable = transposed_table

    transposed_table = [[row[i] for row in data_table_color] for i in range(len(data_table_color[0]))]
    data_table_color = transposed_table

    ### logic for partial tabs
    #if total_dims > x_tabSize:
    #    #implement column truncating
    #    pass
    #else:
    #    x_remainder = (x_tabSize - total_dims) // len(dataTable[0])

    n_columns = len(dataTable)
    if multipleSelection:
        n_columns += 1 # add the selection column

    x_remainder = (x_tabSize - total_dims) // n_columns

    x_colDim = []
    for i in max_dims:
        x_colDim.append(i + x_remainder)

    x_colStart = [0]
    if multipleSelection:
        #x_colStart[0] += 4 # add the selection column
        x_colStart[0] += 7 # add the selection column
    for i in range(len(max_dims) - 1):
        x_colStart.append(x_colStart[-1] + max_dims[i] + x_remainder)

    row = 0
    ### legend loop ###
    if data_table_legend is not None:

        frame_legend = UIgraph.addCustomColorTuple(
            (soft_background, default_background),
            screenState.cursesColors)
        table.attron(curses.color_pair(frame_legend) | curses.A_BOLD )

        table.addstr(row, 0, u'\u2584' * (x_tabSize))
        table.addstr(row + 2, 0, u'\u2580' * (x_tabSize))
        row += 1
        table.attron(curses.color_pair(soft_color))
        table.addstr(row, 0, ' ' * (x_tabSize))
        if multipleSelection:
            table.addstr(row, 0, u' \u25A1 /\u25A0')
        for idx, leg_item in enumerate(data_table_legend):
            table.addstr(row, x_colStart[idx], str(leg_item))
        table_color_pairs.reverse() # to begin always with the soft color
        table_bk_colors.reverse() # to begin always with the soft color

        # disable bold
        table.attroff(curses.A_BOLD)


    ### data loop ###
    row = height_legend
    for data_row, data_idx in zip(
            dataTable[idx_first_element:idx_last_element],
            idx_dataTable[idx_first_element:idx_last_element]):

        custom_bk_color = table_bk_colors[row % 2]
        current_attron = curses.color_pair(table_color_pairs[row % 2])
        if data_idx == select and scope.active:
            current_attron = curses.color_pair(select_color)
            scope.sub_scopes["selected"].state = data_table_keys[data_idx] if data_table_keys else None
            print("data table")
            print(" daa " ,data_table_keys[data_idx] if data_table_keys else None)


        table.attron(current_attron)
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
                current_attron = curses.color_pair(selected_color)
                custom_bk_color = screenState.colors["chia_green"]
                table.attron(current_attron)
                table.addstr(data_idx, 0, ' ' * (x_tabSize))
                table.addstr(row, 1, u' \u25A0')
            else:
                table.addstr(row, 1, u' \u25A1')

        for i_col, col in enumerate(data_row):
            text_color = data_table_color[data_idx][i_col]
            if text_color is not None and (data_idx != select or not scope.active):
                text_c_pair = UIgraph.addCustomColorTuple(
                    (text_color, custom_bk_color),
                    screenState.cursesColors)
                table.attron(curses.color_pair(text_c_pair))

            table.addstr(row, x_colStart[i_col], str(col))
            table.attron(current_attron)

        row += 1
        count += 1
        #row = row % height



    ###### black square
    ###### U+25A0
    ###### white square
    ###### U+25A1

    ### old loop
    #for i_row, row in enumerate(dataTable):
    #    table.attron(curses.color_pair(tableColors[i_row % 2]))
    #    table.addstr(i_row, 0, ' ' * (x_tabSize))
    #    #table.move(i_row, 0)
    #    #table.clrtoeol()
    #    for i_col, col in enumerate(row):
    #        print(i_row)
    #        print(x_colStart[i_col])
    #        table.addstr(i_row, x_colStart[i_col], str(col))
    ### old loop
    #table.addstr(0, 19, "boasigre", curses.color_pair(3))
    #table.addstr(3, 19, "boasigre", vv)
    #table.addstr(3, 19, str(vv), vv)
    #continue implem

    ### keyboard ###
    ##if keyboardState.enter is True:
    #    screenState.screen_data[tabName]["idx_selected"].append(select)
    #if keyboardState.moveUp:
    #    screenState.selection -= 1
    #if keyboardState.moveDown:
    #    screenState.selection += 1
    #if keyboardState.esc is True:
    #    screenState.screen = 'main'

white_darkBlue = None
def screen_tabs(stdscr, keyboardState, screenState, height, width, figlet=False):
    debug_win = createFullSubWin(stdscr, screenState, height, width)
    debug_win.bkgd(' ', curses.color_pair(screenState.colorPairs["body"]))

    if "scopes" not in screenState.screen_data:
        screenState.screen_data["scopes"]  = {}
        screenState.screen_data["active_scope"]  = None
    if "deb_tab" not in screenState.screen_data["scopes"]:
        main_scope = Scope()
        def get_N_scope(scope: Scope, screenState):
            scope.active = False
            active_scope_key = list(scope.sub_scopes.keys())[scope.cursor]

            new_scope = scope.sub_scopes[active_scope_key]
            new_scope.active = True
            return new_scope

        #main_scope.exe = get_N_scope
        main_scope.exec = None
        main_scope.active = True

        screenState.screen_data["scopes"]["deb_tab"]  = main_scope
        screenState.screen_data["active_scope"]  = main_scope

    main_scope = screenState.screen_data["scopes"]["deb_tab"]
    main_scope.update()
    active_scope = screenState.screen_data["active_scope"]



    legend = ["bab", "okment", "t-1"]

    #if "tabs" not in screenState.screen_data:
    #    screenState.screen_data["tabs"] = {}
    #    screenState.screen_data["tabs"]['cursor'] = 0
    #    screenState.screen_data["tabs"]['scope'] = 0
    #tabs_data = screenState.screen_data["tabs"]
    #cursor = screenState.screen_data["tabs"]['cursor']

    #cursor += screenState.selection
    #screenState.selection = 0

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
    print("bordolabba")
    print(theListTransposeColor)

    theListColor = [[row[i] for row in theListTransposeColor]
                        for i in range(len(theListTransposeColor[0]))]

    active = False
    create_tab(debug_win, screenState, main_scope, "tab_a", theList, None, theListColor, True,
            UIgraph.Point(20,10), UIgraph.Point(150,10),
            keyboardState, "test_tabs", active, True, legend)

    create_tab(debug_win, screenState, main_scope, "tab_b", theList2, None, None, True,
            UIgraph.Point(20,25), UIgraph.Point(100,8),
            keyboardState, "test_tabs_small", active, False)

    create_tab(debug_win, screenState, main_scope, "tab_c", theList2, None, None, True,
            UIgraph.Point(20,35), UIgraph.Point(100,8),
               keyboardState, "test_tabs_small", active, False, legend)

    if keyboardState.enter is True:
        active_scope.exec_child(screenState)
        #screenState.screen_data["active_scope"] = active_scope.exe(active_scope)
        #screenState.screen = screenState.menu[screenState.selection]
    if keyboardState.moveUp:
        active_scope.cursor -= 1
        screenState.selection = -1
    if keyboardState.moveDown:
        active_scope.cursor += 1
        screenState.selection = 1
    if keyboardState.esc is True:
        # call back the old scope
        active_scope.active = False
        screenState.screen_data["active_scope"]  = active_scope.parent_scope

        print(type(screenState.screen_data["active_scope"]))
        screenState.screen_data["active_scope"].active = True

    #if keyboardState.moveUp:
    #if keyboardState.moveDown:
    #if keyboardState.esc is True:
    #    screenState.screen = 'main'
    #tabs_data["cursor"] = cursor


def screen_harvester():
    pass


def screen_full_node(stdscr, keyboardState, screenState, height, width, figlet=False):
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

    blockchain_state = asyncio.run(call_rpc_node('get_blockchain_state'))
    difficulty = blockchain_state["difficulty"]
    synced = blockchain_state["sync"]["synced"]
    sync_mode = blockchain_state["sync"]["sync_mode"]
    sub_slot_iters = blockchain_state["sub_slot_iters"]
    space = blockchain_state["space"]
    space = blockchain_state["space"] / (1024**6), ' Eib'
    node_id = blockchain_state["node_id"]

    try:
        row = 5
        col = 4
        node_data.addstr(row, col, f"Network: {network_name}    Port: {full_node_port}   RPC Port: {full_node_rpc_port}")
        row += 1
        node_data.addstr(row, col, f"Node ID: {node_id}")
        row += 1
        node_data.addstr(row, col, f"Genesis Challenge: {genesis_challenge}")
        row += 1

        peak = blockchain_state["peak"]

        if synced:
            node_data.addstr(row, col, "Current Blockchain Status: Full Node Synced")
            row += 1
            node_data.addstr(row, col, f"Peak: Hash: {peak.header_hash}")
            row += 1
        elif peak is not None and sync_mode:
            sync_max_block = blockchain_state["sync"]["sync_tip_height"]
            sync_current_block = blockchain_state["sync"]["sync_progress_height"]
            node_data.addstr(row, col, f"Current Blockchain Status: Syncing {sync_current_block}/{sync_max_block} ({sync_max_block - sync_current_block} behind)."
            )
            row += 1
            node_data.addstr(row, col, f"Peak: Hash: {peak}")
            row += 1
        elif peak is not None:
            node_data.addstr(row, col, f"Current Blockchain Status: Not Synced. Peak height: {peak.height}")
            row += 1
        else:
            node_data.addstr(row, col, "Searching for an initial chain")
            row += 1
            node_data.addstr(row, col, "You may be able to expedite with 'chia peer full_node -a host:port' using a known node.\n")
            row += 1

        if peak is not None:
            if peak.is_transaction_block:
                peak_time = peak.timestamp
            else:
                peak_hash = bytes32(peak.header_hash)
                curr = asyncio.run(call_rpc_node('get_block_record', header_hash=peak_hash))
                #curr = await node_client.get_block_record(peak_hash)
                while curr is not None and not curr.is_transaction_block:
                    curr = asyncio.run(call_rpc_node('get_block_record',header_hash=curr.prev_hash))
                    #curr = await node_client.get_block_record(curr.prev_hash)
                if curr is not None:
                    peak_time = curr.timestamp
                else:
                    peak_time = uint64(0)

            peak_time_struct = time.struct_time(time.localtime(peak_time))

            node_data.addstr(row, col, f"      Time: {time.strftime('%a %b %d %Y %T %Z', peak_time_struct)}                 Height: {peak.height:>10}")
            row += 1

            node_data.addstr(row, col, f"Estimated network space: {space}")
            row += 1
            #node_data.addstr(row, col, format_bytes(blockchain_state["space"]))
            node_data.addstr(row, col, f"Current difficulty: {difficulty}")
            row += 1
            node_data.addstr(row, col, f"Current VDF sub_slot_iters: {sub_slot_iters}")
            row += 1
            #node_data.addstr(row, col, "\n  Height: |   Hash:")
    except Exception as e:
        print(e)
        print("except what?")

    if keyboardState.esc is True:
        screenState.screen = 'main'


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


# non piu usato
#screenGenerators = {
#    'intro': intro,
#    'main': main_menu,
#    'full node': full_node,
#    'wallet': wallet,
#    'coin_wallet': coin_wallet,
#    'dexi': dexi,
#    'tabs': tabs
#}

if True:
    #screenGenerators["debugging window"] = debugging_window
    pass

def interFace(stdscr):

    try:
        data_lock = threading.Lock()
        fingers_state: List[FingerState] = []
        fingers_list: List[int] = []
        finger_active: List[int] = [0]
        count_server = [0]
        coins_data = Dict[str, CoinPriceData]
        coins_data = {}

        frame_start = None
        frame_end = None
        frame_time = 0
        frame_time_max = 0
        frame_time_display = 0
        frame_count = 0

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

        curses.curs_set(0)
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
        screenState.colors["tab_selected"] = UIgraph.addCustomColor(
            (244, 43, 3),
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
        screenState.colorPairs["tab_select"] = UIgraph.addCustomColorTuple(
            (screenState.colors["background"], screenState.colors["chia_green"]),
            screenState.cursesColors)
        screenState.colorPairs["tab_selected"] = UIgraph.addCustomColorTuple(
            (screenState.colors["chia_green"], screenState.colors["tab_selected"]),
            screenState.cursesColors)
        screenState.colorPairs["win_select"] = UIgraph.addCustomColorTuple(
            (screenState.colors["yellow_bee"], screenState.colors["background"]),
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

    except Exception as e:
        print("color creation")
        print(e)
        traceback.print_exc()

    # create the intro and the main menu scopes
    scopeIntro = Scope('intro', screen_intro, screenState)
    scopeMainMenu = Scope('main_menu', screen_main_menu, screenState)

    def activate_scope(scope: Scope, screenState: ScreenState):
        screenState.activeScope = scope
        return scope

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

            # update wallet data
            for fs in fingers_state:
                screenState.public_keys[fs.fingerprint] = fs
            if screenState.active_pk[0] == 0:
                screenState.active_pk = [finger_active[0], screenState.active_pk[1]]

            # update coin data
            with data_lock:
                screenState.coins_data = coins_data

            height, width = stdscr.getmaxyx()
            windowDim = f"height={height}; width={width}"
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
                header.addstr(0, 0, title)
                # write on the right but not in the window, but on the main screen
                fps = f"fps: {frame_time_display}s; "
                window_info = fps + windowDim
                y, x = 0, width - len(window_info) - 1
                header.addstr(y, x, window_info)


                nLinesHeader = (len(title) + len(windowDim)) // width + 1
                screenState.headerLines = nLinesHeader

                def addLineToScr(scr, text):
                    #can we retrive the dimension od the scr to limit the text to one line?
                    #is there a builtin func to make the text stopping at the end of the line?
                    pass

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

                footerDebug = stdscr.subwin(nLinesDebug + extraLines, width,
                                            height-nLines-nLinesDebug - extraLines,
                                            0)
                footerDebug.bkgd(' ', curses.color_pair(screenState.colorPairs["footer"]))
                footerDebug.addstr(0, 0, footer_colors)
                footerDebug.addstr(1, 0, footerTextDebug)


                screenState.footerLines = nLines + nLinesDebug

                # keyboard
                if key == ord('j') or key == curses.KEY_DOWN:
                    keyboardState.moveDown = True

                if key == ord('k') or key == curses.KEY_UP:
                    keyboardState.moveUp = True

                if key == ord('h') or key == curses.KEY_LEFT:
                    keyboardState.moveLeft = True

                if key == ord('l') or key == curses.KEY_RIGHT:
                    keyboardState.moveRight = True

                if key == curses.KEY_ENTER or key == 10 or key == 13:
                    keyboardState.enter = True

                if key == curses.KEY_MOUSE:
                    keyboardState.mouse = True

                if key == 27:
                    keyboardState.esc = True


                # screen selection
                activeScope = screenState.activeScope
                activeScope.screen(stdscr, keyboardState,
                                                     screenState, height, width)

                # keyboard
                if keyboardState.enter is True:
                    activeScope.exec_child(screenState)
                    #screenState.screen_data["active_scope"] = active_scope.exe(active_scope)
                    #screenState.screen = screenState.menu[screenState.selection]
                if keyboardState.moveUp:
                    activeScope.cursor -= 1
                    screenState.selection = -1
                if keyboardState.moveDown:
                    activeScope.cursor += 1
                    screenState.selection = 1
                if keyboardState.esc is True:
                    # call back the old scope
                    if activeScope.parent_scope:
                        screenState.activeScope = activeScope.parent_scope

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
            time.sleep(30/1000)
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


async def call_rpc_node(method_name, *args, **kwargs):
    try:
        full_node_client = await FullNodeRpcClient.create(
            self_hostname, uint16(full_node_rpc_port), DEFAULT_ROOT_PATH, config
        )
        rpc_method = getattr(full_node_client, method_name)
        response = await rpc_method(*args, **kwargs)
        return response
    except Exception as e:
        print("sometime wrong with an rpc node call")
        print(e)

    finally:
        full_node_client.close()
        await full_node_client.await_closed()


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


async def call_daemon_rpc(method_name, *args, **kwargs):

    daemon = await connect_to_daemon_and_validate(DEFAULT_ROOT_PATH, config)

    if daemon is None:
        raise Exception("Failed to connect to chia daemon")

    result = {}
    try:
        ws_request = daemon.format_request(method_name, kwargs)
        ws_response = await daemon._get(ws_request)
        result = ws_response["data"]
    except Exception as e:
        raise Exception(f"Request failed: {e}")
    finally:
        await daemon.close()
    return result

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
