import src.LOGtiller as LOG
from enum import Enum
from pathlib import Path
import json
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


# COSTANT

## database
# DB_WDB = 'walletiller.db'
DB_WDB = 'DBiller_wallets.db'
DB_SB = 'DBiller_spend_bundles.db'

blockchain_db_path = config["full_node"]["database_path"].replace("CHALLENGE", chain_network)
DB_BLOCKCHAIN_RO = f"file:{blockchain_db_path}?mode=ro"

SQL_TIMEOUT = 10

## CLMV
# load the known puzzles
KNOWN_PUZZLES_PATH = './puzzles/puzzles.json'
KNOWN_PUZZLES = None
with open(KNOWN_PUZZLES_PATH, 'r') as f:
    KNOWN_PUZZLES = json.load(f)

## memepool
TXS_MEMPOOL_DELAY = 1000  # ms

## chia tail
XCH_FAKETAIL = '0c61a'
BTC_FAKETAIL = '0b7c'

## currencies
XCH_CUR = 'XCH'
USD_CUR = 'USD'

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


