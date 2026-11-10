"""Puzzle scanners.

Background jobs feed a catalog of the puzzles seen:
- the live chain scanner reads every new block of the node DB and counts the puzzles spent
- the full scan (the full_scan job of LAUNCHtiller, a separate process started from the puzzle scanner view)
  scans the whole chain once, in chunks of heights, with several workers
- the mempool scanner looks at the coin spends of the transactions in the mempool

A puzzle is identified by its layers: the mod hashes found uncurrying the puzzle reveal,
joined with '|'. It is the layered puzzle fingerprint, the same one used in
layered_puzzles.json. A puzzle that is not curried has no layers, it is grouped by its shape
instead of its hash (see classify_puzzle), or every coin with different data in the code
would be a new puzzle.

Two lists:
- known puzzles: layered_puzzles.json and puzzle_types.json in resources/puzzles/catalog.
  The names given by the user are saved there, the files are in the repo so the
  names can be shared on github and used by other apps. They can be edited by hand
  while roto runs: the changes are reloaded and roto never overwrites them.
- puzzles seen: DB_PUZZLES, the sightings (spends counted, first and last seen, example
  coin) and the spends per block: the counts of any time window, the spends heat map. It can
  be deleted and scanned again, the names are not lost.

The full scan and the live scanner never scan the same heights: the full scan takes [0, the
tip when it starts), the live scanner goes on from there. Both add their counts to the DB
(upserts), the catalog in memory is reloaded from the DB while the full scan runs.
"""
import contextlib
import hashlib
import json
import multiprocessing as mp
import os
import re
import signal
import subprocess
import sys
import time
import threading
from collections import deque
from dataclasses import dataclass, replace

import zstd
from chia.consensus.default_constants import DEFAULT_CONSTANTS
from chia.types.blockchain_format.program import Program as PyProgram
from chia_rs import (CoinSpend, FullBlock, G2Element, SpendBundle, get_conditions_from_spendbundle,
                     get_spends_for_trusted_block)

import src.CONFtiller as CONF
from src.CONFtiller import logging, debug_logger
import src.RPCtiller as RPC
import src.PUZZLEtiller as PUZ
import src.TYPEStiller as TYPES
import src.UTILStiller as UTILS
import src.WDBtiller as WDB


SOURCE_CHAIN = 'chain'
SOURCE_MEMPOOL = 'mempool'

# a puzzle that only returns its conditions: (q . conditions)
QUOTED_CONDITIONS_FINGERPRINT = PUZ.QUOTED_CONDITIONS_FINGERPRINT
# prefix of the fingerprint of a puzzle not curried, grouped by shape
SHAPE_FINGERPRINT_PREFIX = PUZ.SHAPE_FINGERPRINT_PREFIX
# atoms with this length or more are data (hashes, amounts, keys), they are not part of the shape
SHAPE_DATA_ATOM_LENGTH = 4

# version of the DB_PUZZLES tables: an older DB is dropped and the chain is scanned again
# (6: the spends per block replace the spends per day and the last 30 days, one by one)
PUZZLES_DB_VERSION = 6

# puzzle_hash -> layered_puzzle_fingerprint, many coins share the same puzzle
PUZZLE_HASH_CACHE_SIZE = 100_000

# the spends are counted per puzzle per block (puzzle_spends_blocks, the times in block_times):
# the spends of a block have its time, so it is as exact as a row a spend, ~300 MB for the
# whole chain against ~6 GB
DAY = 86_400
# time windows of the all puzzles view: label -> seconds (None: since the first block)
TIME_WINDOWS = {'all': None, '1y': 365 * DAY, '1m': 30 * DAY, '1w': 7 * DAY, '1d': DAY, '1h': 3_600}

FULL_SCAN_JOB = 'full'
LIVE_SCAN_JOB = 'live'
FULL_SCAN_CHUNK = 20_000  # heights per chunk of the full scan
FULL_SCAN_LOG = CONF.DB_FOLDER / 'full_scan.log'


def strip_0x(hex_str: str) -> str:
    return hex_str[2:] if hex_str.startswith('0x') else hex_str


def create_puzzles_db(conn):
    if conn.execute("PRAGMA user_version").fetchone()[0] < PUZZLES_DB_VERSION:
        # an older shape: only sightings, the chain can be scanned again
        # puzzle_spends_daily and puzzle_spends_recent: the tables of version 5
        for table in ('puzzles', 'scan_state', 'puzzle_spends_daily', 'puzzle_spends_recent', 'scan_chunks',
                      'puzzle_spends_blocks', 'block_times'):
            conn.execute(f"DROP TABLE IF EXISTS {table}")
        conn.execute(f"PRAGMA user_version = {PUZZLES_DB_VERSION}")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS puzzles (
            id INTEGER PRIMARY KEY,
            layered_puzzle_fingerprint TEXT UNIQUE NOT NULL,  -- mod hashes of the layers joined by '|', or a shape fingerprint
            sub_puzzle_hashes TEXT,       -- json list of the mod hashes
            source TEXT,                  -- where it was seen first: chain or mempool
            first_seen REAL,              -- block timestamps (the time it was seen, in the mempool)
            last_seen REAL,
            seen_count INTEGER DEFAULT 0, -- spends on chain
            first_height INTEGER,
            last_height INTEGER,
            example_coin_id TEXT,
            example_height INTEGER,       -- spent height, NULL if seen in the mempool
            example_puzzle_reveal BLOB
        )""")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS puzzle_spends_blocks (
            puzzle_id INTEGER,
            height INTEGER,
            spends INTEGER,
            PRIMARY KEY (puzzle_id, height)
        ) WITHOUT ROWID""")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS block_times (
            height INTEGER PRIMARY KEY,   -- the transaction blocks scanned
            timestamp INTEGER
        )""")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scan_chunks (
            start INTEGER PRIMARY KEY,    -- heights [start, end) of the full scan
            end INTEGER,
            tx_blocks INTEGER,
            spends INTEGER,
            errors INTEGER,
            seconds REAL,
            done_at REAL
        )""")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scan_state (
            job TEXT PRIMARY KEY,         -- 'live': heights [start_height, last_height]; 'full': [0, end_height)
            start_height INTEGER,
            last_height INTEGER,
            end_height INTEGER,
            updated_at REAL,
            info TEXT                     -- json: full scan pid, workers, started_at, finished_at
        )""")
    conn.commit()


def catalog_classification(layered_puzzle_fingerprint: str, puzzle_reveal: bytes = None) -> dict:
    """PUZ.classify_fingerprint of a layered puzzle fingerprint, with its label and status. puzzle_reveal: an example, for the
    custody"""
    puzzle = PyProgram.from_bytes(bytes(puzzle_reveal)) if puzzle_reveal else None
    c = PUZ.classify_fingerprint(layered_puzzle_fingerprint, puzzle)
    c['label'] = PUZ.classification_label(c, layered_puzzle_fingerprint)
    c['status'] = PUZ.layered_puzzle_status(layered_puzzle_fingerprint)
    # how many puzzles deep (PUZ.puzzle_depth): from the example, None without one. A puzzle
    # that is not curried (shape_, quoted conditions) is 1, like its one layer
    if layered_puzzle_fingerprint not in PUZ._depth_cache and puzzle_reveal:
        PUZ._depth_cache[layered_puzzle_fingerprint] = PUZ.puzzle_depth(puzzle_reveal) or 1
    c['depth'] = PUZ._depth_cache.get(layered_puzzle_fingerprint)
    return c


def catalog_label(layered_puzzle_fingerprint: str, puzzle_reveal: bytes = None):
    """Return (label, family, status): the name in resources/puzzles/catalog, or a label made
    from the classification; the family; KNOWN when every layer is known or it is named"""
    c = catalog_classification(layered_puzzle_fingerprint, puzzle_reveal)
    return c['label'], c['family'][0] or '', c['status']


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
    """Uncurry the puzzle and return (layered_puzzle_fingerprint, sub_puzzle_hashes)"""
    names, hashes = PUZ.unroll_puzzle_to_names(puzzle)
    is_single_unknown = (len(hashes) == 1 and hashes[0] not in CONF.KNOWN_PUZZLES
                         and hashes[0] == puzzle.get_tree_hash().hex())
    if hashes and not is_single_unknown:
        return '|'.join(hashes), hashes

    # not curried and not in the catalog: the hash changes with every value written in the code
    if puzzle.pair is not None and puzzle.first().atom == b'\x01':
        return QUOTED_CONDITIONS_FINGERPRINT, [QUOTED_CONDITIONS_FINGERPRINT]
    fingerprint = SHAPE_FINGERPRINT_PREFIX + shape_hash(puzzle)
    return fingerprint, [fingerprint]


def sub_puzzle_name(sub_puzzle_hash: str) -> str:
    """Name of a layer, also for the fingerprints of the puzzles that are not curried"""
    if sub_puzzle_hash == QUOTED_CONDITIONS_FINGERPRINT:
        return '(q . conditions)'
    if sub_puzzle_hash.startswith(SHAPE_FINGERPRINT_PREFIX):
        return f"not curried code {sub_puzzle_hash[len(SHAPE_FINGERPRINT_PREFIX):][:8]}"
    return PUZ.compare_to_known_puzzles(sub_puzzle_hash)


# --- scanning blocks: shared by the full scan (worker processes) and the live scanner -----------

def node_connection():
    """Read-only connection to the node DB"""
    import sqlite3
    return sqlite3.connect(CONF.DB_BLOCKCHAIN_RO, uri=True, timeout=60)


def chain_tip(node_conn) -> int:
    return node_conn.execute("SELECT MAX(height) FROM full_blocks WHERE in_main_chain = 1").fetchone()[0]


def block_spends(node_conn, blob: bytes, ref_cache: dict):
    """(timestamp, spends) of a block of the node DB: spends is the list of the coin spends
    (chia_rs), run from the block generator here (no RPC). (None, []) for a block without
    transactions. ref_cache: height -> generator of the blocks referenced, kept small."""
    block = FullBlock.from_bytes(zstd.decompress(blob))
    generator = block.transactions_generator
    if generator is None:
        return None, []
    refs = []
    for ref_height in block.transactions_generator_ref_list:
        ref = ref_cache.get(ref_height)
        if ref is None:
            row = node_conn.execute("SELECT block FROM full_blocks WHERE in_main_chain = 1 AND height = ?",
                                    (ref_height,)).fetchone()
            ref = bytes(FullBlock.from_bytes(zstd.decompress(row[0])).transactions_generator)
            if len(ref_cache) > 64:
                ref_cache.clear()
            ref_cache[ref_height] = ref
        refs.append(ref)
    spends = get_spends_for_trusted_block(DEFAULT_CONSTANTS, generator, refs, 0)['block_spends']
    return block.foliage_transaction_block.timestamp, spends


class ScanResult:
    """The puzzles spent in a range of heights, ready for write_scan_result:
    found: fingerprint -> [sub hashes, spends, first height, last height, first ts, last ts,
    example coin id, example height, example reveal]; blocks: (fingerprint, height) -> spends;
    block_times: height -> ts"""

    def __init__(self):
        self.found = {}
        self.blocks = {}
        self.block_times = {}
        self.tx_blocks = self.spends = self.errors = 0

    def add_block(self, height: int, timestamp: int, spends: list, cache: dict):
        self.tx_blocks += 1
        self.block_times[height] = timestamp
        for spend in spends:
            self.spends += 1
            puzzle_hash = bytes(spend.coin.puzzle_hash)
            hit = cache.get(puzzle_hash)
            if hit is None:
                hit = classify_puzzle(PyProgram.from_bytes(bytes(spend.puzzle_reveal)))
                if len(cache) > PUZZLE_HASH_CACHE_SIZE:
                    cache.clear()
                cache[puzzle_hash] = hit
            fingerprint, sub_hashes = hit
            f = self.found.get(fingerprint)
            if f is None:
                self.found[fingerprint] = [sub_hashes, 1, height, height, timestamp, timestamp,
                                           spend.coin.name().hex(), height, bytes(spend.puzzle_reveal)]
            else:
                f[1] += 1
                f[2], f[3] = min(f[2], height), max(f[3], height)
                f[4], f[5] = min(f[4], timestamp), max(f[5], timestamp)
            key = (fingerprint, height)
            self.blocks[key] = self.blocks.get(key, 0) + 1


def scan_heights(start: int, end: int, node_conn=None, cache: dict = None) -> ScanResult:
    """Scan the blocks of heights [start, end) of the node DB"""
    own_conn = node_conn is None
    node_conn = node_conn or node_connection()
    cache = {} if cache is None else cache
    ref_cache = {}
    result = ScanResult()
    try:
        rows = node_conn.execute("SELECT height, block FROM full_blocks WHERE in_main_chain = 1 "
                                 "AND height >= ? AND height < ? ORDER BY height", (start, end))
        for height, blob in rows:
            try:
                timestamp, spends = block_spends(node_conn, blob, ref_cache)
            except Exception as e:
                result.errors += 1
                logging(debug_logger, "DEBUG", f"PUZZLE SCAN block {height} not read: {e}")
                continue
            if timestamp is not None:
                result.add_block(height, timestamp, spends, cache)
    finally:
        if own_conn:
            node_conn.close()
    return result


def scan_chunk(args):
    """A chunk of the full scan, in a worker process: (start, end) -> (start, end, ScanResult,
    seconds)"""
    start, end = args
    t0 = time.time()
    return start, end, scan_heights(start, end), time.time() - t0


UPSERT_PUZZLE = """
    INSERT INTO puzzles (layered_puzzle_fingerprint, sub_puzzle_hashes, source, first_seen, last_seen,
                         seen_count, first_height, last_height, example_coin_id, example_height,
                         example_puzzle_reveal)
    VALUES (?,?,?,?,?,?,?,?,?,?,?)
    ON CONFLICT (layered_puzzle_fingerprint) DO UPDATE SET
        seen_count = seen_count + excluded.seen_count,
        first_seen = min(coalesce(first_seen, excluded.first_seen), coalesce(excluded.first_seen, first_seen)),
        last_seen = max(coalesce(last_seen, excluded.last_seen), coalesce(excluded.last_seen, last_seen)),
        first_height = min(coalesce(first_height, excluded.first_height), coalesce(excluded.first_height, first_height)),
        last_height = max(coalesce(last_height, excluded.last_height), coalesce(excluded.last_height, last_height)),
        -- an example spent on chain replaces one seen in the mempool
        example_coin_id = CASE WHEN example_height IS NULL AND excluded.example_height IS NOT NULL
                               THEN excluded.example_coin_id ELSE example_coin_id END,
        example_puzzle_reveal = CASE WHEN example_height IS NULL AND excluded.example_height IS NOT NULL
                                     THEN excluded.example_puzzle_reveal ELSE example_puzzle_reveal END,
        example_height = coalesce(example_height, excluded.example_height)
"""


def write_scan_result(conn, result: ScanResult, source: str = None):
    """Add a scan result to the DB (in the caller's transaction): counts are added, so the
    full scan and the live scanner can write the same puzzles"""
    source = source or SOURCE_CHAIN
    conn.executemany(UPSERT_PUZZLE, [
        (fp, json.dumps(f[0]), source, f[4], f[5], f[1], f[2], f[3], f[6], f[7], f[8])
        for fp, f in result.found.items()])
    conn.executemany(
        "INSERT INTO puzzle_spends_blocks (puzzle_id, height, spends) "
        "SELECT id, ?, ? FROM puzzles WHERE layered_puzzle_fingerprint = ? "
        "ON CONFLICT (puzzle_id, height) DO UPDATE SET spends = spends + excluded.spends",
        [(h, n, fp) for (fp, h), n in result.blocks.items()])
    conn.executemany("INSERT OR REPLACE INTO block_times (height, timestamp) VALUES (?,?)",
                     result.block_times.items())



OVERRIDE_FIELDS = ('family', 'puzzle_type', 'custody', 'project')


def save_known_puzzle(layered_puzzle_fingerprint: str, sub_puzzle_hashes: list, sub_puzzle_names: list,
                      name: str, family: str = None, example_coin_id: str = None, tags: list = None,
                      overrides: dict = None, puzzle: PyProgram = None):
    """Save a name in catalog/layered_puzzles.json, and the overrides: family, puzzle_type,
    custody, project, each kept only when it is not the value the layers give (None removes
    it). Without overrides, family is the only one. An entry left with no name and no override
    is removed. Saving moves the entry out of puzzle_harvesting/layered_puzzles.json.
    tags: labels added by hand. puzzle: a puzzle reveal of the fingerprint, for the derived custody.
    The file is read from disk and only this entry changes, the edits made by hand stay.
    Raise ValueError if the file is not valid json."""
    changes = overrides if overrides is not None else {'family': family}
    derived = PUZ.classify_fingerprint(layered_puzzle_fingerprint, puzzle, overrides=False)

    def edit(layered: dict):
        entry = dict(layered.get(layered_puzzle_fingerprint, {}))
        if name:
            entry['name'] = name
        else:
            entry.pop('name', None)
        for field, value in changes.items():
            value = (value or '').strip() or None
            if value and value != derived[field][0]:
                entry[field] = value
            else:
                entry.pop(field, None)
        if tags:
            entry['tags'] = list(tags)
        overrides = {'name', 'family', 'puzzle_type', 'custody', 'project', 'tags'} & set(entry)
        if not overrides:
            return layered.pop(layered_puzzle_fingerprint, None) is not None
        entry['sub_puzzle_hashes'] = sub_puzzle_hashes
        entry['sub_puzzle_names'] = sub_puzzle_names
        if example_coin_id:
            entry['example_coin_id'] = example_coin_id
        layered[layered_puzzle_fingerprint] = entry

    with CONF.LAYERED_PUZZLES_LOCK:
        PUZ.update_catalog_file(CONF.KNOWN_LAYERED_PUZZLES_PATH, CONF.KNOWN_LAYERED_PUZZLES, edit)
    with CONF.UNKNOWN_LAYERED_PUZZLES_LOCK:
        if CONF.UNKNOWN_LAYERED_PUZZLES.pop(layered_puzzle_fingerprint, None) is not None:
            with open(CONF.UNKNOWN_LAYERED_PUZZLES_PATH, 'w') as f:
                json.dump(CONF.UNKNOWN_LAYERED_PUZZLES, f, indent=4)


@dataclass
class PuzzleEntry:
    layered_puzzle_fingerprint: str
    sub_puzzle_hashes: list
    source: str
    first_seen: float
    last_seen: float
    seen_count: int
    first_height: int
    last_height: int
    example_coin_id: str
    example_height: int
    example_puzzle_reveal: bytes

    def label(self):
        """Return (label, family, status)"""
        return catalog_label(self.layered_puzzle_fingerprint, self.example_puzzle_reveal)

    def classification(self):
        return catalog_classification(self.layered_puzzle_fingerprint, self.example_puzzle_reveal)

    def sub_puzzle_names(self):
        return [sub_puzzle_name(h) for h in self.sub_puzzle_hashes]

    @staticmethod
    def from_row(row):
        return PuzzleEntry(row[0], json.loads(row[1]), *row[2:])


class PuzzleCatalog:
    """All the puzzles seen. The DB is the source of truth (the full scan process writes it
    too); memory is a copy, updated by the live scanner and reloaded while the full scan runs."""

    COLUMNS = ("layered_puzzle_fingerprint, sub_puzzle_hashes, source, first_seen, last_seen, "
               "seen_count, first_height, last_height, example_coin_id, example_height, example_puzzle_reveal")

    def __init__(self, db_path):
        self.db_path = db_path
        self.lock = threading.Lock()  # memory
        self.db_lock = threading.Lock()  # the writes of this process, one at a time
        self.entries: dict[str, PuzzleEntry] = {}
        self.version = 0  # incremented on every change, the UI can use it to rebuild its tables
        self.reset_count = 0  # incremented by reset: a live scan in progress stops
        self._classes = {}  # fingerprint -> classification, see classifications()
        self._classes_generation = None
        self._classes_thread = None  # see classifications_ready()

    def connection(self):
        conn = WDB.get_connection(self.db_path)
        conn.execute("PRAGMA busy_timeout = 60000")  # the full scan writes the same DB
        return conn

    def load(self):
        """Read every puzzle from the DB; harvest the new unknown combinations"""
        conn = self.connection()
        try:
            create_puzzles_db(conn)
            rows = conn.execute(f"SELECT {self.COLUMNS} FROM puzzles").fetchall()
        finally:
            conn.close()
        entries = {row[0]: PuzzleEntry.from_row(row) for row in rows}
        with self.lock:
            new = [e for fp, e in entries.items() if fp not in self.entries]
            self.entries = entries
            self.version += 1
        with PUZ.harvest_batch():
            for entry in new:
                self.harvest(entry)

    @staticmethod
    def harvest(entry: 'PuzzleEntry'):
        """Put an unknown combination in puzzle_harvesting/ (PUZ.harvest_unknown)"""
        if not entry.example_puzzle_reveal:
            return
        try:
            PUZ.harvest_unknown(entry.layered_puzzle_fingerprint, entry.sub_puzzle_hashes,
                                PyProgram.from_bytes(bytes(entry.example_puzzle_reveal)))
        except Exception as e:
            logging(debug_logger, "DEBUG", f"PUZZLE HARVEST {entry.layered_puzzle_fingerprint[:40]} failed: {e}")

    def add_scan_result(self, result: ScanResult, live_range: tuple = None, reset_count: int = None):
        """Write the spends of the live scanner and update memory. live_range: (start, last)
        heights scanned by the live scanner. Nothing is written if the catalog was reset after
        the scan started (reset_count)"""
        with self.db_lock:
            if reset_count is not None and reset_count != self.reset_count:
                return False
            conn = self.connection()
            try:
                with conn:
                    write_scan_result(conn, result)
                    if live_range is not None:
                        conn.execute("INSERT OR REPLACE INTO scan_state (job, start_height, last_height, updated_at) "
                                     "VALUES (?,?,?,?)", (LIVE_SCAN_JOB, live_range[0], live_range[1], time.time()))
            finally:
                conn.close()
            new = []
            with self.lock:
                for fp, f in result.found.items():
                    e = self.entries.get(fp)
                    if e is None:
                        e = PuzzleEntry(fp, f[0], SOURCE_CHAIN, f[4], f[5], 0, f[2], f[3], f[6], f[7], f[8])
                        self.entries[fp] = e
                        new.append(e)
                    e.seen_count += f[1]
                    e.first_seen = min(x for x in (e.first_seen, f[4]) if x is not None)
                    e.last_seen = max(x for x in (e.last_seen, f[5]) if x is not None)
                    e.first_height = min(x for x in (e.first_height, f[2]) if x is not None)
                    e.last_height = max(x for x in (e.last_height, f[3]) if x is not None)
                    if e.example_height is None:
                        e.example_coin_id, e.example_height, e.example_puzzle_reveal = f[6], f[7], f[8]
                self.version += 1
        for entry in new:
            self.harvest(entry)
        return True

    def record_mempool(self, layered_puzzle_fingerprint: str, sub_puzzle_hashes: list, coin_id: str,
                       puzzle_reveal_hex: str):
        """A puzzle seen in the mempool: added if it is new, not counted (its spend is counted
        when it is in a block)"""
        with self.lock:
            if layered_puzzle_fingerprint in self.entries:
                return False
        now = time.time()
        reveal = bytes.fromhex(strip_0x(puzzle_reveal_hex))
        with self.db_lock:
            conn = self.connection()
            try:
                with conn:
                    conn.execute(UPSERT_PUZZLE, (layered_puzzle_fingerprint, json.dumps(sub_puzzle_hashes),
                                                 SOURCE_MEMPOOL, now, now, 0, None, None, coin_id, None, reveal))
            finally:
                conn.close()
        entry = PuzzleEntry(layered_puzzle_fingerprint, sub_puzzle_hashes, SOURCE_MEMPOOL, now, now, 0, None, None,
                            coin_id, None, reveal)
        with self.lock:
            self.entries.setdefault(layered_puzzle_fingerprint, entry)
            self.version += 1
        self.harvest(entry)
        return True

    def reset(self, live_start: int):
        """Delete every sighting and count (scan everything): the live scanner goes on from
        live_start, the full scan takes the heights before it"""
        with self.db_lock:
            conn = self.connection()
            try:
                with conn:
                    for table in ('puzzles', 'scan_chunks', 'scan_state', 'puzzle_spends_blocks', 'block_times'):
                        conn.execute(f"DELETE FROM {table}")
                    conn.execute("INSERT INTO scan_state (job, start_height, last_height, updated_at) VALUES (?,?,?,?)",
                                 (LIVE_SCAN_JOB, live_start, live_start - 1, time.time()))
            finally:
                conn.close()
            with self.lock:
                self.entries = {}
                self.version += 1
                self.reset_count += 1

    def set_name(self, layered_puzzle_fingerprint: str, name: str, family: str):
        """Save the name and family in layered_puzzles.json, an empty name removes the puzzle"""
        self.set_classification(layered_puzzle_fingerprint, name, {'family': family})

    def set_classification(self, layered_puzzle_fingerprint: str, name: str, overrides: dict):
        """Save the name and the overrides (family, puzzle_type, custody, project; None: the
        value the layers give) in layered_puzzles.json"""
        with self.lock:
            entry = self.entries[layered_puzzle_fingerprint]
            sub_puzzle_hashes = list(entry.sub_puzzle_hashes)
            example_coin_id = entry.example_coin_id
        # names from the shared catalogs only: unknown_puzz_NN names exist only in the local puzzle_harvesting/puzzles.json
        sub_puzzle_names = [CONF.KNOWN_PUZZLES[h]['name'] if h in CONF.KNOWN_PUZZLES else sub_puzzle_name(h)
                            for h in sub_puzzle_hashes]
        sub_puzzle_names = [name if not name.startswith('unknown_puzz_') else CONF.UNKNOWN_PUZZLE
                            for name in sub_puzzle_names]
        reveal = self.entries[layered_puzzle_fingerprint].example_puzzle_reveal
        save_known_puzzle(layered_puzzle_fingerprint, sub_puzzle_hashes, sub_puzzle_names, name, example_coin_id=example_coin_id,
                          overrides=overrides, puzzle=PyProgram.from_bytes(bytes(reveal)) if reveal else None)
        with self.lock:
            self.version += 1
        PUZ.bump_catalog_generation()

    def scan_state(self) -> dict:
        """job -> row of scan_state (start_height, last_height, end_height, updated_at, info dict)"""
        conn = self.connection()
        try:
            rows = conn.execute("SELECT job, start_height, last_height, end_height, updated_at, info "
                                "FROM scan_state").fetchall()
        finally:
            conn.close()
        return {r[0]: dict(start_height=r[1], last_height=r[2], end_height=r[3], updated_at=r[4],
                           info=json.loads(r[5]) if r[5] else {}) for r in rows}

    def get(self, layered_puzzle_fingerprint: str):
        with self.lock:
            entry = self.entries.get(layered_puzzle_fingerprint)
            return replace(entry) if entry else None

    def snapshot(self):
        with self.lock:
            return [replace(entry) for entry in self.entries.values()], self.version

    def classifications(self, entries: list) -> dict:
        """fingerprint -> classification (catalog_classification) of the entries, cached: it
        changes only with the catalog files (PUZ.catalog_generation)"""
        generation = PUZ.catalog_generation()
        if generation != self._classes_generation:
            self._classes, self._classes_generation = {}, generation
        out = {}
        for e in entries:
            c = self._classes.get(e.layered_puzzle_fingerprint)
            if c is None:
                c = self._classes[e.layered_puzzle_fingerprint] = e.classification()
            out[e.layered_puzzle_fingerprint] = c
        return out

    # a few new puzzles (e.g. from the live scan) are classified right away, more in a thread
    CLASSIFY_NOW = 20

    def classifications_ready(self, entries: list, threads: list = None, threads_lock=None):
        """classifications() without waiting: the classifications of the entries if they are
        all known, None otherwise, and a daemon thread computes them (added to threads, e.g.
        screenState.running_threads): call it again in the next frames. The first time a
        catalog is classified takes seconds (PUZ.walk_custody), then it is cached"""
        generation = PUZ.catalog_generation()
        if generation != self._classes_generation:
            self._classes, self._classes_generation = {}, generation
        classes = self._classes
        missing = [e for e in entries if e.layered_puzzle_fingerprint not in classes]
        if len(missing) <= self.CLASSIFY_NOW:
            for e in missing:
                classes[e.layered_puzzle_fingerprint] = e.classification()
            return {e.layered_puzzle_fingerprint: classes[e.layered_puzzle_fingerprint] for e in entries}
        if self._classes_thread is None or not self._classes_thread.is_alive():
            def classify():
                for e in missing:
                    if e.layered_puzzle_fingerprint not in classes:
                        # classes is the dict of this generation: a newer one starts again
                        classes[e.layered_puzzle_fingerprint] = e.classification()
            self._classes_thread = threading.Thread(target=classify, daemon=True, name='classify puzzles')
            self._classes_thread.start()
            if threads is not None:
                with threads_lock or contextlib.nullcontext():
                    threads.append(self._classes_thread)
        return None

    def classifications_progress(self) -> int:
        """How many entries are classified (in this catalog generation)"""
        return len(self._classes)

    def label(self, layered_puzzle_fingerprint: str):
        with self.lock:
            entry = self.entries.get(layered_puzzle_fingerprint)
            if entry is not None:
                return entry.label()
        return catalog_label(layered_puzzle_fingerprint)

    def families(self):
        """The families of puzzle_types.json"""
        with CONF.LAYERED_PUZZLES_LOCK:
            return list(CONF.PUZZLE_TYPES.get('families', {}))


def scan_coin_spend(catalog: PuzzleCatalog, coin_spend: dict, puzzle_hash_cache: dict):
    """Classify the puzzle of a mempool coin spend (rpc json) and add it to the catalog if it
    is new. Return the layered puzzle fingerprint."""
    coin = coin_spend['coin']
    puzzle_hash = strip_0x(coin['puzzle_hash'])

    cached = puzzle_hash_cache.get(puzzle_hash)
    if cached is not None:
        layered_puzzle_fingerprint, sub_puzzle_hashes = cached
    else:
        puzzle = PyProgram.fromhex(strip_0x(coin_spend['puzzle_reveal']))
        layered_puzzle_fingerprint, sub_puzzle_hashes = classify_puzzle(puzzle)
        if len(puzzle_hash_cache) > PUZZLE_HASH_CACHE_SIZE:
            puzzle_hash_cache.clear()
        puzzle_hash_cache[puzzle_hash] = (layered_puzzle_fingerprint, sub_puzzle_hashes)

    coin_id = UTILS.calc_coin_id(coin['parent_coin_info'], coin['puzzle_hash'], coin['amount']).hex()
    catalog.record_mempool(layered_puzzle_fingerprint, sub_puzzle_hashes, coin_id, coin_spend['puzzle_reveal'])
    return layered_puzzle_fingerprint


class ChainPuzzleScanner:
    """Count the puzzles spent in every new block, from the node DB. The first time it starts
    at the tip: the heights before are the full scan's. It goes on from the last height it
    scanned, also after a stop (a gap is filled when roto starts again)."""

    BATCH_BLOCKS = 50  # blocks written to the DB together

    def __init__(self, catalog: PuzzleCatalog, delay: float):
        self.catalog = catalog
        self.delay = delay
        self.status = 'waiting'
        self.start_height = None
        self.last_height = None
        self.tip = None
        self.puzzle_hash_cache = {}
        self.thread = None
        self.wake = threading.Event()

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
            try:
                FULL_SCAN.follow(self.catalog)
            except Exception as e:
                logging(debug_logger, "DEBUG", f"PUZZLE FULL SCAN follow error: {e}")
                UTILS.logging_traceback('PUZZLE FULL SCAN')
            self.wake.wait(self.delay)
            self.wake.clear()

    def scan(self):
        reset_count = self.catalog.reset_count
        node_conn = node_connection()
        try:
            self.tip = chain_tip(node_conn)
            state = self.catalog.scan_state().get(LIVE_SCAN_JOB)
            if state is None:
                # first start: from the tip, the full scan takes what is before
                self.catalog.add_scan_result(ScanResult(), (self.tip, self.tip - 1), reset_count)
                state = dict(start_height=self.tip, last_height=self.tip - 1)
            self.start_height, self.last_height = state['start_height'], state['last_height']
            height = self.last_height + 1
            while height <= self.tip:
                end = min(height + self.BATCH_BLOCKS, self.tip + 1)
                self.status = f'scanning blocks {height:,}-{end - 1:,} of {self.tip:,}'
                result = scan_heights(height, end, node_conn, self.puzzle_hash_cache)
                if not self.catalog.add_scan_result(result, (self.start_height, end - 1), reset_count):
                    return  # reset (scan everything): start again from the new state
                self.last_height = end - 1
                height = end
        finally:
            node_conn.close()
        self.status = f'up to date at {self.last_height:,}'


class FullScanJob:
    """The full scan of the chain: a separate process (the full_scan job of LAUNCHtiller) that scans the heights
    [0, end) in chunks with several workers and writes DB_PUZZLES. It survives a restart of
    roto and can be resumed: the chunks done are in scan_chunks."""

    def __init__(self):
        self.chunks_seen = None  # chunks done at the last follow: reload the catalog when it changes
        self.message = None

    def state(self, catalog: PuzzleCatalog) -> dict:
        """end, pid, running, chunks done and total, spends, started_at, finished_at"""
        full = catalog.scan_state().get(FULL_SCAN_JOB)
        conn = catalog.connection()
        try:
            done, spends, last_done = conn.execute(
                "SELECT COUNT(*), COALESCE(SUM(spends), 0), MAX(done_at) FROM scan_chunks").fetchone()
            ranges = conn.execute("SELECT start, end FROM scan_chunks ORDER BY start").fetchall()
        finally:
            conn.close()
        out = dict(end=None, pid=None, running=False, chunks_done=done, chunks_total=0, spends=spends,
                   ranges=ranges, last_done=last_done, info={}, eta=None)
        if full is not None:
            info = full['info']
            out.update(end=full['end_height'], pid=info.get('pid'), info=info,
                       chunks_total=-(-full['end_height'] // info.get('chunk', FULL_SCAN_CHUNK)))
            out['running'] = process_alive(info.get('pid'))
            # the time left, from the chunks done since this run started
            started = info.get('started_at') or 0
            conn = catalog.connection()
            try:
                since = conn.execute("SELECT COUNT(*) FROM scan_chunks WHERE done_at >= ?", (started,)).fetchone()[0]
            finally:
                conn.close()
            if out['running'] and since:
                out['eta'] = (time.time() - started) / since * (out['chunks_total'] - done)
        return out

    def start(self, catalog: PuzzleCatalog, fresh: bool, workers: int):
        """Start the full scan process; fresh: delete everything and scan from height 0 to the tip"""
        node_conn = node_connection()
        try:
            tip = chain_tip(node_conn)
        finally:
            node_conn.close()
        if fresh:
            catalog.reset(tip + 1)
            end = tip + 1
        else:
            end = (catalog.scan_state().get(FULL_SCAN_JOB) or {}).get('end_height') or tip + 1
        log = open(FULL_SCAN_LOG, 'a')
        process = subprocess.Popen([sys.executable, '-m', 'src.LAUNCHtiller', 'full_scan', str(catalog.db_path),
                                    '--to', str(end), '--workers', str(workers), '--chunk', str(FULL_SCAN_CHUNK)],
                                   stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
                                   cwd=os.getcwd())
        info = dict(pid=process.pid, workers=workers, chunk=FULL_SCAN_CHUNK, started_at=time.time())
        with catalog.db_lock:
            conn = catalog.connection()
            try:
                with conn:
                    conn.execute("INSERT OR REPLACE INTO scan_state (job, start_height, end_height, updated_at, info) "
                                 "VALUES (?,?,?,?,?)", (FULL_SCAN_JOB, 0, end, time.time(), json.dumps(info)))
            finally:
                conn.close()
        self.message = f"full scan started: heights 0-{end - 1:,}, {workers} workers"

    def stop(self, catalog: PuzzleCatalog):
        pid = self.state(catalog)['pid']
        if process_alive(pid):
            os.killpg(pid, signal.SIGTERM)  # the workers are in its process group
            self.message = "full scan stopped: resume it to scan the chunks left"

    def follow(self, catalog: PuzzleCatalog):
        """Called by the live scanner loop: reload the catalog when the full scan wrote new chunks"""
        conn = catalog.connection()
        try:
            done = conn.execute("SELECT COUNT(*) FROM scan_chunks").fetchone()[0]
        finally:
            conn.close()
        if done != self.chunks_seen:
            if self.chunks_seen is not None:
                catalog.load()
            self.chunks_seen = done


def process_alive(pid) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    # a finished child of this process stays a zombie until it is waited for
    try:
        done, _ = os.waitpid(pid, os.WNOHANG)
        return done == 0
    except ChildProcessError:
        return True  # not our child (started by an earlier roto): alive


def coverage(catalog: PuzzleCatalog, tip: int) -> dict:
    """The heights [0, tip] counted by the full scan and the live scanner: covered heights,
    the gaps (the first ones), the spends counted"""
    full = FULL_SCAN.state(catalog)
    live = catalog.scan_state().get(LIVE_SCAN_JOB)
    ranges = [(s, e) for s, e in full['ranges']]
    if live is not None and live['last_height'] >= live['start_height']:
        ranges.append((live['start_height'], live['last_height'] + 1))
    ranges.sort()
    covered, gaps, at = 0, [], 0
    for s, e in ranges:
        s, e = max(s, at), min(e, tip + 1)
        if s > at:
            gaps.append((at, s))
        if e > s:
            covered += e - s
            at = e
    if at <= tip:
        gaps.append((at, tip + 1))
    entries, _ = catalog.snapshot()
    return dict(tip=tip, covered=covered, gaps=gaps, spends=sum(e.seen_count for e in entries),
                puzzles=len(entries), full=full, live=live)


def first_height_since(conn, since: float):
    """The first height of block_times with a time from since (the times grow with the
    height): a binary search on the primary key. None if no block is that recent"""
    lo, hi = conn.execute("SELECT MIN(height), MAX(height) FROM block_times").fetchone()
    if hi is None or conn.execute("SELECT timestamp FROM block_times WHERE height = ?", (hi,)).fetchone()[0] < since:
        return None
    while lo < hi:
        mid = (lo + hi) // 2
        # the first block at mid or after (not every height is a transaction block)
        h, t = conn.execute("SELECT height, timestamp FROM block_times WHERE height >= ? ORDER BY height LIMIT 1",
                            (mid,)).fetchone()
        if t >= since:
            hi = mid  # no block in [mid, h): every height from mid is in
        else:
            lo = h + 1
    return lo


class WindowCounts:
    """Spends per puzzle in a time window, counted in a thread (a month of spends takes a few
    hundred ms) and kept until the catalog changes"""

    MAX_AGE = 15  # s, a result is reused for this long after the catalog changed

    def __init__(self, catalog: PuzzleCatalog):
        self.catalog = catalog
        self.lock = threading.Lock()
        self.results = {}  # window -> (version, computed_at, counts)
        self.running = set()

    def get(self, window: str):
        """fingerprint -> spends in the window, or None while it is counted the first time"""
        version = self.catalog.version
        with self.lock:
            cached = self.results.get(window)
            fresh = cached is not None and (cached[0] == version or time.time() - cached[1] < self.MAX_AGE)
            if not fresh and window not in self.running:
                self.running.add(window)
                threading.Thread(target=self._count, args=(window, version), daemon=True,
                                 name=f'puzzle window {window}').start()
        return cached[2] if cached else None

    def _count(self, window: str, version: int):
        try:
            counts = self.count(window)
            with self.lock:
                self.results[window] = (version, time.time(), counts)
        except Exception as e:
            logging(debug_logger, "DEBUG", f"PUZZLE WINDOW {window} error: {e}")
        finally:
            with self.lock:
                self.running.discard(window)

    def count(self, window: str) -> dict:
        seconds = TIME_WINDOWS[window]
        if seconds is None:
            entries, _ = self.catalog.snapshot()
            return {e.layered_puzzle_fingerprint: e.seen_count for e in entries}
        since = time.time() - seconds
        conn = self.catalog.connection()
        try:
            first = first_height_since(conn, since)
            if first is None:
                return {}
            # one range of the primary key (puzzle_id, height) a puzzle
            rows = conn.execute(
                "SELECT p.layered_puzzle_fingerprint, (SELECT SUM(b.spends) FROM puzzle_spends_blocks b "
                "WHERE b.puzzle_id = p.id AND b.height >= ?) AS n FROM puzzles p", (first,)).fetchall()
        finally:
            conn.close()
        return {fp: n for fp, n in rows if n}


@dataclass
class MempoolTx:
    tx_id: str
    cost: int
    fee: int
    coins_in: int
    coins_out: int
    layered_puzzle_fingerprints: list  # layered puzzle fingerprint of each coin spend
    removal_coin_ids: list
    spend_bundle: dict  # the whole bundle (RPC json), to explore it
    added_at: float
    gone_at: float = None  # when it left the mempool
    validated_at: float = None  # when it was found in a block

    @property
    def fee_per_cost(self):
        return self.fee / self.cost if self.cost else 0


class MempoolPuzzleScanner:
    """Keep the list of the mempool transactions and add their puzzles to the catalog.
    It scans every `delay` seconds, every `fast_delay` while a view asks for it (want_fast)."""

    # with more new transactions than this, load the whole mempool in one call
    MAX_SINGLE_CALLS = 50
    # a view calls want_fast every frame: fast scans stop this long after the view is closed
    FAST_HOLD = 2  # s
    # a transaction that left the mempool is checked on chain for this long, then dropped
    GONE_HOLD = 10  # s
    # validated transactions kept in memory after the views stop showing them: a block does not
    # say which bundles it contains, these are the ones the block view can recognize
    VALIDATED_KEEP = 100

    def __init__(self, catalog: PuzzleCatalog, delay: float, fast_delay: float, validated_delay: float):
        self.catalog = catalog
        self.delay = delay
        self.fast_delay = fast_delay
        self.validated_delay = validated_delay
        self.status = 'waiting'
        self.lock = threading.Lock()
        self.txs: dict[str, MempoolTx] = {}
        self.puzzle_hash_cache = {}
        self.thread = None
        self.fast_until = 0
        self.wake = threading.Event()  # ends the slow wait when a view asks for fast scans
        self.validated_txs = deque(maxlen=self.VALIDATED_KEEP)

    def want_fast(self):
        """Called every frame by the views that show the mempool"""
        now = time.time()
        if now > self.fast_until:
            self.wake.set()
        self.fast_until = now + self.FAST_HOLD

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
            delay = self.fast_delay if time.time() < self.fast_until else self.delay
            self.wake.wait(delay)
            self.wake.clear()

    def scan(self):
        tx_ids = {strip_0x(tx_id) for tx_id in RPC.call_rpc_node('get_all_mempool_tx_ids')}
        now = time.time()

        with self.lock:
            for tx_id, tx in list(self.txs.items()):
                if tx.validated_at is not None and now - tx.validated_at > self.validated_delay:
                    self.validated_txs.append(self.txs.pop(tx_id))
            gone_txs = [tx for tx_id, tx in self.txs.items() if tx_id not in tx_ids and tx.validated_at is None]
            new_tx_ids = tx_ids - set(self.txs)

        # a transaction that left the mempool is validated if its coins are spent on chain,
        # if not it was replaced or expired. Check it again for GONE_HOLD seconds, the block
        # could be not in the DB yet
        validated_tx_ids = self.validated_tx_ids(gone_txs)
        with self.lock:
            for tx in gone_txs:
                if tx.tx_id in validated_tx_ids:
                    tx.validated_at = now
                elif tx.gone_at is None:
                    tx.gone_at = now
                elif now - tx.gone_at > self.GONE_HOLD:
                    self.txs.pop(tx.tx_id, None)

        if len(new_tx_ids) > self.MAX_SINGLE_CALLS:
            items = RPC.call_rpc_node('get_all_mempool_items')
            items = {strip_0x(tx_id): item for tx_id, item in items.items() if strip_0x(tx_id) in new_tx_ids}
        else:
            items = {}
            for tx_id in new_tx_ids:
                items[tx_id] = RPC.call_rpc_node('get_mempool_item_by_tx_id', tx_id=f"0x{tx_id}")

        for tx_id, item in items.items():
            layered_puzzle_fingerprints = []
            for coin_spend in item['spend_bundle']['coin_spends']:
                layered_puzzle_fingerprints.append(scan_coin_spend(self.catalog, coin_spend, self.puzzle_hash_cache))
            removal_coin_ids = [UTILS.calc_coin_id(c['parent_coin_info'], c['puzzle_hash'], c['amount']).hex()
                                for c in item['removals']]
            tx = MempoolTx(tx_id, item['cost'], item['fee'], len(item['removals']),
                           len(item['additions']), layered_puzzle_fingerprints, removal_coin_ids, item['spend_bundle'],
                           time.time())
            with self.lock:
                self.txs[tx_id] = tx

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

    def get(self, tx_id: str):
        """The transaction, also if it just left the mempool; None if it is not known"""
        tx_id = strip_0x(tx_id)
        with self.lock:
            if tx_id in self.txs:
                return self.txs[tx_id]
            for tx in self.validated_txs:
                if tx.tx_id == tx_id:
                    return tx
        return None

    def known_txs(self):
        """All the transactions in memory: in the mempool, just left it, validated"""
        with self.lock:
            return list(self.txs.values()) + list(self.validated_txs)


def mempool_blocks(txs: list):
    """Split the transactions still in the mempool into the next blocks. txs sorted by fee per
    cost, highest first (MempoolPuzzleScanner.snapshot): each block takes them in order until
    the next one does not fit. An estimate: a farmer can skip one that does not fit and take
    a smaller one."""
    blocks = [WDB.MempoolBlock()]
    for tx in txs:
        if tx.validated_at is not None or tx.gone_at is not None:
            continue
        if blocks[-1].transactions and blocks[-1].total_cost + tx.cost > CONF.BLOCK_MAX_COST:
            blocks.append(WDB.MempoolBlock())
        blocks[-1].add_item(tx)
    return blocks


def block_spends_by_puzzle(catalog: PuzzleCatalog, header_hash: str, height: int, block_cost: int):
    """The coins spent in a block by puzzle type, it does not change the catalog. Returns (types,
    coin_types, coin_solutions): types is a list of (name, coins, execution cost, condition
    cost, byte cost) with the costs None if the spends can not be run, coin_types is coin id
    -> name, coin_solutions is coin id -> solution in hex.
    Execution and condition costs are measured for each spend. The byte cost is an estimate:
    the block pays for its compressed generator, what is left of the block cost is split by
    the size of the spends."""
    spends = RPC.call_rpc_node('get_block_spends', header_hash=header_hash)

    costs = None
    try:
        bundle = SpendBundle([CoinSpend.from_json_dict(spend) for spend in spends], G2Element())
        conditions = get_conditions_from_spendbundle(bundle, WDB.DEFAULT_CONSTANTS.MAX_BLOCK_COST_CLVM,
                                                      WDB.DEFAULT_CONSTANTS, height)
        costs = {bytes(spend.coin_id).hex(): (spend.execution_cost, spend.condition_cost)
                 for spend in conditions.spends}
    except Exception as e:
        logging(debug_logger, "DEBUG", f"BLOCK SPENDS costs of block {height} not available: {e}")

    def spend_size(spend):
        return len(spend['puzzle_reveal']) + len(spend['solution'])

    byte_cost_left = 0
    total_size = sum(spend_size(spend) for spend in spends)
    if costs is not None:
        byte_cost_left = max((block_cost or 0) - sum(a + b for a, b in costs.values()), 0)

    layered_puzzle_fingerprints = {}  # the same puzzle is often spent many times in a block
    kinds = {}
    coin_puzzles = {}
    coin_solutions = {}
    for spend in spends:
        coin = spend['coin']
        puzzle_hash = strip_0x(coin['puzzle_hash'])
        if puzzle_hash not in layered_puzzle_fingerprints:
            layered_puzzle_fingerprints[puzzle_hash] = classify_puzzle(PyProgram.fromhex(strip_0x(spend['puzzle_reveal'])))[0]
        name = catalog.label(layered_puzzle_fingerprints[puzzle_hash])[0] or 'unknown'

        coin_id = UTILS.calc_coin_id(coin['parent_coin_info'], coin['puzzle_hash'], coin['amount']).hex()
        coin_puzzles[coin_id] = name
        coin_solutions[coin_id] = strip_0x(spend['solution'])

        kind = kinds.setdefault(name, [name, 0, 0, 0, 0])
        kind[1] += 1
        if costs is not None:
            execution, condition = costs.get(coin_id, (0, 0))
            kind[2] += execution
            kind[3] += condition
            kind[4] += byte_cost_left * spend_size(spend) // total_size

    if costs is None:
        return [(kind[0], kind[1], None, None, None) for kind in kinds.values()], coin_puzzles, coin_solutions
    return [tuple(kind) for kind in kinds.values()], coin_puzzles, coin_solutions


def block_spend_bundles(scanner: MempoolPuzzleScanner, coin_solutions: dict) -> list:
    """The bundles known to be in a block: a block keeps the spends but not their bundles, a
    bundle is in the block if the block spends all its coins with the same solutions. Known are
    the ones in memory (scanner) and the ones saved in the spend bundle DB. Returns a list of
    (bundle hash, coins, cost, fee, source), cost and fee None for the saved ones."""
    def in_block(solutions: dict):
        return solutions and all(coin_solutions.get(coin_id) == solution for coin_id, solution in solutions.items())

    bundles = {}
    for tx in scanner.known_txs():
        if not any(coin_id in coin_solutions for coin_id in tx.removal_coin_ids):
            continue
        solutions = {}
        for spend in tx.spend_bundle['coin_spends']:
            coin = spend['coin']
            coin_id = UTILS.calc_coin_id(coin['parent_coin_info'], coin['puzzle_hash'], coin['amount']).hex()
            solutions[coin_id] = strip_0x(spend['solution'])
        if in_block(solutions):
            bundles[tx.tx_id] = (tx.tx_id, len(solutions), tx.cost, tx.fee, 'mempool')

    for bundle_hash, solutions in WDB.saved_bundles_spending_coins(CONF.DB_SB, list(coin_solutions)):
        if bundle_hash not in bundles and in_block(solutions):
            bundles[bundle_hash] = (bundle_hash, len(solutions), None, None, 'saved')
    return list(bundles.values())


def tx_type(catalog: PuzzleCatalog, layered_puzzle_fingerprints: list):
    """Names of the puzzles spent by a transaction, 'unknown' for the new ones"""
    counts = {}
    for fingerprint in layered_puzzle_fingerprints:
        name, family, status = catalog.label(fingerprint)
        name = name or 'unknown'
        counts[name] = counts.get(name, 0) + 1
    return ', '.join(f"{n}x {name}" if n > 1 else name for name, n in counts.items())


# --- behaviour hints: what the spends of each fingerprint output once run ------------------------
# resources/puzzles/chain_scan/behaviour.json (made by behaviour.py). Only shown, never saved as a
# value. Loaded and reloaded by CatalogFileWatcher (a thread): the dict is replaced whole, the
# screens read it without a lock; BEHAVIOUR_GENERATION changes with it (for the screens' caches).
BEHAVIOUR_HINTS = {}
BEHAVIOUR_FITS = {}  # custody class -> the custodies it fits
BEHAVIOUR_CLASSES = ['signed', 'by message', 'sends messages', 'by announcement', 'open', 'mixed']
BEHAVIOUR_NOT_RUN = 'not run'
BEHAVIOUR_GENERATION = 0
_behaviour_stamp = None


def reload_behaviour_hints() -> bool:
    """Load behaviour.json when it changed on disk (or went away). True when the hints changed"""
    global BEHAVIOUR_HINTS, BEHAVIOUR_FITS, BEHAVIOUR_GENERATION, _behaviour_stamp
    try:
        st = os.stat(CONF.BEHAVIOUR_HINTS_PATH)
        stamp = (st.st_mtime_ns, st.st_size)
    except FileNotFoundError:
        stamp = None
    if stamp == _behaviour_stamp:
        return False
    data, fits = {}, {}
    if stamp is not None:
        try:
            with open(CONF.BEHAVIOUR_HINTS_PATH) as f:
                saved = json.load(f)
            data, fits = saved['fingerprints'], saved.get('fits', {})
        except (ValueError, KeyError) as e:
            # being written: try again on the next check
            logging(debug_logger, "DEBUG", f"BEHAVIOUR {CONF.BEHAVIOUR_HINTS_PATH} not read: {e}")
            return False
    _behaviour_stamp = stamp
    BEHAVIOUR_HINTS, BEHAVIOUR_FITS = data, fits
    BEHAVIOUR_GENERATION += 1
    return True


BEHAVIOUR_NOTHING = 'nothing'  # the template mode of the spends that output nothing (behaviour.py)


def template_mode_text(t: dict) -> str:
    """One mode of a behaviour template as text (behaviour.py, step 6):
    'signed 90%: AGG_SIG_ME + CREATE_COIN x1-3 [RESERVE_FEE 35%]': the core kinds always output,
    the optional ones in [] with the share of the mode's spends that output them"""
    if t['mode'] == BEHAVIOUR_NOTHING:
        return f"{t['mode']} {t['share']:.0%}: outputs no condition"
    rng = lambda lo, hi: '' if hi == 1 else f' x{lo}' if lo == hi else f' x{lo}-{hi}'
    core = ' + '.join(k + rng(lo, hi) for k, lo, hi in t['core']) or '(no core)'
    optional = ' '.join(f'[{k}{rng(lo, hi)} {sh:.0%}]' for k, sh, lo, hi in t['optional'])
    return f"{t['mode']} {t['share']:.0%}: {core}" + (f' {optional}' if optional else '')


def behaviour_class(layered_puzzle_fingerprint: str) -> str:
    """The custody class of a fingerprint's spends, or 'not run'"""
    h = BEHAVIOUR_HINTS.get(layered_puzzle_fingerprint)
    return h['custody_hint'] if h else BEHAVIOUR_NOT_RUN


def behaviour_custody_hint(layered_puzzle_fingerprint: str, custody: str) -> list:
    """The custodies the class fits, when the layers give none (or unknown, hidden)"""
    if custody not in (None, 'UNKNOWN', 'HIDDEN'):
        return []
    return BEHAVIOUR_FITS.get(behaviour_class(layered_puzzle_fingerprint), [])


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
                if reload_behaviour_hints():
                    logging(debug_logger, "DEBUG", f"BEHAVIOUR hints loaded: {len(BEHAVIOUR_HINTS):,} fingerprints")
            except Exception as e:
                logging(debug_logger, "DEBUG", f"BEHAVIOUR hints error: {e}")
            try:
                reloaded = PUZ.reload_catalog_files()
                if reloaded:
                    PUZ.bump_catalog_generation()
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
FULL_SCAN = FullScanJob()
WINDOW_COUNTS = WindowCounts(CATALOG)
CHAIN_SCANNER = ChainPuzzleScanner(CATALOG, CONF.PUZZLE_SCAN_CHAIN_DELAY)
MEMPOOL_SCANNER = MempoolPuzzleScanner(CATALOG, CONF.PUZZLE_SCAN_MEMPOOL_DELAY,
                                       CONF.PUZZLE_SCAN_MEMPOOL_FAST_DELAY, CONF.MEMPOOL_VALIDATED_TX_DELAY)
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
