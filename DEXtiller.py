#!/usr/bin/env python3

import time
import requests
import json
from datetime import datetime, timedelta
import math

from chia.wallet.trading.offer import Offer
from CONFtiller import XCH_MOJO, CAT_MOJO
from UTILITYtiller import print_json, parseFloatJsonValue


def dexieRequest(dexieCall):
    r = json.loads(requests.get(dexieCall).text)
    if not r['success']:
        print('The API call was  unsucessful:')
        #print(dexieCall)
        pass
    return r


def fetch_all_CAT_names_from_spacescan():
    """Fetch all CAT names from spaceScan.io"""
    # Response Schema
    # Field	Type	Description
    # status	string	Success or failure status
    # cats	array	Array of CAT objects
    # CAT Object Fields
    # Field	Type	Description
    # asset_id	string	The unique identifier of the CAT
    # token_id	string	Token ID in tkn format
    # name	string	The name of the CAT
    # description	string	Description of the CAT
    # symbol	string	Trading symbol of the CAT
    # preview_url	string	URL to the CAT's logo image
    # tags	array	Array of category tags
    # twitter	string	Twitter profile URL (null if not set)
    # discord	string	Discord server URL (null if not set)
    # website	string	Official website URL (null if not set)
    # price_xch	number	Price in XCH (only if include_price=true)

    # Construct the API URL
    url = "https://api.spacescan.io/tokens"
    # Send the request
    response = requests.get(url)
    data = response.json()

    if data['status'] == 'success':
        return data['cats']
    else:
        return None


def fetchDexiNameFromTail(tail):
    """Fetch Dexi name for Cat using its tail"""

    dexieCall = f'https://api.dexie.space/v1/offers?offered={tail}&compact=true&page_size=1'
    #dexieCall = dexieCall + f"&include_multiple_requested=false&page_size={page_size}"
    #dexieCall = dexieCall + f"&offered_type=cat&requested_type=cat&page_size={page_size}"
    r = dexieRequest(dexieCall)
    base_currency = r["offers"][0]["offered"][0]["code"]
    base_name = r["offers"][0]["offered"][0]["name"]
    return {"symbol": base_currency, 'name': base_name}


def updateTickerTicker(ticker):
    dexieCall = 'https://api.dexie.space/v2/prices/tickers?ticker_id=' + ticker.base_currency + '_' + ticker.target_currency
    r = dexieRequest(dexieCall)
    dic = r['tickers'][0]
    ticker.base_name = dic['base_name']
    ticker.target_name = dic['target_name']
    ticker.base_currency = dic['base_currency']
    ticker.target_currency = dic['target_currency']
    ticker.base_volume = parseFloatJsonValue(dic, 'base_volume')
    ticker.base_volume = parseFloatJsonValue(dic, 'target_volume')
    ticker.last_price = parseFloatJsonValue(dic, 'last_price')
    ticker.current_avg_price = parseFloatJsonValue(dic, 'current_avg_price')
    ticker.base_volume = parseFloatJsonValue(dic, 'base_volume')
    ticker.target_volume = parseFloatJsonValue(dic, 'target_volume')
    ticker.bid = parseFloatJsonValue(dic, 'bid')
    ticker.ask = parseFloatJsonValue(dic, 'ask')
    ticker.high = parseFloatJsonValue(dic, 'high')
    ticker.low = parseFloatJsonValue(dic, 'low')
    ticker.base_id = dic['base_id']
    ticker.target_id = dic['target_id']
    return dic

def updateTickerOrderbook(ticker, depth, filter_trade_ids = []):
    # temp changing of the way the order book is updated
    #dexieCall = 'https://api.dexie.space/v2/prices/orderbook?ticker_id=' + ticker.base_currency + '_' + ticker.target_currency + '&depth=' + str(depth)
    #r = dexieRequest(dexieCall)
    #ticker.orderbook = r['orderbook']
    ticker.orderbook = fetchBestTickerOffers(ticker, depth // 2)

def fetchBestTickerOffers(ticker, depth, filter_trade_ids = []):
    """Fetch the active offers for a pair and fileter the trade in the given list"""

    dexiCall_bid = f'https://api.dexie.space/v1/offers?requested={ticker.base_currency}&offered={ticker.target_currency}&page_size={depth}'
    dexiCall_ask = f'https://api.dexie.space/v1/offers?requested={ticker.target_currency}&offered={ticker.base_currency}&page_size={depth}'

    r_bid = dexieRequest(dexiCall_bid)
    r_ask = dexieRequest(dexiCall_ask)

    bids = []
    for o in r_bid['offers']:
        trade_id = str(Offer.from_bech32(o['offer']).name())
        if trade_id not in filter_trade_ids:
            offered = o['offered'][0]['amount']
            requested = o['requested'][0]['amount']
            bids.append([offered / requested, requested, trade_id])

    asks = []
    for o in r_ask['offers']:
        trade_id = str(Offer.from_bech32(o['offer']).name())
        if trade_id not in filter_trade_ids:
            offered = o['offered'][0]['amount']
            requested = o['requested'][0]['amount']
            asks.append([requested / offered, offered, trade_id])

    output = {'ticker_id' : f"{ticker.base_currency}_{ticker.target_currency}", 'timestmap' : None, 'bids' : bids, 'asks' : asks}
    return output


def downloadOffersCompleted(ticker):
    trades = []

    page_size = 100

    # buy trades
    flag = True
    dexieCall = f'https://api.dexie.space/v1/offers?status=4&requested={ticker.base_currency}&offered={ticker.target_currency}&compact=true&sort=date_completed'
    # include mutiple requested it seems not working
    #dexieCall = dexieCall + f"&include_multiple_requested=false&page_size={page_size}"
    dexieCall = dexieCall + f"&offered_type=cat&requested_type=cat&page_size={page_size}"
    print(dexieCall)
    page = 1
    while flag:
    #while False:
        call = dexieCall + f'&page={page}'
        r = dexieRequest(call)
        offers = r['offers']
        if len(offers) == 0:
            flag = False
        # test small data
        #if page == 3:
        #    flag = False

        for offer in offers:
            trade = {}
            trade['price'] = 1 / float(offer['price'])
            trade['type'] = 'buy'
            trade['base_volume'] = offer['requested'][0]['amount']
            trade['target_volume'] = offer['offered'][0]['amount']
            trade['trade_timestamp'] = datetime.strptime(offer['date_completed'], "%Y-%m-%dT%H:%M:%S.%fZ").timestamp()
            trade['trade_id'] = offer['trade_id']

            trades.append(trade)

        print(page)
        print(len(offers))
        page += 1
        time.sleep(2)

    # sell trades
    flag = True
    dexieCall = f'https://api.dexie.space/v1/offers?status=4&requested={ticker.target_currency}&offered={ticker.base_currency}&compact=true&sort=date_completed'
    dexieCall = dexieCall + f"&offered_type=cat&requested_type=cat&page_size={page_size}"
    print(dexieCall)
    page = 1
    while flag:
        call = dexieCall + f'&page={page}'
        r = dexieRequest(call)
        offers = r['offers']
        if len(offers) == 0:
            flag = False
        # test small data
        #if page == 3:
        #    flag = False

        for offer in offers:
            trade = {}
            try:
                trade['price'] = offer['price']
                trade['type'] = 'sell'
                trade['base_volume'] = offer['offered'][0]['amount']
                trade['target_volume'] = offer['requested'][0]['amount']
                trade['trade_timestamp'] = datetime.strptime(offer['date_completed'], "%Y-%m-%dT%H:%M:%S.%fZ").timestamp()
                trade['trade_id'] = offer['trade_id']
            except:
                print("offer with something wrong")
                print(offer)

            trades.append(trade)

        print(page)
        print(len(offers))

        page += 1
        time.sleep(2)

    return {"trades" : trades}

def updateTickerTradesHistory(ticker, start_time=0, end_time=0):
    '''Update the historical data of the ticker'''
    #r = requests.get('https://api.dexie.space/v2/prices/historical_trades?ticker_id=' + ticker.base_currency + '_' + ticker.target_currency + '&limit=' + str(limit))
    dexieCall = 'https://api.dexie.space/v2/prices/historical_trades?ticker_id=' + ticker.base_currency + '_' + ticker.target_currency + '&start_time=' + str(end_time)+ '&start_time=' + str(end_time)
    print(dexieCall)
    r = dexieRequest(dexieCall)

    ticker.historical_trades = r
    ticker.historical_trades_lastTimeStamp = r['timestamp']

    ### temp override of the historical trades
    ticker.historical_trades = downloadOffersCompleted(ticker)

class Ticker():
    def __init__(self, simbolBase, simbolTarget):
        #print('inside')
        #print(dic)
        self.base_name = None
        self.target_name = None
        self.base_currency = simbolBase
        self.target_currency = simbolTarget
        self.base_volume = None
        self.base_volume = None
        self.last_price = None
        self.current_avg_price = None
        self.base_volume = None
        self.target_volume = None
        self.bid = None
        self.ask = None
        self.high = None
        self.low = None
        self.base_id = None
        self.ticker = {}
        self.orderbook = {}
        self.historical_trades = {}
        updateTickerTicker(self)

    def pair(self):
        return f"{self.base_currency} {self.target_currency}"

def bestAskAndBidPrice(ticker):
    """give the best price for the bid and ask side"""
    # TODO make a loop to find the first trade that is not ours
    return float(ticker.orderbook['asks'][0][0]), float(ticker.orderbook['bids'][0][0])


def tickerTradeHistory(ticker, days_before):

    ts_now = datetime.now()
    ts_before = ts_now - timedelta(days=days_before)
    ts_before = int(ts_before.timestamp()) * 1000 # in milliseconds

    dexi_call = 'https://api.dexie.space/v2/prices/historical_trades?ticker_id=' + ticker.base_currency + '_' + ticker.target_currency + '&start_time=' + str(ts_before)
    r = dexieRequest(dexi_call)
    return r

def requestTradeHistory(simBase, simTarget, limit):
    r = requests.get('https://api.dexie.space/v2/prices/historical_trades?ticker_id=' + simBase + '_' + simTarget + '&limit=' + str(limit))
    return r

def calculatePriceFromSpread(ticker, desiredSpread, selBidAsk):
    """Calculate the price at a given spread according to a bid or an ask
    spread: the desired spread from the best bid or ask. Positive spread will give a better bid
    or ask price
    selBidAsk: str to select a bid with 'bid' or ask with 'ask'"""
    if selBidAsk == 'ask':
        refPrice = bestAskAndBidPrice(ticker)[0]
        print("ask")
        print(refPrice)
        print(refPrice * (1 - desiredSpread))
        return refPrice * (1 - desiredSpread)
    else:
        refPrice = bestAskAndBidPrice(ticker)[1]
        print("bid")
        print(refPrice)
        print(refPrice * (1 + desiredSpread))
        return refPrice * (1 + desiredSpread)


def requestTicker(simBase, simTarget):
    dexieCall = 'https://api.dexie.space/v2/prices/tickers?ticker_id=' + simBase + '_' + simTarget
    r = dexieRequest(dexieCall)
    return r['tickers'][0]


def tickerSpread(tickers, xchPrice):
    spread = (tickers.bid - tickers.ask) / tickers.current_avg_price / 100
    print(spread)
    spread = (tickers.bid - tickers.ask) / tickers.last_price / 100
    print(spread)
    print("bid ", tickers.bid)
    print("ask ", tickers.ask)
    print("price ", tickers.last_price)
    print("24h average price ", tickers.base_volume / tickers.target_volume)
    print("xch volume ", tickers.target_volume, " in $ ", tickers.target_volume * xchPrice)
    return spread


def orderOfMagnitude(price, digitsDisplayed):
    """Take a value and output its maginitude and the number of digits desidered
    when dislaying the number."""
    if price == 0:
        return 0, 0
    magnitude = (math.log10(abs(price)))
    digitsLimit = 0
    if magnitude < 0:
        magnitude = math.ceil(magnitude)
        digitsLimit = abs(magnitude) + digitsDisplayed
    else:
        magnitude = math.floor(magnitude)
        digitsLimit = digitsDisplayed - magnitude
        if digitsLimit < 0:
            digitslimit = 0
    return magnitude, digitsLimit


def roundNumberAccordingMagnitude(num):
    """Round the number according the magnitude of the number -1. It has some inconsistency,
    when < 1 the magnitude needs to be subtracted by 1, but when > 0 it has a strange behavior
    because it start working from number bigger than 100"""
    mag, digits = orderOfMagnitude(num, 4)
    roundNum = round(num, -1 * (mag - 1))
    return roundNum


def format_and_round_number(num: float, digits: int, max_digits: int):
    mag, display_digits = orderOfMagnitude(num, digits)
    if num > 1:
        if mag > digits:
            return f"{num:.{0}f}"
        else:
            return f"{num:.{digits - mag}f}"
    else:
        if display_digits > max_digits:
            return f"{num:.{digits}g}"
        else:
            return f"{num:.{display_digits}f}"


def displayOrderBook(orders, ticker, digitsTarget, digitsUSD, xchPrice, strOut = []):
    """Display bids or ask orders, their value in dollars and the cumulative depth of the orders.
    orders: bid or ask orders; ticker: the ticker of the pairs; digitsTarget: number of digits for
    the target currency; digitsUSD: number of digits for USD currentcy."""
    depthUSD = 0
    avgPrice = ticker.current_avg_price
    for i in orders:
        targetPrice = float(i[0])
        targetPriceUSD =targetPrice * xchPrice
        baseAmount = float(i[1])
        targetAmount = targetPrice * baseAmount
        targetAmountUSD = targetAmount * xchPrice
        depthUSD += targetAmountUSD

        spread = abs(avgPrice - targetPrice) / avgPrice * 100

        printOut = f"{ticker.target_currency}: {targetPrice:.{digitsTarget}f}, in USD: {targetPriceUSD:.{digitsUSD}f}. Depth: {depthUSD:.2f} Spread avg_price: {spread:.2f}"
        strOut.append(printOut)
        print(printOut)


def dexieSpreadReward(avg_price):
    """Calculate the min a max price to receive the dexie liquidity rewards."""
    max_spread = 0.05
    max_price = avg_price * (1 + max_spread)
    min_price = avg_price * (1 - max_spread)
    return min_price, max_price


def tickerDepth(ticker, depth, xchPrice, strOut=[]):
    dexieCall = 'https://api.dexie.space/v2/prices/orderbook?ticker_id=' + ticker.base_currency + '_' + ticker.target_currency + '&depth=' + str(depth)
    print(dexieCall)
    r = dexieRequest(dexieCall)
    print("dexie call")
    print(r)

    digitsPrecisionDisplayed = 4 # this logic should be added in the init, so we can retrive it every time we print
    print("avg price")
    print(ticker.current_avg_price)
    print("type")
    print(type(ticker.current_avg_price))

    priceUSD = ticker.current_avg_price * xchPrice
    magnitudeUSD, digitsUSD = orderOfMagnitude(priceUSD, digitsPrecisionDisplayed)
    magnitudeTarget, digitsTarget= orderOfMagnitude(ticker.current_avg_price, digitsPrecisionDisplayed)

    depthUSD = 0

    """ In finance, the terms "ask" and "bid" refer to the two prices at which a security can
    be bought or sold at a given point in time.
    The ASK price is the LOWEST price at which a seller is willing to SELL a security.
    The BID price is the HIGHEST price at which a buyer is willing to BUY a security."""

    printOut = "bids, buy the base"
    strOut.append(printOut)
    print(printOut)
    bids = r['orderbook']['bids']
    displayOrderBook(bids, ticker, digitsTarget, digitsUSD, xchPrice, strOut)

    printOut = "asks, sell the base"
    strOut.append(printOut)
    asks = r['orderbook']['asks']
    displayOrderBook(asks, ticker, digitsTarget, digitsUSD, xchPrice, strOut)


    return float(bids[0][0]), float(asks[0][0])


def printCurrency(value, digits):
    return f"{value:.{digits}f}"


def get_current_price_from_tail(tail: str):
    cat_name = fetchDexiNameFromTail(tail)
    ticker_cat_xch = Ticker(cat_name['symbol'], 'XCH')
    updateTickerTicker(ticker_cat_xch)
    return ticker_cat_xch.current_avg_price


def getHistoricPriceFromTail(tail: str, days: int):
    cat_name = fetchDexiNameFromTail(tail)
    ticker_cat_xch = Ticker(cat_name['symbol'], 'XCH')
    days = 7
    trade_history = tickerTradeHistory(ticker_cat_xch, days)
    #print(f"current avg price: {ticker_cat_xch.current_avg_price}")
    #print(trades_history)
    #print(f"number of trades for {days} days: {len(trade_history['trades'])}")

    # Extracting and sorting trades by timestamp
    trades = trade_history['trades']
    trades.sort(key=lambda x: x['trade_timestamp'])

    # Converting timestamps and prices
    #trade_timestamps = [datetime.utcfromtimestamp(trade['trade_timestamp'] / 1000) for trade in trades]
    trade_timestamps = [int(trade['trade_timestamp']) for trade in trades]
    trade_prices = [float(trade['price']) for trade in trades]

    return trade_prices, trade_timestamps


if '__main__' == __name__:
    print('test')
    cat_test = {
        "a628c1c2c6fcb74d53746157e438e108eab5c0bb3e5c80ff9b1910b3e4832913":
        ("SBX", "Spacebucks"),
        "db1a9020d48d9d4ad22631b66ab4b9ebd3637ef7758ad38881348c5d24c38f20":
        ("DBX", "dexie bucks"),
        "e0005928763a7253a9c443d76837bdfab312382fc47cab85dad00be23ae4e82f":
        ("MBX", "Moonbucks"),
        "b8edcc6a7cf3738a3806fdbadb1bbcfc2540ec37f6732ab3a6a4bbcd2dbec105":
        ("MZ", "Monkeyzoo Token"),
        "e816ee18ce2337c4128449bc539fbbe2ecfdd2098c4e7cab4667e223c3bdc23d":
        ("HOA", "HOA COIN"),
        "ccda69ff6c44d687994efdbee30689be51d2347f739287ab4bb7b52344f8bf1d":
        ("BEPE", "BEPE"),
        "8ebf855de6eb146db5602f0456d2f0cbe750d57f821b6f91a8592ee9f1d4cf31":
        ("MRMT", "Marmot Coin"),
        "fa4a180ac326e67ea289b869e3448256f6af05721f7cf934cb9901baa6b7a99d":
        ("wUSDC.b", "Base warp.green USDC"),
        "509deafe3cd8bbfbb9ccce1d930e3d7b57b40c964fa33379b18d628175eb7a8f":
        ("CH21", "Chia Holiday 2021")
    }

    a = fetchDexiNameFromTail("db1a9020d48d9d4ad22631b66ab4b9ebd3637ef7758ad38881348c5d24c38f20")
    print(a)
    for cat in cat_test.keys():
        a = fetchDexiNameFromTail(cat)
        print(a)
        getHistoricPriceFromTail(cat, 7)


