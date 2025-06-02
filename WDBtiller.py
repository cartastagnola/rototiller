import os
import sqlite3
from datetime import datetime
from CONFtiller import (
    server_logger, ui_logger, logging, XCH_FAKETAIL, XCH_MOJO, CAT_MOJO
)


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


def retrive_all_pks(conn):
    conn.row_factory = sqlite3.Row # enable dictionary access
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


if __name__ == "__main__":
    pass

