import os
import pathlib
import json

from chia.types.blockchain_format.program import Program
from chia.wallet.puzzles.load_clvm import load_clvm, compile_clvm
from clvm_tools.binutils import disassemble as bu_disassemble


# repo cni: https://github.com/Chia-Network/chia_puzzles
# repo tibet: https://github.com/Yakuhito/tibet/tree/master/clvm
# repo warp: https://github.com/warpdotgreen/cli/tree/master/puzzles
# repo circuit: https://github.com/circuitdao/puzzles

local_path = os.path.dirname(__file__) + '/chia_puzzles-main/puzzles/'
local_path = 'Repos/chia_puzzles/puzzles/'
files = os.listdir(local_path)
print(local_path)


def load_clvm_from_file(clvm_path, search_paths=[]):

    full_path = pathlib.Path(clvm_path)
    parent_path = full_path.parent
    filename = full_path.name
    hex_filename = f"{filename}.hex"
    clvm_path = parent_path / hex_filename
    print("perent: ",parent_path)
    print("full path; ", full_path)
    print('filename: ', filename)
    print('hex: ', hex_filename)

    # compile the clvm
    # def compile_clvm(full_path: pathlib.Path, output: pathlib.Path, search_paths: list[pathlib.Path] = []):
    out = compile_clvm(
            full_path,
            clvm_path,
            search_paths=[parent_path, *search_paths],
            #search_paths=[parent_path, pathlib.Path.cwd().joinpath("include"), *search_paths],
        )

    # load the clvm hex
    with open(clvm_path, 'r', encoding='utf-8') as file:
        clvm_hex = file.read()
        clvm_blob = bytes.fromhex(clvm_hex)

    return Program.from_bytes(clvm_blob)


def parse_puzzles(path, store, prefix='-', puzzles_root_folder=None):
    if puzzles_root_folder is None:
        puzzles_root_folder = path
    # use only Pathlib
    files = os.listdir(path)
    for file_name in files:
        sub_path = os.path.join(path, file_name)
        if os.path.isdir(sub_path):
            prefix_puzzle = f"{prefix}-{file_name}"
            parse_puzzles(sub_path, store, prefix_puzzle, puzzles_root_folder)
        else:
            if file_name.endswith('.clsp'):
                new_puzzle = {}
                sub_path = os.path.join(path, file_name)
                short_name = file_name[:-5]
                name = f"{prefix}-{short_name}"
                print(sub_path)
                prog = load_clvm_from_file(sub_path, [pathlib.Path(puzzles_root_folder)])

                new_puzzle['file_name'] = file_name
                new_puzzle['name'] = name
                new_puzzle['puzzle_hash'] = str(prog.get_tree_hash())
                with open(sub_path, 'r') as f:
                    new_puzzle['clvm'] = f.read()
                new_puzzle['bytecode'] = prog.to_json_dict()
                new_puzzle['bytecode_disassembled'] = bu_disassemble(prog)
                store[new_puzzle['puzzle_hash']] = new_puzzle
                print(json.dumps(new_puzzle, indent=4))

puzzles = {}

parse_puzzles(local_path, puzzles)


with open('puzzles.json', 'w') as f:
    json.dump(puzzles, f, indent=4)

