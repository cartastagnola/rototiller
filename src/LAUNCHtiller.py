"""The jobs roto starts as separate processes: each is a subcommand of this file. They go on if
roto is closed. The logic of a job is in its own module; here there is only the entry point.

This is a separate file so that the job process does not load the modules roto starts from
(`python -m src.SCANtiller` would load SCANtiller twice, as __main__ and as src.SCANtiller,
each copy with its own catalog and scanners).

usage (from the repo root): python -m src.LAUNCHtiller JOB ...

jobs:
- full_scan: the full scan of the chain, count every puzzle spent from height 0, in chunks of
  heights, with several worker processes. Started by roto from the puzzle scanner view (see
  SCANtiller.FullScanJob). It can be resumed: the chunks done are in the scan_chunks table.
  It writes DB_PUZZLES only (puzzles, puzzle_spends_blocks, block_times, scan_chunks):
  roto reloads its catalog from the DB and harvests the unknown puzzles itself.
  python -m src.LAUNCHtiller full_scan DB_PUZZLES --to END [--workers N] [--chunk N]
"""
import argparse
import multiprocessing as mp
import time

import src.SCANtiller as SCAN


def full_scan(a):
    catalog = SCAN.PuzzleCatalog(a.db)
    conn = catalog.connection()
    SCAN.create_puzzles_db(conn)
    done = {row[0] for row in conn.execute("SELECT start FROM scan_chunks")}
    todo = [(s, min(s + a.chunk, a.end)) for s in range(0, a.end, a.chunk) if s not in done]
    print(f"{len(todo)} chunks to scan ({len(done)} done), heights 0..{a.end:,}, {a.workers} workers", flush=True)

    t0, n = time.time(), 0
    with mp.Pool(a.workers) as pool:
        for start, end, result, seconds in pool.imap_unordered(SCAN.scan_chunk, todo):
            with conn:
                SCAN.write_scan_result(conn, result)
                conn.execute("INSERT OR REPLACE INTO scan_chunks VALUES (?,?,?,?,?,?,?)",
                             (start, end, result.tx_blocks, result.spends, result.errors, seconds, time.time()))
            n += 1
            elapsed = time.time() - t0
            print(f"[{n}/{len(todo)}] {start:,}-{end:,}: {result.tx_blocks} tx blocks, {result.spends:,} spends, "
                  f"{result.errors} errors, {seconds:.0f}s | elapsed {elapsed / 60:.0f} min, "
                  f"eta {elapsed / n * (len(todo) - n) / 60:.0f} min", flush=True)
    conn.close()
    print("done", flush=True)


def main():
    ap = argparse.ArgumentParser()
    jobs = ap.add_subparsers(dest='job', required=True)

    p = jobs.add_parser('full_scan', help='count every puzzle spent from height 0')
    p.add_argument('db')
    p.add_argument('--to', dest='end', type=int, required=True, help='scan the heights [0, END)')
    p.add_argument('--workers', type=int, default=12)
    p.add_argument('--chunk', type=int, default=SCAN.FULL_SCAN_CHUNK)
    p.set_defaults(run=full_scan)

    a = ap.parse_args()
    a.run(a)


if __name__ == '__main__':
    main()
