import sys
import types
import asyncio
import traceback

from CONFtiller import (
        server_logger, ui_logger, logging, DEBUGGING, DB_WDB,
        config, self_hostname, full_node_rpc_port, wallet_rpc_port,
        DEFAULT_ROOT_PATH)

from chia.rpc.full_node_rpc_client import FullNodeRpcClient
from chia.rpc.rpc_server import RpcServer
from chia.rpc.wallet_rpc_client import WalletRpcClient
from chia.daemon.client import connect_to_daemon_and_validate
from chia_rs.sized_bytes import bytes32, bytes48
from chia_rs.sized_ints import uint16, uint32, uint64, uint128


async def get_wallet(coin_id: str):
    try:
        full_node_client = await FullNodeRpcClient.create(
            self_hostname, uint16(full_node_rpc_port), DEFAULT_ROOT_PATH, config)
        coin_record = await full_node_client.get_coin_record_by_name(bytes32.fromhex(coin_id))
        print(coin_record)
        return coin_record.coin
    finally:
        full_node_client.close()
        await full_node_client.await_closed()


async def get_public_keys():
    try:
        wallet_client = await WalletRpcClient.create(
            self_hostname, uint16(wallet_rpc_port), DEFAULT_ROOT_PATH, config
        )
        response = await wallet_client.get_public_keys()
        return response

    finally:
        wallet_client.close()
        await wallet_client.await_closed()


async def get_logged_in_fingerprint():
    try:
        wallet_client = await WalletRpcClient.create(
            self_hostname, uint16(wallet_rpc_port), DEFAULT_ROOT_PATH, config
        )
        response = await wallet_client.get_logged_in_fingerprint()
        return response

    finally:
        wallet_client.close()
        await wallet_client.await_closed()


async def log_in(fingerprint):
    try:
        wallet_client = await WalletRpcClient.create(
            self_hostname, uint16(wallet_rpc_port), DEFAULT_ROOT_PATH, config
        )
        response = await wallet_client.log_in(fingerprint)
        return response

    finally:
        wallet_client.close()
        await wallet_client.await_closed()


async def call_rpc_wallet(method_name, *args, **kwargs):
    try:
        wallet_client = await WalletRpcClient.create(
            self_hostname, uint16(wallet_rpc_port), DEFAULT_ROOT_PATH, config
        )
        response = await wallet_client.fetch(method_name, kwargs)
        return response

    except Exception:
        logging(server_logger, "DEBUG", f"sometime wrong with a wallet rpc call.")
        logging(server_logger, "DEBUG", f"the rpc call was {str(kwargs)} and {str(args)}")
        logging(server_logger, "DEBUG", f"traceback: {traceback.format_exc()}")
        wallet_client.close()
        await wallet_client.await_closed()
        return False

    finally:
        wallet_client.close()
        await wallet_client.await_closed()


async def call_rpc_wallet_legacy(method_name, *args, **kwargs):
    try:
        wallet_client = await WalletRpcClient.create(
            self_hostname, uint16(wallet_rpc_port), DEFAULT_ROOT_PATH, config
        )
        rpc_method = getattr(wallet_client, method_name)
        response = await rpc_method(*args, **kwargs)
        return response

    finally:
        wallet_client.close()
        await wallet_client.await_closed()

# modifier for full_node rpc calls
def get_block_record():
    pass

#async def call_rpc_node(method_name, *args, **kwargs):
#    try:
#        full_node_client = await FullNodeRpcClient.create(
#            self_hostname, uint16(full_node_rpc_port), DEFAULT_ROOT_PATH, config
#        )
#        rpc_method = getattr(full_node_client, method_name)
#        response = await rpc_method(*args, **kwargs)
#        return response
#    except Exception as e:
#        print("sometime wrong with an rpc node call")
#        print(e)
#
#    finally:
#        full_node_client.close()
#        await full_node_client.await_closed()


async def fetch_rpc_daemon(method_name, *args, **kwargs):

    daemon = await connect_to_daemon_and_validate(DEFAULT_ROOT_PATH, config)

    if daemon is None:
        raise Exception("Failed to connect to chia daemon")

    try:
        request = daemon.format_request(method_name, kwargs)
        response = await daemon._get(request)
        response = response['data']
    except Exception as e:
        logging(server_logger, "DEBUG", "sometime wrong with a daemon rpc call")
        raise Exception(f"Request failed: {e}")
    finally:
        await daemon.close()
    return response


# not sure, but all the future rpc call should be done we the function below.
# there are some exception where i want to make further action before having the
# output of the rpc. Maybe i need to abstract all of them


async def fetch_rpc_node(method_name, *args, **kwargs):
    """RPC interface with the node.
    method_name= rpc call,
    then all the parameters as: block_header='0xa89...'"""
    try:
        full_node_client = await FullNodeRpcClient.create(
            self_hostname, uint16(full_node_rpc_port), DEFAULT_ROOT_PATH, config
        )
        #rpc_method = getattr(full_node_client, method_name)
        #response = await rpc_method(*args, **kwargs)
        response = await full_node_client.fetch(method_name, kwargs)
        return response
    except Exception as e:
        print(e)
        logging(server_logger, "DEBUG", "sometime wrong with a node rpc call using the fetch method")
        logging(server_logger, "DEBUG", f"the rpc call was {str(kwargs)} and {str(args)}")
        logging(server_logger, "DEBUG", f"traceback: {traceback.format_exc()}")
        return False

    finally:
        full_node_client.close()
        await full_node_client.await_closed()


async def fetch_rpc_wallet(method_name, *args, **kwargs):
    """RPC interface with the wallet.
    method_name= rpc call,
    then all the parameters as: block_header='0xa89...'"""
    try:
        wallet_client = await WalletRpcClient.create(
            self_hostname, uint16(wallet_rpc_port), DEFAULT_ROOT_PATH, config
        )
        response = await wallet_client.fetch(method_name, kwargs)
        return response

    except Exception:
        logging(server_logger, "DEBUG", f"sometime wrong with a wallet rpc call.")
        logging(server_logger, "DEBUG", f"the rpc call was {str(kwargs)} and {str(args)}")
        logging(server_logger, "DEBUG", f"traceback: {traceback.format_exc()}")
        return False

    finally:
        wallet_client.close()
        await wallet_client.await_closed()



# rpc call from list
# if the items is an empty list the output of the rpc call is unaltered
rpc_call_daemon = {
    "get_key": ["key"],
    "get_wallet_addresses": ["wallet_addresses"]
}

rpc_call_full_node = {
    "get_blockchain_state": ["blockchain_state"],
    "get_network_info": [],
    "get_block": ["block"],
    "get_blocks": ["blocks"],
    "get_block_record": ["block_record"],
    "get_block_records": ["block_records"],
    "get_all_mempool_items": ["mempool_items"],
    "get_all_mempool_tx_ids": ["tx_ids"],
    "get_routes": ["routes"],
    "get_additions_and_removals": [],
    "get_puzzle_and_solution": ["coin_solution"]
}

rpc_call_wallet = {
    "get_sync_status": [],
    "log_in": ["fingerprint"],
    "get_public_keys": ["public_key_fingerprints"],
    "get_logged_in_fingerprint": ["fingerprint"],
    "get_wallets": []
}


# refactor using the name call_rpc_node()
def call_rpc_daemon(method_name, *args, **kwargs):
    """fetch the full node with the given rpc call and filter the output.
    If the output is a single object, the 'success' is filtered out,
    if not the output remain untouched.
    Method_name: name of the method,
    then all the parameters as: block_header='0xa89...'"""

    rpc_result = asyncio.run(fetch_rpc_daemon(method_name, **kwargs))
    output_filter = rpc_call_daemon[method_name]

    if len(output_filter) == 1:
        return rpc_result[output_filter[0]]
    else:
        return rpc_result


# refactor using the name call_rpc_node()
def call_rpc_node(method_name, *args, **kwargs):
    """fetch the full node with the given rpc call and filter the output.
    If the output is a single object, the 'success' is filtered out,
    if not the output remain untouched.
    Method_name: name of the method,
    then all the parameters as: block_header='0xa89...'"""

    rpc_result = asyncio.run(fetch_rpc_node(method_name, **kwargs))
    output_filter = rpc_call_full_node[method_name]

    if len(output_filter) == 1:
        return rpc_result[output_filter[0]]
    else:
        return rpc_result


# refactor using the name call_rpc_wallet()
def call_rpc_wallet_with_output(method_name, *args, **kwargs):
    """fetch the full node with the given rpc call and filter the output.
    If the output is a single object, the 'success' is filtered out,
    if not the output remain untouched.
    Method_name: name of the method,
    then all the parameters as: block_header='0xa89...'"""

    rpc_result = asyncio.run(fetch_rpc_wallet(method_name, **kwargs))
    output_filter = rpc_call_wallet[method_name]

    if len(output_filter) == 1:
        return rpc_result[output_filter[0]]
    elif len(output_filter) == 0:
        raise
    else:
        return rpc_result


if __name__ == '__main__':

    import json
    import WDBtiller as WDB


    def print_json(dict):
        print(json.dumps(dict, sort_keys=True, indent=4))

    blockchain_state = call_rpc_node('get_blockchain_state')
    print(blockchain_state)



    raw_mempool = call_rpc_node('get_all_mempool_items')

    for tx_id, tx in raw_mempool.items():
        #print(f"tx_id: {tx_id}")
        #print_json(tx)
        mm = WDB.MempoolItem(tx_id, tx)
        print(mm)

    n = 4315872

    blocks = call_rpc_node('get_blocks', start=n, end=n+1)
    keys = blocks[0]['reward_chain_block'].keys()

    for key in keys:
        print()
        print(key)
        for b in blocks:
            print(b['reward_chain_block'][key])

    for b in blocks:
        print(b['reward_chain_block']['height'])
        print(b['reward_chain_block']['weight'])
        print(b['header_hash'])

    blocks = call_rpc_node('get_blocks', start=n, end=n+1)

    print('prev block hash')
    print(blocks[0]['foliage']['prev_block_hash'])


    n = 7311095
    blocks = call_rpc_node('get_blocks', start=n, end=n+4)

    for key in keys:
        print()
        print(key)
        for b in blocks:
            print(b['reward_chain_block'][key])

    for b in blocks:
        print(b['reward_chain_block']['height'])
        print(b['reward_chain_block']['weight'])
        print(b['header_hash'])
