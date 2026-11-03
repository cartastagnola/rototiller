"""Write the names of a layered puzzles review submission in layered_puzzles.json.
A name is for a variant group: every puzzle key of the group seen on chain gets it. The family
is saved only when the reviewer chose another one than the layers give (an override); the
tags only when they are labels added by hand (not a family, not a layer name).
Run from the repo root:
  .venv/bin/python resources/puzzles/chain_scan/apply_review.py SUBMISSION.json VARIANT_GROUPS.json [--write]
Without --write it only prints what would change."""
import json, re, sys
sys.path.insert(0, '.')
import src.CONFtiller as CONF
import src.SCANtiller as SCAN
import src.PUZZLEtiller as PUZ



def name_re(sep: str):
    """PROJECT_TAG<sep>what it does, the separator is chosen on the review page (Name format tab)"""
    return re.compile(r'^[A-Z][A-Z0-9_]*' + re.escape(sep) + r'\S.*$')


def hand_tags(tags, layers):
    """The tags that are labels added by hand: the families and the layer names are derived"""
    if tags is None:
        return None
    derived = set(CONF.PUZZLE_TYPES.get('families', {})) | {'UNKNOWN', 'STD'}
    derived |= {l.rsplit('-', 1)[-1] for l in layers}
    return [t for t in dict.fromkeys(tags) if t not in derived]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    write = '--write' in sys.argv
    sub, groups = json.load(open(args[0])), json.load(open(args[1]))
    sub = sub.get('data', sub)
    sep = sub.get('separator', ': ')
    name_ok = name_re(sep)
    plan, problems = [], []
    for n in sub['names']:
        name = n['name'].strip()
        if n['id'] not in groups:
            problems.append(f"unknown row {n['id'][:10]}: {name}")
            continue
        keys = groups[n['id']]['keys']
        kept = all(CONF.KNOWN_LAYERED_PUZZLES.get(k['key'], {}).get('name') == name for k in keys)
        if not kept and not name_ok.match(name):
            problems.append(f"name not in the form 'PROJECT_TAG{sep}what it does': {name!r}")
            continue
        for k in groups[n['id']]['keys']:
            old = CONF.KNOWN_LAYERED_PUZZLES.get(k['key'])
            # the family is an override only when it is not the one the layers give
            derived = PUZ.classify_key(k['key'], overrides=False)['family'][0]
            family = n.get('family') if n.get('family') and n.get('family') != derived else None
            plan.append((k, name, family, hand_tags(n.get('tags'), k['layers']), old))
    def changes(name, family, tags, old):
        """what changes in the entry: name, family override, puzzle tags"""
        if old is None:
            return ['new']
        out = []
        if old.get('name') != name: out.append(f"rename {old.get('name')!r} ->")
        if old.get('family') != family: out.append('family')
        if tags is not None and old.get('tags', []) != tags: out.append('puzzle tags')
        return out
    todo = [(p, changes(*p[1:])) for p in plan]
    todo = [(p, c) for p, c in todo if c]
    print(f"{len(sub['names'])} names -> {len(plan)} puzzle keys: {sum(c == ['new'] for _, c in todo)} new, "
          f"{sum(c != ['new'] for _, c in todo)} changed, {len(plan) - len(todo)} unchanged")
    for p in problems:
        print('  skipped:', p)
    for (k, name, family, tags, old), c in todo:
        print(f"  {' '.join(c)} {name}  [family override: {family or '-'}]  tags {tags}  {k['key'][:40]}...")
    if not write:
        print('dry run: nothing written (add --write)')
        return
    for (k, name, family, tags, old), _ in todo:
        SCAN.save_known_puzzle(k['key'], k['layer_hashes'], k['layers'], name, family, k['example_coin'], tags)
    print('written: resources/puzzles/catalog/layered_puzzles.json')


if __name__ == '__main__':
    main()
