import src.LOGtiller as LOG
from enum import Enum
from pathlib import Path
import json
import threading
import src.TEXTtiller as TEXT


from chia.util.config import load_config
from chia.util.default_root import DEFAULT_ROOT_PATH
#from chia_rs.sized_ints import uint16, uint32, uint64, uint128

DEBUGGING = False

# LOGGING
# logging is initialized here
# 10 MB in bytes (10 * 1024 * 1024)
log_file_max_size = 10 * 1024 * 1024
logging_level = "DEBUG"
debug_logger = LOG.AsyncLogger("debug.log", "./logs", logging_level, log_file_max_size)
debug_logger_thread = LOG.launchLoggerThread(debug_logger, "hole")
logging = LOG.logging


# CHIA RPC CONFIG
## setup the node
## config/config.yaml
config = load_config(DEFAULT_ROOT_PATH, "config.yaml")
self_hostname = config["self_hostname"]  # localhost
full_node_port = config['full_node']['port']  # "8444"
full_node_rpc_port = config["full_node"]["rpc_port"]  # 8555
wallet_rpc_port = config["wallet"]["rpc_port"]  # 9256
chain_network = config["full_node"]["selected_network"]
DAEMON_CERT = Path(DEFAULT_ROOT_PATH) / config['daemon_ssl']['private_crt']
DAEMON_KEY = Path(DEFAULT_ROOT_PATH) / config['daemon_ssl']['private_key']
DAEMON_HOST = config['ui']['daemon_host']
DAEMON_PORT = config['ui']['daemon_port']
FULL_NODE_CERT = Path(DEFAULT_ROOT_PATH) / config['full_node']['ssl']['private_crt']
FULL_NODE_KEY = Path(DEFAULT_ROOT_PATH) / config['full_node']['ssl']['private_key']


# COSTANT


## database
DB_FOLDER = Path('db')
# user DB path
USER_ADDX_WATCHLIST = Path('db/address_watchlist.csv')
# DB_WDB = 'walletiller.db'
DB_WDB = 'DBiller_wallets.db'  # TODO: rename to DB_CACHED_WALLET
DB_CACHED_BLOCKCHAIN = DB_FOLDER / 'DBiller_cached_blockchain.db'
DB_SB = 'db/DBiller_spend_bundles.db'
DB_PUZZLES = DB_FOLDER / 'DBiller_puzzles.db'

blockchain_db_path = config["full_node"]["database_path"].replace("CHALLENGE", chain_network)
# database_path in config.yaml is relative to the chia root (e.g. db/blockchain_v2_CHALLENGE.sqlite)
blockchain_db_path = str(Path(DEFAULT_ROOT_PATH) / blockchain_db_path)
DB_BLOCKCHAIN_RO = f"file:{blockchain_db_path}?mode=ro"

SQL_TIMEOUT = 10



## CLMV
# load the known puzzles
# resources/puzzles/catalog: the catalog, in the repo, read by rototiller
# resources/puzzles/puzzle_harvesting: the puzzles rototiller found that are not in the
# catalog yet, same file names and shape as the catalog, git-ignored (each user has their own)
UNKNOWN_PUZZLE = 'unknown_puzzle'
PUZZLE_CATALOG_DIR = './resources/puzzles/catalog'
PUZZLE_HARVESTING_DIR = './resources/puzzles/puzzle_harvesting'
UNKNOWN_PUZZLES_PATH = f'{PUZZLE_HARVESTING_DIR}/puzzles.json'
KNOWN_PUZZLES_PATH = f'{PUZZLE_CATALOG_DIR}/puzzles.json'
KNOWN_LAYERED_PUZZLES_PATH = f'{PUZZLE_CATALOG_DIR}/layered_puzzles.json'
PUZZLE_TYPES_PATH = f'{PUZZLE_CATALOG_DIR}/puzzle_types.json'
UNKNOWN_LAYERED_PUZZLES_PATH = f'{PUZZLE_HARVESTING_DIR}/layered_puzzles.json'

# the found puzzles were next to the catalog before (2026-11): move them once, so a user
# who updates keeps them
Path(PUZZLE_HARVESTING_DIR).mkdir(parents=True, exist_ok=True)
for _old_path, _new_path in (('./resources/puzzles/unknown_puzzles.json', UNKNOWN_PUZZLES_PATH),
                             ('./resources/puzzles/unknown_layered_puzzles.json', UNKNOWN_LAYERED_PUZZLES_PATH)):
    if Path(_old_path).exists() and not Path(_new_path).exists():
        Path(_old_path).replace(_new_path)

KNOWN_PUZZLES = None
KNOWN_LAYERED_PUZZLES = None
PUZZLE_TYPES = None
with open(KNOWN_PUZZLES_PATH, 'r') as f:
    KNOWN_PUZZLES = json.load(f)
with open(KNOWN_LAYERED_PUZZLES_PATH, 'r') as f:
    KNOWN_LAYERED_PUZZLES = json.load(f)
with open(PUZZLE_TYPES_PATH, 'r') as f:
    PUZZLE_TYPES = json.load(f)

UNKNOWN_PUZZLES = {}
if Path(UNKNOWN_PUZZLES_PATH).exists():
    with open(UNKNOWN_PUZZLES_PATH, 'r') as f:
        UNKNOWN_PUZZLES = json.load(f)
UNKNOWN_PUZZLES_LOCK = threading.Lock()

# layer combinations not named yet: with an unknown layer (unknown_layered_NN) or with
# only known layers (auto_layered_NN)
UNKNOWN_LAYERED_PUZZLES = {}
if Path(UNKNOWN_LAYERED_PUZZLES_PATH).exists():
    with open(UNKNOWN_LAYERED_PUZZLES_PATH, 'r') as f:
        UNKNOWN_LAYERED_PUZZLES = json.load(f)
UNKNOWN_LAYERED_PUZZLES_LOCK = threading.Lock()

LAYERED_PUZZLES_LOCK = threading.Lock()

## puzzle scanners
PUZZLE_SCAN_COIN_LIMIT = 10_000  # the chain scanner looks only at the last N spent coins
PUZZLE_SCAN_CHAIN_DELAY = 60  # s, wait between chain scans for new blocks
PUZZLE_SCAN_MEMPOOL_DELAY = 10  # s, wait between mempool scans
PUZZLE_SCAN_MEMPOOL_FAST_DELAY = 1  # s, wait between mempool scans while the block or mempool view is open
PUZZLE_CATALOG_WATCH_DELAY = 2  # s, check if layered_puzzles.json or puzzle_types.json were edited by hand
MEMPOOL_VALIDATED_TX_DELAY = 15  # s, validated transactions stay in the mempool view before disappearing
MEMPOOL_VALIDATED_TX_FLASH = 5  # s, validated transactions blink during the last seconds before disappearing

## chia tail
XCH_FAKETAIL = '0c61a'
BTC_FAKETAIL = '0b7c'

## currencies
XCH_CUR = 'XCH'
USD_CUR = 'USD'

## prefix
# TODO: check if we are on testnet
ADD_PREFIX = 'xch'
XCH_PREFIX = 'xch'  # REMOVE

## mojo
CAT_MOJO = 1000
XCH_MOJO = 1_000_000_000_000

## block max cost
BLOCK_MAX_COST = 11_000_000_000

# FIGLET FONTs
FIGLET = True  # EVAL: trying using a global instead of a value in screenState
# to make it working ui should import it without using FROM CONFtiller import ...

# init fingletfont
path_figlet_font = Path("resources/figlet_fonts/")
DOOM_FONT = TEXT.Font()
TEXT.loadFontFTL(path_figlet_font / "doom.flf", DOOM_FONT)

FUTURE_FONT = TEXT.Font()
TEXT.loadFontFTL(path_figlet_font / "future.tlf", FUTURE_FONT)

SMALL_FONT = TEXT.Font()
TEXT.loadFontFTL(path_figlet_font / "small.flf", SMALL_FONT)

STANDARD_FONT = TEXT.Font()
TEXT.loadFontFTL(path_figlet_font / "standard.flf", STANDARD_FONT)

SMBLOCK_FONT = TEXT.Font()
TEXT.loadFontFTL(path_figlet_font / "smblock.tlf", SMBLOCK_FONT)




# create a files for types or something similar
class ScopeMode(Enum):
    VISUAL = 'visual'
    INSERT = 'insert'


