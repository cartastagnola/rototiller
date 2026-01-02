import json
import re  # clvm formatter

#from clvm_tools.binutils import disassemble as bu_disassemble
#from chia.wallet.util.debug_spend_bundle import disassemble
from clvm_tools.binutils import disassemble


from chia.types.blockchain_format.serialized_program import SerializedProgram
from chia.types.blockchain_format.program import Program
from chia.types.condition_opcodes import ConditionOpcode
from chia.wallet.util.debug_spend_bundle import debug_spend_bundle

try:
    from chia.types.spend_bundle import SpendBundle
except ImportError:
    try:
        from chia_rs import SpendBundle
    except ImportError:
        print('probably a full_node verison not supporter')



from src.CONFtiller import KNOWN_PUZZLES
from src.RPCtiller import call_rpc_node, call_rpc_daemon

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
    print('puzzle reveal')
    reveals = []
    solutions = []
    for coin in spend_bundle['coin_spends']:
        puz_rev = bytes.fromhex(coin['puzzle_reveal'])
        puz_rev_prog = Program.from_bytes(puz_rev)
        reveals.append(puz_rev_prog)

        puz_sol = bytes.fromhex(coin['solution'])
        puz_sol_prog = Program.from_bytes(puz_sol)
        solutions.append(puz_sol_prog)

    return reveals, solutions

def unroll_coin_puzzle(program: Program, puzzles=None):
    """Uncurry recursively the puzzle and gives the puzzles used"""

    if puzzles is None:
        puzzles = []

    uncurried_program, args = program.uncurry()
    puzzle_hash = uncurried_program.get_tree_hash()
    puzzles.append(puzzle_hash)

    args = list(args.as_iter())
    if len(args) > 1:  # recurse if arguments exist
        unroll_coin_puzzle(args[-1], puzzles)

    return puzzles


def compare_to_known_puzzle(puzzle_hash):
    puzzle = KNOWN_PUZZLES.get(str(puzzle_hash), None)
    print('compare to known puzzle')
    print(puzzle)
    if puzzle is None:
        return "unknown puzzle"
    else:
        return puzzle['name']



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
    print(full_block)
    print(full_block['transactions_generator'])
    tg = full_block['transactions_generator']

    program: Program = Program.fromhex(tg)
    for n, i in enumerate(program.as_iter()):
        print()
        print(i)

    print("list len", program.list_len())
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
    exit()

    def print_out_puz(sp):
        print('puzzle reveal')
        puz_rev = sp['coin_spends'][0]['puzzle_reveal']
        program_hex = bytes.fromhex(puz_rev)
        program_rev = Program.from_bytes(program_hex)
        print(disassemble(program_rev))

        print()
        print('solution')
        puz_rev = sp['coin_spends'][0]['solution']
        program_hex = bytes.fromhex(puz_rev)
        program = Program.from_bytes(program_hex)
        print(disassemble(program))
        print()
        print()

        return program_rev

    with open('./tests/sb_XCH_tx.json', 'r') as f:
        sp = json.load(f)

    print('xch transaction')
    print()
    print_out_puz(sp)

    print()
    print()
    print(sp)
    sp['coin_spends'][0]['puzzle_reveal'] = '0x' + sp['coin_spends'][0]['puzzle_reveal']
    sp['coin_spends'][0]['solution'] = '0x' + sp['coin_spends'][0]['solution']
    #sp['coin_spends'][0]['coin']['amount'] = hex(val)


    sp = SpendBundle.from_json_dict(sp)
    #sp = SpendBundle(sp)
    debug_spend_bundle(sp)

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
    debug_spend_bundle(sp)
    exit()



    with open('./tests/sb_SBX_tx.json', 'r') as f:
        sp = json.load(f)

    print('sbx transaction')
    print()
    program_sbx: Program = print_out_puz(sp)

    with open('./tests/sb_DBX_tx.json', 'r') as f:
        sp = json.load(f)

    print('dbx transaction')
    print()
    print_out_puz(sp)


    with open('./tests/sb_SBX-XCH_swap.json', 'r') as f:
        sp = json.load(f)

    print('swap transaction')
    print()
    print_out_puz(sp)


    with open('./tests/sb_NFT_tx.json', 'r') as f:
        sp = json.load(f)

    print('NFT transaction')
    print()
    program_nft: Program = print_out_puz(sp)




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
    args: Program = None

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
        print(compare_to_known_puzzle(h))



    exit()




    from chia._tests.util.get_name_puzzle_conditions import get_name_puzzle_conditions
    from chia.consensus.cost_calculator import NPCResult
    from chia.consensus.default_constants import DEFAULT_CONSTANTS
    from chia.types.blockchain_format.program import INFINITE_COST

    puz_rev = sp['coin_spends'][0]['solution']
    program_hex = bytes.fromhex(puz_rev[2:])
    program = Program.from_bytes(program_hex)

    npc_result: NPCResult = get_name_puzzle_conditions(
        program,
        INFINITE_COST,
        height=DEFAULT_CONSTANTS.SOFT_FORK6_HEIGHT,  # so that all opcodes are available
        mempool_mode=True,
        constants=DEFAULT_CONSTANTS,
    )

    print("npc")
    print(npc_result)


