import LOGtiller as LOG
from enum import Enum
import sqlite3


from chia.util.config import load_config
from chia.util.default_root import DEFAULT_ROOT_PATH
#from chia_rs.sized_ints import uint16, uint32, uint64, uint128

DEBUGGING = True

# LOGGING
LOGGING_LEVEL = "DEBUG"
a = LOG.LoggingLevels.INFO
server_logger = LOG.AsyncLogger("./server_log.log", LOGGING_LEVEL)
server_logger_thread = LOG.launchLoggerThread(server_logger, "hole")

ui_logger = LOG.AsyncLogger("./ui_log.log", LOGGING_LEVEL)
ui_logger_thread = LOG.launchLoggerThread(ui_logger, "pole")
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
DB_WDB = 'walletiller.db'

blockchain_db_path = config["full_node"]["database_path"].replace("CHALLENGE", chain_network)
DB_BLOCKCHAIN_RO = f"file:{blockchain_db_path}?mode=ro"

SQL_TIMEOUT = 10

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


# create a files for types or something similar
class ScopeMode(Enum):
    VISUAL = 'visual'
    INSERT = 'insert'


