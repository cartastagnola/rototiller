import os
import pathlib
import json
import subprocess
import sys

from chia.types.blockchain_format.program import Program
from chia.wallet.puzzles.load_clvm import compile_clvm
from clvm_tools.binutils import disassemble as bu_disassemble


# Remote puzzle sources to fetch.
# Each entry maps a repo name to its Git URL and the sub-directory that
# contains the .clsp files (use "" for repo root).
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
]

# Local directory where shallow clones are cached between runs.
# Located next to this script so everything stays inside the repo tree.
# Delete this directory if you want to force a fresh download.
SCRIPT_DIR = pathlib.Path(__file__).parent.resolve()
CACHE_DIR = SCRIPT_DIR / "repo_sources"


def ensure_repo(name: str, url: str) -> pathlib.Path:
    """Shallow-clone a repo into CACHE_DIR if it isn't already cached."""
    dest = CACHE_DIR / name
    if dest.exists():
        print(f"[cache] Using existing clone: {dest}")
        return dest

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[git] Cloning {url} …")
    subprocess.run(
        ["git", "clone", "--depth", "1", url, str(dest)],
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
    hex file so the cloned repos stay clean."""
    if search_paths is None:
        search_paths = []

    full_path = pathlib.Path(clvm_path)
    parent_path = full_path.parent
    filename = full_path.name
    hex_filename = f"{filename}.hex"
    hex_path = parent_path / hex_filename

    compile_clvm(
        full_path,
        hex_path,
        search_paths=[parent_path, *search_paths],
    )

    try:
        with open(hex_path, "r", encoding="utf-8") as file:
            clvm_hex = file.read()
            clvm_blob = bytes.fromhex(clvm_hex)
    finally:
        # Remove the temporary .hex artefact so the repo tree stays clean.
        if hex_path.exists():
            hex_path.unlink()

    return Program.from_bytes(clvm_blob)


def parse_puzzles(path, store, prefix="-", puzzles_root_folder=None, include_dirs=None):
    """Recursively scan *path* for .clsp files, compile them, and store
    metadata in *store* keyed by puzzle_hash."""
    if puzzles_root_folder is None:
        puzzles_root_folder = path
    if include_dirs is None:
        include_dirs = []

    files = os.listdir(path)
    for file_name in files:
        sub_path = os.path.join(path, file_name)
        if os.path.isdir(sub_path):
            prefix_puzzle = f"{prefix}-{file_name}"
            parse_puzzles(sub_path, store, prefix_puzzle, puzzles_root_folder, include_dirs)
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


# Main
if __name__ == "__main__":
    all_puzzles = {}

    for src in SOURCES:
        print(f"\n=== {src['name']} ===")
        repo_path = ensure_repo(src["name"], src["url"])
        puzzle_root = get_puzzle_root(repo_path, src.get("subdir", ""))

        if not puzzle_root.exists():
            print(
                f"[SKIP] puzzle root {puzzle_root} does not exist.",
                file=sys.stderr,
            )
            continue

        include_dirs = find_include_dirs(repo_path)
        if include_dirs:
            print(f"  include search paths: {[str(d) for d in include_dirs]}")

        repo_catalog = {}
        parse_puzzles(
            str(puzzle_root),
            repo_catalog,
            prefix=f"--{src['name']}",
            include_dirs=include_dirs,
        )

        out_file = f"{src['name']}_puzzles.json"
        with open(out_file, "w") as f:
            json.dump(repo_catalog, f, indent=4)
        print(f"Wrote {out_file} ({len(repo_catalog)} puzzles)")

        all_puzzles.update(repo_catalog)

    # Combined catalog (backwards-compatible name)
    with open("puzzles.json", "w") as f:
        json.dump(all_puzzles, f, indent=4)
    print(f"\nCombined puzzles.json written ({len(all_puzzles)} total puzzles)")
