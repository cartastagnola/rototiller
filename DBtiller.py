from chia.util.bech32m import decode_puzzle_hash, encode_puzzle_hash
from chia.types.blockchain_format.sized_bytes import bytes32
from chia.util.ints import uint32, uint64

import sqlite3
from datetime import datetime

# all the function need a db init to get the cursor

# Connect to the SQLite database
# Replace 'your_database.db' with the path to your database
db_path = "/mnt/chiaDB/mainnet/db/blockchain_v2_mainnet.sqlite"
# connection = sqlite3.connect(db_path)
# read only read
connection = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
cursor = connection.cursor()


def get_table_columns(table_name):
    """
    Get information about columns in a specific table.
    """
    cursor.execute(f"PRAGMA table_info({table_name});")
    columns = cursor.fetchall()
    print(f"Columns in table '{table_name}':")
    for col in columns:
        cid, name, col_type, notnull, dflt_value, pk = col
        print(f"  Name: {name}, Type: {col_type}, Not Null: {notnull}, Primary Key: {pk}")


def inspect_rows(table_name, limit=5):
    """
    Inspect a few rows from a table and return them.
    """
    cursor.execute(f"SELECT * FROM {table_name} LIMIT {limit};")
    rows = cursor.fetchall()
    print(f"\nFirst {limit} rows from table '{table_name}':")
    for row in rows:
        print(row)
    return rows 


def list_tables():
    """
    List all tables in the database.
    """
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    return [table[0] for table in tables]


