import json, collections, re, hashlib, sys
R, N = sys.argv[1], sys.argv[2]
ps = json.load(open('resources/puzzles/chain_scan/all_puzzles.json'))
lay = [p for p in ps if p['kind'] == '2+ layers']
# counted on the 2+ layer puzzles only, so their families (and row ids) stay the same
nkeys = collections.Counter(l for p in lay for l in set(p['layers']))
# puzzles with 1 layer get a row too: a name in layered_puzzles.json puts the ones of a project
# under its tag, and gives them a family (a catalog puzzle has none)
lay += [p for p in ps if p['kind'] == '1 layer']
# proposals for the 1-layer puzzles of the catalog: layer name -> (tag, what it does, guessed, family)
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
fam = collections.defaultdict(list)
saved_file = json.load(open('resources/puzzles/layered_puzzles.json'))
puzzle_types = json.load(open('resources/puzzles/puzzle_types.json'))
def family_of(first_layer):
    """Family from the outer layer, the same rule as apply_review.py"""
    return 'CAT' if 'cat_v' in first_layer else 'SINGLETON' if 'singleton' in first_layer else 'UNKNOWN'
names = {k: v for k, v in json.load(open(f'{R}/names.json')).items()}
def layer_tags(layers):
    """Puzzle tags from the layers, the same rule as PUZ.layered_puzzle_tags: the last part of
    each known layer name ('--cni-nft_puzzles-nft_state_layer' -> 'nft_state_layer')"""
    tags = []
    for n in layers:
        if n == '*' or n.startswith(('?', '(', 'not curried')):
            continue
        t = n.rsplit('-', 1)[-1]
        if t and not t.startswith('unknown') and t not in tags:
            tags.append(t)
    return tags
# layers identified by hand, kept out of the '*' wildcard so they get their own row
KEEP = set()
NEW_IDS = {}
# what the unknown layers are, shown next to the hash
LABELS = {}
for p in lay:
    # the layer of a 1-layer puzzle is the whole puzzle, never per-instance data
    one_layer = len(p['layers']) == 1
    fam[tuple('*' if l.startswith('?') and nkeys[l] == 1 and l not in KEEP and not one_layer else l for l in p['layers'])].append(p)
fams = sorted(fam.items(), key=lambda kv: -sum(p['seen'] for p in kv[1]))
def short(l):
    l = re.sub(r'^--cni-', '', l); l = re.sub(r'^--', '', l)
    for a in ('nft_puzzles-','cat_puzzles-','did_puzzles-','pool_puzzles-','mips_puzzles-','architecture_puzzles-','member_puzzles-','circuit_puzzles-','vc_puzzles-'): l = l.replace(a,'')
    return l
items, used, families = [], collections.OrderedDict(), {}
for i, (pat, g) in enumerate(fams):
    pid = hashlib.sha1('|'.join(pat).encode()).hexdigest()
    # a 1-layer puzzle: the proposal above, or no project known yet
    one_fam = ONE_LAYER[pat[0]][3] if len(pat) == 1 and pat[0] in ONE_LAYER else None
    if pid in names: tag, desc, uns = names[NEW_IDS.get(pat, pid)][:3]
    elif one_fam: tag, desc, uns = ONE_LAYER[pat[0]][:3]
    else: tag, desc, uns = 'UNKNOWN', f"unidentified {pat[0].lstrip('?')}", True
    known = sorted({p['name'] for p in g if p['name']})
    seen = sum(p['seen'] for p in g)
    named = [saved_file[p['key']]['name'] for p in g if p['key'] in saved_file]
    types = sorted({saved_file[p['key']].get('puzzle_type', '') for p in g if p['key'] in saved_file} - {''})
    # family: the saved one when the family has one, else from the outer layer
    saved_fams = sorted({puzzle_types[t]['family'] for t in types if t in puzzle_types})
    family = saved_fams[0] if len(saved_fams) == 1 else one_fam or family_of(g[0]['layers'][0])
    # puzzle tags without the family (the family is always the first one, chosen on the row):
    # the ones in layered_puzzles.json, else from the layers
    saved_tags = [t for p in g if p['key'] in saved_file for t in saved_file[p['key']].get('tags', [])[1:]]
    ptags = list(dict.fromkeys(saved_tags)) if saved_tags else layer_tags(pat)
    cur = f"{seen:,} spends  ·  heights {min(p['first_height'] for p in g):,}–{max(p['last_height'] for p in g):,}" + \
          (f"  ·  {len(g)} kinds" if len(g) > 1 else '') + f"  ·  {len(pat)} layer{'s' if len(pat) > 1 else ''}"
    items.append(dict(id=pid, hash=pid, group=tag, tagBase=tag, tagSuffix='', desc=desc, proposed=f"{tag}: {desc}",
                      current=cur, file=' > '.join(short(l) + (f' ({LABELS[l]})' if l in LABELS else '') for l in pat), unsure=uns, seen=seen,
                      saved=dict(names=sorted(set(named)), types=types, keys=len(named), total=len(g)) if named else None,
                      example_key=g[0]['key'], family=family, ptags=ptags))
    used[tag] = used.get(tag, 0) + seen
    families[pid] = dict(layers=list(pat), keys=[dict(key=p['key'], layer_hashes=p['layer_hashes'], layers=p['layers'], example_coin=p['example_coin']) for p in g])
tag_notes = {'TIBET_SWAP': 'was TIBET_SW in the first review', 'WARP_GREEN': 'was WARP_G; you wrote WART_GREEN, read as WARP_GREEN',
             'OPTION_CONTRACT': 'CHIP-45; the chip number is secondary info', 'UNKNOWN': 'no layer is known',
             'SINGLETON': 'singleton with an inner puzzle of no known project', 'REWARD_DIST': 'reward distributor (slot machine app)',
             'VAULT': 'vaults / MIPS', 'XCHANDLES': 'XCHandles (slot machine app)', 'CAT_V1': 'the first CAT version (chia 1.3/1.4)',
             'STD': 'the standard transaction', 'CHIA': 'base puzzles of chia (p2_*, notification, identity)',
             'OFFER': 'offers', 'CHIA_GAMING': 'state channel games (Chia-Network/chia-gaming)'}
rules = [dict(id='tag-' + t.lower(), group='Project tags', proposed=t, current='now: ' + tag_notes.get(t, 'project tag'),
              file='', hash='', unsure=False, rule=dict(kind='tag', tag=t)) for t in used]
# separator between the tag and what the puzzle does, ' - ' unless changed in the Name format tab
# (a setting, not a row to review)
rules.append(dict(id='fmt-separator', group='Name format', proposed='separator', current='',
                  file='', hash='', unsure=False, rule=dict(kind='sep', proposed=' - ')))
# puzzle tags: the ones in layered_puzzles.json and the ones from the layers; more can be added
# in the Puzzle tags tab
saved_ptags = sorted({t for v in saved_file.values() for t in v.get('tags', [])[1:]})
rules.append(dict(id='cfg-ptags', group='Puzzle tags', proposed='puzzle tags', current='', file='', hash='', unsure=False,
                  rule=dict(kind='ptags', saved=saved_ptags, layers=sorted({t for it in items for t in it['ptags']} - set(saved_ptags)))))
# the families rototiller knows (puzzle_types.json); more can be added in the Families tab
rules.append(dict(id='cfg-families', group='Families', proposed='families', current='', file='', hash='', unsure=False,
                  rule=dict(kind='families', families=sorted({t['family'] for t in puzzle_types.values()}))))
order = list(used)  # tags by first appearance in spend order
items.sort(key=lambda it: (order.index(it['group']), -it['seen']))  # rules stay first
json.dump(rules + items, open(f'{R}/items.json', 'w'))
json.dump(families, open(f'{R}/families.json', 'w'))
head = open(f'{N}/head.html').read().replace('<title>Puzzle Names Review</title>', '<title>Chain Puzzle Names</title>')
body = open(f'{N}/body.html').read().replace('<h1>Puzzle names review</h1>', '<h1>Chain puzzle names</h1>') \
    .replace('&lt;TAG&gt;[_VERSION][_RUE]: &lt;what it does&gt;', '&lt;PROJECT_TAG&gt;: &lt;what it does&gt;  ·  one row per family of puzzles seen on chain') \
    .replace('Search names, files, notes', 'Search names, layers, notes') \
    .replace('<div id="applyPanel" hidden></div>', '<button type="button" class="gapply" id="submitBtn" title="Send the reviewed names, Claude writes them in layered_puzzles.json">Submit names</button><span class="status" id="subInfo"></span>\n    <div id="applyPanel" hidden></div>')
script = open(f'{N}/script.js').read().replace("const LOCAL_KEY = 'puzzle-names-review';", "const LOCAL_KEY = 'layered-names-review';") + open(f'{R}/submit.js').read()
data = json.dumps(rules + items).replace('</', '<\\/')
open(f'{R}/layered-names-review.html', 'w').write(head + body + '<script type="application/json" id="data">' + data + '</script>\n<script>\n' + script + '</script>\n')
print(len(rules), 'tags', len(items), 'families', sum(it['unsure'] for it in items), 'guessed')
