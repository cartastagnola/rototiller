"""Puzzle scanners.

Two background jobs feed a catalog of the puzzles seen:
- the chain scanner looks at the puzzle reveals of the last spent coins
- the mempool scanner looks at the coin spends of the transactions in the mempool

A puzzle is identified by its layers: the mod hashes found uncurrying the
puzzle reveal, joined with '|'. It is the same key used in layered_puzzles.json.
A puzzle that is not curried has no layers, it is grouped by its shape instead
of its hash (see classify_puzzle), or every coin with different data in the code
would be a new puzzle.

Two lists:
- known puzzles: layered_puzzles.json and puzzle_types.json in resources/puzzles.
  The names given by the user are saved there, the files are in the repo so the
  names can be shared on github and used by other apps. They can be edited by hand
  while roto runs: the changes are reloaded and roto never overwrites them.
- puzzles seen: DB_PUZZLES, only a cache with the sightings (count, dates, example
  coin). It can be deleted and rebuilt, the names are not lost.
"""
import hashlib
import json
import os
import re
import time
import threading
from dataclasses import dataclass, replace

from chia.types.blockchain_format.program import Program as PyProgram

import src.CONFtiller as CONF
from src.CONFtiller import logging, debug_logger
import src.RPCtiller as RPC
import src.PUZZLEtiller as PUZ
import src.UTILStiller as UTILS
import src.WDBtiller as WDB


SOURCE_CHAIN = 'chain'
SOURCE_MEMPOOL = 'mempool'

STATUS_NEW = 'new'
STATUS_KNOWN = 'known'

# a puzzle that only returns its conditions: (q . conditions)
QUOTED_CONDITIONS_KEY = 'quoted_conditions'
# prefix of the key of a puzzle not curried, grouped by shape
SHAPE_KEY_PREFIX = 'shape_'
# atoms with this length or more are data (hashes, amounts, keys), they are not part of the shape
SHAPE_DATA_ATOM_LENGTH = 4

# version of the DB_PUZZLES tables, an old DB is dropped and the puzzles are scanned again
PUZZLES_DB_VERSION = 2

# puzzle_hash -> puzzle_key, many coins share the same puzzle
PUZZLE_HASH_CACHE_SIZE = 100_000


def strip_0x(hex_str: str) -> str:
    return hex_str[2:] if hex_str.startswith('0x') else hex_str


def create_puzzles_db(conn):
    if conn.execute("PRAGMA user_version").fetchone()[0] < PUZZLES_DB_VERSION:
        # old keys or columns, it is only a cache: drop it and scan again
        conn.execute("DROP TABLE IF EXISTS puzzles")
        conn.execute("DROP TABLE IF EXISTS scan_state")
        conn.execute(f"PRAGMA user_version = {PUZZLES_DB_VERSION}")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS puzzles (
            puzzle_key TEXT PRIMARY KEY,  -- mod hashes of the layers joined by '|', or a shape key
            sub_puzzle_hashes TEXT,       -- json list of the mod hashes
            source TEXT,                  -- where it was seen first: chain or mempool
            first_seen REAL,
            last_seen REAL,
            seen_count INTEGER,
            example_coin_id TEXT,
            example_height INTEGER,       -- spent height, NULL if seen in the mempool
            example_puzzle_reveal BLOB
        )""")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scan_state (
            job TEXT PRIMARY KEY,
            last_height INTEGER,
            updated_at REAL
        )""")
    conn.commit()


def catalog_label(puzzle_key: str):
    """Name and family from the puzzle catalogs in resources/puzzles.
    Return (name, family, status)"""
    if puzzle_key == QUOTED_CONDITIONS_KEY:
        return 'quoted conditions', '', STATUS_KNOWN

    layered = CONF.KNOWN_LAYERED_PUZZLES.get(puzzle_key)
    # auto saved layered puzzles have a type that is not in puzzle_types.json, they are not known
    if layered is not None and layered['puzzle_type'] in CONF.PUZZLE_TYPES:
        family = CONF.PUZZLE_TYPES[layered['puzzle_type']]['family']
        return layered['name'], family, STATUS_KNOWN

    # puzzle with a single layer that is in the base catalog
    known = CONF.KNOWN_PUZZLES.get(puzzle_key)
    if known is not None:
        return known['name'], '', STATUS_KNOWN

    return None, '', STATUS_NEW


def shape_hash(puzzle: PyProgram) -> str:
    """Hash of the puzzle code with the data atoms (hashes, amounts, keys) replaced by a
    placeholder: the same code with different data has the same shape hash"""
    sha = hashlib.sha256()
    stack = [puzzle]
    while stack:
        node = stack.pop()
        if node.pair is not None:
            # pre-order walk, like the clvm serialization: the result is not ambiguous
            sha.update(b'\xff')
            stack.append(node.pair[1])
            stack.append(node.pair[0])
        elif len(node.atom) >= SHAPE_DATA_ATOM_LENGTH:
            sha.update(b'\xfe')
        else:
            sha.update(bytes([len(node.atom)]) + node.atom)
    return sha.hexdigest()


def classify_puzzle(puzzle: PyProgram):
    """Uncurry the puzzle and return (puzzle_key, sub_puzzle_hashes)"""
    names, hashes = PUZ.unroll_puzzle_to_names(puzzle)
    is_single_unknown = (len(hashes) == 1 and hashes[0] not in CONF.KNOWN_PUZZLES
                         and hashes[0] == puzzle.get_tree_hash().hex())
    if hashes and not is_single_unknown:
        return '|'.join(hashes), hashes

    # not curried and not in the catalog: the hash changes with every value written in the code
    if puzzle.pair is not None and puzzle.first().atom == b'\x01':
        return QUOTED_CONDITIONS_KEY, [QUOTED_CONDITIONS_KEY]
    key = SHAPE_KEY_PREFIX + shape_hash(puzzle)
    return key, [key]


def sub_puzzle_name(sub_puzzle_hash: str) -> str:
    """Name of a layer, also for the keys of the puzzles that are not curried"""
    if sub_puzzle_hash == QUOTED_CONDITIONS_KEY:
        return '(q . conditions)'
    if sub_puzzle_hash.startswith(SHAPE_KEY_PREFIX):
        return f"not curried code {sub_puzzle_hash[len(SHAPE_KEY_PREFIX):][:8]}"
    return PUZ.compare_to_known_puzzles(sub_puzzle_hash)


def puzzle_type_key(name: str) -> str:
    """Key in puzzle_types.json made from a puzzle name: 'My puzzle v1' -> 'MY_PUZZLE_V1'"""
    return re.sub(r'[^A-Z0-9]+', '_', name.upper()).strip('_') or 'PUZZLE'


def save_known_puzzle(puzzle_key: str, sub_puzzle_hashes: list, sub_puzzle_names: list,
                      name: str, family: str, example_coin_id: str = None, tags: list = None):
    """Add or rename a puzzle in layered_puzzles.json, an empty name removes it.
    The family goes in puzzle_types.json with a type made from the name, a puzzle that
    already has a type with the same family keeps it (eg: a new variant of NFT_V1).
    The family is also the first tag of the entry (PUZ.layered_puzzle_tags), the tags added
    by hand stay. With tags (eg: from the names review page) the entry gets exactly these
    tags, after the family.
    The files are read from disk and only this entry changes, the edits made by hand stay.
    Raise ValueError if a file is not valid json."""
    with CONF.LAYERED_PUZZLES_LOCK:
        if not name:
            PUZ.update_catalog_file(CONF.KNOWN_LAYERED_PUZZLES_PATH, CONF.KNOWN_LAYERED_PUZZLES,
                                    lambda layered: layered.pop(puzzle_key, None) is not None)
            return

        family = family or 'UNKNOWN'
        puzzle_type = None

        def add_type(types: dict):
            nonlocal puzzle_type
            old = CONF.KNOWN_LAYERED_PUZZLES.get(puzzle_key)
            if old is not None and old['puzzle_type'] in types and types[old['puzzle_type']]['family'] == family:
                puzzle_type = old['puzzle_type']
                return False
            base = puzzle_type_key(name)
            puzzle_type = base
            n = 2
            while puzzle_type in types and types[puzzle_type]['family'] != family:
                puzzle_type = f"{base}_{n}"
                n += 1
            if puzzle_type in types:
                return False
            types[puzzle_type] = {'name': name, 'family': family}

        def add_entry(layered: dict):
            old_tags = layered.get(puzzle_key, {}).get('tags')
            entry = {
                'puzzle_type': puzzle_type,
                'name': name,
                'sub_puzzle_hashes': sub_puzzle_hashes,
                'sub_puzzle_names': sub_puzzle_names,
                'tags': (list(dict.fromkeys([family] + list(tags))) if tags is not None
                         else PUZ.layered_puzzle_tags(family, sub_puzzle_names, old_tags)),
            }
            if example_coin_id:
                entry['example_coin_id'] = example_coin_id
            layered[puzzle_key] = entry

        PUZ.update_catalog_file(CONF.PUZZLE_TYPES_PATH, CONF.PUZZLE_TYPES, add_type)
        PUZ.update_catalog_file(CONF.KNOWN_LAYERED_PUZZLES_PATH, CONF.KNOWN_LAYERED_PUZZLES, add_entry)


@dataclass
class PuzzleEntry:
    puzzle_key: str
    sub_puzzle_hashes: list
    source: str
    first_seen: float
    last_seen: float
    seen_count: int
    example_coin_id: str
    example_height: int
    example_puzzle_reveal: bytes

    def label(self):
        """Return (name, family, status)"""
        return catalog_label(self.puzzle_key)

    def sub_puzzle_names(self):
        return [sub_puzzle_name(h) for h in self.sub_puzzle_hashes]

    def to_row(self):
        return (self.puzzle_key, json.dumps(self.sub_puzzle_hashes),
                self.source, self.first_seen, self.last_seen, self.seen_count,
                self.example_coin_id, self.example_height, self.example_puzzle_reveal)

    @staticmethod
    def from_row(row):
        return PuzzleEntry(row[0], json.loads(row[1]), *row[2:])


class PuzzleCatalog:
    """All the puzzles seen. Memory is the source of truth, the DB is written on flush."""

    COLUMNS = ("puzzle_key, sub_puzzle_hashes, source, first_seen, last_seen, "
               "seen_count, example_coin_id, example_height, example_puzzle_reveal")

    def __init__(self, db_path):
        self.db_path = db_path
        self.lock = threading.Lock()  # memory
        self.db_lock = threading.Lock()  # keep the DB writes in the same order of the memory changes
        self.entries: dict[str, PuzzleEntry] = {}
        self.dirty = set()
        self.version = 0  # incremented on every change, the UI can use it to rebuild its tables

    def load(self):
        conn = WDB.get_connection(self.db_path)
        try:
            create_puzzles_db(conn)
            rows = conn.execute(f"SELECT {self.COLUMNS} FROM puzzles").fetchall()
        finally:
            conn.close()
        with self.lock:
            self.entries = {row[0]: PuzzleEntry.from_row(row) for row in rows}
            self.version += 1

    def record_seen(self, puzzle_key: str, sub_puzzle_hashes: list, source: str,
                    coin_id: str, height: int, puzzle_reveal_hex: str):
        """Add a puzzle sighting. Return True if the puzzle is new."""
        now = time.time()
        is_new = False
        with self.lock:
            entry = self.entries.get(puzzle_key)
            if entry is None:
                is_new = True
                entry = PuzzleEntry(puzzle_key, sub_puzzle_hashes, source, now, now, 0,
                                    coin_id, height, bytes.fromhex(strip_0x(puzzle_reveal_hex)))
                self.entries[puzzle_key] = entry
            entry.seen_count += 1
            entry.last_seen = now
            self.dirty.add(puzzle_key)
            self.version += 1
        return is_new

    def flush(self, scan_job: str = None, scan_height: int = None):
        """Write the changed puzzles, and optionally the scan progress, in one transaction."""
        with self.db_lock:
            with self.lock:
                rows = [self.entries[key].to_row() for key in self.dirty]
                self.dirty = set()
            if not rows and scan_job is None:
                return
            conn = WDB.get_connection(self.db_path)
            try:
                with conn:
                    conn.executemany(f"INSERT OR REPLACE INTO puzzles ({self.COLUMNS}) "
                                     f"VALUES (?,?,?,?,?,?,?,?,?)", rows)
                    if scan_job is not None:
                        conn.execute("INSERT OR REPLACE INTO scan_state (job, last_height, updated_at) "
                                     "VALUES (?,?,?)", (scan_job, scan_height, time.time()))
            finally:
                conn.close()

    def set_name(self, puzzle_key: str, name: str, family: str):
        """Save the name and family in layered_puzzles.json, an empty name removes the puzzle"""
        with self.lock:
            entry = self.entries[puzzle_key]
            sub_puzzle_hashes = list(entry.sub_puzzle_hashes)
            example_coin_id = entry.example_coin_id
        # names from the shared catalogs only: unknown_puzz_NN names exist only in the local unknown_puzzles.json
        sub_puzzle_names = [CONF.KNOWN_PUZZLES[h]['name'] if h in CONF.KNOWN_PUZZLES else sub_puzzle_name(h)
                            for h in sub_puzzle_hashes]
        sub_puzzle_names = [name if not name.startswith('unknown_puzz_') else CONF.UNKNOWN_PUZZLE
                            for name in sub_puzzle_names]
        save_known_puzzle(puzzle_key, sub_puzzle_hashes, sub_puzzle_names, name, family, example_coin_id)
        with self.lock:
            self.version += 1

    def get_scan_height(self, scan_job: str):
        conn = WDB.get_connection(self.db_path)
        try:
            row = conn.execute("SELECT last_height FROM scan_state WHERE job = ?", (scan_job,)).fetchone()
        finally:
            conn.close()
        return row[0] if row else None

    def get(self, puzzle_key: str):
        with self.lock:
            entry = self.entries.get(puzzle_key)
            return replace(entry) if entry else None

    def snapshot(self):
        with self.lock:
            return [replace(entry) for entry in self.entries.values()], self.version

    def label(self, puzzle_key: str):
        with self.lock:
            entry = self.entries.get(puzzle_key)
            if entry is not None:
                return entry.label()
        return catalog_label(puzzle_key)

    def families(self):
        """Families in puzzle_types.json"""
        with CONF.LAYERED_PUZZLES_LOCK:
            return sorted({data['family'] for data in CONF.PUZZLE_TYPES.values()})


def scan_coin_spend(catalog: PuzzleCatalog, coin_spend: dict, source: str, height: int,
                    puzzle_hash_cache: dict):
    """Classify the puzzle of a coin spend (rpc json) and add it to the catalog.
    Return the puzzle key."""
    coin = coin_spend['coin']
    puzzle_hash = strip_0x(coin['puzzle_hash'])

    cached = puzzle_hash_cache.get(puzzle_hash)
    if cached is not None:
        puzzle_key, sub_puzzle_hashes = cached
    else:
        puzzle = PyProgram.fromhex(strip_0x(coin_spend['puzzle_reveal']))
        puzzle_key, sub_puzzle_hashes = classify_puzzle(puzzle)
        if len(puzzle_hash_cache) > PUZZLE_HASH_CACHE_SIZE:
            puzzle_hash_cache.clear()
        puzzle_hash_cache[puzzle_hash] = (puzzle_key, sub_puzzle_hashes)

    coin_id = UTILS.calc_coin_id(coin['parent_coin_info'], coin['puzzle_hash'], coin['amount']).hex()
    catalog.record_seen(puzzle_key, sub_puzzle_hashes, source, coin_id, height, coin_spend['puzzle_reveal'])
    return puzzle_key


class ChainPuzzleScanner:
    """Scan the puzzle reveals of the last spent coins, then keep scanning the new blocks."""

    SCAN_JOB = 'chain'

    def __init__(self, catalog: PuzzleCatalog, coin_limit: int, delay: float):
        self.catalog = catalog
        self.coin_limit = coin_limit
        self.delay = delay
        self.status = 'waiting'
        self.blocks_scanned = 0
        self.blocks_total = 0
        self.coins_scanned = 0
        self.last_height = None
        self.puzzle_hash_cache = {}
        self.thread = None

    def start(self):
        self.thread = threading.Thread(target=self.run, daemon=True, name='puzzle chain scanner')
        self.thread.start()

    def run(self):
        while True:
            try:
                self.scan()
            except Exception as e:
                self.status = f'error: {e}'
                logging(debug_logger, "DEBUG", f"PUZZLE CHAIN SCAN error: {e}")
                UTILS.logging_traceback('PUZZLE CHAIN SCAN')
            time.sleep(self.delay)

    def scan(self):
        last_height = self.catalog.get_scan_height(self.SCAN_JOB) or 0
        self.last_height = last_height or None

        db_conn = WDB.get_connection(CONF.DB_BLOCKCHAIN_RO)
        try:
            # the heights of the last spent coins not scanned yet
            rows = db_conn.execute(
                "SELECT DISTINCT spent_index FROM ("
                "SELECT spent_index FROM coin_record WHERE spent_index > ? "
                "ORDER BY spent_index DESC LIMIT ?)",
                (last_height, self.coin_limit)).fetchall()
            # oldest first, so the scan can continue from the last height if it stops
            heights = sorted(row[0] for row in rows)

            self.blocks_total = len(heights)
            self.blocks_scanned = 0
            for height in heights:
                self.status = f'scanning block {height:,}'
                row = db_conn.execute(
                    "SELECT header_hash FROM full_blocks WHERE height = ? AND in_main_chain = 1",
                    (height,)).fetchone()
                if row is not None:
                    spends = RPC.call_rpc_node('get_block_spends', header_hash=f"0x{row[0].hex()}")
                    for coin_spend in spends:
                        scan_coin_spend(self.catalog, coin_spend, SOURCE_CHAIN, height, self.puzzle_hash_cache)
                        self.coins_scanned += 1
                self.blocks_scanned += 1
                self.catalog.flush(self.SCAN_JOB, height)
                self.last_height = height
        finally:
            db_conn.close()

        self.status = 'up to date'


@dataclass
class MempoolTx:
    tx_id: str
    cost: int
    fee: int
    coins_in: int
    coins_out: int
    puzzle_keys: list  # puzzle key of each coin spend
    removal_coin_ids: list
    added_at: float
    gone_at: float = None  # when it left the mempool
    validated_at: float = None  # when it was found in a block

    @property
    def fee_per_cost(self):
        return self.fee / self.cost if self.cost else 0


class MempoolPuzzleScanner:
    """Keep the list of the mempool transactions and add their puzzles to the catalog."""

    # with more new transactions than this, load the whole mempool in one call
    MAX_SINGLE_CALLS = 50

    def __init__(self, catalog: PuzzleCatalog, delay: float, validated_delay: float):
        self.catalog = catalog
        self.delay = delay
        self.validated_delay = validated_delay
        self.status = 'waiting'
        self.lock = threading.Lock()
        self.txs: dict[str, MempoolTx] = {}
        self.puzzle_hash_cache = {}
        self.thread = None

    def start(self):
        self.thread = threading.Thread(target=self.run, daemon=True, name='puzzle mempool scanner')
        self.thread.start()

    def run(self):
        while True:
            try:
                self.scan()
            except Exception as e:
                self.status = f'error: {e}'
                logging(debug_logger, "DEBUG", f"PUZZLE MEMPOOL SCAN error: {e}")
                UTILS.logging_traceback('PUZZLE MEMPOOL SCAN')
            time.sleep(self.delay)

    def scan(self):
        tx_ids = {strip_0x(tx_id) for tx_id in RPC.call_rpc_node('get_all_mempool_tx_ids')}
        now = time.time()

        with self.lock:
            for tx_id, tx in list(self.txs.items()):
                if tx.validated_at is not None and now - tx.validated_at > self.validated_delay:
                    self.txs.pop(tx_id)
            gone_txs = [tx for tx_id, tx in self.txs.items() if tx_id not in tx_ids and tx.validated_at is None]
            new_tx_ids = tx_ids - set(self.txs)

        # a transaction that left the mempool is validated if its coins are spent on chain,
        # if not it was replaced or expired. Check it twice, the block could be not in the DB yet
        validated_tx_ids = self.validated_tx_ids(gone_txs)
        with self.lock:
            for tx in gone_txs:
                if tx.tx_id in validated_tx_ids:
                    tx.validated_at = now
                elif tx.gone_at is None:
                    tx.gone_at = now
                else:
                    self.txs.pop(tx.tx_id, None)

        if len(new_tx_ids) > self.MAX_SINGLE_CALLS:
            items = RPC.call_rpc_node('get_all_mempool_items')
            items = {strip_0x(tx_id): item for tx_id, item in items.items() if strip_0x(tx_id) in new_tx_ids}
        else:
            items = {}
            for tx_id in new_tx_ids:
                items[tx_id] = RPC.call_rpc_node('get_mempool_item_by_tx_id', tx_id=f"0x{tx_id}")

        for tx_id, item in items.items():
            puzzle_keys = []
            for coin_spend in item['spend_bundle']['coin_spends']:
                puzzle_keys.append(scan_coin_spend(self.catalog, coin_spend, SOURCE_MEMPOOL, None,
                                                   self.puzzle_hash_cache))
            removal_coin_ids = [UTILS.calc_coin_id(c['parent_coin_info'], c['puzzle_hash'], c['amount']).hex()
                                for c in item['removals']]
            tx = MempoolTx(tx_id, item['cost'], item['fee'], len(item['removals']),
                           len(item['additions']), puzzle_keys, removal_coin_ids, time.time())
            with self.lock:
                self.txs[tx_id] = tx

        self.catalog.flush()
        self.status = f'updated at {time.strftime("%H:%M:%S")}'

    @staticmethod
    def validated_tx_ids(txs: list):
        """Ids of the transactions with the first removed coin spent on chain"""
        if not txs:
            return set()
        validated = set()
        db_conn = WDB.get_connection(CONF.DB_BLOCKCHAIN_RO)
        try:
            for tx in txs:
                if not tx.removal_coin_ids:
                    continue
                row = db_conn.execute("SELECT spent_index FROM coin_record WHERE coin_name = ?",
                                      (bytes.fromhex(tx.removal_coin_ids[0]),)).fetchone()
                if row is not None and row[0] > 0:
                    validated.add(tx.tx_id)
        finally:
            db_conn.close()
        return validated

    def snapshot(self):
        """Transactions sorted by fee per cost, the first ones go in the next block"""
        with self.lock:
            txs = list(self.txs.values())
        return sorted(txs, key=lambda tx: tx.fee_per_cost, reverse=True)


def tx_type(catalog: PuzzleCatalog, puzzle_keys: list):
    """Names of the puzzles spent by a transaction, 'unknown' for the new ones"""
    counts = {}
    for key in puzzle_keys:
        name, family, status = catalog.label(key)
        name = name or 'unknown'
        counts[name] = counts.get(name, 0) + 1
    return ', '.join(f"{n}x {name}" if n > 1 else name for name, n in counts.items())


class CatalogFileWatcher:
    """Reload layered_puzzles.json and puzzle_types.json when they are edited by hand"""

    def __init__(self, catalog: PuzzleCatalog, delay: float):
        self.catalog = catalog
        self.delay = delay
        self.status = 'waiting'
        self.thread = None

    def start(self):
        self.thread = threading.Thread(target=self.run, daemon=True, name='puzzle catalog watcher')
        self.thread.start()

    def run(self):
        while True:
            try:
                reloaded = PUZ.reload_catalog_files()
                if reloaded:
                    with self.catalog.lock:
                        self.catalog.version += 1
                    self.status = f'reloaded at {time.strftime("%H:%M:%S")}'
                    logging(debug_logger, "DEBUG", f"CATALOG reloaded {reloaded}")
            except Exception as e:
                self.status = f'error: {e}'
                logging(debug_logger, "DEBUG", f"CATALOG WATCHER error: {e}")
                UTILS.logging_traceback('CATALOG WATCHER')
            time.sleep(self.delay)


CATALOG = PuzzleCatalog(CONF.DB_PUZZLES)
CHAIN_SCANNER = ChainPuzzleScanner(CATALOG, CONF.PUZZLE_SCAN_COIN_LIMIT, CONF.PUZZLE_SCAN_CHAIN_DELAY)
MEMPOOL_SCANNER = MempoolPuzzleScanner(CATALOG, CONF.PUZZLE_SCAN_MEMPOOL_DELAY, CONF.MEMPOOL_VALIDATED_TX_DELAY)
CATALOG_WATCHER = CatalogFileWatcher(CATALOG, CONF.PUZZLE_CATALOG_WATCH_DELAY)


def start_scanners():
    """Load the catalog and start the two jobs and the catalog file watcher, only once"""
    if CHAIN_SCANNER.thread is not None:
        return
    CONF.DB_FOLDER.mkdir(exist_ok=True)
    CATALOG.load()
    PUZ.reload_catalog_files()  # remember the state of the files loaded by CONFtiller
    CHAIN_SCANNER.start()
    MEMPOOL_SCANNER.start()
    CATALOG_WATCHER.start()
