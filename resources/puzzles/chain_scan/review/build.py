"""Build the layered names review: items.json, variant_groups.json and layered-names-review.html
(page.html with the rows in it), a page to open from disk, no server.
Run from the repo root: .venv/bin/python resources/puzzles/chain_scan/review/build.py resources/puzzles/chain_scan/review
(after export.py: it reads all_puzzles.json)"""
import json, collections, re, hashlib, sys
R = sys.argv[1]
ps = json.load(open('resources/puzzles/chain_scan/all_puzzles.json'))
lay = [p for p in ps if p['kind'] == '2+ layers']
# counted on the 2+ layer puzzles only, so their variant groups (and row ids) stay the same
nkeys = collections.Counter(l for p in lay for l in set(p['layers']))
# puzzles with 1 layer get a row too: a name in layered_puzzles.json puts the ones of a project
# under its tag
lay += [p for p in ps if p['kind'] == '1 layer']
# proposals for the 1-layer puzzles of the catalog: layer name -> (tag, what it does, guessed, family
# (not used: the family comes from the layers, see all_puzzles.json))
ONE_LAYER = {
    '--cni-p2_delegated_puzzle_or_hidden_puzzle': ('STD', 'standard transaction', False, 'STD'),
    '--cni-p2_singleton_or_delayed_puzhash': ('PLOTNFT', 'pool reward (p2 singleton or delayed puzzle hash)', False, 'UNKNOWN'),
    '--cni-singleton_launcher': ('SINGLETON', 'launcher', False, 'SINGLETON'),
    '--cni-nft_puzzles-create_nft_launcher_from_did': ('NFT_V1', 'creates a launcher from a DID', False, 'UNKNOWN'),
    '--cni-settlement_payments': ('OFFER', 'settlement payments', False, 'UNKNOWN'),
    '--tibet-p2_singleton_flashloan': ('TIBET_SWAP', 'XCH reserve (p2 singleton flashloan)', False, 'UNKNOWN'),
    '--tibet_v1_beta-p2_singleton_flashloan': ('TIBET_SWAP', 'XCH reserve v1 beta', False, 'UNKNOWN'),
    '--cni-p2_delegated_conditions': ('CHIA', 'delegated conditions (p2_delegated_conditions)', False, 'UNKNOWN'),
    '--cni-p2_delegated_puzzle': ('CHIA', 'delegated puzzle (p2_delegated_puzzle)', False, 'UNKNOWN'),
    '--cni-p2_1_of_n': ('CHIA', 'one of n puzzles (p2_1_of_n)', False, 'UNKNOWN'),
    '--cni-p2_parent': ('CHIA', 'pay to parent (p2_parent)', False, 'UNKNOWN'),
    '--cni-notification': ('CHIA', 'notification', False, 'UNKNOWN'),
    '--clvm-identity': ('CHIA', 'identity (anyone can spend)', False, 'UNKNOWN'),
    '--chip_0037-p2_eip712_message': ('CHIA', 'EIP-712 signed message (CHIP-37)', True, 'UNKNOWN'),
    '--cni-cat_puzzles-cat_v2': ('CAT_V2', 'inner puzzle not curried', False, 'CAT'),
    '--chia_blockchain_cat_v1-cat': ('CAT_V1', 'inner puzzle not curried', False, 'CAT'),
    '--cni-singleton_top_layer_v1_1': ('SINGLETON', 'inner puzzle not curried', False, 'SINGLETON'),
    '--cni-singleton_top_layer': ('SINGLETON', 'v1.0, inner puzzle not curried', False, 'SINGLETON'),
    '--cni-p2_singleton': ('SINGLETON', 'pay to singleton (p2_singleton)', False, 'UNKNOWN'),
    '--cni-p2_singleton_via_delegated_puzzle': ('SINGLETON', 'pay to singleton via delegated puzzle', False, 'UNKNOWN'),
    '--warp-bridging_puzzle': ('WARP_GREEN', 'bridging puzzle', False, 'UNKNOWN'),
    '--warp-wrapped_cats-locker': ('WARP_GREEN', 'wrapped CAT locker', False, 'UNKNOWN'),
    '--warp-wrapped_cats-unlocker': ('WARP_GREEN', 'wrapped CAT unlocker', False, 'UNKNOWN'),
    '--warp-wrapped_cats-p2_controller_puzzle_hash': ('WARP_GREEN', 'wrapped CAT, pay to controller', False, 'UNKNOWN'),
    '--warp-wrapped_assets-cat_minter': ('WARP_GREEN', 'wrapped asset CAT minter', False, 'UNKNOWN'),
    '--warp-wrapped_assets-cat_burner': ('WARP_GREEN', 'wrapped asset CAT burner', False, 'UNKNOWN'),
    '--slot_machine_rue-singleton-p2_delegated_by_singleton': ('SLOT_MACHINE', 'pay to singleton, delegated', True, 'UNKNOWN'),
    '--cni-mips_puzzles-member_puzzles-bls_member': ('VAULT', 'BLS key member', True, 'UNKNOWN'),
    '--chia_gaming-unroll_puzzle_state_channel_unrolling_v1': ('CHIA_GAMING', 'channel unroll v1 (2025)', False, 'UNKNOWN'),
    '--chia_gaming-clsp-unroll-unroll_puzzle_state_channel_unrolling': ('CHIA_GAMING', 'channel unroll', False, 'UNKNOWN'),
    '--forge_v16-forge_reserve_launcher': ('FORGE', 'reserve launcher', False, 'UNKNOWN'),
    '--circuit-circuit_puzzles-statutes_launcher': ('CIRCUIT', 'statutes launcher', False, 'UNKNOWN'),
}
# --- the local review page: one row per variant group, in three tabs ---
# confirm: the layers give the puzzle type and the custody, check them and the name
# fill: some fields are known, fill in the others
# unknown: nothing of a project is known, research or skip
puzzle_types = json.load(open('resources/puzzles/catalog/puzzle_types.json'))
# the first proposals (names.json, by row id): only "what it does", the tag is left empty for now
names = json.load(open(f'{R}/names.json'))
FIELDS = ('family', 'puzzle_type', 'custody', 'project')
groups = collections.defaultdict(list)
for p in lay:
    # the layer of a 1-layer puzzle is the whole puzzle, never per-instance data
    one_layer = len(p['layers']) == 1
    groups[tuple('*' if l.startswith('?') and nkeys[l] == 1 and not one_layer else l for l in p['layers'])].append(p)
ordered = sorted(groups.items(), key=lambda kv: -sum(p['seen'] for p in kv[1]))
def short(l):
    l = re.sub(r'^--cni-', '', l); l = re.sub(r'^--', '', l)
    for a in ('nft_puzzles-','cat_puzzles-','did_puzzles-','pool_puzzles-','mips_puzzles-','architecture_puzzles-','member_puzzles-','circuit_puzzles-','vc_puzzles-'): l = l.replace(a,'')
    return l
def guess(pat, family_layer):
    """what it does, from the innermost known layer inside the family layer: its file name
    without the project; empty when no such layer is known"""
    known = [l for l in pat[1 if family_layer else 0:] if l.startswith('--')]
    # the innermost layer must be known: an unknown one inside does what matters
    return short(known[-1]).split('-')[-1].replace('_', ' ') if known and known[-1] == pat[-1] else ''
def tab(f):
    if f['puzzle_type'] and f['custody'] not in (None, 'UNKNOWN'):
        return 'confirm'
    if f['project'] not in (None, 'unknown') or f['puzzle_type'] or f['custody'] not in (None, 'UNKNOWN'):
        return 'fill'
    return 'unknown'
# the behaviour hints (chain_scan/behaviour.py), by layered puzzle fingerprint: only shown, never saved
try:
    _beh = json.load(open('resources/puzzles/chain_scan/behaviour.json'))
except FileNotFoundError:
    _beh = {}
BEH = _beh.get('fingerprints', {})
# the custodies a hint fits (behaviour.py FITS), suggested when the layers give none
HINT_CUSTODY = _beh.get('fits', {})
def behaviour(g, custody):
    """The behaviour of a variant group: its fingerprints' runs together, the shapes and the
    nearest known puzzles of its fingerprint with the most runs"""
    bs = [BEH[p['layered_puzzle_fingerprint']] for p in g if p['layered_puzzle_fingerprint'] in BEH]
    runs = sum(b['runs'] for b in bs)
    if not runs:
        return None
    classes = collections.Counter()
    for b in bs:
        for k, v in b['custody_classes'].items(): classes[k] += v * b['runs']
    hint, n = classes.most_common(1)[0]
    hint = hint if n >= 0.8 * runs else 'mixed'
    main = max(bs, key=lambda b: b['runs'])
    return dict(runs=runs, hint=hint, classes={k: round(v / runs, 2) for k, v in classes.most_common()},
                like=main['behaves_like'], shapes=[[sh, round(c / main['runs'], 2)] for sh, c in main['shapes'][:3] if c / main['runs'] >= 0.01],
                stamp=main['stamp'], template=main['template'], disagrees=' · '.join(b['disagrees'] for b in bs if b['disagrees']),
                # 2. a custody to fill: the layers give none, the conditions say what fits
                suggest=HINT_CUSTODY.get(hint, []) if custody in (None, 'UNKNOWN', 'HIDDEN') else [])
items, variant_groups = [], {}
for pat, g in ordered:
    pid = hashlib.sha1('|'.join(pat).encode()).hexdigest()
    p0 = g[0]  # the fields are the same for the whole group (checked in the build below)
    assert all(all(p[f] == p0[f] for f in FIELDS + ('project_dependencies',)) for p in g), pat
    fields = {f: p0[f] for f in FIELDS}
    if len(pat) == 1 and pat[0] in ONE_LAYER:
        name, guessed = ONE_LAYER[pat[0]][1], ONE_LAYER[pat[0]][2]
    elif pid in names and not re.search(r'unidentified|^\??[0-9a-f]{8}\b', names[pid][1]):
        name, guessed = names[pid][1], names[pid][2]
    else:
        name, guessed = guess(pat, p0['origins']['family'] == 'layer 1'), True
    items.append(dict(id=pid, tab=tab(fields), fields=fields, origins=p0['origins'], project_dependencies=p0['project_dependencies'], name=name, guessed=guessed,
                      layers=[short(l) for l in pat], code_layers=list(pat), seen=sum(p['seen'] for p in g),
                      first=min(p['first_height'] for p in g), last=max(p['last_height'] for p in g),
                      behaviour=behaviour(g, fields['custody']),
                      layered_puzzle_fingerprints=[dict(layered_puzzle_fingerprint=p['layered_puzzle_fingerprint'], layers=p['layers'], coin=p['example_coin'], seen=p['seen']) for p in g]))
    variant_groups[pid] = dict(layers=list(pat), layered_puzzle_fingerprints=[dict(layered_puzzle_fingerprint=p['layered_puzzle_fingerprint'], layer_hashes=p['layer_hashes'], layers=p['layers'], example_coin=p['example_coin']) for p in g])
projects = sorted({it['fields']['project'] for it in items} - {None, 'unknown'} | set(puzzle_types['projects']))
LISTS = dict(family='families', puzzle_type='types', custody='custodies')
vocab = dict(family=list(puzzle_types['families']), puzzle_type=list(puzzle_types['types']),
             custody=list(puzzle_types['custodies']), project=projects,
             # id -> label of each list: the page shows the labels, the verdicts keep the ids
             labels={**{f: {v: e.get('label', v) for v, e in puzzle_types[l].items()} for f, l in LISTS.items()},
                     'project': {p: puzzle_types['projects'].get(p, {}).get('label', p) for p in projects}},
             # for the fields overlay: the values of each field with their meaning
             desc={f: {v: e.get('description', '') for v, e in puzzle_types[l].items()} for f, l in LISTS.items()},
             projects=puzzle_types['projects'], project_roles=puzzle_types.get('project_roles', {}),
)
# for the code overlay: the source of each catalog layer of the rows (layer name -> where, code)
catalog = {v['name']: v for v in json.load(open('resources/puzzles/catalog/puzzles.json')).values()}
code = {}
for it in items:
    for l in it['code_layers']:
        if l in catalog and l not in code:
            c, src = catalog[l], (catalog[l].get('sources') or [{}])[0]
            code[l] = dict(file=c.get('file_name'), repo=src.get('repo'), commit=src.get('commit'), path=src.get('path'),
                           language=src.get('language'), hash=c.get('puzzle_hash'),
                           text=c.get('clvm') or c.get('bytecode_disassembled') or '',
                           disassembled=not c.get('clvm'))
json.dump(items, open(f'{R}/items.json', 'w'))
json.dump(variant_groups, open(f'{R}/variant_groups.json', 'w'))
data = json.dumps(dict(items=items, vocab=vocab, code=code)).replace('</', '<\\/')
page = open(f'{R}/page.html').read().replace('/*DATA*/null', data)
open(f'{R}/layered-names-review.html', 'w').write(page)
print(sum(bool(it['behaviour']) for it in items), 'with a behaviour hint,', sum(bool(it['behaviour'] and it['behaviour']['disagrees']) for it in items), 'disagree with the catalog')
print(len(items), 'variant groups:', dict(collections.Counter(it['tab'] for it in items)), sum(it['guessed'] for it in items), 'guessed names')
