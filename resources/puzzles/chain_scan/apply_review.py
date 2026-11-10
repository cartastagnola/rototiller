"""Write the verdicts of the layered names review (review/layered-names-review.html, Export) in
catalog/layered_puzzles.json. A row is a variant group: every layered puzzle fingerprint of the group seen on
chain gets the name and the overrides of its OK row. The name is "what it does" (no project tag
for now); an override is a family, puzzle type, custody or project set by hand on the page,
written only when it is not the value the layers give. A field not set on the page removes the
override saved before. Rows marked Research or Skip are not written.
Run from the repo root:
  .venv/bin/python resources/puzzles/chain_scan/apply_review.py VERDICTS.json resources/puzzles/chain_scan/review/variant_groups.json [--write]
Without --write it only prints what would change."""
import json, sys
sys.path.insert(0, '.')
import src.CONFtiller as CONF
import src.SCANtiller as SCAN
import src.PUZZLEtiller as PUZ

FIELDS = SCAN.OVERRIDE_FIELDS  # family, puzzle_type, custody, project


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    write = '--write' in sys.argv
    sub, groups = json.load(open(args[0])), json.load(open(args[1]))
    if sub.get('format') != 'chain-names-review/1':
        sys.exit(f"{args[0]}: not an export of the layered names review (format chain-names-review/1)")
    plan, problems = [], []
    for n in sub['names']:
        name = (n.get('name') or '').strip()
        overrides = {f: n.get(f) for f in FIELDS}
        if n['id'] not in groups:
            problems.append(f"unknown row {n['id'][:10]}: {name}")
            continue
        if not name and not any(overrides.values()):
            problems.append(f"row {n['id'][:10]}: OK with no name and no field set")
            continue
        for k in groups[n['id']]['layered_puzzle_fingerprints']:
            # a value the layers already give is not an override (save_known_puzzle drops it too)
            derived = PUZ.classify_fingerprint(k['layered_puzzle_fingerprint'], overrides=False)
            kept = {f: v if v and v != derived[f][0] else None for f, v in overrides.items()}
            plan.append((k, name, kept, CONF.KNOWN_LAYERED_PUZZLES.get(k['layered_puzzle_fingerprint'])))

    def changes(name, overrides, old):
        """what changes in the entry: the name, each override"""
        old = old or {}
        out = []
        if old.get('name') != (name or None):
            out.append(f"name {old.get('name')!r} -> {name!r}" if old.get('name') else f"name {name!r}")
        for f in FIELDS:
            if old.get(f) != overrides[f]:
                out.append(f"{f} {old.get(f) or '-'} -> {overrides[f] or '-'}")
        return out
    todo = [(p, changes(*p[1:])) for p in plan]
    todo = [(p, c) for p, c in todo if c]
    statuses = {}
    for v in sub.get('verdicts', {}).values():
        statuses[v.get('status', '')] = statuses.get(v.get('status', ''), 0) + 1
    print(f"{len(sub['names'])} OK rows -> {len(plan)} layered puzzle fingerprints: {len(todo)} to change, "
          f"{len(plan) - len(todo)} unchanged  (verdicts: {statuses})")
    for p in problems:
        print('  skipped:', p)
    for (k, *_), c in todo:
        print(f"  {k['layered_puzzle_fingerprint'][:24]}...  " + '; '.join(c))
    if not write:
        print('dry run: nothing written (add --write)')
        return
    for (k, name, overrides, _), _c in todo:
        SCAN.save_known_puzzle(k['layered_puzzle_fingerprint'], k['layer_hashes'], k['layers'], name, example_coin_id=k['example_coin'],
                               overrides=overrides)
    print('written: resources/puzzles/catalog/layered_puzzles.json')


if __name__ == '__main__':
    main()
