#!/usr/bin/env python3

import sys, os
import curses
import json
from pathlib import Path
import traceback
import copy

import time
import datetime

from dataclasses import dataclass
from typing import List, Tuple, Dict, Union

from PIL import Image

import DEXtiller as dex


def dumpJson(dic):
    """Dump the state to a JSON file"""
    with open(dicPath, 'w') as file:
        json.dump(dic, file)


def loadJson(dicJson):
    """Load the state to a JSON file"""
    with open(dicPath, 'r') as file:
        dicJson.update(json.load(file))


def remapColor(number):
    """Remap from 0-256 to 0-1000"""
    return int(number / 256 * 1000)


class CustomColors():
    """struc to store custom colors. Start idx allow to jumps the first indexes
    and preserve the default colors of curses"""

    def __init__(self, startIdx):
        self.colors = {}
        self.pairs = {}
        self.colorsIndex = startIdx
        self.pairsIndex = startIdx


def customColorsPairs_findByValue(customColors, value):
    for key, item in customColors.pairs.items():
        if item == value:
            return key
            # return ast.literal_eval(key)
    return None


def customColors_findByValue(customColors, value):
    for key, item in customColors.colors.items():
        if item == value:
            # return ast.literal_eval(key)
            return key
    return f"default_{value}"


def addCustomColor(color: Tuple[int, int, int], customColors):
    """Create a custom color and add it to an hash table with the
    tuple colors in RGB as key"""

    if not isinstance(color, tuple):
        raise ValueError('The color has to be a tuple(int, int, int)')

    if color in customColors.colors.keys():
        return customColors.colors[color]
    else:
        customColors.colorsIndex += 1
        curses.init_color(customColors.colorsIndex, remapColor(color[0]), remapColor(color[1]), remapColor(color[2]))
        customColors.colors[color] = customColors.colorsIndex
        return customColors.colorsIndex


def addCustomColorTuple(colorPair: Tuple[Tuple[int, int, int,], Tuple[int, int, int]],
                        customColors):
    """Create a custom pair of color and add it to an hash table with the tuple of the colors RGB pairs
    as key"""

    colorPair_rgb = None
    idx_color0 = None
    idx_color1 = None

    if isinstance(colorPair[0], int) and isinstance(colorPair[1], int):
        idx_color0 = colorPair[0]
        idx_color1 = colorPair[1]
        p0 = customColors_findByValue(customColors, idx_color0)
        p1 = customColors_findByValue(customColors, idx_color1)
        colorPair_rgb = (p0, p1)
    else:
        if not isinstance(colorPair, tuple):
            raise ValueError('The color pairs has to be a tuple(tuple(...), tuple(...))')
        colorPair_rgb = colorPair
        idx_color0 = customColors.colors[colorPair[0]]
        idx_color1 = customColors.colors[colorPair[1]]

    if colorPair_rgb in customColors.pairs.keys():
        return customColors.pairs[colorPair_rgb]
    else:
        customColors.pairsIndex += 1
        curses.init_pair(customColors.pairsIndex, idx_color0, idx_color1)
        index = customColors.pairsIndex
        customColors.pairs[colorPair_rgb] = index
        return index


def addCustomColorTuple_FAST(colorPair: Tuple[Tuple[int, int, int,],
                                              Tuple[int, int, int]],
                             customColors):
    addCustomColor(colorPair[0], customColors)
    addCustomColor(colorPair[1], customColors)
    idx = addCustomColorTuple(colorPair, customColors)
    return idx


class Point():
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def swapXY(self):
        a = self.x
        self.x = self.y
        self.y = a

    def deepcopy(self):
        return copy.deepcopy(self)

    def __add__(self, other):
        if not isinstance(other, Point):
            return NotImplemented
        return Point(self.x + other.x, self.y + other.y)

    def __mul__(self, other):
        if not isinstance(other, int):
            return NotImplemented
        return Point(self.x * other, self.y * other)

    def __rmul__(self, other):
        if not isinstance(other, int):
            return NotImplemented
        return Point(self.x * other, self.y * other)

    def __str__(self):
        return f"Point: x={self.x}; y={self.y}"



# help function for draw line
import math


def ipart(x):
    return math.floor(x)


def iround(x):
    return ipart(x + 0.5)


# fractional part of x
def fpart(x):
    return x - ipart(x)


def rfpart(x):
    return 1 - fpart(x)


def plot(stdscr, screenState, x, y, color):
    """color=((r,g,b), (r,g,b))"""
    color = screenState.cursesColors.pairs[color]
    stdscr.addstr(y, x, u'\u2588', curses.color_pair(color))


def colorFromBrightness(brightness, colors):
    scale = len(colors) - 1
    idx_brightness = int(brightness * scale)
    return (colors[idx_brightness], (0, 10, 45))


def drawPoint(stdscr, screenState, point0, color_pair):
    """color_pair= index of the curses color"""
    color = None
    if isinstance(color_pair, int):
        color = customColorsPairs_findByValue(screenState.cursesColors, color_pair)
    else:
        color = color_pair

    plot(stdscr, screenState, point0.x, point0.y, color)


def drawPointBox(stdscr, screenState, point0, color_pair):
    """color_pair= index of the curses color"""
    color = customColorsPairs_findByValue(screenState.cursesColors, color_pair)
    plot(stdscr, screenState, point0.x + 1, point0.y, color)
    plot(stdscr, screenState, point0.x + 1, point0.y + 1, color)
    plot(stdscr, screenState, point0.x + 1, point0.y - 1, color)
    plot(stdscr, screenState, point0.x, point0.y + 1, color)
    plot(stdscr, screenState, point0.x - 1, point0.y, color)
    plot(stdscr, screenState, point0.x - 1, point0.y - 1, color)
    plot(stdscr, screenState, point0.x - 1, point0.y + 1, color)
    plot(stdscr, screenState, point0.x, point0.y - 1, color)

def drawPoints_sub(stdscr, screenState, points, color):
    height, width = stdscr.getmaxyx()
    buffer_size = (width, height * 2)
    image_buffer = [None] * (buffer_size[0] * buffer_size[1])

    for p in points:
        image_buffer[p.x + p.y * buffer_size[0]] = color

    addSubPixel_fromDic(stdscr, screenState, image_buffer, buffer_size,
                        (255,255,255))

def addSubPixel_fromDic(stdscr, screenState, image_buffer: List[Tuple[int,int,int]],
                        buffer_size: Tuple[int,int], default_color: Tuple[int,int,int]):

    custom_colors = screenState.cursesColors
    width_buffer = buffer_size[0]
    row_char = [0] * width_buffer

    print("subpixeling")
    print(buffer_size)

    for idx, p in enumerate(image_buffer):
        row = idx // width_buffer
        col = idx % width_buffer
        #if idx > 1874:
        #    break
        if row % 2:
            if p == None and row_char[col][0] == None:
                # nothing to do
                continue

            row_char[col] = (row_char[col][0], p)
            if row_char[col][1] is None:
                row_char[col] = (row_char[col][0], default_color)
            if row_char[col][0] is None:
                row_char[col] = (default_color, row_char[col][1])

            if row_char[col] not in custom_colors.pairs.keys():
                if row_char[col][0] not in custom_colors.colors.keys():
                    addCustomColor(row_char[col][0], custom_colors)
                if row_char[col][1] not in custom_colors.colors.keys():
                    addCustomColor(row_char[col][1], custom_colors)
                addCustomColorTuple(row_char[col], custom_colors)
            colors_pair_idx = custom_colors.pairs[row_char[col]]
            stdscr.attron(curses.color_pair(colors_pair_idx))
            try:
                stdscr.addstr(idx // width_buffer // 2, idx % width_buffer, u'\u2580')
            except:
                print("boda boda")
                pass
        else:
            row_char[col] = (p, None)

def drawLine2pts_aliasing_sub(stdscr, screenState, point0, point1, color_pair):

    custom_colors = screenState.cursesColors
    point0 = Point(point0.x, point0.y * 2)
    point1 = Point(point1.x, point1.y * 2)

    #stdscr.addstr(30, 40, f"color: {color_pair}")
    try:
        coint01 = time.perf_counter()
        colors = customColorsPairs_findByValue(screenState.cursesColors, color_pair)
        #stdscr.addstr(31, 40, f"color pairs: {str(colors)}")
        color0 = colors[0]
        #stdscr.addstr(32, 40, f"color0: {str(color0)}")
        color1 = colors[1]
        color_bk = colors[1]
        #stdscr.addstr(33, 40, f"color1: {str(color1)}")
        #stdscr.addstr(34, 40, f"color: {str(curses.color_pair(color_pair))}")

        # create de gradations
        n_grad = 8
        grad = []
        diff_color = [(color0[0] - color1[0]) / n_grad,
                      (color0[1] - color1[1]) / n_grad,
                      (color0[2] - color1[2]) / n_grad]

        for i in range(n_grad + 1):
            grad.append((
                int(color1[0] + diff_color[0] * i),
                int(color1[1] + diff_color[1] * i),
                int(color1[2] + diff_color[2] * i)
                ))

        coint02 = time.perf_counter()
        #stdscr.addstr(35, 40, f"grad: {str(grad)}")
        #stdscr.addstr(36, 40, f"diff_color: {str(diff_color)}")

        # create curses colors
        try:
            for c in grad:
                color_idx = addCustomColor(c, screenState.cursesColors)
                addCustomColorTuple(
                    (color_idx,
                     color_bk),
                    screenState.cursesColors)
        except Exception as e:
            print("lie mei")
            print(e)
            traceback.print_exc()

        coint03 = time.perf_counter()
        #drawPoints_sub(stdscr, screenState, [point0], (200,200,0))
        # drawing the line
        deltaX = point1.x - point0.x
        deltaY = point1.y - point0.y

        steep = abs(deltaY) > abs(deltaX)
        if steep:
            point0.swapXY()
            point1.swapXY()
            #stdscr.addstr(42, 40, f"step: {str(steep)}, x-y swapped")
        else:
            pass
            #stdscr.addstr(42, 40, f"step: {str(steep)}")

        if point0.x > point1.x:
            temp = point0
            point0 = point1
            point1 = temp
            #stdscr.addstr(43, 40, f"points inverted")
        else:
            pass
            #stdscr.addstr(43, 40, f"points are the same")

        # already calculated delta X
        dX = point1.x - point0.x
        dY = point1.y - point0.y

        gradient = 0
        if dX == 0:
            gradient = 1
        else:
            gradient = dY / dX

        height, width = stdscr.getmaxyx()

        buffer_size = (width, height * 2)
        image_buffer = [None] * (buffer_size[0] * buffer_size[1])

        def change_pixel(buffer_size, image_buffer, x, y, color):
            image_buffer[x + y * buffer_size[0]] = color

        # first point
        x_end = iround(point0.x)
        y_end = point0.y + gradient * (x_end - point0.x)
        x_gap = rfpart(point0.x + 0.5)
        x_pixel0 = x_end
        y_pixel0 = ipart(y_end)
        #drawPoints_sub(stdscr, screenState, [Point(x_pixel0, y_pixel0)], (100,0,200))

        # the if of the shifted point is not from the original algo
        # i added it to correct some behaviour but maybe it was because
        # i used always rounded point. To investigate
        if steep:
            brightness = rfpart(y_end) * x_gap
            color = colorFromBrightness(brightness, grad)[0]
            change_pixel(buffer_size, image_buffer, y_pixel0, x_pixel0, color)

            if point1.y < point0.y:
                brightness = fpart(y_end) * x_gap
                color = colorFromBrightness(brightness, grad)[0]
                change_pixel(buffer_size, image_buffer, y_pixel0 - 1, x_pixel0, color)
            else:
                brightness = fpart(y_end) * x_gap
                color = colorFromBrightness(brightness, grad)[0]
                change_pixel(buffer_size, image_buffer, y_pixel0 + 1, x_pixel0, color)

        else:
            brightness = rfpart(y_end) * x_gap
            color = colorFromBrightness(brightness, grad)[0]
            change_pixel(buffer_size, image_buffer, x_pixel0, y_pixel0, color)

            if point1.y < point0.y:
                brightness = fpart(y_end) * x_gap
                color = colorFromBrightness(brightness, grad)[0]
                change_pixel(buffer_size, image_buffer, x_pixel0, y_pixel0 - 1, color)
            else:
                brightness = fpart(y_end) * x_gap
                color = colorFromBrightness(brightness, grad)[0]
                change_pixel(buffer_size, image_buffer, x_pixel0, y_pixel0 + 1, color)

        # first y-intersection
        intery = y_end + gradient

        # second point
        x_end = iround(point1.x)
        y_end = point1.y + gradient * (x_end - point1.x)
        x_gap = fpart(point1.x + 0.5)
        x_pixel1 = x_end
        y_pixel1 = ipart(y_end)

        if steep:
            brightness = rfpart(y_end) * x_gap
            color = colorFromBrightness(brightness, grad)[0]
            change_pixel(buffer_size, image_buffer, y_pixel1, x_pixel1, color)

            if point1.y < point0.y:
                brightness = fpart(y_end) * x_gap
                color = colorFromBrightness(brightness, grad)[0]
                change_pixel(buffer_size, image_buffer, y_pixel1 + 1, x_pixel1, color)
            else:
                brightness = fpart(y_end) * x_gap
                color = colorFromBrightness(brightness, grad)[0]
                change_pixel(buffer_size, image_buffer, y_pixel1 - 1, x_pixel1, color)

        else:
            brightness = rfpart(y_end) * x_gap
            color = colorFromBrightness(brightness, grad)[0]
            change_pixel(buffer_size, image_buffer, x_pixel1, y_pixel1, color)

            if point1.y < point0.y:
                brightness = fpart(y_end) * x_gap
                color = colorFromBrightness(brightness, grad)[0]
                change_pixel(buffer_size, image_buffer, x_pixel1, y_pixel1 + 1, color)
            else:
                brightness = fpart(y_end) * x_gap
                color = colorFromBrightness(brightness, grad)[0]
                change_pixel(buffer_size, image_buffer, x_pixel1, y_pixel1 - 1, color)

        # the loop
        coint04 = time.perf_counter()
        if steep:
            for x in range(x_pixel0 + 0, x_pixel1 - 0):
                brightness = rfpart(intery)
                color = colorFromBrightness(brightness, grad)[0]
                change_pixel(buffer_size, image_buffer, ipart(intery), x, color)

                brightness = fpart(intery)
                color = colorFromBrightness(brightness, grad)[0]
                change_pixel(buffer_size, image_buffer, ipart(intery) + 1, x, color)

                intery = intery + gradient
                #stdscr.addstr(45, 40, f"steep: {steep} and x {x}")
                #stdscr.addstr(46, 40, f"point: {point1.x}, {point1.y}")
                #stdscr.addstr(47, 40, f"point: {point0.x}, {point0.y}")
                #stdscr.addstr(48, 40, f"form: {x_pixel0 + 1}, {x_pixel1 - 1}")
        else:
            for x in range(x_pixel0 + 0, x_pixel1 - 0):
                brightness = rfpart(intery)
                color = colorFromBrightness(brightness, grad)[0]
                change_pixel(buffer_size, image_buffer, x, ipart(intery), color)

                brightness = fpart(intery)
                color = colorFromBrightness(brightness, grad)[0]
                change_pixel(buffer_size, image_buffer, x, ipart(intery) + 1, color)

                intery = intery + gradient
                #stdscr.addstr(45, 40, f"steep: {steep} and x {x} and gradient: {gradient}")
                #stdscr.addstr(46, 40, f"point: {point1.x}, {point1.y}")
                #stdscr.addstr(47, 40, f"point: {point0.x}, {point0.y}")
                #stdscr.addstr(48, 40, f"form: {x_pixel0 + 1}, {x_pixel1 - 1}")

        coint05 = time.perf_counter()
        addSubPixel_fromDic(stdscr, screenState, image_buffer,
                            buffer_size, color_bk)

        coint06 = time.perf_counter()

        print(f"gym fime 01: {coint02 - coint01}")
        print(f"gym fime 01: {coint03 - coint02}")
        print(f"gym fime 01: {coint04 - coint03}")
        print(f"gym fime 01: {coint05 - coint04}")
        print(f"gym fime 01: {coint06 - coint05}")
        # create the png
        #for idx, i in enumerate(image_buffer):
        #    if i == None:
        #        image_buffer[idx] = [240,240,240]

        #for idx, i in enumerate(image_buffer):
        #    image_buffer[idx] = (i[0],i[1],i[2])
        #
        #image = Image.new('RGB', (buffer_size[0], buffer_size[1]))
        #image.putdata(image_buffer)
        #image.save("barbo.png")

    except Exception as e:
        print("bi")
        print(e)
        traceback.print_exc()
        print(screenState.colorPairs)
        print(color_pair)
        print("curese color")
        print(screenState.cursesColors.colors)
        print(screenState.cursesColors.pairs)

        print("roto colors")
        print(screenState.colorPairs)
        print(screenState.colors)

def drawLine2pts_aliasing(stdscr, screenState, point0, point1, color_pair):

    stdscr.addstr(30, 40, f"color: {color_pair}")
    try:
        colors = customColorsPairs_findByValue(screenState.cursesColors, color_pair)
        stdscr.addstr(31, 40, f"color: {str(colors)}")
        color0 = colors[0]
        stdscr.addstr(33, 40, f"color0: {str(color0)}")
        color1 = colors[1]
        stdscr.addstr(32, 40, f"color1: {str(color1)}")
        stdscr.addstr(35, 40, f"color: {str(curses.color_pair(color_pair))}")
        print(color1)
        print(color0)

        # create de gradations
        n_grad = 8
        grad = []
        diff_color = [(color0[0] - color1[0]) / n_grad,
                      (color0[1] - color1[1]) / n_grad,
                      (color0[2] - color1[2]) / n_grad]
        for i in range(n_grad + 1):
            grad.append([
                int(color1[0] + diff_color[0] * i),
                int(color1[1] + diff_color[1] * i),
                int(color1[2] + diff_color[2] * i)
                ])

        stdscr.addstr(37, 40, f"color: {str(grad)}")
        stdscr.addstr(32, 40, f"color: {str(diff_color)}")

        # create curses colors
        try:
            for c in grad:
                color_idx = addCustomColor(c, screenState.cursesColors)
                addCustomColorTuple(
                    (color_idx,
                     screenState.colors["background"]),
                    screenState.cursesColors)
        except Exception as e:
            print("lie mei")
            print(e)
            traceback.print_exc()

        # drawing the line
        deltaX = point1.x - point0.x
        deltaY = point1.y - point0.y

        # delta incremenent
        #dX = 1
        #dY = 1
        #if deltaX < 0:
        #    dX = -1
        #if deltaY < 0:
        #    dY = -1

        steep = abs(deltaY) > abs(deltaX)
        if steep:
            point0.swapXY()
            point1.swapXY()
            stdscr.addstr(42, 40, f"step: {str(steep)}, x-y swapped")
        else:
            stdscr.addstr(42, 40, f"step: {str(steep)}")

        if point0.x > point1.x:
            temp = point0
            point0 = point1
            point1 = temp
            stdscr.addstr(43, 40, f"points inverted")
        else:
            stdscr.addstr(43, 40, f"points are the same")

        # already calculated delta X
        dX = point1.x - point0.x
        dY = point1.y - point0.y

        gradient = 0
        if dX == 0:
            gradient = 1
        else:
            gradient = dY / dX

        # first point
        x_end = iround(point0.x)
        y_end = point0.y + gradient * (x_end - point0.x)
        x_gap = rfpart(point0.x + 0.5)
        x_pixel0 = x_end
        y_pixel0 = ipart(y_end)

        # the if of the shifted point is not from the original algo
        # i added it to correct some behaviour but maybe it was because
        # i used always rounded point. To investigate
        if steep:
            brightness = rfpart(y_end) * x_gap
            color = colorFromBrightness(brightness, grad)
            plot(stdscr, screenState, y_pixel0, x_pixel0, color)

            if point1.y < point0.y:
                brightness = fpart(y_end) * x_gap
                color = colorFromBrightness(brightness, grad)
                plot(stdscr, screenState, y_pixel0 - 1, x_pixel0, color)
            else:
                brightness = fpart(y_end) * x_gap
                color = colorFromBrightness(brightness, grad)
                plot(stdscr, screenState, y_pixel0 + 1, x_pixel0, color)

        else:
            brightness = rfpart(y_end) * x_gap
            color = colorFromBrightness(brightness, grad)
            plot(stdscr, screenState, x_pixel0, y_pixel0, color)

            if point1.y < point0.y:
                brightness = fpart(y_end) * x_gap
                color = colorFromBrightness(brightness, grad)
                plot(stdscr, screenState, x_pixel0, y_pixel0 - 1, color)
            else:
                brightness = fpart(y_end) * x_gap
                color = colorFromBrightness(brightness, grad)
                plot(stdscr, screenState, x_pixel0, y_pixel0 + 1, color)

        # first y-intersection
        intery = y_end + gradient

        # second point
        x_end = iround(point1.x)
        y_end = point1.y + gradient * (x_end - point1.x)
        x_gap = fpart(point1.x + 0.5)
        x_pixel1 = x_end
        y_pixel1 = ipart(y_end)

        if steep:
            brightness = rfpart(y_end) * x_gap
            color = colorFromBrightness(brightness, grad)
            plot(stdscr, screenState, y_pixel1, x_pixel1, color)

            if point1.y < point0.y:
                brightness = fpart(y_end) * x_gap
                color = colorFromBrightness(brightness, grad)
                plot(stdscr, screenState, y_pixel1 + 1, x_pixel1, color)
            else:
                brightness = fpart(y_end) * x_gap
                color = colorFromBrightness(brightness, grad)
                plot(stdscr, screenState, y_pixel1 - 1, x_pixel1, color)

        else:
            brightness = rfpart(y_end) * x_gap
            color = colorFromBrightness(brightness, grad)
            plot(stdscr, screenState, x_pixel1, y_pixel1, color)

            if point1.y < point0.y:
                brightness = fpart(y_end) * x_gap
                color = colorFromBrightness(brightness, grad)
                plot(stdscr, screenState, x_pixel1, y_pixel1 + 1, color)
            else:
                brightness = fpart(y_end) * x_gap
                color = colorFromBrightness(brightness, grad)
                plot(stdscr, screenState, x_pixel1, y_pixel1 - 1, color)


        # the loop

        if steep:
            for x in range(x_pixel0 + 0, x_pixel1 - 0):
                brightness = rfpart(intery)
                color = colorFromBrightness(brightness, grad)
                plot(stdscr, screenState, ipart(intery), x, color)

                brightness = fpart(intery)
                color = colorFromBrightness(brightness, grad)
                plot(stdscr, screenState, ipart(intery) + 1, x, color)

                intery = intery + gradient
                stdscr.addstr(45, 40, f"steep: {steep} and x {x}")
                stdscr.addstr(46, 40, f"point: {point1.x}, {point1.y}")
                stdscr.addstr(47, 40, f"point: {point0.x}, {point0.y}")
                stdscr.addstr(48, 40, f"form: {x_pixel0 + 1}, {x_pixel1 - 1}")
        else:
            for x in range(x_pixel0 + 0, x_pixel1 - 0):
                brightness = rfpart(intery)
                color = colorFromBrightness(brightness, grad)
                plot(stdscr, screenState, x, ipart(intery), color)

                brightness = fpart(intery)
                color = colorFromBrightness(brightness, grad)
                plot(stdscr, screenState, x, ipart(intery) + 1, color)

                intery = intery + gradient
                stdscr.addstr(45, 40, f"steep: {steep} and x {x} and gradient: {gradient}")
                stdscr.addstr(46, 40, f"point: {point1.x}, {point1.y}")
                stdscr.addstr(47, 40, f"point: {point0.x}, {point0.y}")
                stdscr.addstr(48, 40, f"form: {x_pixel0 + 1}, {x_pixel1 - 1}")


    except Exception as e:
        print("bi")
        print(e)
        traceback.print_exc()
        print(screenState.colorPairs)
        print(color_pair)
        print("curese color")
        print(screenState.cursesColors.colors)
        print(screenState.cursesColors.pairs)

        print("roto colors")
        print(screenState.colorPairs)
        print(screenState.colors)



def drawLine2pts(stdscr, point1, point2):
    stdscr.addstr(point1.y, point1.x, u'\u2588')
    stdscr.addstr(point2.y, point2.x, u'\u2588')
                    # the top and the bottom of the body
                    #fullBlock = u'\u2588'
                    #halfUpperBlock = u'\u2580'
                    #halfLowerBlock = u'\u2584'

    # Bresenham algo
    # slope = rise / run = deltaY / deltaX
    deltaX = point2.x - point1.x
    deltaY = point2.y - point1.y

    # delta incremenent
    dX = 1
    dY = 1
    if deltaX < 0:
        dX = -1
    if deltaY < 0:
        dY = -1

    # first pixel
    X = point1.x
    Y = point1.y

    stdscr.addstr(20, 20, f"dwf; {dY}")

    deltaX = abs(deltaX)
    deltaY = abs(deltaY)

    if deltaY < deltaX:
        # P decision parameter
        P = 2 * deltaY - deltaX
        for i in range(deltaX):
            if P >= 0:
                P = P + 2 * deltaY - 2 * deltaX
                X += dX
                Y += dY
                stdscr.addstr(Y, X, u'\u2588')
            else:
                P = P + 2 * deltaY
                X += dX
                stdscr.addstr(Y, X, u'\u2588')
    else:
        P = 2 * deltaX - deltaY
        for i in range(deltaY):
            if P >= 0:
                P = P + 2 * deltaX - 2 * deltaY
                X += dX
                Y += dY
                stdscr.addstr(Y, X, u'\u2588')
            else:
                P = P + 2 * deltaX
                Y += dY
                stdscr.addstr(Y, X, u'\u2588')


def drawLine2pts_subpixel(stdscr, point1, point2):
                    # the top and the bottom of the body
                    #fullBlock = u'\u2588'
                    #halfUpperBlock = u'\u2580'
                    #halfLowerBlock = u'\u2584'


    # Bresenham algo
    # slope = rise / run = deltaY / deltaX
    stdscr.addstr(2, 5, f"point2 pre; {point1.x}, {point1.y}")
    stdscr.addstr(3, 5, f"point2 pre; {point2.x}, {point2.y}")
    #point2 = Point(point2.x, point2.y * 2)
    deltaX = point2.x - point1.x
    deltaY = point2.y - point1.y
    deltaY = deltaY * 2
    stdscr.addstr(4, 5, f"point2 pre; {point2.x}, {point2.y}")

    # delta
    dX = 0
    dY = 0
    # delta of the delta incremenent... waooo
    ddX = 1
    ddY = 1
    if deltaX < 0:
        ddX = -1
    if deltaY < 0:
        ddY = -1

    # first pixel
    X = point1.x
    Y = point1.y

    pixelComposer = {} # [(coordinate point):(color_pairs)] default color is all background

    stdscr.addstr(20, 20, f"dwf; {dY}")

    deltaX = abs(deltaX)
    deltaY = abs(deltaY)

    if deltaY < deltaX:
        stdscr.addstr(point1.y, point1.x, u'\u2580')
        stdscr.addstr(point2.y, point2.x, u'\u2580')
        # P decision parameter
        P = 2 * deltaY - deltaX
        for i in range(deltaX - 1):
            if P >= 0:
                P = P + 2 * deltaY - 2 * deltaX
                dX += ddX
                dY += ddY
                if dY % 2:
                    cc = (dX, (dY-1)//2)
                    if cc not in pixelComposer.keys():
                        pixelComposer[cc] = (1, 0)
                        stdscr.addstr(Y + cc[1], X + cc[0], u'\u2584')
                    else:
                        pixelComposer[cc] = (1, 1)
                        stdscr.addstr(Y + cc[1], X + cc[0], u'\u2588')
                else:
                    cc = (dX, dY//2)
                    if cc not in pixelComposer.keys():
                        pixelComposer[cc] = (0, 1)
                        stdscr.addstr(Y + cc[1], X + cc[0], u'\u2580')
                    else:
                        pixelComposer[cc] = (1, 1)
                        stdscr.addstr(Y + cc[1], X + cc[0], u'\u2588')
            else:
                P = P + 2 * deltaY
                dX += ddX
                if dY % 2:
                    cc = (dX, (dY-1)//2)
                    if cc not in pixelComposer.keys():
                        pixelComposer[cc] = (1, 0)
                        stdscr.addstr(Y + cc[1], X + cc[0], u'\u2584')
                    else:
                        pixelComposer[cc] = (1, 1)
                        stdscr.addstr(Y + cc[1], X + cc[0], u'\u2588')
                else:
                    cc = (dX, dY//2)
                    if cc not in pixelComposer.keys():
                        pixelComposer[cc] = (0, 1)
                        stdscr.addstr(Y + cc[1], X + cc[0], u'\u2580')
                    else:
                        pixelComposer[cc] = (1, 1)
                        stdscr.addstr(Y + cc[1], X + cc[0], u'\u2588')
    else:
        stdscr.addstr(point1.y, point1.x, u'\u2580')
        stdscr.addstr(point2.y, point2.x, u'\u2580')
        P = 2 * deltaX - deltaY
        for i in range(deltaY):
            if P >= 0:
                P = P + 2 * deltaX - 2 * deltaY
                dX += ddX
                dY += ddY
                if dY % 2:
                    cc = (dX, (dY-1)//2)
                    if cc not in pixelComposer.keys():
                        pixelComposer[cc] = (1, 0)
                        stdscr.addstr(Y + cc[1], X + cc[0], u'\u2584')
                    else:
                        pixelComposer[cc] = (1, 1)
                        stdscr.addstr(Y + cc[1], X + cc[0], u'\u2588')
                else:
                    cc = (dX, dY//2)
                    if cc not in pixelComposer.keys():
                        pixelComposer[cc] = (0, 1)
                        stdscr.addstr(Y + cc[1], X + cc[0], u'\u2580')
                    else:
                        pixelComposer[cc] = (1, 1)
                        stdscr.addstr(Y + cc[1], X + cc[0], u'\u2588')
            else:
                P = P + 2 * deltaX
                dY += ddY
                if dY % 2:
                    cc = (dX, (dY-1)//2)
                    if cc not in pixelComposer.keys():
                        pixelComposer[cc] = (1, 0)
                        stdscr.addstr(Y + cc[1], X + cc[0], u'\u2584')
                    else:
                        pixelComposer[cc] = (1, 1)
                        stdscr.addstr(Y + cc[1], X + cc[0], u'\u2588')
                else:
                    cc = (dX, dY//2)
                    if cc not in pixelComposer.keys():
                        pixelComposer[cc] = (0, 1)
                        stdscr.addstr(Y + cc[1], X + cc[0], u'\u2580')
                    else:
                        pixelComposer[cc] = (1, 1)
                        stdscr.addstr(Y + cc[1], X + cc[0], u'\u2588')


def drawPriceGraph(stdscr, screenState, data_prices, data_timestamps, days, P_color=None):
    """data_prices: list of prices; data_timestamps: list of timestamps refered to the prices
    days: number of days of the graph"""
    coint01 = time.perf_counter()
    points_per_day = 3
    total_points = days * points_per_day
    height, width = stdscr.getmaxyx()
    end = int(time.time()) * 1000  # * 1000 not needed useing history from offers
    start = end - int(datetime.timedelta(days=days).total_seconds()) * 1000
    end_price = data_prices[-1]
    start_price = data_prices[0]
    unit_time = datetime.timedelta(days=1).total_seconds() * 1000 / points_per_day

    # divde data per unit
    # at the moment it keeps one price for unit time
    time_group = {}
    for p, t in zip(data_prices, data_timestamps):
        time_group[(t - start) // unit_time] = p

    min_price = min(data_prices)
    max_price = max(data_prices)
    delta_price = max_price - min_price
    unit_price = 1
    if delta_price != 0:
        unit_price = (height - 1) / delta_price

    coint02 = time.perf_counter()

    if width < days:
        print("do not compute")
        pass

    else:
        print(f"len(time_gorup): {len(time_group)} and width: {width}")
        if len(time_group) > width:
            print("do not compute")
        else:
            print("hei: ", unit_price, ' ', height)
            pixel_shift = width / total_points
            # draw the first and the last point
            line_points = [Point(1, int((start_price - min_price) * unit_price))]
            for n, i in enumerate(time_group):
                #avg = sum / len(time_group[i])
                avg = time_group[i]
                y = round((avg - min_price) * unit_price)
                x = round(i * pixel_shift)
                # handle a curses exception
                if x >= (width - 1) and y >= (height - 1):
                    x -= 1
                    y -= 1
                line_points.append(Point(x, y))
            last_price = int((end_price - min_price) * unit_price)
            if last_price >= height - 1:
                last_price -= 1
            line_points.append(Point(width - 1, last_price))
            # ok, now you can test by drawing points
            for p in line_points:
                print(p)
            coint03 = time.perf_counter()

            color_pair = ((255, 0, 255), (1, 1, 1))
            color_pair_idx = addCustomColorTuple_FAST(color_pair, screenState.cursesColors)
            if P_color is not None:
                color_pair_idx = P_color
            point0 = line_points[0]
            for i in range(1, len(line_points)):
                point1 = line_points[i]
                print("color type")
                print(color_pair)
                drawLine2pts_aliasing_sub(stdscr, screenState, point0, point1, color_pair_idx)
                point0 = point1

            coint04 = time.perf_counter()
            print(f"fime 01: {coint02 - coint01}")
            print(f"fime 01: {coint03 - coint02}")
            print(f"fime 01: {coint04 - coint03}")
            #for p in line_points:
            #    point0 = p
            #    color_pair = ((255, 255, 255), (100, 255, 200))
            #    addCustomColorTuple_FAST(color_pair, screenState.cursesColors)
            #    print("hei: ", unit_price, ' ', height)
            #    drawPoint(stdscr, screenState, point0, color_pair)

            #stdscr.addstr(2, 10, f"time group len: {len(time_group)} and point per day {total_points}", 12)
            #stdscr.addstr(12, 10, f"berto",12)


class Candle:
    """Store the open, close, min and max price of a candle"""
    def __init__(self):
        self.open = 0
        self.close = 0
        self.max = 0
        self.min = 0
        self.base_volume = 0
        self.target_volume = 0
        self.target_volume_buy = 0
        self.target_volume_sell = 0
        self.tf = None
        self.timestamp = None # begin
        self.ntrades = 0
        self.average_price = 0

    def __str__(self):
        # usal problem with UNIT to fix
        # return f"candle ts: {datetime.datetime.fromtimestamp(self.timestamp * self.tf / 1000)} and tf: {self.tf} prices; open: {self.open}, close: {self.close}, min: {self.min}, max: {self.max}"
        return f"candle ts: {datetime.datetime.fromtimestamp(self.timestamp * self.tf)} and tf: {self.tf} prices; open: {self.open}, close: {self.close}, min: {self.min}, max: {self.max}"

def filterTrades(trades, begin, end, timeFrame):
    """Filter the trade and group them in a timeframe
    begin: timestamp
    end: timestamp
    timeFrame"""
    tf_groups = {}

    for n in trades:
        timestamp = n['trade_timestamp']
        if timestamp < begin or timestamp > end:
            continue
        multiple = timestamp//timeFrame
        if multiple in tf_groups:
            tf_groups[multiple].append(n)
        else:
            tf_groups[multiple] = [n]

# code to filter candle, but replaced. could be deleted
#    ### find mean of the day
#    for key in tf_groups.keys():
#        item = tf_groups[key]
#        if not isinstance(item, dict):
#            print('not instance___________; ', item)
#            print()
#        else:
#            print('it is ok', item)
#            print()
#
#    for key in tf_groups.keys():
#        print(key)
#
#    tf_groups_key = [item for item in tf_groups.keys()]
#    print(tf_groups_key)
#    tf_groups_key = sorted(tf_groups_key)
#    print(tf_groups_key)
#
#    tf_groups_avg = {}
#    tf_groups_avgP = {}
#    for key in tf_groups.keys():
#        trades = tf_groups[key]
#        sum_price = 0
#        sum_volume = 0
#        count = 0
#        tt = 0
#        for t in trades:
#            sum_price += t['price']
#            tt += t['price']*t['base_volume']
#            sum_volume += t['base_volume']
#            count += 1
#        tf_groups_avg[key] = sum_price / count
#        tf_groups_avgP[key] = tt / sum_volume
#    print(tf_groups_avg)
#    print(tf_groups_avgP)
#    for i in tf_groups[19721]:
#        print(i)
#    print('mepkkk')
#    for i in tf_groups[19723]:
#        print(i)
#    exit()

    return tf_groups

def initCandles(trades, begin, end, timeFrame):
    tf_groups = filterTrades(trades, begin, end, timeFrame)
    candles = []
    for time, group in tf_groups.items():
        candle = Candle()
        candle.open = float(group[0]['price'])
        candle.close = float(group[-1]['price'])
        candle.min = candle.open
        candle.max = candle.open
        candle.timestamp = time
        candle.tf = timeFrame
        candle.ntrades = len(group)
        priceSum = 0
        priceCount = 0

        for t in group:
            price = float(t['price'])
            priceSum += price
            priceCount += 1
            if price < candle.min:
                candle.min = price
            if price > candle.max:
                candle.max = price
            candle.base_volume += float(t['base_volume'])
            candle.target_volume += float(t['target_volume'])
            if t['type'] == 'buy':
                candle.target_volume_buy += float(t['target_volume'])
            else:
                candle.target_volume_sell += float(t['target_volume'])
        candle.average_price = priceSum / priceCount
        candles.append(candle)

    return candles

def candlesRange(candlesList):
    """Return the min and max price of a list of candles"""
    max = candlesList[0].max
    min = candlesList[0].min
    i = 1
    while i < len(candlesList):
        if candlesList[i].max > max:
            max = candlesList[i].max
        if candlesList[i].min < min:
            min = candlesList[i].min
        i += 1

    return min, max




#####################33 test to find min a max price #############################
def minmax(trades):
    min = trades[0]["price"]
    max = trades[0]["price"]
    for i in trades:
        if i["price"] > max:
            max = i["price"]
        if i["price"] < min:
            min = i["price"]
    return min, max


##### convolve implementation - to move or to delete #########################
def convolve_simple(signal, kernel):
    # Length of the input signal and kernel
    signal_len = len(signal)
    kernel_len = len(kernel)

    # Output length after convolution
    output_len = signal_len + kernel_len - 1

    # Initialize the result array
    result = np.zeros(output_len)

    # Flip the kernel
    kernel = np.flip(kernel)

    # Perform convolution
    for i in range(output_len):
        for j in range(kernel_len):
            if i - j >= 0 and i - j < signal_len:
                result[i] += signal[i - j] * kernel[j]

    return result


def menu(stdscr):
    key = 0

    stdscr.clear()
    stdscr.refresh()

    # mouse setup
    curses.mousemask(curses.ALL_MOUSE_EVENTS)  # Enable all mouse events
    curses.mouseinterval(0)  # Report mouse events immediately

    # Start colors in curses
    curses.start_color()
    curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_CYAN)
    curses.init_pair(3, curses.COLOR_RED, curses.COLOR_YELLOW)
    ############# colors ##################

    customColors = CustomColors(10)
    white_c = [255, 255, 255]
    white_w = [255, 255, 255]
    white_c = [50, 120, 175]
    blue_c = [80, 150, 210]
    black_c = [0, 0, 0]
    darkBlue_c = [60, 70, 120]
    red = [255, 0, 0]
    green = [0, 255, 0]
    yellow = [255, 255, 5]

    addCustomColor(white_c, customColors)
    addCustomColor(blue_c, customColors)
    addCustomColor(darkBlue_c, customColors)
    addCustomColor(black_c, customColors)
    addCustomColor(white_w, customColors)
    addCustomColor(white_w, customColors)
    addCustomColor(red, customColors)
    addCustomColor(green, customColors)
    addCustomColor(yellow, customColors)

    white_t = addCustomColorTuple((white_c, black_c), customColors)
    blue_t = addCustomColorTuple((blue_c, black_c), customColors)
    white_w = addCustomColorTuple((white_w, black_c), customColors)
    red_t = addCustomColorTuple((red, black_c), customColors)
    green_t = addCustomColorTuple((green, black_c), customColors)
    yellow_t = addCustomColorTuple((yellow, black_c), customColors)
    selected_t = addCustomColorTuple((yellow, darkBlue_c), customColors)

    print("asdf")
    try:
        print("qwer")
    except:
        print("awefgawe")

    mouse_x = 0
    mouse_y = 0

    while key != ord('q'):
        stdscr.clear()
        height, width = stdscr.getmaxyx()
        if key == ord('a'):
            continue
        if key == ord('h'):
            continue
        if key == curses.KEY_MOUSE:
            _, mouse_x, mouse_y, _, _ = curses.getmouse()
            stdscr.addstr(20, 0, f"Mouse clicked at coordinates: ({mouse_x}, {mouse_y})")
            stdscr.refresh()


        winOff = 3
        minPrice, maxPrice = candlesRange(cands)
        diffPrice = maxPrice - minPrice
        stdscr.addstr(0, 0, f"min {minPrice}, max {maxPrice}, diff {diffPrice}, number of candles; {len(cands)}")
        if height > winOff and width > winOff:
            # TODO img is the graph, change the name
            img_height = height - winOff * 2
            img_width = width - winOff * 4

            img = stdscr.subwin(img_height, img_width, winOff, winOff * 2)
            mouse_p = mouse_x - winOff * 2
            img.bkgd(' ', curses.color_pair(3))

            lastCandlePos = img_width - 5
            subBlock = 2
            virtual_img_height = img_height * subBlock
            h_unit = virtual_img_height / diffPrice
            a = 0
            b = 3
            tt = 0
            stdscr.addstr(1, 0, f"img h {img_height}, img witdth {img_width}, diff {diffPrice}, h_unit; {h_unit}")
            stdscr.addstr(2, 0, f"min price {minPrice}, max peice {maxPrice}, diff {diffPrice}, h_unit; {h_unit}")

            # create legend
            img.addstr(0, 0, u'\u2588')
            img.addstr(img_height - 1, 0, u'\u2588')
            img.addstr(0, img_width - 1, u'\u2588')
            img.addstr(img_height - 2, img_width - 1, u'\u2588')
            img.addstr(img_height - 1, img_width - 2, u'\u2588')
            img.addstr(img_height - 1, img_width - 3, 'aA')
            img.insstr(img_height - 1, img_width - 2, ' ')

            n_elm = img_height / 3

            for i in range(img_height):
                if i % 3 == 0:
                    if i == img_height - 1:
                        img.addstr(i, img_width - 12, f'0.0000{i}324')
                        img.insstr(i, img_width - 12, ' ')
                    else:
                        img.addstr(i, img_width - 10, f'0.0000{i}324')

            # check the TF and chose what to do,
            # h - 4h - 8h -12h day plus hours
            # day 3day week- only day
            # month - year
            #
            #create a format day to assign at the candle, and then according to the tf chose what to dispaly
            #


            #for i in range(img_height):
            #    img.addstr(i, 0, u'\u2588')
            #for i in range(img_height - 1):
            #    img.addstr(i, img_width - 1, u'\u2588')



            #candles for testing, the screen has to have at least 80 lines
            if debug:
                t_cands = [
                    [10, 75, 30, 45],
                    [44, 66, 45, 65],
                    [16, 62, 62, 47],
                    [22, 48, 47, 22],
                    [21, 27, 21, 25],
                    [11, 57, 26, 22]
                ]
                t_count = 0

            for c in reversed(cands):


#                if a % 2:
#                    img.attron(curses.color_pair(white_t))
#                else:
#                    img.attron(curses.color_pair(blue_t))
                img.attron(curses.color_pair(blue_t))

                deltaStart = c.open - minPrice
                deltaClose = c.close - minPrice
                start = virtual_img_height - int(deltaStart * h_unit)
                close = virtual_img_height - int(deltaClose * h_unit)

                deltaMin = c.min - minPrice
                deltaMax = c.max - minPrice
                min = virtual_img_height - 1 - int(deltaMin * h_unit)
                max = virtual_img_height - 1 - int(deltaMax * h_unit)


                if debug:
                    lt = len(t_cands)
                    max = t_cands[t_count % lt][0]
                    min = t_cands[t_count % lt][1]
                    start = t_cands[t_count % lt][2]
                    close = t_cands[t_count % lt][3]
                    t_count += 1

                max_body = 0
                min_body = 0
                if start > close:
                    max_body = close
                    min_body = start
                    img.attron(curses.color_pair(white_w))
                else:
                    max_body = start
                    min_body = close



                top = max
                top_body = max_body
                bottom_body =  min_body
                bottom = min

                #stdscr.addstr(3, 0, f"top {top}, top_body {top_body}, bottom_body {bottom_body}, bottom {bottom}")

                if lastCandlePos == mouse_p:
                    img.addstr(img_height - 1, lastCandlePos, u'\u2503')
                    img.attron(curses.color_pair(selected_t))
                    img.addstr(img_height - 2, 0, f"top {top}, top_body {top_body}, bottom_body {bottom_body}, bottom {bottom}")
                    img.addstr(img_height - 1, 0, f"min {c.min}, max {c.max}, open: {c.open}, close: {c.close}, date: {datetime.datetime.fromtimestamp(c.timestamp * c.tf / 1).date()}")
                    for x in range(img_height):
                        img.addstr(x, lastCandlePos, ' ')



                try:
                    # the top and the bottom tip
                    ## the bottom part of the candle
                    if bottom % 2:
                        bottom -= 1
                        img.addstr(bottom // subBlock, lastCandlePos, u'\u2502')
                        bottom -= 2
                    else:
                        img.addstr(bottom // subBlock, lastCandlePos, u'\u2575')
                        bottom -= 2
                    # the top part of the candle
                    if top % 2:
                        top += 1
                        img.addstr(top // subBlock, lastCandlePos, u'\u2502')
                        top += 2
                    else:
                        img.addstr(top // subBlock, lastCandlePos, u'\u2577')
                        top += 2

                    while bottom >= bottom_body:
                        img.addstr(bottom // subBlock, lastCandlePos, u'\u2502')
                        bottom -= 2

                    b_top = top_body # the bottom of the upper line
                    while b_top >= top:
                        img.addstr(b_top // subBlock, lastCandlePos, u'\u2502')
                        b_top -= 2

                    # the top and the bottom of the body
                    #fullBlock = u'\u2588'
                    #halfUpperBlock = u'\u2580'
                    #halfLowerBlock = u'\u2584'

                    #fullBlock = u'\u2503'
                    #halfUpperBlock = u'\u2579'
                    #halfLowerBlock = u'\u257b'

                    # cases with no body
                    if top_body == bottom_body:
                        if top_body == bottom and top_body == top:
                            img.addstr(top_body // subBlock, lastCandlePos, u'\u2501')
                        elif top_body == bottom and top_body != top:
                            img.addstr(top_body // subBlock, lastCandlePos, u'\u2537')
                        elif top_body != bottom and top_body == top:
                            img.addstr(top_body // subBlock, lastCandlePos, u'\u252F')
                        else:
                            img.addstr(top_body // subBlock, lastCandlePos, u'\u253F')
                    else:
                        # cases with the body
                        if bottom_body % 2:
                            bottom_body -= 1
                            #img.addstr(bottom_body // subBlock, lastCandlePos, u'\u2588')
                            img.addstr(bottom_body // subBlock, lastCandlePos, u'\u2503')
                            bottom_body -= 2
                        else:
                            #img.addstr(bottom_body // subBlock, lastCandlePos, u'\u2580')
                            img.addstr(bottom_body // subBlock, lastCandlePos, u'\u257F') # half upper line u2579
                            bottom_body -= 2
                        # the max part of the candle
                        if top_body % 2:
                            top_body += 1
                            #img.addstr(top_body // subBlock, lastCandlePos, u'\u2588')
                            img.addstr(top_body // subBlock, lastCandlePos, u'\u2503')
                            top_body += 2
                        else:
                            #img.addstr(top_body // subBlock, lastCandlePos, u'\u2584')
                            img.addstr(top_body // subBlock, lastCandlePos, u'\u257D') # half lower line u257B')
                            top_body += 2


                    while bottom_body >= top_body:
                        img.addstr(bottom_body // subBlock, lastCandlePos, u'\u2503')
                        bottom_body -= 2

                except:
                    print("the new loop sais nothing")
                    print(f"error open {start} and close {close}")

                #img.addstr(b, 3, f"min {min} max {max} open {start} close {close} n. {a} N: {str(a)} ntrades: {c.ntrades}")
#                #img.addstr(b, 3, f"n. {a} deltaMin {deltaMin} deltaMax {deltaMax} min {min} - {c.min} max {max} candleN: {str(a)} ntrades: {c.ntrades} date: {datetime.datetime.fromtimestamp(c.timestamp * c.tf / 1).date()}")
#                #img.addstr(b, 3, f"n. {a} min {min} - {c.min} max {max} close {close} - {c.close} open {start} - {c.open} candleN: {str(a)} ntrades: {c.ntrades} date: {datetime.datetime.fromtimestamp(c.timestamp * c.tf / 1).date()}")


#

                img.addstr(a % 3 * 2, lastCandlePos, str(a))
                a += 1
                b += 1
                lastCandlePos -= 1



        # Turning on attributes for title
        stdscr.attron(curses.color_pair(1))
        stdscr.attron(curses.A_BOLD)

        # Rendering title
        try:
            stdscr.addstr(10, 0, "A")
        except:
            stdscr.addstr(5, 0, "not working")


        stdscr.refresh()
        key = stdscr.getch()


def main():
    curses.wrapper(menu)

class StdOutWrapper:
    text = ""
    def write(self,txt):
        self.text += txt
        self.text = '\n'.join(self.text.split('\n')[-300:])
    def get_text(self,beg=0,end=-1):
        """I think it is reversed the order, i should change it"""
        return '\n'.join(self.text.split('\n')[beg:end]) + '\n'


if __name__ == "__main__":

    debug = False
    dicPath = 'tradesHistory.json'



# timestamp filters
# different api use different timestamp unit..
# tf_second = 1000
    tf_second = 1
    tf_hour = tf_second * 60 * 60
    tf_4hours = tf_second * 60 * 60 * 4
    tf_day = tf_hour * 24
    tf_week = tf_day * 7
    tf_month = tf_day * 30 # approx
    tf_year = tf_day * 365 # approx


    history = {}

    if False:
        tick = dex.Ticker('SBX', 'XCH')
        dex.updateTickerTradesHistory(tick)
        dumpJson({"trades": tick.historical_trades})
        history = tick.historical_trades
    else:
        loadJson(history)

    trades = history['trades']['trades']
    print(trades[0])
    sorted_trades = sorted(trades, key=lambda x: x["trade_timestamp"])


############################################################################
############################################################################
###################### Filtering of outlier ################################


    import numpy as np

    filtered_trades = []
    n_trades = len(sorted_trades)
    print("number of trades before filtereing ", n_trades)
    trades_price = np.zeros(n_trades)
    trades_volume = np.zeros(n_trades)

    sample = 5

    for n, i in enumerate(sorted_trades):
        trades_price[n] = i['price']

    for n, i in enumerate(sorted_trades):
        trades_volume[n] = i['base_volume']

# esclude the first 5 and the last 5

    for i in range(sample, n_trades - sample):
        sumWeight = 0
        sumVolume = 0
        for u in range(i - sample, i + sample):
            sumWeight += trades_price[u] * trades_volume[u]
            sumVolume += trades_volume[u]
        avg_price = sumWeight / sumVolume
        delta = abs(trades_price[i] - avg_price) /  avg_price
        if delta < 0.35: # this is the value that is filtered
            filtered_trades.append(sorted_trades[i])

    n_ftrades = len(filtered_trades)

# replace the original trades with the filtered ones, to regactor in a function
#


    trades = filtered_trades



    # Example usage:
    signal = np.array([1, 2, 1, 2, 1, 3, 1, 1, 2])
    kernel = np.array([0.6, 1, 0.5])

    result_simple = convolve_simple(signal, kernel)
    result_np = np.convolve(signal, kernel, mode='full')

    # Compare results
    print("Result (Simple):", result_simple)
    print("Result (NumPy):", result_np)



##### convolve implementation - to move or to delete #########################
##############################################################################
##############################################################################
##############################################################################
##############################################################################
##############################################################################






########################test by filtering one day ############################33
    day = datetime.datetime(2024,1,6)
    day_ts = day.timestamp()

    def filterPerDay(day_ts, trades):

        end_day = day_ts + tf_day
        day_trades  = []
        for i in trades:
           if i["trade_timestamp"] > day_ts and i["trade_timestamp"] < end_day:
               day_trades.append(i)

        return day_trades

    dd = filterPerDay(day_ts, trades)

    sumP = 0
    sumV = 0
    for i in dd:
        sumP += i["price"] * i["base_volume"]
        sumV += i["base_volume"]
    avg = sumP / sumV

    pp = []
    for i in dd:
        dv = i["price"] /  avg
        pv = i["price"] - avg
        if dv < 1.55: # this is the value that is filtered
            pp.append(i)

###############################################################################33

    # i have to delete the dic entry in the dumpJson
    #

    now = int(time.time()) # * 1000 not needed useing history from offers
    print("now", now)

    #change data and time
    date = datetime.datetime(2024,1,9)
    now = date.timestamp()

    n_candle = 100
    tf = tf_day
    begin = now - n_candle * tf

    print(trades[2])
    tf_trades = filterTrades(trades, begin, now, tf)

    cands = initCandles(trades, begin, now, tf)
    cands = sorted(cands, key=lambda x: x.timestamp)

    #############
    ############# print trade data
    #ticker = dex.Ticker('SBX', 'XCH')

    #for i in trades:
    #    print(i['price'], " ", datetime.datetime.fromtimestamp(i['trade_timestamp'] /1000), " ", i['type'], " ", i['target_volume'])

    print(len(cands))

    main()

    mystdout = StdOutWrapper()
    sys.stdout = mystdout
    sys.stderr = mystdout

    try:
        main()
    except Exception as e:
        print("The exception of main is: ", e)
        print(traceback.format_exc())

    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__
    sys.stdout.write(mystdout.get_text())
