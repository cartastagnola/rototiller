from __future__ import annotations
import contextlib
import json
import os
import re  # clvm formatter
import threading

#from clvm_tools.binutils import disassemble as bu_disassemble
#from chia.wallet.util.debug_spend_bundle import disassemble
#from clvm_tools.binutils import disassemble


from chia.types.blockchain_format.serialized_program import SerializedProgram
from chia.types.blockchain_format.program import Program as PyProgram
from chia.types.condition_opcodes import ConditionOpcode
from clvm_tools.binutils import disassemble as py_disassemble
from chia.wallet.util.debug_spend_bundle import debug_spend_bundle
from chia.wallet.util.debug_spend_bundle import uncurry_dump

from chia_rs import Program as RsProgram
from chia_rs import G1Element, G2Element
from chia_rs import is_canonical_serialization, serialized_length, tree_hash
from chia_rs.sized_bytes import bytes32
from chia.wallet.cat_wallet.cat_utils import CAT_MOD_HASH
from chia.wallet.nft_wallet.nft_puzzles import NFT_OWNERSHIP_LAYER_HASH, NFT_STATE_LAYER_MOD_HASH
from chia.wallet.puzzles.p2_delegated_puzzle_or_hidden_puzzle import MOD as STANDARD_MOD
from chia.wallet.puzzles.singleton_top_layer_v1_1 import SINGLETON_MOD_HASH

from clvm_tools_rs import binutils as binutils_rs

rs_disassemble = binutils_rs.disassemble_generic

try:
    from chia.types.spend_bundle import SpendBundle
except ImportError:
    try:
        from chia_rs import SpendBundle
    except ImportError:
        print('probably a full_node verison not supporter')

from src.CONFtiller import logging, debug_logger
import src.CONFtiller as CONF
from src.RPCtiller import call_rpc_node, call_rpc_daemon
import src.UTILStiller as UTILS
import src.TYPEStiller as TYPES
import src.RPCtiller as RPC
import src.WDBtiller as WDB

# puzzle repo: https://github.com/Chia-Network/chia-blockchain/tree/fad414132e6950e79e805629427af76bf9ddcbc5/chia/wallet/puzzles


# parse spend bundle
#
# INPUT coins -> what coin are used > puzzle reveal
#                                   > memo for cat?
# solution -> what is created > number of coin, memo

def get_opcode_name(number: int):
    """Take an int and return the opcode name"""
    return ConditionOpcode(bytes([number])).name


def get_puzzle_reveals_and_solutions(spend_bundle: str):
    reveals = []
    solutions = []
    for coin in spend_bundle['coin_spends']:
        puz_rev = bytes.fromhex(coin['puzzle_reveal'])
        puz_rev_prog = PyProgram.from_bytes(puz_rev)
        reveals.append(puz_rev_prog)

        puz_sol = bytes.fromhex(coin['solution'])
        puz_sol_prog = PyProgram.from_bytes(puz_sol)
        solutions.append(puz_sol_prog)

    return reveals, solutions


# In a layered puzzle fingerprint, a known puzzle curried in two steps: the program curried once is not a layer of
# its own (its hash changes with the data curried in it), it is marked with CURRIED_AGAIN and
# the known puzzle follows it. Eg: every Forge pool is
# singleton_top_layer_v1_1|action|+|forge_multi_reserve_finalizer|forge_reserve_amount
CURRIED_AGAIN = '+'
CURRIED_AGAIN_NAME = '(curried again)'


def known_base_of(program: PyProgram):
    """The hash of the known puzzle that a curried program is made of, uncurrying it as many
    times as needed, or None. Only the shared catalog counts (the fingerprint is the same everywhere)."""
    for _ in range(8):
        base, _ = program.uncurry()
        if base == program:
            return None
        base_hash = base.get_tree_hash().hex()
        if base_hash in CONF.KNOWN_PUZZLES:
            return base_hash
        program = base
    return None


# fingerprints of the puzzles that are not curried and not in the catalog (SCAN.classify_puzzle)
QUOTED_CONDITIONS_FINGERPRINT = 'quoted_conditions'  # a puzzle that only returns its conditions: (q . conditions)
SHAPE_FINGERPRINT_PREFIX = 'shape_'  # code not curried, grouped by shape


# --- Classification of a layer combination ------------------------------------------
# Family, puzzle type, custody and project come from fields on the base puzzles of
# catalog/puzzles.json (family on the family layers, puzzle_type on the purpose layers,
# custody on the p2 puzzles, inner_arg on the layers that wrap an inner puzzle, project where
# the sources give no single one), read by hash; an entry of layered_puzzles.json can
# override them. The names, types and families are for people: no code decides from them.

HELD_CUSTODIES = ('KEY', 'KEYS', 'OFFER', 'SINGLETON', 'ANYONE')  # someone holds the coin
FAMILY_ASSET = {'XCH': 'XCH', 'CAT': 'CAT', 'SINGLETON': 'SINGLETON'}  # the type of a held coin
CHIA_PROJECT = 'chia'
_custody_cache = {}  # layered puzzle fingerprint -> (custody, origin): puzzles.json is read once, at start


def uncurry_fully(program: PyProgram):
    """(base hash, args) of a known puzzle curried once or more (the args of every curry, in
    the order they are passed), or (None, None)"""
    levels = []
    for _ in range(8):
        mod, curried_args = program.uncurry()
        if mod == program:
            return None, None
        levels.append(list(curried_args.as_iter()))
        mod_hash = mod.get_tree_hash().hex()
        if mod_hash in CONF.KNOWN_PUZZLES:
            return mod_hash, [arg for level in reversed(levels) for arg in level]
        program = mod
    return None, None


_depth_cache = {}  # layered puzzle fingerprint -> depth


def puzzle_depth(puzzle_reveal: bytes) -> int:
    """How many puzzles deep a puzzle is: its layer, plus the deepest of the curried programs it
    holds as arguments (the inner puzzle, a transfer program...). The same nodes as the layers of
    unroll_puzzle_to_names: a puzzle of the catalog is 1 and ends the walk; a puzzle curried in
    two steps (CURRIED_AGAIN) is one level, the args of both curries are its children; args that
    are not curried are not layers. Programs side by side do not add up: the deepest counts.
    0 when the puzzle is not curried.

    It works on the serialized puzzle, a node is its offset in the bytes: the hashes are
    chia_rs.tree_hash of the bytes of the node and only the curry wrappers are read, 7x faster
    than uncurry and get_tree_hash, which serialize every program again (0.5 s for 1,227
    puzzles)."""
    blob = bytes(puzzle_reveal)
    if not is_canonical_serialization(blob):  # back references (0xfe): written again without
        blob = bytes(PyProgram.from_bytes(blob))
    mv = memoryview(blob)
    PAIR, NIL = 0xff, 0x80

    def length(s):
        return serialized_length(mv[s:])

    def rest(s):  # s is a pair: where its second element starts
        return s + 1 + length(s + 1)

    def is_known(s):
        return tree_hash(mv[s:s + length(s)]).hex() in CONF.KNOWN_PUZZLES

    def uncurry(s):
        """(mod, [args]) of (a (q . mod) (c (q . arg) (c ... 1))), offsets; (None, None)
        when it is not curried. The small atoms (a=2, q=1, c=4) are one byte"""
        # (2 . ((1 . mod) . (args . ())))
        if mv[s] != PAIR or mv[s + 1] != 0x02 or mv[s + 2] != PAIR:
            return None, None
        quoted = s + 3
        if mv[quoted] != PAIR or mv[quoted + 1] != 0x01:
            return None, None
        mod = quoted + 2
        tail = rest(s + 2)
        if mv[tail] != PAIR or mv[rest(tail)] != NIL:
            return None, None
        node, args = tail + 1, []
        # (4 . ((1 . arg) . (next . ())))
        while mv[node] == PAIR:
            if mv[node + 1] != 0x04 or mv[node + 2] != PAIR:
                return None, None
            quoted = node + 3
            if mv[quoted] != PAIR or mv[quoted + 1] != 0x01:
                return None, None
            args.append(quoted + 2)
            tail = rest(node + 2)
            if mv[tail] != PAIR or mv[rest(tail)] != NIL:
                return None, None
            node = tail + 1
        if mv[node] != 0x01:
            return None, None
        return mod, args

    def depth(s, level):
        if level > 30 or is_known(s):
            return 1
        args, curried, program = [], False, s
        for _ in range(8):  # the curries of this layer, down to its mod
            mod, curried_args = uncurry(program)
            if mod is None:
                break
            curried = True
            args += curried_args
            if is_known(mod):
                break
            program = mod
        if not curried:
            return 0
        children = [depth(a, level + 1) for a in args if mv[a] == PAIR and uncurry(a)[0] is not None]
        return 1 + max(children, default=0)

    return depth(0, 0)


def walk_custody(puzzle: PyProgram):
    """(custody, origin) of a puzzle: walk from the outside in, through the inner puzzle
    argument (inner_arg) of each known layer, to the innermost puzzle. A whole puzzle of the
    catalog ends the walk (a compiled puzzle with constants looks curried). An argument that
    is only a hash: HIDDEN. An unknown layer: go on with its last argument that is a program,
    the origin becomes 'guessed'."""
    origin = 'walk'
    for _ in range(30):
        puzzle_hash = puzzle.get_tree_hash().hex()
        if puzzle_hash in CONF.KNOWN_PUZZLES:
            return CONF.KNOWN_PUZZLES[puzzle_hash].get('custody', 'CONTRACT'), origin
        base_hash, args = uncurry_fully(puzzle)
        if base_hash is None:
            mod, curried_args = puzzle.uncurry()
            programs = [arg for arg in curried_args.as_iter() if arg.atom is None] if mod != puzzle else []
            if not programs:
                return 'UNKNOWN', origin
            puzzle, origin = programs[-1], 'guessed'
            continue
        base = CONF.KNOWN_PUZZLES[base_hash]
        inner_arg = base.get('inner_arg')
        if inner_arg is None:
            return base.get('custody', 'CONTRACT'), origin
        if inner_arg > len(args):
            logging(debug_logger, "DEBUG", f"CATALOG inner_arg {inner_arg} of {base['name']} past its {len(args)} args")
            return 'UNKNOWN', origin
        inner = args[inner_arg - 1]
        if inner.atom is not None:
            return 'HIDDEN', origin
        puzzle = inner
    return 'UNKNOWN', origin


def source_projects(puzzle_hash: str) -> set:
    """The project ids of a base puzzle: its project field, else the projects of its sources"""
    entry = CONF.KNOWN_PUZZLES.get(puzzle_hash, {})
    if entry.get('project'):
        return {entry['project']}
    project_of = {source: project for project, p in CONF.PUZZLE_TYPES.get('projects', {}).items()
                  for source in p.get('sources', [])}
    return {project_of.get(source.get('project'), source.get('project')) for source in entry.get('sources', [])}


def known_projects() -> list:
    """Every project id of the catalog: the projects of puzzle_types.json and the projects of
    the sources and of the project fields of catalog/puzzles.json"""
    projects = set(CONF.PUZZLE_TYPES.get('projects', {}))
    for puzzle_hash in CONF.KNOWN_PUZZLES:
        projects |= source_projects(puzzle_hash)
    projects.discard(None)
    return sorted(projects)


# every list of puzzle_types.json (families, types, custodies, projects) maps an id to a label:
# the code and the json files keep the id, the screens show the label, so a value is renamed by
# changing its label only. Only a power user reading the json sees the ids.
FIELD_LISTS = {'family': 'families', 'puzzle_type': 'types', 'custody': 'custodies', 'project': 'projects'}


def field_entries(field: str) -> dict:
    return CONF.PUZZLE_TYPES.get(FIELD_LISTS[field], {})


def field_values(field: str) -> list:
    """The ids of a list; for the project, also the projects of the catalog's sources"""
    return known_projects() if field == 'project' else list(field_entries(field))


def value_label(field: str, value) -> str:
    """The label of an id; 'a + b' (an undecided project) gives each label"""
    if not value:
        return value
    entries = field_entries(field)
    return ' + '.join((entries.get(v) or {}).get('label', v) for v in value.split(' + '))


def value_id(field: str, label: str) -> str:
    """The id of a label; a label that is not in the list is a new id"""
    return next((v for v, e in field_entries(field).items() if e.get('label', v) == label), label)


def value_description(field: str, value: str) -> str:
    return (field_entries(field).get(value) or {}).get('description', '')


def project_label(project) -> str:
    return value_label('project', project)


def project_id(label: str) -> str:
    return value_id('project', label)


# --- editing the lists of puzzle_types.json (the lists view) --------------------------------

# the ids the code decides from: they can be renamed (label) but not deleted
CODE_VALUES = {'family': {'XCH', 'CAT', 'SINGLETON', 'UNKNOWN'},
               'puzzle_type': set(FAMILY_ASSET.values()),
               'custody': set(HELD_CUSTODIES) | {'CONTRACT', 'HIDDEN', 'UNKNOWN'},
               'project': {CHIA_PROJECT, 'unknown'}}
PROJECT_ROLES = ('app', 'framework', 'base')


def new_value_id(field: str, label: str) -> str:
    """An id for a new value, made from its label (projects lowercase, the others uppercase),
    not used yet in its list"""
    base = re.sub(r'[^0-9A-Za-z]+', '_', label).strip('_') or 'VALUE'
    base = base.lower() if field == 'project' else base.upper()
    value, n = base, 2
    while value in field_entries(field):
        value, n = f"{base}_{n}", n + 1
    return value


def value_uses(field: str, value: str) -> int:
    """How many entries of the catalog files name the value: the hand fields of
    catalog/puzzles.json (for a project, also the sources it groups), the overrides of
    catalog/layered_puzzles.json"""
    n = sum(1 for e in CONF.KNOWN_LAYERED_PUZZLES.values() if e.get(field) == value)
    for e in CONF.KNOWN_PUZZLES.values():
        if e.get(field) == value:
            n += 1
        elif field == 'project' and not e.get('project') and value in source_projects(e.get('puzzle_hash', '')):
            n += 1
    return n


def dump_puzzle_types(data: dict) -> str:
    """puzzle_types.json with one value per line, as it is written by hand"""
    parts = []
    for name, values in data.items():
        if isinstance(values, dict):
            body = ',\n'.join(f'        {json.dumps(k)}: {json.dumps(v, ensure_ascii=False)}' for k, v in values.items())
            parts.append(f'    {json.dumps(name)}: {{\n{body}\n    }}')
        else:
            parts.append(f'    {json.dumps(name)}: {json.dumps(values, ensure_ascii=False)}')
    return '{\n' + ',\n'.join(parts) + '\n}\n'


def edit_puzzle_types(change):
    """Read catalog/puzzle_types.json from disk, apply change(data) and write it back (one value
    per line), then update the lists in memory. Raise ValueError if the file is not valid json
    (it is never overwritten)."""
    path = CONF.PUZZLE_TYPES_PATH
    with CONF.LAYERED_PUZZLES_LOCK:
        with open(path, 'r') as f:
            data = json.loads(f.read())
        if change(data) is False:
            return
        tmp_path = f"{path}.tmp"
        with open(tmp_path, 'w') as f:
            f.write(dump_puzzle_types(data))
        os.replace(tmp_path, path)
        _catalog_file_stamps[path] = _file_stamp(path)
        _replace_in_place(CONF.PUZZLE_TYPES, data)
    bump_catalog_generation()


def save_list_value(field: str, value: str, label: str, description: str, role: str = None,
                    sources: list = None) -> str:
    """Add (value None: a new id from the label) or change a value of a list. Return its id."""
    label = label.strip()
    if not label:
        raise ValueError('the label is empty')
    if any(e.get('label', v) == label for v, e in field_entries(field).items() if v != value):
        raise ValueError(f'"{label}" is already a label of this list')
    value = value or new_value_id(field, label)

    def change(data):
        entries = data.setdefault(FIELD_LISTS[field], {})
        entry = dict(entries.get(value, {}))
        entry['label'] = label
        if field == 'project':
            entry.pop('description', None)
            if description.strip():
                entry['description'] = description.strip()
            if role and role != 'app':
                entry['role'] = role
            else:
                entry.pop('role', None)
            if sources:
                entry['sources'] = sources
            else:
                entry.pop('sources', None)
        else:
            entry['description'] = description.strip()
        entries[value] = entry
    edit_puzzle_types(change)
    return value


def delete_list_value(field: str, value: str):
    """Delete a value no catalog entry and no code uses (ValueError otherwise)"""
    if value in CODE_VALUES.get(field, ()):
        raise ValueError('the code uses this value: it can be renamed, not deleted')
    uses = value_uses(field, value)
    if uses:
        raise ValueError(f'{uses} catalog entries use this value')
    edit_puzzle_types(lambda data: data.get(FIELD_LISTS[field], {}).pop(value, None) is not None or False)


# the role of a project (project_roles in puzzle_types.json) decides which project of the
# layers leads a puzzle: an app before a framework, a framework before the base (chia)
PROJECT_ROLE_RANK = {'base': 0, 'framework': 1, 'app': 2}


def project_role(project: str) -> str:
    return CONF.PUZZLE_TYPES.get('projects', {}).get(project, {}).get('role', 'app')


def layer_hashes(layered_puzzle_fingerprint: str) -> list:
    """The layers of a layered puzzle fingerprint, without the CURRIED_AGAIN markers"""
    return [h for h in layered_puzzle_fingerprint.split('|') if h != CURRIED_AGAIN]


def all_layers_known(layered_puzzle_fingerprint: str) -> bool:
    if layered_puzzle_fingerprint == QUOTED_CONDITIONS_FINGERPRINT:
        return True
    return all(h in CONF.KNOWN_PUZZLES for h in layer_hashes(layered_puzzle_fingerprint))


def classify_fingerprint(layered_puzzle_fingerprint: str, puzzle: PyProgram = None, overrides: bool = True) -> dict:
    """name, family, puzzle_type, custody, project of a layer combination, each value with
    its origin: 'set' (layered_puzzles.json), 'layer N', 'walk', 'guessed', 'held', ...
    puzzle: a puzzle reveal with this fingerprint, for the custody (cached per fingerprint).
    overrides=False: what the layers give, without the entry's overrides."""
    entry = (CONF.KNOWN_LAYERED_PUZZLES.get(layered_puzzle_fingerprint) or {}) if overrides else {}
    out = {'name': entry.get('name')}
    if layered_puzzle_fingerprint == QUOTED_CONDITIONS_FINGERPRINT:
        out.update(family=('XCH', 'quoted conditions'), custody=('ANYONE', 'quoted conditions'),
                   puzzle_type=('XCH', 'held'), project=(CHIA_PROJECT, 'quoted conditions'),
                   project_dependencies=([], 'quoted conditions'))
        return out
    if layered_puzzle_fingerprint.startswith(SHAPE_FINGERPRINT_PREFIX):
        out.update(family=('UNKNOWN', 'unknown code'), custody=('UNKNOWN', 'unknown code'),
                   puzzle_type=(None, 'unknown code'), project=('unknown', 'unknown code'),
                   project_dependencies=([], 'unknown code'))
        return out
    layers = layer_hashes(layered_puzzle_fingerprint)
    fields = [CONF.KNOWN_PUZZLES.get(h, {}) for h in layers]

    # family: the outer layer. A layer with a family is a wrapper (skipped for the puzzle type
    # and the label) when it also wraps an inner puzzle (inner_arg); without one it is a contract
    # that keeps its own lineage (e.g. circuit's announcer), its family is its behavior
    family_layer = bool(fields) and 'family' in fields[0] and 'inner_arg' in fields[0]
    if 'family' in entry:
        out['family'] = (entry['family'], 'set')
    elif family_layer:
        out['family'] = (fields[0]['family'], 'layer 1')
    elif fields and 'family' in fields[0]:
        out['family'] = (fields[0]['family'], 'layer 1, own lineage')
    elif layers and layers[0] in CONF.KNOWN_PUZZLES:
        out['family'] = ('XCH', 'no family layer')
    else:
        # not XCH: an unknown outer layer may wrap the coin (a CAT or singleton build not in
        # the catalog)
        out['family'] = ('UNKNOWN', 'unknown outer layer')

    # custody: the innermost puzzle
    if 'custody' in entry:
        out['custody'] = (entry['custody'], 'set')
    elif layered_puzzle_fingerprint in _custody_cache:
        out['custody'] = _custody_cache[layered_puzzle_fingerprint]
    elif puzzle is not None:
        out['custody'] = _custody_cache[layered_puzzle_fingerprint] = walk_custody(puzzle)
    elif len(layers) == 1 and layers[0] in CONF.KNOWN_PUZZLES:
        out['custody'] = (fields[0].get('custody', 'CONTRACT'), 'layer 1')
    else:
        out['custody'] = (None, 'no example')

    # type: the outermost purpose layer inside the family layer, else the asset of a held coin
    if 'puzzle_type' in entry:
        out['puzzle_type'] = (entry['puzzle_type'], 'set')
    else:
        start = 1 if family_layer else 0
        found = next(((f['puzzle_type'], f'layer {i + 1}') for i, f in enumerate(fields)
                      if i >= start and 'puzzle_type' in f), None)
        if found:
            out['puzzle_type'] = found
        elif out['custody'][0] in HELD_CUSTODIES:
            out['puzzle_type'] = (FAMILY_ASSET.get(out['family'][0]), 'held')
        else:
            out['puzzle_type'] = (None, 'app contract' if out['custody'][0] == 'CONTRACT' else 'not known')

    # project: the lead, the projects of the layers with the strongest role (app > framework >
    # base); the other ones, without the base, are its dependencies
    projects = set()
    for h in layers:
        projects |= source_projects(h)
    projects.discard(None)
    if 'project' in entry:
        out['project'] = (entry['project'], 'set')
    else:
        rank = max((PROJECT_ROLE_RANK.get(project_role(p), 2) for p in projects), default=0)
        lead = {p for p in projects if PROJECT_ROLE_RANK.get(project_role(p), 2) == rank}
        if rank == 0 and any(h not in CONF.KNOWN_PUZZLES for h in layers):
            # only the base is known: the unknown layer may be an app's
            out['project'] = ('unknown', 'unknown layer')
        elif len(lead) == 1:
            out['project'] = (lead.pop(), 'layers')
        elif lead:
            out['project'] = (' + '.join(sorted(lead)), 'undecided')
        else:
            out['project'] = (CHIA_PROJECT, 'layers')
    leads = set((out['project'][0] or '').split(' + '))
    out['project_dependencies'] = (sorted(p for p in projects if p not in leads and project_role(p) != 'base'),
                                   'layers')
    return out


def classification_label(c: dict, layered_puzzle_fingerprint: str) -> str:
    """The name of a combination, or a label made from its classification"""
    if c.get('name'):
        return c['name']
    puzzle_type, custody = value_label('puzzle_type', c['puzzle_type'][0]), value_label('custody', c['custody'][0])
    if puzzle_type:
        return f"{puzzle_type} ({custody})" if custody else puzzle_type
    inside = layer_hashes(layered_puzzle_fingerprint)[1 if c['family'][1] == 'layer 1' else 0:]
    core = next((CONF.KNOWN_PUZZLES[h]['name'].lstrip('-').split('-')[-1] for h in inside
                 if h in CONF.KNOWN_PUZZLES), None)
    if core:
        return f"{project_label(c['project'][0])}: {core}"
    # nothing known inside: the name it has in puzzle_harvesting/, if any
    return CONF.UNKNOWN_LAYERED_PUZZLES.get(layered_puzzle_fingerprint, {}).get('name')


def compare_to_known_puzzles(puzzle_hash):
    """Look up a puzzle hash in known puzzles, then in saved unknown puzzles. """
    if puzzle_hash == CURRIED_AGAIN:
        return CURRIED_AGAIN_NAME
    # Check against known puzzles first
    puzzle = CONF.KNOWN_PUZZLES.get(str(puzzle_hash), None)
    if puzzle is not None:
        return puzzle['name']

    # Check against previously saved unknown puzzles
    puzzle = CONF.UNKNOWN_PUZZLES.get(str(puzzle_hash), None)
    if puzzle is not None:
        return puzzle['name']

    return CONF.UNKNOWN_PUZZLE


# --- catalog files edited by hand ---------------------------------------------
# layered_puzzles.json and puzzle_types.json are in the repo and can be edited by hand
# while roto runs: a change on disk is reloaded (reload_catalog_files), and a save reads
# the file from disk and changes only its own entry (update_catalog_file), so nothing
# written by hand is lost. Both need CONF.LAYERED_PUZZLES_LOCK.

# path -> (mtime_ns, size) of the file as last loaded or written by roto
_catalog_file_stamps = {}


def _catalog_files():
    """(path, dict in memory) of the catalog files that are watched"""
    return ((CONF.KNOWN_LAYERED_PUZZLES_PATH, CONF.KNOWN_LAYERED_PUZZLES),
            (CONF.PUZZLE_TYPES_PATH, CONF.PUZZLE_TYPES))


def _file_stamp(path):
    stat = os.stat(path)
    return stat.st_mtime_ns, stat.st_size


def _replace_in_place(target: dict, data: dict):
    """Update the dict in memory without replacing it, other modules keep a reference to it.
    No clear(): a reader in another thread never sees an empty catalog."""
    target.update(data)
    for key in [key for key in target if key not in data]:
        del target[key]


def reload_catalog_files():
    """Reload the catalog files changed on disk. Return the paths reloaded.
    A file that is not valid json (eg: an edit not finished) is skipped until it changes again."""
    reloaded = []
    with CONF.LAYERED_PUZZLES_LOCK:
        for path, target in _catalog_files():
            try:
                stamp = _file_stamp(path)
            except FileNotFoundError:
                continue
            last_stamp = _catalog_file_stamps.get(path)
            _catalog_file_stamps[path] = stamp
            if last_stamp is None or stamp == last_stamp:
                # first check: the file was just loaded by CONFtiller
                continue
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
            except ValueError as e:
                logging(debug_logger, "DEBUG", f"CATALOG {path} is not valid json, keeping the previous version: {e}")
                continue
            _replace_in_place(target, data)
            reloaded.append(path)
    return reloaded


def update_catalog_file(path, target: dict, change):
    """Read the file from disk, apply change(data) and write it back, then update the dict
    in memory. change returns False when there is nothing to write.
    Raise ValueError if the file on disk is not valid json: it is never overwritten."""
    with open(path, 'r') as f:
        text = f.read()
    data = json.loads(text)
    if change(data) is False:
        _replace_in_place(target, data)
        return
    tmp_path = f"{path}.tmp"
    with open(tmp_path, 'w') as f:
        json.dump(data, f, indent=4)
        if text.endswith('\n'):
            f.write('\n')
    os.replace(tmp_path, path)  # a crash can not leave a truncated file
    _catalog_file_stamps[path] = _file_stamp(path)
    _replace_in_place(target, data)


# --- harvesting in batches: a backfill adds hundreds of entries, each write rewrites a whole
# (several MB) json file. Inside harvest_batch() the files are written once, at the end.
_harvest_batch_depth = 0
_harvest_dirty = set()  # paths to write when the batch ends
_harvest_batch_lock = threading.Lock()


def _write_harvest_file(path, data: dict):
    with _harvest_batch_lock:
        if _harvest_batch_depth:
            _harvest_dirty.add(path)
            return
    with open(path, 'w') as f:
        json.dump(data, f, indent=4)


@contextlib.contextmanager
def harvest_batch():
    global _harvest_batch_depth
    with _harvest_batch_lock:
        _harvest_batch_depth += 1
    try:
        yield
    finally:
        with _harvest_batch_lock:
            _harvest_batch_depth -= 1
            paths = set(_harvest_dirty) if _harvest_batch_depth == 0 else set()
            if paths:
                _harvest_dirty.clear()
        for path in paths:
            if path == CONF.UNKNOWN_PUZZLES_PATH:
                with CONF.UNKNOWN_PUZZLES_LOCK:
                    _write_harvest_file(path, CONF.UNKNOWN_PUZZLES)
            else:
                with CONF.UNKNOWN_LAYERED_PUZZLES_LOCK:
                    _write_harvest_file(path, CONF.UNKNOWN_LAYERED_PUZZLES)


# the generation of the catalog files: incremented when they change (reload, a name saved, a
# list edited), so the classifications cached by the screens are computed again
_catalog_generation = 0


def catalog_generation() -> int:
    return _catalog_generation


def bump_catalog_generation():
    global _catalog_generation
    _catalog_generation += 1


def save_layered_puzzle(layered_puzzle_fingerprint: str, sub_hashes: list, sub_names: list):
    """Save a layer combination with an unknown layer in puzzle_harvesting/layered_puzzles.json,
    named unknown_layered_NN, and return its name. A combination whose layers are all known is
    not saved: its classification comes from its layers (classify_fingerprint).
    The catalog (catalog/layered_puzzles.json) is written only when the user saves a name."""
    with CONF.UNKNOWN_LAYERED_PUZZLES_LOCK:
        target = CONF.UNKNOWN_LAYERED_PUZZLES
        if layered_puzzle_fingerprint in target:
            return target[layered_puzzle_fingerprint]['name']
        numbers = [int(e['name'].rsplit('_', 1)[-1]) for e in target.values()
                   if e.get('name', '').startswith('unknown_layered_') and e['name'].rsplit('_', 1)[-1].isdigit()]
        name = f"unknown_layered_{max(numbers, default=0) + 1:02d}"
        target[layered_puzzle_fingerprint] = {'name': name, 'sub_puzzle_hashes': sub_hashes, 'sub_puzzle_names': sub_names}
        # local file, only roto writes it
        _write_harvest_file(CONF.UNKNOWN_LAYERED_PUZZLES_PATH, target)
        return name


def harvest_unknown(layered_puzzle_fingerprint: str, sub_puzzle_hashes: list, puzzle: PyProgram):
    """Put a combination with an unknown layer in puzzle_harvesting/: the combination in
    layered_puzzles.json (unknown_layered_NN) and its unknown puzzles in puzzles.json
    (unknown_puzz_NN, by unroll_puzzle_to_nodes). Called by the scanners for the fingerprints they
    see first; a known or named combination, or one already harvested, is skipped.
    Return True if something was added."""
    if (layered_puzzle_fingerprint in CONF.KNOWN_LAYERED_PUZZLES or layered_puzzle_fingerprint in CONF.UNKNOWN_LAYERED_PUZZLES
            or layered_puzzle_fingerprint.startswith((QUOTED_CONDITIONS_FINGERPRINT, SHAPE_FINGERPRINT_PREFIX)) or all_layers_known(layered_puzzle_fingerprint)):
        return False
    unroll_puzzle_to_nodes(puzzle)  # saves the unknown puzzles
    save_layered_puzzle(layered_puzzle_fingerprint, sub_puzzle_hashes, [compare_to_known_puzzles(h) for h in sub_puzzle_hashes])
    return True


def compare_unrolled_puzzle_to_known_layered_puzzles(sub_puzzle_hashes: list, puzzle: PyProgram = None):
    """(puzzle type, label) of a layer combination: its derived type ('-' when it has none) and
    its name, or a label made from its classification. A combination with an unknown layer that
    is not in the catalog is saved in puzzle_harvesting/layered_puzzles.json.
    puzzle: the puzzle reveal, for the custody."""
    layered_puzzle_fingerprint = '|'.join(sub_puzzle_hashes)
    named = layered_puzzle_fingerprint in CONF.KNOWN_LAYERED_PUZZLES and CONF.KNOWN_LAYERED_PUZZLES[layered_puzzle_fingerprint].get('name')
    if not named and not all_layers_known(layered_puzzle_fingerprint):
        harvest_name = CONF.UNKNOWN_LAYERED_PUZZLES.get(layered_puzzle_fingerprint, {}).get('name') or save_layered_puzzle(
            layered_puzzle_fingerprint, sub_puzzle_hashes, [compare_to_known_puzzles(h) for h in sub_puzzle_hashes])
        c = classify_fingerprint(layered_puzzle_fingerprint, puzzle)
        return value_label('puzzle_type', c['puzzle_type'][0]) or '-', harvest_name
    c = classify_fingerprint(layered_puzzle_fingerprint, puzzle)
    return value_label('puzzle_type', c['puzzle_type'][0]) or '-', classification_label(c, layered_puzzle_fingerprint)


def print_tree_path(path: list, level):
    text = f'lev: {level} | '
    for i in path:
        if len(i) == 0:
            text += "()"
        else:
            text += f"({i[0]}_{i[1]}), "
    return text


def save_unknown_puzzle(puzzle_hash: str, puzzle: PyProgram, example: str = None):
    """Save an unknown puzzle to unknown_puzzle.json if not already present."""
    with CONF.UNKNOWN_PUZZLES_LOCK:
        if puzzle_hash in CONF.KNOWN_PUZZLES or puzzle_hash in CONF.UNKNOWN_PUZZLES:
            return

        max_num = 0
        for entry in CONF.UNKNOWN_PUZZLES.values():
            name = entry.get('name', '')
            if name.startswith('unknown_puzz_'):
                try:
                    num = int(name.split('_')[-1])
                    if num > max_num:
                        max_num = num
                except ValueError:
                    pass

        new_num = max_num + 1
        unique_name = f"unknown_puzz_{new_num:02d}"

        entry = {
            "file_name": None,
            "name": unique_name,
            "puzzle_hash": puzzle_hash,
            "clvm": None,
            "bytecode": "0x" + bytes(puzzle).hex(),
            "bytecode_disassembled": rs_disassemble(bytes(puzzle))
        }
        if example is not None:
            entry["example_curried_instance"] = example

        CONF.UNKNOWN_PUZZLES[puzzle_hash] = entry
        _write_harvest_file(CONF.UNKNOWN_PUZZLES_PATH, CONF.UNKNOWN_PUZZLES)


G1_INFINITY = bytes(G1Element())  # c0 followed by 47 zero bytes
TIMESTAMP_RANGE = (1_500_000_000, 2_500_000_000)  # an int in this range is shown also as a date


def puzzle_hash_to_address(puzzle_hash: bytes) -> str:
    from chia.util.bech32m import encode_puzzle_hash
    return encode_puzzle_hash(bytes32(puzzle_hash), CONF.ADD_PREFIX)


CHAIN_CHECKING = 'checking the chain...'


def chain_lookup_hash(hash_hex: str) -> str:
    """What 32 bytes are on chain: a coin id, a puzzle hash with coins, a hint of coins.
    Empty if the node knows nothing about them (or does not answer). Slow: run it in a thread.
    A popular puzzle hash returns all its coin records, it can take long."""
    found = []
    try:
        record = RPC.call_rpc_node('get_coin_record_by_name', name='0x' + hash_hex)
    except Exception:
        record = None  # not a coin id: the node answers with an error
    if record:
        spent = (f"spent at height {record['spent_block_index']:,}" if record.get('spent')
                 else 'unspent')
        found.append(f"coin id: {UTILS.xch_amount(record['coin']['amount'])} XCH, created at height "
                     f"{record['confirmed_block_index']:,}, {spent}")
    for method, label in (('get_coin_records_by_puzzle_hash', 'puzzle hash'),
                          ('get_coin_records_by_hint', 'hint')):
        key = 'puzzle_hash' if label == 'puzzle hash' else 'hint'
        try:
            records = RPC.call_rpc_node(method, **{key: '0x' + hash_hex, 'include_spent_coins': True})
        except Exception:
            records = None
        if records:
            if label == 'puzzle hash':
                found.append(f"address: {puzzle_hash_to_address(bytes.fromhex(hash_hex))}, "
                             f"{len(records):,} coin{'s' * (len(records) != 1)}")
            else:
                found.append(f"hint of {len(records):,} coin{'s' * (len(records) != 1)}")
    return ' | '.join(found)


def unknown_hashes_in_arg(arg: PyProgram, cat_names: dict = None) -> list:
    """The 32 byte atoms of a curried arg (also inside a list) that are not a known puzzle
    or a CAT asset id: the ones to look up on chain with chain_lookup_hash"""
    hashes, stack = [], [arg]
    while stack:
        n = stack.pop()
        if n.pair is not None:
            # a curried or known puzzle is not data
            if compare_to_known_puzzles(n.get_tree_hash().hex()) != CONF.UNKNOWN_PUZZLE:
                continue
            if n.uncurry()[0] != n:
                continue
            stack += [PyProgram.to(n.pair[1]), PyProgram.to(n.pair[0])]
        elif len(n.atom) == 32:
            h = n.atom.hex()
            if compare_to_known_puzzles(h) == CONF.UNKNOWN_PUZZLE and h not in (cat_names or {}):
                hashes.append(h)
    return hashes


def _short_atom_type(atom: bytes, cat_names: dict = None, chain: dict = None) -> str:
    """Type of an atom in a few words, with what it is when known (for lists)"""
    kind, meaning = _describe_atom(atom, cat_names, chain)
    if not meaning or meaning == CHAIN_CHECKING or kind != 'hash 32':
        return kind
    if meaning.startswith(('mod or puzzle: ', 'CAT asset id: ')):
        return f"{kind} = {meaning.split(': ', 1)[1]}"
    # on chain: only what it is (coin id, address, hint), the details are too long for a list
    return f"{kind} = " + ', '.join(part.split(':')[0].split(' of ')[0] for part in meaning.split(' | '))


def _describe_atom(atom: bytes, cat_names: dict = None, chain: dict = None):
    size = len(atom)
    if size == 0:
        return 'nil', ''
    if size == 32:
        name = compare_to_known_puzzles(atom.hex())
        if name != CONF.UNKNOWN_PUZZLE:
            return 'hash 32', f"mod or puzzle: {name}"
        cat = (cat_names or {}).get(atom.hex())
        if cat:
            return 'hash 32', f"CAT asset id: {cat}"
        # looked up on chain by the screen: None while it runs, '' if nothing was found
        found = (chain or {}).get(atom.hex(), '')
        return 'hash 32', CHAIN_CHECKING if found is None else found
    if size == 48:
        if atom == G1_INFINITY:
            # a valid point, but no key: anyone can sign for it
            return 'pubkey 48', 'infinity point (empty key)'
        try:
            G1Element.from_bytes(atom)
            return 'pubkey 48', 'valid BLS public key'
        except Exception:
            return 'bytes 48', 'not a valid BLS public key'
    if size == 96:
        try:
            G2Element.from_bytes(atom)
            return 'signature 96', 'valid BLS signature'
        except Exception:
            return 'bytes 96', 'not a valid BLS signature'
    if size >= 3 and all(32 <= b < 127 for b in atom):
        return 'text', atom.decode()
    if size <= 8:
        value = int.from_bytes(atom, 'big', signed=True)
        if TIMESTAMP_RANGE[0] <= value <= TIMESTAMP_RANGE[1]:
            return 'int', f"{value:,}, as date: {UTILS.timestamp_to_date(value)}"
        return 'int', f"{value:,}"
    return f"bytes {size}", ''


def describe_curried_arg(arg: PyProgram, cat_names: dict = None, chain: dict = None):
    """Return (type, meaning) of a curried arg: hash 32 (with the name of a known mod, the
    CAT name of an asset id, or what it is on chain), pubkey 48, signature 96, int, text, list,
    puzzle (a curried puzzle or a known one).
    cat_names: asset id hex -> 'name (TICKER)'
    chain: hash hex -> chain_lookup_hash result, None while the lookup runs"""
    if arg.pair is None:
        return _describe_atom(arg.atom, cat_names, chain)

    arg_hash = arg.get_tree_hash()
    name = compare_to_known_puzzles(arg_hash.hex())
    # a known puzzle keeps its name: uncurry also splits a puzzle that is not curried,
    # e.g. settlement payments `(a (q . code) 1)` gives its code as a mod with no args
    if name == CONF.UNKNOWN_PUZZLE:
        mod, _ = arg.uncurry()
        if mod != arg:
            name = compare_to_known_puzzles(mod.get_tree_hash().hex())
    if name != CONF.UNKNOWN_PUZZLE:
        return 'puzzle', f"{name}, address: {puzzle_hash_to_address(arg_hash)}"

    # a list (or pairs): the type of its first atoms
    items, node = 0, arg
    while node.pair is not None:
        items += 1
        node = node.pair[1]
    kind = f"list ({items})" if node.atom == b'' else 'pairs'
    atoms, stack = [], [arg]
    while stack and len(atoms) < 5:
        n = stack.pop()
        if n.pair is not None:
            stack += [n.pair[1], n.pair[0]]
        else:
            atoms.append(n.atom)
    leaves = [_short_atom_type(a, cat_names, chain) for a in atoms if a != b'']
    return kind, ', '.join(leaves) + (', ...' if stack else '')


def unroll_puzzle_to_nodes(puzzle: PyProgram, level: int = 0, array: list = None, path: list = None):
    """Recursive function to uncurry a puzzle to list all the puzzles used and their parameters"""
    if array is None:
        array = []
    if path is None:
        path = [('L',0)]


    puzzle_hash = puzzle.get_tree_hash().hex()
    puzzle_name = compare_to_known_puzzles(puzzle_hash)

    mod, curried_args = puzzle.uncurry()
    mod_hash = mod.get_tree_hash().hex()
    mod_name = compare_to_known_puzzles(mod_hash)

    level += 1

    # Base structure for this node
    node = {
        "level": level,
        "path": print_tree_path(path, level),
        "is_curried": None,
        "hash": None,
        "puzz_name": None,
        "disassembly": None,
        "puzzle_hash": puzzle_hash,  # hash of the puzzle at this level, curried args included
        "args": [],
        "arg_hex": []  # the curried args serialized, for describe_curried_arg
    }

    if mod != puzzle and puzzle_name == CONF.UNKNOWN_PUZZLE:
        node['is_curried'] = True
        node['hash'] = mod_hash
        node['puzz_name'] = mod_name
        node['disassembly'] = rs_disassemble(bytes(mod))  # should we put the disassembly of the mod?
        base_hash = known_base_of(mod) if mod_name == CONF.UNKNOWN_PUZZLE else None
        if base_hash is not None:
            # a known puzzle curried again: not an unknown puzzle, it is not saved
            node['puzz_name'] = f"{compare_to_known_puzzles(base_hash)}, curried again"

        # Save unknown template with an example curried instance
        if mod_name == CONF.UNKNOWN_PUZZLE and base_hash is None:
            save_unknown_puzzle(
                mod_hash,
                mod,
                example=rs_disassemble(bytes(puzzle))
            )

        # Recursively capture arguments and store in the node
        count = 0
        for arg in curried_args.as_iter():
            node["arg_hex"].append(bytes(arg).hex())
            arg_hash = arg.get_tree_hash().hex()
            arg_name = compare_to_known_puzzles(arg_hash)
            if arg_name != CONF.UNKNOWN_PUZZLE:
                node["args"].append(arg_name)
            else:
                sub_mod, sub_curried_args = arg.uncurry()
                if sub_mod != arg:
                    sub_mod_hash = sub_mod.get_tree_hash().hex()
                    sub_mod_name = compare_to_known_puzzles(sub_mod_hash)
                    node["args"].append(sub_mod_name)
                else:
                    node["args"].append(rs_disassemble(bytes(arg)))
            count += 1

        array.append(node)

        # Check if the mod itself can be uncurried further
        # here add the number
        mod2, curried_args2 = mod.uncurry()
        if mod2 != mod and node['puzz_name'] == CONF.UNKNOWN_PUZZLE:
            new_path = path + [('LL', 0)]
            unroll_puzzle_to_nodes(mod, level, array=array, path=new_path)

        # scan again the args to launch the recursion
        # here add the letters
        for n, arg in enumerate(curried_args.as_iter()):
            current_path = path.copy()
            arg_hash = arg.get_tree_hash().hex()
            arg_name = compare_to_known_puzzles(arg_hash)
            sub_mod, sub_curried_args = arg.uncurry()
            if sub_mod != arg:
                sub_mod_hash = sub_mod.get_tree_hash().hex()
                sub_mod_name = compare_to_known_puzzles(sub_mod_hash)
                # remove last level and fo to the right
                current_path.pop(-1)
                ## TODO move this if at the beginning of unroll_puzzle_to_nodes by
                ## passing the path without [(L, 0)]
                if arg_name != CONF.UNKNOWN_PUZZLE:
                    new_path = current_path + [('R',n)] + [()]
                else:
                    new_path = current_path + [('R',n)] + [('L', 0)]
                unroll_puzzle_to_nodes(arg, level, array=array, path=new_path)

    elif puzzle_name != CONF.UNKNOWN_PUZZLE:
        node['is_curried'] = False
        node['hash'] = puzzle_hash
        node['puzz_name'] = puzzle_name
        node['disassembly'] = rs_disassemble(bytes(puzzle))

        array.append(node)

    else:
        # Non-curried unknown puzzle
        node['is_curried'] = False
        node['hash'] = puzzle_hash
        node['puzz_name'] = puzzle_name
        node['disassembly'] = rs_disassemble(bytes(puzzle))

        array.append(node)
        save_unknown_puzzle(puzzle_hash, puzzle)

    return array


def unroll_puzzle_to_names(puzzle: PyProgram, level: int = 0, array: list = None):
    """Recursive function to uncurry a puzzle to list all the names of the puzzles used
       output: names, hashes"""
    if array is None:
        array = [[],[]]


    puzzle_hash = puzzle.get_tree_hash().hex()
    puzzle_name = compare_to_known_puzzles(puzzle_hash)
    # the walk depends only on the shared catalog (catalog/puzzles.json), not on the local
    # puzzle_harvesting/puzzles.json, or the same puzzle would get a different fingerprint on every machine
    puzzle_is_known = puzzle_hash in CONF.KNOWN_PUZZLES

    mod, curried_args = puzzle.uncurry()
    mod_hash = mod.get_tree_hash().hex()
    mod_name = compare_to_known_puzzles(mod_hash)
    mod_is_known = mod_hash in CONF.KNOWN_PUZZLES

    if mod != puzzle and not puzzle_is_known:

        if not mod_is_known and known_base_of(mod) is not None:
            # a known puzzle curried again: the known puzzle is added by the recursion below
            array[0].append(CURRIED_AGAIN_NAME)
            array[1].append(CURRIED_AGAIN)
        else:
            array[0].append(mod_name)
            array[1].append(mod_hash)

        # Check if the mod itself can be uncurried further
        mod2, curried_args2 = mod.uncurry()
        if mod2 != mod and not mod_is_known:
            # here we should check if there are multiple
            unroll_puzzle_to_names(mod, level, array=array)

        # scan again the args to launch the recursion
        for n, arg in enumerate(curried_args.as_iter()):
            sub_mod, sub_curried_args = arg.uncurry()
            if sub_mod != arg:
                # remove last level and fo to the right
                unroll_puzzle_to_names(arg, level, array=array)
    elif puzzle_is_known:
        # case where a puzzle is use as argument without any curried args
        array[0].append(puzzle_name)
        array[1].append(puzzle_hash)

    return array[0], array[1]


def unroll_puzzle_from_coin_id(coin_record: TYPES.CoinRecordRoto):

    puz = None
    if coin_record.spent_block_index > 0:
        try:
            spent_height = coin_record.spent_block_index
            parent = coin_record.coin.parent_coin_info.hex()
            puzzle = coin_record.coin.puzzle_hash.hex()
            amount = coin_record.coin.amount

            logging(debug_logger, "DEBUG", f"LOAD i fetcher parenty: {parent}")
            logging(debug_logger, "DEBUG", f"LOAD i fetcher puzz: {puzzle}")
            logging(debug_logger, "DEBUG", f"LOAD i fetcher amo: {amount}")
            coin_name = UTILS.calc_coin_id(parent, puzzle, amount)  # we already have the coin_name
            logging(debug_logger, "DEBUG", f"LOAD i fetcher coin NAME: {coin_name}")

            logging(debug_logger, "DEBUG", f"LOAD i here the COIN NAMEEEEE: {coin_name}")
            logging(debug_logger, "DEBUG", f"LOAD i SPENRT NAMEEEEE: {coin_record.coin_name}")
            logging(debug_logger, "DEBUG", f"LOAD i SPENRT NAMEEEEE: {coin_record.coin_name.hex()}")
            logging(debug_logger, "DEBUG", f"LOAD i SPENRT height: {spent_height}")
            out = RPC.call_rpc_node('get_puzzle_and_solution', coin_id=coin_record.coin_name.hex(), height=spent_height)
            program = PyProgram.fromhex(out['puzzle_reveal'])
            puzzle_disassembled = py_disassemble(program)
            logging(debug_logger, "DEBUG", f"LOAD i fetcher program: {program}")
            unroll_puzzles = unroll_puzzle_to_nodes(program)
            puz_names, puz_hashes = unroll_puzzle_to_names(program)
            layered_puzzle_type, layered_puzzle_name = compare_unrolled_puzzle_to_known_layered_puzzles(puz_hashes, program)
            logging(debug_logger, "DEBUG", f"LOAD puz_hashes: {puz_hashes}")

            puz = TYPES.PuzzleRecord(out, puzzle_disassembled, unroll_puzzles, layered_puzzle_type, layered_puzzle_name,
                                     layered_puzzle_status('|'.join(puz_hashes)))

        except Exception as e:
            logging(debug_logger, "DEBUG", f"LOAD program exc {e}")
            UTILS.logging_traceback("decode puzzle")

    else:
        # check teh coin parent
        pass

    return puz


def get_coin_parent(coin_parent_id: bytes32):
    """if now coin are found return the record, if not look into the block for ephemeral coins"""
    pass


def get_coin_type_from_parent(parent_coin_id, confirmed_height):
    out = RPC.call_rpc_node(
        'get_puzzle_and_solution',
        coin_id=parent_coin_id,
        height=confirmed_height
    )
    program = PyProgram.fromhex(out['puzzle_reveal'])
    puz_names, puz_hashes = unroll_puzzle_to_names(program)
    layered_puzzle_type_str, _ = compare_unrolled_puzzle_to_known_layered_puzzles(puz_hashes)

    # when this is written: decide from the mod hashes of the layers (eg: the CAT layer), not
    # from the family or the puzzle type, which people can rename in the catalog
#    match puzzle_family:
#        case STD:
#            pass
#        case SINGLETON:
#            pass
#        case CAT:
#            pass
#        case _:
#            pass
#
#


def get_type_unspent_coin(coin_record: TYPES.CoinRecordRoto):
    """For an unspent coin, fetch the parent's puzzle reveal and deduce the coin type.

    Args:
        coin_record: A CoinRecordRoto representing an unspent coin.

    Returns:
        The puzzle type text of the catalog (shown only, see TYPES.PuzzleStatus), or None if it
        can not be found.
    """


    # check if there are spent coins with the same puzzle
    fetcher = WDB.FetchMaker.puzzle_hash_fetcher(coin_record.coin.puzzle_hash, 'confirmed_index', 0, max_height, False)
    db_conn = WDB.get_connection(CONF.DB_BLOCKCHAIN_RO)
    all_coins = fetcher(db_conn, 0, 1000)
    spent_coins = [c for c in all_coins if c.spent_block_index > 0]

    if spent_coins:
        pass
        # do on a spent coin
    else:
        pass
        # do on the parent


        confirmed_height = coin_record.confirmed_block_index
        parent_coin_id = coin_record.coin.parent_coin_info.hex()

        try:
            out = RPC.call_rpc_node(
                'get_puzzle_and_solution',
                coin_id=parent_coin_id,
                height=confirmed_height
            )
            program = PyProgram.fromhex(out['puzzle_reveal'])
            puz_names, puz_hashes = unroll_puzzle_to_names(program)
            layered_puzzle_type_str, _ = compare_unrolled_puzzle_to_known_layered_puzzles(puz_hashes)

            is_parent_same_type_child(layered_puzzle_type_str, out)

            # what kind of puzzle id?
            # cat do this
            # nft / singleton do this
            # unknown do this
            return layered_puzzle_type_str

        except Exception as e:
            logging(debug_logger, "DEBUG", f"get_type_unspent_coin failed: {e}")
            return None


def layered_puzzle_status(layered_puzzle_fingerprint: str) -> TYPES.PuzzleStatus:
    """VERIFIED if a person saved the combination in catalog/layered_puzzles.json, RECOGNIZED
    if every layer is in catalog/puzzles.json (the classification comes from the layers),
    UNKNOWN otherwise"""
    if layered_puzzle_fingerprint in CONF.KNOWN_LAYERED_PUZZLES:
        return TYPES.PuzzleStatus.VERIFIED
    if all_layers_known(layered_puzzle_fingerprint):
        return TYPES.PuzzleStatus.RECOGNIZED
    return TYPES.PuzzleStatus.UNKNOWN


# --- Data of a coin, read from its puzzle -------------------------------------------
# One `if` per kind of coin, decided by the mod hashes of its layers (chia's own constants),
# never by the names, puzzle types or families of the catalog, which people can rename. When
# a coin needs its own data on the screens, add an `if`.

STANDARD_MOD_HASH = STANDARD_MOD.get_tree_hash()


def puzzle_data(puzzle: PyProgram) -> list:
    """(key, value) pairs read from a puzzle, for the screens. [] when no `if` knows it."""
    mod, curried_args = puzzle.uncurry()
    mod_hash = mod.get_tree_hash()
    args = list(curried_args.as_iter())

    if mod_hash == CAT_MOD_HASH:
        # (mod hash, tail hash = asset id, inner puzzle)
        return [('asset_id', args[1].as_atom().hex()),
                ('owner', puzzle_hash_to_address(args[2].get_tree_hash()))]

    if mod_hash == SINGLETON_MOD_HASH:
        # ((mod hash . (launcher id . launcher puzzle hash)), inner puzzle)
        inner_mod, inner_args = args[1].uncurry()
        if inner_mod.get_tree_hash() == NFT_STATE_LAYER_MOD_HASH:
            # NFT state layer: (mod hash, metadata, metadata updater hash, inner puzzle)
            p2_puzzle = list(inner_args.as_iter())[3]
            p2_mod, p2_args = p2_puzzle.uncurry()
            if p2_mod.get_tree_hash() == NFT_OWNERSHIP_LAYER_HASH:
                # ownership layer: (mod hash, owner DID, transfer program, inner puzzle)
                p2_puzzle = list(p2_args.as_iter())[3]
            return [('owner', puzzle_hash_to_address(p2_puzzle.get_tree_hash()))]

    if mod_hash == STANDARD_MOD_HASH:
        # the standard transaction: its puzzle hash is the owner's address
        return [('owner', puzzle_hash_to_address(puzzle.get_tree_hash()))]

    return []


def hint_owner(hint: bytes32, coin_puzzle_hash: bytes32, nodes: list = None) -> str:
    """Is the hint the hash of one of the coin's layers? The hint is a memo the sender
    writes, nothing checks it on chain. nodes: unroll_puzzle_to_nodes of the coin's own
    puzzle, None while the coin is not spent (its puzzle is not on chain yet)."""
    if hint is None:
        return 'no hint'
    if nodes is None:
        if hint == coin_puzzle_hash:
            return "yes: the coin's puzzle hash"
        return 'not checked (unspent)'
    for n, node in enumerate(nodes):
        if node['puzzle_hash'] == hint.hex():
            return f"yes: layer ({n}) {node['puzz_name']}"
    return 'no'


def coin_puzzle_data(coin: TYPES.CoinRecordRoto, hint: bytes32 = None) -> tuple:
    """(hint owner, puzzle data, source) of a coin. A spent coin is read from its own
    puzzle (source 'coin'); an unspent one from its parent's puzzle (source 'parent'),
    because its own puzzle is not on chain yet: the data are the parent's.
    It calls the node: run it in a thread."""
    if coin.spent_block_index > 0:
        source, coin_id, height = 'coin', coin.coin_name, coin.spent_block_index
    else:
        source, coin_id, height = 'parent', coin.coin.parent_coin_info, coin.confirmed_block_index
    out = RPC.call_rpc_node('get_puzzle_and_solution', coin_id=bytes(coin_id).hex(), height=height)
    if not out:
        return hint_owner(hint, coin.coin.puzzle_hash), [], source
    puzzle = PyProgram.fromhex(out['puzzle_reveal'])
    nodes = unroll_puzzle_to_nodes(puzzle) if source == 'coin' else None
    return hint_owner(hint, coin.coin.puzzle_hash, nodes), puzzle_data(puzzle), source




































def format_chia_lisp_level(lisp_code, max_depth_level):
    """
    Attempts to format Chia Lisp code stopping at a certain level

    Args:
        lisp_code: A string containing the Chialisp code.
        max_level: number after stopping splitting code

    Returns:
        A string containing the formatted Chialisp code.
    """

    depth_level = 0
    indent_string = "  "
    current_line_lev = 0
    current_line = ""
    len_current_line = 0
    max_line_len = 90
    formatted_lines = []

    # Add spaces around parentheses for easier splitting
    spaced_code = re.sub(r"(\(|\))", r" \1 ", lisp_code)
    tokens = spaced_code.split()

#    for i, token in enumerate(tokens):
    i = 0
    while i < len(tokens):
        token = tokens[i]

        if token == '(':
            if len(current_line) > 0:
                if depth_level < max_depth_level:
                    formatted_lines.append(indent_string * (current_line_lev) + current_line)
                    current_line = token
                    current_line_lev = depth_level
                    depth_level += 1
                else:
                    depth_level += 1
                    current_line = current_line + ' ' + token
            else:
                current_line = token
                current_line_lev = depth_level
                depth_level += 1

        elif token == ')':
            if depth_level <= max_depth_level:
                if len(current_line) > 0:
                    current_line = current_line + token
                    formatted_lines.append(indent_string * current_line_lev + current_line)
                    current_line = ""
                    depth_level -= 1
                else:
                    depth_level -= 1
                    formatted_lines.append(indent_string * depth_level + token)
            else:
                depth_level -= 1
                current_line = current_line + token
        elif tokens[i - 1] == ')' and tokens[i + 1] == '(' and len(current_line) == 0:
            formatted_lines.append(indent_string * depth_level + token)
        else:
            current_line = current_line + ' ' + token

        i += 1

    return "\n".join(formatted_lines)


if __name__ == "__main__":

    print("get transactions_generator")

    a = call_rpc_node("get_block_record_by_height", height=7942939)  # 7942939
    print(a)
    print(a['header_hash'])
    ha = a['header_hash']

    full_block = call_rpc_node("get_block", header_hash=ha)
   # print(full_block)
   # print(full_block['transactions_generator'])
    tg = full_block['transactions_generator']

    program: PyProgram = PyProgram.fromhex(tg)
    for n, i in enumerate(program.as_iter()):
        pass
        #print()
        #print(i)

    #print("list len", program.list_len())
    from clvm_tools.binutils import assemble, disassemble

    # clvm = disassemble(program)
    # print(clvm)

    # a = format_chia_lisp_level(clvm, 4)
    # print(a)

    # with open('block.lisp', 'w') as f:
    #     f.write(str(a))


    #args = list(args.as_iter())
    #if len(args) > 1:  # recurse if arguments exist

    import hashlib
    coin_id = bytes.fromhex("50dde439417b4811f6fe8c18212deac0bf3e900ebc3dca88c6e2634e838a2e56")
    message = bytes.fromhex("69421f4c6f23788226fffa27b005edfa69c3afa332cee5b05df2b0c7e33b835f")
    print(coin_id)
    print(message)
    # print(message.decode('utf-8'))

    hash = hashlib.sha256(coin_id + message)
    print(hash)
    hash_dig = hash.digest()
    print(hash_dig.hex())




    print(get_opcode_name(60))
    print(get_opcode_name(61))
    print(get_opcode_name(62))

    def print_out_puz(sp):
        print('puzzle reveal')
        puz_rev = sp['coin_spends'][0]['puzzle_reveal']
        program_hex = bytes.fromhex(puz_rev)
        program_rev = PyProgram.from_bytes(program_hex)
        print(disassemble(program_rev))

        print()
        print('solution')
        puz_rev = sp['coin_spends'][0]['solution']
        program_hex = bytes.fromhex(puz_rev)
        program = PyProgram.from_bytes(program_hex)
        print(disassemble(program))
        print()
        print()

        return program_rev

    with open('./tests/sb_XCH_tx.json', 'r') as f:
        sp = json.load(f)

    print('xch transaction')
    print()
    #print_out_puz(sp)

    print()
    print()
    print(sp)
    sp['coin_spends'][0]['puzzle_reveal'] = '0x' + sp['coin_spends'][0]['puzzle_reveal']
    sp['coin_spends'][0]['solution'] = '0x' + sp['coin_spends'][0]['solution']
    #sp['coin_spends'][0]['coin']['amount'] = hex(val)


    sp = SpendBundle.from_json_dict(sp)
    #sp = SpendBundle(sp)
    #debug_spend_bundle(sp)

    with open('./tests/sb_SBX-XCH_swap.json', 'r') as f:
        sp = json.load(f)

    print()
    print()
    print()
    print()
    print()
    print()
    print('swap transaction')
    sp = SpendBundle.from_json_dict(sp)
    #debug_spend_bundle(sp)



    with open('./tests/sb_SBX_tx.json', 'r') as f:
        sp = json.load(f)

    print('sbx transaction')
    print()
    program_sbx: PyProgram = print_out_puz(sp)
    print()
    print("SBX DUMP")
    print()
    #uncurry_dump(program_sbx)

    with open('./tests/sb_DBX_tx.json', 'r') as f:
        sp = json.load(f)

    print('dbx transaction')
    print()
    #print_out_puz(sp)


    with open('./tests/sb_SBX-XCH_swap.json', 'r') as f:
        sp = json.load(f)

    print('swap transaction')
    print()
    #print_out_puz(sp)


    with open('./tests/sb_NFT_tx.json', 'r') as f:
        sp = json.load(f)

    print('NFT transaction')
    print()
    program_nft: PyProgram = print_out_puz(sp)

    from chia.wallet.uncurried_puzzle import UncurriedPuzzle

    def LOTO_uncurry_dump(puzzle: PyProgram, prefix: str = "", layer: int = 0) -> None:
        mod, curried_args = puzzle.uncurry()

        if mod != puzzle:
            # If it's the very first call, print the header
            if layer == 0:
                print(f"{prefix}- <curried puzzle>")
                prefix += "  "

            print(f"{prefix}- Layer {layer + 1}:")
            print(f"{prefix}  - Mod hash: {mod.get_tree_hash().hex()}")
            print(f"{prefix}  - puz name; {compare_to_known_puzzles(mod.get_tree_hash().hex())} ehm")

            # Recursively dump arguments
            for arg in curried_args.as_iter():
                LOTO_uncurry_dump(arg, prefix=f"{prefix}  ", layer=0)  # Reset layer for args

            # Uncurry the mod further if possible
            mod2, curried_args2 = mod.uncurry()
            if mod2 != mod:
                LOTO_uncurry_dump(mod, prefix, layer + 1)
        else:
            # Base case: nothing left to uncurry
            print(f"{prefix}- {bu_disassemble(puzzle)}")


    def uncurry_to_dict(puzzle: PyProgram, layer: int = 0) -> dict:
        mod, curried_args = puzzle.uncurry()

        # Base structure for this node
        node = {
            "layer": layer + 1,
            "is_curried": mod != puzzle,
            "hash": mod.get_tree_hash().hex() if mod != puzzle else None,
            "puzz_name": compare_to_known_puzzles(mod.get_tree_hash().hex()) if mod != puzzle else None,
            "disassembly": bu_disassemble(puzzle) if mod == puzzle else None,
            "args": []
        }

        if mod != puzzle:
            # Recursively capture arguments
            for arg in curried_args.as_iter():
                node["args"].append(uncurry_to_dict(arg, layer=0))

            # Check if the mod itself can be uncurried further
            mod2, curried_args2 = mod.uncurry()
            if mod2 != mod:
                # We nest the next "layer" of the mod
                node["inner_mod"] = uncurry_to_dict(mod, layer + 1)

        return node

    def dict_to_array_puzz(dic, puzz_arr = []):
        is_curried = dic['is_curried']
        name = compare_to_known_puzzles(dic['hash'])

        if is_curried:

            print("the hame ", name)



    print()
    print("NFT DUMP")
    print()
    LOTO_uncurry_dump(program_nft, 'DOMO')
    print("mmmmmmmmmmmmmmmmmmmmmmm")
    n = uncurry_to_dict(program_nft)
    print()
    UTILS.print_json(n)
    print()
    print(dict_to_array_puzz(n))

    print("barbizza")

    appay = []
    uncurry_to_array(program_nft, 0, appay)
    print(f"len appay : {len(appay)} and type {type(appay)}")
    print(f"len appay[9] : {len(appay[0])} and tryep: {type(appay[0])}")
    print()
    print()

    for i in appay:
        print()
        UTILS.print_json(i)

    print("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    print("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    print("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    print("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    print("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")

    import src.RPCtiller as RPC
    coin_name = 'f3ceda7ee09ccee1f34ea423571de06be9d155c50bd8c66ba35fc7ca24f7259a'
    spent_height = 7302401
    out = RPC.call_rpc_node('get_puzzle_and_solution', coin_id=coin_name, height=spent_height)
    print(out)
    program_ach = PyProgram.fromhex(out['puzzle_reveal'])

    #uncurry_dump(program_ach)
    LOTO_uncurry_dump(program_ach)

    exit()



    def ROTO_recursive_uncurry_dump(puzzle: PyProgram, layer: int, prefix: str, uncurried_already: UncurriedPuzzle) -> None:
        if uncurried_already is not None:
            mod = uncurried_already.mod
            curried_args = uncurried_already.args
        else:
            mod, curried_args = puzzle.uncurry()

        if mod != puzzle:
            print(f"{prefix}- Layer {layer}:")
            print(f"{prefix}  - Mod hash: {mod.get_tree_hash().hex()}")
            for arg in curried_args.as_iter():
                uncurry_dump(arg, prefix=f"{prefix}  ")
            mod2, curried_args2 = mod.uncurry()
            if mod2 != mod:
                ROTO_recursive_uncurry_dump(mod, layer + 1, prefix, UncurriedPuzzle(mod2, curried_args2))
        else:
            print(f"{prefix}- {bu_disassemble(puzzle)}")


    def uncurry_dump(puzzle: PyProgram, prefix: str = "") -> None:
        mod, curried_args = puzzle.uncurry()
        if mod != puzzle:
            print(f"{prefix}- <curried puzzle>")
            prefix = f"{prefix}  "

        ROTO_recursive_uncurry_dump(puzzle, 1, prefix, UncurriedPuzzle(mod, curried_args))


    exit()


    from chia.util.bech32m import encode_puzzle_hash, decode_puzzle_hash
    import pathlib


    from clvm_tools.clvmc import compile_clvm as compile_clvm_py
    compile_clvm = compile_clvm_py
#from clvm_tools_rs import compile_clvm

    def load_clvm_from_file(clvm_path, search_paths=[]):

        full_path = pathlib.Path(clvm_path)
        parent_path = full_path.parent
        filename = full_path.name
        hex_filename = f"{filename}.hex"
        clvm_path = parent_path / hex_filename  # is the clvm the hex version of the clsp?
        print(parent_path)
        print(full_path)
        print(filename)
        print(hex_filename)

        # compile the clvm
        out = compile_clvm(
                full_path,
                clvm_path,
                search_paths=[parent_path, pathlib.Path.cwd().joinpath("include"), *search_paths],
            )

        # load the clvm
        with open(clvm_path, 'r', encoding='utf-8') as file:
            clvm_hex = file.read()
            clvm_blob = bytes.fromhex(clvm_hex)

        return SerializedProgram.from_bytes(clvm_blob)

    def calc_puz(clvm_path):
        clvmP = load_clvm_from_file(clvm_path)
        print("clvm loaded")
        puzzle_raw = clvmP.to_program()
        puzzle_hash = clvmP.get_tree_hash()
        puzzle_add = encode_puzzle_hash(puzzle_hash, prefix='txch')
        print("puzzle raw")
        print(puzzle_raw)
        print()
        print("puzzle_clvm")
        print(disassemble(puzzle_raw))
        print("puzzle_hash")
        print(puzzle_hash)
        print("address")
        print(puzzle_add)
        return puzzle_raw, puzzle_hash, puzzle_add


    print("eval CAT2 puzzle")
    calc_puz("./tests/puzzles/cat_v2.clvm")

    print("eval tail puzzle")
    calc_puz("./tests/puzzles/delegated_tail.clvm")

    print("end")

    print("uncurry")
    print("uncurry CAT")

    print(type(program_sbx))
    print(program_sbx)
    print()
    print('level 1')
    args: PyProgram = None

    uncurry_sbx_l1, args = program_sbx.uncurry()
    print(uncurry_sbx_l1)
    print(disassemble(uncurry_sbx_l1))
    last_el = None
    for n, i in enumerate(args.as_iter()):
        print(n)
        print(i)
        print(disassemble(i))
        last_el = i

    print()
    print('level 2')
    uncurry_sbx_l2, args = last_el.uncurry()
    print(uncurry_sbx_l2)
    print(disassemble(uncurry_sbx_l2))
    for n, i in enumerate(args.as_iter()):
        print(n)
        print(i)
        print(disassemble(i))

    print()
    print('uncurry NFT')
    print('uncurry NFT')
    print('uncurry NFT')
    print('uncurry NFT')
    print()
    print(program_nft)

    print(disassemble(program_nft))
    print()
    uncurry_nft, args = program_nft.uncurry()
    print("lev1 uncurried")
    print(uncurry_nft)
    print(f" first hash; {uncurry_nft.get_tree_hash()}")
    print(disassemble(uncurry_nft))
    last_el = None
    for n, i in enumerate(args.as_iter()):
        print(n)
        print(i)
        print(disassemble(i))
        last_el = i

    uncurry_nft, args = last_el.uncurry()
    print()
    print("lev2 uncurried")
    print(uncurry_nft)
    print(f" second hash; {uncurry_nft.get_tree_hash()}")
    print(disassemble(uncurry_nft))
    for n, i in enumerate(args.as_iter()):
        print(n)
        print(i)
        print(disassemble(i))

    def uncurry_coin(prog):
        uncurry_nft, args = prog.uncurry()
        last_el = None
        for n, i in enumerate(args.as_iter()):
            print(f"{n} - {i}")
            print(disassemble(i))
            print()
            last_el = i
        return last_el




    hashes = unroll_coin_puzzle(program_nft)
    print(hashes)


    for h in hashes:
        print(compare_to_known_puzzles(h))







    from chia._tests.util.get_name_puzzle_conditions import get_name_puzzle_conditions
    from chia.consensus.cost_calculator import NPCResult
    from chia.consensus.default_constants import DEFAULT_CONSTANTS
    from chia.types.blockchain_format.program import INFINITE_COST

    puz_rev = sp['coin_spends'][0]['solution']
    program_hex = bytes.fromhex(puz_rev[2:])
    program = PyProgram.from_bytes(program_hex)

    npc_result: NPCResult = get_name_puzzle_conditions(
        program,
        INFINITE_COST,
        height=DEFAULT_CONSTANTS.SOFT_FORK6_HEIGHT,  # so that all opcodes are available
        mempool_mode=True,
        constants=DEFAULT_CONSTANTS,
    )

    print("npc")
    print(npc_result)


