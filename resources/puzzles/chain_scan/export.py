"""Write all_puzzles.json and all_puzzles.md from roto's puzzles DB (db/DBiller_puzzles.db, filled
by the puzzle scanner view: scan everything), or from another DB with the same puzzles table.
Run from the repo root: .venv/bin/python resources/puzzles/chain_scan/export.py resources/puzzles/chain_scan [DB]"""
import json, sqlite3, sys, collections
sys.path.insert(0, '.')
import src.CONFtiller as CONF
import src.SCANtiller as SCAN
import src.PUZZLEtiller as PUZ
import src.TYPEStiller as TYPES
from chia.types.blockchain_format.program import Program as PyProgram

D = sys.argv[1]
conn = sqlite3.connect(sys.argv[2] if len(sys.argv) > 2 else CONF.DB_PUZZLES)
# the puzzles spent on chain (the ones only seen in the mempool have no height)
rows = conn.execute("SELECT layered_puzzle_fingerprint, sub_puzzle_hashes, seen_count, first_height, last_height, "
                    "example_coin_id, example_height, example_puzzle_reveal FROM puzzles "
                    "WHERE first_height IS NOT NULL").fetchall()

# the fingerprints in the db are the ones of the catalog at scan time: classify each example puzzle
# again with the current catalog (a puzzle added later changes the layers), rows that get
# the same fingerprint are merged
merged, changed = {}, 0
for old_fp, subs, count, first, last, coin, ex_h, reveal in rows:
    fp, subs = SCAN.classify_puzzle(PyProgram.from_bytes(reveal))
    changed += fp != old_fp
    m = merged.get(fp)
    if m is None:
        merged[fp] = [subs, count, first, last, coin, ex_h, count, reveal]
        continue
    m[1] += count
    m[2], m[3] = min(m[2], first), max(m[3], last)
    if count > m[6]:  # example of the row seen most
        m[4], m[5], m[6], m[7] = coin, ex_h, count, reveal
print(f"{len(rows):,} rows, {changed:,} with a new fingerprint, {len(merged):,} fingerprints after merging")

ps = []
for fp, (subs, count, first, last, coin, ex_h, _, reveal) in sorted(merged.items(), key=lambda kv: -kv[1][1]):
    # the example reveal gives the custody
    c = SCAN.catalog_classification(fp, reveal)
    name, family, status = c['label'], c['family'][0] or '', c['status']
    # a name from puzzle_harvesting/ (unknown_layered_NN) is local to each user: not written
    if name and name == CONF.UNKNOWN_LAYERED_PUZZLES.get(fp, {}).get('name'):
        name = ''
    layers = [SCAN.sub_puzzle_name(h) for h in subs]
    # unknown layers: first 8 hex of the mod hash, also the ones named in puzzle_harvesting/
    # (unknown_puzz_NN: local to each user, not part of the catalog)
    layers = [f"?{h[:8]}" if l == CONF.UNKNOWN_PUZZLE or h in CONF.UNKNOWN_PUZZLES else l for l, h in zip(layers, subs)]
    if fp.startswith(SCAN.SHAPE_FINGERPRINT_PREFIX): kind = 'not curried'
    elif fp == SCAN.QUOTED_CONDITIONS_FINGERPRINT: kind = 'quoted'
    elif len(subs) == 1: kind = '1 layer'
    else: kind = '2+ layers'
    ps.append(dict(layered_puzzle_fingerprint=fp, kind=kind, known=status != TYPES.PuzzleStatus.UNKNOWN, status=str(status), name=name, family=family,
                   puzzle_type=c['puzzle_type'][0], custody=c['custody'][0], project=c['project'][0], project_label=PUZ.project_label(c['project'][0]),
                   project_dependencies=c['project_dependencies'][0],
                   named=bool(c['name']), layers=layers, layer_hashes=subs, seen=count, first_height=first,
                   last_height=last, example_coin=coin, example_height=ex_h,
                   # where each value comes from: 'layer N', 'walk', 'held', 'set', ...
                   origins={f: c[f][1] for f in ('family', 'puzzle_type', 'custody', 'project')}))
json.dump(ps, open(f"{D}/all_puzzles.json", 'w'), indent=1)

# variant groups: an unknown layer seen in only one layered puzzle fingerprint is per-instance data, it becomes
# '*' (a known puzzle curried twice is already one fingerprint: the + marker of the unroll)
lay = [p for p in ps if p['kind'] == '2+ layers']
nkeys = collections.Counter(l for p in lay for l in set(p['layers']))
groups = collections.defaultdict(list)
for p in lay:
    groups[tuple('*' if l.startswith('?') and nkeys[l] == 1 else l for l in p['layers'])].append(p)

c = collections.Counter((p['kind'], p['known']) for p in ps)
peak = max(p['last_height'] for p in ps)
with open(f"{D}/all_puzzles.md", 'w') as f:
    f.write(f"# All puzzles on chain\n\n{len(ps):,} layered puzzle fingerprints, {sum(p['seen'] for p in ps):,} spends, "
            f"heights 0 to {peak:,}.\n\n"
            "A layered puzzle fingerprint is the list of layer mod hashes of a puzzle, joined with `|`: two coins "
            "with the same layers have the same fingerprint.\n\n"
            "`?abcd1234` = layer not in any catalog (first 8 hex of its mod hash). "
            "`(curried again)` = a known puzzle curried in two steps, the known puzzle follows. "
            "In variant groups, `*` = an unknown layer seen in only one layered puzzle fingerprint (per-instance data read "
            "as a layer), and `fingerprints` = how many layered puzzle fingerprints are in the group.\n\n")
    for (kind, known), n in sorted(c.items()):
        f.write(f"- {kind}, {'known' if known else 'unknown'}: {n:,}\n")
    f.write(f"\n## Variant groups with 2+ layers ({len(groups)})\n\n"
            "| spends | first | last | fingerprints | known names | layers |\n|---:|---:|---:|---:|---|---|\n")
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
                        f"{'yes' if p['known'] else ''} | {p['name'] or ''} | {PUZ.value_label('puzzle_type', p['puzzle_type']) or ''} | "
                        f"{PUZ.value_label('custody', p['custody']) or ''} | {p['project_label'] or ''}{' (depends on ' + ', '.join(PUZ.project_label(d) for d in p['project_dependencies']) + ')' if p['project_dependencies'] else ''} | {' / '.join(p['layers'])} |\n")
