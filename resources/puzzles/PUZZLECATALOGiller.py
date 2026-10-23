import os
import pathlib
import json
import subprocess
import sys
import tempfile
from datetime import date

from chia.types.blockchain_format.program import Program
from chia.wallet.puzzles.load_clvm import compile_clvm
from clvm_tools.binutils import disassemble as bu_disassemble


# Remote puzzle sources to fetch.
# Each entry maps a repo name to its Git URL and the sub-directory that
# contains the .clsp files (use "" for repo root).
# Optional fields:
#   "language": "chialisp" (default, the .clsp files are compiled here) or "rue" (the
#               compiled .rue.hex committed in the repo is read, see parse_rue_puzzles)
#   "repo":     folder of the clone in CACHE_DIR (default: "name"), two sources of the
#               same repo share one clone
#   "include_dirs": folders of the repo to search for included files, added to the ones
#               found by find_include_dirs (it finds only folders with .clib files).
#               {"repo": <name>, "path": <folder>} is a folder of another source's clone
#   "sparse":   folders to check out, for big repos (git sparse checkout, cone mode).
#               The clone has only these folders, so find_include_dirs looks only there
#   "markdown_puzzles": puzzles written inside a markdown file (e.g. a CHIP) instead of a
#               .clsp file, see parse_markdown_puzzles. A list of
#               {"file": <.md path in the repo>, "section": <heading text>, "name": <puzzle name>},
#               the puzzle is the first code block under that heading. A source with
#               "markdown_puzzles" compiles only them, "subdir" is not scanned
#   "compiled_dir": (rue only) folder of the repo with the compiled <file>.rue.hex, when it
#               is not next to the .rue file (dist_dir in Rue.toml). The folder is flat: the
#               hex of puzzles/upstream/slot.rue is <compiled_dir>/slot.rue.hex
#   "exclude":  files or folders of "subdir" that are not scanned (e.g. test puzzles),
#               paths relative to "subdir"
SOURCES = [
    {
        "name": "cni",
        "url": "https://github.com/Chia-Network/chia_puzzles.git",
        "subdir": "puzzles",
    },
    {
        "name": "tibet",
        "url": "https://github.com/Yakuhito/tibet.git",
        "subdir": "clsp",
    },
    {
        "name": "warp",
        "url": "https://github.com/warpdotgreen/cli.git",
        "subdir": "puzzles",
    },
    {
        "name": "circuit",
        "url": "https://github.com/circuitdao/puzzles.git",
        "subdir": "",          # repo root — files are at top level
    },
    {
        # Yakuhito's slot machine: action layer, slots, CATalog and XCHandles.
        # puzzles/ has the chialisp version (the include/ folder has the .clib files).
        # The chialisp version compiles to other hashes than the Rue one, the deployed
        # puzzles (and the ones in chia-wallet-sdk) are the Rue version, see slot_machine_rue
        "name": "slot_machine",
        "url": "https://github.com/Yakuhito/slot-machine.git",
        "subdir": "puzzles",
    },
    {
        # Same repo, rue-puzzles/ has the Rue version: every puzzle has its compiled
        # <file>.rue.hex and <file>.rue.hash committed (Rue.toml: compiler 0.9.0).
        # The .rue files without .rue.hex are libraries (common_types, merkle_utils, ...).
        "name": "slot_machine_rue",
        "repo": "slot_machine",
        "url": "https://github.com/Yakuhito/slot-machine.git",
        "subdir": "rue-puzzles",
        "language": "rue",
    },
    {
        # DIG Network reward distributor (DIP-0002, CHIP-0051): the actions of the reward
        # distributor and p2_parent_v2. Same layout of slot-machine: puzzles/ is the
        # chialisp version, rue-puzzles/ the Rue version (deployed, it is in chia-wallet-sdk)
        "name": "reward_distributor",
        "url": "https://github.com/DIG-Network/reward-distributor-clsp.git",
        "subdir": "puzzles",
    },
    {
        "name": "reward_distributor_rue",
        "repo": "reward_distributor",
        "url": "https://github.com/DIG-Network/reward-distributor-clsp.git",
        "subdir": "rue-puzzles",
        "language": "rue",
    },
    {
        # CHIP-0037 EIP-712 wallet puzzle: p2_eip712_message (coins spent with an EIP-712
        # signature, e.g. from an Ethereum hardware wallet) and p2_controller_puzzle (coins
        # controlled by the messages of another puzzle, one signature for many coins).
        # Both are in chia-wallet-sdk. The other CHIPs in this repo have no puzzle files.
        "name": "chip_0037",
        "repo": "chips",
        "url": "https://github.com/Chia-Network/chips.git",
        "subdir": "assets/chip-0037/clsp",
    },
    {
        # CHIP-0045 option contracts (put and call options), by Rigidity. The puzzle is only
        # written in the CHIP text, under "### Option Contract Puzzle". It is the inner puzzle
        # of a singleton_top_layer_v1_1, OPTION_CONTRACT in chia-wallet-sdk.
        # It includes curry.clib and utility_macros.clib, which are not in the chips repo:
        # the standard ones of chia_puzzles (cni) are used
        "name": "chip_0045",
        "repo": "chips",
        "url": "https://github.com/Chia-Network/chips.git",
        "include_dirs": [{"repo": "cni", "path": "puzzles"}],
        "markdown_puzzles": [
            {"file": "CHIPs/chip-0045.md", "section": "Option Contract Puzzle", "name": "option_contract"},
        ],
    },
    {
        # chia-blockchain custody puzzles (CHIP-0043 MIPS, vaults): restrictions that check the
        # conditions of a delegated puzzle, e.g. heightlock (ASSERT_HEIGHT_RELATIVE required),
        # fixed_create_coin_destinations (CREATE_COIN only to a fixed curried puzzle hash) and
        # send_message_banned (no SEND_MESSAGE). They are not in chia_puzzles nor in
        # chia-wallet-sdk. Only chia/wallet/puzzles is checked out (it has the .clib files
        # they include): the repo is big
        "name": "chia_blockchain_custody",
        "repo": "chia_blockchain",
        "url": "https://github.com/Chia-Network/chia-blockchain.git",
        "subdir": "chia/wallet/puzzles/custody",
        "sparse": ["chia/wallet/puzzles"],
    },
    {
        # Yakuhito's streaming puzzle: pays CATs/XCH to a recipient over time, with clawback.
        # It is STREAM_PUZZLE in chia-wallet-sdk. Its included files end in .clsp, not .clib
        "name": "streaming",
        "url": "https://github.com/Yakuhito/streaming.git",
        "subdir": "puzzles",
        "include_dirs": ["include"],
    },
    {
        # DIG Network DataLayer driver: delegation_layer and writer_filter, the layers DIG
        # adds to a DataLayer store. They are DELEGATION_LAYER_PUZZLE and WRITER_LAYER_PUZZLE
        # in chia-wallet-sdk
        "name": "dig_datalayer",
        "url": "https://github.com/DIG-Network/DataLayer-Driver.git",
        "subdir": "puzzles",
    },
    {
        # Forge (forge.awizard.dev): a weighted N-asset AMM, an action layer singleton built on
        # CHIP-0050. One Rue project for every revision in contracts/vNN: V16 is the shipping
        # one (the only one on mainnet), V15 and V14 are still live on testnet11.
        # The hex is in compiled/ (dist_dir of Rue.toml). puzzles/upstream/ is slot-machine
        # copied verbatim (already in slot_machine_rue, same puzzle hashes).
        # The puzzles equal in more revisions get the name of the last one (forge_v16)
        "name": "forge_v14",
        "repo": "forge",
        "url": "https://github.com/awizardxch/forge-puzzles.git",
        "subdir": "contracts/v14/puzzles",
        "compiled_dir": "contracts/v14/compiled",
        "exclude": ["testing"],
        "language": "rue",
    },
    {
        "name": "forge_v15",
        "repo": "forge",
        "url": "https://github.com/awizardxch/forge-puzzles.git",
        "subdir": "contracts/v15/puzzles",
        "compiled_dir": "contracts/v15/compiled",
        "exclude": ["testing"],
        "language": "rue",
    },
    {
        "name": "forge_v16",
        "repo": "forge",
        "url": "https://github.com/awizardxch/forge-puzzles.git",
        "subdir": "contracts/v16/puzzles",
        "compiled_dir": "contracts/v16/compiled",
        "exclude": ["testing"],
        "language": "rue",
    },
    {
        # The chialisp puzzles of Forge: the inner puzzles of the LP token, the same in V14,
        # V15 and V16 (vNN/clsp/forge_lp_mint_inner.clsp, and forge_lp_melt_inner_FORGE.clsp
        # in contracts/ that every revision uses). forge_lp_mint_inner_FORGE.clsp is the
        # older V10 version, not used by V14-V16
        "name": "forge_clsp",
        "repo": "forge",
        "url": "https://github.com/awizardxch/forge-puzzles.git",
        "subdir": "contracts",
        "exclude": ["v14", "v15", "forge_lp_mint_inner_FORGE.clsp"],
    },
]

# Puzzles that are not in a .clsp file, they are hardcoded here as compiled bytecode.
# The puzzle hash is checked when the catalog is built.
HARDCODED_PUZZLES = [
    {
        # MIPS index wrapper: (a 5 7), curried with (nonce inner_puzzle) it runs the inner
        # puzzle and ignores the nonce, the nonce only changes the puzzle hash.
        # Used by the vaults (MIPS), the bulletin layer and the reward distributor (where
        # it is called NONCE_WRAPPER_PUZZLE).
        # Found in https://github.com/xch-dev/chia-wallet-sdk (commit ed584e3, 2026-10-19):
        #   crates/chia-sdk-types/src/puzzles/mips/index_wrapper.rs (INDEX_WRAPPER, INDEX_WRAPPER_HASH)
        # It is defined only as hex in Rust, there is no .clsp file.
        "source": "sdk",
        "name": "mips-index_wrapper",
        "bytecode": "ff02ff05ff0780",
        "puzzle_hash": "847d971ef523417d555ea9854b1612837155d34d453298defcd310774305f657",
        # clvm written by hand from the bytecode, the sdk has only the hex
        "clvm": "(mod (INDEX INNER_PUZZLE . inner_solution) (a INNER_PUZZLE inner_solution))",
    },
    {
        # MIPS member controlled by an Ethereum (secp256k1) key: it checks an EIP-712 signature
        # of ChiaCoinSpend(coin_id, delegated_puzzle_hash), like p2_eip712_message of CHIP-0037
        # but as a vault member, and returns only ASSERT_MY_COIN_ID.
        # No official source found: it is not in chia_puzzles nor in the CHIPs, the bytecode
        # is from https://github.com/xch-dev/chia-wallet-sdk (commit ed584e3, 2026-10-19):
        #   crates/chia-sdk-types/src/puzzles/mips/members/eip712_member.rs (EIP712_MEMBER, EIP712_MEMBER_HASH)
        # The sdk links as its source a third party repo (Sols Lot, tokenized real world assets):
        #   https://github.com/MattHintz/solslot-protocol/blob/108ac023d836cf0198775eebd377880d0f8d6aef/solslot_puzzles/eip712_member_v2.clsp
        # the clvm below is that file, it compiles to this puzzle hash.
        # Do not use eip712_member.clsp (v1) of that repo: it returns ASSERT_MY_AMOUNT, every spend fails
        "source": "sdk",
        "name": "mips-eip712_member",
        "bytecode": (
            "ff02ffff01ff02ffff03ffff22ffff20ffff8413d61f00ff17ff81bfff82017f8080ffff20ffff24"
            "ffff01820ab9ffff0101ffff01ff02ffff03ffff09ffff3eff02ffff3eff05ff0bff178080ff2f80"
            "ff80ffff01ff088080ff0180ffff04ff05ffff04ff0bffff04ff5fffff04ff2fffff04ff81bfff80"
            "8080808080808080ffff01ff04ffff04ff02ffff04ff5fff808080ff8080ffff01ff088080ff0180"
            "ffff04ffff0146ff018080"
        ),
        "puzzle_hash": "aaf5d0676da9c06b02ae94acc7f226c6b583205d42f5b350bec43df7fcd09ea7",
        "clvm": (
            '; eip712_member_v2.clsp -- CHIP-0043 member for EIP-712 daily keys.\n'
            ';\n'
            '; This is the Authority V3 variant of the historical integration fixture.\n'
            '; It preserves the CHIP-0037 signed payload while emitting the consensus\n'
            '; ASSERT_MY_COIN_ID opcode (70). The old fixture emitted opcode 73\n'
            '; (ASSERT_MY_AMOUNT) and remains unchanged for V2 audit reproducibility.\n'
            '\n'
            '(mod (PREFIX_AND_DOMAIN_SEPARATOR TYPE_HASH PUBKEY\n'
            '      delegated_puzzle_hash\n'
            '      my_id signed_hash signature)\n'
            '\n'
            '  (defconstant ASSERT_MY_COIN_ID 70)\n'
            '\n'
            '  (if (all\n'
            '        (not (secp256k1_verify PUBKEY signed_hash signature))\n'
            '        (not (softfork\n'
            '                (q . 2745)\n'
            '                (q . 1)\n'
            '                (mod\n'
            '                  (PREFIX_AND_DOMAIN_SEPARATOR TYPE_HASH my_id\n'
            '                   delegated_puzzle_hash signed_hash)\n'
            '                  (if (= (keccak256 PREFIX_AND_DOMAIN_SEPARATOR\n'
            '                                    (keccak256 TYPE_HASH my_id\n'
            '                                               delegated_puzzle_hash))\n'
            '                         signed_hash)\n'
            '                      ()\n'
            '                      (x)))\n'
            '                (list PREFIX_AND_DOMAIN_SEPARATOR TYPE_HASH my_id\n'
            '                      delegated_puzzle_hash signed_hash))))\n'
            '      (list (list ASSERT_MY_COIN_ID my_id))\n'
            '      (x)))\n'
        ),
    },
    {
        # MIPS wrapper that forces the vault singleton to recreate itself unchanged: the amount
        # of ASSERT_MY_AMOUNT must be equal to the amount of the odd CREATE_COIN, so the
        # singleton can not be melted and its amount can not change.
        # Source not found: it is only hex in https://github.com/xch-dev/chia-wallet-sdk
        # (commit ed584e3, 2026-10-19), added by PR #437 "Add new vault feature":
        #   crates/chia-sdk-types/src/puzzles/mips/wrappers/force_singleton_recreation.rs
        #   (FORCE_SINGLETON_RECREATION, FORCE_SINGLETON_RECREATION_HASH)
        # The sdk file says "TODO: Import these from chia-puzzles after they are published": when
        # it is in chia_puzzles the cni source finds it (it will have another name there).
        # The clvm below is written by hand from the bytecode (names are ours, the functions are
        # named so that the compiler keeps their order): it compiles to this puzzle hash
        "source": "sdk",
        "name": "mips-force_singleton_recreation",
        "bytecode": (
            "ff02ffff01ff02ff1effff04ff02ffff04ffff02ff16ffff04ff02ffff04ff05ff80808080ffff04"
            "ff05ff8080808080ffff04ffff01ffff4933ffff02ffff03ffff09ff09ff0c80ffff01ff02ffff03"
            "ffff18ff2dffff010180ffff01ff04ff13ff2d80ffff010b80ff0180ffff01ff02ffff03ffff09ff"
            "09ff0880ffff01ff04ff15ff1b80ffff010b80ff018080ff0180ffff02ffff03ff05ffff01ff02ff"
            "0affff04ff02ffff04ff09ffff04ffff02ff16ffff04ff02ffff04ff0dff80808080ff8080808080"
            "ffff01ff01ff808080ff0180ff02ffff03ffff09ff09ff0d80ffff010bffff01ff088080ff0180ff"
            "018080"
        ),
        "puzzle_hash": "63e04374ced7e7f9ab0f46e9bad1b4e82bf3edf671ea355cd60113c7a947ee1e",
        "clvm": (
            '(mod (conditions)\n'
            '    (defconstant ASSERT_MY_AMOUNT 73)\n'
            '    (defconstant CREATE_COIN 51)\n'
            '\n'
            '    ; info is (asserted_amount . odd_create_coin_amount)\n'
            '    (defun add_condition (condition info)\n'
            '        (if (= (f condition) CREATE_COIN)\n'
            '            (if (logand (f (r (r condition))) 1)\n'
            '                (c (f info) (f (r (r condition))))\n'
            '                info\n'
            '            )\n'
            '            (if (= (f condition) ASSERT_MY_AMOUNT)\n'
            '                (c (f (r condition)) (r info))\n'
            '                info\n'
            '            )\n'
            '        )\n'
            '    )\n'
            '\n'
            '    (defun collect_info (conditions)\n'
            '        (if conditions\n'
            '            (add_condition (f conditions) (collect_info (r conditions)))\n'
            '            (q ())\n'
            '        )\n'
            '    )\n'
            '\n'
            '    (defun verify_info (info conditions)\n'
            '        (if (= (f info) (r info))\n'
            '            conditions\n'
            '            (x)\n'
            '        )\n'
            '    )\n'
            '\n'
            '    (verify_info (collect_info conditions) conditions)\n'
            ')\n'
        ),
    },
    {
        # The program 1: returns its whole solution (identity). One puzzle hash for many roles,
        # so the name says what it does, not where it is used. In chia-wallet-sdk (commit ed584e3):
        #   - XCH_CAT_MAKER_PUZZLE (action layer: for XCH the payment puzzle hash is not wrapped)
        #   - RESERVE_FINALIZER_DEFAULT_RESERVE_AMOUNT_FROM_STATE_PROGRAM (reserve finalizer:
        #     the reserve amount is the state itself)
        # Used as the puzzle of a coin it means "anyone can spend": the solution is the conditions
        "source": "clvm",
        "name": "identity",
        "bytecode": "01",
        "puzzle_hash": "9dcf97a184f32623d11a73124ceb99a5709b083721e878a16d78f596718ba7b2",
        "clvm": "(mod args args)",
    },
    {
        # The program 11: returns the third element of its solution, (f (r (r solution))).
        # In chia-wallet-sdk (commit ed584e3) it is DL_METADATA_UPDATER_PUZZLE: the DataLayer
        # metadata updater takes the new metadata from the third element of its solution
        "source": "clvm",
        "name": "third_argument",
        "bytecode": "0b",
        "puzzle_hash": "57bfd1cb0adda3d94315053fda723f2028320faa8338225d99f629e3d46d43a9",
        "clvm": "(mod (first second third) third)",
    },
]

# All the puzzles of chia-wallet-sdk (commit ed584e3) are in the catalog now. In the sdk most
# of them are only hex constants in Rust: pub const NAME: [u8; N] = hex!(...) with NAME_HASH
# next to it; the standard ones come from the chia-puzzles crate (the cni source).
# Where each one was found:
#   - Rue puzzles of slot-machine: slot_machine_rue; ANY_METADATA_UPDATER: slot_machine
#   - Rue puzzles of the reward distributor: reward_distributor_rue;
#     P2_PARENT_PUZZLE: reward_distributor (p2_parent_v2)
#   - P2_CONTROLLER_PUZZLE_PUZZLE and P2_EIP712_MESSAGE_PUZZLE: chip_0037
#   - STREAM_PUZZLE: streaming
#   - DELEGATION_LAYER_PUZZLE and WRITER_LAYER_PUZZLE: dig_datalayer
#   - OPTION_CONTRACT: chip_0045
#   - INDEX_WRAPPER, EIP712_MEMBER and FORCE_SINGLETON_RECREATION: HARDCODED_PUZZLES (no
#     official source found)
#   - XCH_CAT_MAKER_PUZZLE and RESERVE_FINALIZER_DEFAULT_RESERVE_AMOUNT_FROM_STATE_PROGRAM (the
#     program 1) and DL_METADATA_UPDATER_PUZZLE (the program 11): HARDCODED_PUZZLES, named
#     --clvm-identity and --clvm-third_argument
#   - NONCE_WRAPPER_PUZZLE: same program of INDEX_WRAPPER
# FORCE_SINGLETON_RECREATION_HASH is a hash, not a program.


# Local directory where shallow clones are cached between runs.
# Located next to this script so everything stays inside the repo tree.
# Delete this directory if you want to force a fresh download.
SCRIPT_DIR = pathlib.Path(__file__).parent.resolve()
CACHE_DIR = SCRIPT_DIR / "repo_sources"


def ensure_repo(name: str, url: str, sparse: list = None) -> pathlib.Path:
    """Shallow-clone a repo into CACHE_DIR if it isn't already cached.
    With *sparse* only those folders are checked out (see "sparse" in SOURCES)."""
    dest = CACHE_DIR / name
    if dest.exists():
        print(f"[cache] Using existing clone: {dest}")
        return dest

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[git] Cloning {url} …")
    sparse_args = ["--filter=blob:none", "--sparse"] if sparse else []
    subprocess.run(
        ["git", "clone", "--depth", "1", *sparse_args, url, str(dest)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if sparse:
        subprocess.run(
            ["git", "-C", str(dest), "sparse-checkout", "set", *sparse],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    return dest


def get_puzzle_root(repo_path: pathlib.Path, subdir: str) -> pathlib.Path:
    """Return the sub-directory inside the repo that holds the .clsp files.

    If *subdir* is provided and exists we use it; otherwise we fall back to the
    repo root.
    """
    if subdir:
        candidate = repo_path / subdir
        if candidate.exists():
            return candidate
        print(
            f"[warn] Requested subdir '{subdir}' not found in {repo_path}; "
            f"falling back to repo root.",
            file=sys.stderr,
        )
    return repo_path


def find_include_dirs(repo_path: pathlib.Path) -> list[pathlib.Path]:
    """Return every directory under *repo_path* that contains at least one .clib file."""
    include_dirs = set()
    for root, _dirs, files in os.walk(repo_path):
        if any(f.endswith(".clib") for f in files):
            include_dirs.add(pathlib.Path(root))
    return sorted(include_dirs)


def load_clvm_from_file(clvm_path, search_paths=None):
    """Compile a .clsp file to a temporary hex file, load it, then delete the
    hex file. The hex file is outside the repo: some repos have their own
    <file>.clsp.hex committed, it must not be overwritten or deleted."""
    if search_paths is None:
        search_paths = []

    full_path = pathlib.Path(clvm_path)
    parent_path = full_path.parent

    # a new folder for every file: the hex file must not exist before compiling
    with tempfile.TemporaryDirectory() as tmp_dir:
        hex_path = pathlib.Path(tmp_dir) / f"{full_path.name}.hex"
        compile_clvm(
            full_path,
            hex_path,
            search_paths=[parent_path, *search_paths],
        )
        with open(hex_path, "r", encoding="utf-8") as file:
            clvm_blob = bytes.fromhex(file.read())

    return Program.from_bytes(clvm_blob)


def build_hardcoded_puzzles():
    """Catalog entries of HARDCODED_PUZZLES, with the same fields of the compiled ones"""
    store = {}
    for puzzle in HARDCODED_PUZZLES:
        prog = Program.fromhex(puzzle["bytecode"])
        puzzle_hash = str(prog.get_tree_hash())
        if puzzle_hash != puzzle["puzzle_hash"]:
            raise ValueError(f"{puzzle['name']}: puzzle hash {puzzle_hash} != {puzzle['puzzle_hash']}")
        # the clvm is written here, not taken from a repo: check it is the same puzzle
        with tempfile.TemporaryDirectory() as tmp_dir:
            clsp_path = pathlib.Path(tmp_dir) / "puzzle.clsp"
            clsp_path.write_text(puzzle["clvm"])
            clvm_hash = str(load_clvm_from_file(clsp_path).get_tree_hash())
        if clvm_hash != puzzle_hash:
            raise ValueError(f"{puzzle['name']}: the clvm compiles to {clvm_hash}, not {puzzle_hash}")
        store[puzzle_hash] = {
            "file_name": None,
            "name": f"--{puzzle['source']}-{puzzle['name']}",
            "puzzle_hash": puzzle_hash,
            "bytecode": prog.to_json_dict(),
            "bytecode_disassembled": bu_disassemble(prog),
            "clvm": puzzle["clvm"],
        }
    return store


def parse_puzzles(path, store, prefix="-", puzzles_root_folder=None, include_dirs=None, exclude=()):
    """Recursively scan *path* for .clsp files, compile them, and store
    metadata in *store* keyed by puzzle_hash. The paths in *exclude* are skipped."""
    if puzzles_root_folder is None:
        puzzles_root_folder = path
    if include_dirs is None:
        include_dirs = []

    files = os.listdir(path)
    for file_name in files:
        sub_path = os.path.join(path, file_name)
        if pathlib.Path(sub_path) in exclude:
            print(f"  excluded: {sub_path}")
            continue
        if os.path.isdir(sub_path):
            prefix_puzzle = f"{prefix}-{file_name}"
            parse_puzzles(sub_path, store, prefix_puzzle, puzzles_root_folder, include_dirs, exclude)
        else:
            if file_name.endswith(".clsp"):
                short_name = file_name[:-5]
                name = f"{prefix}-{short_name}"
                print(f"  processing {sub_path} …")
                try:
                    search_paths = [pathlib.Path(puzzles_root_folder)] + include_dirs
                    prog = load_clvm_from_file(sub_path, search_paths)
                except Exception as exc:
                    print(f"  [ERROR] skipped {sub_path}: {exc}", file=sys.stderr)
                    continue

                new_puzzle = {
                    "file_name": file_name,
                    "name": name,
                    "puzzle_hash": str(prog.get_tree_hash()),
                    "bytecode": prog.to_json_dict(),
                    "bytecode_disassembled": bu_disassemble(prog),
                }
                with open(sub_path, "r") as f:
                    new_puzzle["clvm"] = f.read()

                store[new_puzzle["puzzle_hash"]] = new_puzzle
                print(f"  → {name} ({new_puzzle['puzzle_hash']})")


# TODO (step 2): compile the Rue puzzles here instead of trusting the committed .rue.hex.
#   - install the compiler of the version in the repo Rue.toml ([compiler] version, 0.9.0
#     for slot-machine): cargo install rue-cli --version 0.9.0 (repo: github.com/xch-dev/rue)
#   - find the build command and where it writes the output (rue build? per file?)
#   - compile into a temporary folder (like load_clvm_from_file) and compare with the
#     committed .rue.hex: a difference means the committed output is out of date
#   - if rue is not installed, or its version differs from Rue.toml, use the committed
#     .rue.hex as now and print a warning
def parse_rue_puzzles(path, store, prefix="-", compiled_dir=None, exclude=()):
    """Recursively scan *path* for .rue files that have their compiled <file>.rue.hex
    committed next to them (or in *compiled_dir*, see SOURCES), and store them in *store*
    keyed by puzzle_hash. The paths in *exclude* are skipped.
    The hash of the hex must be equal to <file>.rue.hash when that file exists.
    .rue files without .rue.hex are libraries, they are skipped."""
    for file_name in sorted(os.listdir(path)):
        sub_path = os.path.join(path, file_name)
        if pathlib.Path(sub_path) in exclude:
            print(f"  excluded: {sub_path}")
            continue
        if os.path.isdir(sub_path):
            parse_rue_puzzles(sub_path, store, f"{prefix}-{file_name}", compiled_dir, exclude)
            continue
        if not file_name.endswith(".rue"):
            continue
        if compiled_dir is None:
            hex_path = pathlib.Path(sub_path + ".hex")
        else:
            hex_path = pathlib.Path(compiled_dir) / f"{file_name}.hex"
        if not hex_path.exists():
            print(f"  library (no .rue.hex), skipped: {sub_path}")
            continue
        name = f"{prefix}-{file_name[:-4]}"
        try:
            prog = Program.fromhex(hex_path.read_text().strip())
        except Exception as exc:
            print(f"  [ERROR] skipped {sub_path}: invalid .rue.hex: {exc}", file=sys.stderr)
            continue
        puzzle_hash = str(prog.get_tree_hash())
        hash_path = hex_path.with_suffix(".hash")
        if hash_path.exists():
            expected = hash_path.read_text().strip().removeprefix("0x")
            if puzzle_hash != expected:
                print(f"  [ERROR] skipped {sub_path}: hash of .rue.hex {puzzle_hash} "
                      f"!= .rue.hash {expected}", file=sys.stderr)
                continue
        with open(sub_path, "r") as f:
            source = f.read()
        store[puzzle_hash] = {
            "file_name": file_name,
            "name": name,
            "puzzle_hash": puzzle_hash,
            "bytecode": prog.to_json_dict(),
            "bytecode_disassembled": bu_disassemble(prog),
            "clvm": source,  # the Rue source, not chialisp
            "language": "rue",
        }
        print(f"  → {name} ({puzzle_hash})")


def resolve_include_dirs(src, repo_path):
    """find_include_dirs of the source repo, plus its "include_dirs" (see SOURCES)"""
    include_dirs = find_include_dirs(repo_path)
    for entry in src.get("include_dirs", []):
        if isinstance(entry, dict):  # a folder of another source's clone
            other = next(s for s in SOURCES if s.get("repo", s["name"]) == entry["repo"])
            folder = ensure_repo(entry["repo"], other["url"]) / entry["path"]
        else:
            folder = repo_path / entry
        if folder not in include_dirs:
            include_dirs.append(folder)
    return include_dirs


def markdown_code_block(md_path, section):
    """Text of the first ``` code block under the heading *section* of a markdown file,
    before the next heading of the same or higher level"""
    lines = pathlib.Path(md_path).read_text().splitlines()
    start = level = None
    for i, line in enumerate(lines):
        hashes = len(line) - len(line.lstrip("#"))
        if hashes and line[hashes:].strip() == section:
            start, level = i + 1, hashes
            break
    if start is None:
        raise ValueError(f"heading '{section}' not found in {md_path}")
    block = None
    for line in lines[start:]:
        hashes = len(line) - len(line.lstrip("#"))
        if block is None:
            if hashes and hashes <= level and line[hashes:].startswith(" "):
                break  # next section, no code block
            if line.startswith("```"):
                block = []
        elif line.startswith("```"):
            return "\n".join(block) + "\n"
        else:
            block.append(line)
    raise ValueError(f"no code block under '{section}' in {md_path}")


def parse_markdown_puzzles(src, repo_path, store, include_dirs):
    """Compile the puzzles of src["markdown_puzzles"] (see SOURCES) into *store*"""
    for puzzle in src["markdown_puzzles"]:
        md_path = repo_path / puzzle["file"]
        name = f"--{src['name']}-{puzzle['name']}"
        print(f"  processing {md_path} '{puzzle['section']}' …")
        try:
            source = markdown_code_block(md_path, puzzle["section"])
            with tempfile.TemporaryDirectory() as tmp_dir:
                clsp_path = pathlib.Path(tmp_dir) / f"{puzzle['name']}.clsp"
                clsp_path.write_text(source)
                prog = load_clvm_from_file(clsp_path, [md_path.parent, *include_dirs])
        except Exception as exc:
            print(f"  [ERROR] skipped {name}: {exc}", file=sys.stderr)
            continue
        puzzle_hash = str(prog.get_tree_hash())
        store[puzzle_hash] = {
            "file_name": md_path.name,
            "name": name,
            "puzzle_hash": puzzle_hash,
            "bytecode": prog.to_json_dict(),
            "bytecode_disassembled": bu_disassemble(prog),
            "clvm": source,
            "markdown_section": puzzle["section"],  # where the puzzle is in file_name
        }
        print(f"  → {name} ({puzzle_hash})")


# The combined catalog is never rewritten from scratch: the compiled puzzles are merged
# into the existing file (see merge_into_catalog), the entries already there are kept.
CATALOG_FILE = SCRIPT_DIR / "puzzles.json"


def merge_into_catalog(catalog: dict, new_puzzles: dict, found_date: str):
    """Add new_puzzles to catalog, nothing in catalog is changed or deleted.
    - puzzle hash already in the catalog: skipped
    - name already in the catalog with another puzzle hash (the source changed): added
      as a new puzzle named <name>_CHANGED_FOUND_ON_<yy_mm_dd>
    - new name: added
    Return (added, modified, skipped) lists of names."""
    names = {entry["name"] for entry in catalog.values()}
    added, modified, skipped = [], [], []
    for puzzle_hash, puzzle in new_puzzles.items():
        if puzzle_hash in catalog:
            skipped.append(puzzle["name"])
            continue
        puzzle = dict(puzzle)
        if puzzle["name"] in names:
            name = f"{puzzle['name']}_CHANGED_FOUND_ON_{found_date}"
            n = 2
            while name in names:  # changed again on the same day
                name = f"{puzzle['name']}_CHANGED_FOUND_ON_{found_date}_{n}"
                n += 1
            puzzle["name"] = name
            modified.append(name)
        else:
            added.append(puzzle["name"])
        names.add(puzzle["name"])
        catalog[puzzle_hash] = puzzle
    return added, modified, skipped


# Main
if __name__ == "__main__":
    all_puzzles = {}

    for src in SOURCES:
        print(f"\n=== {src['name']} ===")
        repo_path = ensure_repo(src.get("repo", src["name"]), src["url"], src.get("sparse"))
        puzzle_root = get_puzzle_root(repo_path, src.get("subdir", ""))

        if not puzzle_root.exists():
            print(
                f"[SKIP] puzzle root {puzzle_root} does not exist.",
                file=sys.stderr,
            )
            continue

        repo_catalog = {}
        exclude = {puzzle_root / entry for entry in src.get("exclude", [])}
        if src.get("language", "chialisp") == "rue":
            compiled_dir = repo_path / src["compiled_dir"] if "compiled_dir" in src else None
            parse_rue_puzzles(
                str(puzzle_root),
                repo_catalog,
                prefix=f"--{src['name']}",
                compiled_dir=compiled_dir,
                exclude=exclude,
            )
        elif "markdown_puzzles" in src:
            parse_markdown_puzzles(src, repo_path, repo_catalog, resolve_include_dirs(src, repo_path))
        else:
            include_dirs = resolve_include_dirs(src, repo_path)
            if include_dirs:
                print(f"  include search paths: {[str(d) for d in include_dirs]}")
            parse_puzzles(
                str(puzzle_root),
                repo_catalog,
                prefix=f"--{src['name']}",
                include_dirs=include_dirs,
                exclude=exclude,
            )

        out_file = f"{src['name']}_puzzles.json"
        with open(out_file, "w") as f:
            json.dump(repo_catalog, f, indent=4)
        print(f"Wrote {out_file} ({len(repo_catalog)} puzzles)")

        all_puzzles.update(repo_catalog)

    print("\n=== hardcoded ===")
    hardcoded = build_hardcoded_puzzles()
    for puzzle in hardcoded.values():
        print(f"  → {puzzle['name']} ({puzzle['puzzle_hash']})")
    all_puzzles.update(hardcoded)

    # Combined catalog (backwards-compatible name): merge into the existing file
    catalog = {}
    if CATALOG_FILE.exists():
        with open(CATALOG_FILE, "r") as f:
            catalog = json.load(f)
    count_before = len(catalog)
    added, modified, skipped = merge_into_catalog(catalog, all_puzzles, date.today().strftime("%y_%m_%d"))

    print(f"\n=== {CATALOG_FILE.name} ===")
    print(f"  already in the catalog: {len(skipped)}")
    for name in added:
        print(f"  [new] {name}")
    for name in modified:
        print(f"  [modified source, added as new puzzle] {name}")

    if added or modified:
        tmp_file = CATALOG_FILE.with_name(CATALOG_FILE.name + ".tmp")
        with open(tmp_file, "w") as f:
            json.dump(catalog, f, indent=4)
        os.replace(tmp_file, CATALOG_FILE)  # a crash can not leave a truncated file
    print(f"{CATALOG_FILE.name}: {count_before} -> {len(catalog)} puzzles")
