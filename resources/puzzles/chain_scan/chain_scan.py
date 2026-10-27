"""Scan every spend of the chain and list all the puzzles that exist (by layers).
Reads the node DB read-only, writes OUT_DB. Resumable: chunks already done are skipped.
usage: chain_scan.py OUT_DB [--workers N] [--chunk N] [--from H] [--to H]"""
import argparse, json, multiprocessing as mp, os, sqlite3, sys, time, traceback
from collections import OrderedDict

REPO = '/home/pane/repos/rototiller'
sys.path.insert(0, REPO)
os.chdir(REPO)

import zstd
from chia_rs import FullBlock, get_spends_for_trusted_block
from chia.consensus.default_constants import DEFAULT_CONSTANTS
from chia.types.blockchain_format.program import Program as PyProgram
import src.CONFtiller as CONF
import src.SCANtiller as SCAN

CACHE_SIZE = 300_000


def node_conn():
    return sqlite3.connect(CONF.DB_BLOCKCHAIN_RO, uri=True, timeout=60)


def scan_chunk(args):
    start, end = args
    t0 = time.time()
    conn = node_conn()
    cache = OrderedDict()          # puzzle hash -> (key, sub hashes)
    found = {}                     # key -> [sub_hashes, count, first_h, last_h, coin_id, reveal]
    spends = blocks = errors = 0
    try:
        rows = conn.execute("SELECT height, block FROM full_blocks WHERE in_main_chain = 1 "
                            "AND height >= ? AND height < ? ORDER BY height", (start, end))
        for height, blob in rows:
            fb = FullBlock.from_bytes(zstd.decompress(blob))
            gen = fb.transactions_generator
            if gen is None:
                continue
            blocks += 1
            try:
                refs = []
                for ref_h in fb.transactions_generator_ref_list:
                    rb = conn.execute("SELECT block FROM full_blocks WHERE in_main_chain = 1 AND height = ?",
                                      (ref_h,)).fetchone()[0]
                    refs.append(bytes(FullBlock.from_bytes(zstd.decompress(rb)).transactions_generator))
                block_spends = get_spends_for_trusted_block(DEFAULT_CONSTANTS, gen, refs, 0)['block_spends']
            except Exception:
                errors += 1
                if errors <= 3:
                    sys.stderr.write(f"block {height}: {traceback.format_exc(limit=2)}\n")
                continue
            for cs in block_spends:
                spends += 1
                ph = bytes(cs.coin.puzzle_hash)
                hit = cache.get(ph)
                if hit is None:
                    hit = SCAN.classify_puzzle(PyProgram.from_bytes(bytes(cs.puzzle_reveal)))
                    cache[ph] = hit
                    if len(cache) > CACHE_SIZE:
                        cache.popitem(last=False)
                else:
                    cache.move_to_end(ph)
                key, subs = hit
                f = found.get(key)
                if f is None:
                    found[key] = [subs, 1, height, height, cs.coin.name().hex(), bytes(cs.puzzle_reveal)]
                else:
                    f[1] += 1
                    f[3] = height
    finally:
        conn.close()
    return start, end, found, blocks, spends, errors, time.time() - t0


def open_out(path):
    out = sqlite3.connect(path)
    out.execute("""CREATE TABLE IF NOT EXISTS puzzles (
        puzzle_key TEXT PRIMARY KEY, sub_puzzle_hashes TEXT, seen_count INTEGER,
        first_height INTEGER, last_height INTEGER, example_coin_id TEXT, example_height INTEGER,
        example_puzzle_reveal BLOB)""")
    out.execute("""CREATE TABLE IF NOT EXISTS chunks (
        start INTEGER PRIMARY KEY, end INTEGER, tx_blocks INTEGER, spends INTEGER, errors INTEGER, seconds REAL)""")
    out.commit()
    return out


def merge(out, found):
    for key, (subs, count, first_h, last_h, coin_id, reveal) in found.items():
        row = out.execute("SELECT seen_count, first_height, last_height FROM puzzles WHERE puzzle_key = ?",
                          (key,)).fetchone()
        if row is None:
            out.execute("INSERT INTO puzzles VALUES (?,?,?,?,?,?,?,?)",
                        (key, json.dumps(subs), count, first_h, last_h, coin_id, first_h, reveal))
        else:
            out.execute("UPDATE puzzles SET seen_count = ?, first_height = ?, last_height = ? WHERE puzzle_key = ?",
                        (row[0] + count, min(row[1], first_h), max(row[2], last_h), key))
            if first_h < row[1]:   # keep the oldest example
                out.execute("UPDATE puzzles SET example_coin_id = ?, example_height = ?, example_puzzle_reveal = ? "
                            "WHERE puzzle_key = ?", (coin_id, first_h, reveal, key))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out_db')
    ap.add_argument('--workers', type=int, default=12)
    ap.add_argument('--chunk', type=int, default=20_000)
    ap.add_argument('--from', dest='start', type=int, default=0)
    ap.add_argument('--to', dest='end', type=int, default=None)
    a = ap.parse_args()

    end = a.end
    if end is None:
        c = node_conn()
        end = c.execute("SELECT MAX(height) FROM full_blocks WHERE in_main_chain = 1").fetchone()[0] + 1
        c.close()
    out = open_out(a.out_db)
    done = {r[0] for r in out.execute("SELECT start FROM chunks")}
    todo = [(s, min(s + a.chunk, end)) for s in range(a.start, end, a.chunk) if s not in done]
    total = len(todo)
    print(f"{total} chunks to scan ({len(done)} done), heights {a.start:,}..{end:,}, {a.workers} workers", flush=True)
    t0 = time.time(); n = 0; spends_all = 0
    with mp.Pool(a.workers) as pool:
        for start, stop, found, blocks, spends, errors, secs in pool.imap_unordered(scan_chunk, todo):
            merge(out, found)
            out.execute("INSERT OR REPLACE INTO chunks VALUES (?,?,?,?,?,?)", (start, stop, blocks, spends, errors, secs))
            out.commit()
            n += 1; spends_all += spends
            el = time.time() - t0
            eta = el / n * (total - n)
            keys = out.execute("SELECT COUNT(*) FROM puzzles").fetchone()[0]
            print(f"[{n}/{total}] {start:,}-{stop:,}: {blocks} tx blocks, {spends:,} spends, {errors} errors, "
                  f"{secs:.0f}s | puzzles {keys:,} | elapsed {el/60:.0f} min, eta {eta/60:.0f} min", flush=True)
    print("done", flush=True)


if __name__ == '__main__':
    main()
