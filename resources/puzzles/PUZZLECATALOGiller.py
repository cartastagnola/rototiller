import os
import pathlib
import json
import subprocess
import sys
import re
import tempfile
from datetime import date

from chia.types.blockchain_format.program import Program
from chia.wallet.puzzles.load_clvm import compile_clvm
from clvm_tools.binutils import disassemble as bu_disassemble


# Remote puzzle sources to fetch.
# Each entry maps a repo name to its Git URL and the sub-directory that
# contains the .clsp files (use "" for repo root).
# Optional fields:
#   "language": "chialisp" (default, the .clsp files are compiled here), "rue" (the
#               compiled .rue.hex committed in the repo is read, see parse_rue_puzzles) or
#               "chialisp-23" (modern Chialisp with modules, compiled with the chialisp
#               package, see parse_chialisp23_puzzles)
#   "repo":     folder of the clone in CACHE_DIR (default: "name"), two sources of the
#               same repo share one clone
#   "include_dirs": folders of the repo to search for included files, added to the ones
#               found by find_include_dirs (it finds only folders with .clib files).
#               {"repo": <name>, "path": <folder>} is a folder of another source's clone
#   "ref":      commit to check out instead of the latest one, for old versions of the
#               puzzles that are still on chain. The clone has only that commit
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
#   "files":    only these files of "subdir" are compiled, paths relative to "subdir".
#               They can end in .clvm (old repos), not only .clsp
#   "history":  every version of the puzzles in the whole history of the repo (every branch
#               and tag) is compiled, not only the latest one, see parse_history_puzzles.
#               The clone is a full one, not shallow. Chialisp only
#   "hashes_only": the catalog gets only the name, puzzle hash and sources of each puzzle,
#               not its code (CODE_FIELDS): for repos whose license does not allow copying
#               the code. Rototiller never reads the code from the catalog (the coin screen
#               shows the coin's own puzzle reveal)
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
        # TibetSwap v1 beta, used on mainnet in April 2023 (heights 3,560,549-3,603,036) and
        # replaced after "fix bug in pair code" (2023-04-29). At this commit (2023-04-09) the
        # pair_inner_puzzle, router and p2_singleton_flashloan are the beta ones seen on chain
        "name": "tibet_v1_beta",
        "url": "https://github.com/Yakuhito/tibet.git",
        "ref": "48944f2dcfe1a34a570a79e08331d6fffe628b45",
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
        # CAT v1 (puzzle hash 72dec062...), used on mainnet from 2022 until CAT v2 (chia 1.5.0,
        # July 2022). It is cat.clvm in chia-blockchain 1.3.0 and 1.4.0, this is 1.4.0.
        # The old CATs on chain still use it
        "name": "chia_blockchain_cat_v1",
        "url": "https://github.com/Chia-Network/chia-blockchain.git",
        "ref": "bd35cb183bd9cd752dc9df5ffba3efd437011c90",
        "sparse": ["chia/wallet/puzzles"],
        "subdir": "chia/wallet/puzzles",
        "files": ["cat.clvm"],
    },
    {
        # chia-gaming: two-player games over state channels (Chia Network). On chain: the
        # unroll coin (closes a channel), the referee (a game coin in a dispute) and the move
        # validators of each game, run by the referee. Arcade21 builds on it. Modern Chialisp
        # (cl-23, modules). The factories build a game's parameters off chain: not compiled
        "name": "chia_gaming",
        "url": "https://github.com/Chia-Network/chia-gaming.git",
        "ref": "ad21a649434dd5eb9eb7c0d4df70da841a44e44f",
        "language": "chialisp-23",
        "subdir": "",
        "exclude": ["clsp/test", "games/debug", "node_modules", "front-end", "wasm",
                    "games/calpoker/clsp/factory.clsp", "games/calpoker/clsp/factory_probe.clsp",
                    "games/calpoker/clsp/onchain/test_atomsort.clsp",
                    "games/krunk/clsp/factory.clsp", "games/krunk/clsp/factory_probe.clsp",
                    "games/spacepoker/clsp/factory.clsp", "games/spacepoker/clsp/factory_probe.clsp"],
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
    {
        # Solslot (Sols Lot): tokenized real world assets on Chia, by Matthew S. Hintz. On
        # testnet11 in 2026-11, mainnet expected. The puzzles are in solslot_puzzles/
        # (populis_puzzles/ until the rename to Solslot, 2026-07-12); release-manifests/ has
        # copies of old versions. They change often (13 versions of vault_singleton_inner), so
        # every version of the history is built.
        # The repo is public but its LICENSE is proprietary, all rights reserved (no copying,
        # no disassembling): the catalog gets only the names, hashes and sources, not the code.
        # sgt_tail (pgt_tail before) is genesis_by_coin_id and eip712_member_v2 is the sdk
        # eip712_member: those two entries keep project "chia" (set by hand). The test fixtures
        # are excluded (test_fixture_bls_member is the cni bls_member)
        "name": "solslot",
        "url": "https://github.com/MattHintz/solslot-protocol.git",
        "subdir": "",
        "history": True,
        "hashes_only": True,
        "exclude": ["populis_puzzles/test_fixture_bls_member.clsp",
                    "populis_puzzles/test_fixture_eip712_member.clsp",
                    "solslot_puzzles/test_fixture_bls_member.clsp",
                    "solslot_puzzles/test_fixture_eip712_member.clsp"],
    },
]

# Puzzles that are not in a .clsp file, they are hardcoded here as compiled bytecode.
# The puzzle hash is checked when the catalog is built. "clvm" is the source written here,
# checked to compile to the same puzzle hash; an entry without "clvm" has "source_url" instead:
# where the bytecode comes from, for code that today's compilers build to another hash.
# "source" is the project tag (the name prefix). Where the bytecode was found, when known:
# "repo", "commit" and "path" (a file of that repo), and "source_url" (a link to the file the
# clvm comes from). They go in the puzzle's "sources", see make_source.
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
        "repo": "https://github.com/xch-dev/chia-wallet-sdk.git",
        "commit": "ed584e3",
        "path": "crates/chia-sdk-types/src/puzzles/mips/index_wrapper.rs",
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
        "repo": "https://github.com/xch-dev/chia-wallet-sdk.git",
        "commit": "ed584e3",
        "path": "crates/chia-sdk-types/src/puzzles/mips/members/eip712_member.rs",
        "source_url": "https://github.com/MattHintz/solslot-protocol/blob/108ac023d836cf0198775eebd377880d0f8d6aef/solslot_puzzles/eip712_member_v2.clsp",
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
        "repo": "https://github.com/xch-dev/chia-wallet-sdk.git",
        "commit": "ed584e3",
        "path": "crates/chia-sdk-types/src/puzzles/mips/wrappers/force_singleton_recreation.rs",
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
        # chia-gaming unroll puzzle (state_channel_unrolling) used from July 2024 until
        # "Tightened up unroll logic" (2026-05-05), seen on mainnet at heights
        # 8,031,665-8,661,414. The bytecode is the compiled file committed in the repo; the
        # repo built it with an unreleased compiler (clvm_tools_rs rev c3ecaa49 in Cargo.toml),
        # the released chialisp 0.4.4-0.5.0 build the same source to other hashes. The
        # current version is in the chia_gaming source
        "source": "chia_gaming",
        "name": "unroll_puzzle_state_channel_unrolling_v1",
        "bytecode": "ff02ffff01ff02ff26ffff04ff02ffff04ff03ffff04ffff02ff3effff04ff02ffff04ff2fff80808080ff8080808080ffff04ffff01ff80ffffff02ff2affff04ff02ffff04ff03ffff04ff05ff8080808080ffff02ffff03ffff09ff23ffff010180ffff0153ffff01ff02ff12ffff04ff02ffff04ff19ff8080808080ff0180ff02ff26ffff04ff02ffff04ff03ffff04ffff02ff3effff04ff02ffff04ff2fff80808080ff8080808080ffffff02ffff03ff7dffff01ff02ff36ffff04ff02ffff04ff03ffff04ffff02ff5dffff04ff8200bdff808080ff8080808080ffff01ff02ffff03ffff09ff2dff0b80ffff015dffff01ff088080ff018080ff0180ff02ff2effff04ff02ffff04ff03ffff04ffff02ff12ffff04ff02ffff04ff0bff80808080ff8080808080ffff02ffff03ffff15ff0bff5180ffff01ff02ffff03ffff18ffff0101ffff1aff0bff518080ffff01ff02ffff03ffff09ff21ff2980ffff0115ffff01ff088080ff0180ffff01ff088080ff0180ffff01ff088080ff0180ff02ffff03ffff07ff0580ffff01ff0bffff0102ffff02ff3effff04ff02ffff04ff09ff80808080ffff02ff3effff04ff02ffff04ff0dff8080808080ffff01ff0bffff0101ff058080ff0180ff018080",
        "puzzle_hash": "e2589bed0800093691a2d78ecbb92a46507b77554f0057caba1c0f569bd4f3bb",
        "source_url": "https://github.com/Chia-Network/chia-gaming/blob/78f1e604ebad3a3db3b6b7b70b4c0f9dcdc30ada/clsp/unroll/unroll_puzzle_state_channel_unrolling.hex",
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


def ensure_repo(name: str, url: str, sparse: list = None, ref: str = None, full: bool = False) -> pathlib.Path:
    """Shallow-clone a repo into CACHE_DIR if it isn't already cached.
    With *sparse* only those folders are checked out (see "sparse" in SOURCES).
    With *ref* only that commit is fetched and checked out (see "ref" in SOURCES).
    With *full* the whole history is cloned, every branch and tag (see "history" in SOURCES)."""
    dest = CACHE_DIR / name
    if dest.exists():
        print(f"[cache] Using existing clone: {dest}")
        return dest

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if ref:
        print(f"[git] Fetching {url} at {ref[:10]} …")
        sparse_steps = [["-C", str(dest), "sparse-checkout", "set", *sparse]] if sparse else []
        filter_args = ["--filter=blob:none"] if sparse else []
        for args in (["init", "-q", str(dest)], *sparse_steps,
                     ["-C", str(dest), "fetch", "-q", "--depth", "1", *filter_args, url, ref],
                     ["-C", str(dest), "checkout", "-q", "FETCH_HEAD"]):
            subprocess.run(["git", *args], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return dest
    print(f"[git] Cloning {url} …")
    sparse_args = ["--filter=blob:none", "--sparse"] if sparse else []
    depth_args = [] if full else ["--depth", "1"]
    subprocess.run(
        ["git", "clone", *depth_args, *sparse_args, url, str(dest)],
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


_commits = {}


def git_commit(repo_path: pathlib.Path) -> str:
    """Commit checked out in a cached clone: the one the puzzles were compiled from"""
    if repo_path not in _commits:
        _commits[repo_path] = subprocess.run(
            ["git", "-C", str(repo_path), "rev-parse", "HEAD"],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True).stdout.strip()
    return _commits[repo_path]


# Every catalog entry has "sources": where the puzzle can be found, one item for each source
# that builds the same puzzle hash (e.g. the same file in two repos):
#   "project":  the project tag (the name prefix, the "name" of the source in SOURCES)
#   "repo", "commit", "path": the git URL, the commit compiled and the file in that repo
#   "language": chialisp, chialisp-23 or rue
#   optional: "section" (heading of a markdown file), "export" (module export of a
#   chialisp-23 file), "compiled" (the .rue.hex read for a rue file), "url" (a link),
#   "hardcoded": true (the bytecode is written in HARDCODED_PUZZLES)
def make_source(src: dict, repo_path: pathlib.Path, file_path, **extra) -> dict:
    """The "sources" item of a puzzle compiled from file_path, a file of the clone repo_path"""
    def in_repo(path):
        return pathlib.Path(path).resolve().relative_to(repo_path.resolve()).as_posix()

    if "compiled" in extra:
        extra["compiled"] = in_repo(extra["compiled"])
    return {
        "project": src["name"],
        "repo": src["url"],
        "commit": git_commit(repo_path),
        "path": in_repo(file_path),
        "language": src.get("language", "chialisp"),
        **extra,
    }


def source_key(source: dict) -> tuple:
    """Two sources are the same place if they have the same project, file and part of it"""
    return (source.get("project"), source.get("path"), source.get("section"), source.get("export"))


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
        if "clvm" in puzzle:
            with tempfile.TemporaryDirectory() as tmp_dir:
                clsp_path = pathlib.Path(tmp_dir) / "puzzle.clsp"
                clsp_path.write_text(puzzle["clvm"])
                clvm_hash = str(load_clvm_from_file(clsp_path).get_tree_hash())
            if clvm_hash != puzzle_hash:
                raise ValueError(f"{puzzle['name']}: the clvm compiles to {clvm_hash}, not {puzzle_hash}")
        source = {"project": puzzle["source"], "hardcoded": True}
        source.update({key: puzzle[key] for key in ("repo", "commit", "path") if key in puzzle})
        if "source_url" in puzzle:
            source["url"] = puzzle["source_url"]
        store[puzzle_hash] = {
            "file_name": None,
            "name": f"--{puzzle['source']}-{puzzle['name']}",
            "puzzle_hash": puzzle_hash,
            "bytecode": prog.to_json_dict(),
            "bytecode_disassembled": bu_disassemble(prog),
            "clvm": puzzle.get("clvm"),
            "sources": [source],
        }
    return store


def parse_puzzles(path, store, prefix="-", puzzles_root_folder=None, include_dirs=None, exclude=(), only=None,
                  source_of=None):
    """Recursively scan *path* for .clsp files, compile them, and store
    metadata in *store* keyed by puzzle_hash. The paths in *exclude* are skipped.
    With *only* (a set of paths) only those files are compiled, .clvm ones too.
    source_of(file_path, **extra) gives the "sources" item of a file (see make_source)."""
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
            parse_puzzles(sub_path, store, prefix_puzzle, puzzles_root_folder, include_dirs, exclude, only,
                          source_of)
        else:
            if only is not None and pathlib.Path(sub_path) not in only:
                continue
            if file_name.endswith(".clsp") or (only is not None and file_name.endswith(".clvm")):
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
                if source_of is not None:
                    new_puzzle["sources"] = [source_of(sub_path)]

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
def parse_rue_puzzles(path, store, prefix="-", compiled_dir=None, exclude=(), source_of=None):
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
            parse_rue_puzzles(sub_path, store, f"{prefix}-{file_name}", compiled_dir, exclude, source_of)
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
        }
        if source_of is not None:
            store[puzzle_hash]["sources"] = [source_of(sub_path, compiled=hex_path)]
        print(f"  → {name} ({puzzle_hash})")


def parse_chialisp23_puzzles(repo_path, puzzle_root, store, prefix, exclude=(), source_of=None):
    """Compile the .clsp files under *puzzle_root* with the modern compiler (chialisp
    package): files that start with (include *standard-cl-23*) use modules, (import a.b)
    is a file of the repo, searched from the repo root and from clsp/ (like chia-gaming's
    build.rs). A module writes one <file>[_<export>].hex next to the source for each
    export, so the repo is copied to a temporary folder first: the cached clone is not
    changed. Each export is a puzzle, named <prefix>-<folders>-<hex name>; the exports
    that are only a hash (32 bytes) are skipped. The paths in *exclude* are skipped."""
    import shutil
    import chialisp

    with tempfile.TemporaryDirectory() as tmp_dir:
        work = pathlib.Path(tmp_dir) / "repo"
        shutil.copytree(repo_path, work, ignore=shutil.ignore_patterns(".git", "node_modules", "target"))
        root = work / puzzle_root.relative_to(repo_path)
        skip = {work / p.relative_to(repo_path) for p in exclude}
        cwd = os.getcwd()
        os.chdir(work)
        try:
            for clsp in sorted(root.rglob("*.clsp")):
                if any(clsp == x or x in clsp.parents for x in skip):
                    continue
                rel = clsp.relative_to(work)
                # compiling a module also writes the .hex of the modules it imports: remove
                # this file's outputs first, so the ones found after compiling are its own
                own = lambda: set(clsp.parent.glob(clsp.stem + ".hex")) | set(clsp.parent.glob(clsp.stem + "_*.hex"))
                for old in own():
                    old.unlink()
                print(f"  processing {rel} …")
                try:
                    with tempfile.TemporaryDirectory() as out_dir:
                        out = pathlib.Path(out_dir) / "out.hex"
                        chialisp.compile_clvm(str(rel), str(out), ["clsp", "."])
                        # classic files: the program is the output; modules: the output
                        # lists the exports, written as .hex files next to the source
                        outputs = sorted(own()) or [out]
                        compiled = [(o, Program.fromhex(o.read_text().strip())) for o in outputs]
                except Exception as exc:
                    print(f"  [ERROR] skipped {rel}: {str(exc).splitlines()[-1][:200]}", file=sys.stderr)
                    continue
                folders = "-".join(rel.parent.relative_to(root.relative_to(work)).parts)
                for o, prog in compiled:
                    if prog.atom is not None and len(prog.atom) == 32:
                        continue  # <export>_hash.hex: the hash of another export
                    stem = clsp.stem if o.name == "out.hex" else o.name[:-4]
                    name = "-".join(x for x in (prefix, folders, stem) if x)
                    puzzle_hash = str(prog.get_tree_hash())
                    store[puzzle_hash] = {
                        "file_name": clsp.name,
                        "name": name,
                        "puzzle_hash": puzzle_hash,
                        "bytecode": prog.to_json_dict(),
                        "bytecode_disassembled": bu_disassemble(prog),
                        "clvm": clsp.read_text(),
                    }
                    if source_of is not None:
                        # rel is a path of the temporary copy: the same path in the clone
                        extra = {} if o.name == "out.hex" else {"export": stem}
                        store[puzzle_hash]["sources"] = [source_of(repo_path / rel, **extra)]
                    print(f"  → {name} ({puzzle_hash})")
        finally:
            os.chdir(cwd)


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


def parse_markdown_puzzles(src, repo_path, store, include_dirs, source_of=None):
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
        }
        if source_of is not None:
            store[puzzle_hash]["sources"] = [source_of(md_path, section=puzzle["section"])]
        print(f"  → {name} ({puzzle_hash})")


def git_output(repo_path: pathlib.Path, *args, text=True):
    """Output of a git command run in the clone repo_path"""
    return subprocess.run(["git", "-C", str(repo_path), *args], check=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, text=text).stdout


# the files of a commit written to a temporary folder to compile its puzzles: the .clsp files
# and the files they can include
HISTORY_SUFFIXES = (".clsp", ".clib", ".clinc")


def parse_history_puzzles(src, repo_path, store, prefix, exclude=(), source_of=None):
    """Compile every version of the .clsp files under src["subdir"] in the whole history of the
    clone, every branch and tag (see "history" in SOURCES), into *store* keyed by puzzle hash.
    - a version of a file is a puzzle hash: a commit that changes only its comments, or files
      it does not include, gives no new version. A commit is compiled in a temporary folder
      (its .clsp, .clib and .clinc files); a file is compiled again only when it or an
      include file changed
    - the version of a file at HEAD gets the name parse_puzzles gives (<prefix>-<folders>-<stem>),
      a file deleted before HEAD gives it to its last version. Its other versions are
      <name>_CHANGED_FOUND_ON_<yy_mm_dd>, the date of the first commit that has them (the
      suffix merge_into_catalog gives to a changed puzzle)
    - every file that has the puzzle hash is a source item, at the first commit that has it.
      A puzzle hash of more files (a copied or moved file) takes the name of the file where it
      is the HEAD version, else the last version of a deleted file, else an old version; among
      equals, of the file that had it last (then first)
    - a committed <file>.clsp.hex that is another puzzle is printed (the repo did not rebuild it)
    - the compiled versions are cached between runs in build/<source>_compiled.json (git-ignored,
      dropped when the compiler version changes): a run compiles only the new versions
    The paths in *exclude* (files or folders, relative to src["subdir"]) are skipped."""
    import hashlib
    import io
    import tarfile
    from importlib.metadata import version

    if git_output(repo_path, "rev-parse", "--is-shallow-repository").strip() == "true":
        raise ValueError(f"{repo_path} is a shallow clone: delete it, a history source needs the whole history")
    subdir = src.get("subdir", "").strip("/")

    compiler = f"chia-blockchain {version('chia-blockchain')}, clvm_tools_rs {version('clvm_tools_rs')}"
    cache_file = BUILD_DIR / f"{src['name']}_compiled.json"
    cache = {"compiler": compiler, "programs": {}}
    if cache_file.exists():
        with open(cache_file) as f:
            saved = json.load(f)
        if saved.get("compiler") == compiler:
            cache = saved
        else:
            print(f"  compiler changed ({saved.get('compiler')} -> {compiler}): every version is compiled again")

    def cache_key(blob, includes):
        return f"{blob}|{hashlib.sha256(json.dumps(includes).encode()).hexdigest()}"

    def save_cache():
        BUILD_DIR.mkdir(exist_ok=True)
        tmp_file = cache_file.with_name(cache_file.name + ".tmp")
        with open(tmp_file, "w") as f:
            json.dump(cache, f)
        os.replace(tmp_file, cache_file)

    def is_puzzle(path):
        if not path.endswith(".clsp") or (subdir and not path.startswith(subdir + "/")):
            return False
        rel = path[len(subdir) + 1:] if subdir else path
        return not any(rel == x or rel.startswith(x.rstrip("/") + "/") for x in exclude)

    compiled = {}       # (.clsp blob, include files) -> (puzzle hash, Program), None if it does not compile
    hex_hashes = {}     # blob of a committed .clsp.hex -> its puzzle hash
    programs = {}       # puzzle hash -> (Program, .clsp blob)
    stale_hex = set()   # (path, compiled puzzle hash, puzzle hash of the committed hex)

    def compile_commit(sha, files):
        """{path: puzzle hash} of the puzzles of a commit; files is {path: blob}"""
        includes = tuple(sorted((p, b) for p, b in files.items() if p.endswith((".clib", ".clinc"))))
        puzzles = [p for p in files if is_puzzle(p)]
        todo = []
        for p in puzzles:
            key = (files[p], includes)
            if key in compiled:
                continue
            hex_text = cache["programs"].get(cache_key(*key))  # compiled in an earlier run
            if hex_text is None:
                todo.append(p)
            else:
                prog = Program.fromhex(hex_text)
                compiled[key] = (str(prog.get_tree_hash()), prog)
        if todo:
            with tempfile.TemporaryDirectory() as tmp_dir:
                root = pathlib.Path(tmp_dir)
                paths = [p for p in files if p.endswith(HISTORY_SUFFIXES)]
                archive = git_output(repo_path, "archive", "--format=tar", sha, "--", *paths, text=False)
                with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
                    tar.extractall(root, filter="data")
                search_paths = [root / subdir] + resolve_include_dirs(src, root)
                for p in todo:
                    key = (files[p], includes)
                    if key in compiled:  # the same file in two folders
                        continue
                    print(f"  compiling {p} at {sha[:10]} …")
                    try:
                        prog = load_clvm_from_file(root / p, search_paths)
                    except Exception as exc:
                        print(f"  [ERROR] skipped {p} at {sha[:10]}: {exc}", file=sys.stderr)
                        compiled[key] = None
                        continue
                    compiled[key] = (str(prog.get_tree_hash()), prog)
                    cache["programs"][cache_key(*key)] = bytes(prog).hex()
            save_cache()  # an interrupted run keeps what it compiled
        versions = {}
        for p in puzzles:
            result = compiled[(files[p], includes)]
            if result is None:
                continue
            puzzle_hash, prog = result
            programs.setdefault(puzzle_hash, (prog, files[p]))
            versions[p] = puzzle_hash
            hex_blob = files.get(p + ".hex")
            if hex_blob is not None:
                if hex_blob not in hex_hashes:
                    try:
                        hex_text = git_output(repo_path, "cat-file", "-p", hex_blob).strip()
                        hex_hashes[hex_blob] = str(Program.fromhex(hex_text).get_tree_hash())
                    except Exception:
                        hex_hashes[hex_blob] = "(not a program)"
                if hex_hashes[hex_blob] != puzzle_hash:
                    stale_hex.add((p, puzzle_hash, hex_hashes[hex_blob]))
        return versions

    head = git_output(repo_path, "rev-parse", "HEAD").strip()
    head_versions = {}
    tree_versions = {}  # the files of a commit -> its {path: puzzle hash}
    first = {}          # (path, puzzle hash) -> (date, commit, index) of the first commit that has it
    last = {}           # (path, puzzle hash) -> index of the last commit that has it
    commits = [line.split() for line in
               git_output(repo_path, "log", "--all", "--reverse", "--date-order", "--format=%H %cs").splitlines()]
    print(f"  {len(commits)} commits")
    for index, (sha, day) in enumerate(commits):
        files = {}
        for item in git_output(repo_path, "ls-tree", "-r", "-z", sha).split("\0"):
            if item:
                meta, path = item.split("\t", 1)
                if path.endswith(HISTORY_SUFFIXES) or path.endswith(".clsp.hex"):
                    files[path] = meta.split()[2]
        tree = tuple(sorted(files.items()))
        if tree not in tree_versions:
            tree_versions[tree] = compile_commit(sha, files)
        for path, puzzle_hash in tree_versions[tree].items():
            first.setdefault((path, puzzle_hash), (day, sha, index))
            last[(path, puzzle_hash)] = index
        if sha == head:
            head_versions = tree_versions[tree]

    lineages = {}  # path -> its puzzle hashes, in the order of their first commit
    for path, puzzle_hash in first:
        lineages.setdefault(path, []).append(puzzle_hash)
    # puzzle hash -> its places, best name first: [(rank, -last index, first index, path, name, commit)]
    # rank 0: the HEAD version of a file, 1: the last version of a file deleted before HEAD, 2: an old version
    places = {}
    for path, hashes in lineages.items():
        rel = path[len(subdir) + 1:] if subdir else path
        *folders, file_name = rel.split("/")
        name = "-".join([prefix, *folders, file_name[:-len(".clsp")]])
        at_head = path in head_versions
        current = head_versions[path] if at_head else max(hashes, key=lambda h: last[(path, h)])
        used = set()
        for puzzle_hash in hashes:
            day, sha, index = first[(path, puzzle_hash)]
            version_name, rank = name, 0 if at_head else 1
            if puzzle_hash != current:
                version_name = base = f"{name}{CHANGED_SUFFIX}{day[2:].replace('-', '_')}"
                n = 2
                while version_name in used:  # changed again on the same day
                    version_name = f"{base}_{n}"
                    n += 1
                used.add(version_name)
                rank = 2
            places.setdefault(puzzle_hash, []).append(
                (rank, -last[(path, puzzle_hash)], index, path, version_name, sha))

    entries = []
    for puzzle_hash, found in places.items():
        found.sort()
        rank, _, _, path, name, sha = found[0]
        day = first[(path, puzzle_hash)][0]
        entry = {"file_name": path.split("/")[-1], "name": name, "puzzle_hash": puzzle_hash}
        if not src.get("hashes_only"):  # (the disassembly is slow)
            prog, blob = programs[puzzle_hash]
            entry.update({
                "bytecode": prog.to_json_dict(),
                "bytecode_disassembled": bu_disassemble(prog),
                "clvm": git_output(repo_path, "cat-file", "-p", blob),
            })
        if source_of is not None:
            entry["sources"] = [source_of(repo_path / p, commit=c) for _, _, _, p, _, c in found]
        entries.append(((rank < 2, day), entry))
    # the current versions last: previous_version takes the last entry of a name as the newest
    for _, entry in sorted(entries, key=lambda e: e[0]):
        store[entry["puzzle_hash"]] = entry
        print(f"  → {entry['name']} ({entry['puzzle_hash']})")
    for path, puzzle_hash, hex_hash in sorted(stale_hex):
        print(f"  [warn] committed {path}.hex is {hex_hash}, the file compiles to {puzzle_hash}",
              file=sys.stderr)
    print(f"  {len(store)} puzzle hashes from {len(lineages)} files, {len(commits)} commits")


# The combined catalog is never rewritten from scratch: the compiled puzzles are merged
# into the existing file (see merge_into_catalog), the entries already there are kept.
CATALOG_FILE = SCRIPT_DIR / "catalog" / "puzzles.json"
# the puzzles of each source, written on every run (git-ignored)
BUILD_DIR = SCRIPT_DIR / "build"


# fields of the old catalog entries that are now in "sources"
LEGACY_SOURCE_FIELDS = ("language", "markdown_section", "source")

# the code of a puzzle in a catalog entry: a "hashes_only" source (see SOURCES) does not store it
CODE_FIELDS = ("bytecode", "bytecode_disassembled", "clvm")


def merge_sources(entry: dict, new_sources: list) -> bool:
    """Add new_sources to entry["sources"]: a place already there (source_key) gets the new
    commit, a new place is added. The legacy fields go (they are in the sources now).
    Return True if the entry changed."""
    sources = [dict(s) for s in entry.get("sources", [])]
    for new in new_sources:
        same = next((s for s in sources if source_key(s) == source_key(new)), None)
        if same is None:
            sources.append(new)
        else:
            same.update(new)
    changed = sources != entry.get("sources") or any(f in entry for f in LEGACY_SOURCE_FIELDS)
    entry["sources"] = sources
    for field in LEGACY_SOURCE_FIELDS:
        entry.pop(field, None)
    return changed


def add_puzzle(store: dict, puzzle_hash: str, puzzle: dict):
    """Add a built puzzle to store. A puzzle hash built by more sources keeps all their places
    (merge_sources); the first source gives the name and the code, but an entry without code
    (a hashes_only source) gives its place to one with code"""
    old = store.get(puzzle_hash)
    if old is None:
        store[puzzle_hash] = puzzle
    elif "bytecode" not in old and "bytecode" in puzzle:
        new = dict(puzzle)
        merge_sources(new, old.get("sources", []))
        store[puzzle_hash] = new
    else:
        merge_sources(old, puzzle.get("sources", []))


# the classification fields set by hand on a puzzle (see docs/puzzles.md): they say what the
# puzzle is for, a change of its code keeps them
HAND_FIELDS = ("family", "puzzle_type", "custody", "project")
CHANGED_SUFFIX = "_CHANGED_FOUND_ON_"


def mod_parameters(source):
    """The parameters of the (mod ...) of a chialisp source, in order: the curried arguments
    are the first ones. A destructured parameter, (A B), is its text; a dotted rest ends the
    list. None when there is no (mod (...)) in the source (Rue, a chialisp-23 module, a
    hardcoded puzzle without clvm)."""
    if not source:
        return None
    tokens = [t for t in re.findall(r'"(?:[^"\\]|\\.)*"|;[^\n]*|\(|\)|[^\s()]+', source)
              if not t.startswith(";")]
    start = next((i for i in range(len(tokens) - 2)
                  if tokens[i] == "(" and tokens[i + 1] == "mod" and tokens[i + 2] == "("), None)
    if start is None:
        return None
    params, depth, current = [], 0, []
    for token in tokens[start + 2:]:
        if token == "(":
            depth += 1
            if depth > 1:
                current.append(token)
            continue
        if token == ")":
            depth -= 1
            if depth == 0:
                return params
            current.append(token)
            if depth == 1:
                params.append(" ".join(current).replace("( ", "(").replace(" )", ")"))
                current = []
            continue
        if depth == 1:
            if token == ".":
                return params
            params.append(token)
        else:
            current.append(token)
    return None  # unbalanced


def copy_hand_fields(old: dict, old_hash: str, new: dict) -> list:
    """Copy the hand fields of old (the previous version of a puzzle) to new (the version
    built from a changed source), and return the lines of the checklist printed at the end.
    - HAND_FIELDS are copied;
    - inner_arg is a position among the curried arguments, a code change can move it: it is
      copied (with inner_arg_from) only when the parameter at that position has the same
      name in the old and the new source, else it is dropped (the custody walk stops at
      this layer: CONTRACT, until it is set by hand);
    - new gets "fields_from": old_hash, the code never reads it: remove it once checked."""
    copied = [field for field in HAND_FIELDS if field in old]
    for field in copied:
        new[field] = old[field]
    lines = []
    if "inner_arg" in old:
        position = old["inner_arg"]
        name_at = lambda params: params[position - 1] if params and len(params) >= position else None
        before, after = name_at(mod_parameters(old.get("clvm"))), name_at(mod_parameters(new.get("clvm")))
        if before is not None and before == after:
            new["inner_arg"] = position
            if "inner_arg_from" in old:
                new["inner_arg_from"] = old["inner_arg_from"]
            copied.append(f"inner_arg {position} ({before})")
        else:
            lines.append(f"inner_arg {position} NOT copied: parameter {position} was {before or '(not read)'}, "
                         f"now {after or '(not read)'}: set inner_arg by hand, custody is CONTRACT until then")
    if copied:
        lines.insert(0, f"copied: {', '.join(copied)}")
    if copied or lines:
        new["fields_from"] = old_hash
        lines.insert(0, f"fields from {old['name']} ({old_hash})")
    return lines


def previous_version(catalog: dict, name: str):
    """(hash, entry) of the newest catalog entry named name or name_CHANGED_FOUND_ON_...:
    new entries are added at the end of the catalog"""
    found = None
    for puzzle_hash, entry in catalog.items():
        if entry["name"] == name or entry["name"].startswith(name + CHANGED_SUFFIX):
            found = (puzzle_hash, entry)
    return found


def merge_into_catalog(catalog: dict, new_puzzles: dict, found_date: str):
    """Add new_puzzles to catalog, nothing in catalog is deleted.
    - puzzle hash already in the catalog: only its "sources" are updated (merge_sources)
    - name already in the catalog with another puzzle hash (the source changed): added
      as a new puzzle named <name>_CHANGED_FOUND_ON_<yy_mm_dd>, with the hand fields of the
      previous version (copy_hand_fields)
    - new name: added
    Return (added, modified, skipped, sources_updated) lists of names; modified holds
    (name, checklist lines)."""
    names = {entry["name"] for entry in catalog.values()}
    added, modified, skipped, sources_updated = [], [], [], []
    for puzzle_hash, puzzle in new_puzzles.items():
        if puzzle_hash in catalog:
            skipped.append(puzzle["name"])
            if merge_sources(catalog[puzzle_hash], puzzle.get("sources", [])):
                sources_updated.append(catalog[puzzle_hash]["name"])
            continue
        puzzle = dict(puzzle)
        if puzzle["name"] in names:
            old_hash, old = previous_version(catalog, puzzle["name"])
            name = f"{puzzle['name']}{CHANGED_SUFFIX}{found_date}"
            n = 2
            while name in names:  # changed again on the same day
                name = f"{puzzle['name']}{CHANGED_SUFFIX}{found_date}_{n}"
                n += 1
            puzzle["name"] = name
            modified.append((name, copy_hand_fields(old, old_hash, puzzle)))
        else:
            added.append(puzzle["name"])
        names.add(puzzle["name"])
        catalog[puzzle_hash] = puzzle
    return added, modified, skipped, sources_updated


# Main
if __name__ == "__main__":
    all_puzzles = {}

    for src in SOURCES:
        print(f"\n=== {src['name']} ===")
        repo_path = ensure_repo(src.get("repo", src["name"]), src["url"], src.get("sparse"), src.get("ref"),
                                src.get("history", False))
        puzzle_root = get_puzzle_root(repo_path, src.get("subdir", ""))

        if not puzzle_root.exists():
            print(
                f"[SKIP] puzzle root {puzzle_root} does not exist.",
                file=sys.stderr,
            )
            continue

        repo_catalog = {}
        exclude = {puzzle_root / entry for entry in src.get("exclude", [])}
        source_of = lambda file_path, src=src, repo_path=repo_path, **extra: make_source(src, repo_path, file_path, **extra)
        if src.get("history"):
            parse_history_puzzles(src, repo_path, repo_catalog, f"--{src['name']}", src.get("exclude", []), source_of)
        elif src.get("language", "chialisp") == "rue":
            compiled_dir = repo_path / src["compiled_dir"] if "compiled_dir" in src else None
            parse_rue_puzzles(
                str(puzzle_root),
                repo_catalog,
                prefix=f"--{src['name']}",
                compiled_dir=compiled_dir,
                exclude=exclude,
                source_of=source_of,
            )
        elif src.get("language") == "chialisp-23":
            parse_chialisp23_puzzles(repo_path, puzzle_root, repo_catalog, f"--{src['name']}", exclude, source_of)
        elif "markdown_puzzles" in src:
            parse_markdown_puzzles(src, repo_path, repo_catalog, resolve_include_dirs(src, repo_path), source_of)
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
                only={puzzle_root / entry for entry in src["files"]} if "files" in src else None,
                source_of=source_of,
            )

        if src.get("hashes_only"):
            for puzzle in repo_catalog.values():
                for field in CODE_FIELDS:
                    puzzle.pop(field, None)

        BUILD_DIR.mkdir(exist_ok=True)
        out_file = BUILD_DIR / f"{src['name']}.json"
        with open(out_file, "w") as f:
            json.dump(repo_catalog, f, indent=4)
        print(f"Wrote {out_file} ({len(repo_catalog)} puzzles)")

        for puzzle_hash, puzzle in repo_catalog.items():
            add_puzzle(all_puzzles, puzzle_hash, puzzle)

    print("\n=== hardcoded ===")
    hardcoded = build_hardcoded_puzzles()
    for puzzle in hardcoded.values():
        print(f"  → {puzzle['name']} ({puzzle['puzzle_hash']})")
    for puzzle_hash, puzzle in hardcoded.items():
        add_puzzle(all_puzzles, puzzle_hash, puzzle)

    # Combined catalog (backwards-compatible name): merge into the existing file
    catalog = {}
    if CATALOG_FILE.exists():
        with open(CATALOG_FILE, "r") as f:
            catalog = json.load(f)
    count_before = len(catalog)
    added, modified, skipped, sources_updated = merge_into_catalog(catalog, all_puzzles,
                                                                   date.today().strftime("%y_%m_%d"))

    print(f"\n=== {CATALOG_FILE.name} ===")
    print(f"  already in the catalog: {len(skipped)} ({len(sources_updated)} with new or changed sources)")
    no_source = [entry["name"] for entry in catalog.values() if not entry.get("sources")]
    if no_source:
        print(f"  no source (not built by any source today): {len(no_source)}")
        for name in no_source:
            print(f"    {name}")
    for name in added:
        print(f"  [new] {name}")
    for name, _ in modified:
        print(f"  [modified source, added as new puzzle] {name}")
    # the hand fields of the changed puzzles: what to check in the catalog
    checklist = [(name, lines) for name, lines in modified if lines]
    if checklist:
        print(f"\n=== to check: hand fields of the changed puzzles ({len(checklist)}) ===")
        for name, lines in checklist:
            print(f"  {name}")
            for line in lines:
                print(f"    {line}")
        print('  remove "fields_from" from an entry once it is checked')

    if added or modified or sources_updated:
        tmp_file = CATALOG_FILE.with_name(CATALOG_FILE.name + ".tmp")
        with open(tmp_file, "w") as f:
            json.dump(catalog, f, indent=4)
        os.replace(tmp_file, CATALOG_FILE)  # a crash can not leave a truncated file
    print(f"{CATALOG_FILE.name}: {count_before} -> {len(catalog)} puzzles")
