from __future__ import annotations
import json
import os
import re  # clvm formatter

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


def compare_to_known_puzzles(puzzle_hash):
    """Look up a puzzle hash in known puzzles, then in saved unknown puzzles. """
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


def save_layered_puzzle(puzzle_key: str, sub_hashes: list, sub_names: list):
    """Save a layered puzzle combination to the appropriate JSON file.

    If any sub-puzzle is unknown, the combination goes to unknown_layered_puzzles.json.
    If all sub-puzzles are known, it goes to layered_puzzles.json.

    Args:
        puzzle_key: The pipe-separated hash string used as key.
        sub_hashes: List of sub-puzzle hashes.
        sub_names: List of resolved sub-puzzle names.

    Returns:
        The generated name for the layered combination.
    """
    has_unknown = any(hash not in CONF.KNOWN_PUZZLES for hash in sub_hashes)

    if has_unknown:
        target_dict = CONF.UNKNOWN_LAYERED_PUZZLES
        target_path = CONF.UNKNOWN_LAYERED_PUZZLES_PATH
        lock = CONF.UNKNOWN_LAYERED_PUZZLES_LOCK
        prefix = "unknown_layered"
    else:
        target_dict = CONF.KNOWN_LAYERED_PUZZLES
        target_path = CONF.KNOWN_LAYERED_PUZZLES_PATH
        lock = CONF.LAYERED_PUZZLES_LOCK
        prefix = "auto_layered"

    def add_entry(catalog: dict):
        """Add the entry to the catalog, return (puzzle_type, name, added)"""
        if puzzle_key in catalog:
            entry = catalog[puzzle_key]
            return entry['puzzle_type'], entry['name'], False

        #find max unkonw puzzle
        max_num = 0
        for entry in catalog.values():
            name = entry.get('name', '')
            if name.startswith(prefix + '_'):
                try:
                    num = int(name.split('_')[-1])
                    if num > max_num:
                        max_num = num
                except ValueError:
                    pass

        new_name = f"{prefix}_{max_num + 1:02d}"
        new_type = f"type_{new_name}"

        catalog[puzzle_key] = {
            "puzzle_type": new_type,
            "name": new_name,
            "sub_puzzle_hashes": sub_hashes,
            "sub_puzzle_names": sub_names
        }
        return new_type, new_name, True

    with lock:
        if puzzle_key in target_dict:
            entry = target_dict[puzzle_key]
            return entry['puzzle_type'], entry['name']

        if has_unknown:
            # local file, only roto writes it
            new_type, new_name, added = add_entry(target_dict)
            with open(target_path, 'w') as f:
                json.dump(target_dict, f, indent=4)
            return new_type, new_name

        # layered_puzzles.json can be edited by hand: add the entry to the file on disk
        result = []

        def change(data):
            result.extend(add_entry(data))
            return result[2]

        try:
            update_catalog_file(target_path, target_dict, change)
        except ValueError as e:
            logging(debug_logger, "DEBUG", f"CATALOG {target_path} is not valid json, {puzzle_key} not saved: {e}")
            return add_entry(dict(target_dict))[:2]
        return result[0], result[1]


def compare_unrolled_puzzle_to_known_layered_puzzles(sub_puzzle_hashes: list):
    """Compare a list of sub-puzzle hashes against known layered puzzles.

    If the combination is not found, save it to the appropriate catalog
    (known or unknown layered puzzles) and return the generated name.

    Args:
        sub_puzzle_hashes: List of sub-puzzle hash strings.

    Returns:
        The puzzle name if found, or a generated name if newly saved.
    """
    puzzle_key = '|'.join(sub_puzzle_hashes)

    puzzle = CONF.KNOWN_LAYERED_PUZZLES.get(puzzle_key, None)
    if puzzle is not None:
        return puzzle['puzzle_type'], puzzle['name']

    puzzle = CONF.UNKNOWN_LAYERED_PUZZLES.get(puzzle_key, None)
    if puzzle is not None:
        return puzzle['puzzle_type'], puzzle['name']

    sub_names = [compare_to_known_puzzles(h) for h in sub_puzzle_hashes]
    return save_layered_puzzle(puzzle_key, sub_puzzle_hashes, sub_names)


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

        with open(CONF.UNKNOWN_PUZZLES_PATH, 'w') as f:
            json.dump(CONF.UNKNOWN_PUZZLES, f, indent=4)


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
        "args": []
    }

    if mod != puzzle and puzzle_name == CONF.UNKNOWN_PUZZLE:
        node['is_curried'] = True
        node['hash'] = mod_hash
        node['puzz_name'] = mod_name
        node['disassembly'] = rs_disassemble(bytes(mod))  # should we put the disassembly of the mod?

        # Save unknown template with an example curried instance
        if mod_name == CONF.UNKNOWN_PUZZLE:
            save_unknown_puzzle(
                mod_hash,
                mod,
                example=rs_disassemble(bytes(puzzle))
            )

        # Recursively capture arguments and store in the node
        count = 0
        for arg in curried_args.as_iter():
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
    # the walk depends only on the shared catalog (puzzles.json), not on the local
    # unknown_puzzles.json, or the same puzzle would get a different key on every machine
    puzzle_is_known = puzzle_hash in CONF.KNOWN_PUZZLES

    mod, curried_args = puzzle.uncurry()
    mod_hash = mod.get_tree_hash().hex()
    mod_name = compare_to_known_puzzles(mod_hash)
    mod_is_known = mod_hash in CONF.KNOWN_PUZZLES

    if mod != puzzle and not puzzle_is_known:

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
            layered_puzzle_type_str, layered_puzzle_name = compare_unrolled_puzzle_to_known_layered_puzzles(puz_hashes)
            logging(debug_logger, "DEBUG", f"LOAD puz_hashes: {puz_hashes}")

            try:
                layered_puzzle_type = TYPES.CoinType(layered_puzzle_type_str)
            except (ValueError, KeyError):
                layered_puzzle_type = TYPES.CoinType.UNKNOWN

            puz = TYPES.PuzzleRecord(out, puzzle_disassembled, unroll_puzzles, layered_puzzle_type, layered_puzzle_name)

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
        CoinType enum member, or CoinType.UNKNOWN if type cannot be determined.
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
            try:
                return TYPES.CoinType(layered_puzzle_type_str)
            except (ValueError, KeyError):
                return TYPES.CoinType.UNKNOWN

        except Exception as e:
            logging(debug_logger, "DEBUG", f"get_type_unspent_coin failed: {e}")
            return TYPES.CoinType.UNKNOWN


# --- Type checker registry ----------------------------------------------------
_TYPE_CHECKERS = []


def _register_type_checker(func):
    """Decorator to register a coin-type checker."""
    _TYPE_CHECKERS.append(func)
    return func


def _puzzle_name_from_hash(puzzle_hash_hex: str) -> str:
    """Look up a puzzle name from its hash using CONF.KNOWN_PUZZLES."""
    entry = CONF.KNOWN_PUZZLES.get(puzzle_hash_hex)
    if entry is not None:
        return entry.get('name', CONF.UNKNOWN_PUZZLE)
    return CONF.UNKNOWN_PUZZLE


# ------------------------------------------------------------------------------
# CAT checker
# ------------------------------------------------------------------------------
@_register_type_checker
def _check_cat_type(coin, puzzle_program, hint):
    """Identify a CAT coin and verify ownership via *hint*.

    *puzzle_program* is either the coin's own puzzle (spent) or the parent
    puzzle (unspent).  In both cases we can extract the tail and reconstruct
    ``CAT_MOD.curry(CAT_MOD_HASH, tail, hint)``.  If the reconstructed tree
    hash equals ``coin.coin.puzzle_hash`` the coin is verified as ours."""
    mod, curried_args = puzzle_program.uncurry()
    mod_hash_hex = mod.get_tree_hash().hex()
    mod_name = _puzzle_name_from_hash(mod_hash_hex)

    if not mod_name.endswith('cat_v2'):
        return None

    # curried_args = (cat_mod_hash, tail_program, inner_puzzle)
    args = list(curried_args.as_iter())
    if len(args) < 3:
        return None
    tail_program = args[1]
    inner_puzzle = args[2]

    # For a spent coin, puzzle_program IS the coin's own puzzle reveal.
    # Verify ownership by checking if the inner puzzle hash matches the hint.
    if hint is not None and inner_puzzle.get_tree_hash() == hint:
        return {
            'type': 'CAT',
            'verified': True,
            'detail': {
                'asset_id': tail_program.get_tree_hash().hex(),
                'inner_puzzle_hash': hint.hex()
            }
        }

    # Fallback: try reconstructing with hint as inner puzzle (for cases where
    # we got the full inner puzzle program rather than just the hash)
    try:
        tail_program = tail_program.get_tree_hash()
        print(f"[CAT DEBUG] mod type: {type(mod)}")
        print(f"[CAT DEBUG] tail_program type: {type(tail_program)}")
        print(f"[CAT DEBUG] tail_program value: {tail_program}")
        print(f"[CAT DEBUG] hint type: {type(hint)}")
        print(f"[CAT DEBUG] hint value: {hint}")

        reconstructed = mod.curry(mod, tail_program, hint)
        if reconstructed is None:
            return None

        print('reconstructed')
        print(reconstructed.get_tree_hash())
        print('puzzle hash')
        print(coin.coin.puzzle_hash)
        if reconstructed.get_tree_hash() != coin.coin.puzzle_hash:
            return None  # hint does not match this CAT

        return {
            'type': 'CAT',
            'verified': True,
            'detail': {
                'asset_id': tail_program.get_tree_hash().hex(),
                'inner_puzzle_hash': hint.hex() if hint else None
            }
        }
    except Exception:
        return None


# ------------------------------------------------------------------------------
# NFT checker
# ------------------------------------------------------------------------------
@_register_type_checker
def _check_nft_type(coin, puzzle_program, hint):
    """Check if *puzzle_program* is a singleton NFT and the hint owns it."""
    # --- step 1: outer layer must be singleton top-layer ---
    mod, curried_args = puzzle_program.uncurry()
    mod_hash = mod.get_tree_hash().hex()
    mod_name = _puzzle_name_from_hash(mod_hash)
    if not mod_name.endswith('singleton_top_layer_v1_1'):
        return None

    # --- step 2: inner layer must be NFT state layer ---
    singleton_args = list(curried_args.as_iter())
    if len(singleton_args) < 2:
        return None
    inner_puzzle = singleton_args[1]
    inner_mod, inner_args = inner_puzzle.uncurry()
    inner_mod_hash = inner_mod.get_tree_hash().hex()
    inner_mod_name = _puzzle_name_from_hash(inner_mod_hash)
    if not inner_mod_name.endswith('nft_state_layer'):
        return None

    # --- step 3: amount must be odd (1-mojo NFT) ---
    if coin.coin.amount % 2 == 0:
        return None

    # --- step 4: extract the p2 puzzle hash from the innermost layer ---
    # inner_args of NFT state layer tends to be:
    #   (nft_mod_hash, metadata, updater, innermost_puzzle)
    # innermost_puzzle might itself be wrapped by NFT_OWNERSHIP_LAYER for DID-linked NFTs.
    state_args = list(inner_args.as_iter())
    if len(state_args) < 4:
        return None
    innermost_puzzle = state_args[3]
    im_mod, im_args = innermost_puzzle.uncurry()
    im_mod_hash = im_mod.get_tree_hash().hex()
    im_mod_name = _puzzle_name_from_hash(im_mod_hash)
    if im_mod_name.endswith('nft_ownership_layer'):
        # DID-linked NFT – unwrap once more
        ownership_args = list(im_args.as_iter())
        if len(ownership_args) < 1:
            return None
        p2_puzzle = ownership_args[0]
    else:
        p2_puzzle = innermost_puzzle

    p2_puzzle_hash = p2_puzzle.get_tree_hash()

    # --- step 5: verify the hint matches the p2 puzzle hash ---
    verified = (hint is not None and p2_puzzle_hash == hint)

    return {
        'type': 'NFT',
        'verified': verified,
        'detail': {'p2_puzzle_hash': p2_puzzle_hash.hex()}
    }


# ------------------------------------------------------------------------------
# Standard transaction (XCH / P2) checker
# ------------------------------------------------------------------------------
@_register_type_checker
def _check_standard_type(coin, puzzle_program, hint):
    """Identify a standard (XCH) P2 transaction and verify via *hint*."""
    mod, curried_args = puzzle_program.uncurry()
    mod_hash = mod.get_tree_hash().hex()
    mod_name = _puzzle_name_from_hash(mod_hash)
    if not mod_name.endswith('p2_delegated_puzzle_or_hidden_puzzle'):
        return None

    # For standard P2 the hint should equal the coin puzzle hash.
    verified = (hint is not None and coin.coin.puzzle_hash == hint)

    return {
        'type': 'XCH',
        'verified': verified,
        'detail': {
            'puzzle_hash': coin.coin.puzzle_hash.hex(),
            'checker': 'standard_p2'
        }
    }




































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


