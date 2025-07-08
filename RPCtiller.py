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
from chia.types.blockchain_format.sized_bytes import bytes32, bytes48
from chia.util.ints import uint16, uint32, uint64


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

    blockchain_state = call_rpc_node('get_blockchain_state')
    print(blockchain_state)

#rpc_functions = {}
#
## create dynamic methods
#for methods_name, outputs in rpc_call_full_node.items():
#    def rpc_func_template(*args, **kwargs):
#        return call_rpc_with_output(methods_name, outputs, *args, **kwargs)
#    rpc_func = types.FunctionType(
#        rpc_func_template.__code__,
#        globals(),
#        name=methods_name,
#        argdefs=rpc_function_template.__defaults__,
#        closure=rpc_function_template.__closure__
#    )
#
#    rpc_func.__name__ = methods_name
#    rpc_function.__doc__ = f"RPC function for method '{method_name}'"
#    rpc_functions[method_name] = rpc_function
#
#
#
#def create_rpc_call_from_name_list(names: dict, module_name: str):
#    """It creates dinamically funcions that mirror the rpc calls.
#    names: dict with the key=rpc_call name, and item=list of results to output"""
#.
#
#    # create a sub-module
#    module = types.ModuleType(module_name)
#    sys.modules[module_name] = module
#
#    functions = {}
#    for fun_name, items in names.items():
#        def _dynamic_function(*args, **kwargs):
#            """Dynamic function"""
#            rpc_result = asyncio.run(call_rpc_fetch(fun_name, kwargs))
#            # should I check for something? if success is False it should be
#            # already failed
#            if len(items) == 1:
#                return rpc_result[items[0]]
#            else:
#                return rpc_result
#
#
#        _dynamic_function.__name__ = fun_name
#        functions[fun_name] = _dynamic_function
#
#        setattr(module, fun_name, _dynamic_function)
#
#    return module
#
#
#rpc_call_full_node = {
#    "get_block_record": ["block_record"],
#    "get_block_records": ["block_records"],
#    "get_all_mempool_items": ["mempool_items"],
#    "get_routes": ["routes"]
#}
#
#
#
#
#mod = create_rpc_call_from_name_list(rpc_call_full_node, "full_node")
#
#mod.get_block_records(start=2, end=3)


