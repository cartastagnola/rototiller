import requests
import time
import json
import csv
import sqlite3
import traceback
import asyncio
import threading
from datetime import datetime, timedelta

import src.UTILStiller as UTILS
import src.DEXtiller as DEX
import src.WDBtiller as WDB
import src.RPCtiller as RPC
from src.CONFtiller import (
    logging, debug_logger, DB_WDB, SQL_TIMEOUT, BTC_FAKETAIL, XCH_FAKETAIL, XCH_MOJO,
    XCH_CUR, CAT_MOJO, USD_CUR)
from src.TYPEStiller import (CoinPriceData, WalletState, PkState, TransactionRecordRoto)


# dexi api
def loadAllTickers():
    r = requests.get('https://api.dexie.space/v2/prices/tickers')
    tickers = json.loads(r.text)["tickers"]
    return tickers


def write_prices(name, prices):
    name += '.csv'
    with open(name, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(['timestamps', 'value'])
        writer.writerows([[UTILS.convert_ts_to_date(key), value] for key, value in prices.items()])


def convert_historic_price_to_currency(historic_timestamp_ref_coin, historic_price_ref_coin,
                                       historic_timestamp_target_coin, historic_price_target_coin,
                                       invert_target_coin=False):
    """Convert historic price of a pair using another pair with a coin in common.
    EG:
    ref_coin= BTC_USD
    target_coin = XCH_USD
    convert the the XCH_USD pair to XCH_BTC
    """

    # TODO: set a threshold for the time diff, for which, if exceeded discard the data
    # TODO: use bisect instead of the while to find the best insertion point

    len_ref_coin_ts = len(historic_timestamp_ref_coin)
    u = 0
    new_historic_price_target_coin = []
    new_timestamps = []
    for n, i in enumerate(historic_timestamp_target_coin):
        #diff = abs(i - historic_timestamp_ref_coin[u])
        #while u < (len_ref_coin_ts - 1):
        #    next_diff = abs(i - historic_timestamp_ref_coin[u + 1])
        #    if next_diff >= diff:
        #        break
        #    u += 1

        u = UTILS.binary_search_l(historic_timestamp_ref_coin, i)
        if u >= len_ref_coin_ts - 1:
            u = len_ref_coin_ts - 1
        elif abs(i - historic_timestamp_ref_coin[u]) < abs(i - historic_timestamp_ref_coin[u + 1]):
            pass
        else:
            u += 1

        price_ref_coin = historic_price_ref_coin[u]
        if invert_target_coin:
            price_ref_coin = 1 / historic_price_ref_coin[u]

        new_historic_price_target_coin.append(historic_price_target_coin[n] * price_ref_coin)
        new_timestamps.append(historic_timestamp_target_coin[n])

    return dict(zip(new_timestamps, new_historic_price_target_coin))


def convert_historic_price_to_currency_DEB(historic_timestamp_ref_coin, historic_price_ref_coin,
                                           historic_timestamp_target_coin, historic_price_target_coin,
                                           invert_target_coin=False, name="memento"):
    """Convert historic price of a pair using another pair with a coin in common.
    EG:
    ref_coin= BTC_USD
    target_coin = XCH_USD
    convert the the XCH_USD pair to XCH_BTC
    """

    # TODO: set a threshold for the time diff, for which, if exceeded discard the data
    # TODO: use bisect instead of the while to find the best insertion point

    len_ref_coin_ts = len(historic_timestamp_ref_coin)
    u = 0
    new_historic_price_target_coin = []
    new_timestamps = []
    name += '.csv'
    with open(name, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(['target', 'target', 'ref', 'ref', 'ref', 'calculated'])
        writer.writerow(['date', 'price', 'date', 'price', 'original price', 'calculated price'])
        for n, i in enumerate(historic_timestamp_target_coin):
            u = UTILS.binary_search_l(historic_timestamp_ref_coin, i)
            if u >= len_ref_coin_ts - 1:
                u = len_ref_coin_ts - 1
            elif abs(i - historic_timestamp_ref_coin[u]) < abs(i - historic_timestamp_ref_coin[u + 1]):
                pass
            else:
                u += 1

            price_ref_coin = historic_price_ref_coin[u]
            if invert_target_coin:
                price_ref_coin = 1 / historic_price_ref_coin[u]

            new_historic_price_target_coin.append(historic_price_target_coin[n] * price_ref_coin)
            new_timestamps.append(historic_timestamp_target_coin[n])
            the_row = [UTILS.convert_ts_to_date(historic_timestamp_target_coin[n]), historic_price_target_coin[n], UTILS.convert_ts_to_date(historic_timestamp_ref_coin[u]), price_ref_coin, historic_price_ref_coin[u], historic_price_target_coin[n] * price_ref_coin]
            writer.writerow(the_row)

        writer.writerow([])
        ts = [[UTILS.convert_ts_to_date(i), 'empty'] for i in historic_timestamp_ref_coin]

        writer.writerows(ts)

    return dict(zip(new_timestamps, new_historic_price_target_coin))


# fetch coin data
def fetch_coin_data(data_lock, coins_data, tail):
    # TODO: rename fetch_cat_data
    "fetch data for a coin"

    logging(debug_logger, "DEBUG", f"fetching CAT's data with tail: {tail}")

    try:

        if tail in coins_data:
            last_update = coins_data[tail].local_timestamp
            if not last_update:
                last_update = 0
            diff = datetime.now().timestamp() * 1000 - last_update
            if diff < (60 * 1000):
                logging(debug_logger, "DEBUG", f"fetching CAT's data with tail: {tail}, already recorded")
                return

        current_price = DEX.get_current_price_from_tail(tail)
        historic_price, historic_timestamp = DEX.getHistoricPriceFromTail(tail, 7)
        end = datetime.now()
        begin = int((end - timedelta(days=7)).timestamp())
        conn = sqlite3.connect(DB_WDB, timeout=SQL_TIMEOUT)

        for price, ts in zip(historic_price, historic_timestamp):
            WDB.insert_price(conn, tail, ts, price, XCH_CUR)
        conn.close()

        if len(historic_price) == 0:
            historic_price.append(current_price)
            historic_timestamp.append(int(datetime.now().timestamp() * 1000))

        with data_lock:
            if tail not in coins_data:
                coins_data[tail] = CoinPriceData()
                coins_data[tail].tail = tail
            current_price_chia = coins_data[XCH_FAKETAIL].current_price_currency
            historic_timestamp_chia = list(coins_data[XCH_FAKETAIL].historic_price_currency.keys())
            historic_price_chia = list(coins_data[XCH_FAKETAIL].historic_price_currency.values())

            coins_data[tail].local_timestamp = datetime.now().timestamp() * 1000
            coins_data[tail].current_price = current_price
            coins_data[tail].current_price_currency = current_price * current_price_chia
            coins_data[tail].current_price_date = int(datetime.now().timestamp() * 1000)
            coins_data[tail].historic_price = dict(zip(historic_timestamp, historic_price))


            historic_price_currency = convert_historic_price_to_currency(
                historic_timestamp_chia, historic_price_chia,
                historic_timestamp, historic_price)

            coins_data[tail].historic_price_currency = historic_price_currency
            coins_data[tail].historic_range_price_data = (begin, end)

    except Exception as e:
        logging(debug_logger, "DEBUG", f"fetching coindata error {tail}")
        logging(debug_logger, "DEBUG", f"Balance error. Exception: {e}")
        logging(debug_logger, "DEBUG", f"Traceback: {traceback.format_exc()}")
        traceback.print_exc()


def fetch_btc_data(data_lock, coins_data):
    "fetch btc price"
    logging(debug_logger, "DEBUG", "fetching btc's price")

    with data_lock:
        if BTC_FAKETAIL in coins_data:
            last_update = coins_data[BTC_FAKETAIL].local_timestamp
            if not last_update:
                last_update = 0
            diff = datetime.now().timestamp() * 1000 - last_update
            if diff < (60 * 1000):
                logging(debug_logger, "DEBUG", "fetching btc's data: already in")
                return

        # retrive last 7 days
        currency = 'usd'
        days = '7'
        btc_cg_id = 'bitcoin'

        # Construct the API URL
        url = f"https://api.coingecko.com/api/v3/coins/{btc_cg_id}/market_chart?vs_currency={currency}&days={days}"

        # Send the request to CoinGecko API
        response = requests.get(url)

        # Parse the JSON response
        data = response.json()

        # Extract relevant information (e.g., prices over the last 7 days)
        prices = data['prices']
        current_price = prices[-1]
        historic_timestamp = []
        historic_price = []
        conn = sqlite3.connect(DB_WDB, timeout=SQL_TIMEOUT)
        for i in prices:
            ts = i[0]
            p = i[1]
            historic_timestamp.append(ts)
            historic_price.append(p)
            # save on the DB
            WDB.insert_price(conn, BTC_FAKETAIL, ts, p, USD_CUR)
        conn.close()

        if BTC_FAKETAIL not in coins_data:
            coins_data[BTC_FAKETAIL] = CoinPriceData()
            coins_data[BTC_FAKETAIL].tail = BTC_FAKETAIL

        coins_data[BTC_FAKETAIL].local_timestamp = datetime.now().timestamp() * 1000
        coins_data[BTC_FAKETAIL].current_price = 1
        coins_data[BTC_FAKETAIL].current_price_currency = current_price[1]
        coins_data[BTC_FAKETAIL].current_price_date = current_price[0]
        coins_data[BTC_FAKETAIL].historic_price = dict(zip(historic_timestamp,
                                                       [1] * len(historic_price)))
        coins_data[BTC_FAKETAIL].historic_price_currency = dict(zip(historic_timestamp,
                                                                historic_price))
        end = datetime.now()
        begin = int((end - timedelta(days=7)).timestamp())
        coins_data[BTC_FAKETAIL].historic_range_price_data = (begin, end)


def fetch_chia_data(data_lock, coins_data):
    "fetch data for a coin"

    logging(debug_logger, "DEBUG", "fetching chia's data")

    try:
        # lock now to be sure chia is the first entry and it is available for later entries
        with data_lock:

            chia_id = XCH_FAKETAIL

            if chia_id in coins_data:
                last_update = coins_data[chia_id].local_timestamp
                diff = datetime.now().timestamp() * 1000 - last_update
                if diff < (60 * 1000):
                    logging(debug_logger, "DEBUG", "fetching chia's data: already in")
                    return

            # retrive last 7 days
            currency = 'usd'
            days = '7'
            chia_cg_id = 'chia'

            # Construct the API URL
            url = f"https://api.coingecko.com/api/v3/coins/{chia_cg_id}/market_chart?vs_currency={currency}&days={days}"

            # Send the request to CoinGecko API
            response = requests.get(url)

            # Parse the JSON response
            data = response.json()

            # Extract relevant information (e.g., prices over the last 7 days)
            prices = data['prices']
            current_price = prices[-1]
            historic_timestamp = []
            historic_price = []
            conn = sqlite3.connect(DB_WDB, timeout=SQL_TIMEOUT)
            for i in prices:
                ts = i[0]
                p = i[1]
                historic_timestamp.append(ts)
                historic_price.append(p)
                # save on the DB
                WDB.insert_price(conn, XCH_FAKETAIL, ts, p, USD_CUR)
            conn.close()

            if chia_id not in coins_data:
                coins_data[chia_id] = CoinPriceData()
                coins_data[chia_id].tail = chia_id

            coins_data[chia_id].local_timestamp = datetime.now().timestamp() * 1000
            coins_data[chia_id].current_price = 1
            coins_data[chia_id].current_price_currency = current_price[1]
            coins_data[chia_id].current_price_date = current_price[0]
            coins_data[chia_id].historic_price = dict(zip(historic_timestamp,
                                                          [1] * len(historic_price)))
            coins_data[chia_id].historic_price_currency = dict(zip(historic_timestamp,
                                                                   historic_price))
            end = datetime.now()
            begin = int((end - timedelta(days=7)).timestamp())
            coins_data[chia_id].historic_range_price_data = (begin, end)

    except Exception as e:
        logging(debug_logger, "DEBUG", f"fetching chia coindata error from coin geko")
        logging(debug_logger, "DEBUG", f"Balance error. Exception: {e}")
        logging(debug_logger, "DEBUG", f"Traceback: {traceback.format_exc()}")
        traceback.print_exc()


def fetch_addresses(data_lock, fingerprint: int, pk_state_id: int):
    """Fetch addresses for each fingerprints until the last FREE_ADD addresses are unused"""
    ### to implement the logic to load until last 100 are unused
    conn = sqlite3.connect(DB_WDB, timeout=SQL_TIMEOUT)
    non_observer = False
    logging(debug_logger, "DEBUG", "fetching addresses from daemon")
    response = RPC.call_rpc_daemon("get_wallet_addresses", fingerprints=[fingerprint], index=0, count=1000, non_observer_derivation=non_observer)
    adds = response[str(fingerprint)]
    # pk_state_id = WDB.retrive_pk(conn, fingerprint)[0]

    for a in adds:
        WDB.insert_address(conn, pk_state_id, a['hd_path'], a['address'], non_observer)
        logging(debug_logger, "DEBUG", f"added adx with path {a['hd_path']} of finger: {fingerprint} to the db")


def load_WDB_data(conn, fingers_state, fingers_list, coins_data, finger_active):
    """Load all wallet and asset data from the db"""
    # TODO: move to DBtiller?
    #### laod key ####
    pk_states = WDB.retrive_all_pks(conn)

    for state in pk_states:
        new_pk = PkState()
        new_pk.fingerprint = state['fingerprint']
        new_pk.pk = state['public_key']
        new_pk.label = state["label"]
        fingers_list.append(new_pk.fingerprint)
        fingers_state.append(new_pk)

    #### load wallets ####

    for finger in fingers_list:

        pk_state_id = WDB.retrive_pk(conn, finger)[0]
        logging(debug_logger, "DEBUG", f"finger {finger}")
        idx = fingers_list.index(finger)
        wallets = fingers_state[idx].wallets

        db_wallets = WDB.retrive_wallets_by_pk_state_id(conn, pk_state_id)

        for db_w in db_wallets:
            tail = db_w['tail']
            mojo = CAT_MOJO
            if tail == XCH_FAKETAIL:
                mojo = XCH_MOJO
            wallet: WalletState = WalletState()
            wallet.confirmed_wallet_balance = db_w['confirmed_wallet_balance'] / mojo
            wallet.spendable_balance = db_w['spendable_balance'] / mojo
            wallet.unspent_coin_count = db_w['unspent_coin_count']
            # load asset data
            asset = WDB.retrive_asset(conn, tail)
            if asset:
                wallet.name = asset['name']
                wallet.ticker = asset['ticker']
                wallets[tail] = wallet

            #### load used tails ####
            if tail not in coins_data:
                coins_data[tail] = CoinPriceData()
                coins_data[tail].tail = tail


        # load btc prices
        tail = BTC_FAKETAIL
        coins_data[tail] = CoinPriceData()
        coins_data[tail].tail = tail
        prices = WDB.retrive_price_tail_currency(conn, tail, USD_CUR)
        if prices:
            prices = sorted(prices, key=lambda x: x[0])
            last_prices = prices[0]
            coins_data[tail].local_timestamp = last_prices[0]
            coins_data[tail].current_price_currency = last_prices[2]
            coins_data[tail].historic_price_currency = {
                timestamp: price for timestamp, _, price, _ in prices}

        # load chia prices
        tail = XCH_FAKETAIL
        prices = WDB.retrive_price_tail_currency(conn, tail, USD_CUR)
        if prices:
            prices = sorted(prices, key=lambda x: x[0])
            last_prices = prices[0]
            coins_data[tail].local_timestamp = last_prices[0]
            coins_data[tail].current_price_currency = last_prices[2]
            coins_data[tail].historic_price_currency = {
                timestamp: price for timestamp, _, price, _ in prices}

            timestamp_price_chia = last_prices[0]
            current_price_chia = last_prices[2]
            historic_timestamp_chia = list(coins_data[tail].historic_price_currency.keys())
            historic_price_chia = list(coins_data[tail].historic_price_currency.values())


        # laod CAT price data
        fifteen_minutes = 15 * 60  # CONST for limit price convertion from XCH to currency
        for tail in coins_data:
            if tail == XCH_FAKETAIL or BTC_FAKETAIL:
                continue

            # retrive CAT price in XCH
            prices = WDB.retrive_price_tail_currency(conn, tail, XCH_CUR)
            if not prices:
                continue
            prices = sorted(prices, key=lambda x: x[0])
            last_prices = prices[0]
            coins_data[tail].local_timestamp = last_prices[0]
            coins_data[tail].current_price = last_prices[2]
            #coins_data[tail].historic_price = {}
            #for p in prices:
            #    coins_data[tail].historic_price[p[0]] = p[2]
            coins_data[tail].historic_price = {
                timestamp: price for timestamp, _, price, _ in prices}

            # here i should use the convert_historic_price_to_currency function
            if abs(timestamp_price_chia - coins_data[tail].local_timestamp) > fifteen_minutes:
                coins_data[tail].current_price_currency = coins_data[tail].current_price * current_price_chia
                coins_data[tail].current_price_date = timestamp_price_chia

            historic_timestamp = list(coins_data[tail].historic_price.keys())
            historic_price = list(coins_data[tail].historic_price.values())
            historic_price_currency = convert_historic_price_to_currency(
                historic_timestamp_chia, historic_price_chia,
                historic_timestamp, historic_price)
            coins_data[tail].historic_price_currency = historic_price_currency
            #coins_data[tail].historic_price_currency = dict(zip(historic_timestamp,
            #                                                    historic_price_currency))
            begin = historic_timestamp[0]
            end = historic_timestamp[-1]
            coins_data[tail].historic_range_price_data = (begin, end)


def get_spendable_coin(wallet_id):
    """Get spendable coins by waiting for the wallet to be ready"""
    coins = False
    count = 0
    #while not coins or count == 10:
    while not coins:
        coins = asyncio.run(
            call_rpc_wallet('get_spendable_coins', wallet_id=wallet_id))
        logging(debug_logger, "DEBUG", f"Coin retrive form: {coins}")
        if not coins:
            # temp workaround about not synced wallet
            time.sleep(5)
            count += 1
            continue
        else:
            return coins["confirmed_records"]
    return False


def fetch_cat_assets():

    conn = sqlite3.connect(DB_WDB, timeout=SQL_TIMEOUT)
    last_update = WDB.retrive_table_timestamp(conn, 'asset_name')
    cats_data = None
    min_time_elapsed = 1 * 60 * 60
    now = datetime.now().timestamp()
    if (now - last_update) > min_time_elapsed:
        # insert the chia asset on
        cats_data = DEX.fetch_all_CAT_names_from_spacescan()

    if cats_data:
        for cat in cats_data:
            WDB.insert_asset(conn, cat['asset_id'], cat['name'], cat['symbol'])
        WDB.insert_table_timestamp(conn, 'asset_name')


# wallet fetcher
# TODO: finger_list: List[int] is rendundant of fingers_state, List[FingerState]
def fetch_wallet(data_lock, fingers_state, fingers_list, finger_active,
                 coins_data, count_server):
    """Fetch wallet data."""

    logging(debug_logger, "DEBUG", "wallet fetcher started.")

    while True:

        count_server[0] += 1
        logging(debug_logger, "DEBUG", f'wallet fetcher loop counting: {count_server[0]}')

        original_logged_finger = asyncio.run(RPC.call_rpc_wallet('get_logged_in_fingerprint'))['fingerprint']
        finger_active[0] = original_logged_finger

        fingerprints = []
        ######################### LOAD CAT DATA #####################
        cat_data = threading.Thread(target=fetch_cat_assets, daemon=True)
        cat_data.start()

        ######################### FINGERPRINTS LOADING ################
        try:
            logging(debug_logger, "DEBUG", f'loading fingerprints.\n\n')
            fingerprints = asyncio.run(RPC.call_rpc_wallet('get_public_keys'))
            logging(debug_logger, "DEBUG", f'fingerprints: {fingerprints}')

            if fingerprints["success"]:
                fingerprints = fingerprints["public_key_fingerprints"]
            else:
                raise ConnectionError("The rpc call failed.")

            # get logged finger -> to place on a screen variable
            #screenState.active_pk = (False, asyncio.run(call_rpc_wallet('get_logged_in_fingerprint')))
            conn = sqlite3.connect(DB_WDB, timeout=SQL_TIMEOUT)
            for finger in fingerprints:
                if finger in fingers_list:
                    continue
                else:
                    new_pk = PkState()
                    new_pk.fingerprint = finger
                    key = RPC.call_rpc_daemon("get_key", fingerprint=finger)
                    new_pk.pk = key["public_key"]
                    new_pk.label = key["label"]
                    fingers_list.append(finger)
                    fingers_state.append(new_pk)

                    # store the fingerprints
                    logging(debug_logger, "DEBUG", 'WDB insert PK starting')

                    try:
                        pk_state_id = WDB.insert_pk(conn, finger, key["label"], key["public_key"])
                    except Exception as e:
                        logging(debug_logger, "DEBUG", f'WDB insert_pk error: {e}')

                    if pk_state_id:
                        add_addresses_thread = threading.Thread(target=fetch_addresses,
                                                                args=(data_lock,
                                                                      finger,
                                                                      pk_state_id),
                                                                daemon=True)
                        add_addresses_thread.start()

                    logging(debug_logger, "DEBUG", 'WDB insert PK ended')

            logging(debug_logger, "DEBUG", 'fingerprint loading ended')
            conn.close()

        except Exception as e:
            logging(debug_logger, "DEBUG", "probably there is no chia node and wallet running")
            logging(debug_logger, "DEBUG", f"Exception: {e}")


        #################### LOAD WALLET ########################
        try:
            logging(debug_logger, "DEBUG", 'loading wallet.\n\n')

            conn = sqlite3.connect(DB_WDB, timeout=SQL_TIMEOUT)
            for finger in fingerprints:

                pk_state_id = WDB.retrive_pk(conn, finger)[0]
                logging(debug_logger, "DEBUG", f"SQL {pk_state_id}")
                logged_finger = asyncio.run(RPC.call_rpc_wallet('get_logged_in_fingerprint'))
                if logged_finger != finger:
                    result = asyncio.run(RPC.call_rpc_wallet('log_in', fingerprint=finger))

                #time.sleep(15)

                logging(debug_logger, "DEBUG", f"finger {finger}")
                logging(debug_logger, "DEBUG", f"finger list {fingers_list}")
                idx = fingers_list.index(finger)
                wallets = fingers_state[idx].wallets

                # chia wallet
                chia_wallet: WalletState = WalletState()
                chia_wallet_id = 1
                response = asyncio.run(RPC.call_rpc_wallet('get_wallet_balance', wallet_id=chia_wallet_id))
                logging(debug_logger, "DEBUG", f"rpc balance {response}")

                if response:
                    response = response["wallet_balance"]
                else:
                    raise ConnectionError("The rpc call failed.")
                    logging(debug_logger, "DEBUG", f'get balance did not get anything for the chia wallet. Finger; {finger}')
                chia_wallet.confirmed_wallet_balance = response['confirmed_wallet_balance'] / XCH_MOJO
                chia_wallet.spendable_balance = response['spendable_balance'] / XCH_MOJO
                chia_wallet.unspent_coin_count = response['unspent_coin_count']
                chia_wallet.name = "Chia"
                chia_wallet.ticker = "XCH"
                WDB.insert_wallet(conn, pk_state_id, XCH_FAKETAIL, chia_wallet)
                btc_data_thread = threading.Thread(target=fetch_btc_data,
                                                   args=(data_lock,
                                                         coins_data),
                                                   daemon=True)
                btc_data_thread.start()
                chia_data_thread = threading.Thread(target=fetch_chia_data,
                                                    args=(data_lock,
                                                          coins_data),
                                                    daemon=True)
                chia_data_thread.start()

                coins = get_spendable_coin(chia_wallet_id)
                #if coins:
                #    if len(coins) > 4:
                #        chia_wallet.coins.extend(coins[:4])
                #    else:
                #        chia_wallet.coins.extend(coins)
                chia_wallet.coins.extend(coins)
                wallets[XCH_FAKETAIL] = chia_wallet

                # add CATs
                cat_chia_wallets = asyncio.run(
                    RPC.call_rpc_wallet('get_wallets', type=6))["wallets"]

                logging(debug_logger, "DEBUG", f"chia cat wallet {cat_chia_wallets}")
                for e, i in enumerate(cat_chia_wallets):
                    cat_wallet = WalletState()
                    balance = None
                    coins = []
                    try:
                        balance = asyncio.run(
                            RPC.call_rpc_wallet('get_wallet_balance', wallet_id=i['id']))["wallet_balance"]
                        logging(debug_logger, "DEBUG", f"rpc balance for a cat {balance}")
                    except Exception as e:
                        logging(debug_logger, "DEBUG", f"Balance error. Exception: {e}")
                        logging(debug_logger, "DEBUG", f"Traceback: {traceback.format_exc()}")
                        traceback.print_exc()

                    coins = get_spendable_coin(i['id'])
                    if coins:
                        cat_wallet.coins.extend(coins)
                    else:
                        logging(debug_logger, "DEBUG", f"Error while retriving spendable coins for {i['id']} asset and for the finger")

                    try:
                        transactions = asyncio.run(RPC.call_rpc_wallet('get_transactions',
                                                                   wallet_id=i['id']))["transactions"]
                    except Exception as e:
                        logging(debug_logger, "DEBUG", f"Coin retrive error for get_transaction. Probably wallet not synced? Exception: {e}")
                        logging(debug_logger, "DEBUG", f"Traceback: {traceback.format_exc()}")
                        logging(debug_logger, "DEBUG", f"Error for the {i['id']} asset and for the finger {finger}")
                        traceback.print_exc()
                    transactions_roto = []
                    for t in transactions:
                        transactions_roto.append(TransactionRecordRoto(
                                                 t["confirmed_at_height"],
                                                 t["created_at_time"],
                                                 t["to_puzzle_hash"],
                                                 t["amount"],
                                                 t["fee_amount"],
                                                 t["confirmed"],
                                                 t["trade_id"],
                                                 t["type"],
                                                 t["name"])
                                                 )

                    try:
                        cat_wallet.transactions = transactions_roto
                    except Exception as e:
                        logging(debug_logger, "DEBUG", f"Exception: {e}")
                        logging(debug_logger, "DEBUG", f"Traceback: {traceback.format_exc()}")
                        traceback.print_exc()

                    tail = balance['asset_id']  # it is the tail...
                    cat_wallet.data = tail
                    #print(f'cata wallet data: ', cat_wallet.data)
                    cat_name_sym = DEX.fetchDexiNameFromTail(cat_wallet.data)
                    #print(f"dexi data: ", cat_name_sym)
                    # fetch prices from dexi
                    WDB.insert_asset(conn, cat_wallet.data,
                                     cat_name_sym['name'],
                                     cat_name_sym['symbol'])
                    coin_data_thread = threading.Thread(target=fetch_coin_data,
                                                        args=(data_lock,
                                                              coins_data,
                                                              cat_wallet.data),
                                                        daemon=True)
                    coin_data_thread.start()

                    cat_wallet.name = cat_name_sym['name']
                    cat_wallet.ticker = cat_name_sym['symbol']
                    cat_wallet.confirmed_wallet_balance = balance['confirmed_wallet_balance'] // CAT_MOJO
                    cat_wallet.spendable_balance = balance['spendable_balance'] // CAT_MOJO
                    cat_wallet.unspent_coin_count = balance['unspent_coin_count']
                    # bedore i was using the wallet id of the cat wallet.
                    # now i am using the cat tail
                    #wallets[i['id']] = cat_wallet
                    wallets[cat_wallet.data] = cat_wallet
                    # evaluate if it is better to use the byte32 name

                    # store
                    WDB.insert_wallet(conn, pk_state_id, tail, cat_wallet)

                # add fake coins for testing
                #cat_test = {
                #    "a628c1c2c6fcb74d53746157e438e108eab5c0bb3e5c80ff9b1910b3e4832913":
                #    ("SBX", "Spacebucks"),
                #    "db1a9020d48d9d4ad22631b66ab4b9ebd3637ef7758ad38881348c5d24c38f20":
                #    ("DBX", "dexie bucks"),
                #    "e0005928763a7253a9c443d76837bdfab312382fc47cab85dad00be23ae4e82f":
                #    ("MBX", "Moonbucks"),
                #    "b8edcc6a7cf3738a3806fdbadb1bbcfc2540ec37f6732ab3a6a4bbcd2dbec105":
                #    ("MZ", "Monkeyzoo Token"),
                #    "e816ee18ce2337c4128449bc539fbbe2ecfdd2098c4e7cab4667e223c3bdc23d":
                #    ("HOA", "HOA COIN"),
                #    "ccda69ff6c44d687994efdbee30689be51d2347f739287ab4bb7b52344f8bf1d":
                #    ("BEPE", "BEPE"),
                #    "8ebf855de6eb146db5602f0456d2f0cbe750d57f821b6f91a8592ee9f1d4cf31":
                #    ("MRMT", "Marmot Coin"),
                #    "fa4a180ac326e67ea289b869e3448256f6af05721f7cf934cb9901baa6b7a99d":
                #    ("wUSDC.b", "Base warp.green USDC"),
                #    "e233f9c0ebc092f083aaacf6295402ed0a0bb1f9acb1b56500d8a4f5a5e4c957":
                #    ("MWIF", "MWIF"),
                #    "d1adf97f603cdec4998a63eb8ffdd19480a60e20751c8ec8386283b1d86bf3f9":
                #    ("MOG", "MOG"),
                #    "4cb15a8ecc85068fb1f98c09a5e489d1ad61b2af79690ce00f9fc4803c8b597f":
                #    ("wmilliETH", "Ethereum warp.green milliETH"),
                #    "70010d83542594dd44314efbae75d82b3d9ae7d946921ed981a6cd08f0549e50":
                #    ("LOVE", "LOVE"),
                #    "a66ce97b58a748b3bb2a8224713620cca0ca00cb87e75837b1f04e3a543aaa40":
                #    ("BANANA", "BANANA"),
                #    "ec9d874e152e888231024c72e391fc484e8b6a1cf744430a322a0544e207bf46":
                #    ("PEPE", "PepeCoin"),
                #    "ea830317f831a23b178aa653e50484568d30d2c5b34d8140e71247ead05961c7":
                #    ("CC", "Caesar Coin"),
                #    "b0495abe70851d43d8444f785daa4fb2aaa8dae6312d596ee318d2b5834cc987":
                #    ("DBW", "DBW"),
                #    "509deafe3cd8bbfbb9ccce1d930e3d7b57b40c964fa33379b18d628175eb7a8f":
                #    ("CH21", "Chia Holiday 2021")
                #    }

                #for e, cat_tail in enumerate(cat_test):
                #    if cat_tail in wallets:
                #        continue
                #    cat_wallet = WalletState()
                #    balance = 999
                #    cat_wallet.data = cat_tail
                #    dexi_name = DEX.fetchDexiNameFromTail(cat_wallet.data)
                #    cat_wallet.name = dexi_name['name']
                #    cat_wallet.ticker = dexi_name['symbol']
                #    cat_wallet.confirmed_wallet_balance = 111
                #    cat_wallet.spendable_balance = 222
                #    cat_wallet.unspent_coin_count = 333
                #    wallets[cat_tail] = cat_wallet
                #    # fetch prices from dexi
                #    coin_data_thread = threading.Thread(target=fetch_coin_data,
                #                                        args=(data_lock,
                #                                              coins_data,
                #                                              cat_wallet.data),
                #                                        daemon=True)
                #    coin_data_thread.start()
                #    # evaluate if it is better to use the byte32 name

            conn.close()

            logging(debug_logger, "DEBUG", "loading wallet ended")

        except Exception as e:
            logging(debug_logger, "DEBUG", "probably there is no chia node and wallet running")
            logging(debug_logger, "DEBUG", f"Exception: {e}")
            traceback.print_exc()
            logging(debug_logger, "DEBUG", f"Traceback: {traceback.format_exc()}")

        try:
            result = asyncio.run(
                RPC.call_rpc_wallet('log_in', fingerprint=original_logged_finger))
            logging(debug_logger, "DEBUG", f"original fingerprint: {original_logged_finger}")
            logging(debug_logger, "DEBUG", f"call output log in: {result}")
            if not result:
                result = result['fingerprint']
            else:
                print("no come back")
        except Exception as e:
            logging(debug_logger, "DEBUG", "logging back to the main fingerprint")
            logging(debug_logger, "DEBUG", f"Exception: {e}")
            traceback.print_exc()
            logging(debug_logger, "DEBUG", f"Traceback: {traceback.format_exc()}")

        logging(debug_logger, "DEBUG", "begin sleep")
        time.sleep(10)
        logging(debug_logger, "DEBUG", "end sleep")


