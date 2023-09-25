#!/usr/bin/env python3

import sys,os
import curses
import time

import requests
import json

sys.path.append('/home/boon/gitRepos/Chia-Py-RPC/src/')
from chia_py_rpc.wallet import Wallet
from chia_py_rpc.wallet import WalletManagement
from chia_py_rpc.wallet import KeyManagement


sys.path.append('/home/boon/gitRepos/')
import dex as dex

# first menu
## wallet
## hdd analytics
## harvester analytics
## move interface

# dexi api
def loadAllTickers():
    r = requests.get('https://api.dexie.space/v2/prices/tickers')
    tickers = json.loads(r.text)["tickers"]
    return tickers

# UI
def menu_select(stdscr, menu, select):
    for i, item in enumerate(menu):
        if select == i:
            stdscr.attron(curses.color_pair(2))
        else:
            stdscr.attron(curses.color_pair(1))
        stdscr.addstr(10 + i, 30, (str(i) + " - " + str(item)))

def menu(stdscr):
    key = 0

    stdscr.nodelay(True)
    stdscr.erase()
    stdscr.refresh()
    # trying to stop print
    #curses.noecho()
    #curses.cbreak()


    # Start colors in curses
    curses.start_color()
    curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_CYAN)

    # costant
    menu = ["Wallet", "Full node", "Harvester Analytics", "DEX", "Move plots"]
    wallet_menu = ["balance", "NFT", "cat"]
    screen = "main"
    select = 0
    active_wallet = 0
    tickers = 0
    idxFirst = 0  # defined as global for testing the dynamic menu
    selTicker = {} # do we need it global?



    pad = curses.newpad(100, 100)
    aa = 0
    bb = 0
    # try to stop flickering
    #pad.idlok(False)
    #pad.idcok(False)
    #
    #
    begin_x = 38; begin_y = 40
    height = 50; width = 20
    win = curses.newwin(height, width, begin_y, begin_x)

    # chia rpc
    Wrpc = Wallet()
    KMrpc = KeyManagement()
    WMrpc = WalletManagement()
    while key != ord('q'):
        stdscr.erase()

        height, width = stdscr.getmaxyx()

        # keyboard
        if key == ord('j'):
            select -= 1
        if key == ord('k'):
            select += 1

        # Turning on attributes for title
        stdscr.attron(curses.A_BOLD)
        if screen == "main":

            if key == curses.KEY_ENTER or key == 10 or key == 13:
                screen = menu[select]
                select = 0

            select = select % len(menu)

            menu_select(stdscr, menu, select)
            stdscr.attron(curses.color_pair(1))
            stdscr.addstr(0, 0, u'\u3042'.encode('utf-8'))
            stdscr.addstr(2, 2, u'\u1F973'.encode('utf-8'))
            stdscr.addstr(4, 4, u'\u2580'.encode('utf-8'))
            stdscr.addstr(5, 4, u'\u2581'.encode('utf-8'))
            stdscr.addstr(6, 4, u'\u2582'.encode('utf-8'))
            stdscr.addstr(7, 4, u'\u2583'.encode('utf-8'))
            stdscr.addstr(8, 4, u'\u2588'.encode('utf-8'))
            stdscr.addstr(4, 7, u'\u25C0'.encode('utf-8'))
            stdscr.addstr(4, 8, u'\u26F3'.encode('utf-8'))
            stdscr.addstr(5, 8, u'\u26A1'.encode('utf-8'))
            stdscr.addstr(8, 9, u'\U0001F331'.encode('utf-8'))
        elif screen == "Wallet":
            # select fingerprint
            if active_wallet == 0:
                fingers = []
                try:
                    fingers = KMrpc.get_public_keys()['public_key_fingerprints']
                    finger_selected = KMrpc.get_logged_in_fingerprint()['fingerprint']
                except Exception as e:
                    stdscr.addstr(0, 0, "probably there is no chia node and wallet running")
                    stdscr.addstr(1, 0, str(e))
                fingers_str = []
                for fin in fingers:
                    if fin == finger_selected:
                        fingers_str.append(str(fin) + ' >')
                    else:
                        fingers_str.append(str(fin))
                # if no chia node/wallet are active next step give an error
                # implent user message no node. Maybe finally is processed only if no exception arise
                select = select % len(fingers)
                menu_select(stdscr, fingers_str, select)

                if key == curses.KEY_ENTER or key == 10 or key == 13:
                    active_wallet = fingers[select]
                    select = 0
                    try:
                        fingers = KMrpc.log_in(active_wallet)
                    except Exception as e:
                        stdscr.addstr(0, 0, "probably there is no chia node and wallet running. KMrpc.log_in()")
                        stdscr.addstr(1, 0, str(e))
            else:
                # wallet
                raw_balance = {}
                try:
                    raw_balance = Wrpc.get_wallet_balance(1)['wallet_balance']
                except Exception as e:
                    stdscr.addstr(0, 0, "probably there is no chia node and wallet running")
                    stdscr.addstr(1, 0, str(e))

                stdscr.attron(curses.color_pair(1))
                stdscr.addstr(11, 10, 'WHAT>>>? Wallet: ' + str(active_wallet))

                y = 13
                for keyName in raw_balance:
                    name = keyName.replace('_', ' ')
                    value = str(raw_balance[keyName])
                    stdscr.addstr(y, 10, name + ' ' + value)
                    y += 1


                #    {'success': True, 'wallet_balance': {'confirmed_wallet_balance': 130, 'fingerprint': 291595168, 'max_send_amount': 130, 'pending_change': 0, 'pending_coin_removal_count': 0,
                #                                         'spendable_balance': 130, 'unconfirmed_wallet_balance': 130, 'unspent_coin_count': 3, 'wallet_id': 1, 'wallet_type': 0}
        elif screen == "DEX":
            # select pair
            if tickers == 0:
                tickers = loadAllTickers()

            stdscr.attron(curses.color_pair(1))
            stdscr.addstr(11, 10, 'WHAT>>>? ' + str(tickers[0]))

            ymin = 22
            y = ymin
            yMax = 42
            yLines = yMax - ymin
            select = select % len(tickers)
            ## idxFirst = 0  i defined as global
            idxLast = idxFirst + yLines
            if select  >= (idxLast):
                idxLast = select + 1
                idxFirst = idxLast - yLines
            elif idxFirst > select:
                idxFirst = select % len(tickers)
                idxLast = (idxFirst + yLines) % len(tickers)
            count = 0
            idTickers = range(len(tickers))
            dd = idTickers[idxFirst:idxLast]

            # define as globla
            ## selTicker = {}

            for ticker, idCount in zip(tickers[idxFirst:idxLast], idTickers[idxFirst:idxLast]):
                #print(
                #propably string func is not capable of join emoji? no because it is working on WHAT>>>>
                if idCount == select:
                    stdscr.attron(curses.color_pair(2))
                    selTicker = ticker
                else:
                    stdscr.attron(curses.color_pair(1))

                stdscr.addstr(y, 10, 'WHAT>>>? ' + str(idCount) + ' ' + ticker["base_name"] + "/" + ticker["target_name"])

                #stdscr.refresh()
                #time.sleep(1/2)
                #tickers_menu.append(ticker["base_name"] + "/" + ticker["target_name"])
                y += 1
                count += 1
                y = y % height

            stdscr.addstr(50, 10, 'WHAT>>>? ' + str(select) + ' / idxLast ' + str(idxLast) + 'idx first ' + str(idxFirst) + ' ' + str(dd))


            if key == curses.KEY_ENTER or key == 10 or key == 13:
                screen = "TradePair"
                select = 0

        elif screen == "TradePair":
            # show bid - ask - last trade
            stdscr.addstr(40, 10, 'WHAT>>>? ' + selTicker["base_name"] + "/" + selTicker["target_name"])
            stdscr.addstr(41, 10, 'WHAT>>>? ' + str(selTicker))
            ticker = dex.Ticker(selTicker)
            strOut = []
            xchPrice = 28
            try:
                dex.tickerDepth(ticker, 30, xchPrice, strOut)
            except Exception as e:
                print("exception is")
                print(e)
                print(strOut)
            strOut = '\n'.join(strOut)

            stdscr.addstr(45, 10, 'WHAT>>>? am im mie \n asdflkjadf /n aoiwsef a\n asdf \n asdf \n')
            stdscr.noutrefresh()
            win.addstr(1, 1, 'bollo bloolb llboll blb ob lbo ')
            win.addstr(2, 1, 'bollo bloolb llboll blb ob lbo ')
            win.noutrefresh()
            #
            #stdscr.addstr(0, 0, "jlkj;lkj;lkj;lkjl;kj")
            #stdscr.addstr(1, 1, strOut)
            # pad
            try:
                pad.erase()
                pad.addstr(0,0, strOut)
            except Exception as e:
                print(e)
            # These loops fill the pad with letters; addch() is
            # explained in the next section
            #for y in range(0, 99):
            #    for x in range(0, 99):
            #        pad.addch(y,x, ord('a') + (x*x+y*y) % 26)

            # Displays a section of the pad in the middle of the screen.
            # (0,0) : coordinate of upper-left corner of pad area to display.
            # (5,5) : coordinate of upper-left corner of window area to be filled
            #         with pad content.
            # (20, 75) : coordinate of lower-right corner of window area to be
            #          : filled with pad content.
            if key == curses.KEY_RIGHT:
                aa += 1
            elif key == curses.KEY_LEFT:
                aa -= 1
            elif key == curses.KEY_UP:
                bb -= 1
            elif key == curses.KEY_DOWN:
                bb += 1
            #
            pad.noutrefresh( bb,aa, 5,5, 20,75)

            # devo tovare il modo per printare delle stirnghe multi linea dalle funzioni trade.
            # Tenerle separate? o provare un modo per creare le stirnghe e poi utilizzare le funzioni
            # con un print per fare altre cose con la libreria dex?
            # usare le finestre e i pad. Provare il pad anche con il menu? Sara simile a quello
            # che ho fatto io per il menu il funzionamento di pad?
            # ultima pagina on python brave ho delle guide su windows and pads

        else:
            pass

        # html tables: https://www.w3.org/TR/xml-entity-names/026.html


        # Rendering title
        #stdscr.addstr(10, 30, "1 - Wallet")
        #stdscr.addstr(11, 30, "2 - harvester analytics")
        #stdscr.addstr(12, 30, "3 - hdd analytics")
        #stdscr.addstr(13, 30, "4 - move interface")

        curses.doupdate()
        time.sleep(30/1000)
        #stdscr.refresh()
        key = stdscr.getch()


class StdOutWrapper:
    text = ""
    def write(self,txt):
        self.text += txt
        self.text = '\n'.join(self.text.split('\n')[-300:])
    def get_text(self,beg=0,end=-1):
        """I think it is reversed the order, i should change it"""
        return '\n'.join(self.text.split('\n')[beg:end])

if __name__ == "__main__":

    screen = curses.initscr()
    curses.noecho()
    curses.cbreak()

    # do your stuff here
    # you can also output mystdout.get_text() in a ncurses widget in runtime

    screen.keypad(0)
    curses.nocbreak()
    curses.echo()
    curses.endwin()

def main():
    curses.wrapper(menu)

if __name__ == "__main__":

    mystdout = StdOutWrapper()
    sys.stdout = mystdout
    sys.stderr = mystdout
    try:
        main()
    except:
        screen.keypad(0)
        curses.nocbreak()
        curses.echo()
        curses.endwin()


    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__
    sys.stdout.write(mystdout.get_text())
