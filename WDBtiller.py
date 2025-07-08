import os
import sqlite3
import json
import zstd
from datetime import datetime

from chia.types.full_block import FullBlock
from chia.consensus.block_record import BlockRecord

from CONFtiller import (
    server_logger, ui_logger, logging, XCH_FAKETAIL, XCH_MOJO, CAT_MOJO
)


def print_json(dict):
    print(json.dumps(dict, sort_keys=True, indent=4))


def reconstruct_block_from_bytes(block_bytes: bytes):
    return FullBlock.from_bytes(zstd.decompress(block_bytes)).to_json_dict()


def reconstruct_block_record_from_bytes(block_bytes: bytes):
    return BlockRecord.from_bytes(block_bytes).to_json_dict()


def create_wallet_db(conn):
    """Creates the wallet database file if it doesn't already exist.
    coin_store.py in chia/full_node"""

    try:
        cursor = conn.cursor()

        # public key TABLE pk_state
        # subTable: wallet_state
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS pk_state ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "fingerprint int NOT NULL,"
            "label TEXT NOT NULL,"
            "public_key BLOB UNIQUE NOT NULL);")

        # wallet state TABLE wallet_state
        ## subTable addresses (if they are observable or not)
        ## subTable coins
        ## subTable transactions
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS wallet_state ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "pk_state_id INTEGER NOT NULL,"
            "tail INTEGER NOT NULL,"
            "block_height BLOB NOT NULL,"
            "confirmed_wallet_balance BLOB NOT NULL,"
            "spendable_balance BLOB NOT NULL,"
            "unspent_coin_count INT NOT NULL,"
            "FOREIGN KEY (pk_state_id) REFERENCES pk_state (id) ON DELETE CASCADE,"
            "UNIQUE (pk_state_id, tail))"
        )

        # asset name TABLE asset_name
        ## subTable asset_price
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS asset_name ("
            "tail BLOB PRIMARY KEY NOT NULL UNIQUE, "
            "name TEXT NOT NULL,"
            "ticker TEXT,"
            "description TEXT,"
            "preview_url TEXT,"
            "tags TEXT,"
            "twitter TEXT,"
            "discord TEXT,"
            "website TEXT)"
        )
        # add chia asset
        insert_asset(conn, XCH_FAKETAIL, 'chia', 'XCH')

        # asset price data TABLE asset_price
        # subTable historic asset price
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS asset_price ("
            "timestamp BIGINT PRIMARY KEY NOT NULL,"
            "tail NOT NULL,"
            "price REAL NOT NULL,"
            "currency TEXT NOT NULL,"
            "FOREIGN KEY (tail) REFERENCES asset_name (tail) ON DELETE CASCADE,"
            "UNIQUE (tail, timestamp, currency))"
        )

        # historic asset price TABLE historic_asset_price
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS historic_asset_price ("
            "asset_price_id INT NOT NULL,"
            "price REALE NOT NULL,"
            "timestamp BIGINT UNIQUE NOT NULL)"
        )

        # addresses TABLE
        ## native in the sense that are really on that address and not a ref like CAT or NFT
        ## could be enough the derivation path?
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS addresses ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "pk_state_id INTEGER NOT NULL,"
            "address TEXT NOT NULL,"
            "hd_path_root TEXT NOT NULL,"
            "hd_path_index INT NOT NULL,"
            "hardened BOOL NOT NULL,"
            "active_coins INT NOT NULL,"
            "active_coins_native INT NOT NULL,"
            "times_used INT NOT NULL,"
            "times_used_native INT NOT NULL,"
            "block_height BLOB NOT NULL)"
        )

        # TODO
        # for CAT create a new table that store only the used adx for each asset with all the statistics

        # table with the timestamp of the last update of particular tables
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS table_timestamps ("
            "table_name TEXT PRIMARY KEY UNIQUE NOT NULL,"
            "timestamp BIGINT NOT NULL)"
        )

        conn.commit()
        print("The WDB database was populated successfully.")
    except sqlite3.Error as e:
        print(f"Error creating the wallet database: {e}")
        logging(server_logger, "DEBUG", f"WDB error while creating the database: {e}")
        logging(server_logger, "DEBUG", "WDB error _________________________________________")
        logging(server_logger, "DEBUG", "WDB error _________________________________________")
        logging(server_logger, "DEBUG", "WDB error _________________________________________")


def insert_table_timestamp(conn, table_name):
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO table_timestamps ("
        "table_name, timestamp) VALUES (?, ?);",
        (table_name, datetime.now().timestamp()))

    conn.commit()


def retrive_table_timestamp(conn, table_name):
    cursor = conn.cursor()
    cursor.execute(
        "SELECT timestamp FROM table_timestamps WHERE table_name = ?;",
        (table_name,)
    )
    item = cursor.fetchone()
    timestamp = 0
    if item:
        timestamp = item[0]

    return timestamp


def get_row_count(conn, table_name):
    cursor = conn.cursor()
    cursor.execute(
        f"SELECT COUNT(*) FROM {table_name};",
    )
    count = cursor.fetchone()[0]
    return count


def retrive_all_pks(conn):
    conn.row_factory = sqlite3.Row  # enable dictionary access
    cursor = conn.cursor()
    pk_states = []

    try:
        cursor.execute("SELECT * FROM pk_state")
        pk_states = [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logging(server_logger, "DEBUG", f"WDB error while retriving the PK in the database: {e}")
        print(e)

    conn.row_factory = None  # restore the default value 
    return pk_states


def retrive_pk(conn, finger):
    cursor = conn.cursor()
    pk_state = None
    try:
        cursor.execute(
            "SELECT id, fingerprint, label, public_key "
            "FROM  pk_state "
            "WHERE fingerprint = ?;", (finger,))
        pk_state = cursor.fetchone()
    except Exception as e:
        logging(server_logger, "DEBUG", f"WDB error while retriving the PK in the database: {e}")
        print(e)

    if not pk_state:
        return None
    return pk_state


def delete_pk(name, label, private_property, subelements):
    pass


def insert_pk(conn, fingerprint, label, public_key):
    cursor = conn.cursor()
    # insert into the main table
    store_id = None
    try:
        cursor.execute(
            "INSERT OR IGNORE INTO pk_state ("
            "fingerprint, label, public_key) VALUES (?, ?, ?);",
            (fingerprint, label, public_key))

        # Get the ID of the inserted object if inserted
        if cursor.rowcount == 0:
            cursor.execute(
                "SELECT id FROM pk_state WHERE public_key = ?",
                (public_key,))
            store_id = cursor.fetchone()[0]
        else:
            store_id = cursor.lastrowid

        conn.commit()
    except Exception as e:
        logging(server_logger, "DEBUG", f"WDB error while inserting the PK in the database: {e}")
    return store_id


# update is still missing
def insert_wallet(conn, pk_state_id, tail, wallet_state):
    """Save the wallet data with the balance in mojo"""
    cursor = conn.cursor()
    # Insert into the main table
    mojo = CAT_MOJO
    if tail == XCH_FAKETAIL:
        mojo = XCH_MOJO
    store_id = None
    cursor.execute(
        "INSERT OR IGNORE INTO wallet_state ("
        "pk_state_id, tail, block_height, confirmed_wallet_balance, "
        "spendable_balance, unspent_coin_count) VALUES (?, ?, ?, ?, ?, ?);",
        (pk_state_id,
         tail,
         wallet_state.block_height,
         int(wallet_state.confirmed_wallet_balance * mojo),
         int(wallet_state.spendable_balance * mojo),
         wallet_state.unspent_coin_count))

    # find the store_id if the execute was IGNORE
    if cursor.rowcount == 0:
        cursor.execute(
            "SELECT id FROM wallet_state WHERE pk_state_id = ? AND tail = ?",
            (pk_state_id, tail)
        )
        store_id = cursor.fetchone()[0]
    else:
        store_id = cursor.lastrowid

    conn.commit()
    return store_id


def retrive_wallets_by_pk_state_id(conn, pk_state_id):
    conn.row_factory = sqlite3.Row  # enable dictionary access
    cursor = conn.cursor()
    wallet = []

    try:
        cursor.execute("SELECT * FROM wallet_state WHERE pk_state_id = ?", (pk_state_id,))
        wallet = [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logging(server_logger, "DEBUG", f"WDB error while retriving the PK in the database: {e}")
        print(e)

    conn.row_factory = None  # restore the default value
    return wallet


def insert_asset(conn, tail, name=None, ticker=None, description=None,
                 preview_url=None, twitter=None, discord=None, website=None):
    """The tail is text or bytes? I htink it is better to use the same as the chia
    codebase"""
    cursor = conn.cursor()
    # Insert into the main table
    cursor.execute(
        "INSERT OR IGNORE INTO asset_name ("
        "tail, name, ticker, description, preview_url, twitter, discord, website) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
        (tail, name, ticker, description, preview_url, twitter, discord, website))

    conn.commit()
    return tail


def retrive_asset(conn, tail):
    conn.row_factory = sqlite3.Row  # enable dictionary access
    cursor = conn.cursor()
    asset = None

    try:
        cursor.execute("SELECT * FROM asset_name WHERE tail = ?", (tail,))
        asset = dict(cursor.fetchone())
    except Exception as e:
        logging(server_logger, "DEBUG", f"WDB error while retriving the PK in the database: {e}")
        print(e)

    conn.row_factory = None  # restore the default value
    return asset


def get_asset_id(conn, tail):
    """Needed?"""
    # cursor = conn.cursor()
    # # Insert into the main table
    # store_id = None
    # cursor.execute(
    #     "SELECT id FROM asset_name WHERE tail = ?",
    #     (str(tail),)
    # )
    # logging(server_logger, "DEBUG", f"WDB tail: {tail}")
    # try:
    #     store_id = cursor.fetchone()[0]
    # except Exception as e:
    #     logging(server_logger, "ERROR", f"WDB exception ception {e}")
    #     cursor.execute("SELECT * FROM asset_name")
    #     store = cursor.fetchall()
    #     logging(server_logger, "ERROR", f"WDB following store {store}")
    #     for i in store:
    #         logging(server_logger, "ERROR", f"WDB {i[1]} and tail: {tail}")
    # logging(server_logger, "DEBUG", f"WDB store_id: {store_id}")
    # conn.commit()
    return tail


def insert_price(conn, tail, timestamp, price, currency):
    cursor = conn.cursor()
    # Insert into the main table
    store_id = None
    try:
        cursor.execute(
            "INSERT OR IGNORE INTO asset_price ("
            "timestamp, tail, price, currency) "
            "VALUES (?, ?, ?, ?);",
            (timestamp, tail, price, currency))
        store_id = cursor.lastrowid
    except Exception as e:
        logging(server_logger, "ERROR", f"WDB error inserting pricrs: {e}")
        print(e)
    conn.commit()
    return store_id


def retrive_price_tail_currency(conn, tail, currency):
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM asset_price WHERE tail = ? AND currency = ?;",
        (tail, currency)
    )
    prices = cursor.fetchall()
    if not prices:
        prices = None

    return prices


# retrive address should be only one function, with defaul parameter...
def retrive_address(conn, fingerprint, derivation_index):
    pk_state_id = retrive_pk(conn, fingerprint)[0]
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM addresses WHERE pk_state_id = ? AND hd_path_index = ?;",
        (pk_state_id, derivation_index)
    )
    addresses = cursor.fetchall()
    if not addresses:
        addresses = None

    return addresses


def retrive_address_range(conn, pk_state_id, derivation_index, n_elements):
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM addresses WHERE pk_state_id = ? "
        "ORDER BY hd_path_index LIMIT ? OFFSET ? ;",
        (pk_state_id, n_elements, derivation_index)
    )
    addresses = cursor.fetchall()
    if not addresses:
        addresses = None

    return addresses


def insert_address(conn, pk_state_id, hd_path, address, hardened):
    """Insert or update the address datas"""

    cursor = conn.cursor()
    store_id = None

    # split the hd_path at the last /
    i = 0
    last_slash = 4
    hd_path_root = ""
    hd_path_index = hd_path
    while i < last_slash:
        idx = hd_path_index.find("/")
        hd_path_root += hd_path_index[:idx + 1]
        hd_path_index = hd_path_index[idx + 1:]
        i += 1

    hd_path_index = int(hd_path_index)
    active_coins = 0
    active_coins_native = 0
    times_used = 0
    times_used_native = 0
    block_height = 0

    try:
        cursor.execute(
            "INSERT OR IGNORE INTO addresses ("
            "pk_state_id, address, hd_path_root, hd_path_index, hardened, active_coins, active_coins_native,"
            "times_used, times_used_native, block_height) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);",
            (pk_state_id, address, hd_path_root, hd_path_index, hardened, active_coins,
             active_coins_native, times_used, times_used_native, block_height))
        store_id = cursor.lastrowid
    except Exception as e:
        logging(server_logger, "ERROR", f"WDB error inserting new address: {e}")
        print(e)
    conn.commit()
    return store_id


# block state type
class BlockState:

    # height: int
    # infused: bool
    # mempool: bool
    # transaction_block: bool
    # cost: int
    # fullness: float  # redundant
    # signage_point_index: int
    # timestamp: int
    # fee: int
    # transactions: int  # obj: from where amount
    # additions: int  # coin
    # removals: int  # coin
    # rewards: int  # coin
    # pool_receiver: int  # address
    # farmer_receiver: int  # address
    # k-size of the winning plot

    def __init__(self, raw_data, full_init: bool):

        # raw data shape:
        ## 0 - header_hash
        ## 1 - prev_hash
        ## 2 - height
        ## 3 - sub_epoch_summary
        ## 4 - is_fully_compactified
        ## 5 - in_main_chain
        ## 6 - block
        ## 7 - block_record

        self.header_hash = raw_data[0]
        self.height = raw_data[2]
        self.sub_epoch_summary = raw_data[3]

        block = reconstruct_block_from_bytes(raw_data[6])
        block_record = reconstruct_block_record_from_bytes(raw_data[7])

        # blockrecords:
        self.fees = block_record['fees']
        self.header_hash = block_record['header_hash']
        self.farmer_puzzle_hash = block_record['farmer_puzzle_hash']
        self.pool_puzzle_hash = block_record['pool_puzzle_hash']
        self.deficit = block_record['deficit']   # what is it? number of block needed to be infused in this slot
        self.overflow = block_record['overflow']   # if the block end in the next slot or sub-slot, i don t remember
        self.prev_transaction_block_height = block_record['prev_transaction_block_height']
        self.reward_claims_incorporated = block_record['reward_claims_incorporated']   # amount, parent_coin_info, puzzle_hash
        self.signage_point_index = block_record['signage_point_index']
        self.required_iters = block_record['required_iters']
        self.sub_slot_iters = block_record['sub_slot_iters']
        self.total_iters = block_record['total_iters']
        self.weight = block_record['weight']
        self.timestamp = block_record['timestamp']

        # block:
        self.farmer_puzzle_hash_b = block['foliage']['foliage_block_data']['farmer_reward_puzzle_hash']
        self.pool_puzzle_hash_b = block['foliage']['foliage_block_data']['pool_target']['puzzle_hash']

        if block['foliage_transaction_block'] == "None":
            self.additions_merkle_root = block['foliage_transaction_block']['addition_root']  # merkle root of the coin additions
            self.timestamp_b = block['foliage_transaction_block']['timestamp']
        else:
            self.additions_merkle_root = None
            self.timestamp_b = None
        self.n_iteration_challenge_chain = block['reward_chain_block']['challenge_chain_ip_vdf']['number_of_iterations']
        self.height_b = block['reward_chain_block']['height']
        self.is_transaction_block_b = block['reward_chain_block']['is_transaction_block']
        self.plot_public_key = block['reward_chain_block']['proof_of_space']['plot_public_key']
        self.pool_public_key = block['reward_chain_block']['proof_of_space']['pool_public_key']
        self.proof_of_space_proof = block['reward_chain_block']['proof_of_space']['proof']
        self.proof_of_space_size = block['reward_chain_block']['proof_of_space']['size']
        self.signage_point_index_b = block['reward_chain_block']['signage_point_index']  # redundant
        self.total_iters_b = block['reward_chain_block']['total_iters']  # redundant
        self.weight_b = block['reward_chain_block']['weight']  # redundant
        self.transactions_generator = block['transactions_generator'] # chialisp
        self.transactions_generator_ref_list = block['transactions_generator_ref_list']  # ref to other block if needed
        if block['transactions_info'] == "None":
            self.aggregate_signature = block['transactions_info']['aggregated_signature']
            self.cost = block['transactions_info']['cost']  # total cost
            self.fees_b = block['transactions_info']['fees']
        else:
            self.aggregate_signature = None
            self.cost = None
            self.fees_b = None

    def __str__(self):
        return f"Block height: {self.height:,}; sp: {self.signage_point_index}; ts: {self.timestamp} and {self.timestamp_b} ; header: {self.header_hash}"


##### Data chunk loader
import threading
import time
from dataclasses import dataclass


def make_sql_fetcher(table, sort_column="id"):
    def fetch(conn, start, count, filters=None):
        if not filters:
            filters = {}

        #print(f" fileter : {filters}")
        where_clauses = []
        values = []

        for filter, val in filters.items():
            where_clauses.append(f"{filter} = ?")
            values.append(val)

        #print(f"where clau {where_clauses}")
        where_sql = f" WHERE {' AND '.join(where_clauses)} AND {sort_column} > ?" if filters else f" WHERE {sort_column} > ?"
        #where_sql = f" WHERE {' AND '.join(where_clauses)}" if filters else ""

        cur = conn.cursor()
        ### ref ### query = "SELECT * FROM full_blocks WHERE height > ? ORDER BY height LIMIT ?;"
        query = f"SELECT * FROM {table} {where_sql} ORDER BY {sort_column} LIMIT ?"
        #query = f"SELECT * FROM {table} {where_sql} ORDER BY {sort_column} LIMIT ? OFFSET ?"
        print(f"questy: {query}")
        values.extend([start, count])
        print(query)
        print(values)
        cur.execute(query, values)
        return cur.fetchall()

    return fetch


@dataclass
class Chunk:
    chunk_idx: int
    first_idx: int
    data: list


class DataChunkLoader:
    def __init__(self, conn, table_name: str, chunk_size: int, offset: int = 0, sorting_column="id", filters=None, data_struct=None):
        """offset = distance from the beging of the array of elements
           filters = a dic with filter and value. EG. {'pk_state_id': 2, 'other_filter': 'yellow'}"""
        self.table_name = table_name
        self.total_row_count = self.update_total_row_count(conn)
        self.sorting_column = sorting_column
        self.lock = threading.Lock()
        self.current_offset: int = offset
        self.chunk_size: int = chunk_size
        self.chunk_arena_size = 5  # n. of chunks kept in memory
        self.chunk_arena: list[Chunk] = [None] * self.chunk_arena_size
        self.main_chunk_pointer: int = 0
        self.fetcher = make_sql_fetcher(table_name, self.sorting_column)
        self.data_struct = data_struct
        self.filters = filters

        # fetch_main chunk
        self.chunk_arena[self.main_chunk_pointer] = self.fetch_chunk(conn, self.current_offset)
        if (self.current_offset - self.chunk_size) >= 0:
            pre_chunk_pointer = (self.main_chunk_pointer - 1) % self.chunk_arena_size
            self.chunk_arena[pre_chunk_pointer] = self.fetch_chunk(conn, self.current_offset - self.chunk_size)
        post_chunk_pointer = (self.main_chunk_pointer + 1) % self.chunk_arena_size
        self.chunk_arena[post_chunk_pointer] = self.fetch_chunk(conn, self.current_offset + self.chunk_size)

    def update_offset(self, offset: int):
        with self.lock:
            self.current_offset = offset

    def change_current_offset(self, idx):
        self.current_offset = idx

    def update_total_row_count(self, conn):
        return get_row_count(conn, self.table_name)

    def fetch_db(self, conn, start, count):
        return self.fetcher(conn, start, count, self.filters)

    def fetch_chunk(self, conn, data_index):
        chunk_idx = data_index // self.chunk_size
        chunk_first_idx = chunk_idx * self.chunk_size
        # chunk_last_idx = chunk_first_idx + self.chunk_size
        data = self.fetch_db(conn, chunk_first_idx, self.chunk_size)
        if self.data_struct is not None:
            sturctured_data = []
            for d in data:
                sturctured_data.append(self.data_struct(d, False))
            data = sturctured_data

        return Chunk(chunk_idx, chunk_first_idx, data)

    def update_current_chunk(self):
        current_chunk_idx = self.get_current_chunk().chunk_idx
        if self.current_offset // self.chunk_size > current_chunk_idx:
            self.main_chunk_pointer = (self.main_chunk_pointer + 1) % self.chunk_arena_size
        elif self.current_offset // self.chunk_size < current_chunk_idx:
            self.main_chunk_pointer = (self.main_chunk_pointer - 1) % self.chunk_arena_size

    def get_current_item(self):
        with self.lock:
            current_chunk_idx = self.get_current_chunk().chunk_idx
            if self.current_offset // self.chunk_size > current_chunk_idx:
                self.main_chunk_pointer = (self.main_chunk_pointer + 1) % self.chunk_arena_size
            elif self.current_offset // self.chunk_size < current_chunk_idx:
                self.main_chunk_pointer = (self.main_chunk_pointer - 1) % self.chunk_arena_size

            data_idx = self.current_offset % self.chunk_size
            return self.get_current_chunk().data[data_idx]

    def get_item_by_idx(self, idx):
        with self.lock:
            chunk_idx = idx // self.chunk_size
            # check if the chunk is in the cache
            for i in self.chunk_arena:
                if chunk_idx == i.chunk_idx:
                    data_idx = idx % self.chunk_size
                    return i.data[data_idx]
                else:
                    return None

    def get_items_hot_chunks(self):
        """Return (data, chunk_idx, n_chunks) where:
        chunk_idx: is the index of the first valid chunk"""
        with self.lock:
            current_chunk: Chunk = self.get_current_chunk()
            pre_chunk: Chunk = self.chunk_arena[(self.main_chunk_pointer - 1) % self.chunk_arena_size]
            post_chunk: Chunk = self.chunk_arena[(self.main_chunk_pointer + 1) % self.chunk_arena_size]

            data = []
            chunk_idx = None
            if pre_chunk:
                data.extend(pre_chunk.data)
                chunk_idx = pre_chunk.chunk_idx
            else:
                chunk_idx = current_chunk.chunk_idx
            data.extend(current_chunk.data)
            if post_chunk:
                data.extend(post_chunk.data)

            return data, chunk_idx * self.chunk_size


    def update_loader(self, conn):
        with self.lock:
            # TODO: is this the place to update also the offset wiht scope.cursor?
            self.update_current_chunk()
            current_chunk: Chunk = self.get_current_chunk()
            pre_chunk: Chunk = self.chunk_arena[(self.main_chunk_pointer - 1) % self.chunk_arena_size]
            post_chunk: Chunk = self.chunk_arena[(self.main_chunk_pointer + 1) % self.chunk_arena_size]

            # add logic to deal with empty chunks
            if not post_chunk or current_chunk.chunk_idx + 1 != post_chunk.chunk_idx:
                post_chunk_pointer = (self.main_chunk_pointer + 1) % self.chunk_arena_size
                self.chunk_arena[post_chunk_pointer] = self.fetch_chunk(conn, self.current_offset + self.chunk_size)

            if current_chunk.chunk_idx > 0:
                if not pre_chunk or current_chunk.chunk_idx - 1 != pre_chunk.chunk_idx:
                    pre_chunk_pointer = (self.main_chunk_pointer - 1) % self.chunk_arena_size
                    self.chunk_arena[pre_chunk_pointer] = self.fetch_chunk(conn, self.current_offset - self.chunk_size)

    def get_current_chunk(self):
        return self.chunk_arena[self.main_chunk_pointer]



if __name__ == "__main__":


    from CONFtiller import DB_WDB, SQL_TIMEOUT
    from time import sleep
    import traceback
    conn = sqlite3.connect(DB_WDB, timeout=SQL_TIMEOUT)


    # test blockchain DB
    db_path = "/mnt/chiaDB/mainnet/db/blockchain_v2_mainnet.sqlite"

    # connection = sqlite3.connect(db_path)
    # read only read
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)

    table_name = 'full_blocks'
    chunk_size = 20  # height * 2  # to be sure to have at least 2 full screen of data
    offset = 34000
    sorting_column = 'height'
    filters = {}
    data_loader = DataChunkLoader(conn, table_name, chunk_size, offset, filters=filters, sorting_column=sorting_column, data_struct=BlockState)

    ## one block
    ## fetch all the coins
    ## Define the query
    #query = "SELECT * FROM full_blocks WHERE height = ?"

    #height = 333_222

    ## Execute the query with a parameter
    #cursor = conn.cursor()
    #cursor.execute(query, (height,))

    ## Fetch all matching rows
    #rows = cursor.fetchall()[0]

    #for row in rows:
    #    print(row)
    #    print("|||||||||||")


    #print('rows 6')
    #print(rows[6])
    #fb = FullBlock.from_bytes(zstd.decompress(rows[6]))
    #print_json(fb.to_json_dict())

    #fbJ = fb.to_json_dict()
    #print(fbJ.keys())
    #print(fbJ['reward_chain_block']['challenge_chain_ip_vdf']['output']['data'])

    ## block record
    #br = rows[7]
    #br = BlockRecord.from_bytes(rows[7])
    #print_json(br.to_json_dict())
    #brJ = br.to_json_dict()
    #print(brJ['infused_challenge_vdf_output']['data'])

    #print('show blocks in the chunks')
    #print('_________________________')

    bbs, idx = data_loader.get_items_hot_chunks()
    print(len(bbs))
    for b in bbs:
        print(b)


    # fing the peak

    from RPCtiller import call_rpc_node

    blockchain_state = call_rpc_node('get_blockchain_state')
    height_last_block = int(blockchain_state['peak']['height'])
    
    print(f'peak {height_last_block}') 

    offset = height_last_block
    data_loader = DataChunkLoader(conn, table_name, chunk_size, offset, filters=filters, sorting_column=sorting_column, data_struct=BlockState)
    bbs, idx = data_loader.get_items_hot_chunks()
    print(len(bbs))

    for b in bbs:
        print(b)

    print(f'peak {height_last_block:_}')

    ## one block
    ## fetch all the coins
    ## Define the query
    query = "SELECT * FROM full_blocks WHERE height = ?"
    query = "SELECT * FROM full_blocks  ORDER BY height LIMIT ? OFFSET ?"
    query = "SELECT * FROM full_blocks WHERE height > ? ORDER BY height LIMIT ?;"

    values = (height_last_block,)
    values = (5, 10)
    values = (5, height_last_block - 1000)
    values = (height_last_block + 5, 5)

    # Execute the query with a parameter
    cursor = conn.cursor()
    cursor.execute(query, values)

    # Fetch all matching rows
    rows = cursor.fetchall()

    print(f'peak {height_last_block:_}')
    print(f"values: {values}")
    for row in rows:
        print('row block')
        print(row[0])
        print(row[1])
        print(row[2])

    print('boom')

    conn.close()

    exit()

    # test loading chunks

    def th_update_loader(loader: DataChunkLoader):
        try:
            th_conn = sqlite3.connect(DB_WDB, timeout=SQL_TIMEOUT)
            while True:
                loader.update_loader(th_conn)
                sleep(1.01)
        except Exception:
            traceback.print_exc()

    # row count
    c = get_row_count(conn, "addresses")
    print('row')
    print(type(c))
    print(c)


    # change name of the address table from addresses to address
    fi = retrive_address(conn, 291595168, 1)
    print(fi)

    fo = retrive_address_range(conn, 1, 1, 5)
    print(fo)


    table_name = 'addresses'
    chunk_size = 3
    offset = 0
    #filters = {'pk_state_id': 2,}
    filters = {'pk_state_id': 2, 'hardened': False}
    data_chunk_loader = DataChunkLoader(conn, table_name, chunk_size, offset, filters=filters)

    cu = data_chunk_loader.get_current_item()
    print('current item: ', cu)


    chunks_preloaded = data_chunk_loader.get_items_hot_chunks()[0]
    print("chunks preloaded")
    for e, i in enumerate(chunks_preloaded):
        print(f"{e} - {i}")

    loader_thread = threading.Thread(target=th_update_loader, args=(data_chunk_loader,), daemon=True)
    loader_thread.start()

    for i in range(30):
        cu = data_chunk_loader.get_current_item()
        print(f'{i} - current item: {cu}')
        data_chunk_loader.change_current_offset(data_chunk_loader.current_offset + 1)
        sleep(0.55)
        #data_chunk_loader.update_loader(conn)
        if i == 20:
            chunks_preloaded = data_chunk_loader.get_items_hot_chunks()[0]
            print("chunks preloaded")
            for e, i in enumerate(chunks_preloaded):
                print(f"{e} - {i}")

    conn.close()






