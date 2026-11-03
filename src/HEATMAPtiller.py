"""Time heat map: when did an event happen.

Events are timestamps. Time is cut into columns of one duration (the scale) and each column is
cut into as many squares as the screen has rows, so a column reads top to bottom and the columns
left to right, the newest on the right. A square is colored by the number of events in it.

The idea comes from chiaharvestgraph by Bram Stolk (https://github.com/stolk/chiaharvestgraph).

This module has no curses code: the scales and the time buckets, the color ramps, the cursor and
the zoom of a view (HeatmapView), a source of events read from log files (LogFileSource) and a
series of times with a value each (TimeSeries, e.g. the depth of a fork).
The drawing is ELEMENTS.create_time_heatmap.

The buckets follow the local wall clock: a day starts at local midnight, a week on Monday (see
WALL_ORIGIN for the summer time changes).
"""

import bisect
import calendar
import math
import os
import re
import threading
import time
from array import array
from datetime import datetime

DAY = 86400
WEEK = 7 * DAY

# the durations of one column: (name, seconds, months). A month column is a calendar month, so its
# length changes. Each scale is cut into a whole number of columns of the scale before it, so a
# zoom (HeatmapView.zoom_in) turns one column into 2 or more.
# Five scales, by their macro column: 24 minutes (4 columns of 6m), the hour (4 of 15m), the day
# (4 of 6h), the month (a column each day), the year (a column each month)
COLUMN_SCALES = [
    ('6m', 6 * 60, 0),
    ('15m', 15 * 60, 0),
    ('6h', 6 * 3600, 0),
    ('24h', DAY, 0),
    ('1mo', 0, 1),
]
SCALE_INDEX = {name: i for i, (name, _, _) in enumerate(COLUMN_SCALES)}

# the bands of two alternating shades that show the passing of time: seconds, 'month' or 'year'.
# COLUMN_BAND: the columns of a band have one background shade in the graph and on the labels.
# TOP_BAND: the bigger band, on the labels above the column bands (the day of the hours).
COLUMN_BAND = {'6m': 24 * 60, '15m': 3600, '6h': DAY, '24h': 'month', '1mo': 'year'}
TOP_BAND = {'6m': 3600, '15m': DAY, '6h': 'month', '24h': 'year', '1mo': None}  # None: no top band
BAND_LIGHTNESS = 0.035  # how much lighter the second shade is, in OKLab

# the buckets are counted on the local wall clock (the time with the UTC offset of that moment), from
# Monday 2024-01-01 00:00: an hour starts at :00 and a day at midnight also with summer time, and a
# week starts on Monday. When the clock goes back, its repeated hour falls in the same buckets as
# the first one (a bucket of 2 hours); when it goes forward, the skipped hour is an empty bucket
WALL_ORIGIN = 1704067200  # 2024-01-01 00:00 as seconds of a naive (UTC-like) clock


def to_wall(t: float) -> float:
    return t + time.localtime(t).tm_gmtoff


def from_wall(w: float) -> float:
    whole = math.floor(w)
    return time.mktime(time.gmtime(whole)[:8] + (-1,)) + (w - whole)


def zoom_in_scale(scale_idx: int):
    """The scale that cuts a column of scale_idx in columns; None for the smallest"""
    return scale_idx - 1 if scale_idx > 0 else None


def column_index(t: float, scale_idx: int) -> int:
    """Index of the column of scale_idx that holds the time t"""
    _, seconds, months = COLUMN_SCALES[scale_idx]
    w = to_wall(t)
    if seconds:
        return math.floor((w - WALL_ORIGIN) / seconds)
    d = time.gmtime(math.floor(w))
    return ((d.tm_year - 2024) * 12 + d.tm_mon - 1) // months


def wall_column(w: float, scale_idx: int) -> int:
    """Index of the column of scale_idx that holds the wall clock time w"""
    _, seconds, months = COLUMN_SCALES[scale_idx]
    if seconds:
        return math.floor((w - WALL_ORIGIN) / seconds)
    d = time.gmtime(math.floor(w))
    return ((d.tm_year - 2024) * 12 + d.tm_mon - 1) // months


def column_wall(col: int, scale_idx: int):
    """[w0, w1) of a column on the wall clock"""
    _, seconds, months = COLUMN_SCALES[scale_idx]
    if seconds:
        w0 = WALL_ORIGIN + col * seconds
        return w0, w0 + seconds

    def month_start(m):
        return calendar.timegm((2024 + m // 12, m % 12 + 1, 1, 0, 0, 0))
    return month_start(col * months), month_start((col + 1) * months)


def column_bounds(col: int, scale_idx: int):
    """[t0, t1) of a column"""
    w0, w1 = column_wall(col, scale_idx)
    return from_wall(w0), from_wall(w1)


def band_id(w: float, unit) -> int:
    """The number of the band of `unit` (seconds, 'month' or 'year') that holds the wall clock
    time w; two bands next to each other have a different parity"""
    if unit == 'month':
        d = time.gmtime(math.floor(w))
        return d.tm_year * 12 + d.tm_mon - 1
    if unit == 'year':
        return time.gmtime(math.floor(w)).tm_year
    return math.floor((w - WALL_ORIGIN) / unit)


def band_wall(w: float, unit):
    """[b0, b1) on the wall clock of the band of `unit` that holds w"""
    if unit in ('month', 'year'):
        d = time.gmtime(math.floor(w))
        if unit == 'year':
            return calendar.timegm((d.tm_year, 1, 1, 0, 0, 0)), calendar.timegm((d.tm_year + 1, 1, 1, 0, 0, 0))
        m = d.tm_year * 12 + d.tm_mon - 1
        return (calendar.timegm((m // 12, m % 12 + 1, 1, 0, 0, 0)),
                calendar.timegm(((m + 1) // 12, (m + 1) % 12 + 1, 1, 0, 0, 0)))
    b0 = WALL_ORIGIN + band_id(w, unit) * unit
    return b0, b0 + unit


def column_band(col: int, scale_idx: int) -> int:
    """0 or 1: the background band of a column"""
    return band_id(column_wall(col, scale_idx)[0], COLUMN_BAND[COLUMN_SCALES[scale_idx][0]]) % 2


def human_duration(seconds) -> str:
    """2d, 4.6d, 27h, 45s, 12ms"""
    for unit, s in (('d', DAY), ('h', 3600), ('m', 60), ('s', 1)):
        if seconds >= s:
            value = seconds / s
            return f"{value:.0f}{unit}" if abs(value - round(value)) < 0.05 else f"{value:.1f}{unit}"
    return f"{seconds * 1000:.0f}ms"


# ---------------------------------------------------------------- colors

def _srgb_to_linear(c):
    c /= 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _linear_to_srgb(c):
    c = max(0.0, min(1.0, c))
    c = c * 12.92 if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055
    return round(c * 255)


def rgb_to_oklab(rgb):
    r, g, b = (_srgb_to_linear(c) for c in rgb)
    l = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    return (0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
            1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
            0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s)


def oklab_to_rgb(lab):
    L, a, b = lab
    l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    return (_linear_to_srgb(4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s),
            _linear_to_srgb(-1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s),
            _linear_to_srgb(-0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s))


def mix(rgb0, rgb1, t: float):
    """Mix two colors in OKLab, t=0 is rgb0, t=1 is rgb1"""
    a, b = rgb_to_oklab(rgb0), rgb_to_oklab(rgb1)
    return oklab_to_rgb(tuple(x + (y - x) * t for x, y in zip(a, b)))


def make_ramp(seeds, steps: int):
    """`steps` colors that go through the seed colors, evenly spaced in OKLab"""
    if len(seeds) == 1 or steps == 1:
        return [tuple(seeds[0])] * steps
    ramp = []
    for i in range(steps):
        pos = i / (steps - 1) * (len(seeds) - 1)
        k = min(int(pos), len(seeds) - 2)
        ramp.append(mix(seeds[k], seeds[k + 1], pos - k))
    return ramp


def ramp_from_seed(seed, steps: int, background):
    """A ramp from one color: from near the background, through the seed, to a light tint of it"""
    return make_ramp([mix(background, seed, 0.3), seed, mix(seed, (255, 255, 255), 0.6)], steps)


class HeatmapStyle:
    """How a count becomes a color.
    ramp: the colors, from few events to many
    expected_rate: events per second when all is fine. The count of a cell is compared with the
        expected one (ratio 1 is the last ramp color). None: compared with the busiest cell in view
    fixed_max: compared with this value instead of the busiest cell, so the colors do not change
        with the zoom (for a value that does not grow with the column duration, e.g. a depth)
    presence: only happened or not, the last ramp color or `zero`
    zero: the color of a cell without events (None: the first ramp color)
    over: the color above over_ratio times the expected count (None: the last ramp color)
    no_data: before the source starts (default: the tab background, COLORS tab_soft); future: after now
    count_name: what a cell holds, in the selection line and the footer ("events", "forks")"""

    def __init__(self, ramp, expected_rate=None, presence=False, zero=None, over=None, over_ratio=1.2,
                 no_data=(28, 36, 68), future=(0, 10, 45), cursor=(250, 250, 250), names=None,
                 count_name='events', fixed_max=None):
        self.ramp = [tuple(c) for c in ramp]
        self.expected_rate = expected_rate
        self.presence = presence
        self.zero = tuple(zero) if zero else self.ramp[0]
        self.over = tuple(over) if over else None
        self.over_ratio = over_ratio
        self.no_data = tuple(no_data)
        self.future = tuple(future)
        self.cursor = tuple(cursor)
        self.count_name = count_name
        self.fixed_max = fixed_max
        # legend: (color, label)
        self.names = names
        self._shaded = {}

    def selected(self, color):
        """The color of a square in a selection of more squares (the cursor square is `cursor`)"""
        key = ('selected', color)
        if key not in self._shaded:
            self._shaded[key] = mix(color, self.cursor, 0.55)
        return self._shaded[key]

    def shaded(self, color):
        """The color on the second background band: a little lighter"""
        if color not in self._shaded:
            L, a, b = rgb_to_oklab(color)
            self._shaded[color] = oklab_to_rgb((L + BAND_LIGHTNESS, a, b))
        return self._shaded[color]

    def ratio(self, count: int, seconds: float, view_max: int):
        if self.expected_rate:
            return count / (self.expected_rate * seconds)
        if self.fixed_max:
            return count / self.fixed_max
        return count / view_max if view_max else 0

    def color(self, count: int, seconds: float, view_max: int):
        if count == 0:
            return self.zero
        if self.presence:
            return self.ramp[-1]
        ratio = self.ratio(count, seconds, view_max)
        if self.over and ratio > self.over_ratio:
            return self.over
        level = min(len(self.ramp) - 1, int(ratio * (len(self.ramp) - 1) + 0.5))
        return self.ramp[level]

    def legend(self):
        if self.names:
            return self.names
        if self.presence:
            return [(self.zero, 'no event'), (self.ramp[-1], 'event'), (self.no_data, 'no data')]
        what = 'expected' if self.expected_rate else 'busiest'
        items = [(self.zero, f'no {self.count_name}'), (self.ramp[len(self.ramp) // 2], f'½ {what}'), (self.ramp[-1], what)]
        if self.over:
            items.append((self.over, f'over {self.over_ratio}x'))
        return items + [(self.no_data, 'no data')]


# ---------------------------------------------------------------- events

class EventSeries:
    """The times of the events, sorted, and where each one comes from (file, byte offset, line).
    start: the time the source starts (cells before it have no data)"""

    def __init__(self):
        self.times = array('d')
        self.file_idx = array('H')
        self.offsets = array('Q')
        self.lines = array('L')
        self.start = None
        self.version = 0

    def __len__(self):
        return len(self.times)

    def count(self, t0: float, t1: float) -> int:
        return bisect.bisect_left(self.times, t1) - bisect.bisect_left(self.times, t0)

    def index_range(self, t0: float, t1: float):
        """Indexes [i0, i1) of the events in [t0, t1)"""
        return bisect.bisect_left(self.times, t0), bisect.bisect_left(self.times, t1)

    def append(self, t, file_idx, offset, line):
        self.times.append(t)
        self.file_idx.append(file_idx)
        self.offsets.append(offset)
        self.lines.append(line)

    def sort(self):
        """Lines of different processes can be a little out of order"""
        times = self.times
        if all(times[i] <= times[i + 1] for i in range(len(times) - 1)):
            return
        order = sorted(range(len(times)), key=times.__getitem__)
        for name in ('times', 'file_idx', 'offsets', 'lines'):
            old = getattr(self, name)
            setattr(self, name, array(old.typecode, (old[i] for i in order)))


class TimeSeries:
    """Events with a value each (e.g. the depth of a fork): the times sorted, and one value for
    each, for the cell counts (count) and for a heat map colored by the biggest value (max_value).
    start: the time from which the source has data (see EventSeries). A new series has a new
    version, so the views count their cells again"""

    def __init__(self, pairs, start: float = 0):
        pairs = sorted(pairs)
        self.times = [t for t, _ in pairs]
        self.values = [v for _, v in pairs]
        self.start = start
        self.version = 0

    def __len__(self):
        return len(self.times)

    def index_range(self, t0: float, t1: float):
        """Indexes [i0, i1) of the events in [t0, t1)"""
        return bisect.bisect_left(self.times, t0), bisect.bisect_left(self.times, t1)

    def count(self, t0: float, t1: float) -> int:
        i0, i1 = self.index_range(t0, t1)
        return i1 - i0

    def max_value(self, t0: float, t1: float):
        i0, i1 = self.index_range(t0, t1)
        return max(self.values[i0:i1], default=0)


LINE_HEAD = re.compile(rb'\d{4}-\d\d-\d\d[T ]\d\d:')  # a log line that starts with its time


def parse_line_time(line: bytes):
    """Time of a log line that starts with 'YYYY-MM-DDTHH:MM:SS[.mmm]' (or a space instead of T).
    None for the lines without it (e.g. the lines of a traceback)"""
    if len(line) < 19 or line[4] != 45 or line[7] != 45 or line[10] not in (84, 32) or line[13] != 58:
        return None
    end = 23 if len(line) >= 23 and line[19] == 46 else 19
    try:
        return datetime.fromisoformat(line[:end].decode()).timestamp()
    except ValueError:
        return None


class LogFileSource:
    """Events from log files: the lines that match a regex.
    paths: the log files, the newest first (debug.log, debug.log.1, ...); missing files are skipped
    match: a regex (str) searched in each line with a time; None takes every line with a time.
    load() reads all the files, refresh() reads the new lines of the newest file and loads all
    again when it was rotated. Both are made to run in a thread; series is replaced, not changed,
    by load()"""

    def __init__(self, name: str, paths, match: str = None):
        self.name = name
        self.paths = list(paths)
        self.match = re.compile(match.encode()) if match else None
        self.series = EventSeries()
        self.files = []  # oldest first, the indexes of series.file_idx
        self.status = 'not loaded'
        self.error = None
        self.loaded = False
        self.lock = threading.Lock()
        self.last_refresh = 0
        self._tail = None  # (inode, offset, line number) of the newest file

    def _read(self, series: EventSeries, file_idx: int, offset: int, line_no: int, set_start: bool):
        path = self.files[file_idx]
        match = self.match
        with open(path, 'rb') as f:
            f.seek(offset)
            for line in f:
                if not line.endswith(b'\n'):  # a line still being written
                    break
                t = None
                if set_start and series.start is None:
                    t = parse_line_time(line)
                    if t is not None:
                        series.start = t
                if match is None or match.search(line):
                    if t is None:
                        t = parse_line_time(line)
                    if t is not None:
                        series.append(t, file_idx, offset, line_no)
                offset += len(line)
                line_no += 1
        return offset, line_no

    def load(self):
        with self.lock:
            try:
                self.status = 'loading'
                self.files = [p for p in reversed(self.paths) if os.path.exists(p)]
                if not self.files:
                    raise FileNotFoundError(f"no log file: {', '.join(self.paths)}")
                series = EventSeries()
                for i, path in enumerate(self.files):
                    self.status = f"loading {os.path.basename(path)} ({i + 1}/{len(self.files)})"
                    offset, line_no = self._read(series, i, 0, 1, True)
                series.sort()
                series.version = self.series.version + 1
                self._tail = (os.stat(self.files[-1]).st_ino, offset, line_no)
                self.series = series
                self.error = None
                self.loaded = True
                self.status = 'loaded'
            except Exception as e:
                self.error = f"{self.name}: {e}"
                self.status = 'error'
            self.last_refresh = time.time()

    def refresh(self):
        """Read the lines added to the newest file"""
        if not self.loaded or self._tail is None:
            return self.load()
        try:
            st = os.stat(self.files[-1])
        except OSError:
            return self.load()
        inode, offset, line_no = self._tail
        if st.st_ino != inode or st.st_size < offset:  # rotated
            return self.load()
        with self.lock:
            series = self.series
            n = len(series)
            offset, line_no = self._read(series, len(self.files) - 1, offset, line_no, False)
            self._tail = (inode, offset, line_no)
            if len(series) != n:
                series.sort()
                series.version += 1
            self.last_refresh = time.time()

    def lines_between(self, t0: float, t1: float, filters, max_lines: int = 5000):
        """The log lines from the first line at t0 to the last one before t1, with the lines
        without a time that follow them (e.g. a traceback). Needs a source of every line
        (match None). filters: [(name, regex str or None for every line)]; a line without a time
        goes with the line before it. Return {name: (rows, total)}, rows: at most max_lines
        (file name, line number, text)"""
        with self.lock:
            series, files = self.series, list(self.files)
        found = {name: ([], 0) for name, _ in filters}
        i0, i1 = series.index_range(t0, t1)
        if i0 >= i1:
            return found
        compiled = [(name, re.compile(regex.encode()) if regex else None) for name, regex in filters]
        rows = {name: [] for name, _ in filters}
        totals = {name: 0 for name, _ in filters}
        matched = {name: False for name, _ in filters}
        end = (series.file_idx[i1], series.offsets[i1]) if i1 < len(series) else None
        fi, off, ln = series.file_idx[i0], series.offsets[i0], series.lines[i0]
        while fi < len(files):
            with open(files[fi], 'rb') as f:
                f.seek(off)
                for line in f:
                    if (fi, off) == end or not line.endswith(b'\n'):
                        return {name: (rows[name], totals[name]) for name in rows}
                    has_time = LINE_HEAD.match(line) is not None
                    row = None
                    for name, regex in compiled:
                        if has_time:
                            matched[name] = regex is None or regex.search(line) is not None
                        if matched[name]:
                            totals[name] += 1
                            if len(rows[name]) < max_lines:
                                if row is None:
                                    row = (os.path.basename(files[fi]), ln,
                                           line.decode(errors='replace').rstrip('\n'))
                                rows[name].append(row)
                    off += len(line)
                    ln += 1
            fi, off, ln = fi + 1, 0, 1
        return {name: (rows[name], totals[name]) for name in rows}


# ---------------------------------------------------------------- view

class HeatmapView:
    """Scale, cursor and scroll of one heat map.
    Each column is cut in n_rows squares, the rows the screen has, so a square is the column
    duration / n_rows (a 30m column on 80 rows: 22.5 s).
    Two modes: in 'column' mode the cursor selects a macro column, the columns of one background
    band (COLUMN_BAND: the 4 columns of an hour, of a day, the days of a month), and the zoom
    changes the scale; in 'square' mode it selects one square, or the squares from anchor_time
    to the cursor in the order of time. The cursor is a time, so it stays on the same moment
    when the scale changes. right_col is the index of the rightmost column; it follows the current
    time while it shows it. zoom_range: [t0, t1) of the macro column the last zoom in cut, to
    center the view on it"""

    def __init__(self, scale_idx: int = 6):
        self.scale_idx = scale_idx
        self.mode = 'column'
        self.cursor_time = None
        self.anchor_time = None  # square mode: the other end of a selection of more squares
        self.right_col = None
        self.cols = 1
        self.n_rows = 1
        self.zoom_range = None
        self.recenter = False

    @property
    def scale_name(self):
        return COLUMN_SCALES[self.scale_idx][0]

    @property
    def left_col(self):
        return self.right_col - self.cols + 1

    def column_bounds(self, col: int):
        return column_bounds(col, self.scale_idx)

    def square_seconds(self, col: int):
        w0, w1 = column_wall(col, self.scale_idx)
        return (w1 - w0) / self.n_rows

    def cell_bounds(self, col: int, row: int):
        """[t0, t1) of a square"""
        w0, w1 = column_wall(col, self.scale_idx)
        step = (w1 - w0) / self.n_rows
        return from_wall(w0 + row * step), from_wall(w0 + (row + 1) * step)

    def locate(self, t: float):
        """(column, row) of the square that holds t"""
        col = column_index(t, self.scale_idx)
        w0, w1 = column_wall(col, self.scale_idx)
        row = math.floor((to_wall(t) - w0) / (w1 - w0) * self.n_rows)
        return col, max(0, min(row, self.n_rows - 1))

    def cursor(self):
        return self.locate(self.cursor_time)

    def macro_wall(self, col: int):
        """[w0, w1) on the wall clock of the macro column that holds the column col"""
        return band_wall(column_wall(col, self.scale_idx)[0], COLUMN_BAND[self.scale_name])

    def macro_columns(self, col: int):
        """The first and last column of the macro column that holds the column col"""
        w0, w1 = self.macro_wall(col)
        return wall_column(w0, self.scale_idx), wall_column(w1 - 0.5, self.scale_idx)

    def selected_squares(self):
        """The first and last (column, row) of the selected squares, in the order of time"""
        cursor = self.cursor()
        if self.anchor_time is None:
            return cursor, cursor
        anchor = self.locate(self.anchor_time)
        return min(anchor, cursor), max(anchor, cursor)

    def selection(self):
        """[t0, t1) of the selected macro column, or of the selected squares in square mode"""
        if self.mode == 'square':
            first, last = self.selected_squares()
            return self.cell_bounds(*first)[0], self.cell_bounds(*last)[1]
        w0, w1 = self.macro_wall(self.cursor()[0])
        return from_wall(w0), from_wall(w1)

    def selection_columns(self):
        """The first and last column of the selection"""
        if self.mode == 'square':
            first, last = self.selected_squares()
            return first[0], last[0]
        return self.macro_columns(self.cursor()[0])

    def zoom_columns(self):
        """The first and last column of zoom_range, None without it"""
        if self.zoom_range is None:
            return None
        t0, t1 = self.zoom_range
        return column_index(t0, self.scale_idx), column_index(t1 - 1e-3, self.scale_idx)

    def layout(self, cols: int, n_rows: int, now: float = None):
        """Fit the view in `cols` columns of `n_rows` squares; call it every frame before drawing"""
        now = time.time() if now is None else now
        self.cols = max(cols, 1)
        self.n_rows = max(n_rows, 1)
        now_col = column_index(now, self.scale_idx)
        if self.right_col is None:
            self.right_col = now_col
        if self.cursor_time is None:
            self.cursor_time = now
        self.cursor_time = min(self.cursor_time, now)
        col, row = self.cursor()
        if self.mode == 'square':
            t0, t1 = self.cell_bounds(col, row)
            self.cursor_time = (t0 + t1) / 2
        else:
            self.anchor_time = None
        if self.recenter:
            zoom = self.zoom_columns()
            if zoom:
                right = zoom[1] + max(0, (self.cols - (zoom[1] - zoom[0] + 1)) // 2)
            else:
                right = col + self.cols // 2
            self.right_col = min(now_col, right)
            self.recenter = False
        elif self.right_col >= now_col - 1 and col >= now_col - 1:
            self.right_col = now_col  # follow the current time
        if col > self.right_col:
            self.right_col = col
        elif col < self.right_col - self.cols + 1:
            self.right_col = col + self.cols - 1
        self.right_col = min(self.right_col, now_col)

    def move(self, dx: int = 0, dy: int = 0, now: float = None, extend: bool = False):
        """Column mode: dx macro columns (-1 or 1), at the same place in the macro column. Square
        mode: dx columns and dy rows; the rows go on in the next column, like the time. extend:
        the selection grows from where it was (anchor_time), else it is the cursor square only"""
        now = time.time() if now is None else now
        col, row = self.cursor()
        if self.mode == 'column':
            first, last = self.macro_columns(col)
            w0, w1 = self.macro_wall(col)
            part = (to_wall(self.cursor_time) - w0) / (w1 - w0)
            n0, n1 = self.macro_wall(last + 1 if dx > 0 else first - 1)
            t = from_wall(n0 + part * (n1 - n0))
            if t > now:
                if from_wall(n0) > now:
                    return
                t = now
            self.cursor_time = t
            return
        if not extend:
            self.anchor_time = None
        elif self.anchor_time is None:
            self.anchor_time = self.cursor_time
        row += dy
        col += dx + row // self.n_rows
        row %= self.n_rows
        t0, t1 = self.cell_bounds(col, row)
        if t0 <= now:
            self.cursor_time = (t0 + t1) / 2

    def set_scale(self, scale_idx: int):
        scale_idx = max(0, min(scale_idx, len(COLUMN_SCALES) - 1))
        if scale_idx != self.scale_idx:
            self.scale_idx = scale_idx
            self.zoom_range = None
            self.recenter = True

    def zoom_in(self):
        """The selected macro column becomes the columns of the next scale down, its first macro
        column selected"""
        target = zoom_in_scale(self.scale_idx)
        if target is None:
            return False
        t0, t1 = self.selection()
        self.set_scale(target)
        self.zoom_range = (t0, t1)
        self.cursor_time = t0
        return True

    def zoom_out(self):
        """The macro column of the next scale up that holds the cursor"""
        if self.scale_idx + 1 >= len(COLUMN_SCALES):
            return False
        self.set_scale(self.scale_idx + 1)
        return True

    def go_now(self, now: float = None):
        self.cursor_time = time.time() if now is None else now
        self.right_col = None
