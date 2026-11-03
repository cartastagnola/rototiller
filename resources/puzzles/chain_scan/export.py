"""Write all_puzzles.json and all_puzzles.md from chain_puzzles.db.
Run from the repo root: .venv/bin/python resources/puzzles/chain_scan/export.py resources/puzzles/chain_scan"""
import json, sqlite3, sys, collections
sys.path.insert(0, '.')
import src.SCANtiller as SCAN
import src.TYPEStiller as TYPES
from chia.types.blockchain_format.program import Program as PyProgram

D = sys.argv[1]
conn = sqlite3.connect(f"{D}/chain_puzzles.db")
rows = conn.execute("SELECT puzzle_key, sub_puzzle_hashes, seen_count, first_height, last_height, "
                    "example_coin_id, example_height, example_puzzle_reveal FROM puzzles").fetchall()

# the keys in the db are the ones of the catalog at scan time: classify each example puzzle
# again with the current catalog (a puzzle added later changes the layers), rows that get
# the same key are merged
merged, rekeyed = {}, 0
for old_key, subs, count, first, last, coin, ex_h, reveal in rows:
    key, subs = SCAN.classify_puzzle(PyProgram.from_bytes(reveal))
    rekeyed += key != old_key
    m = merged.get(key)
    if m is None:
        merged[key] = [subs, count, first, last, coin, ex_h, count, reveal]
        continue
    m[1] += count
    m[2], m[3] = min(m[2], first), max(m[3], last)
    if count > m[6]:  # example of the row seen most
        m[4], m[5], m[6], m[7] = coin, ex_h, count, reveal
print(f"{len(rows):,} rows, {rekeyed:,} with a new key, {len(merged):,} keys after merging")

ps = []
for key, (subs, count, first, last, coin, ex_h, _, reveal) in sorted(merged.items(), key=lambda kv: -kv[1][1]):
    # the example reveal gives the custody
    c = SCAN.catalog_classification(key, reveal)
    name, family, status = c['label'], c['family'][0] or '', c['status']
    layers = [SCAN.sub_puzzle_name(h) for h in subs]
    # unknown layers: first 8 hex of the mod hash
    layers = [f"?{h[:8]}" if l == 'unknown_puzzle' else l for l, h in zip(layers, subs)]
    if key.startswith(SCAN.SHAPE_KEY_PREFIX): kind = 'not curried'
    elif key == SCAN.QUOTED_CONDITIONS_KEY: kind = 'quoted'
    elif len(subs) == 1: kind = '1 layer'
    else: kind = '2+ layers'
    ps.append(dict(key=key, kind=kind, known=status == TYPES.PuzzleStatus.KNOWN, name=name, family=family,
                   puzzle_type=c['puzzle_type'][0], custody=c['custody'][0], project=c['project'][0],
                   named=bool(c['name']), layers=layers, layer_hashes=subs, seen=count, first_height=first,
                   last_height=last, example_coin=coin, example_height=ex_h))
json.dump(ps, open(f"{D}/all_puzzles.json", 'w'), indent=1)

# variant groups: an unknown layer seen in only one puzzle key is per-instance data, it becomes
# '*' (a known puzzle curried twice is already one key: the + marker of the unroll)
lay = [p for p in ps if p['kind'] == '2+ layers']
nkeys = collections.Counter(l for p in lay for l in set(p['layers']))
groups = collections.defaultdict(list)
for p in lay:
    groups[tuple('*' if l.startswith('?') and nkeys[l] == 1 else l for l in p['layers'])].append(p)

c = collections.Counter((p['kind'], p['known']) for p in ps)
peak = max(p['last_height'] for p in ps)
with open(f"{D}/all_puzzles.md", 'w') as f:
    f.write(f"# All puzzles on chain\n\n{len(ps):,} puzzle keys, {sum(p['seen'] for p in ps):,} spends, "
            f"heights 0 to {peak:,}.\n\n"
            "A puzzle key is the list of layer mod hashes of a puzzle, joined with `|`: two coins "
            "with the same layers have the same key.\n\n"
            "`?abcd1234` = layer not in any catalog (first 8 hex of its mod hash). "
            "`(curried again)` = a known puzzle curried in two steps, the known puzzle follows. "
            "In variant groups, `*` = an unknown layer seen in only one puzzle key (per-instance data read "
            "as a layer), and `keys` = how many puzzle keys are in the group.\n\n")
    for (kind, known), n in sorted(c.items()):
        f.write(f"- {kind}, {'known' if known else 'unknown'}: {n:,}\n")
    f.write(f"\n## Variant groups with 2+ layers ({len(groups)})\n\n"
            "| spends | first | last | keys | known names | layers |\n|---:|---:|---:|---:|---|---|\n")
    for pat, g in sorted(groups.items(), key=lambda kv: -sum(p['seen'] for p in kv[1])):
        names = sorted({p['name'] for p in g if p['named']})
        f.write(f"| {sum(p['seen'] for p in g):,} | {min(p['first_height'] for p in g):,} | "
                f"{max(p['last_height'] for p in g):,} | {len(g)} | {'; '.join(names)} | {' / '.join(pat)} |\n")
    for kind in ('2+ layers', '1 layer', 'not curried', 'quoted'):
        title = f"with {kind}" if 'layer' in kind else kind
        f.write(f"\n## All {title}\n\n| spends | first | last | known | name or label | type | custody | project | layers |\n"
                "|---:|---:|---:|---|---|---|---|---|---|\n")
        for p in ps:
            if p['kind'] == kind:
                f.write(f"| {p['seen']:,} | {p['first_height']:,} | {p['last_height']:,} | "
                        f"{'yes' if p['known'] else ''} | {p['name'] or ''} | {p['puzzle_type'] or ''} | "
                        f"{p['custody'] or ''} | {p['project'] or ''} | {' / '.join(p['layers'])} |\n")
