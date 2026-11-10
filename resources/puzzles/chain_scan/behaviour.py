"""Behaviour of the puzzles: run spends of every layered puzzle fingerprint with their on-chain
solution, and write behaviour.json: what each one outputs, a custody hint from it, the known
puzzles it behaves like, and where the known ones disagree with the catalog.
PLAN.md, "New ways to classify puzzles", point 3. Hints only: nothing here sets a name or a value.

Run from the repo root (the node DB and db/DBiller_puzzles.db are read, nothing is written there):
  .venv/bin/python resources/puzzles/chain_scan/behaviour.py resources/puzzles/chain_scan [--collect [BLOCKS]]
--collect reads the blocks again (BLOCKS random ones, default 30,000, plus the heights where
DBiller_puzzles.db saw each fingerprint) and saves the runs in behaviour_runs.json; without it the
saved runs are analysed again (after a catalog change: run export.py first, it gives the labels).

The steps:
1. runs: each spend is run (puzzle with solution); a run is kept as its conditions by kind with
   their counts and a few flags on the coins it creates (how many, one with the same puzzle
   hash, an odd amount, the amount kept, less or more).
2. layer stamps: a family layer (CAT, singleton top layer) adds its own conditions to every spend
   (the CAT ring, the singleton's lineage checks). Measured, not written by hand: for each outer
   layer with a family, in 3 fingerprints or more, a condition kind with count k is its stamp
   when 98% of the runs of its puzzles have it at least k times. Each run loses its outer layer's stamp: what is left is the
   custody and the action.
3. custody hint, per run, from what is left: signed (an AGG_SIG), by message (RECEIVE_MESSAGE),
   sends messages (SEND_MESSAGE), by announcement (asserts a coin or puzzle announcement), open
   (none of these). A fingerprint gets the class of 80% of its runs, else "mixed"; from 1 run
   too (most unknown puzzles were spent once or twice ever), with its number of runs.
4. behaves like: a profile per fingerprint (the share of runs with each condition kind and each
   flag); similarity = weighted Jaccard (sum of minimums / sum of maximums). The nearest known
   fingerprints, by their label.
6. template: what a fingerprint's spends output, merged into one description. The runs are split
   into modes by their custody class (a spend that outputs nothing once the stamp is removed is
   the mode "nothing"): a plot NFT claims rewards (signed) or does its other action (by
   announcement), two modes, not one action with extras. In each mode, the core is the condition
   kinds of 95% of its runs (always done), the optional ones those of 1% or more with their share
   (what the user chose: change, fee, offer), the rest is counted as rare; counts are kept as
   ranges (CREATE_COIN x1-33). Modes under 1% of the runs are counted as rare too. The template key
   is the core kinds of the modes of 10% or more: fingerprints with the same key are grouped.
5. disagreements, on known fingerprints: the custody hint does not fit the custody of the catalog
   (only for the custodies the conditions can tell: KEY, KEYS, SINGLETON, OFFER, ANYONE; 3 runs
   or more)."""
import collections, json, multiprocessing as mp, random, sqlite3, sys, time
sys.path.insert(0, '.')
import src.CONFtiller as CONF
import src.SCANtiller as SCAN
from chia.types.blockchain_format.program import Program as PyProgram

OP = {1: 'REMARK', 43: 'AGG_SIG_PARENT', 44: 'AGG_SIG_PUZZLE', 45: 'AGG_SIG_AMOUNT', 46: 'AGG_SIG_PUZZLE_AMOUNT',
      47: 'AGG_SIG_PARENT_AMOUNT', 48: 'AGG_SIG_PARENT_PUZZLE', 49: 'AGG_SIG_UNSAFE', 50: 'AGG_SIG_ME',
      51: 'CREATE_COIN', 52: 'RESERVE_FEE', 60: 'CREATE_COIN_ANN', 61: 'ASSERT_COIN_ANN', 62: 'CREATE_PUZ_ANN',
      63: 'ASSERT_PUZ_ANN', 64: 'ASSERT_CONCURRENT_SPEND', 65: 'ASSERT_CONCURRENT_PUZ', 66: 'SEND_MESSAGE',
      67: 'RECEIVE_MESSAGE', 70: 'ASSERT_MY_COIN_ID', 71: 'ASSERT_MY_PARENT_ID', 72: 'ASSERT_MY_PUZZLEHASH',
      73: 'ASSERT_MY_AMOUNT', 74: 'ASSERT_MY_BIRTH_SECONDS', 75: 'ASSERT_MY_BIRTH_HEIGHT', 76: 'ASSERT_EPHEMERAL',
      80: 'ASSERT_SECONDS_REL', 81: 'ASSERT_SECONDS_ABS', 82: 'ASSERT_HEIGHT_REL', 83: 'ASSERT_HEIGHT_ABS',
      84: 'ASSERT_BEFORE_SECONDS_REL', 85: 'ASSERT_BEFORE_SECONDS_ABS', 86: 'ASSERT_BEFORE_HEIGHT_REL',
      87: 'ASSERT_BEFORE_HEIGHT_ABS'}
CAP = 300               # runs kept per fingerprint per worker
WORKERS = 8
STAMP_SHARE = 0.98      # a condition is a layer's stamp when this share of its runs has it
STAMP_MIN_RUNS = 100    # fewer runs: no stamp measured for the layer
STAMP_MIN_FPS = 3       # fingerprints (with MIN_RUNS each) the layer must be in: else the stamp
                        # would be the whole behaviour of one puzzle
HINT_SHARE = 0.8        # a fingerprint gets a custody hint when this share of its runs agree
MIN_RUNS = 5            # a known fingerprint needs this many runs to be compared with
DISAGREE_RUNS = 3       # a disagreement needs this many runs
CORE_SHARE = 0.95       # template: a condition kind of this share of a mode's runs is its core
OPTIONAL_SHARE = 0.01   # template: rarer kinds and modes are only counted as rare
KEY_MODE_SHARE = 0.10   # template: the modes of this share or more make the template key
NOTHING = SCAN.BEHAVIOUR_NOTHING  # template: the mode of the spends that output nothing (after the stamp)
# what each custody hint fits, of the custodies the conditions can tell
FITS = {'signed': {'KEY', 'KEYS'}, 'by message': {'SINGLETON', 'KEYS'}, 'sends messages': {'KEYS'},
        'by announcement': {'SINGLETON'}, 'open': {'OFFER', 'ANYONE'}}
TOLD = {'KEY', 'KEYS', 'SINGLETON', 'OFFER', 'ANYONE'}


# --- 1. runs ------------------------------------------------------------------------------------

def run_key(spend) -> str:
    """'KIND=n,KIND=n|flag flag': the conditions of a spend by kind, and flags on its children"""
    puzzle, solution = PyProgram.from_bytes(bytes(spend.puzzle_reveal)), PyProgram.from_bytes(bytes(spend.solution))
    kinds, kids = collections.Counter(), []
    for c in puzzle.run(solution).as_iter():
        c = list(c.as_iter())
        if not c or c[0].atom is None:
            continue
        op = int.from_bytes(c[0].atom, 'big')
        kinds[OP.get(op, f'op{op}')] += 1
        if op == 51:
            kids.append((bytes(c[1].atom), c[2].as_int()))
    flags = [f"kids={len(kids) if len(kids) < 3 else '3+'}"]
    if any(ph == bytes(spend.coin.puzzle_hash) for ph, _ in kids): flags.append('same_ph_child')
    if any(a % 2 for _, a in kids): flags.append('odd_child')
    if kids:
        out, amount = sum(a for _, a in kids), spend.coin.amount
        flags.append('amount_kept' if out == amount else 'amount_less' if out < amount else 'amount_more')
    return ','.join(f'{k}={v}' for k, v in sorted(kinds.items())) + '|' + ' '.join(flags)


def collect_heights(heights):
    """Worker: run the spends of the blocks at these heights -> {fingerprint: [runs, errors]}"""
    node, ref, cache, found = SCAN.node_connection(), {}, {}, {}
    for h in heights:
        row = node.execute("SELECT block FROM full_blocks WHERE in_main_chain = 1 AND height = ?", (h,)).fetchone()
        if not row:
            continue
        try:
            ts, spends = SCAN.block_spends(node, row[0], ref)
        except Exception:
            continue
        for s in spends:
            ph = bytes(s.coin.puzzle_hash)
            fp = cache.get(ph)
            if fp is None:
                fp = cache[ph] = SCAN.classify_puzzle(PyProgram.from_bytes(bytes(s.puzzle_reveal)))[0]
            f = found.setdefault(fp, [collections.Counter(), 0])
            if sum(f[0].values()) >= CAP:
                continue
            try:
                f[0][run_key(s)] += 1
            except Exception:
                f[1] += 1
    return found


def collect(n_blocks: int) -> dict:
    node = SCAN.node_connection()
    tip = SCAN.chain_tip(node)
    # the heights where each fingerprint was seen: every one gets a few runs, also the rare ones
    seen = set()
    pz = sqlite3.connect(CONF.DB_PUZZLES)
    for row in pz.execute("SELECT first_height, last_height, example_height FROM puzzles"):
        seen.update(h for h in row if h is not None)
    # ~30 blocks a puzzle, spread over its whole history (sampled in the DB: the busiest have millions)
    for (h,) in pz.execute(
            "SELECT height FROM (SELECT height, ROW_NUMBER() OVER (PARTITION BY puzzle_id ORDER BY height) AS rn, "
            "COUNT(*) OVER (PARTITION BY puzzle_id) AS n FROM puzzle_spends_blocks) WHERE rn % MAX(1, n / 30) = 0"):
        seen.add(h)
    # random blocks over the whole chain (from the first transaction block): many runs of the common ones
    rnd = set(random.Random(1).sample(range(225000, tip), n_blocks))
    heights = sorted(seen | rnd)
    random.Random(2).shuffle(heights)
    chunks = [heights[i::WORKERS * 4] for i in range(WORKERS * 4)]
    t0, runs = time.time(), {}
    with mp.Pool(WORKERS) as pool:
        for found in pool.imap_unordered(collect_heights, chunks):
            for fp, (c, e) in found.items():
                r = runs.setdefault(fp, {'runs': collections.Counter(), 'errors': 0})
                r['runs'].update(c)
                r['errors'] += e
    print(f"{len(heights):,} blocks ({len(seen):,} where a fingerprint was seen) in {time.time() - t0:.0f} s, "
          f"{len(runs):,} fingerprints", file=sys.stderr)
    return dict(blocks=len(heights), tip=tip, made=time.strftime('%Y-%m-%d'),
                fingerprints={fp: {'runs': dict(r['runs']), 'errors': r['errors']} for fp, r in runs.items()})


# --- 2.-5. analysis -----------------------------------------------------------------------------

def parse(key: str):
    kinds, flags = key.split('|')
    return {k: int(v) for k, v in (x.split('=') for x in kinds.split(',') if x)}, flags.split()


def agg_sig(kinds) -> bool:
    return any(k.startswith('AGG_SIG') for k in kinds)


def custody_class(kinds: dict) -> str:
    if agg_sig(kinds): return 'signed'
    if kinds.get('RECEIVE_MESSAGE'): return 'by message'
    if kinds.get('SEND_MESSAGE'): return 'sends messages'
    if kinds.get('ASSERT_PUZ_ANN') or kinds.get('ASSERT_COIN_ANN'): return 'by announcement'
    return 'open'


def measure_stamps(fps: dict, families: dict) -> dict:
    """outer layer hash -> {kind: count}: the conditions the layer adds to every spend"""
    per_layer, n_fps = collections.defaultdict(list), collections.Counter()
    for fp, d in fps.items():
        layers = fp.split('|')
        if len(layers) > 1 and layers[0] in families:
            n_fps[layers[0]] += sum(d['runs'].values()) >= MIN_RUNS
            for key, n in d['runs'].items():
                per_layer[layers[0]].append((parse(key)[0], n))
    stamps = {}
    for layer, runs in per_layer.items():
        total = sum(n for _, n in runs)
        if total < STAMP_MIN_RUNS or n_fps[layer] < STAMP_MIN_FPS:
            continue
        stamp = {}
        for kind in {k for kinds, _ in runs for k in kinds}:
            k = 1
            while sum(n for kinds, n in runs if kinds.get(kind, 0) >= k) >= STAMP_SHARE * total:
                k += 1
            if k > 1:
                stamp[kind] = k - 1
        stamps[layer] = dict(sorted(stamp.items()))
    return stamps


def template(modes: dict, n: int) -> dict:
    """The modes of a fingerprint's runs, each with its core and optional condition kinds
    (step 6). modes: mode -> [(kinds left after the stamp, runs)]"""
    out, rare = [], 0
    for mode, runs in sorted(modes.items(), key=lambda kv: -sum(c for _, c in kv[1])):
        m = sum(c for _, c in runs)
        if m < OPTIONAL_SHARE * n:
            rare += m
            continue
        have, lo, hi = collections.Counter(), {}, {}
        for kinds, c in runs:
            for k, v in kinds.items():
                have[k] += c
                lo[k], hi[k] = min(lo.get(k, v), v), max(hi.get(k, 0), v)
        core = [[k, lo[k], hi[k]] for k in sorted(have) if have[k] >= CORE_SHARE * m]
        optional = [[k, round(have[k] / m, 3), lo[k], hi[k]] for k in sorted(have, key=lambda k: -have[k])
                    if OPTIONAL_SHARE * m <= have[k] < CORE_SHARE * m]
        rare_kinds = sum(1 for k in have if have[k] < OPTIONAL_SHARE * m)
        out.append(dict(mode=mode, share=round(m / n, 3), runs=m, core=core, optional=optional, rare_kinds=rare_kinds))
    key = ' | '.join(f"{t['mode']}: {' + '.join(k for k, _, _ in t['core']) or '-'}"
                     for t in out if t['share'] >= KEY_MODE_SHARE)
    return dict(modes=out, rare=round(rare / n, 3) if n else 0, key=key)


def similarity(a: dict, b: dict) -> float:
    keys = a.keys() | b.keys()
    top = sum(max(a.get(k, 0), b.get(k, 0)) for k in keys)
    return sum(min(a.get(k, 0), b.get(k, 0)) for k in keys) / top if top else 0.0


def analyse(saved: dict, puzzles: list, catalog: dict) -> dict:
    families = {h: e['family'] for h, e in catalog.items() if e.get('family')}
    fps = saved['fingerprints']
    stamps = measure_stamps(fps, families)
    info = {p['layered_puzzle_fingerprint']: p for p in puzzles}
    out = {}
    for fp, d in fps.items():
        stamp = stamps.get(fp.split('|')[0], {})
        n = sum(d['runs'].values())
        classes, profile, shapes = collections.Counter(), collections.Counter(), collections.Counter()
        modes = collections.defaultdict(list)  # mode -> [(kinds left, runs)]
        for key, c in d['runs'].items():
            kinds, flags = parse(key)
            left = {k: v - min(v, stamp.get(k, 0)) for k, v in kinds.items()}
            left = {k: v for k, v in left.items() if v}
            classes[custody_class(left)] += c
            modes[custody_class(left) if left else NOTHING].append((left, c))
            for k in left: profile[k] += c
            for f in flags: profile[f] += c
            shapes[', '.join(f'{k} x{v}' if v > 1 else k for k, v in sorted(left.items())) or '(nothing)'] += c
        top_class, top_n = classes.most_common(1)[0] if classes else ('', 0)
        # from 1 run too: most unknown puzzles were spent once or twice ever (the page shows the runs)
        hint = top_class if top_n >= HINT_SHARE * n else 'mixed'
        p = info.get(fp)
        out[fp] = dict(runs=n, errors=d['errors'], stamp=stamp,
                       custody_hint=hint, custody_classes={k: round(v / n, 3) for k, v in classes.most_common()} if n else {},
                       shapes=[[s, c] for s, c in shapes.most_common(5)],
                       template=template(modes, n),
                       profile={k: round(v / n, 3) for k, v in profile.items()} if n else {},
                       known=bool(p and p['known']), label=(p['name'] or ' > '.join(p['layers'])) if p else '',
                       custody=p['custody'] if p else None, puzzle_type=p['puzzle_type'] if p else None,
                       family=p['family'] if p else None)
    # 6. the fingerprints with the same template key (5 runs or more: one run is not a template)
    groups = collections.Counter(o['template']['key'] for o in out.values() if o['runs'] >= MIN_RUNS)
    for o in out.values():
        o['template']['same'] = groups[o['template']['key']] - 1 if o['runs'] >= MIN_RUNS else 0
    # 4. behaves like: the nearest known fingerprints (another one than itself), best per label
    known = {fp: o for fp, o in out.items() if o['known'] and o['runs'] >= MIN_RUNS}
    for fp, o in out.items():
        best = {}
        for kfp, k in known.items():
            if kfp == fp:
                continue
            s = similarity(o['profile'], k['profile'])
            if s > best.get(k['label'], (0,))[0]:
                best[k['label']] = (s, k['custody'])
        o['behaves_like'] = [[label, round(s, 2), c] for label, (s, c) in sorted(best.items(), key=lambda kv: -kv[1][0])[:3]]
    # 5. disagreements: a known fingerprint whose conditions do not fit its custody
    for o in out.values():
        o['disagrees'] = ''
        if (o['known'] and o['runs'] >= DISAGREE_RUNS and o['custody'] in TOLD and o['custody_hint'] in FITS
                and o['custody'] not in FITS[o['custody_hint']]):
            o['disagrees'] = (f"custody {o['custody']}, but {o['custody_classes'][o['custody_hint']]:.0%} of "
                              f"{o['runs']} spends are '{o['custody_hint']}'")
    return dict(made=saved['made'], blocks=saved['blocks'], tip=saved['tip'],
                fits={k: sorted(v) for k, v in FITS.items()},
                stamps={h: dict(layer=catalog[h]['name'], stamp=s) for h, s in stamps.items()},
                fingerprints=out)


def report(res: dict):
    fps = res['fingerprints']
    print(f"{len(fps):,} fingerprints run, {sum(o['runs'] for o in fps.values()):,} runs, "
          f"{sum(o['errors'] for o in fps.values()):,} errors")
    print('\nlayer stamps:')
    for s in res['stamps'].values():
        print(f"  {s['layer']}: {', '.join(f'{k} x{v}' if v > 1 else k for k, v in s['stamp'].items()) or '(none)'}")
    # how good the custody hint is: on the known fingerprints with a custody the conditions can tell
    print('\ncustody hint on known fingerprints (custody KEY, KEYS, SINGLETON, OFFER, ANYONE):')
    table = collections.defaultdict(collections.Counter)
    for o in fps.values():
        if o['known'] and o['custody'] in TOLD and o['runs'] >= DISAGREE_RUNS:
            table[o['custody']][o['custody_hint']] += 1
    for c, hints in sorted(table.items()):
        print(f"  {c:10} {dict(hints.most_common())}")
    ok = sum(n for c, h in table.items() for k, n in h.items() if k in FITS and c in FITS[k])
    print(f"  fits: {ok} of {sum(sum(h.values()) for h in table.values())} (mixed counts as not fitting)")
    # how good "behaves like" is: the nearest other known fingerprint, has it the same custody?
    known = {o['label']: o for o in fps.values() if o['known'] and o['runs'] >= MIN_RUNS}
    near = [(o, known[o['behaves_like'][0][0]]) for o in known.values() if o['behaves_like']]
    same = sum(o['custody'] == n['custody'] for o, n in near)
    print(f"\nbehaves like, on known fingerprints with {MIN_RUNS}+ runs: the nearest other one has the same "
          f"custody for {same} of {len(near)}, the same puzzle type for {sum(o['puzzle_type'] == n['puzzle_type'] for o, n in near)}")
    print()
    for kind in ('known', 'unknown'):
        sel = [o for o in fps.values() if o['known'] == (kind == 'known')]
        for label, part in (('5+ runs', [o for o in sel if o['runs'] >= MIN_RUNS]), ('1-4 runs', [o for o in sel if o['runs'] < MIN_RUNS])):
            hs = collections.Counter(o['custody_hint'] for o in part)
            print(f"{kind} fingerprints, {label} ({len(part)}): {dict(hs.most_common())}")
    # 6. templates
    many = [o for o in fps.values() if o['runs'] >= MIN_RUNS]
    keys = collections.Counter(o['template']['key'] for o in many)
    no_core = sum(any(not t['core'] and t['mode'] != NOTHING for t in o['template']['modes']) for o in many)
    print(f"\ntemplates, fingerprints with {MIN_RUNS}+ runs: {len(many)}, {len(keys)} template keys, "
          f"{no_core} with a mode without core, {sum(len(o['template']['modes']) > 1 for o in many)} with 2+ modes")
    for key, n in keys.most_common(5):
        labels = collections.Counter(o['label'] for o in many if o['template']['key'] == key)
        print(f"  {n:4} fingerprints  {key[:90]}  ({', '.join(l[:40] for l, _ in labels.most_common(2))})")
    for name in ('standard transaction', 'plot NFT (contract)', 'XCH (offer)', 'XCH (keys)'):
        o = max((o for o in many if o['label'] == name), key=lambda o: o['runs'], default=None)
        if o:
            print(f"  {name}:")
            for t in o['template']['modes']:
                print(f"    {SCAN.template_mode_text(t)}")
    print('\nmixed, known, with a custody the conditions can tell:')
    for o in fps.values():
        if o['known'] and o['custody'] in TOLD and o['custody_hint'] == 'mixed' and o['runs'] >= DISAGREE_RUNS:
            print(f"  {o['label']} ({o['custody']}, {o['runs']} runs): {o['custody_classes']}")
    print('\ndisagreements:')
    for fp, o in fps.items():
        if o['disagrees']:
            print(f"  {o['label']}: {o['disagrees']}; shapes {o['shapes'][:2]}")
    if not any(o['disagrees'] for o in fps.values()):
        print('  none')


def main():
    D = sys.argv[1]
    if '--collect' in sys.argv:
        i = sys.argv.index('--collect')
        n = int(sys.argv[i + 1]) if len(sys.argv) > i + 1 and sys.argv[i + 1].isdigit() else 30000
        json.dump(collect(n), open(f'{D}/behaviour_runs.json', 'w'))
    saved = json.load(open(f'{D}/behaviour_runs.json'))
    puzzles = json.load(open(f'{D}/all_puzzles.json'))
    catalog = json.load(open(CONF.KNOWN_PUZZLES_PATH))
    res = analyse(saved, puzzles, catalog)
    json.dump(res, open(f'{D}/behaviour.json', 'w'), indent=1)
    report(res)


if __name__ == '__main__':
    main()
