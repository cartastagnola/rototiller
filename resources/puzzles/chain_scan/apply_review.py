"""Write the names of a layered puzzles review submission in layered_puzzles.json.
A name is for a family of puzzles: every puzzle key of the family seen on chain gets it.
Run from the repo root:
  .venv/bin/python resources/puzzles/chain_scan/apply_review.py SUBMISSION.json FAMILIES.json [--write]
Without --write it only prints what would change."""
import json, re, sys
sys.path.insert(0, '.')
import src.CONFtiller as CONF
import src.SCANtiller as SCAN



def name_re(sep: str):
    """PROJECT_TAG<sep>what it does, the separator is chosen on the review page (Name format tab)"""
    return re.compile(r'^[A-Z][A-Z0-9_]*' + re.escape(sep) + r'\S.*$')


def family_of(first_layer: str) -> str:
    """Family from the outer layer, like the entries already in puzzle_types.json"""
    if 'cat_v' in first_layer:
        return 'CAT'
    if 'singleton' in first_layer:
        return 'SINGLETON'
    return 'UNKNOWN'


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    write = '--write' in sys.argv
    sub, families = json.load(open(args[0])), json.load(open(args[1]))
    sub = sub.get('data', sub)
    sep = sub.get('separator', ': ')
    name_ok = name_re(sep)
    plan, problems = [], []
    for n in sub['names']:
        name = n['name'].strip()
        if n['id'] not in families:
            problems.append(f"unknown row {n['id'][:10]}: {name}")
            continue
        keys = families[n['id']]['keys']
        kept = all(CONF.KNOWN_LAYERED_PUZZLES.get(k['key'], {}).get('name') == name for k in keys)
        if not kept and not name_ok.match(name):
            problems.append(f"name not in the form 'PROJECT_TAG{sep}what it does': {name!r}")
            continue
        for k in families[n['id']]['keys']:
            old = CONF.KNOWN_LAYERED_PUZZLES.get(k['key'])
            # a family given in the submission wins over the one from the outer layer
            family = n.get('family') or family_of(k['layers'][0])
            # puzzle tags: the family first (older submissions have none: the entry keeps its tags)
            tags = n.get('tags')
            tags = list(dict.fromkeys([family] + tags)) if tags is not None else None
            plan.append((k, name, family, tags, old))
    def changes(name, family, tags, old):
        """what changes in the entry: name, family, puzzle tags"""
        if old is None:
            return ['new']
        out = []
        if old['name'] != name: out.append(f"rename {old['name']!r} ->")
        if CONF.PUZZLE_TYPES.get(old['puzzle_type'], {}).get('family') != family: out.append('family')
        if tags is not None and old.get('tags') != tags: out.append('puzzle tags')
        return out
    todo = [(p, changes(*p[1:])) for p in plan]
    todo = [(p, c) for p, c in todo if c]
    print(f"{len(sub['names'])} names -> {len(plan)} puzzle keys: {sum(c == ['new'] for _, c in todo)} new, "
          f"{sum(c != ['new'] for _, c in todo)} changed, {len(plan) - len(todo)} unchanged")
    for p in problems:
        print('  skipped:', p)
    for (k, name, family, tags, old), c in todo:
        print(f"  {' '.join(c)} {name}  [{family}]  tags {tags}  {k['key'][:40]}...")
    if not write:
        print('dry run: nothing written (add --write)')
        return
    for (k, name, family, tags, old), _ in todo:
        SCAN.save_known_puzzle(k['key'], k['layer_hashes'], k['layers'], name, family, k['example_coin'], tags)
    print('written: resources/puzzles/layered_puzzles.json and puzzle_types.json')


if __name__ == '__main__':
    main()
