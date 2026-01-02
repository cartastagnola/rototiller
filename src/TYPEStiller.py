import time
import copy
import threading
import traceback
import sqlite3  # TODO: remove it

from dataclasses import dataclass
from typing import List, Tuple, Dict, Union, Callable
from collections import deque

from chia_rs.sized_bytes import bytes32, bytes48
from chia_rs.sized_ints import uint16, uint32, uint64, uint128

import src.UIgraph as UIgraph
from src.CONFtiller import ScopeMode, debug_logger, logging, DB_SB, SQL_TIMEOUT
import src.RPCtiller as RPC
import src.WDBtiller as WDB



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
    key: int = None
    moveUp: bool = False
    moveDown: bool = False
    moveLeft: bool = False
    moveRight: bool = False
    yank: bool = False
    paste: bool = False
    mouse: bool = False
    enter: bool = False
    esc: bool = False
    home: bool = False


class FullNodeMeta:

    def __init__(self):
        self.peak_height: int = None
        self.peak_header_hash = None
        self.peak_timestamp = None
        self.genesis_challenge = None
        self.network_name = None
        self.difficulty = None
        self.synced = None
        self.sync_mode = None
        self.sub_slot_iters = None
        self.net_space = None
        self.node_id = None
        self.sync_tip_height = None
        self.sync_progress_height = None
        self.finished_challenge_slot_hashes = None
        self.finished_infused_challenge_slot_hashes = None
        self.finished_reward_slot_hashes = None
        self.prev_hash = None
        self.prev_transaction_block_hash = None


class FullNodeState:

    def __init__(self, db_path: str):
        self.lock = threading.Lock()
        self.db_path = db_path
        self.mempool_items = None
        self.mempool_archive = {}
        self.blocks_loader: WDB.DataChunkLoader = None
        self.is_blocks_loader_on_peak = True
        self.full_node_meta = FullNodeMeta()

        self.update_chain_info()
        self.update_chain_state()
        self.init_mempool()

        table_name = 'full_blocks'
        chunk_size = 50  # 120  # height * 2  # to be sure to have at least 2 full screen of data
        offset = self.full_node_meta.peak_height
        sorting_column = 'height'
        filters = {'in_main_chain': 1}
        self.blocks_loader = WDB.DataChunkLoader(db_path, table_name, chunk_size, offset, filters=filters, sorting_column=sorting_column, data_struct=WDB.BlockState)
        # create and keep track of the thread that update the block loader, so it is possible to know if it is running and calling in different places. Once it ends
        # it has to be recrated
        # self.blocks_loader_thread = threading.Thread(target=self._update_blocks_loader, daemon=True)
        # self.blocks_loader_thread.start()

        table_name = 'spend_bundles'
        chunk_size = 30  # 120  # height * 2  # to be sure to have at least 2 full screen of data
        offset = 0
        sorting_column = None
        filters = None  # {'in_main_chain': 1}
        self.spend_bundle_archive_loader: WDB.DataChunkLoader = WDB.DataChunkLoader(DB_SB, table_name, chunk_size,
                                                                                    offset, sorting_column=sorting_column,
                                                                                    data_struct=WDB.BundleState)
        self.spend_bundle_archive_loader.start_updater_thread()


    def init_mempool(self):
        mempool_items = {spend_bundle_hash: WDB.MempoolItem(spend_bundle_hash, json_item) for spend_bundle_hash, json_item in RPC.call_rpc_node('get_all_mempool_items').items()}

        #for spend_bundle_hash, json_item in call_rpc_node('get_all_mempool_items').items():
        #    print(f"tx id: {spend_bundle_hash} and json: {json_item}")

        with self.lock:
            self.mempool_items = mempool_items
            logging(debug_logger, "DEBUG", f"NODE STATE - init mempool, inserting items")
            # TODO; move sqlite in DB.py
            conn = sqlite3.connect(DB_SB, timeout=SQL_TIMEOUT)
            for key, item in mempool_items.items():
                sb = item.spend_bundle

            conn.close()


    def update_mempool(self):
        with self.lock:
            self.mempool_items = {spend_bundle_hash: WDB.MempoolItem(spend_bundle_hash, json_item) for spend_bundle_hash, json_item in RPC.call_rpc_node('get_all_mempool_items').items()}

        # removed expired transactions older then
        # TODO:
        # - add property in_mempool
        # - remove apptoved txs after 15s

        #logging(debug_logger, "DEBUG", f"NODE STATE - updating mempool")
        #new_mempool = {spend_bundle_hash: WDB.MempoolItem(spend_bundle_hash, json_item) for spend_bundle_hash, json_item in call_rpc_node('get_all_mempool_items').items()}
        #added_tx = new_mempool.keys() - self.mempool_items.keys()
        #removed_txs = self.mempool_items.keys() - new_mempool.keys()
        #with self.lock:
        #    logging(debug_logger, "DEBUG", f"NODE STATE - lock")
        #    conn = sqlite3.connect(DB_SB, timeout=SQL_TIMEOUT)
        #    for tx in added_tx:
        #        logging(debug_logger, "DEBUG", f"NODE STATE - tx: {tx}")
        #        self.mempool_items[tx] = new_mempool[tx]
        #        # add to the db
        #        raw_sb = new_mempool[tx].spend_bundle
        #        logging(debug_logger, "DEBUG", f"NODE STATE - raw_sb: {raw_sb}")
        #        sb = SpendBundle.from_json_dict(new_mempool[tx].spend_bundle)
        #        logging(debug_logger, "DEBUG", f"NODE STATE - {type(sb)}")
        #        WDB.insert_spend_bundle(conn, sb)
        #        logging(debug_logger, "DEBUG", f"NODE STATE - inserting SB")

        #    conn.close()
        #for tx in removed_txs:
        #    # here we should modify the status of the sb also in the db, as invalid or blocked
        #    if self.mempool_items[tx].removed_at is None:
        #        with self.lock:
        #            self.mempool_items[tx].removed_at = time.time()
        #    else:
        #        if self.mempool_items[tx].removed_at - time.time() > TXS_MEMPOOL_DELAY:
        #            with self.lock:
        #                self.mempool_archive = self.mempool_items.pop(tx)



    def parse_mempool_txs(self):
        for spend_bundle_hash, tx in self.mempool_items:
            pass
            # take SB
            # take input coin
            # fill coin types
            # take solution coin

        pass


    def update_chain_info(self):
        network_info = RPC.call_rpc_node('get_network_info')
        with self.lock:
            full_node_meta = self.full_node_meta
            full_node_meta.genesis_challenge = network_info["genesis_challenge"]
            full_node_meta.network_name = network_info["network_name"]

    def update_chain_state(self):
        blockchain_state = RPC.call_rpc_node('get_blockchain_state')
        print(blockchain_state)
        with self.lock:
            full_node_meta = self.full_node_meta
            if blockchain_state['peak'] is not None:
                full_node_meta.peak_height = blockchain_state['peak']['height']
                full_node_meta.peak_header_hash = blockchain_state['peak']['header_hash']
                if blockchain_state['peak']['timestamp'] is not None:
                    full_node_meta.peak_timestamp = blockchain_state['peak']['timestamp']
                full_node_meta.finished_challenge_slot_hashes = blockchain_state['peak']['finished_challenge_slot_hashes']
                full_node_meta.finished_infused_challenge_slot_hashes = blockchain_state['peak']['finished_infused_challenge_slot_hashes']
                full_node_meta.finished_reward_slot_hashes = blockchain_state['peak']['finished_reward_slot_hashes']
                full_node_meta.prev_hash = blockchain_state['peak']['prev_hash']
                full_node_meta.prev_transaction_block_hash = blockchain_state['peak']['prev_transaction_block_hash']
            else:
                full_node_meta.peak_height = None

            full_node_meta.difficulty = blockchain_state["difficulty"]
            full_node_meta.synced = blockchain_state["sync"]["synced"]
            full_node_meta.sync_mode = blockchain_state["sync"]["sync_mode"]
            full_node_meta.sub_slot_iters = blockchain_state["sub_slot_iters"]
            # full_node_meta.net_space = blockchain_state["space"]
            full_node_meta.net_space = blockchain_state["space"] / (1024**6), ' Eib'
            full_node_meta.node_id = blockchain_state["node_id"]
            full_node_meta.sync_tip_height = blockchain_state["sync"]["sync_tip_height"]
            full_node_meta.sync_progress_height = blockchain_state["sync"]["sync_progress_height"]


    def update_blocks(self):
        if self.is_blocks_loader_on_peak:
            self.blocks_loader.update_loader()

    def update_state(self, screenState):
        print("updating the state")
        while True:
            try:
                logging(debug_logger, "DEBUG", f"NODE STATE - updating node state")
                self.update_chain_state()
                self.update_mempool()
                logging(debug_logger, "DEBUG", f"NODE STATE - state updated")
            except Exception as e:
                print(e)
                traceback.print_exc()

            try:
                if "block_band" not in screenState.scopes or screenState.scopes["block_band"].data['on_peak']:
                    # if the band is not created it keep up with the peak.
                    # here it should update also the offset with the peak to do a real update
                    self.update_blocks()
                    logging(debug_logger, "DEBUG", f"NODE STATE - blocks updated")
            except:
                traceback.print_exc()


            time.sleep(10)

    def deepcopy_meta(self):
        return copy.deepcopy(self.full_node_meta)

    def deepcopy_mempool(self):
        return copy.deepcopy(self.mempool_items)

    def deepcopy_mempool_archive(self):
        return copy.deepcopy(self.mempool_archive)


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
    footer_text: str
    roto_clipboard: deque
    pending_action: List[Union[int, Callable]]

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
        self.footer_text = ""
        self.pending_action = []

        # init copy/paste
        self.roto_clipboard = deque(maxlen=5)
        self.scopes['copy'] = None
        self.scopes['paste'] = None


class Scope():
    gen_id = 0

    def __init__(self, name: str, screen_handler: Callable[..., None],
                 screenState: ScreenState):
        self.name = name
        # remove selected flag
        self.selected = False  # make a method to check if it is selected by the parent
        self.visible = False
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
        self.exec_esc = ScopeActions.exit_scope

    def set_visible(self):
        parent_scope: Scope = self.parent_scope
        if self.name not in parent_scope.sub_scopes:
            parent_scope.sub_scopes[self.name] = self 
        self.visible = True

    def reset_sub_scope_visibility(self):
        """Reset the valie of 'visible' for all the subscope"""
        for key, item in self.sub_scopes.items():
            item.visible = False

    def filter_sub_scope_by_visibility(self):
        """Remove sub scope that are not visible"""
        print("FILTERINGGGG")
        keys = list(self.sub_scopes.keys())
        print(keys)
        for key in keys:
            print(f"key {key}")
            print(f"visible value {self.sub_scopes[key].visible}")
            if not self.sub_scopes[key].visible:
                print(f"deleting the {key} key")
                self.sub_scopes.pop(key)

    ### consider to move this logic in each elements, should be more flexible
    def update(self):
        """Update the counter using the number of sub scopes"""

        self.filter_sub_scope_by_visibility()

        for key, item in self.sub_scopes.items():
            item.selected = False
        if len(self.sub_scopes) != 0:
            self.cursor = self.cursor % len(self.sub_scopes)
            sel_scope = list(self.sub_scopes.keys())[self.cursor]
            self.sub_scopes[sel_scope].selected = True

        self.reset_sub_scope_visibility()

    ### menu should be not create sub scope, but create the scope only once
    ### selected
    def update_legacy(self):
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


class ScopeActions():
    ### Scope executions for exec ###
    @staticmethod
    def activate_scope(scope: Scope, screenState: ScreenState):
        screenState.activeScope = scope
        return scope


    @staticmethod
    def activate_scope_from_sibling(scope: Scope, screenState: ScreenState):
        screenState.activeScope = scope
        parent = scope.parent_scope
        count = 0
        for key, item in parent.sub_scopes.items():
            if item == scope:
                parent.cursor = count
                scope.selected = True
            else:
                item.selected = False
            count += 1
        return scope


    @staticmethod
    def activate_scope_next_sibling(scope: Scope, screenState: ScreenState, *args):
        ### used in the block band
        parent = scope.parent_scope

        count = 0
        next_item = False
        next_scope = None
        for key, item in parent.sub_scopes.items():
            if item == scope:
                parent.cursor = count + 1
                scope.selected = False
                next_item = True
            elif next_item:
                screenState.activeScope = item
                item.selected = True
                next_item = False
                next_scope = item
            else:
                item.selected = False
            count += 1
        return next_scope


    @staticmethod
    def activate_scope_prev_sibling(scope: Scope, screenState: ScreenState, *args):
        ### used in the block band
        parent = scope.parent_scope

        count = 0
        prev_item_id = False
        prev_scope = None
        for key, item in parent.sub_scopes.items():
            if item == scope:
                prev_item_id = count - 1
                parent.cursor = prev_item_id
                scope.selected = False
            else:
                item.selected = False
            count += 1

        prev_scope = list(parent.sub_scopes.values())[prev_item_id]
        screenState.activeScope = prev_scope
        prev_scope.selected = True
        return prev_scope


    @staticmethod
    def select_next_scope(scope: Scope, screenState: ScreenState, *args):
        ### used in the block band
        parent = scope.parent_scope
        screenState.activeScope = parent
        parent.cursor += 1

        return parent


    @staticmethod
    def select_prev_scope(scope: Scope, screenState: ScreenState, *args):
        ### used in the block band
        parent = scope.parent_scope
        screenState.activeScope = parent
        parent.cursor -= 1

        return parent


    @staticmethod
    def activate_pk(scope: Scope, screenState: ScreenState):
        """Acvtivate the scope and set the active pk in the ScreenState"""
        screenState.activeScope = scope
        return scope


    @staticmethod
    def activate_grandparent_scope(scope: Scope, screenState: ScreenState):
        screenState.activeScope = scope.parent_scope.parent_scope
        return scope.parent_scope.parent_scope


    @staticmethod
    def get_N_scope(scope: Scope, screenState):
        scope.active = False
        active_scope_key = list(scope.sub_scopes.keys())[scope.cursor]

        new_scope = scope.sub_scopes[active_scope_key]
        new_scope.active = True
        return new_scope


    @staticmethod
    def activate_scope_and_set_pk(scope: Scope, screenState):
        """Activate both active and main scope and set the active finger"""
        screenState.activeScope = scope
        screenState.active_pk[0] = int(scope.name)  # Maibe use the possibility to
        # change the args input of the scope exec
        return scope


# used to open a coin view from a tab
# we can create a open_stuff function to not create a particular fn for each type
# and add the screen_fn as parameter
    @staticmethod
    def open_coin_wallet(scope: Scope, screenState: ScreenState, tail):
        new_name = f"{scope.parent_scope.name}_{tail}"
        new_scope = Scope(new_name, screen_coin_wallet, screenState)
        new_scope.parent_scope = scope  # parent_scope
        new_scope.data['tail'] = tail
        new_scope.exec = None
        screenState.activeScope = new_scope
        return new_scope


    @staticmethod
    def open_transaction(scope: Scope, screenState: ScreenState, spend_bundle_hash):
        new_name = f"{scope.parent_scope.name}_{spend_bundle_hash}"
        new_scope = Scope(new_name, screen_transaction, screenState)
        new_scope.parent_scope = scope  # parent_scope
        new_scope.data['spend_bundle_hash'] = spend_bundle_hash
        new_scope.exec = None
        screenState.activeScope = new_scope
        return new_scope


    @staticmethod
    def exit_scope(scope: Scope, screen_state: ScreenState, *args):
        if scope.parent_scope:
            screen_state.activeScope = scope.parent_scope
            return scope.parent_scope
