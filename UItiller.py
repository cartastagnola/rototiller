#!/usr/bin/env python3

import sys,os
import curses

def menu(stdscr):
    key = 0

    stdscr.clear()
    stdscr.refresh()

    # Start colors in curses
    curses.start_color()
    curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)


    while key != ord('q'):
        stdscr.clear()
        height, width = stdscr.getmaxyx()

        # Turning on attributes for title
        stdscr.attron(curses.color_pair(1))
        stdscr.attron(curses.A_BOLD)

        # Rendering title
        stdscr.addstr(10, 30, "hahh lkahoai hao hlakwj ")

        stdscr.refresh()
        key = stdscr.getch()


def main():
    curses.wrapper(menu)

if __name__ == "__main__":
    main()
