import os
import sqlite3
import json
import zstd
import copy
from datetime import datetime
import time

from chia.types.full_block import FullBlock
from chia.consensus.block_record import BlockRecord
from chia.types.spend_bundle import SpendBundle
from chia_rs import CoinSpend, Coin, Program
from chia.util.hash import std_hash
from chia_rs.sized_bytes import bytes32, bytes48
from chia_rs.sized_ints import uint16, uint32, uint64, uint128
from clvm.casts import int_to_bytes

from chia_rs import (ELIGIBLE_FOR_DEDUP, ELIGIBLE_FOR_FF, BLSCache, ConsensusConstants,
    G2Element, supports_fast_forward, validate_clvm_and_signature)

from chia.consensus.default_constants import DEFAULT_CONSTANTS
from chia.types.spend_bundle_conditions import SpendBundleConditions, SpendConditions


from UTILITYtiller import timestamp_to_date
from CONFtiller import (
    server_logger, ui_logger, logging, XCH_FAKETAIL, XCH_MOJO, CAT_MOJO, SQL_TIMEOUT, DB_SB
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


######################## spend bundles db ##########################

def create_spend_bundle_db(conn):
    """Creates a database to store spend bundles and puzzles if it doesn't already exist.
    Puzzle reveals are store in a separate table and referenced by hash. """

    try:
        cursor = conn.cursor()

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
            "coin_id BLOB NOT NULL UNIQUE, "
            "parent_id BLOB NOT NULL, "
            "amount INT NOT NULL, "
            #"puzzle_hash BLOB NOT NULL,"
            "puzzle_reveal_hash BLOB NOT NULL, "
            "solution BLOB NOT NULL, "

            "FOREIGN KEY (puzzle_reveal_hash) REFERENCES puzzles(puzzle_hash), "
            "FOREIGN KEY (spend_bundle_id) REFERENCES spend_bundles(id));"

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
            "raw_spend_bundle BLOB NOT NULL);"
        )

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
            "spend_bundle_id BLOB NOT NULL UNIQUE, "
            "FOREIGN KEY (group_id) REFERENCES group_names(id),"
            "FOREIGN KEY (spend_bundle_id) REFERENCES spend_bundles(id));"
        )

        # Indexing for quick lookups
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_coin_spend_bundle_id ON coin_spends(spend_bundle_id); "
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_coin_id ON coin_spends(coin_id); "
        )

        conn.commit()

    except sqlite3.Error as e:
        print(f"Error creating the spend bundle database: {e}")
        logging(server_logger, "DEBUG", f"WDB error while creating the spend bundle database: {e}")
        logging(server_logger, "DEBUG", "WDB error _________________________________________")
        logging(server_logger, "DEBUG", "WDB error _________________________________________")
        logging(server_logger, "DEBUG", "WDB error _________________________________________")


def insert_puzzle(contable_namen, puzzle_hash, puzzle, size):
    cursor = conn.cursor()

    cursor.execute(
        "INSERT OR IGNORE INTO puzzles ("
        "puzzle_hash, clvm, size) VALUES (?, ?, ?);",
        (puzzle_hash,
         puzzle,
         size)
    )


def add_spend_bundles_to_watch_later(conn, spend_bundle_hash):
    cursor = conn.cursor()
    group_name = "watch later"

    spend_bundle_hash = bytes.fromhex(spend_bundle_hash)

    # retrive the id of the sb
    cursor.execute(
        "SELECT id FROM spend_bundles WHERE spend_bundle_hash = ?;",
        (spend_bundle_hash,)
    )
    item = cursor.fetchone()
    spend_bundle_id = None
    if item:
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

    # SHould return something?


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
        print(f"we have and exception guys... do something please!!! {e}")
        logging(server_logger, "DEBUG", f"WDB error while inserting the SP in the database: {e}")


    for spend in coin_spends:
        puzzle_reveal = spend.puzzle_reveal
        puzzle_hash = puzzle_reveal.get_tree_hash()
        print()
        print("puzzle hash")
        print(f"hash: {puzzle_reveal.get_hash()}")
        print(f"tree hash: {puzzle_reveal.get_tree_hash()}")
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
                print(f"we have and exception guys... puzzle insertion do something please!!! {e}")
                logging(server_logger, "DEBUG", f"WDB error while inserting the "
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
            print(f"we have and exception guys... coin spend insertion do something please!!! {e}")
            logging(server_logger, "DEBUG", f"WDB error while inserting the SP in the database: {e}")

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
    print("done")
    # aggregated_signature are not needed to be directily accessible...


    return "bye bye..."


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
            " SELECT s.raw_spend_bundle, s.timestamp FROM "
            " spend_bundles s JOIN spend_bundle_groups g "
            " ON s.id = g.spend_bundle_id WHERE g.id = ? AND s.spend_bundle_hash = ? ",
            (group_id, bundle_hash)
        )

    else:
        cursor.execute(
            "SELECT raw_spend_bundle, timestamp FROM spend_bundles WHERE spend_bundle_hash = ? ",
            (bundle_hash,)
        )

    raw_spend_bundles = cursor.fetchall()
    if len(raw_spend_bundles) == 0:
        return None

    bundle_states = []
    for rsp in raw_spend_bundles:
        spend_bundle_state: BundleState = BundleState(rsp)
        bundle_states.append(spend_bundle_state)

    return bundle_states


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
        self.n_iteration_challenge_chain = block['reward_chain_block']['challenge_chain_ip_vdf']['number_of_iterations']
        self.height_b = block['reward_chain_block']['height']
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
        keys.append('height_b')
        values.append(self.height_b)
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



##### Data chunk loader
import threading
import time
from dataclasses import dataclass


def make_sql_fetcher(table, sorting_column=None):
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
            values.extend([start + count, start])


        cur = conn.cursor()
        query = f"SELECT * FROM {table} {where_sql}"
        print(query)
        print(values)
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


class DataChunkLoader:
    def __init__(self, db_path: str, table_name: str, chunk_size: int, offset: int = 0, sorting_column=None, row_offset=False, filters={}, data_struct=None):
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
        self.fetcher = make_sql_fetcher(table_name, self.sorting_column)
        self.fetcher_first_last = make_sql_fetcher_first_last_element(table_name, self.sorting_column)
        self.data_struct = data_struct
        self.filters = filters

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
        total_row_count = get_row_count(conn, self.table_name, self.filters)
        with self.lock:
            self.total_row_count = total_row_count
        return total_row_count

    #def update_idx_last_item(self, conn):
    #    """ Return the highest value of the sorted columns, it can differs from 
    #    the total_row_count in case of double entries"""
    #    self.idx_last_item = self.fetcher(conn, 1, 1, self.filters, 'DESC')
    #    return self.idx_last_item

    def update_last_item(self, conn):
        first_last_items = self.fetcher_first_last(conn, self.filters, 'DESC')
        if first_last_items:
            last_item = first_last_items[0]
            with self.lock:
                self.last_item = last_item
        else:
            self.last_item = None
        return self.last_item

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
            print("pre")
            print(pre_chunk)
            print("current")
            print(current_chunk)
            print("current offset")
            print(self.current_offset)
            if pre_chunk and pre_chunk.chunk_idx < current_chunk.chunk_idx:
                data.extend(pre_chunk.data)
                chunk_idx = pre_chunk.chunk_idx
            else:
                chunk_idx = current_chunk.chunk_idx
            data.extend(current_chunk.data)
            if post_chunk:
                data.extend(post_chunk.data)

            return data, chunk_idx * self.chunk_size

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

    hash = "0x186c2aeb854c599627c4c7268a7e3f99bae52bde15768093aa6cf7a0642f65e5"
    hash = "186c2aeb854c599627c4c7268a7e3f99bae52bde15768093aa6cf7a0642f65e5"
    hash = bytes32.fromhex(hash)
    table = 'full_blocks'
    sorting_column = 'height'
    fetcher = make_sql_fetcher(table, sorting_column)
    obj = fetcher(conn, 0, 12_000_000, filters={'header_hash': hash})
    #obj = fetcher(conn, 0, 2, filters={'height': 100})
    print(obj)
    print('jkjkjjjkj')
    print('jkjkjjjkj')
    print('jkjkjjjkj')
    print('jkjkjjjkj')
    print('jkjkjjjkj')
    print('jkjkjjjkj')
    fetcher = make_sql_fetcher(table)
    obj = fetcher(conn, 0, 1, filters={'header_hash': hash})
    print(len(obj))
    print(obj)


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






