import json
import zstd
import copy
import traceback
import sqlite3
import time
from datetime import datetime
from dataclasses import dataclass
from typing import List, Tuple, Dict, Union, Callable

##### Data chunk loader
import threading

try:
    from chia.types.full_block import FullBlock
    from chia.consensus.block_record import BlockRecord
    from chia.types.spend_bundle import SpendBundle
    from chia.types.spend_bundle_conditions import SpendBundleConditions, SpendConditions
except ImportError:
    try:
        from chia_rs import FullBlock, BlockRecord, SpendBundle, SpendBundleConditions, SpendConditions
    except ImportError:
        print('probably a full_node verison not supporter')

from chia_rs import CoinSpend, Coin
from chia_rs import Program as RsProgram
from chia.types.blockchain_format.program import Program as PyProgram
from chia_rs.sized_bytes import bytes32
from chia_rs.sized_ints import uint16, uint32, uint64, uint128
from clvm.casts import int_from_bytes, int_to_bytes
from chia.types.condition_opcodes import ConditionOpcode

from chia_rs import (ELIGIBLE_FOR_DEDUP, ELIGIBLE_FOR_FF, BLSCache, ConsensusConstants,
    G2Element, supports_fast_forward, validate_clvm_and_signature)

from chia.consensus.default_constants import DEFAULT_CONSTANTS
from chia.util.bech32m import decode_puzzle_hash, encode_puzzle_hash

from src.UTILStiller import timestamp_to_date
from src.CONFtiller import (
    debug_logger, logging, XCH_FAKETAIL, XCH_PREFIX, XCH_MOJO, CAT_MOJO, SQL_TIMEOUT, DB_SB)
import src.TYPEStiller as TYPES

import src.RPCtiller as RPC
import src.UTILStiller as UTILS
import src.PUZZLEtiller as PUZ
import src.CONFtiller as CONF




import csv
import os
from pathlib import Path



def print_json(dict):
    print(json.dumps(dict, sort_keys=True, indent=4))


def reconstruct_block_from_bytes(block_bytes: bytes):
    return FullBlock.from_bytes(zstd.decompress(block_bytes)).to_json_dict()


def reconstruct_block_record_from_bytes(block_bytes: bytes):
    return BlockRecord.from_bytes(block_bytes).to_json_dict()


# Load and save csv
def load_csv(path: Path):
    """Load all the row in the CSV file."""
    with open(path, newline="", encoding="utf-8") as f:
        #f = [row for row in f if not row.strip().startswith("#")]
        reader = csv.reader(f, quotechar="'", skipinitialspace=True)
        #next(reader, None)  # jump the first line
        return list(reader)


def load_csv_no_comments(path: Path):
    """Load a CSV file, skipping any lines that start with #."""
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(
            (row for row in f if not row.strip().startswith("#")),
            quotechar="'",
            skipinitialspace=True
        )
        return list(reader)


def save_csv(path: Path, rows: list[tuple[str, str, str]]):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")

    with tmp_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)
        f.flush()
        os.fsync(f.fileno())

    os.replace(tmp_path, path)


def get_connection(db_path):
    conn = sqlite3.connect(db_path, uri=True, timeout=CONF.SQL_TIMEOUT)
    conn.execute("PRAGMA journal_mode=WAL;")  # allow writing and reading concurrently
    conn.execute("PRAGMA synchronous=NORMAL;")  # Recommended for WAL mode
    return conn


def create_cache_blockchain_db(conn):
    """Create a partial local enriched db of the blockchain"""

    # add db version
    # add info about last update?
    #### spent coin, do not need update
    #### unspent coin, add column last time checked?

    CACHED_DB_VERSION = 0

    try:
        cursor = conn.cursor()
        # DB verison

        cursor.execute(
            "CREATE TABLE IF NOT EXISTS cached_DB_version ("
            "key TEXT PRIMARY KEY, "
            "value INT "
            ");"
        )
        logging(debug_logger, "DEBUG", "WDB cached error A")

        # INIT the version if it is empty
        cursor.execute(
            f"INSERT OR IGNORE INTO cached_DB_version (key, value) "
            f"VALUES ('version', {CACHED_DB_VERSION});"
        )
        logging(debug_logger, "DEBUG", "WDB cached error B")

        # address summary
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS cached_address_info ("
            "puzzle_hash BLOB PRIMARY KEY, "
            "last_height INT, "
            "balance INT, "
            "total_coin_count INT, "
            "unspent_coin_count INT, "
            "total_hinted_count INT, "
            "unspent_hinted_count INT);"
        )

        # coin_records
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS cached_coin_record ("
            "coin_name BLOB PRIMARY KEY, "
            "confirmed_index BIGINT, "
            "spent_index BIGINT, "
            "coinbase INT, "
            "puzzle_hash BLOB, "
            "coin_parent BLOB, "
            "amount BIGINT, "
            "timestamp BIGINT, "
            "record_type INT, "  # 0-full, 1-partial (for children) # lets see, i could not be needed
            "parent_puzzle_hash BLOB, "  # at the moment we will keep it. We will see if to store the full coin data later
            "child_count INT, "
            "coin_type INT, "
            "coin_type_metadata BLOB, "  # like tail
            "full_memo BLOB, "
            "hint BLOB, "
            # coin sent from the same puzzle hash, computed by sqlite, used in the indexes for the remove_self filter
            "is_self INT GENERATED ALWAYS AS (COALESCE(parent_puzzle_hash = puzzle_hash, 0)) VIRTUAL);"
        )

        # add is_self to caches created before it existed
        columns = [row[1] for row in cursor.execute("PRAGMA table_xinfo(cached_coin_record);")]
        if 'is_self' not in columns:
            cursor.execute(
                "ALTER TABLE cached_coin_record ADD COLUMN "
                "is_self INT GENERATED ALWAYS AS (COALESCE(parent_puzzle_hash = puzzle_hash, 0)) VIRTUAL;"
            )

        cursor.execute(
            "CREATE TABLE IF NOT EXISTS cached_memo_progress ("
            "puzzle_hash BLOB PRIMARY KEY, "
            "last_confirmed_index BIGINT "
            ");"
        )

        # where the cache updater arrived, for all the followed addresses (one row)
        # the header hash is used to detect reorgs
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS cached_sync_state ("
            "id INTEGER PRIMARY KEY CHECK (id = 0), "
            "height BIGINT, "
            "header_hash BLOB);"
        )

        # addresses kept up to date by the cache updater, added once their first build is done
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS cached_followed ("
            "puzzle_hash BLOB PRIMARY KEY);"
        )

        logging(debug_logger, "DEBUG", "WDB cached error C")
        # indexes
        ## puzzle hash
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_puzzle_hash ON cached_coin_record(puzzle_hash);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_parent_puzzle_hash ON cached_coin_record(parent_puzzle_hash);")
        # used by the address loaders (inbound and outbound): sort by confirmed_index and apply
        # the filters reading only the index (the first time, on a big existing cache, building them takes a while)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cache_inbound ON cached_coin_record("
                       "puzzle_hash, confirmed_index, spent_index, is_self);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cache_outbound ON cached_coin_record("
                       "parent_puzzle_hash, confirmed_index, record_type, spent_index, is_self);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_confirmed_index ON cached_coin_record(confirmed_index);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_spent_index ON cached_coin_record(spent_index);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_coin_type_metadata ON cached_coin_record(coin_type_metadata);")
        #cursor.execute("CREATE INDEX IF NOT EXISTS idx_cache_fetch ON cached_coin_record (puzzle_hash, confirmed_index, spent_index")  # new to check
        ## coin type
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_coin_type ON cached_coin_record(coin_type);")
        ## parent coin id
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_parent ON cached_coin_record(coin_parent);")

        conn.commit()
        cursor.close()

    except sqlite3.Error as e:
        print(f"Error creating the cached DB: {e}")
        logging(debug_logger, "DEBUG", f"WDB error while creating the cached DB: {e}")
        logging(debug_logger, "DEBUG", "WDB cached error _________________________________________")
        logging(debug_logger, "DEBUG", "WDB cached error _________________________________________")
        logging(debug_logger, "DEBUG", "WDB cached error _________________________________________")


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
        logging(debug_logger, "DEBUG", f"WDB error while creating the database: {e}")
        logging(debug_logger, "DEBUG", "WDB error _________________________________________")
        logging(debug_logger, "DEBUG", "WDB error _________________________________________")
        logging(debug_logger, "DEBUG", "WDB error _________________________________________")


def insert_cache_address_info(conn, puzzle_hash, last_height, balance, total_coin_count,
                              unspent_coin_count, total_hinted_count=None, unspent_hinted_count=None):
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO cached_address_info ("
        "puzzle_hash, last_height, balance, total_coin_count, "
        "unspent_coin_count, total_hinted_count, unspent_hinted_count) "
        "VALUES (?, ?, ?, ?, ?, ?, ?);",
        (puzzle_hash, last_height, balance, total_coin_count, unspent_coin_count,
         total_hinted_count, unspent_hinted_count)
    )
    conn.commit()


def retrive_cache_address_info(conn, puzzle_hash):
    cursor = conn.cursor()
    cursor.execute(
        "SELECT "
        "last_height, balance, total_coin_count, "
        "unspent_coin_count, total_hinted_count, unspent_hinted_count "
        "FROM cached_address_info "
        "WHERE puzzle_hash = ?;",
        (puzzle_hash,)
    )
    item = cursor.fetchone()
    return item


def retrive_cache_db_stats(conn, db_path: Path):
    """Size of the cache DB and the addresses stored in it.
       The size of an address is an estimate: its share of the rows times the DB size.
       The rows of an address are its coins and the coins it created (children and phantom)."""
    page_size = conn.execute("PRAGMA page_size;").fetchone()[0]
    page_count = conn.execute("PRAGMA page_count;").fetchone()[0]
    db_size = page_size * page_count
    wal_path = Path(f"{db_path}-wal")
    wal_size = wal_path.stat().st_size if wal_path.exists() else 0
    file_size = Path(db_path).stat().st_size + wal_size

    total_rows = conn.execute("SELECT COUNT(*) FROM cached_coin_record;").fetchone()[0]

    addresses = []
    for puzzle_hash, last_height, balance in conn.execute(
            "SELECT puzzle_hash, last_height, balance FROM cached_address_info;").fetchall():
        coins = conn.execute(
            "SELECT COUNT(*) FROM cached_coin_record INDEXED BY idx_cache_inbound WHERE puzzle_hash = ?;",
            (puzzle_hash,)).fetchone()[0]
        created = conn.execute(
            "SELECT COUNT(*) FROM cached_coin_record INDEXED BY idx_cache_outbound WHERE parent_puzzle_hash = ?;",
            (puzzle_hash,)).fetchone()[0]
        # coins sent to itself are counted in both
        self_coins = conn.execute(
            "SELECT COUNT(*) FROM cached_coin_record INDEXED BY idx_cache_inbound WHERE puzzle_hash = ? AND is_self = 1;",
            (puzzle_hash,)).fetchone()[0]
        rows = coins + created - self_coins
        size = db_size * rows // total_rows if total_rows else 0
        addresses.append({'puzzle_hash': bytes(puzzle_hash), 'last_height': last_height, 'balance': balance,
                          'coins': coins, 'created': created, 'rows': rows, 'size': size})

    addresses.sort(key=lambda a: a['size'], reverse=True)
    return {'file_size': file_size, 'wal_size': wal_size, 'db_size': db_size,
            'total_rows': total_rows, 'addresses': addresses}


CACHE_DATA_TABLES = ("cached_coin_record", "cached_address_info", "cached_memo_progress",
                     "cached_sync_state", "cached_followed")


def clear_cache_db(conn):
    """Delete every address and coin of the cache DB (the tables stay), then VACUUM so the
       file shrinks. Use CacheUpdater.clear(), it stops the updater while the cache is emptied"""
    for table in CACHE_DATA_TABLES:
        conn.execute(f"DELETE FROM {table};")
    conn.commit()
    shrink_cache_db(conn)


def shrink_cache_db(conn):
    """VACUUM after a big delete, so the file shrinks. The delete is already committed: if the
       VACUUM fails (e.g. the DB is busy) the free pages stay in the file and are reused later"""
    try:
        conn.execute("VACUUM;")
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
    except sqlite3.OperationalError as e:
        logging(debug_logger, "DEBUG", f"cache VACUUM skipped: {e}")


def delete_cache_address(conn, puzzle_hash, vacuum=True):
    """Delete one address from the cache DB: its coins and the coins it created, except the
       rows another cached address still uses (a coin sent between two cached addresses).
       Use CacheUpdater.remove(), it stops the updater while the rows are deleted"""
    puzzle_hash = bytes(puzzle_hash)
    others = "SELECT puzzle_hash FROM cached_address_info WHERE puzzle_hash != ?"
    conn.execute(
        "DELETE FROM cached_coin_record INDEXED BY idx_puzzle_hash WHERE puzzle_hash = ? "
        f"AND (parent_puzzle_hash IS NULL OR parent_puzzle_hash NOT IN ({others}));",
        (puzzle_hash, puzzle_hash))
    conn.execute(
        "DELETE FROM cached_coin_record INDEXED BY idx_parent_puzzle_hash WHERE parent_puzzle_hash = ? "
        f"AND (puzzle_hash IS NULL OR puzzle_hash NOT IN ({others}));",
        (puzzle_hash, puzzle_hash))
    for table in ("cached_address_info", "cached_memo_progress", "cached_followed"):
        conn.execute(f"DELETE FROM {table} WHERE puzzle_hash = ?;", (puzzle_hash,))
    # no address followed anymore: the next followed one starts the sync from its own build
    if conn.execute("SELECT COUNT(*) FROM cached_followed;").fetchone()[0] == 0:
        conn.execute("DELETE FROM cached_sync_state;")
    conn.commit()
    if vacuum:
        shrink_cache_db(conn)


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


def get_row_count(conn, table_name, filters={}):
    """ Really slow if filters (not indexed) are used """

    where_clauses = []
    values = []

    for filter, val in filters.items():
        where_clauses.append(f"{filter} = ?")
        values.append(val)

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if filters else ""
    query = f"SELECT COUNT(*) FROM {table_name} {where_sql}"

    print(f" row count: {query} val {values}")
    cursor = conn.cursor()
    cursor.execute(query, values)
    count = cursor.fetchone()[0]
    print(f"count {count}")
    return count


def retrive_all_pks(conn):
    conn.row_factory = sqlite3.Row  # enable dictionary access
    cursor = conn.cursor()
    pk_states = []

    try:
        cursor.execute("SELECT * FROM pk_state")
        pk_states = [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logging(debug_logger, "DEBUG", f"WDB error while retriving the PK in the database: {e}")
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
        logging(debug_logger, "DEBUG", f"WDB error while retriving the PK in the database: {e}")
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
        logging(debug_logger, "DEBUG", f"WDB error while inserting the PK in the database: {e}")
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
        logging(debug_logger, "DEBUG", f"WDB error while retriving the PK in the database: {e}")
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
        logging(debug_logger, "DEBUG", f"WDB error while retriving the PK in the database: {e}")
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
    # logging(debug_logger, "DEBUG", f"WDB tail: {tail}")
    # try:
    #     store_id = cursor.fetchone()[0]
    # except Exception as e:
    #     logging(debug_logger, "ERROR", f"WDB exception ception {e}")
    #     cursor.execute("SELECT * FROM asset_name")
    #     store = cursor.fetchall()
    #     logging(debug_logger, "ERROR", f"WDB following store {store}")
    #     for i in store:
    #         logging(debug_logger, "ERROR", f"WDB {i[1]} and tail: {tail}")
    # logging(debug_logger, "DEBUG", f"WDB store_id: {store_id}")
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
        logging(debug_logger, "ERROR", f"WDB error inserting pricrs: {e}")
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
        logging(debug_logger, "ERROR", f"WDB error inserting new address: {e}")
        print(e)
    conn.commit()
    return store_id


######################## spend bundles db ##########################

# tables whose old schema allowed one bundle per coin and one group per bundle
_OLD_SPEND_BUNDLE_TABLES = {
    'coin_spends': ('coin_id BLOB NOT NULL UNIQUE',
                    'spend_bundle_id, coin_id, parent_id, amount, puzzle_reveal_hash, solution'),
    'spend_bundle_groups': ('spend_bundle_id BLOB NOT NULL UNIQUE', 'group_id, spend_bundle_id'),
}


def _rename_old_spend_bundle_tables(cursor):
    """Rename the tables with the old constraints to <table>_old, so they are created again
    with the new ones. Returns the renamed tables."""
    renamed = []
    for table, (old_column, _) in _OLD_SPEND_BUNDLE_TABLES.items():
        cursor.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?;", (table,))
        row = cursor.fetchone()
        if row is not None and old_column in row[0]:
            cursor.execute(f"ALTER TABLE {table} RENAME TO {table}_old;")
            renamed.append(table)
    if 'coin_spends' in renamed:
        # the indexes move with the renamed table, drop them so they are created on the new one
        cursor.execute("DROP INDEX IF EXISTS idx_coin_spend_bundle_id;")
        cursor.execute("DROP INDEX IF EXISTS idx_coin_id;")
    return renamed


def _copy_old_spend_bundle_tables(cursor, renamed):
    for table in renamed:
        columns = _OLD_SPEND_BUNDLE_TABLES[table][1]
        cursor.execute(f"INSERT OR IGNORE INTO {table} ({columns}) SELECT {columns} FROM {table}_old;")
        cursor.execute(f"DROP TABLE {table}_old;")


def create_spend_bundle_db(conn):
    """Creates a database to store spend bundles and puzzles if it doesn't already exist.
    Puzzle reveals are store in a separate table and referenced by hash. """

    try:
        cursor = conn.cursor()
        if not conn.in_transaction:
            cursor.execute("BEGIN;")  # the migration renames and copies tables: all or nothing
        renamed = _rename_old_spend_bundle_tables(cursor)

        # puzzle table
        # i think i shoud get the hash of the first uncurried puzzle. The last curried stuff
        ## should be always the std transaction and so the puzzle_hash change always because the
        ## public key is curried in
        ### i should check the levels of uncurried puzzle, and i lev 1 exist exlude that one
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS puzzles("
            "puzzle_hash BLOB PRIMARY KEY NOT NULL UNIQUE, "
            "clvm BLOB NOT NULL, "
            "size INT);"
        )

        ## coin spend db
        # parent id, amount and puzzle hash are already on the chain. Could be deleted
        # puzzle_reveal reference to the puzzles TABLE
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS coin_spends("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "spend_bundle_id INT NOT NULL, "
            "coin_id BLOB NOT NULL, "
            "parent_id BLOB NOT NULL, "
            "amount INT NOT NULL, "
            #"puzzle_hash BLOB NOT NULL,"
            "puzzle_reveal_hash BLOB NOT NULL, "
            "solution BLOB NOT NULL, "

            "FOREIGN KEY (puzzle_reveal_hash) REFERENCES puzzles(puzzle_hash), "
            "FOREIGN KEY (spend_bundle_id) REFERENCES spend_bundles(id), "
            # a coin can be spent by more bundles (a fee bump, a double spend)
            "UNIQUE (spend_bundle_id, coin_id));"

        )

        # spend bundle TABLE spend_bundles
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS spend_bundles("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "spend_bundle_hash BLOB NOT NULL UNIQUE, "  # spend bundle hash
            "timestamp BIGINT NOT NULL, "  # first appearance
            "block_height INT, "
            "status TEXT NOT NULL, "  # change to INT: 0-pending, 1-confirmed, 2-invalid
            "aggregated_signature BLOB NOT NULL, "
            "raw_spend_bundle BLOB NOT NULL, "
            "replaced_by INT REFERENCES spend_bundles(id));"  # the fee bump that took its place
        )
        cursor.execute("PRAGMA table_info(spend_bundles);")
        if 'replaced_by' not in [column[1] for column in cursor.fetchall()]:
            cursor.execute("ALTER TABLE spend_bundles ADD COLUMN replaced_by INT REFERENCES spend_bundles(id);")

        cursor.execute(
            "CREATE TABLE IF NOT EXISTS spend_bundle_group_names ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "name TEXT NOT NULL UNIQUE);"
        )

        # spend bundle groups (eg: watchlater)
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS spend_bundle_groups ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "group_id INT NOT NULL, "
            "spend_bundle_id INT NOT NULL, "
            "FOREIGN KEY (group_id) REFERENCES spend_bundle_group_names(id), "
            "FOREIGN KEY (spend_bundle_id) REFERENCES spend_bundles(id), "
            # a bundle can be in more groups
            "UNIQUE (group_id, spend_bundle_id));"
        )

        # Indexing for quick lookups
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_coin_spend_bundle_id ON coin_spends(spend_bundle_id); "
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_coin_id ON coin_spends(coin_id); "
        )

        _copy_old_spend_bundle_tables(cursor, renamed)
        conn.commit()

    except sqlite3.Error as e:
        conn.rollback()
        print(f"Error creating the spend bundle database: {e}")
        logging(debug_logger, "DEBUG", f"WDB error while creating the spend bundle database: {e}")
        logging(debug_logger, "DEBUG", "WDB error _________________________________________")
        logging(debug_logger, "DEBUG", "WDB error _________________________________________")
        logging(debug_logger, "DEBUG", "WDB error _________________________________________")


def insert_puzzle(contable_namen, puzzle_hash, puzzle, size):
    cursor = conn.cursor()

    cursor.execute(
        "INSERT OR IGNORE INTO puzzles ("
        "puzzle_hash, clvm, size) VALUES (?, ?, ?);",
        (puzzle_hash,
         puzzle,
         size)
    )


def _bundle_hash_bytes(spend_bundle_hash) -> bytes:
    """Bundle hashes come as bytes or as hex, with or without 0x."""
    if isinstance(spend_bundle_hash, str):
        return bytes.fromhex(spend_bundle_hash.removeprefix('0x'))
    return bytes(spend_bundle_hash)


def add_spend_bundles_to_watch_later(conn, spend_bundle_hash) -> bool:
    """Add a bundle already saved with insert_spend_bundle to the watch later group.
    False if the bundle is not in the DB."""
    cursor = conn.cursor()
    group_name = "watch later"

    spend_bundle_hash = _bundle_hash_bytes(spend_bundle_hash)

    # retrive the id of the sb
    cursor.execute(
        "SELECT id FROM spend_bundles WHERE spend_bundle_hash = ?;",
        (spend_bundle_hash,)
    )
    item = cursor.fetchone()
    if item is None:
        return False
    spend_bundle_id = item[0]

    # add the group name or retrive the id
    cursor.execute(
        "INSERT OR IGNORE INTO spend_bundle_group_names (name) VALUES (?);",
        (group_name, )
    )

    if cursor.rowcount == 0:
        cursor.execute(
            "SELECT id FROM spend_bundle_group_names WHERE name = ?",
            (group_name,))
        group_id = cursor.fetchone()[0]
    else:
        group_id = cursor.lastrowid

    # add the sb to the group
    cursor.execute(
        "INSERT OR IGNORE INTO spend_bundle_groups (group_id, spend_bundle_id) VALUES (?,?);",
        (group_id, spend_bundle_id)
    )

    conn.commit()
    return True


def remove_spend_bundle_from_group(spend_bundle_hash):
    pass


def insert_spend_bundle(conn, spend_bundle: SpendBundle):

    cursor = conn.cursor()

    # spend_bundle
    spend_bundle_hash = spend_bundle.get_hash()
    timestamp = time.time()
    block_height = None  # added when executer
    status = 'pending'
    aggregated_signature = spend_bundle.aggregated_signature.to_bytes()
    raw_spend_bundle = spend_bundle.to_bytes()

    spend_bundle_id = None  # i should get the id from the execute of the bundle
    ### cursor.execute() spend bundle

    # puzzles and coin_spend
    puzzles = {}
    coin_spends: list[CoinSpend] = spend_bundle.coin_spends

    try:
        cursor.execute(
            "INSERT OR IGNORE INTO spend_bundles("
            "spend_bundle_hash, timestamp, block_height, status, "
            "aggregated_signature, raw_spend_bundle) "
            "VALUES (?, ?, ?, ?, ?, ?);",
            (spend_bundle_hash, timestamp, block_height, status, aggregated_signature, raw_spend_bundle)
        )

        if cursor.rowcount == 0:
            return None  # spend bundle already added

        spend_bundle_id = cursor.lastrowid

    except Exception as e:
        logging(debug_logger, "DEBUG", f"WDB error while inserting the SP in the database: {e}")
        return None


    for spend in coin_spends:
        puzzle_reveal = spend.puzzle_reveal
        puzzle_hash = puzzle_reveal.get_tree_hash()
        if puzzle_hash not in puzzles:
            puzzles[puzzle_hash] = puzzle_reveal

            ### TODO: here we need to decompose the puzzle in all the sub puzzle, and save the input on the coin_spend table, and all the puzzle in the puzzles table

            try:
                cursor.execute(
                    "INSERT OR IGNORE INTO puzzles("
                    "puzzle_hash, clvm, size) "
                    "VALUES (?, ?, ?);",
                    (puzzle_hash, puzzle_reveal.to_bytes(), 0)  # for now the size is 0
                )
            except Exception as e:
                logging(debug_logger, "DEBUG", f"WDB error while inserting the "
                        f" a new puzzle in the database: {e}")

        coin = spend.coin
        coin_id = coin.name()  # get_hash() is not the coin_it, but the hash of the data
        # coin_id manual
        #coin_id_manual = std_hash(coin.parent_coin_info +
        #    coin.puzzle_hash +
        #    int_to_bytes(coin.amount)).hex()
        coin_amount = coin.amount
        coin_parent = coin.parent_coin_info
        coin_puzzle_reveal_hash = puzzle_hash
        coin_solution = spend.solution

        try:
            cursor.execute(
                "INSERT OR IGNORE INTO coin_spends("
                "spend_bundle_id, coin_id, parent_id, amount, puzzle_reveal_hash, solution) "
                "VALUES (?, ?, ?, ?, ?, ?);",
                (spend_bundle_id, coin_id, coin_parent, coin_amount,
                 coin_puzzle_reveal_hash, coin_solution.to_bytes())
            )

        except Exception as e:
            logging(debug_logger, "DEBUG", f"WDB error while inserting the SP in the database: {e}")

        # check if the puzzle hash of the coin is the same of the tree hash,
        # if yes the puzzle is the one with curried in pk
        # try to do with the first uncurried one

        # saving the puzzles it could be a lit bit more involved. The puzzle shoud be unbcurried
        # and for each uncurried levele the parameter saved

        # 2 uncurry levels
        # first puzzle - n. parameter of which one is the second puzzle
        # second puzzle - n. parameter

        # per adesso salviamo solo il puzzle principale semplice


        # Program.get_hash  # it is calculate on the blob data, faster and less costly
        # Program.get_tree_hash  # the one used in the puzzles

    conn.commit()
    # aggregated_signature are not needed to be directily accessible...

    return spend_bundle_id


def load_spend_bundles(conn, group_name=None):
    """General loader, it loads all the entries"""

    cursor = conn.cursor()

    if group_name is not None:

        cursor.execute(
            "SELECT id FROM spend_bundle_group_names WHERE name = ?;",
            (group_name,)
        )

        fetch = cursor.fetchone()
        if fetch is None:
            return None

        group_id = fetch[0]

        cursor. execute(
            " SELECT s.* FROM "
            " spend_bundles s JOIN spend_bundle_groups g "
            " ON s.id = g.spend_bundle_id WHERE g.group_id = ? ",
            (group_id,))

    else:
        cursor.execute(
            "SELECT * FROM spend_bundles;"
        )
    raw_spend_bundles = cursor.fetchall()

    bundle_states = []
    for rsp in raw_spend_bundles:
        spend_bundle_state: BundleState = BundleState(rsp)
        bundle_states.append(spend_bundle_state)

    return bundle_states


def load_spend_bundle(conn, bundle_hash, group_name=None):
    """General loader, it loads all the entries"""

    cursor = conn.cursor()

    if group_name is not None:

        cursor.execute(
            "SELECT id FROM spend_bundle_group_names WHERE name = ?;",
            (group_name,)
        )
        fetch = cursor.fetchone()
        if fetch is None:
            return None

        group_id = fetch[0]


        cursor. execute(
            " SELECT s.* FROM "
            " spend_bundles s JOIN spend_bundle_groups g "
            " ON s.id = g.spend_bundle_id WHERE g.group_id = ? AND s.spend_bundle_hash = ? ",
            (group_id, _bundle_hash_bytes(bundle_hash))
        )

    else:
        cursor.execute(
            "SELECT s.* FROM spend_bundles s WHERE spend_bundle_hash = ? ",
            (_bundle_hash_bytes(bundle_hash),)
        )

    raw_spend_bundles = cursor.fetchall()
    if len(raw_spend_bundles) == 0:
        return None

    bundle_states = []
    for rsp in raw_spend_bundles:
        spend_bundle_state: BundleState = BundleState(rsp)
        bundle_states.append(spend_bundle_state)

    return bundle_states


def refresh_bundle_status(conn, spend_bundle_id):
    """Check a pending bundle's coins on chain and update its status:
    - confirmed: all its coins are spent with its solutions, block_height is where;
    - conflict: a coin was spent with another solution (another bundle won);
    - pending: some coins are not spent yet (or the node does not know them).
    Slow (2 RPC calls per coin): run it in a thread. Returns (status, block_height),
    or None when the node does not answer."""
    cursor = conn.cursor()
    cursor.execute("SELECT coin_id, solution FROM coin_spends WHERE spend_bundle_id = ?;",
                   (spend_bundle_id,))
    spends = cursor.fetchall()
    if len(spends) == 0:
        return None

    status, block_height = 'confirmed', None
    for coin_id, solution in spends:
        try:
            record = RPC.call_rpc_node('get_coin_record_by_name', name='0x' + coin_id.hex())
        except Exception:
            record = None  # not on chain yet (e.g. a coin created in the bundle itself)
        if not record or not record.get('spent'):
            status, block_height = 'pending', None
            break
        height = record['spent_block_index']
        try:
            out = RPC.call_rpc_node('get_puzzle_and_solution', coin_id=coin_id.hex(), height=height)
        except Exception:
            return None
        chain_solution = PyProgram.fromhex(out['solution'].removeprefix('0x'))
        if chain_solution.get_tree_hash() != PyProgram.from_bytes(solution).get_tree_hash():
            status, block_height = 'conflict', height
            break
        block_height = height if block_height is None else max(block_height, height)

    cursor.execute("UPDATE spend_bundles SET status = ?, block_height = ? WHERE id = ?;",
                   (status, block_height, spend_bundle_id))
    conn.commit()
    return status, block_height


############### mempool structure ######################

# mempool items
## why not to use the class Spendbundle()?
class MempoolItem:

    def __init__(self, spend_bundle_hash=None, rpc_json_item=None, raw_json_spendbundle=None, timestamp=None):
        if rpc_json_item is not None:
            self.spend_bundle_hash = spend_bundle_hash
            self.cost = rpc_json_item['cost']
            self.fee = rpc_json_item['fee']

            self.addition_amount = rpc_json_item['npc_result']['conds']['addition_amount']
            self.removal_amount = rpc_json_item['npc_result']['conds']['removal_amount']
            self.additions = rpc_json_item['additions']
            self.removals = rpc_json_item['removals']
            self.spend_bundle = rpc_json_item['spend_bundle']
            self.added_coins_count = len(self.additions)
            self.removed_coins_count = len(self.removals)
            self.fee_per_cost = self.fee / self.cost

            self.added_at = time.time()
            self.removed_at = None
            self.coin_types = None
            self.single_coins_with_all_type = None  # list of internal puzzle
            # form to store coin type (dic with tuple)
        elif raw_json_spendbundle is not None and timestamp is not None:

            sp: SpendBundle = SpendBundle.from_json_dict(raw_json_spendbundle)


            #def validate_clvm_and_signature(
            #    new_spend: SpendBundle,
            #    max_cost: int,
            #    constants: ConsensusConstants,
            #    peak_height: int)
            #    -> tuple[SpendBundleConditions, list[tuple[bytes32, GTElement]], float]: ...

            sp_conds: SpendBundleConditions = validate_clvm_and_signature(
                sp,
                1000000000,  # max cost
                DEFAULT_CONSTANTS,  # ConsensusConstants
                1000000000)  # peak_height
            sp_conds = sp_conds[0]  # keep only the conditions

            # sp_conds.condition_cost
            # sp_conds.execution_cost
            # sp_conds.reserve_fee)

            self.spend_bundle_hash = sp.name()

            self.cost = sp_conds.cost
            self.fee = sp_conds.removal_amount - sp_conds.addition_amount

            self.addition_amount = sp_conds.addition_amount
            self.removal_amount = sp_conds.removal_amount

            # spends
            spends = sp_conds.spends

            removals_dict: dict[bytes32, Coin] = {}
            additions_dict: dict[bytes32, Coin] = {}
            addition_amount: int = 0
            removal_amount: int = 0

            for spend in spends:
                coin_id = bytes32(spend.coin_id)
                removals_dict[coin_id] = Coin(spend.parent_id, spend.puzzle_hash, spend.coin_amount)
                removal_amount += spend.coin_amount
                spend_additions = []
                for puzzle_hash, amount, _ in spend.create_coin:
                    child_coin = Coin(coin_id, puzzle_hash, uint64(amount))
                    spend_additions.append(child_coin)
                    additions_dict[child_coin.name()] = child_coin
                    addition_amount += child_coin.amount

            # convert to dict for compatibility
            def coin_to_dict(coin):
                return {'parent_coin_info': f'0x{coin.parent_coin_info}', 'puzzle_hash': f'0x{coin.puzzle_hash}', 'amount': coin.amount}

            self.additions = [coin_to_dict(c) for c in additions_dict.values()]
            self.removals = [coin_to_dict(c) for c in removals_dict.values()]
            self.spend_bundle = raw_json_spendbundle
            self.added_coins_count = len(additions_dict)
            self.removed_coins_count = len(removals_dict)
            self.fee_per_cost = self.fee / self.cost

            self.added_at = None
            self.removed_at = None
            self.coin_types = None
            self.single_coins_with_all_type = None  # list of internal puzzle
            # form to store coin type (dic with tuple)
        else:
            raise "an spend_bundle_hash + rpc output or a json spendbule + timestamp is needed"


    def __str__(self):
        str = (f"spend_bundle_hash: {self.spend_bundle_hash} | cost: {self.cost} | fee: {self.fee:_} mojo or {self.fee / 1_000_000_000_000} | "
            f"amount added/removed: {self.addition_amount} / {self.removal_amount} | "
            f"added/removed coins: {self.added_coins_count} / {self.removed_coins_count}"
               )
        return str


class MempoolBlock:

    def __init__(self):
        self.transactions = []
        self.total_cost = 0

    def add_item(self, item: MempoolItem):
        self.transactions.append(item)
        self.total_cost += item.cost

    def __str__(self):
        return f"n. of transaction {len(self.transactions)}, total cost: {self.total_cost}"

class BundleState:

    def __init__(self, raw_data):
        self.id = raw_data[0]
        self.spend_bundle_hash = raw_data[1].hex()
        self.timestamp = raw_data[2]
        self.block_height = raw_data[3]
        self.status = raw_data[4]
        self.aggregated_signature = raw_data[5]
        self.raw_spend_bundle = raw_data[6]
        self.replaced_by = raw_data[7] if len(raw_data) > 7 else None

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

    def __init__(self, raw_data, full_init: bool = True):

        # raw data shape:
        ## 0 - header_hash
        ## 1 - prev_hash
        ## 2 - height
        ## 3 - sub_epoch_summary
        ## 4 - is_fully_compactified
        ## 5 - in_main_chain
        ## 6 - block
        ## 7 - block_record

        self.header_hash = "0x" + bytes32(raw_data[0]).hex()
        self.height = raw_data[2]
        self.sub_epoch_summary = raw_data[3]

        if not full_init:
            return None

        block = reconstruct_block_from_bytes(raw_data[6])
        block_record = reconstruct_block_record_from_bytes(raw_data[7])

        # blockrecords:
        self.fees = block_record['fees']
        # self.header_hash = block_record['header_hash']
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

        ## --- reward chain block ---
        rcb = block["reward_chain_block"]

        self.rcb_pos_ss_cc_challenge_hash = rcb["pos_ss_cc_challenge_hash"]
        self.rcb_challenge_chain_sp_signature = rcb["challenge_chain_sp_signature"]
        self.rcb_reward_chain_sp_signature = rcb["reward_chain_sp_signature"]
        self.rcb_height = rcb['height']

        self.n_iteration_challenge_chain = block['reward_chain_block']['challenge_chain_ip_vdf']['number_of_iterations']
        self.is_transaction_block = block['reward_chain_block']['is_transaction_block']
        self.plot_public_key = block['reward_chain_block']['proof_of_space']['plot_public_key']
        self.pool_public_key = block['reward_chain_block']['proof_of_space']['pool_public_key']
        self.proof_of_space_proof = block['reward_chain_block']['proof_of_space']['proof']
        self.proof_of_space_size = block['reward_chain_block']['proof_of_space']['size']
        self.signage_point_index_b = block['reward_chain_block']['signage_point_index']  # redundant
        self.total_iters_b = block['reward_chain_block']['total_iters']  # redundant
        self.weight_b = block['reward_chain_block']['weight']  # redundant
        self.transactions_generator = block['transactions_generator']  # chialisp
        self.transactions_generator_ref_list = block['transactions_generator_ref_list']  # ref to other block if needed
        if block['transactions_info'] is not None:
            self.aggregate_signature = block['transactions_info']['aggregated_signature']
            self.cost = block['transactions_info']['cost']  # total cost
            self.fees_b = block['transactions_info']['fees']
        else:
            self.aggregate_signature = None
            self.cost = None
            self.fees_b = None



        ## --- foliage ---
        #foliage = block["foliage"]

        #self.prev_block_hash = foliage["prev_block_hash"]
        #self.reward_block_hash = foliage["reward_block_hash"]
        #self.foliage_block_data_signature = foliage["foliage_block_data_signature"]
        #self.foliage_tx_block_hash = foliage["foliage_transaction_block_hash"]
        #self.foliage_tx_block_signature = foliage["foliage_transaction_block_signature"]

        ## --- foliage block data ---
        #fbd = foliage["foliage_block_data"]

        #self.extension_data = fbd["extension_data"]
        #self.unfinished_reward_block_hash = fbd["unfinished_reward_block_hash"]

        ## --- transaction block (ONLY if present) ---
        #ftb = block["foliage_transaction_block"]
        #if ftb is not None:
        #    self.additions_merkle_root = ftb["additions_root"]
        #    self.removals_merkle_root = ftb["removals_root"]
        #    self.transactions_merkle_root = ftb["transactions_root"]
        #    self.timestamp_b = ftb["timestamp"]
        #else:
        #    self.additions_merkle_root = None
        #    self.removals_merkle_root = None
        #    self.transactions_merkle_root = None
        #    self.timestamp_b = None

        ## --- reward chain block ---
        #rcb = block["reward_chain_block"]

        #self.pos_ss_cc_challenge_hash = rcb["pos_ss_cc_challenge_hash"]
        #self.challenge_chain_sp_signature = rcb["challenge_chain_sp_signature"]
        #self.reward_chain_sp_signature = rcb["reward_chain_sp_signature"]

        ## challenge chain IP VDF
        #cc_ip_vdf = rcb["challenge_chain_ip_vdf"]
        #self.cc_ip_iters = cc_ip_vdf["number_of_iterations"]
        #self.cc_ip_vdf_output = cc_ip_vdf["output"]["data"]

        ## reward chain IP VDF
        #rc_ip_vdf = rcb["reward_chain_ip_vdf"]
        #self.rc_ip_iters = rc_ip_vdf["number_of_iterations"]
        #self.rc_ip_vdf_output = rc_ip_vdf["output"]["data"]

        ## --- proof of space ---
        #pos = rcb["proof_of_space"]

        #self.pos_challenge = pos["challenge"]
        #self.pool_contract_puzzle_hash = pos["pool_contract_puzzle_hash"]

        ## --- proofs ---
        #self.challenge_chain_ip_proof = block["challenge_chain_ip_proof"]
        #self.challenge_chain_sp_proof = block["challenge_chain_sp_proof"]
        #self.infused_challenge_chain_ip_proof = block["infused_challenge_chain_ip_proof"]
        #self.reward_chain_ip_proof = block["reward_chain_ip_proof"]
        #self.reward_chain_sp_proof = block["reward_chain_sp_proof"]
        #
        ## --- misc ---
        #self.finished_sub_slots = block["finished_sub_slots"]





    def __str__(self):
        return f"Block height: {self.height:,}; sp: {self.signage_point_index}; ts: {self.timestamp} and {self.timestamp_b} ; header: {self.header_hash}"

    def operational_error(self):
        op_error = copy.deepcopy(self)
        op_error.header_hash = '0x0000000000000000000942b19f16b83a316acfa31e067c0b766c4dda034dc37f'
        op_error.height = 675317
        op_error.timestamp = 1616132171
        op_error.preimage = 'bitcoin_hash:0000000000000000000942b19f16b83a316acfa31e067c0b766c4dda034dc37f,bram_message:"Operational error causes Fed payment system to crash" We stand on the shoulders of giants, now let\'s get farming!'
        op_error.genesis_challange = '0xccd5bb71183532bff220ba46c268991a3ff07eb358e8255a65c30a2dce0e5fbb'
        return op_error

    def b_block_to_2d_list(self):
        keys = []
        values = []

        keys.append('bitcoin_hash')
        values.append(self.header_hash)
        keys.append('height')
        values.append(self.height)
        keys.append('timestamp')
        values.append(self.timestamp)
        keys.append('date')
        values.append(timestamp_to_date(self.timestamp))
        keys.append('preimage')
        values.append(self.preimage)
        keys.append('genesis challange')
        values.append(self.genesis_challange)

        return [keys, values]

    def block_state_to_2d_list(self):
        keys = []
        values = []

        keys.append('header_hash')
        values.append(self.header_hash)
        keys.append('height')
        values.append(self.height)
        keys.append('sub_epoch_summary')
        values.append(self.sub_epoch_summary)

        # blockrecords:
        keys.append('fees')
        values.append(self.fees)
        keys.append('farmer_puzzle_hash')
        values.append(self.farmer_puzzle_hash)
        keys.append('pool_puzzle_hash')
        values.append(self.pool_puzzle_hash)
        keys.append('deficit')
        values.append(self.deficit)
        keys.append('overflow')
        values.append(self.overflow)
        keys.append('prev_transaction_block_height')
        values.append(self.prev_transaction_block_height)
        keys.append('reward_claims_incorporated')
        values.append(self.reward_claims_incorporated)
        keys.append('signage_point_index')
        values.append(self.signage_point_index)
        keys.append('required_iters')
        values.append(self.required_iters)
        keys.append('sub_slot_iters')
        values.append(self.sub_slot_iters)
        keys.append('total_iters')
        values.append(self.total_iters)
        keys.append('weight')
        values.append(self.weight)
        keys.append('timestamp')
        values.append(self.timestamp)

        keys.append('date')
        if self.timestamp:
            values.append(timestamp_to_date(self.timestamp))
        else:
            values.append(None)

        # block:
        keys.append('farmer_puzzle_hash_b')
        values.append(self.farmer_puzzle_hash_b)
        keys.append('pool_puzzle_hash_b')
        values.append(self.pool_puzzle_hash_b)

        keys.append('additions_merkle_root')
        values.append(self.additions_merkle_root)
        keys.append('timestamp_b')
        values.append(self.timestamp_b)
        keys.append('n_iteration_challenge_chain')
        values.append(self.n_iteration_challenge_chain)
        keys.append('reward chain block (rcb)')
        values.append('')
        keys.append('rcb / height')
        values.append(self.rcb_height)
        keys.append('rcb / pos_ss_cc_challenge_hash')
        values.append(self.rcb_pos_ss_cc_challenge_hash)
        keys.append('rcb / challenge_chain_sp_signature')
        values.append(self.rcb_challenge_chain_sp_signature)
        keys.append('rcb / reward_chain_sp_signature')
        values.append(self.rcb_reward_chain_sp_signature)
        keys.append('is_transaction_block')
        values.append(self.is_transaction_block)
        keys.append('plot_public_key')
        values.append(self.plot_public_key)
        keys.append('pool_public_key')
        values.append(self.pool_public_key)
        keys.append('proof_of_space_proof')
        values.append(self.proof_of_space_proof)
        keys.append('proof_of_space_size')
        values.append(self.proof_of_space_size)
        keys.append('signage_point_index_b')
        values.append(self.signage_point_index_b)
        keys.append('total_iters_b')
        values.append(self.total_iters_b)
        keys.append('weight_b')
        values.append(self.weight_b)
        keys.append('transactions_generator')
        values.append(self.transactions_generator)
        keys.append('transactions_generator_ref_list')
        values.append(self.transactions_generator_ref_list)
        keys.append('aggregate_signature')
        values.append(self.aggregate_signature)
        keys.append('cost')
        values.append(self.cost)
        keys.append('fees_b')
        values.append(self.fees_b)

        return [keys, values]


# VDF chains: blocks on the three VDF chains, from the block records of the node DB
class VdfBlockPoint:
    """A block on the VDF chains. Only the block record is decoded (no full block),
    so many blocks can be loaded fast. Iterations are total iterations (absolute)."""

    def __init__(self, height: int, raw_block_record: bytes):
        br = BlockRecord.from_bytes(raw_block_record)
        self.height = height
        self.is_transaction_block = br.is_transaction_block
        self.signage_point_index = br.signage_point_index
        self.deficit = br.deficit
        self.overflow = br.overflow
        self.is_challenge_block = br.is_challenge_block(DEFAULT_CONSTANTS)  # the infused challenge chain starts here
        self.first_in_sub_slot = br.first_in_sub_slot
        self.sub_slot_iters = br.sub_slot_iters
        self.required_iters = br.required_iters
        self.ip_iters = br.ip_iters(DEFAULT_CONSTANTS)  # infusion point, in its sub-slot
        self.sp_iters = br.sp_iters(DEFAULT_CONSTANTS)  # signage point, in its sub-slot
        self.ip_total_iters = br.total_iters
        self.sp_total_iters = br.sp_total_iters(DEFAULT_CONSTANTS)
        self.ip_sub_slot_start = br.ip_sub_slot_total_iters(DEFAULT_CONSTANTS)
        self.sp_sub_slot_start = br.sp_sub_slot_total_iters(DEFAULT_CONSTANTS)
        self.timestamp = br.timestamp  # only transaction blocks have it, None for the others


class VdfSubSlot:
    """A sub-slot on the VDF chains, with the blocks infused in it."""

    def __init__(self, start: int, sub_slot_iters: int):
        self.start = start
        self.sub_slot_iters = sub_slot_iters
        self.end = start + sub_slot_iters
        self.blocks: list[VdfBlockPoint] = []
        self.deficit_start = None
        self.deficit_end = None
        self.icc_start = None  # where the infused challenge chain starts, None if there is none
        self.icc_into_cc = False  # the infused challenge chain goes into the challenge chain at the end


class VdfClock:
    """Time of the VDF iterations, from the timestamps of the transaction blocks. A timestamp
    is set by the farmer when it makes the block, after the signage point, and it is off by a
    few seconds, so the times come from a line fitted on many blocks."""

    def __init__(self, speed: float, iters0: float, time0: float):
        self.speed = speed  # iterations per second
        self.iters0 = iters0
        self.time0 = time0

    def time_at(self, iters) -> float:
        return self.time0 + (iters - self.iters0) / self.speed

    @staticmethod
    def fit(points, start: int, end: int, min_blocks: int = 6):
        """Fit the transaction blocks of points with the signage point between start and end
        (total iterations). Return a VdfClock, or None if there are too few blocks."""
        xs, ys = [], []
        for p in points:
            if p.timestamp is not None and start <= p.sp_total_iters <= end:
                xs.append(p.sp_total_iters)
                ys.append(p.timestamp)
        if len(xs) < min_blocks:
            return None
        mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
        sxx = sum((x - mx) ** 2 for x in xs)
        sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
        if sxy <= 0:
            return None
        return VdfClock(sxx / sxy, mx, my)


def load_vdf_block_points(conn, start_height: int, end_height: int) -> dict:
    """Load the blocks of the main chain from start_height to end_height (included)"""
    cur = conn.cursor()
    cur.execute("SELECT height, block_record FROM full_blocks "
                "WHERE in_main_chain = 1 AND height >= ? AND height <= ?",
                (start_height, end_height))
    return {height: VdfBlockPoint(height, raw) for height, raw in cur.fetchall()}


def find_previous_vdf_block(conn, before_height: int, kind: str, max_blocks: int = 50_000, chunk: int = 1000):
    """The newest block under before_height that is:
    - kind 'overflow': an overflow block (infused in the sub-slot after the one of its signage point);
    - kind 'long_slot': the first block of a sub-slot when the slot goes on from the previous
      sub-slot (the infused challenge chain started and the deficit did not reach 0, as in
      build_vdf_sub_slots): it carries the end of that sub-slot.
    Look at max_blocks blocks at most. Return its height or None."""
    cur = conn.cursor()
    newer = None  # the block after the one checked, for long_slot
    hi = before_height - 1
    lowest = max(0, before_height - max_blocks)
    while hi >= lowest:
        lo = max(lowest, hi - chunk + 1)
        cur.execute("SELECT height, block_record FROM full_blocks "
                    "WHERE in_main_chain = 1 AND height >= ? AND height <= ? ORDER BY height DESC", (lo, hi))
        for height, raw in cur.fetchall():
            point = VdfBlockPoint(height, raw)
            if kind == 'overflow' and point.overflow:
                return height
            if (kind == 'long_slot' and newer is not None and newer.ip_sub_slot_start > point.ip_sub_slot_start
                    and 0 < point.deficit < DEFAULT_CONSTANTS.MIN_BLOCKS_PER_CHALLENGE_BLOCK):
                return newer.height
            newer = point
        hi = lo - 1
    return None


def build_vdf_sub_slots(points: list[VdfBlockPoint]) -> list[VdfSubSlot]:
    """Group the blocks by the sub-slot of their infusion point, add the empty sub-slots
    between them, and follow the deficit and the infused challenge chain.
    The points must be consecutive blocks, sorted by height. The first sub-slot can
    miss its first blocks, so its deficit and infused challenge chain can be wrong."""
    sub_slots: list[VdfSubSlot] = []
    for point in points:
        if not sub_slots or point.ip_sub_slot_start >= sub_slots[-1].end:
            # empty sub-slots before the new one
            while sub_slots and point.ip_sub_slot_start >= sub_slots[-1].end + sub_slots[-1].sub_slot_iters:
                sub_slots.append(VdfSubSlot(sub_slots[-1].end, sub_slots[-1].sub_slot_iters))
            sub_slots.append(VdfSubSlot(point.ip_sub_slot_start, point.sub_slot_iters))
        sub_slots[-1].blocks.append(point)

    prev = None
    for sub_slot in sub_slots:
        # the infused challenge chain goes on from the previous sub-slot if the deficit did not reach 0
        icc_carried = prev is not None and prev.icc_start is not None and prev.deficit_end != 0
        if icc_carried:
            sub_slot.icc_start = sub_slot.start
            sub_slot.deficit_start = prev.deficit_end
        else:
            sub_slot.deficit_start = DEFAULT_CONSTANTS.MIN_BLOCKS_PER_CHALLENGE_BLOCK
        for block in sub_slot.blocks:
            if block.is_challenge_block and sub_slot.icc_start is None:
                sub_slot.icc_start = block.ip_total_iters
        if sub_slot.blocks:
            sub_slot.deficit_end = sub_slot.blocks[-1].deficit
            if prev is None and sub_slot.icc_start is None and sub_slot.blocks[0].deficit < DEFAULT_CONSTANTS.MIN_BLOCKS_PER_CHALLENGE_BLOCK - 1:
                # first sub-slot loaded: the challenge block is before the first block loaded
                sub_slot.icc_start = sub_slot.start
        else:
            sub_slot.deficit_end = sub_slot.deficit_start
        sub_slot.icc_into_cc = sub_slot.icc_start is not None and sub_slot.deficit_end == 0
        prev = sub_slot

    return sub_slots


def load_block_vdfs(conn, height: int) -> dict:
    """The VDFs of a block, from its full block: for each VDF the total iterations where
    it ends and its number of iterations (it starts at end - iterations).
    'end_of_sub_slots' are the sub-slots finished before the block (their end VDFs)."""
    cur = conn.cursor()
    cur.execute("SELECT block, block_record FROM full_blocks WHERE in_main_chain = 1 AND height = ?", (height,))
    row = cur.fetchone()
    if row is None:
        return None
    block = FullBlock.from_bytes(zstd.decompress(row[0]))
    br = BlockRecord.from_bytes(row[1])
    rcb = block.reward_chain_block
    sp_total_iters = br.sp_total_iters(DEFAULT_CONSTANTS)
    ip_total_iters = br.total_iters

    def vdf(info, end):
        if info is None:
            return None
        return {'end': end, 'iterations': info.number_of_iterations}

    vdfs = {
        'height': height,
        'cc_sp': vdf(rcb.challenge_chain_sp_vdf, sp_total_iters),
        'rc_sp': vdf(rcb.reward_chain_sp_vdf, sp_total_iters),
        'cc_ip': vdf(rcb.challenge_chain_ip_vdf, ip_total_iters),
        'rc_ip': vdf(rcb.reward_chain_ip_vdf, ip_total_iters),
        'icc_ip': vdf(rcb.infused_challenge_chain_ip_vdf, ip_total_iters),
        'end_of_sub_slots': [],
    }

    # the finished sub-slots end where the infusion sub-slot of the block starts, one after the other
    sub_slot_end = br.ip_sub_slot_total_iters(DEFAULT_CONSTANTS) - br.sub_slot_iters * (len(block.finished_sub_slots) - 1)
    for sub_slot in block.finished_sub_slots:
        cc = sub_slot.challenge_chain
        icc = sub_slot.infused_challenge_chain
        vdfs['end_of_sub_slots'].append({
            'end': sub_slot_end,
            'cc': vdf(cc.challenge_chain_end_of_slot_vdf, sub_slot_end),
            'icc': vdf(icc.infused_challenge_chain_end_of_slot_vdf, sub_slot_end) if icc is not None else None,
            'rc': vdf(sub_slot.reward_chain.end_of_slot_vdf, sub_slot_end),
            'icc_into_cc': cc.infused_challenge_chain_sub_slot_hash is not None,
            'deficit': sub_slot.reward_chain.deficit,
        })
        sub_slot_end += br.sub_slot_iters
    return vdfs


class FetchMaker:
    # TODO: merge first_last_count with the main fetcher...
    # TODO: remove filters from fetch

    @staticmethod
    def get_coin_record_by_name(db_cursor, coin_name):
        """Fetch a coin_record (8 columns) from the blockchain DB by coin_name.
           Returns None if not found.
           Columns: (coin_name, confirmed_index, spent_index, coinbase, puzzle_hash,
                     coin_parent, amount, timestamp)"""
        db_cursor.execute(
            "SELECT coin_name, confirmed_index, spent_index, coinbase, puzzle_hash, "
            "coin_parent, amount, timestamp FROM coin_record WHERE coin_name = ?",
            (coin_name,),
        )
        return db_cursor.fetchone()

    @staticmethod
    def get_coin_hint(db_cursor, coin_name):
        """Fetch the hint for a coin from the hints table.
           Returns the hint bytes32 or None."""
        db_cursor.execute(
            "SELECT hint FROM hints WHERE coin_id = ?",
            (coin_name,),
        )
        row = db_cursor.fetchone()
        return bytes32(row[0]) if row else None

    @staticmethod
    def get_cached_coin_record(cache_cursor, coin_name):
        """Fetch a cached coin_record (15 columns) from the cached_coin_record table by coin_name.
           Returns None if not found.
           Columns: (coin_name, confirmed_index, spent_index, coinbase, puzzle_hash,
                     coin_parent, amount, timestamp, record_type, parent_puzzle_hash,
                     child_count, coin_type, coin_type_metadata, full_memo, hint)"""
        cache_cursor.execute(
            "SELECT coin_name, confirmed_index, spent_index, coinbase, puzzle_hash, coin_parent, "
            "amount, timestamp, record_type, parent_puzzle_hash, child_count, coin_type, "
            "coin_type_metadata, full_memo, hint "
            "FROM cached_coin_record WHERE coin_name = ?",
            (coin_name,),
        )
        return cache_cursor.fetchone()

    @staticmethod
    def cache_coin_record(db_cursor, cache_cursor, coin_record_row, puzzle_hash):
        """Process a coin_record row (8 columns from coin_record table)
           and cache it along with its children.
           Looks up parent_puzzle_hash, retrieves child coins, creates PHANTOM/CHILD
           records, and caches the main coin as NORMAL.
        coin_record_row: (coin_name, confirmed_index, spent_index, coinbase, puzzle_hash,
              coin_parent, amount, timestamp)
        """
        coin_parent = coin_record_row[5]
        coinbase = coin_record_row[3]

        if coinbase:
            parent_puzzle_hash = None
        else:
            db_cursor.execute(
                "SELECT puzzle_hash FROM coin_record WHERE coin_name=? ",
                (coin_parent,),
            )
            items = db_cursor.fetchall()
            if len(items) > 1:
                parent_puzzle_hash = items[0][0]
                raise "one, and only one parent..."
            elif len(items) == 1:
                parent_puzzle_hash = items[0][0]
            else:
                raise "zero... no way! terminate everything"

        coin_name = coin_record_row[0]
        spent_index = coin_record_row[2]
        amount = coin_record_row[6]
        child_count = 0
        if spent_index > 0:
            db_cursor.execute(
                "SELECT coin_name, confirmed_index, spent_index, coinbase, puzzle_hash, "
                "coin_parent, amount, timestamp FROM coin_record WHERE coin_parent=? ",
                (coin_name,),
            )
            items = db_cursor.fetchall()
            child_count = len(items)

            if child_count == 0:
                sub_args = []
                sub_args.append(UTILS.calc_coin_id(coin_name, puzzle_hash, amount))
                sub_args.append(spent_index)
                sub_args.append(spent_index)
                sub_args.append(0)
                sub_args.append(bytes(32))
                sub_args.append(coin_name)
                sub_args.append(amount)

                db_cursor.execute(
                    "SELECT block_record FROM full_blocks WHERE height = ?",
                    (spent_index,)
                )
                items = db_cursor.fetchall()
                block_record = reconstruct_block_record_from_bytes(items[0][0])
                sub_args.append(block_record['timestamp'])

                sub_args.append(TYPES.CacheCoinRecordType.PHANTOM_SPENT)
                sub_args.append(puzzle_hash)

                cache_cursor.execute(
                    "INSERT OR REPLACE INTO cached_coin_record (coin_name, confirmed_index, spent_index, "
                    "coinbase, puzzle_hash, coin_parent, amount, timestamp, record_type, parent_puzzle_hash) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?) ",
                    sub_args
                )

            else:
                for sub_args in items:
                    sub_args = list(sub_args)
                    sub_args.append(TYPES.CacheCoinRecordType.CHILD)
                    sub_args.append(puzzle_hash)

                    cache_cursor.execute(
                        "INSERT INTO cached_coin_record (coin_name, confirmed_index, spent_index, "
                        "coinbase, puzzle_hash, coin_parent, amount, timestamp, record_type, parent_puzzle_hash) "
                        "VALUES (?,?,?,?,?,?,?,?,?,?) "

                        # the coin data never changes, only the spent state does. A child that is
                        # also a coin of a followed address stays NORMAL (NORMAL < CHILD)
                        "ON CONFLICT(coin_name) DO UPDATE SET "
                        "spent_index = excluded.spent_index, "
                        "record_type = MIN(cached_coin_record.record_type, excluded.record_type) ",
                        sub_args
                    )

        # --- cache main coin record ---
        args = list(coin_record_row)
        args.append(TYPES.CacheCoinRecordType.NORMAL)
        args.append(parent_puzzle_hash)
        args.append(child_count)
        args.append(None)  # coin_type
        args.append(None)  # coin_type_metadata
        args.append(None)  # full_memo

        # query hint from blockchain hints table
        db_cursor.execute(
            "SELECT hint FROM hints WHERE coin_id = ?",
            (coin_name,),
        )
        hint_row = db_cursor.fetchone()
        args.append(bytes(hint_row[0]) if hint_row else None)  # hint

        cache_cursor.execute(
            "INSERT INTO cached_coin_record ("
            "coin_name, confirmed_index, spent_index, coinbase, puzzle_hash, "
            "coin_parent, amount, timestamp, record_type, parent_puzzle_hash, "
            "child_count, coin_type, coin_type_metadata, full_memo, hint) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) "
            # the coin data never changes: update the spent state and what a CHILD row lacks,
            # keep coin_type, coin_type_metadata and full_memo already computed
            "ON CONFLICT(coin_name) DO UPDATE SET "
            "spent_index = excluded.spent_index, "
            "record_type = excluded.record_type, "
            "parent_puzzle_hash = excluded.parent_puzzle_hash, "
            "child_count = excluded.child_count, "
            "hint = COALESCE(excluded.hint, cached_coin_record.hint) ",
            args
        )

    # rename to cache builder / updater
    @staticmethod
    def cache_fetcher(db_conn, cache_conn, puzzle_hash, start_height: uint32 = 0,
                      end_height: uint32 = (2**32 - 1), callback: Callable = None):
        '''callback(done, total) is called while the cache is still being created, so the
           caller can show the coins already cached and the progress'''
        CALLBACK_INTERVAL = 2  # seconds
        # take all coin with puzz hash in batches

        db_cursor = db_conn.cursor()
        cache_cursor = cache_conn.cursor()
        logging(debug_logger, "DEBUG", f"CACHE UPDATE")

        import time
        ttime = time.perf_counter()

        try:
            # only used for the first build of an address (not followed yet), so it reads all its
            # coins: the upserts below make a build stopped halfway safe to run again.
            # newest first, so the coins shown while the cache is building are the latest ones
            db_cursor.execute(
                "SELECT coin_name, confirmed_index, spent_index, coinbase, puzzle_hash, "
                "coin_parent, amount, timestamp FROM coin_record "
                "WHERE puzzle_hash=? "
                "ORDER BY confirmed_index DESC",
                (puzzle_hash,)
            )
            all_rows = db_cursor.fetchall()
            total = len(all_rows)
            logging(debug_logger, "DEBUG", f"CACHE build {puzzle_hash.hex()}: {total} coins")

            sub_db_cursor = db_conn.cursor()
            done = 0
            last_done = 0
            last_callback = time.perf_counter()
            chunk_size = 100  # small first chunk, so the first coins show quickly
            while done < total:
                rows = all_rows[done:done + chunk_size]
                for row in rows:
                    FetchMaker.cache_coin_record(sub_db_cursor, cache_cursor, row, puzzle_hash)
                cache_conn.commit()
                done += len(rows)
                chunk_size = 1000

                # after the first chunk, then at most every CALLBACK_INTERVAL seconds
                if callback and (done == len(rows) or time.perf_counter() - last_callback > CALLBACK_INTERVAL):
                    callback(done, total)
                    last_callback = time.perf_counter()
                    last_done = done

            # all the coins are cached, the spent children are checked below
            if callback and total and last_done != total:
                callback(total, total)

            ######
            ### rescan upsent children coins that could have been spended
            ### scan only children that are partial record (CHILD)
            cache_cursor.execute(
                "SELECT coin_name, confirmed_index, spent_index, coinbase, puzzle_hash, "
                "coin_parent, amount, timestamp FROM cached_coin_record "  # INDEXED BY coin_puzzle_hash " 
                f"WHERE parent_puzzle_hash=? AND spent_index = 0 AND record_type = {TYPES.CacheCoinRecordType.CHILD}",
                (puzzle_hash,)
            )

            sub_cache_cursor = cache_conn.cursor()
            while True:
                rows = cache_cursor.fetchmany(1000)
                logging(debug_logger, "DEBUG", f"CACHE DB fetchmany {len(rows)}, check for childs updates")
                if not rows:
                    break

                coin_names = [row[0] for row in rows]


                placeholders = ','.join(['?'] * len(coin_names))
                db_cursor.execute(
                    f"SELECT * FROM coin_record WHERE coin_name IN ({placeholders}) AND spent_index > 0",
                    coin_names
                )

                coin_records_updates = db_cursor.fetchall()

                if coin_records_updates:
                    for cr in coin_records_updates:
                        sub_args = list(cr)
                        sub_args.append(TYPES.CacheCoinRecordType.CHILD)  # partial coin_record
                        sub_args.append(puzzle_hash)

                        sub_cache_cursor.execute(
                            "INSERT OR REPLACE INTO cached_coin_record (coin_name, confirmed_index, spent_index, "
                            "coinbase, puzzle_hash, coin_parent, amount, timestamp, record_type, parent_puzzle_hash) "
                            "VALUES (?,?,?,?,?,?,?,?,?,?) ",
                            sub_args
                        )

                cache_conn.commit()

        except Exception as e:
            print(e)
            logging(debug_logger, "DEBUG", f"CACHE TIMO TRHE BIG ONE LOAD OUT exc {e}")
            logging(debug_logger, "DEBUG", f"CACHE TIMO LOAD edarbello")
            text = traceback.format_exc()
            text = text.replace("\n", "")
            logging(debug_logger, "DEBUG", f"CACHE TIMO LOAD irogram exc {text}")
            import time
            time.sleep(2)



        endtime = time.perf_counter()

        logging(debug_logger, "DEBUG", f"CACHE TIMO LOAD for {puzzle_hash} in {endtime - ttime}")
        logging(debug_logger, "DEBUG", f"CACHE TIMO LOAD for {puzzle_hash} in {endtime - ttime}")
        logging(debug_logger, "DEBUG", f"CACHE TIMO LOAD for {puzzle_hash} in {endtime - ttime}")
        logging(debug_logger, "DEBUG", f"CACHE TIMO LOAD for {puzzle_hash} in {endtime - ttime}")
        logging(debug_logger, "DEBUG", f"CACHE TIMO LOAD for {puzzle_hash} in {endtime - ttime}")
        logging(debug_logger, "DEBUG", f"CACHE TIMO LOAD for {puzzle_hash} in {endtime - ttime}")
        logging(debug_logger, "DEBUG", f"CACHE TIMO LOAD for {puzzle_hash} in {endtime - ttime}")
        # find puzz hash of coin_id_parent
        # secondary
        # find hinted
        pass

    @staticmethod
    def cache_sync_range(db_conn, cache_conn, followed: set, from_height: int, to_height: int):
        """Update the cache of all the followed puzzle hashes for the blocks in (from_height, to_height].
           Reads only the coins created or spent in the range, whatever the size of the addresses.
           Returns {puzzle_hash: [balance, total_coin_count, unspent_coin_count]} with the changes
           of the followed puzzle hashes touched in the range."""
        cols = ("coin_name, confirmed_index, spent_index, coinbase, puzzle_hash, "
                "coin_parent, amount, timestamp")
        db_cursor = db_conn.cursor()
        cache_cursor = cache_conn.cursor()

        created = db_conn.execute(
            f"SELECT {cols} FROM coin_record INDEXED BY coin_confirmed_index "
            "WHERE confirmed_index > ? AND confirmed_index <= ?", (from_height, to_height)).fetchall()
        spent = db_conn.execute(
            f"SELECT {cols} FROM coin_record INDEXED BY coin_spent_index "
            "WHERE spent_index > ? AND spent_index <= ?", (from_height, to_height)).fetchall()

        # a coin created and spent in the range is in both lists, keep it once
        touched = {row[0]: row for row in created}
        touched.update((row[0], row) for row in spent)

        deltas = {}
        # inbound coins. When the coin is spent, cache_coin_record also caches its children
        # (the outbound CHILD rows) or the phantom row, so the outbound side needs nothing else:
        # a child is always created in the same block where its parent is spent
        for row in touched.values():
            puzzle_hash = row[4]
            if puzzle_hash not in followed:
                continue
            FetchMaker.cache_coin_record(db_cursor, cache_cursor, row, puzzle_hash)

            # the row is the current state of the node, which can be ahead of to_height:
            # count only what happened inside the range
            is_created = from_height < row[1] <= to_height
            is_spent = from_height < row[2] <= to_height
            delta = deltas.setdefault(puzzle_hash, [0, 0, 0])
            delta[0] += int_from_bytes(row[6]) * (is_created - is_spent)
            delta[1] += is_created
            delta[2] += is_created - is_spent

        # spends of outbound children sent to puzzle hashes we don't follow (primary key lookups)
        cache_cursor.executemany(
            "UPDATE cached_coin_record SET spent_index = ? "
            f"WHERE coin_name = ? AND record_type = {TYPES.CacheCoinRecordType.CHILD}",
            [(row[2], row[0]) for row in spent if row[4] not in followed])

        return deltas

    @staticmethod
    def memo_fetcher(cache_conn, puzzle_hash, sleep_between_calls: float = 0.05):
        """Fetch memos for cached coins by running parent puzzle+solution via RPC.
           Stores all memos as a JSON-encoded list of hex strings in full_memo.
           Retries RPC calls indefinitely on failure. Resumes from last_confirmed_index."""
        cache_cursor = cache_conn.cursor()

        # --- 1. read progress ---
        cache_cursor.execute(
            "SELECT last_confirmed_index FROM cached_memo_progress WHERE puzzle_hash = ?",
            (puzzle_hash,)
        )
        row = cache_cursor.fetchone()
        last_confirmed_index = row[0] if row else 0

        # --- 2. fetch coins needing memos ---
        cache_cursor.execute(
            "SELECT coin_name, confirmed_index, spent_index, coinbase, puzzle_hash, "
            "       coin_parent, amount, timestamp, record_type, parent_puzzle_hash, "
            "       child_count, coin_type, full_memo "
            "FROM cached_coin_record "
            "WHERE puzzle_hash = ? AND coinbase = 0 AND confirmed_index >= ? AND full_memo IS NULL "
            "ORDER BY confirmed_index ASC",
            (puzzle_hash, last_confirmed_index)
        )

        # --- 3. group by coin_parent ---
        coins_by_parent = {}
        for coin_row in cache_cursor.fetchall():
            parent = coin_row[5]
            coins_by_parent.setdefault(parent, []).append(coin_row)

        if not coins_by_parent:
            logging(debug_logger, "DEBUG", "MEMO FETCHER: nothing to do")
            return

        total_parents = len(coins_by_parent)
        logging(debug_logger, "DEBUG", f"MEMO FETCHER: {total_parents} parents to process")

        # --- 4. process each parent ---
        processed_count = 0
        total_key_matches = 0
        total_key_mismatches = 0
        for parent, child_coins in coins_by_parent.items():
            processed_count += 1
            parent_hex = parent.hex()
            spent_height = child_coins[0][1]  # confirmed_index of any child

            # retry-loop RPC
            for i in range(15):
                try:
                    out = RPC.call_rpc_node('get_puzzle_and_solution', coin_id=parent_hex, height=spent_height)
                    logging(debug_logger, "DEBUG", f"MEMO FETCHER RPC solution out: {out}")
                    break
                except Exception as e:
                    logging(debug_logger, "DEBUG", f"MEMO FETCHER RPC error for parent {parent_hex} at height {spent_height}: {e}, retrying...")
                    print(traceback.format_exc())
                    time.sleep(sleep_between_calls)

            puzzle_program = PyProgram.fromhex(out['puzzle_reveal'])
            solution_program = PyProgram.fromhex(out['solution'])

            # run puzzle
            max_cost = CONF.BLOCK_MAX_COST
            try:
                cost, result = puzzle_program.run_with_cost(max_cost, solution_program)
            except Exception as e:
                logging(debug_logger, "DEBUG", f"MEMO FETCHER run_with_cost failed for {parent_hex}: {e}")
                continue

            # build lookup: (target_puzzle_hash, amount) -> list of coin_names
            child_lookup = {}
            for c in child_coins:
                child_name = bytes(c[0])
                child_puzzle = bytes(c[4])
                child_amount_raw = c[6]
                if isinstance(child_amount_raw, bytes):
                    child_amount = int.from_bytes(child_amount_raw, 'big')
                else:
                    child_amount = int(child_amount_raw)
                key = (child_puzzle, child_amount)
                child_lookup.setdefault(key, []).append(child_name)

            logging(debug_logger, "DEBUG", f"MEMO FETCHER ___________________________________")
            logging(debug_logger, "DEBUG", f"MEMO FETCHER child_coins {child_coins}")
            logging(debug_logger, "DEBUG", f"MEMO FETCHER coin parent {parent_hex}")

            # scan conditions
            for condition in result.as_iter():
                cond_list = condition.as_python()
                if cond_list[0] != ConditionOpcode.CREATE_COIN:
                    continue

                target_puzzle = bytes(cond_list[1])
                target_amount_raw = cond_list[2]
                target_amount = int.from_bytes(target_amount_raw, 'big') if isinstance(target_amount_raw, bytes) else int(target_amount_raw)
                key = (target_puzzle, target_amount)

                logging(debug_logger, "DEBUG", f"MEMO FETCHER key {key}")
                if key not in child_lookup:
                    continue

                # extract memos
                memos = cond_list[3] if len(cond_list) > 3 else []
                if memos:
                    memo_json = json.dumps([str(m) for m in memos]).encode()
                    logging(debug_logger, "DEBUG", f"MEMO FETCHER MEMOS JSON {memo_json}!!!")
                else:
                    memo_json = b'[]'
                    logging(debug_logger, "DEBUG", f"MEMO FETCHER NO MEMOS !!!")

                # update all matching children
                for child_name in child_lookup[key]:
                    cache_cursor.execute(
                        "UPDATE cached_coin_record SET full_memo = ? WHERE coin_name = ?",
                        (memo_json, child_name)
                    )
                    if cache_cursor.rowcount == 0:
                        logging(debug_logger, "DEBUG", f"MEMO FETCHER WARNING: UPDATE affected 0 rows for {child_name.hex()}")
                del child_lookup[key]

            # raise if unmatched children 
            if len(child_lookup) > 0:
                raise "memo fetching: child with no parent?"

            # update progress
            highest_confirmed = max(c[1] for c in child_coins)
            cache_cursor.execute(
                "INSERT OR REPLACE INTO cached_memo_progress (puzzle_hash, last_confirmed_index) VALUES (?, ?)",
                (puzzle_hash, highest_confirmed)
            )
            cache_conn.commit()

            if sleep_between_calls:
                time.sleep(sleep_between_calls)

            if processed_count % 10 == 0 or processed_count == total_parents:
                address = encode_puzzle_hash(bytes32(puzzle_hash), CONF.ADD_PREFIX)
                logging(debug_logger, "DEBUG", f"MEMO FETCHER progress: {processed_count}/{total_parents} parents processed for {address}")

        logging(debug_logger, "DEBUG", f"MEMO FETCHER: done ({processed_count}/{total_parents} processed)")

    @staticmethod
    def CACHE_puzzle_hash_fetcher(puzzle_hash: bytes, sorting_column: str,
                                  start_height: uint32 = uint32(0),
                                  end_height: uint32 = uint32((2**32) - 1),
                                  remove_spent_coins: bool = False,
                                  remove_self_transactions: bool = False,
                                  order='DESC',
                                  first_last_count: bool = False):
        """ inbound cached fetcher"""

        base_query = (

            f" WITH main_coins AS ( "
            f"     SELECT coin_name, confirmed_index, spent_index, coinbase, puzzle_hash, "
            f"            coin_parent, amount, timestamp, record_type, parent_puzzle_hash "
            f"     FROM cached_coin_record INDEXED BY idx_cache_inbound "
            f"     WHERE puzzle_hash = ? "
            f"       AND confirmed_index >= ? "
            f"       AND confirmed_index < ? "
            f"       {'AND spent_index <= 0' if remove_spent_coins else ''} "
            f"       {'AND is_self = 0' if remove_self_transactions else ''} "
            f" ) "  # use the comma only if there is another statement for the CTE, otherwise do not place it
        )

        selection_query = (
            f"SELECT coin_name, confirmed_index, spent_index, coinbase, puzzle_hash, "
            f"       coin_parent, amount, timestamp, record_type, parent_puzzle_hash "
            f"FROM main_coins "
            f"ORDER BY {sorting_column} {order} "
        )

        logging(debug_logger, "DEBUG", f"LOAD query {base_query} ")

        if first_last_count:
            def fetch(conn):
                flc_base_query = f"{base_query}, filtered AS ( {selection_query} ) "

                # count on main_coins, without the ORDER BY of filtered, so it can be read from the index only
                count_query = base_query + "SELECT COUNT(*) FROM main_coins "

                with conn:
                    cursor = conn.execute(count_query,
                                          (puzzle_hash, start_height, end_height))
                    item_count = cursor.fetchall()[0][0]

                # first last items
                flc_selection_query = (
                    f"SELECT * FROM (SELECT * FROM filtered ORDER BY {sorting_column} ASC LIMIT 1 ) "
                    f" UNION ALL "
                    f"SELECT * FROM (SELECT * FROM filtered ORDER BY {sorting_column} DESC LIMIT 1 ); "
                )

                first_last_query = flc_base_query + flc_selection_query

                with conn:
                    cursor = conn.execute(first_last_query,
                                          (puzzle_hash, start_height, end_height))
                    items = cursor.fetchall()

                coin_record_list = []

                #logging(debug_logger, "DEBUG", f"DB TIMO CACHE SLOW lenght {len(items[1])} ")
                for i in items:
                    coin_record_list.append(TYPES.CoinRecordRoto(i))

                if item_count > 0:
                    if len(coin_record_list) >= 2:
                        return item_count, coin_record_list[0], coin_record_list[1]
                    else:
                        return item_count, None, None
                else:
                    return 0, None, None
            return fetch
        else:
            def fetch(conn, start, count):

                limit_offset_query = "LIMIT ? OFFSET ? "
                query = base_query + selection_query + limit_offset_query

                # debug sql
                #query = f" EXPLAIN QUERY PLAN " + query
                #query_exp = "EXPLAIN QUERY PLAN " + query
                #with conn:
                #    cursor = conn.execute(query_exp,
                #                          (puzzle_hash, start_height, end_height, count, start))
                #    items = cursor.fetchall()


                with conn:
                    cursor = conn.execute(query,
                                          (puzzle_hash, start_height, end_height, count, start))
                    items = cursor.fetchall()

                coin_record_list = []
                for i in items:
                    coin_record_list.append(TYPES.CoinRecordRoto(i))

                return coin_record_list

            return fetch

    @staticmethod
    def CACHE_puzzle_hash_outbound_fetcher(puzzle_hash: bytes, sorting_column: str,
                                           start_height: uint32 = uint32(0),
                                           end_height: uint32 = uint32((2**32) - 1),
                                           remove_spent_coins: bool = False,
                                           remove_self_transactions: bool = False,
                                           show_phantom_coin_outputs: bool = False,
                                           order: str = 'DESC',
                                           first_last_count: bool = False):
        """ outbound cached fetcher"""
        ### add coin spent with no child?

        base_query = (
            f" WITH main_coins AS ( "
            f"     SELECT coin_name, confirmed_index, spent_index, coinbase, puzzle_hash, "
            f"            coin_parent, amount, timestamp, record_type, parent_puzzle_hash "
            f"     FROM cached_coin_record INDEXED BY idx_cache_outbound "
            f"     WHERE parent_puzzle_hash = ? "
            f"       AND confirmed_index >= ? "
            f"       AND confirmed_index < ? "
            f"       {'AND spent_index <= 0' if remove_spent_coins else ''} "
            f"       {'AND is_self = 0' if remove_self_transactions else ''} "
            f"       {'' if show_phantom_coin_outputs else 'AND record_type != 2'} "  # 2 are sibling input coins
            f" ) "  # use the comma only if there is another statement for the CTE, otherwise do not place it
        )

        selection_query = (
            f"SELECT coin_name, confirmed_index, spent_index, coinbase, puzzle_hash, "
            f"       coin_parent, amount, timestamp, record_type, parent_puzzle_hash "
            f"FROM main_coins "
            f"ORDER BY {sorting_column} {order} "
        )

        if first_last_count:

            def fetch(conn):

                flc_base_query = f"{base_query}, filtered AS ( {selection_query} ) "

                # count on main_coins, without the ORDER BY of filtered, so it can be read from the index only
                count_query = base_query + "SELECT COUNT(*) FROM main_coins "


                with conn:
                    cursor = conn.execute(count_query,
                                          (puzzle_hash, start_height, end_height))
                    item_count = cursor.fetchall()[0][0]

                # first last items
                flc_selection_query = (
                    f"SELECT * FROM (SELECT * FROM filtered ORDER BY {sorting_column} ASC LIMIT 1 ) "
                    f" UNION ALL "
                    f"SELECT * FROM (SELECT * FROM filtered ORDER BY {sorting_column} DESC LIMIT 1 ); "
                )

                first_last_query = flc_base_query + flc_selection_query

                with conn:
                    cursor = conn.execute(first_last_query,
                                          (puzzle_hash, start_height, end_height))
                    items = cursor.fetchall()

                coin_record_list = []
                for i in items:
                    coin_record_list.append(TYPES.CoinRecordRoto(i))

                if item_count > 0:
                    if len(coin_record_list) >= 2:
                        return item_count, coin_record_list[0], coin_record_list[1]
                    else:
                        return item_count, None, None
                else:
                    return 0, None, None

        else:
            def fetch(conn, start, count):

                limit_offset_query = "LIMIT ? OFFSET ? "
                query = base_query + selection_query + limit_offset_query

                # DEBUG SQL
                #query = f" EXPLAIN QUERY PLAN " + query
                #query_exp = "EXPLAIN QUERY PLAN " + query
                #with conn:
                #    cursor = conn.execute(query_exp,
                #                          (puzzle_hash, start_height, end_height, count, start))
                #    items = cursor.fetchall()

                with conn:
                    cursor = conn.execute(query,
                                          (puzzle_hash, start_height, end_height, count, start))
                    items = cursor.fetchall()

                coin_record_list = []
                for i in items:
                    coin_record_list.append(TYPES.CoinRecordRoto(i))

                return coin_record_list

        return fetch

    @staticmethod
    def CACHE_one_spent_coin(conn, puzzle_hash: bytes):
        """Any spent coin of the puzzle hash, or None. All the coins with the same puzzle hash
           have the same puzzle, so any spent coin is enough to get the puzzle reveal."""
        row = conn.execute(
            "SELECT coin_name, confirmed_index, spent_index, coinbase, puzzle_hash, "
            "       coin_parent, amount, timestamp, record_type, parent_puzzle_hash "
            "FROM cached_coin_record INDEXED BY idx_cache_inbound "
            "WHERE puzzle_hash = ? AND spent_index > 0 "
            "LIMIT 1",
            (puzzle_hash,)).fetchone()
        return TYPES.CoinRecordRoto(row) if row else None

    @staticmethod
    def puzzle_hash_base_cte(remove_spent_coins: bool,
                             remove_self_transactions: bool) -> str:

        main_coins = (
            f" WITH main_coins AS ( "
            f"     SELECT coin_name, confirmed_index, spent_index, coinbase, puzzle_hash, "
            f"            coin_parent, amount, timestamp "
            f"     FROM coin_record INDEXED BY coin_puzzle_hash "
            f"     WHERE puzzle_hash = ? "
            f"       AND confirmed_index >= ? "
            f"       AND confirmed_index < ? "
            f"       {'AND spent_index <= 0' if remove_spent_coins else ''} "
            f" ), "
        )
        where = "WHERE COALESCE(cr.puzzle_hash, '') != ?1" if remove_self_transactions else ""
        filtered = (
            f"filtered AS ( "
            f"    SELECT mc.*, 0 AS record_type, cr.puzzle_hash AS parent_puzzle_hash "
            f"    FROM main_coins mc "
            f"    LEFT JOIN coin_record cr "
            f"      ON mc.coin_parent = cr.coin_name "
            f"    {where} "
            f") "
        )

        return f"{main_coins} {filtered}"

    @staticmethod
    def puzzle_hash_fetcher(puzzle_hash: bytes, sorting_column: str,
                            start_height: uint32 = uint32(0),
                            end_height: uint32 = uint32((2**32) - 1),
                            remove_spent_coins: bool = False,
                            remove_self_transactions: bool = False,
                            order='DESC'):
        """ inbound fetcher the does not use cache """

        def fetch(conn, start, count):

            timo = UTILS.Timer()
            timo.start()
            timo.clocking('init')
            base_query = FetchMaker.puzzle_hash_base_cte(remove_spent_coins, remove_self_transactions)

            selection_query = (
                f"SELECT coin_name, confirmed_index, spent_index, coinbase, puzzle_hash, "
                f"       coin_parent, amount, timestamp, record_type, parent_puzzle_hash "
                f"FROM filtered "
                f"ORDER BY {sorting_column} {order} "
                f"LIMIT ? OFFSET ? "
            )

            query = base_query + selection_query

            # debug sql
            # query = f" EXPLAIN QUERY PLAN " + query
            with conn:
                cursor = conn.execute(query,
                                      (puzzle_hash, start_height, end_height, count, start))
                items = cursor.fetchall()

            coin_record_list = []
            for i in items:
                coin_record_list.append(TYPES.CoinRecordRoto(i))

            timo.clocking('end')
            timo.end()
            timo_s = f"{timo}"
            timo_ss = timo_s.split('\n')
            logging(debug_logger, "DEBUG", "DB TIMO SLOW fetch: ")
            for n, i in enumerate(timo_ss):
                logging(debug_logger, "DEBUG", f"DB TIMO SLOWWW i{n}-{i}")


            return coin_record_list

        return fetch

    # TODO: the preview should be light, it is only a quick look at the last coins before opening
    # the address viewer. Rowid windows, filters and progress make it heavier than needed, simplify it.
    @staticmethod
    def puzzle_hash_preview(conn, puzzle_hash: bytes, count: int = 100,
                            start_height: uint32 = uint32(0),
                            end_height: uint32 = uint32((2**32) - 1),
                            remove_spent_coins: bool = False,
                            remove_self_transactions: bool = False,
                            window_size: int = 5000,
                            progress: Callable = None,
                            stop: Callable = None):
        """Last `count` coins of a puzzle hash, newest first, from the chia db.
           The chia db inserts the coins block by block, so the rowid follows the confirmed height,
           and the coin_puzzle_hash index (puzzle_hash, rowid) can be walked backward without sorting
           all the coins of the puzzle hash. The scan goes in windows of `window_size` index entries,
           after each window `progress(height)` is called with the height reached.
           `stop()` returning True ends the scan (e.g. a new search started), and None is returned."""

        # rowid bounds of the height range, so the scan jump directly to it
        low_rowid = 0
        if start_height > 0:
            row = conn.execute(
                "SELECT rowid FROM coin_record INDEXED BY coin_confirmed_index "
                "WHERE confirmed_index >= ? ORDER BY confirmed_index ASC, rowid ASC LIMIT 1",
                (start_height,)).fetchone()
            if row is None:
                return []
            low_rowid = row[0]
        high_rowid = 2**63 - 1
        if end_height < 2**32 - 1:
            row = conn.execute(
                "SELECT rowid FROM coin_record INDEXED BY coin_confirmed_index "
                "WHERE confirmed_index < ? ORDER BY confirmed_index DESC, rowid DESC LIMIT 1",
                (end_height,)).fetchone()
            if row is None:
                return []
            high_rowid = row[0]

        # the confirmed_index condition stay as the real filter, the rowid only bounds the scan
        main_coins = (
            "SELECT rowid AS rid, coin_name, confirmed_index, spent_index, coinbase, puzzle_hash, "
            "       coin_parent, amount, timestamp "
            "FROM coin_record INDEXED BY coin_puzzle_hash "
            "WHERE puzzle_hash = ?1 AND rowid BETWEEN ?2 AND ?3 "
            "  AND confirmed_index >= ?4 AND confirmed_index < ?5 "
            f" {'AND spent_index <= 0' if remove_spent_coins else ''} "
            "ORDER BY rowid DESC "
        )
        if remove_self_transactions:
            # the parent is needed to filter, join the whole window
            query = (
                f"SELECT mc.coin_name, mc.confirmed_index, mc.spent_index, mc.coinbase, mc.puzzle_hash, "
                f"       mc.coin_parent, mc.amount, mc.timestamp, 0 AS record_type, cr.puzzle_hash AS parent_puzzle_hash "
                f"FROM ({main_coins}) mc "
                f"LEFT JOIN coin_record cr ON mc.coin_parent = cr.coin_name "
                f"WHERE COALESCE(cr.puzzle_hash, '') != ?1 "
                f"ORDER BY mc.rid DESC LIMIT ?6"
            )
        else:
            # join only the coins kept
            query = (
                f"SELECT mc.coin_name, mc.confirmed_index, mc.spent_index, mc.coinbase, mc.puzzle_hash, "
                f"       mc.coin_parent, mc.amount, mc.timestamp, 0 AS record_type, cr.puzzle_hash AS parent_puzzle_hash "
                f"FROM ({main_coins} LIMIT ?6) mc "
                f"LEFT JOIN coin_record cr ON mc.coin_parent = cr.coin_name "
                f"ORDER BY mc.rid DESC"
            )

        items = []
        cursor_rowid = high_rowid
        while len(items) < count and cursor_rowid >= low_rowid:
            if stop and stop():
                return None

            # lower rowid of the next window, reading only the index
            row = conn.execute(
                "SELECT rowid, confirmed_index FROM coin_record INDEXED BY coin_puzzle_hash "
                "WHERE puzzle_hash = ? AND rowid BETWEEN ? AND ? "
                "ORDER BY rowid DESC LIMIT 1 OFFSET ?",
                (puzzle_hash, low_rowid, cursor_rowid, window_size - 1)).fetchone()
            if row is None:
                window_low_rowid = low_rowid
                window_height = start_height
            else:
                window_low_rowid, window_height = row

            items += conn.execute(query, (puzzle_hash, window_low_rowid, cursor_rowid, start_height,
                                          end_height, count - len(items))).fetchall()
            cursor_rowid = window_low_rowid - 1

            if progress:
                progress(window_height)

        coin_record_list = [TYPES.CoinRecordRoto(i) for i in items]
        coin_record_list.sort(key=lambda cr: cr.confirmed_block_index, reverse=True)
        return coin_record_list


    @staticmethod
    def puzzle_hash_first_last_count_fetcher(
            puzzle_hash: bytes, sorting_column: str, start_height: uint32 = uint32(0),
            end_height: uint32 = uint32((2**32) - 1), remove_spent_coins: bool = True,
            remove_self_transactions: bool = False, order: str = "DESC"):
        """ inbound first last count fetcher the does not use cache """
        # TODO: use the order to invert first last

        def fetch(conn):

            base_query = FetchMaker.puzzle_hash_base_cte(remove_spent_coins, remove_self_transactions)

            # count
            selection_query = (
                f"SELECT COUNT(*) "
                f"FROM filtered "
            )
            count_query = base_query + selection_query

            with conn:
                cursor = conn.execute(count_query,
                                      (puzzle_hash, start_height, end_height))
                item_count = cursor.fetchall()[0][0]

            # first last items
            selection_query = (
                f"SELECT * FROM (SELECT * FROM filtered ORDER BY {sorting_column} ASC LIMIT 1 ) "
                f" UNION ALL "
                f"SELECT * FROM (SELECT * FROM filtered ORDER BY {sorting_column} DESC LIMIT 1 ); "
            )

            first_last_query = base_query + selection_query

            with conn:
                cursor = conn.execute(first_last_query,
                                      (puzzle_hash, start_height, end_height))
                items = cursor.fetchall()

            coin_record_list = []
            for i in items:
                coin_record_list.append(TYPES.CoinRecordRoto(i))

            if item_count > 0:
                if len(coin_record_list) >= 2:
                    return item_count, coin_record_list[0], coin_record_list[1]
                else:
                    return item_count, None, None
            else:
                return 0, None, None

        return fetch

    @staticmethod
    def get_total_amount_and_count_from_puzzle_hash(path: str, puzzle_hash: bytes):
        """Not a fetcher"""
        query_amount = "SELECT amount FROM coin_record WHERE puzzle_hash = ? AND spent_index <= 0;"
        query_total_coin = "SELECT COUNT(*) FROM coin_record WHERE puzzle_hash = ? ;"
        query_max_block_height = "SELECT max(height) FROM full_blocks WHERE in_main_chain = 1;"

        conn = sqlite3.connect(path, uri=True, timeout=SQL_TIMEOUT)

        timo = UTILS.Timer()
        timo.start()
        timo.clocking('init')

        with conn:
            cursor = conn.execute(query_amount, (puzzle_hash,))
            items = cursor.fetchall()
            balance = 0
            unspent_coin_count = len(items)
            for i in items:
                balance += int_from_bytes(i[0])
            timo.clocking('amount')

            cursor = conn.execute(query_total_coin, (puzzle_hash,))
            items = cursor.fetchall()
            total_coin_count = items[0][0]
            timo.clocking('total items count')

            cursor = conn.execute(query_max_block_height)
            peak_height = cursor.fetchone()[0]

        return balance, unspent_coin_count, total_coin_count, peak_height

    @staticmethod
    def get_hinted_amount_and_type_count_from_puzzle_hash(path: str, puzzle_hash: bytes):
        """Not a fetcher"""

        query_unspent_hinted_coin_count = """ SELECT COUNT(*) FROM coin_record cr JOIN hints h ON cr.coin_name = h.coin_id WHERE spent_index <= 0 AND h.hint = ? """
        query_total_hinted_coin_count = """ SELECT COUNT(*) FROM coin_record cr JOIN hints h ON cr.coin_name = h.coin_id WHERE h.hint = ? """

        conn = sqlite3.connect(path, uri=True, timeout=SQL_TIMEOUT)

        timo = UTILS.Timer()
        timo.start()
        timo.clocking('init')

        with conn:

            cursor = conn.execute(query_unspent_hinted_coin_count, (puzzle_hash,))
            unspent_hinted_coin_count = cursor.fetchall()[0][0]
            timo.clocking('unspent hinted items count')

            cursor = conn.execute(query_total_hinted_coin_count, (puzzle_hash,))
            total_hinted_coin_count = cursor.fetchall()[0][0]
            timo.clocking('total hinted items count')

            timo.end()
            timo_s = f"{timo}"
            timo_ss = timo_s.split('\n')
            logging(debug_logger, "DEBUG", "DB TIMO INFO DATA : ")
            for n, i in enumerate(timo_ss):
                logging(debug_logger, "DEBUG", f"DB TIMO INFO DATA i{n}-{i}")

        return unspent_hinted_coin_count, total_hinted_coin_count

    @staticmethod
    def get_coins_by_hint(path: str, puzzle_hash: bytes):
        """Not a fetcher"""

        query = """ SELECT cr.coin_name, cr.confirmed_index, cr.coin_parent, cr.puzzle_hash, cr.amount FROM coin_record cr JOIN hints h ON cr.coin_name = h.coin_id WHERE h.hint = ? """

        conn = sqlite3.connect(path, uri=True, timeout=SQL_TIMEOUT)

        with conn:
            cursor = conn.execute(query, (puzzle_hash,))
            coins = cursor.fetchall()

        # DB for hinted coins: normal coin + (parent_puzzle_hash, ) + (type, complete memo, )
        for i in coins:
            coin_name = bytes32.from_bytes(i[0])
            spent_height = i[1]
            parent = bytes32.from_bytes(i[2])
            puzzle = bytes32.from_bytes(i[3])
            amount = int_from_bytes(i[4])

            out = RPC.call_rpc_node('get_puzzle_and_solution', coin_id=parent.hex(), height=spent_height)

            puzzle_program = PyProgram.fromhex(out['puzzle_reveal'])
            solution_program = PyProgram.fromhex(out['solution'])

            # find the puzzle type
            names, hashes = PUZ.unroll_puzzle_to_names(puzzle_program)

            for n, h in zip(names, hashes):
                print(f"{n.upper()} with hash; {h}")

            puzzle_type, name = PUZ.compare_unrolled_puzzle_to_known_layered_puzzles(hashes)

            # Run the puzzle with the solution (returns cost and conditions)
            max_cost = 11_000_000_000
            try:
                cost, result = puzzle_program.run_with_cost(max_cost, solution)
            except Exception as e:
                print(f"Failed to run puzzle: {e}")
                return

            # result is a Program object representing the list of conditions
            for condition in result.as_iter():
                cond_list = condition.as_python()
                opcode = cond_list[0]

                # Check for opcode 51 (CREATE_COIN)
                if opcode == ConditionOpcode.CREATE_COIN:
                    # Format: (51 puzzle_hash amount [memos])
                    if len(cond_list) > 3:
                        memos = cond_list[3]
                        print(f"Target: {cond_list[1].hex()} | Amount: {int.from_bytes(cond_list[2], 'big')}")
                        for memo in memos:
                            print(f"  -> Found Memo: {memo.hex()}")
                    else:
                        print(f"Target: {cond_list[1].hex()} - No memos present.")

    # ------------------------------------------------------------------
    # Coin type verification (CAT / NFT / XCH)
    # ------------------------------------------------------------------

    # _check_cats = [] etc.

    @staticmethod
    def verify_coin_type(coin_record, hint: bytes = None):
        """
        Detect whether *coin_record* is a CAT, NFT, or plain XCH coin,
        and verify that it is owned by the hint provided.

        Parameters
        ----------
        coin_record : CoinRecordRoto or tuple
            The coin to analyse.  If it is a ``CoinRecordRoto`` the helper
            reads ``coin_record.spent_block_index`` etc.  Otherwise it is
            treated as a raw DB row.
        hint : bytes, optional
            The puzzle-hash hint that identifies the owner.  If *None* the
            function will try to look the hint up in the database.

        Returns
        -------
        dict
            ``{'type': str, 'verified': bool, 'detail': dict}``
            *type* is ``'CAT'``, ``'NFT'``, ``'XCH'`` or ``'UNKNOWN'``.
        """
        coin = FetchMaker._normalize_coin_record(coin_record)
        if coin is None:
            return {'type': 'UNKNOWN', 'verified': False, 'detail': {}}

        # 1. Resolve hint if not supplied (needs a DB cursor)
        if hint is None:
            return {'type': 'UNKNOWN', 'verified': False, 'detail': {'reason': 'no_hint_provided'}}

        # 2. Fetch the puzzle reveal relevant to this coin
        if coin.spent_block_index > 0:
            # Spent coin: we can read the coin's own puzzle reveal
            puzzle_program, _ = FetchMaker._fetch_puzzle_and_solution(coin)
        else:
            # Unspent coin: we look at the parent's puzzle reveal
            puzzle_program, _ = FetchMaker._fetch_parent_puzzle_and_solution(coin)

        if puzzle_program is None:
            return {'type': 'UNKNOWN', 'verified': False,
                    'detail': {'reason': 'puzzle_fetch_failed'}}

        # 3. Run type checkers
        for checker in _TYPE_CHECKERS:
            result = checker(coin, puzzle_program, hint)
            if result is not None:
                return result

        # 3. Fallback – plain XCH if the hint matches the coin puzzle hash
        plain_match = coin.coin.puzzle_hash == hint
        return {
            'type': 'XCH',
            'verified': plain_match,
            'detail': {'puzzle_hash': coin.coin.puzzle_hash.hex()}
        }

    @staticmethod
    def _normalize_coin_record(coin_record):
        """Return a CoinRecordRoto from either a CoinRecordRoto or a DB tuple."""
        if isinstance(coin_record, TYPES.CoinRecordRoto):
            return coin_record
        # Raw row from get_coins_by_hint: (coin_name, confirmed_index, coin_parent, puzzle_hash, amount)
        try:
            return TYPES.CoinRecordRoto(coin_record)
        except Exception:
            return None

    @staticmethod
    def _fetch_puzzle_and_solution(coin):
        """Return (puzzle_program, solution_program) for the coin's own spend."""
        out = RPC.call_rpc_node('get_puzzle_and_solution',
                                coin_id=coin.coin_name.hex(),
                                height=coin.spent_block_index)
        if out is None:
            return None, None
        puzzle = PyProgram.fromhex(out['puzzle_reveal'])
        solution = PyProgram.fromhex(out['solution'])
        return puzzle, solution

    @staticmethod
    def _fetch_parent_puzzle_and_solution(coin):
        """Return (puzzle_program, solution_program) for the coin's parent spend."""
        parent_name = coin.coin.parent_coin_info.hex()
        out = RPC.call_rpc_node('get_puzzle_and_solution',
                                coin_id=parent_name,
                                height=coin.confirmed_block_index)
        if out is None:
            return None, None
        puzzle = PyProgram.fromhex(out['puzzle_reveal'])
        solution = PyProgram.fromhex(out['solution'])
        return puzzle, solution

    @staticmethod
    def puzzle_hash_outbound_fetcher(puzzle_hash: bytes, sorting_column: str, start_height: uint32 = uint32(0),
                                     end_height: uint32 = uint32((2**32) - 1),
                                     include_self_spent_coin: bool = True, order='DESC'):
        """ outbound fetcher - NO CACHE """

        def fetch(conn, start, count, filters=None):

            values = [puzzle_hash, start_height, end_height]
            height_filter = "AND parent.confirmed_index>=? AND parent.confirmed_index<? "
            filtering_self_spent = ''
            if include_self_spent_coin:
                filtering_self_spent = " AND child.puzzle_hash != ? "
                values.append(puzzle_hash)
            values.append(count)
            values.append(start)
            out_bound_query = (
                f"SELECT child.coin_name, child.confirmed_index, child.spent_index, child.coinbase, child.puzzle_hash, "
                f"       child.coin_parent, child.amount, child.timestamp, 0 AS record_type, NULL AS parent_puzzle_hash "
                f"FROM coin_record AS child "
                f"JOIN coin_record AS parent ON child.coin_parent = parent.coin_name "
                f"WHERE parent.puzzle_hash = ? {height_filter} {filtering_self_spent} "
                f"ORDER BY child.{sorting_column} {order} LIMIT ? OFFSET ? "
            )

            with conn:
                cursor = conn.execute(out_bound_query, values)
                items = cursor.fetchall()

            coin_record_list = []
            for i in items:
                coin_record_list.append(TYPES.CoinRecordRoto(i))

            return coin_record_list

        return fetch


    @staticmethod
    def puzzle_hash_outbound_first_last_count_fetcher(puzzle_hash: bytes, sorting_column: str,
                                                      start_height: uint32 = uint32(0),
                                                      end_height: uint32 = uint32((2**32) - 1),
                                                      include_self_spent_coin: bool = True, order: str = 'DESC'):
        """ outbound first last count fetcher the does not use cache """
        # TODO: use the order to invert first last
        def fetch(conn, filters=None):

            values = [puzzle_hash, start_height, end_height]
            height_filter = "AND parent.confirmed_index>=? AND parent.confirmed_index<? "
            filtering_self_spent = ''
            if include_self_spent_coin:
                filtering_self_spent = " AND child.puzzle_hash != ? "
                values.append(puzzle_hash)

            # total items count
            count_query = (
                f"SELECT COUNT(*) "
                f"FROM coin_record AS child "
                f"JOIN coin_record AS parent ON child.coin_parent = parent.coin_name "
                f"WHERE parent.puzzle_hash = ? {height_filter} {filtering_self_spent} "
            )

            with conn:
                cursor = conn.execute(count_query, values)
                item_count = cursor.fetchall()[0][0]

            # first_last_query
            first_last_query = (
                f"SELECT * FROM ( "
                f"  SELECT child.coin_name, child.confirmed_index, child.spent_index, child.coinbase, child.puzzle_hash, "
                f"         child.coin_parent, child.amount, child.timestamp, 0 AS record_type, NULL AS parent_puzzle_hash "
                f"    FROM coin_record AS child "
                f"    JOIN coin_record AS parent ON child.coin_parent = parent.coin_name "
                f"    WHERE parent.puzzle_hash = ? {height_filter} {filtering_self_spent} "
                f"    ORDER BY child.{sorting_column} ASC LIMIT 1 ) "
                f"UNION ALL "
                f"SELECT * FROM ( "
                f"  SELECT child.coin_name, child.confirmed_index, child.spent_index, child.coinbase, child.puzzle_hash, "
                f"         child.coin_parent, child.amount, child.timestamp, 0 AS record_type, NULL AS parent_puzzle_hash "
                f"    FROM coin_record AS child "
                f"    JOIN coin_record AS parent ON child.coin_parent = parent.coin_name "
                f"    WHERE parent.puzzle_hash = ? {height_filter} {filtering_self_spent} "
                f"    ORDER BY child.{sorting_column} DESC LIMIT 1 )  "
            )
            valuesX2 = values + values

            with conn:
                cursor = conn.execute(first_last_query, valuesX2)
                items = cursor.fetchall()

            coin_record_list = []
            for i in items:
                coin_record_list.append(TYPES.CoinRecordRoto(i))

            if item_count > 0:
                if len(coin_record_list) >= 2:
                    return item_count, coin_record_list[0], coin_record_list[1]
                else:
                    return item_count, None, None
            else:
                return 0, None, None

        return fetch


    @staticmethod
    def block_fetcher(table, sorting_column=None):
        # NB:
        # it is not clear, if you use sorting_column the start, count are min and max height
        # sorting in sql is not use, sorting means only on which column apply start and count
        # NB:
        # filters work only for "=", not sure if it worth keep it as parameter. Maybe it is better
        # to create a new fun
        def fetch(conn, start, count, filters=None):
            """ order is not implemented... """
            if not filters:
                filters = {}

            where_clauses = []
            values = []

            for filter, val in filters.items():
                where_clauses.append(f"{filter} = ?")
                values.append(val)

            if sorting_column is not None:
                range_sql = f"{sorting_column} >= ? AND {sorting_column} < ?"
                where_sql = f"WHERE {' AND '.join(where_clauses)} AND {range_sql}" if filters else f"WHERE {range_sql}"
                values.extend([start, start + count])
            else:
                range_sql = 'LIMIT ? OFFSET ?'
                where_sql = f"WHERE {' AND '.join(where_clauses)} {range_sql}" if filters else f"{range_sql}"
                values.extend([count, start])


            cur = conn.cursor()
            query = f"SELECT * FROM {table} {where_sql}"
            #print(query)
            #print(values)
            #query = f"SELECT * FROM {table} {where_sql} ORDER BY {sorting_column} LIMIT ? OFFSET ?"

            cur.execute(query, values)
            items = cur.fetchall()
            return items

        return fetch

    @staticmethod
    def block_first_last_count_fetcher(table, sorting_column=None):
        def fetch(conn, filters={}):

            where_clauses = []
            values = []

            for filter, val in filters.items():
                where_clauses.append(f"{filter} = ?")
                values.append(val)

            where_sql = f" WHERE {' AND '.join(where_clauses)} " if filters else ""

            # total items count
            count_query = f"SELECT COUNT(*) FROM {table} {where_sql} "
            with conn:
                cursor = conn.execute(count_query, values)
                item_count = cursor.fetchall()[0][0]

            # first and last
            first_last_query = (
                f"SELECT * FROM ( "
                f"    SELECT * FROM {table} {where_sql} ORDER BY {sorting_column} ASC LIMIT 1) "
                f"UNION ALL "
                f"SELECT * FROM ( "
                f"    SELECT * FROM {table} {where_sql} ORDER BY {sorting_column} DESC LIMIT 1) "
            )

            values = values + values
            with conn:
                cursor = conn.execute(first_last_query, values)
                items = cursor.fetchall()
            return item_count, items[0], items[1]

        return fetch

    @staticmethod
    def fetch_rpc_coin_memo(coin_name_hex: str, coin_record: tuple):
        """Fetch coin record from full node via RPC and extract memo from parent's puzzle_and_solution.
        Returns (rpc_spent, coin_memo)."""
        rpc_result = None
        try:
            rpc_result = RPC.call_rpc_node('get_coin_record_by_name', name=coin_name_hex)
        except Exception as e:
            logging(debug_logger, "DEBUG", f"fetch_coin_record_by_name failed: {e}")

        coin_memo = ''
        if rpc_result and rpc_result is not False:
            try:
                parent_id = rpc_result['coin']['parent_coin_info']
                spent_idx = rpc_result['confirmed_block_index']
                if parent_id:
                    sol = RPC.call_rpc_node('get_puzzle_and_solution', coin_id=parent_id, height=spent_idx)
                    if sol and sol is not False:
                        puzzle = PyProgram.fromhex(sol['puzzle_reveal'])
                        solution = PyProgram.fromhex(sol['solution'])
                        cost, result = puzzle.run_with_cost(CONF.BLOCK_MAX_COST, solution)
                        target_puz = coin_record[4]
                        target_amt = int.from_bytes(coin_record[6], 'big')
                        for cond in result.as_iter():
                            cl = cond.as_python()
                            if cl[0] == ConditionOpcode.CREATE_COIN:
                                cp = bytes(cl[1])
                                car = cl[2]
                                ca = int.from_bytes(car, 'big')
                                if cp == target_puz and ca == target_amt and len(cl) > 3:
                                    memos = cl[3]
                                    if memos:
                                        coin_memo = json.dumps([str(m) for m in memos]).encode()
                                    break
                                else:
                                    coin_memo = b'[]'

            except Exception as e:
                logging(debug_logger, "DEBUG", f"cl is {cl}")
                logging(debug_logger, "DEBUG", f"coin id {bytes32(cp).hex()} amount: {ca} and target puz {target_puz}")

                logging(debug_logger, "DEBUG", f"RPC memo fetch failed: {e}")
                UTILS.logging_traceback("RPC MEMO FETCH")

        return coin_memo

    @staticmethod
    def fetch_and_cache_coin_memo(cache_conn, coin_name_hex: str, coin_record: tuple):
        """Fetch memo via RPC using fetch_rpc_coin_memo and save it into the cache DB.
        coin_name_hex should include the 0x prefix."""
        coin_memo = FetchMaker.fetch_rpc_coin_memo(coin_name_hex, coin_record)
        if coin_memo:
            #memo_json = json.dumps(coin_memo).encode()
            memo_json = coin_memo
            coin_name_bytes = bytes32.fromhex(coin_name_hex[2:] if coin_name_hex.startswith('0x') else coin_name_hex)
            cache_conn.execute(
                "UPDATE cached_coin_record SET full_memo = ? WHERE coin_name = ?",
                (memo_json, bytes(coin_name_bytes))
            )
            cache_conn.commit()

        return coin_memo


# --- Type checker registry ----------------------------------------------------
_TYPE_CHECKERS = []


def _register_type_checker(func):
    """Decorator to register a coin-type checker."""
    _TYPE_CHECKERS.append(func)
    return func


def _puzzle_name_from_hash(puzzle_hash_hex: str) -> str:
    """Look up a puzzle name from its hash using CONF.KNOWN_PUZZLES."""
    entry = CONF.KNOWN_PUZZLES.get(puzzle_hash_hex)
    if entry is not None:
        return entry.get('name', CONF.UNKNOWN_PUZZLE)
    return CONF.UNKNOWN_PUZZLE


# ------------------------------------------------------------------------------
# CAT checker
# ------------------------------------------------------------------------------
@_register_type_checker
def _check_cat_type(coin, puzzle_program, hint):
    """Identify a CAT coin and verify ownership via *hint*.

    *puzzle_program* is either the coin's own puzzle (spent) or the parent
    puzzle (unspent).  In both cases we can extract the tail and reconstruct
    ``CAT_MOD.curry(CAT_MOD_HASH, tail, hint)``.  If the reconstructed tree
    hash equals ``coin.coin.puzzle_hash`` the coin is verified as ours."""
    mod, curried_args = puzzle_program.uncurry()
    mod_hash_hex = mod.get_tree_hash().hex()
    mod_name = _puzzle_name_from_hash(mod_hash_hex)

    if not mod_name.endswith('cat_v2'):
        return None

    # curried_args = (cat_mod_hash, tail_program, inner_puzzle)
    args = list(curried_args.as_iter())
    if len(args) < 3:
        return None
    tail_program = args[1]
    inner_puzzle = args[2]

    # For a spent coin, puzzle_program IS the coin's own puzzle reveal.
    # Verify ownership by checking if the inner puzzle hash matches the hint.
    if hint is not None and inner_puzzle.get_tree_hash() == hint:
        return {
            'type': 'CAT',
            'verified': True,
            'detail': {
                'asset_id': tail_program.get_tree_hash().hex(),
                'inner_puzzle_hash': hint.hex()
            }
        }

    # Fallback: try reconstructing with hint as inner puzzle (for cases where
    # we got the full inner puzzle program rather than just the hash)
    try:
        tail_program = tail_program.get_tree_hash()
        print(f"[CAT DEBUG] mod type: {type(mod)}")
        print(f"[CAT DEBUG] tail_program type: {type(tail_program)}")
        print(f"[CAT DEBUG] tail_program value: {tail_program}")
        print(f"[CAT DEBUG] hint type: {type(hint)}")
        print(f"[CAT DEBUG] hint value: {hint}")

        reconstructed = mod.curry(mod, tail_program, hint)
        if reconstructed is None:
            return None

        print('reconstructed')
        print(reconstructed.get_tree_hash())
        print('puzzle hash')
        print(coin.coin.puzzle_hash)
        if reconstructed.get_tree_hash() != coin.coin.puzzle_hash:
            return None  # hint does not match this CAT

        return {
            'type': 'CAT',
            'verified': True,
            'detail': {
                'asset_id': tail_program.get_tree_hash().hex(),
                'inner_puzzle_hash': hint.hex() if hint else None
            }
        }
    except Exception:
        return None


# ------------------------------------------------------------------------------
# NFT checker
# ------------------------------------------------------------------------------
@_register_type_checker
def _check_nft_type(coin, puzzle_program, hint):
    """Check if *puzzle_program* is a singleton NFT and the hint owns it."""
    # --- step 1: outer layer must be singleton top-layer ---
    mod, curried_args = puzzle_program.uncurry()
    mod_hash = mod.get_tree_hash().hex()
    mod_name = _puzzle_name_from_hash(mod_hash)
    if not mod_name.endswith('singleton_top_layer_v1_1'):
        return None

    # --- step 2: inner layer must be NFT state layer ---
    singleton_args = list(curried_args.as_iter())
    if len(singleton_args) < 2:
        return None
    inner_puzzle = singleton_args[1]
    inner_mod, inner_args = inner_puzzle.uncurry()
    inner_mod_hash = inner_mod.get_tree_hash().hex()
    inner_mod_name = _puzzle_name_from_hash(inner_mod_hash)
    if not inner_mod_name.endswith('nft_state_layer'):
        return None

    # --- step 3: amount must be odd (1-mojo NFT) ---
    if coin.coin.amount % 2 == 0:
        return None

    # --- step 4: extract the p2 puzzle hash from the innermost layer ---
    # inner_args of NFT state layer tends to be:
    #   (nft_mod_hash, metadata, updater, innermost_puzzle)
    # innermost_puzzle might itself be wrapped by NFT_OWNERSHIP_LAYER for DID-linked NFTs.
    state_args = list(inner_args.as_iter())
    if len(state_args) < 4:
        return None
    innermost_puzzle = state_args[3]
    im_mod, im_args = innermost_puzzle.uncurry()
    im_mod_hash = im_mod.get_tree_hash().hex()
    im_mod_name = _puzzle_name_from_hash(im_mod_hash)
    if im_mod_name.endswith('nft_ownership_layer'):
        # DID-linked NFT – unwrap once more
        ownership_args = list(im_args.as_iter())
        if len(ownership_args) < 1:
            return None
        p2_puzzle = ownership_args[0]
    else:
        p2_puzzle = innermost_puzzle

    p2_puzzle_hash = p2_puzzle.get_tree_hash()

    # --- step 5: verify the hint matches the p2 puzzle hash ---
    verified = (hint is not None and p2_puzzle_hash == hint)

    return {
        'type': 'NFT',
        'verified': verified,
        'detail': {'p2_puzzle_hash': p2_puzzle_hash.hex()}
    }


# ------------------------------------------------------------------------------
# Standard transaction (XCH / P2) checker
# ------------------------------------------------------------------------------
@_register_type_checker
def _check_standard_type(coin, puzzle_program, hint):
    """Identify a standard (XCH) P2 transaction and verify via *hint*."""
    mod, curried_args = puzzle_program.uncurry()
    mod_hash = mod.get_tree_hash().hex()
    mod_name = _puzzle_name_from_hash(mod_hash)
    if not mod_name.endswith('p2_delegated_puzzle_or_hidden_puzzle'):
        return None

    # For standard P2 the hint should equal the coin puzzle hash.
    verified = (hint is not None and coin.coin.puzzle_hash == hint)

    return {
        'type': 'XCH',
        'verified': verified,
        'detail': {
            'puzzle_hash': coin.coin.puzzle_hash.hex(),
            'checker': 'standard_p2'
        }
    }


def make_sql_fetcher(table, sorting_column=None):
    # NB:
    # it is not clear, if you use sorting_column the start, count are min and max height
    # sorting in sql is not use, sorting means only on which column apply start and count
    def fetch(conn, start, count, filters=None, order='ASC'):
        """ order is not implemented... """
        if not filters:
            filters = {}

        where_clauses = []
        values = []

        for filter, val in filters.items():
            where_clauses.append(f"{filter} = ?")
            values.append(val)

        if sorting_column is not None:
            range_sql = f"{sorting_column} >= ? AND {sorting_column} < ?"
            where_sql = f"WHERE {' AND '.join(where_clauses)} AND {range_sql}" if filters else f"WHERE {range_sql}"
            values.extend([start, start + count])
        else:
            range_sql = 'LIMIT ? OFFSET ?'
            where_sql = f"WHERE {' AND '.join(where_clauses)} {range_sql}" if filters else f"{range_sql}"
            values.extend([count, start])


        cur = conn.cursor()
        query = f"SELECT * FROM {table} {where_sql}"
        #print(query)
        #print(values)
        #query = f"SELECT * FROM {table} {where_sql} ORDER BY {sorting_column} LIMIT ? OFFSET ?"

        cur.execute(query, values)
        items = cur.fetchall()
        return items

    return fetch


def make_sql_fetcher_range(table, sorting_column="id"):
    def fetch(conn, start, count, filters=None, order='ASC'):
        if not filters:
            filters = {}

        where_clauses = []
        values = []

        for filter, val in filters.items():
            where_clauses.append(f"{filter} = ?")
            values.append(val)

        values = list(range(start, start + count))
        range_sql = f"{sorting_column} in ({', '.join(['?'] * count)})"

        where_sql = f"WHERE {' AND '.join(where_clauses)} AND {range_sql}" if filters else f"WHERE {range_sql}"

        cur = conn.cursor()
        query = f"SELECT * FROM {table} {where_sql}"
        #print(f"questy: {query}")
        #print(f"valuesty: {values}")
        cur.execute(query, values)
        items = cur.fetchall()
        return items

    return fetch


def make_sql_fetcher_range_M(table, sorting_column="id"):
    def fetch(conn, start, count, filters={}, order='ASC'):

        where_clauses = []
        values = [start, start + count]

        for filter, val in filters.items():
            where_clauses.append(f"{filter} = ?")
            values.append(val)

        range_sql = f"{sorting_column} >= ? AND {sorting_column} < ?"

        where_sql = f"WHERE {' AND '.join(where_clauses)} AND {range_sql}" if filters else f"WHERE {range_sql}"

        cur = conn.cursor()
        query = f"SELECT * FROM {table} {where_sql}"
        #print(f"questy: {query}")
        #print(f"valuesty: {values}")
        cur.execute(query, values)
        items = cur.fetchall()
        return items

    return fetch


def make_sql_fetcher_first_last_element(table, sorting_column=None):
    def fetch(conn, filters={}, order='ASC'):

        where_clauses = []
        values = []

        for filter, val in filters.items():
            where_clauses.append(f"{filter} = ?")
            values.append(val)

        where_sql = f" WHERE {' AND '.join(where_clauses)} " if filters else ""

        if sorting_column is not None:
            query = f"SELECT * FROM {table} {where_sql} ORDER BY {sorting_column} {order} LIMIT 1"
        else:
            query = f"SELECT * FROM {table} {where_sql} ORDER BY 1 {order} LIMIT 1"  # use the first column

        cur = conn.cursor()
        cur.execute(query, values)
        return cur.fetchall()

    return fetch



@dataclass
class Chunk:
    chunk_idx: int  # idx of the chunk
    first_idx: int  # idx of the first element of the chunk
    chunk_size: int
    data: list

    def __post_init__(self):
        """ It make the data len equal to the chunk size """
        if len(self.data) < self.chunk_size:
            self.data.extend([None] * (self.chunk_size - len(self.data)))

    def is_full(self):
        valid_items = 0
        for i in self.data:
            if i is not None:
                valid_items += 1

        return True if valid_items == self.chunk_size else False


def refresh_cache_address_info(cache_conn, puzzle_hash):
    """Recompute balance and counts of an address from the node DB (slow on big addresses)"""
    balance, unspent_coin_count, total_coin_count, peak_height = \
        FetchMaker.get_total_amount_and_count_from_puzzle_hash(CONF.DB_BLOCKCHAIN_RO, puzzle_hash)
    unspent_hinted_coin_count, total_hinted_coin_count = \
        FetchMaker.get_hinted_amount_and_type_count_from_puzzle_hash(CONF.DB_BLOCKCHAIN_RO, puzzle_hash)
    insert_cache_address_info(cache_conn, puzzle_hash, peak_height, balance, total_coin_count,
                              unspent_coin_count, total_hinted_coin_count, unspent_hinted_coin_count)


class CacheUpdater:
    """Keeps all the followed addresses of the cache up to date, with one pass per new block
       over the coins created and spent in the new blocks.
       An address is followed after its first build (FetchMaker.cache_fetcher), see follow()."""
    WINDOW = 100        # blocks per pass, so a long gap is read in pieces
    REORG_DEPTH = 32    # blocks rolled back when the last synced block is not in the main chain anymore

    def __init__(self):
        self.followed: set = set()
        self.lock = threading.Lock()  # one pass at a time
        self.memo_lock = threading.Lock()
        self.after_sync = {}  # name -> callback, called once after the next pass

    def start(self, puzzle_hashes_to_build=()):
        """Load the followed addresses, bring them to the node peak, then build and follow
           the given addresses not followed yet (watchlist and old caches). Run it in a thread."""
        cache_conn = get_connection(CONF.DB_CACHED_BLOCKCHAIN)
        try:
            self.followed = {bytes(row[0]) for row in
                             cache_conn.execute("SELECT puzzle_hash FROM cached_followed").fetchall()}
        finally:
            cache_conn.close()
        logging(debug_logger, "DEBUG", f"CACHE UPDATER following {len(self.followed)} addresses")

        self.sync()

        for puzzle_hash in puzzle_hashes_to_build:
            puzzle_hash = bytes(puzzle_hash)
            if puzzle_hash in self.followed:
                continue
            try:
                self.build_and_follow(puzzle_hash)
            except Exception:
                UTILS.logging_traceback("CACHE UPDATER BUILD")

    def clear(self):
        """Empty the cache DB and stop following every address. It waits for the running pass
           and memo fetch, so nothing is written while the tables are emptied"""
        with self.lock, self.memo_lock:
            cache_conn = get_connection(CONF.DB_CACHED_BLOCKCHAIN)
            try:
                clear_cache_db(cache_conn)
            finally:
                cache_conn.close()
            self.followed = set()
        logging(debug_logger, "DEBUG", "CACHE UPDATER cache cleared")

    def remove(self, puzzle_hash):
        """Delete one address from the cache DB and stop following it, like clear()"""
        puzzle_hash = bytes(puzzle_hash)
        with self.lock, self.memo_lock:
            cache_conn = get_connection(CONF.DB_CACHED_BLOCKCHAIN)
            try:
                delete_cache_address(cache_conn, puzzle_hash)
            finally:
                cache_conn.close()
            self.followed.discard(puzzle_hash)
        logging(debug_logger, "DEBUG", f"CACHE UPDATER removed {puzzle_hash.hex()}")

    def is_followed(self, puzzle_hash) -> bool:
        return bytes(puzzle_hash) in self.followed

    def node_peak(self, db_conn):
        return db_conn.execute(
            "SELECT height, header_hash FROM full_blocks WHERE in_main_chain = 1 "
            "ORDER BY height DESC LIMIT 1").fetchone()

    def build_and_follow(self, puzzle_hash):
        """First build of an address, then follow it"""
        db_conn = get_connection(CONF.DB_BLOCKCHAIN_RO)
        cache_conn = get_connection(CONF.DB_CACHED_BLOCKCHAIN)
        try:
            built_height = self.node_peak(db_conn)[0]
            FetchMaker.cache_fetcher(db_conn, cache_conn, puzzle_hash)
            refresh_cache_address_info(cache_conn, puzzle_hash)
            self.follow(puzzle_hash, built_height)
            FetchMaker.memo_fetcher(cache_conn, puzzle_hash, sleep_between_calls=0.05)
        finally:
            cache_conn.close()
            db_conn.close()

    def follow(self, puzzle_hash, built_height: int):
        """Start following an address whose first build read the node up to built_height.
           The blocks between its build and the updater are read for this address only."""
        puzzle_hash = bytes(puzzle_hash)
        with self.lock:
            if puzzle_hash in self.followed:
                return
            db_conn = get_connection(CONF.DB_BLOCKCHAIN_RO)
            cache_conn = get_connection(CONF.DB_CACHED_BLOCKCHAIN)
            try:
                state = cache_conn.execute("SELECT height FROM cached_sync_state").fetchone()
                if state is None:
                    # first followed address, the updater starts from its build
                    self.save_state(cache_conn, built_height, None)
                    sync_height = built_height
                else:
                    sync_height = state[0]

                height = built_height
                while height < sync_height:
                    to_height = min(height + self.WINDOW, sync_height)
                    deltas = FetchMaker.cache_sync_range(db_conn, cache_conn, {puzzle_hash}, height, to_height)
                    self.apply_deltas(cache_conn, deltas, height, to_height)
                    cache_conn.commit()
                    height = to_height

                cache_conn.execute("INSERT OR IGNORE INTO cached_followed (puzzle_hash) VALUES (?)",
                                   (puzzle_hash,))
                cache_conn.commit()
                self.followed.add(puzzle_hash)
                logging(debug_logger, "DEBUG", f"CACHE UPDATER follow {puzzle_hash.hex()} from {built_height}")
            finally:
                cache_conn.close()
                db_conn.close()

    def on_new_block(self, data):
        """Daemon NEW_BLOCK callback"""
        if not data['data']['transaction_block']:
            return
        self.sync()

    def sync(self):
        """Bring the followed addresses to the node peak"""
        # a pass is already running: it or the next block will cover this one
        if not self.lock.acquire(blocking=False):
            return
        changed = set()
        try:
            db_conn = get_connection(CONF.DB_BLOCKCHAIN_RO)
            cache_conn = get_connection(CONF.DB_CACHED_BLOCKCHAIN)
            try:
                state = cache_conn.execute("SELECT height, header_hash FROM cached_sync_state").fetchone()
                if state is not None and self.followed:
                    height, header_hash = state
                    reorg = header_hash is not None and not self.in_main_chain(db_conn, header_hash)
                    if reorg:
                        height = self.rollback(cache_conn, max(height - self.REORG_DEPTH, 0))
                    changed = self.advance(db_conn, cache_conn, height)
                    if reorg:
                        # the balances had the deltas of the orphaned blocks
                        for puzzle_hash in self.followed:
                            refresh_cache_address_info(cache_conn, puzzle_hash)
            finally:
                cache_conn.close()
                db_conn.close()
        except Exception:
            UTILS.logging_traceback("CACHE UPDATER")
        finally:
            self.lock.release()

        callbacks, self.after_sync = self.after_sync, {}
        for callback in callbacks.values():
            try:
                callback()
            except Exception:
                UTILS.logging_traceback("CACHE UPDATER CALLBACK")

        if changed:
            self.fetch_memos(changed)

    def advance(self, db_conn, cache_conn, height):
        peak_height, peak_hash = self.node_peak(db_conn)
        changed = set()
        while height < peak_height:
            to_height = min(height + self.WINDOW, peak_height)
            deltas = FetchMaker.cache_sync_range(db_conn, cache_conn, self.followed, height, to_height)
            self.apply_deltas(cache_conn, deltas, height, to_height)
            changed |= deltas.keys()
            to_hash = db_conn.execute(
                "SELECT header_hash FROM full_blocks WHERE height = ? AND in_main_chain = 1",
                (to_height,)).fetchone()[0]
            self.save_state(cache_conn, to_height, to_hash)
            # commit per window: an interrupted pass restarts from the last window, no gaps
            cache_conn.commit()
            height = to_height
        if changed:
            logging(debug_logger, "DEBUG", f"CACHE UPDATER synced to {height}, {len(changed)} addresses changed")
        return changed

    @staticmethod
    def apply_deltas(cache_conn, deltas, from_height, to_height):
        """Add the changes of the range to the address info. An info computed after from_height
           (a new search recomputes it) already has them, so it is left as it is"""
        for puzzle_hash, (balance, total, unspent) in deltas.items():
            cache_conn.execute(
                "UPDATE cached_address_info SET "
                "balance = balance + ?, total_coin_count = total_coin_count + ?, "
                "unspent_coin_count = unspent_coin_count + ?, last_height = ? "
                "WHERE puzzle_hash = ? AND last_height <= ?",
                (balance, total, unspent, to_height, puzzle_hash, from_height))

    def fetch_memos(self, puzzle_hashes):
        """Memos of the new coins, through the RPC. Skipped if a previous one is still running,
           memo_fetcher resumes from where it arrived"""
        if not self.memo_lock.acquire(blocking=False):
            return
        cache_conn = get_connection(CONF.DB_CACHED_BLOCKCHAIN)
        try:
            for puzzle_hash in puzzle_hashes:
                FetchMaker.memo_fetcher(cache_conn, puzzle_hash, sleep_between_calls=0.05)
        except Exception:
            UTILS.logging_traceback("CACHE UPDATER MEMO")
        finally:
            cache_conn.close()
            self.memo_lock.release()

    @staticmethod
    def in_main_chain(db_conn, header_hash):
        row = db_conn.execute("SELECT in_main_chain FROM full_blocks WHERE header_hash = ?",
                              (header_hash,)).fetchone()
        return bool(row and row[0])

    def rollback(self, cache_conn, fork_height):
        """Undo everything above fork_height, the next advance reads it again from the node"""
        logging(debug_logger, "DEBUG", f"CACHE UPDATER reorg, rolling back to {fork_height}")
        cache_conn.execute("DELETE FROM cached_coin_record WHERE confirmed_index > ?", (fork_height,))
        cache_conn.execute("UPDATE cached_coin_record SET spent_index = 0, child_count = 0 "
                           "WHERE spent_index > ?", (fork_height,))
        cache_conn.execute("UPDATE cached_memo_progress SET last_confirmed_index = "
                           "MIN(last_confirmed_index, ?)", (fork_height,))
        self.save_state(cache_conn, fork_height, None)
        cache_conn.commit()
        return fork_height

    @staticmethod
    def save_state(cache_conn, height, header_hash):
        cache_conn.execute("INSERT OR REPLACE INTO cached_sync_state (id, height, header_hash) "
                           "VALUES (0, ?, ?)", (height, header_hash))


@dataclass
class Fork:
    """A branch of blocks that left the main chain: from the orphaned tip down to the
    main chain block it starts from. With depth 1 it can also be a block that lost the
    race and was never the peak of the node"""
    tip_hash: bytes
    tip_height: int
    fork_height: int  # the last block shared with the main chain
    orphaned_blocks: int
    timestamp: int = None  # of the main chain transaction block at the tip height or under it

    @property
    def depth(self):
        return self.tip_height - self.fork_height


class ReorgScanner:
    """Find the forks in the node DB: the blocks of full_blocks with in_main_chain = 0.
    The first scan reads the whole table (no index on in_main_chain = 0, ~30 sec cold),
    the next ones only the last blocks, with the height index"""
    RESCAN_DEPTH = 64  # a reorg can flip the main chain blocks under the last scanned height

    def __init__(self):
        self.lock = threading.Lock()
        self.orphans = {}  # header_hash -> (height, prev_hash)
        self.timestamps = {}  # tip_hash -> timestamp, they do not change
        self.scanned_height = None  # main chain peak at the last scan
        self.forks: list[Fork] = []
        self.status = 'not started'
        self.error = None
        self.last_scan = 0

    def refresh(self):
        """Scan the node DB, one scan at a time. Returns False if a scan is already running"""
        if not self.lock.acquire(blocking=False):
            return False
        try:
            self.status = 'scanning the whole node DB' if self.scanned_height is None else 'scanning the last blocks'
            db_conn = get_connection(CONF.DB_BLOCKCHAIN_RO)
            try:
                self._scan(db_conn)
            finally:
                db_conn.close()
            self.error = None
            self.status = 'done'
        except Exception as e:
            UTILS.logging_traceback("REORG SCANNER")
            self.error = f"reorg scan error: {e}"
            self.status = 'error'
        finally:
            self.last_scan = time.time()
            self.lock.release()
        return True

    def _scan(self, db_conn):
        peak = db_conn.execute("SELECT max(height) FROM full_blocks WHERE in_main_chain = 1").fetchone()[0] or 0
        if self.scanned_height is None:
            rows = db_conn.execute("SELECT header_hash, prev_hash, height FROM full_blocks "
                                   "WHERE in_main_chain = 0").fetchall()
            orphans = {}
        else:
            from_height = max(self.scanned_height - self.RESCAN_DEPTH, 0)
            rows = db_conn.execute("SELECT header_hash, prev_hash, height FROM full_blocks "
                                   "WHERE height > ? AND in_main_chain = 0", (from_height,)).fetchall()
            # the blocks above from_height are read again, also the ones back in the main chain
            orphans = {h: v for h, v in self.orphans.items() if v[0] <= from_height}
        for header_hash, prev_hash, height in rows:
            orphans[bytes(header_hash)] = (height, bytes(prev_hash))

        # a fork for each orphan that is not the parent of another orphan
        parents = {prev_hash for height, prev_hash in orphans.values() if prev_hash in orphans}
        forks = []
        for tip_hash, (tip_height, prev_hash) in orphans.items():
            if tip_hash in parents:
                continue
            count = 1
            base_height = tip_height
            while prev_hash in orphans:
                base_height, prev_hash = orphans[prev_hash]
                count += 1
            fork = Fork(tip_hash, tip_height, base_height - 1, count)
            if tip_hash not in self.timestamps:
                self.timestamps[tip_hash] = self._timestamp_at(db_conn, tip_height)
            fork.timestamp = self.timestamps[tip_hash]
            forks.append(fork)
        forks.sort(key=lambda f: f.tip_height, reverse=True)

        self.orphans = orphans
        self.forks = forks
        self.scanned_height = peak

    @staticmethod
    def _timestamp_at(db_conn, height):
        """Timestamp of the main chain transaction block at height or the closest one under it"""
        rows = db_conn.execute("SELECT block_record FROM full_blocks WHERE in_main_chain = 1 "
                               "AND height <= ? AND height > ? ORDER BY height DESC",
                               (height, height - 50)).fetchall()
        for (raw,) in rows:
            timestamp = BlockRecord.from_bytes(raw).timestamp
            if timestamp is not None:
                return int(timestamp)
        return None


REORG_SCANNER = ReorgScanner()


class DataChunkLoader:
    def __init__(self, db_path: str, table_name: str, chunk_size: int, fetch_fun: callable,
                 fetch_first_last_count_fun: callable, offset: int = 0, sorting_column=None,
                 row_offset=False, filters={}, data_struct=None):
        """offset = distance from the beging of the array of elements
           filters = a dic with filter and value. EG. {'pk_state_id': 2, 'other_filter': 'yellow'}
           row_offset: bool; use the row number to select item, instead of the value of the sorting column (NOT IMPLEMENTED: at the moment
           this behaviour is granted by soting_column=None)
           it is supposed that the chunk is small enough to not degrade performance using not indexed filters"""

        self.db_path = db_path
        conn = self.create_sql_conneciton()

        self.table_name = table_name
        self.total_row_count = None
        #self.idx_last_item = None  # if there are double elements, this it could be different from the total row count
        self.last_item = None  # raw values of the last item. If double, only the first one is taken
        self.sorting_column = sorting_column
        self.lock = threading.Lock()
        self.current_offset: int = offset
        self.chunk_size: int = chunk_size
        self.chunk_arena_size = 5  # n. of chunks kept in memory
        self.chunk_arena: list[Chunk] = [None] * self.chunk_arena_size
        self.main_chunk_pointer: int = 0
        #self.fetcher = make_sql_fetcher(table_name, self.sorting_column)
        #self.fetcher_first_last = make_sql_fetcher_first_last_element(table_name, self.sorting_column)
        self.fetcher = fetch_fun
        self.fetcher_first_last_count = fetch_first_last_count_fun
        ### TODO: move the struct conversion in the FetchMaker
        self.data_struct = data_struct
        #self.filters = filters

        self.update_loader_thread = None

        self.update_total_row_count(conn)
        #self.update_idx_last_item(conn)
        self.update_last_item(conn)

        # fetch_main chunk
        self.chunk_arena[self.main_chunk_pointer] = self.fetch_chunk(conn, self.current_offset)
        if (self.current_offset - self.chunk_size) >= 0:
            pre_chunk_pointer = (self.main_chunk_pointer - 1) % self.chunk_arena_size
            self.chunk_arena[pre_chunk_pointer] = self.fetch_chunk(conn, self.current_offset - self.chunk_size)
        post_chunk_pointer = (self.main_chunk_pointer + 1) % self.chunk_arena_size
        self.chunk_arena[post_chunk_pointer] = self.fetch_chunk(conn, self.current_offset + self.chunk_size)

        conn.close()

    def create_sql_conneciton(self):
        return sqlite3.connect(self.db_path, uri=True, timeout=SQL_TIMEOUT)

    def update_offset(self, offset: int):
        with self.lock:
            self.current_offset = offset

        # check if the new offset is still in the cache, if not fetch it
        current_chunk_idx = self.get_current_chunk().chunk_idx
        new_current_chunk_idx = self.current_offset // self.chunk_size

        # update cache if outside
        if abs(current_chunk_idx - new_current_chunk_idx) > 1:
            conn = self.create_sql_conneciton()

            # fetch the whole chunk
            ##fetched_chunk = self.fetch_chunk(conn, self.current_offset)

            # fetch the only the offset item in the chunk
            fetched_chunk = self.fetch_only_current_offset(conn)

            with self.lock:
                self.main_chunk_pointer = 2  # arbitrarly start from the middle chunk
                self.chunk_arena[self.main_chunk_pointer] = fetched_chunk

    # probably it is very slow
    def update_total_row_count(self, conn):
        total_row_count, _, _ = self.fetcher_first_last_count(conn)
        with self.lock:
            self.total_row_count = total_row_count
        return total_row_count

    #def update_idx_last_item(self, conn):
    #    """ Return the highest value of the sorted columns, it can differs from 
    #    the total_row_count in case of double entries"""
    #    self.idx_last_item = self.fetcher(conn, 1, 1, self.filters, 'DESC')
    #    return self.idx_last_item

    def update_last_item(self, conn):
        _, _, last_item = self.fetcher_first_last_count(conn)
        if last_item:
            with self.lock:
                self.last_item = last_item
        else:
            self.last_item = None
        return self.last_item

    def fetch_db(self, conn, start, count):
        return self.fetcher(conn, start, count)

    def fetch_chunk(self, conn, data_index):
        chunk_idx = data_index // self.chunk_size
        chunk_first_idx = chunk_idx * self.chunk_size
        # chunk_last_idx = chunk_first_idx + self.chunk_size
        data = self.fetch_db(conn, chunk_first_idx, self.chunk_size)
        ### TODO: move the struct conversion in the FetchMaker
        if self.data_struct is not None:
            sturctured_data = []
            for d in data:
                sturctured_data.append(self.data_struct(d))
            data = sturctured_data

        return Chunk(chunk_idx, chunk_first_idx, self.chunk_size, data)

    def fetch_only_current_offset(self, conn):
        chunk_idx = self.current_offset // self.chunk_size
        chunk_first_idx = chunk_idx * self.chunk_size

        data_offset = self.fetch_db(conn, self.current_offset, 1)
        if self.data_struct is not None:
            data_offset = self.data_struct(data_offset[0])

        data = [None] * self.chunk_size
        offset_local_idx = self.current_offset - chunk_first_idx
        data[offset_local_idx] = data_offset

        return Chunk(chunk_idx, chunk_first_idx, self.chunk_size, data)


    def fetch_item_chunk(self, data_index):
        """Fetch a particular item only if its chunk is already in the cache,
        Return False if the related chunk is not in the cache"""
        conn = self.create_sql_conneciton()
        with self.lock:
            chunk_idx = data_index // self.chunk_size
            chunk_first_idx = chunk_idx * self.chunk_size
            # check if the chunk is in the cache
            for chunk in self.chunk_arena:
                if chunk is not None and chunk.chunk_idx == chunk_idx:
                    item_local_idx = data_index % self.chunk_size
                    if chunk.data[item_local_idx] is not None:
                        # already present
                        conn.close()
                        return True
                    data = self.fetch_db(conn, data_index, 1)
                    if self.data_struct is not None:
                        data = self.data_struct(data[0],False)
                    item_local_idx = data_index % self.chunk_size
                    chunk.data.insert(item_local_idx, data)
                    conn.close()
                    return True
            conn.close()
            return False


    def update_current_chunk_pointer(self):
        current_chunk_idx = self.get_current_chunk().chunk_idx

        # DEBUG
        current_chunk_idx = self.get_current_chunk().chunk_idx
        new_current_chunk_idx = self.current_offset // self.chunk_size

        if abs(current_chunk_idx - new_current_chunk_idx) > 1:
            raise "The offset is not in a consecutive chunk"

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
            if pre_chunk and pre_chunk.chunk_idx < current_chunk.chunk_idx:
                data.extend(pre_chunk.data)
                chunk_idx = pre_chunk.chunk_idx
            else:
                chunk_idx = current_chunk.chunk_idx
            data.extend(current_chunk.data)
            if post_chunk:
                data.extend(post_chunk.data)

            # deep copy of the nested lists
            deep_data = copy.deepcopy(data)

            return deep_data, chunk_idx * self.chunk_size

    def start_updater_thread(self):
        with self.lock:
            if self.update_loader_thread is None or not self.update_loader_thread.is_alive():
                self.update_loader_thread = threading.Thread(target=self.update_loader, daemon=True)
                self.update_loader_thread.start()

    def update_loader(self):
        conn = self.create_sql_conneciton()
        self.update_total_row_count(conn)

        # read chunks data
        with self.lock:
            # update total row and current chunk
            self.update_current_chunk_pointer()
            current_chunk: Chunk = self.get_current_chunk()

            current_chunk_pointer = self.main_chunk_pointer % self.chunk_arena_size
            pre_chunk_pointer = (self.main_chunk_pointer - 1) % self.chunk_arena_size
            post_chunk_pointer = (self.main_chunk_pointer + 1) % self.chunk_arena_size

            pre_chunk: Chunk = self.chunk_arena[pre_chunk_pointer]
            post_chunk: Chunk = self.chunk_arena[post_chunk_pointer]

        if current_chunk is None:
            raise "can we be None? the chunk is None"

        # current chunk, fetch again if not full
        if not current_chunk.is_full():
            fetched_chunk = self.fetch_chunk(conn, self.current_offset)
            if fetched_chunk is None:
                print("fetched chunk was None")
            with self.lock:
                self.chunk_arena[current_chunk_pointer] = fetched_chunk

        # add logic to deal with empty chunks
        # post chunk
        if not post_chunk or not post_chunk.is_full() or current_chunk.chunk_idx + 1 != post_chunk.chunk_idx:
            fetched_chunk = self.fetch_chunk(conn, self.current_offset + self.chunk_size)
            with self.lock:
                self.chunk_arena[post_chunk_pointer] = fetched_chunk

        # pre chunk, do not fetch if we are at the beginning
        if current_chunk.chunk_idx > 0:
            if not pre_chunk or not pre_chunk.is_full() or current_chunk.chunk_idx - 1 != pre_chunk.chunk_idx:
                fetched_chunk = self.fetch_chunk(conn, self.current_offset - self.chunk_size)
                with self.lock:
                    self.chunk_arena[pre_chunk_pointer] = fetched_chunk
        conn.close()

    def get_current_chunk(self):
        return self.chunk_arena[self.main_chunk_pointer]



if __name__ == "__main__":


    # hash

    db_path = "/mnt/chiaDB/mainnet/db/blockchain_v2_mainnet.sqlite"
    # read only read
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)

    height = 8568188
    query = "SELECT block FROM full_blocks WHERE height = ?"
    cursor = conn.cursor()
    cursor.execute(query, (height,))
    row = cursor.fetchall()

    print(row)
    print(len(row))
    exit()


    hash = "0x186c2aeb854c599627c4c7268a7e3f99bae52bde15768093aa6cf7a0642f65e5"
    hash = "186c2aeb854c599627c4c7268a7e3f99bae52bde15768093aa6cf7a0642f65e5"
    hash = bytes32.fromhex(hash)
    table = 'full_blocks'
    sorting_column = 'height'
    fetcher = make_sql_fetcher(table, sorting_column)
    obj = fetcher(conn, 0, 12_000_000, filters={'header_hash': hash})
    #obj = fetcher(conn, 0, 2, filters={'height': 100})
    print(obj)
    fetcher = make_sql_fetcher(table)
    obj = fetcher(conn, 0, 1, filters={'header_hash': hash})
    print(len(obj))
    print(obj)

    #test NFT
    coins = [
        ('1aefa2cd07cf5fd091f68226f9fc76acebb926d256f30e0a623bf7e41d0a5d8b', 6048761),  # orange with no delegated at the end
        ('40c6b2e7b86991873f63367102ad72224a42108bb6318da8d901e32637c99adb', 5868512),
        ('64be88280bca492c4729ddfc8bb00c17c6f25413cd1ad6754e1973b5c56ab8c9', 8061050),
        ('7781b5651c67fc2917c8fa6967fdb9fd81915a8abef5d34cd0b0e48e447a3f6a', 7714734),  # donald tre
        ('aed02d1208b2c137867f18b86ff7c7236b693f8968b1a10c2c99c5a85c49c777', 6712403),

    ]




    from chia_puzzles_py.programs import CAT_PUZZLE, NFT_STATE_LAYER
    CAT_MOD = PyProgram.from_bytes(CAT_PUZZLE)
    NFT_STATE_LAYER_MOD = PyProgram.from_bytes(NFT_STATE_LAYER)

    print("#############################################")
    print("#############################################")
    print("#############################################")
    print("#############################################")
    print("#############################################")

    for c, s in coins:
        out = RPC.call_rpc_node('get_puzzle_and_solution', coin_id=c, height=s)

        puzzle = PyProgram.fromhex(out['puzzle_reveal'])
        solution = PyProgram.fromhex(out['solution'])

        # 2. Run the puzzle with the solution (returns cost and conditions)
        # The 'run' method executes the CLVM code
        max_cost = 11_000_000_000
        try:
            cost, result = puzzle.run_with_cost(max_cost, solution)
        except Exception as e:
            print(f"Failed to run puzzle: {e}")

        # 3. Parse the result into a list of conditions
        # result is a Program object representing the list of conditions
        for condition in result.as_iter():
            cond_list = condition.as_python()
            opcode = cond_list[0]

            # Check for opcode 51 (CREATE_COIN)
            if opcode == ConditionOpcode.CREATE_COIN:
                # Format: (51 puzzle_hash amount [memos])
                if len(cond_list) > 3:
                    memos = cond_list[3]
                    print(f"Target: {cond_list[1].hex()} | Amount: {int.from_bytes(cond_list[2], 'big')}")
                    for memo in memos:
                        print(f"  -> Found Memo: {memo.hex()}")
                else:
                    print(f"Target: {cond_list[1].hex()} - No memos present.")

        base_mod, args = puzzle.uncurry()
        if base_mod == CAT_MOD:
            print("IT IS A CAT")
        elif base_mod == NFT_STATE_LAYER_MOD:
            print("THIS IS A EWAL NFT")
        else:
            print("Standard or Other... BOOORINGGG")

        name = PUZ.compare_to_known_puzzles(base_mod.get_tree_hash().hex())
        print(name)
        print(puzzle.get_tree_hash().hex())

        unroll_puzzles = PUZ.unroll_puzzle_to_nodes(puzzle)
        print("LEVELLL")
        print("LEVELLL")
        UTILS.print_json(unroll_puzzles)
        print("####LEVELLL'#####")
        print("####LEVELLL'#####")
        names, hashes = PUZ.unroll_puzzle_to_names(puzzle)

        for n, h in zip(names, hashes):
            print(f"{n.upper()} with hash; {h}")

        puzzle_type, name = PUZ.compare_unrolled_puzzle_to_known_layered_puzzles(hashes)
        print(f"THE NAME: {name}")
        for i in unroll_puzzles:
            print(i)

    def is_hex_bytes(s: str) -> bool:
        if not isinstance(s, str):
            return False
        s = s.removeprefix("0x")
        return len(s) % 2 == 0 and all(c in "0123456789abcdefABCDEF" for c in s)

    def classify_number(s: str):
        if not isinstance(s, str) or not s:
            return "invalid"

        # decimal int (no prefix)
        if s.isdigit():
            return "int"

        # hex (with or without 0x)
        t = s.removeprefix("0x").removeprefix("0X")
        if t and all(c in "0123456789abcdefABCDEF" for c in t):
            return "hex"

        return "invalid"


    hash = "0x186c2aeb854c599627c4c7268a7e3f99bae52bde15768093aa6cf7a0642f65e5"
    print(is_hex_bytes(hash))
    print(classify_number(hash))
    hash = "1234"
    print(is_hex_bytes(hash))
    print(classify_number(hash))
    hash = "186c2aeb854c599627c4c7268a7e3f99bae52bde15768093aa6cf7a0642f65e5"
    print(is_hex_bytes(hash))
    print(classify_number(hash))
    hash = "186c22eb854c599627c4c7268a7e3f99bae52bde15768093aa6cf7a0642f65e5"
    print(3, " ", is_hex_bytes(hash))
    print(classify_number(hash))
    hash = "186c2aeb8k4c599627c4c7268a7e3f99bae52bde15768093aa6cf7a0642f65e5"
    print(is_hex_bytes(hash))
    print(classify_number(hash))
    hash = "186c2aeb854c599627c4c7268a7e3f99bae52bde15768093aa6cf7a0642f65e5"
    hash = bytes32.fromhex(hash)
    print(is_hex_bytes(hash))
    print(classify_number(hash))

    print(obj[0][2])

    fe = FetchMaker.block_first_last_count_fetcher(table, sorting_column)
    print(fe)
    a = fe(conn)
    print(a)
    for i in a:
        print(i)
    print(len(a))



    print("IT IS NOW")
    ACH = 'xch1lv34uumcyg892zrv35rhrx87hu5nx87em7zcag5nc2vjecupkdzspc9xn6'  # only nft
    bram = 'xch1322stwc3cw307dqnry884tu3as7jahzgxkavcqqatetqs3lkl72qhgcd7g'  # only cat
    oran = 'xch1xwapr2g9vd3tl85c8vsdpxqyq686ecqyvt6trmyua3lhcw4tch6qkqfrd0'  # nft and cat

    ACH_bytes: bytes32 = decode_puzzle_hash(bram)
    ACH_bytes: bytes32 = decode_puzzle_hash(oran)
    ACH_bytes: bytes32 = decode_puzzle_hash(ACH)
    print(ACH_bytes.hex())

    blob: bytes = bytes(ACH_bytes)

    #PUZ.unroll_puzzle_to_nodes(program)

    fetcher = FetchMaker.puzzle_hash_fetcher(blob, 'confirmed_index', 0, uint32((2**32) - 1), True)












    #i = fetcher(conn, 0, uint32((2**32) - 1))
    i = fetcher(conn, 0, 1000)


    print(i)
    print("END")
    exit()




    #def print_query_plan(connection, sql, params=()):
    #    print("--- QUERY PLAN ---")
    #    # Prepend the EXPLAIN command
    #    explain_sql = f"EXPLAIN QUERY PLAN {sql}"
    #    
    #    cursor = connection.execute(explain_sql, params)
    #    rows = cursor.fetchall()
    #    
    #    for row in rows:
    #        # row[3] is typically the 'detail' column in SQLite
    #        print(f"| {row[3]}")
    #    print("------------------\n")

    ## Usage with your CTE
    #sql_query = puzzle_hash_base_cte(True, True) + " SELECT * FROM filtered"
    #params = (b'my_puzzle_hash', 1000000, 2000000, b'my_puzzle_hash')

    #print_query_plan(src_conn, sql_query, params)











    a, b, c, _, _ = FetchMaker.get_total_amount_and_type_count_from_puzzle_hash(db_path, blob)
    print(a)
    print(b)
    print(c)
    print("ALLLAOLK")
    #a = FetchMaker.get_coins_by_hint(db_path, blob)

#    with open('watchlist.csv', 'w', newline='') as f:
#        writer = csv.writer(f)
#        # Optional: Add a header row
#        writer.writerow(["confirmed_index", "spent_index", "coinbase", "puzzle_hash", "coin_parent", "amount", "timestamp", "parent_puzzle_hash"])
#        # Write all tuples at once
#        writer.writerows(data)
#
#    print("one")
#    exit()
#

    coin_id = None
    spent_height = None
    fetcher = FetchMaker.puzzle_hash_fetcher(blob, 'confirmed_index', 0, uint32((2**32) - 1), True)
    i = fetcher(conn, 0, 100)
    for a in i:
        if a.spent_block_index != 0:
            print(a)
            spent_height = a.spent_block_index
            print(a.coin.puzzle_hash)
            address = encode_puzzle_hash(a.coin.puzzle_hash, 'xch')
            print(address)


            ########## PART copied from coin hint
            coin_name = UTILS.calc_coin_id(a.coin.parent_coin_info, a.coin.puzzle_hash, a.coin.amount)

            #coin_name = bytes32.from_bytes(i[0])
            spent_height = a.confirmed_block_index
            parent = a.coin.parent_coin_info
            puzzle = a.coin.puzzle_hash
            #amount = int_from_bytes(i[4])
            amount = a.coin.amount

            out = RPC.call_rpc_node('get_puzzle_and_solution', coin_id=parent.hex(), height=spent_height)

            puzzle_program = PyProgram.fromhex(out['puzzle_reveal'])
            solution_program = PyProgram.fromhex(out['solution'])

            # find the puzzle type
            names, hashes = PUZ.unroll_puzzle_to_names(puzzle_program)

            for n, h in zip(names, hashes):
                print(f"{n.upper()} with hash; {h}")

            puzzle_type, name = PUZ.compare_unrolled_puzzle_to_known_layered_puzzles(hashes)


            # Run the puzzle with the solution (returns cost and conditions)
            max_cost = 11_000_000_000
            try:
                cost, result = puzzle_program.run_with_cost(max_cost, solution)
            except Exception as e:
                print(f"Failed to run puzzle: {e}")

            # result is a Program object representing the list of conditions
            for condition in result.as_iter():
                cond_list = condition.as_python()
                opcode = cond_list[0]

                # Check for opcode 51 (CREATE_COIN)
                if opcode == ConditionOpcode.CREATE_COIN:
                    # Format: (51 puzzle_hash amount [memos])
                    if len(cond_list) > 3:
                        memos = cond_list[3]
                        print(f"Target: {cond_list[1].hex()} | Amount: {int.from_bytes(cond_list[2], 'big')}")
                        for memo in memos:
                            print(f"  -> Found Memo: {memo.hex()}")
                    else:
                        print(f"Target: {cond_list[1].hex()} - No memos present.")

            unrolled = PUZ.unroll_puzzle_to_nodes(puzzle_program)
            UTILS.print_json(unrolled)
            print()
            print(name)

            break

    #print("puzzle")
    #print(parent)
    #print(puzzle)
    #print(amount)
    #import src.UTILStiller as UTILS
    #coin_name = UTILS.calc_coin_id(parent, puzzle, amount)
    #print("coin name")
    #print(coin_name)

    #import src.RPCtiller as RPC
    #import src.PUZZLEtiller as PUZ
    #out = RPC.call_rpc_node('get_puzzle_and_solution', coin_id=coin_name.hex(), height=spent_height)

    #print(out)
    #program = PyProgram.fromhex(out['puzzle_reveal'])
    #puzzle = PUZ.unroll_coin_puzzle_to_puzzle_hashes(program)
    #print(puzzle)
    #puz_name = []
    #for p in puzzle:
    #    puz_name.append(PUZ.compare_to_known_puzzles(p))

    #print("name")
    #print(puz_name)
    #from clvm_tools.binutils import assemble, disassemble
    #dd = disassemble(program)
    #print(dd)
    exit()


    # test ddos db

    table_name = 'full_blocks'
    chunk_size = 30  # height * 2  # to be sure to have at least 2 full screen of data
    offset = 100000  #34000
    sorting_column = 'height'
    filters = {'in_main_chain': 1}
    sqlite_path ="file:/mnt/chiaDB/mainnet_sync/db/blockchain_v2_mainnet.sqlite?mode=ro"
    data_loader: DataChunkLoader = DataChunkLoader(sqlite_path, table_name, chunk_size, offset, filters=filters, sorting_column=sorting_column, data_struct=BlockState)


    last_item = data_loader.get_current_item()
    print(f"last item = {last_item}")

    delta = 160

    for i in range(1000):
        data_loader.update_offset(data_loader.current_offset + delta)
        data_loader.update_loader()
        last_item = data_loader.get_current_item()
        print(f"last item = {last_item}")

        time.sleep(0.01)

    exit()











    #### test rebuild spendbundle info
    ## fee
    ## cost
    ## cost / fee

    # spend_bundle_hash = spend_bundle_hash
    # cost = json_item['cost']
    # fee = json_item['fee']
    #
    # addition_amount = json_item['npc_result']['conds']['addition_amount']
    # removal_amount = json_item['npc_result']['conds']['removal_amount']
    # additions = json_item['additions']
    # removals = json_item['removals']
    # spend_bundle = json_item['spend_bundle']
    # added_coins_count = len(self.additions)
    # removed_coins_count = len(self.removals)
    # fee_per_cost = self.fee / self.cost
    #
    # added_at = time.time()
    # removed_at = None
    # coin_types = None
    # removed_at = None
    # single_coins_with_all_type = None  # list of internal puzzle
    #
    #
    #### test spendbundle db

    with open('mempool_items.json', 'r') as f:
        meme = json.load(f)

    item_ids = list(meme['mempool_items'].keys())
    print(item_ids)
    idx = 0
    item = meme['mempool_items'][item_ids[idx]]
    print(item)

    mempool_item: MempoolItem = MempoolItem(item_ids[idx], item)
    print(mempool_item)
    print(type(mempool_item.spend_bundle))
    sp = SpendBundle.from_json_dict(mempool_item.spend_bundle)
    print("spend")
    print(sp)
    print(type(sp))



#def validate_clvm_and_signature(
#    new_spend: SpendBundle,

#    constants: ConsensusConstants,
#    peak_height: int,
#) -> tuple[SpendBundleConditions, list[tuple[bytes32, GTElement]], float]: ...

    a: SpendBundleConditions = validate_clvm_and_signature(
        sp,
        1000000000,
        DEFAULT_CONSTANTS,
        1000000000
    )

    print(a)
    print("conditions")
    print(a[0])
    a = a[0]
    print("condition cost ", a.condition_cost)
    print("execution cost ", a.execution_cost)
    print("cost ", a.cost)
    print("original cost ", mempool_item.cost)
    print(a.addition_amount)
    print(a.removal_amount)
    print("fee")
    print(a.addition_amount - a.removal_amount)
    print(a.reserve_fee)
    print('other')

    spends = a.spends

    print(f"spend conditions count: {len(spends)}")
    print(spends)
    for i in spends:
        print()
        print(i)
        print(type(i))



    print("recreate spends")

    removals_dict: dict[bytes32, Coin] = {}
    additions_dict: dict[bytes32, Coin] = {}
    addition_amount: int = 0
    removal_amount: int = 0

    for spend in a.spends:
        coin_id = bytes32(spend.coin_id)
        removals_dict[coin_id] = Coin(spend.parent_id, spend.puzzle_hash, spend.coin_amount)
        removal_amount += spend.coin_amount
        spend_additions = []
        for puzzle_hash, amount, _ in spend.create_coin:
            child_coin = Coin(coin_id, puzzle_hash, uint64(amount))
            spend_additions.append(child_coin)
            additions_dict[child_coin.name()] = child_coin
            addition_amount += child_coin.amount

    print(f"type spends {a}")
    print(f"type spend {a.spends[0]}")
    print(f"type create coin {a.spends[0].create_coin}")
    print(f"type create coin [] {a.spends[0].create_coin[0]}")

    print(f"addition amount: {addition_amount}")
    print(f"removal amount: {removal_amount}")
    print(f"removals name: {removals_dict}")
    print(f"fee: {removal_amount - addition_amount}")
    print(f"fee from the mempool item: {mempool_item.fee}")




    print('meta plinto')

    raw_sp = mempool_item.spend_bundle
    new_mem = MempoolItem(raw_json_spendbundle=raw_sp, timestamp=mempool_item.added_at)
    print('original')
    print(mempool_item)
    print("new mem")
    print(new_mem)

    exit()


    conn = sqlite3.connect(DB_SB, timeout=SQL_TIMEOUT)
    sp_db = create_spend_bundle_db(conn)
    print(sp_db)

    with open('./tests/sb_SBX-XCH_swap.json', 'r') as f:
        sp = json.load(f)

    print()
    print('swap transaction')
    sp = SpendBundle.from_json_dict(sp)
    print(sp)

    print("add SB")
    insert_spend_bundle(conn, sp)



    conn.close()
    exit()



    #### test block and double block 

    from CONFtiller import DB_WDB, SQL_TIMEOUT
    from RPCtiller import call_rpc_node
    from time import sleep
    import time
    import traceback
    import multiprocessing
    conn = sqlite3.connect(DB_WDB, timeout=SQL_TIMEOUT)

    # fing the peak
    blockchain_state = call_rpc_node('get_blockchain_state')
    height_last_block = int(blockchain_state['peak']['height'])
    print(f'peak {height_last_block}')

    # test blockchain DB
    db_path = "/mnt/chiaDB/mainnet/db/blockchain_v2_mainnet.sqlite"
    sqlite_path ="file:/mnt/chiaDB/mainnet/db/blockchain_v2_mainnet.sqlite?mode=ro"

    # connection = sqlite3.connect(db_path)
    # read only read
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)

    fetch_item = make_sql_fetcher('full_blocks', sorting_column='height')
    fetch_last_item = make_sql_fetcher_first_last_element('full_blocks', sorting_column='height')

    table_name = 'full_blocks'
    chunk_size = 20  # height * 2  # to be sure to have at least 2 full screen of data
    offset = 4315870 #34000
    sorting_column = 'height'
    filters = {'in_main_chain': 1}

    fe = FetchMaker.block_first_last_count_fetcher(table_name, sorting_column)
    data_loader = DataChunkLoader(sqlite_path, table_name, chunk_size, offset, filters=filters, sorting_column=sorting_column, data_struct=BlockState)

    last_item1 = data_loader.total_row_count
    print(f"row count = {last_item1}")
    #last_item = data_loader.fetch_last_item()
    #print(f"last item = {last_item}")
    #last_item = data_loader.idx_last_item[0][2]
    #print(f"last item height = {last_item}")
    #print(f"last item bd {last_item1} = {last_item}")
    #print(f"fiff = {last_item1 - last_item}")
    #print(f"diff from peak: {last_item1 - height_last_block}")

    a1 = time.perf_counter()
    a = (fetch_last_item(conn, filters, 'DESC'))
    a2 = time.perf_counter()
    b = (fetch_last_item(conn, {}, 'DESC'))
    a3 = time.perf_counter()
    c = (fetch_last_item(conn, filters, 'DESC'))
    a4 = time.perf_counter()

    print(f"t1: {a2-a1}")
    print(f"t2: {a3-a2}")
    print(f"t2: {a4-a3}")
    l = fetch_last_item(conn, {}, 'DESC')
    print(BlockState(l[0], True))



    start = offset
    for i in range(start, start + 10):
        items = fetch_item(conn, i, 2)
        print(f"n. items {len(items)}")
        for m in items:
            b = BlockState(m, True)
            print(f"idx {i} and height {b.height}, hash: {b.header_hash}, {b.weight}")
        print("----")

    print("___________________________")
    curr = conn.cursor()
    query = f"SELECT * FROM full_blocks WHERE height = ?"
    value = [4315872]
    curr.execute(query, value)
    items = curr.fetchall()
    print(f"n. items {len(items)}")
    for m in items:
        b = BlockState(m, True)
        print(f"idx {i} and height {b.height}, hash: {b.header_hash}, {b.weight}")



    block_ranger = make_sql_fetcher("full_blocks", sorting_column="height")
    p1 = time.perf_counter()
    blocks = block_ranger(conn, offset, 10000, filters=filters)
    p2 = time.perf_counter()
    blocks = block_ranger(conn, offset, 10000)
    p3 = time.perf_counter()
    print(f"time 1 {p2 - p1}")
    print(f"time 2 {p3 - p2}")


    p4 = time.perf_counter()
    data_loader.update_total_row_count(conn)
    p5 = time.perf_counter()
    a = get_row_count(conn, 'full_blocks', filters={'in_main_chain': 1})
    p6 = time.perf_counter()
    print(f"time 3 {p5 - p4}")
    print(f"time 4 {p6 - p5}")

    exit()
    for m in blocks:
        b = BlockState(m, False)
        print(f"idx {i} and height {b.height}, hash: {b.header_hash}, {b.weight}")


    # prototype for forks searcher
    import queue
    #block_queue = queue.Queue(maxsize=100_000)
    block_queue = multiprocessing.Queue(maxsize=10_000)
    llock = threading.Lock()

    def load_blocks(lock):

        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, check_same_thread=False)
        size_count = 0
        count = offset
        step = 5_000
        start = time.perf_counter()
        while True:

            p0 = time.perf_counter()
            pre_calc = p0 - start
            p1 = time.perf_counter()
            broks = block_ranger(conn, count, step)
            p2 = time.perf_counter()
            count += step

            for b in broks:
                block_queue.put(b)
            p3 = time.perf_counter()

            size_count += 1
            end = time.perf_counter()
            delta_time = end - start
            #print(f"precalc: {pre_calc}")
            #print(f"db loading: {p2 - p1}")
            #print(f"queueing: {p3 - p2}")
            if size_count % 10 == 0:
                print(f"queue size = {block_queue.qsize()}")
                print(f"tot time: {delta_time}")
                print(f"_____________________________")
            start = end

    #loader_man_thread = threading.Thread(target=load_blocks, args=(llock,), daemon=True)
    loader_man_thread = multiprocessing.Process(target=load_blocks, args=(llock,))
    loader_man_thread.start()


    # offset = 4315870 #34000
    count = offset
    file = "forks.text"
    prev_forked_block = 0
    fork = 0
    diff = 0

    start = time.perf_counter()
    while True:
        c: BlockState = BlockState(block_queue.get(), False)
        if int(c.height) != (count - diff):
            diff += 1
            if prev_forked_block != int(c.height - 1):
                fork += 1
            with open(file, "a") as f:
                f.write(f"height {c.height} count: {count} fork: {fork}\n")
                #raise Exception(f"c height {c.height} count: {count}")

            prev_forked_block = int(c.height)

        if count % 10_000 == 0:
            print('||||||||||||||||')
            print(f"counting: {count}")
            print(f"c height {c.height} count: {count - diff} effective count: {count}")
            print(f"queue size = {block_queue.qsize()}")
            end = time.perf_counter()
            delta_time = end - start
            print(f"tot time processing: {delta_time}")
            start = end
            print('||||||||||||||||')
        if count % 100_000 == 0:
            print(f"c height {c.height} count: {count - diff} effective count: {count}")
            time.sleep(0.01)
        #print(f"c height {c.height} count: {count - diff} effective count: {count}")
        count += 1
        #if count == 4330883:
        #    break

    exit()














    count = offset
    file = "forks.text"
    prev_forked_block = 0
    fork = 0
    diff = 0

    while True:
        c: BlockState = data_loader.get_current_item()
        if int(c.height) != (count - diff):
            diff += 1
            with open(file, "a") as f:
                f.write(f"height {c.height} count: {count} fork: {fork}\n")
                #raise Exception(f"c height {c.height} count: {count}")
            if prev_forked_block != int(c.height - 1):
                fork += 1

            prev_forked_block = int(c.height)

        if count % 100 == 0:
            print(count)
        count += 1
        data_loader.update_offset(count)
        if count % chunk_size == 0:
            data_loader.update_loader()
        if count % 1000 == 0:
            print(f"c height {c.height} count: {count -1}")
            time.sleep(1)
    exit()

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



    offset = height_last_block
    offset = 0
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
        data_chunk_loader.update_offset(data_chunk_loader.current_offset + 1)
        sleep(0.55)
        #data_chunk_loader.update_loader(conn)
        if i == 20:
            chunks_preloaded = data_chunk_loader.get_items_hot_chunks()[0]
            print("chunks preloaded")
            for e, i in enumerate(chunks_preloaded):
                print(f"{e} - {i}")

    conn.close()






