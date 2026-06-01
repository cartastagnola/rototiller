import json
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



from src.CONFtiller import UNKNOWN_PUZZLE, KNOWN_PUZZLES, KNOWN_LAYERED_PUZZLES, logging, debug_logger
from src.RPCtiller import call_rpc_node, call_rpc_daemon
import src.UTILStiller as UTILS

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


#def unroll_coin_puzzle_to_puzzle_hashes(program: PyProgram, puzzle_hashes=None, lev=0):
#    """Uncurry recursively the puzzle and gives the puzzles used"""
#
#    if puzzle_hashes is None:
#        puzzle_hashes = []
#        print()
#        print()
#        print("LEVELLO ZERO")
#        lev += 1
#    else:
#        print()
#        print(f"LEVELLO {lev}")
#        lev += 1
#
#    uncurried_program, args = program.uncurry()
#    puzzle_hash = uncurried_program.get_tree_hash()
#    puzzle_hashes.append(puzzle_hash)
#    print(f"tree hash: {puzzle_hash}")
#    print(f"puzz: {disassemble(uncurried_program)}")
#    #print(f"args: {disassemble(args)}")
#
#    print("args")
#    args = list(args.as_iter())
#    for n, i in enumerate(args):
#        print(f"{n}n - {disassemble(i)}")
#
#    #print(f"last:{args[-1]}")
#    if len(args) > 1:  # recurse if arguments exist
#        unroll_coin_puzzle_to_puzzle_hashes(args[-1], puzzle_hashes, lev)
#
#    return puzzle_hashes
#

#### DELETE
#def unroll_coin_puzzle_to_puzzles_and_args(program: PyProgram, puzzles=None, args_list=None):
#    """Uncurry recursively the puzzle and gives the puzzles used"""
#
#    if puzzles is None:
#        puzzles = []
#        args_list = []
#
#    uncurried_program, args = program.uncurry()
#    puzzles.append(uncurried_program)
#    args_list.append(args)
#
#    args = list(args.as_iter())
#    if len(args) > 1:  # recurse if arguments exist
#        unroll_coin_puzzle_to_puzzles_and_args(args[-1], puzzles, args_list)
#
#    return puzzles, args_list


def compare_to_known_puzzles(puzzle_hash):
    puzzle = KNOWN_PUZZLES.get(str(puzzle_hash), None)
    if puzzle is None:
        return UNKNOWN_PUZZLE
    else:
        return puzzle['name']


def compare_unrolled_puzzle_to_known_layered_puzzles(sub_puzzle_hashes: list):
    """Compare a list of sub puzzle with known combination of puzzles"""
    puzzle_key = '|'.join(sub_puzzle_hashes)
    puzzle = KNOWN_LAYERED_PUZZLES.get(str(puzzle_key), None)
    for i in KNOWN_LAYERED_PUZZLES.keys():
        print(i)
    print(f"puzzle key: {puzzle_key}")
    if puzzle is None:
        return "unknown puzzle"
    else:
        return puzzle['name']


def print_tree_path(path: list, level):
    text = f'lev: {level} | '
    for i in path:
        if len(i) == 0:
            text += "()"
        else:
            text += f"({i[0]}_{i[1]}), "
    return text


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

    if mod != puzzle and puzzle_name == UNKNOWN_PUZZLE:
        node['is_curried'] = True
        node['hash'] = mod_hash
        node['puzz_name'] = mod_name
        node['disassembly'] = rs_disassemble(bytes(mod))  # should we put the disassembly of the mod?

        # Recursively capture arguments and store in the node
        count = 0
        for arg in curried_args.as_iter():
            arg_hash = arg.get_tree_hash().hex()
            arg_name = compare_to_known_puzzles(arg_hash)
            if arg_name != UNKNOWN_PUZZLE:
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
        if mod2 != mod and node['puzz_name'] == UNKNOWN_PUZZLE:
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
                if arg_name != UNKNOWN_PUZZLE:
                    new_path = current_path + [('R',n)] + [()]
                else:
                    new_path = current_path + [('R',n)] + [('L', 0)]
                unroll_puzzle_to_nodes(arg, level, array=array, path=new_path)

    elif puzzle_name != 'unknow puzzle':
        node['is_curried'] = False
        node['hash'] = puzzle_hash
        node['puzz_name'] = puzzle_name
        node['disassembly'] = rs_disassemble(bytes(puzzle))

        array.append(node)

    return array


def unroll_puzzle_to_names(puzzle: PyProgram, level: int = 0, array: list = None):
    """Recursive function to uncurry a puzzle to list all the names of the puzzles used
       output: names, hashes"""
    if array is None:
        array = [[],[]]


    puzzle_hash = puzzle.get_tree_hash().hex()
    puzzle_name = compare_to_known_puzzles(puzzle_hash)

    mod, curried_args = puzzle.uncurry()
    mod_hash = mod.get_tree_hash().hex()
    mod_name = compare_to_known_puzzles(mod_hash)

    if mod != puzzle and puzzle_name == UNKNOWN_PUZZLE:

        array[0].append(mod_name)
        array[1].append(mod_hash)

        # Check if the mod itself can be uncurried further
        mod2, curried_args2 = mod.uncurry()
        if mod2 != mod and mod_name == UNKNOWN_PUZZLE:
            # here we should check if there are multiple
            unroll_puzzle_to_names(mod, level, array=array)

        # scan again the args to launch the recursion
        for n, arg in enumerate(curried_args.as_iter()):
            sub_mod, sub_curried_args = arg.uncurry()
            if sub_mod != arg:
                # remove last level and fo to the right
                unroll_puzzle_to_names(arg, level, array=array)
    elif puzzle_name != UNKNOWN_PUZZLE:
        # case where a puzzle is use as argument without any curried args
        array[0].append(puzzle_name)
        array[1].append(puzzle_hash)

    return array[0], array[1]


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


