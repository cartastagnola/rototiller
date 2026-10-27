"""Time heat map: when did an event happen.

Events are timestamps. Time is cut into columns of one duration (the scale) and each column is
cut into as many squares as the screen has rows, so a column reads top to bottom and the columns
left to right, the newest on the right. A square is colored by the number of events in it.

The idea comes from chiaharvestgraph by Bram Stolk (https://github.com/stolk/chiaharvestgraph).

This module has no curses code: the scales and the time buckets, the color ramps, the cursor and
the zoom of a view (HeatmapView) and a source of events read from log files (LogFileSource).
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
# zoom (HeatmapView.zoom_in) turns one column into 2 or more; the month is cut into days (ZOOM_IN)
COLUMN_SCALES = [
    ('1s', 1, 0),
    ('10s', 10, 0),
    ('1m', 60, 0),
    ('5m', 5 * 60, 0),
    ('10m', 10 * 60, 0),
    ('20m', 20 * 60, 0),
    ('1h', 3600, 0),
    ('6h', 6 * 3600, 0),
    ('12h', 12 * 3600, 0),
    ('24h', DAY, 0),
    ('7d', WEEK, 0),
    ('1mo', 0, 1),
    ('3mo', 0, 3),
    ('1y', 0, 12),
]
SCALE_INDEX = {name: i for i, (name, _, _) in enumerate(COLUMN_SCALES)}
ZOOM_IN = {SCALE_INDEX['1mo']: SCALE_INDEX['24h']}  # the scale a zoom goes to, when not the one before

# round steps for the row labels, in seconds
LABEL_STEPS = [0.1, 0.2, 0.5, 1, 2, 5, 10, 15, 30, 60, 120, 300, 600, 900, 1800, 3600, 2 * 3600,
               3 * 3600, 6 * 3600, 12 * 3600, DAY, 2 * DAY, WEEK, 2 * WEEK, 4 * WEEK, 13 * WEEK]

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
    if scale_idx in ZOOM_IN:
        return ZOOM_IN[scale_idx]
    return scale_idx - 1 if scale_idx > 0 else None


def column_index(t: float, scale_idx: int) -> int:
    """Index of the column of scale_idx that holds the time t"""
    _, seconds, months = COLUMN_SCALES[scale_idx]
    w = to_wall(t)
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


def human_duration(seconds) -> str:
    """2d, 4.6d, 27h, 45s, 12ms"""
    for unit, s in (('d', DAY), ('h', 3600), ('m', 60), ('s', 1)):
        if seconds >= s:
            value = seconds / s
            return f"{value:.0f}{unit}" if abs(value - round(value)) < 0.05 else f"{value:.1f}{unit}"
    return f"{seconds * 1000:.0f}ms"


def short_offset(seconds) -> str:
    """An offset in a column for the row labels: 0, 45s, 2m30, 1h, 2h30"""
    if seconds < 1:
        return f"{seconds:.1f}s" if seconds else '0'
    seconds = round(seconds)
    h, rest = divmod(seconds, 3600)
    m, s = divmod(rest, 60)
    if h:
        return f"{h}h{m:02d}" if m else f"{h}h"
    if m:
        return f"{m}m{s:02d}" if s else f"{m}m"
    return f"{s}s"


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
    presence: only happened or not, the last ramp color or `zero`
    zero: the color of a cell without events (None: the first ramp color)
    over: the color above over_ratio times the expected count (None: the last ramp color)
    no_data: before the source starts; future: after now"""

    def __init__(self, ramp, expected_rate=None, presence=False, zero=None, over=None, over_ratio=1.2,
                 no_data=(52, 54, 62), future=(0, 10, 45), cursor=(250, 250, 250), names=None):
        self.ramp = [tuple(c) for c in ramp]
        self.expected_rate = expected_rate
        self.presence = presence
        self.zero = tuple(zero) if zero else self.ramp[0]
        self.over = tuple(over) if over else None
        self.over_ratio = over_ratio
        self.no_data = tuple(no_data)
        self.future = tuple(future)
        self.cursor = tuple(cursor)
        # legend: (color, label)
        self.names = names

    def ratio(self, count: int, seconds: float, view_max: int):
        if self.expected_rate:
            return count / (self.expected_rate * seconds)
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
        items = [(self.zero, '0'), (self.ramp[len(self.ramp) // 2], f'½ {what}'), (self.ramp[-1], what)]
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

    def line_text(self, i: int) -> str:
        """The line of the event i"""
        s = self.series
        with open(self.files[s.file_idx[i]], 'rb') as f:
            f.seek(s.offsets[i])
            return f.readline().decode(errors='replace').rstrip('\n')

    def lines_around(self, i0: int, i1: int, before: int = 40, after: int = 40, max_lines: int = 3000):
        """The log lines from `before` lines before the event i0 to `after` lines after the event
        i1 - 1, at most max_lines (the interval [i0, i1) can have many events).
        Lines before the first event stay in its file.
        Return a list of (file name, line number, text, is an event of [i0, i1))"""
        s = self.series
        if i0 >= i1:
            return []
        events = {(s.file_idx[i], s.offsets[i]) for i in range(i0, min(i1, i0 + max_lines))}
        fi, off, ln = s.file_idx[i0], s.offsets[i0], s.lines[i0]
        last = (s.file_idx[i1 - 1], s.offsets[i1 - 1])
        rows = []

        # before: read back some bytes and keep the last lines
        with open(self.files[fi], 'rb') as f:
            back = min(off, before * 600)
            f.seek(off - back)
            chunk = f.read(back).split(b'\n')
            if off - back > 0:
                chunk = chunk[1:]  # the first line is cut
            if chunk and chunk[-1] == b'':  # the chunk ends where the event line starts
                chunk.pop()
            chunk = chunk[-before:] if before else []
            for k, text in enumerate(chunk):
                rows.append((os.path.basename(self.files[fi]), ln - len(chunk) + k,
                             text.decode(errors='replace'), False))

        # the interval, then `after` lines
        after_left = None
        while fi < len(self.files) and len(rows) < max_lines:
            with open(self.files[fi], 'rb') as f:
                f.seek(off)
                for line in f:
                    is_event = (fi, off) in events
                    rows.append((os.path.basename(self.files[fi]), ln,
                                 line.decode(errors='replace').rstrip('\n'), is_event))
                    if after_left is None and (fi, off) == last:
                        after_left = after
                    elif after_left is not None:
                        after_left -= 1
                    off += len(line)
                    ln += 1
                    if (after_left is not None and after_left <= 0) or len(rows) >= max_lines:
                        return rows
            fi, off, ln = fi + 1, 0, 1
        return rows


# ---------------------------------------------------------------- view

class HeatmapView:
    """Scale, cursor and scroll of one heat map.
    Each column is cut in n_rows squares, the rows the screen has, so a square is the column
    duration / n_rows (a 30m column on 80 rows: 22.5 s).
    Two modes: in 'column' mode the cursor selects a whole column and the zoom changes the scale;
    in 'square' mode it selects one square. The cursor is a time, so it stays on the same moment
    when the scale changes. right_col is the index of the rightmost column; it follows the current
    time while it shows it. zoom_range: [t0, t1) of the column the last zoom in cut, shown on
    the columns it became"""

    def __init__(self, scale_idx: int = 6):
        self.scale_idx = scale_idx
        self.mode = 'column'
        self.cursor_time = None
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

    def selection(self):
        """[t0, t1) of the selected column, or square in square mode"""
        col, row = self.cursor()
        if self.mode == 'square':
            return self.cell_bounds(col, row)
        return self.column_bounds(col)

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

    def move(self, dx: int = 0, dy: int = 0, now: float = None):
        """Column mode: dx columns, at the same place in the column. Square mode: dx columns and
        dy rows; the rows go on in the next column, like the time"""
        now = time.time() if now is None else now
        col, row = self.cursor()
        if self.mode == 'column':
            w0, w1 = column_wall(col, self.scale_idx)
            part = (to_wall(self.cursor_time) - w0) / (w1 - w0)
            n0, n1 = column_wall(col + dx, self.scale_idx)
            t = from_wall(n0 + part * (n1 - n0))
            if t > now:
                if from_wall(n0) > now:
                    return
                t = now
            self.cursor_time = t
            return
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
        """The selected column becomes the columns of the next scale down, the first one selected"""
        target = zoom_in_scale(self.scale_idx)
        if target is None:
            return False
        t0, t1 = self.column_bounds(self.cursor()[0])
        self.set_scale(target)
        self.zoom_range = (t0, t1)
        self.cursor_time = t0
        return True

    def zoom_out(self):
        """The column of the next scale up that holds the cursor"""
        if self.scale_idx + 1 >= len(COLUMN_SCALES):
            return False
        self.set_scale(self.scale_idx + 1)
        return True

    def go_now(self, now: float = None):
        self.cursor_time = time.time() if now is None else now
        self.right_col = None
