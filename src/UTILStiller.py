import json
import time
from datetime import datetime, timedelta

from chia_rs.sized_bytes import bytes32
from chia.util.hash import std_hash
from chia_rs.sized_ints import uint16, uint32, uint64, uint128
from clvm.casts import int_to_bytes


##############################################################################
########### varius
def print_json(dict):
    print(json.dumps(dict, sort_keys=True, indent=4))


def parseFloatJsonValue(dic, key):
    """Filter out non valid float values"""
    try:
        return float(dic[key])
    except:
        return None

############################################
########### chia utility

def calc_coin_id(amount: uint64, parent_coin_info: str, puzzle_hash: str):
    return std_hash(bytes32.from_hexstr(parent_coin_info) + bytes32.from_hexstr(puzzle_hash) + int_to_bytes(amount))

##############################################################################
########### binary search
def binary_search(lst, target):

    low = 0
    high = len(lst)

    while low < high:
        mid = (high + low) // 2
        if lst[mid] == target:
            return mid
        elif lst[mid] < target:
            low = mid + 1
        else:
            high = mid
    return -1


def binary_search_l(lst, target):
    low = 0
    high = len(lst)

    while low < high:
        mid = (high + low) // 2
        if lst[mid] < target:
            low = mid + 1
        else:
            high = mid
    return high


def binary_search_r(lst, target):
    low = 0
    high = len(lst)

    while low < high:
        mid = (high + low) // 2
        if lst[mid] <= target:
            low = mid + 1
        else:
            high = mid
    return high

#####################################################


### numbers
def classify_number(s: str):
    if not isinstance(s, str) or not s:
        return "invalid"

    # decimal int (no prefix)
    if s.isdigit():
        return "int"

    # hex (with or without 0x)
    t = s.removeprefix("0x").removeprefix("0X")
    if t and all(c in "0123456789abcdefABCDEF" for c in t):
        return "hex"

    return "invalid"


def truncate(n, decimals=0):
    """You can use negative to truncate on the left side"""
    multiplier = 10**decimals
    return int(n * multiplier) / multiplier


def humanizer(num: int, suffixes: list[str]) -> str:

    magnitude = 0

    while abs(num) >= 1000 and magnitude < len(suffixes) - 1:
        num /= 1000.0
        magnitude += 1

    # format with 3 significant digits
    return f"{num:.3g}{suffixes[magnitude]}"


def human_mojo(num: int) -> str:
    # suffixes
    suffixes = ['', 'K', 'M', 'B', 'XCH']
    return humanizer(num, suffixes)


def human_int(num: int) -> str:
    # suffixes
    suffixes = ['', 'K', 'M', 'B', 'T']
    return humanizer(num, suffixes)

# TODO: keep only one
def timestamp_to_date(timestamp):
    try:
        datetime.fromtimestamp(int(timestamp)).strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        print(e)
        print(timestamp)
        print(type(timestamp))
    return datetime.fromtimestamp(int(timestamp)).strftime('%Y-%m-%d %H:%M:%S')


# TODO: keep only one
def convert_ts_to_date(ts):
    """Convert a timestamp to a date, with ts in milliseconds"""
    return datetime.fromtimestamp(ts/1000).strftime('%Y-%m-%d %H:%M:%S')


def time_ago(ts):
    now = datetime.now()
    delta = now - ts
    seconds = int(delta.total_seconds())

    y, rem = divmod(seconds, 31536000)  # 365 * 24 * 60 * 60
    m, rem = divmod(rem, 2592000)       # 30 * 24 * 60 * 60
    d, rem = divmod(rem, 86400)         # 24 * 60 * 60
    h, rem = divmod(rem, 3600)          # 60 * 60
    mi, s = divmod(rem, 60)

    if y > 0:
        return f"{y}y {m}m ago"
    elif m > 0:
        return f"{m}m {d}d ago"
    elif d > 0:
        return f"{d}d {h}h ago"
    elif h > 0:
        return f"{h}h {mi}m ago"
    elif mi > 2:
        return f"{mi}m ago"
    elif mi > 0:
        return f"{mi}m {s}s ago"
    else:
        return f"{s}sec ago"


#############################################
############## timer #######################

class Timer:
    def __init__(self, name='lapper', tag='t'):
        self.name = name
        self.tag = tag
        self.times = {}
        self.count = 0
        self.timestamps = []
        self.worst_times = {}
        self.init = False

    def start(self):
        if not self.init:
            self.times = {}
            self.count = 0
            self.timestamps = []
        else:
            raise "timer already initialized"

        self.timestamps.append(time.perf_counter())
        self.init = True

    def clocking(self, tag=None):
        lap = time.perf_counter()
        if tag is None:
            tag = f'{self.tag}_{self.count}'

        self.times[tag] = lap - self.timestamps[-1]
        self.timestamps.append(lap)
        self.count += 1

    def end(self):
        if len(self.worst_times) != 0:
            for key, value in self.times.items():
                if key in self.worst_times:
                    self.worst_times[key] = max(value, self.worst_times[key])
                else:
                    self.worst_times[key] = value
        else:
            self.worst_times = self.times
        self.init = False

    def __str__(self):
        text = f"{self.name} timing:\n"
        for tag, t in self.worst_times.items():
            if tag in self.times:
                last_t = f"{self.times[tag]:5f}"
            else:
                last_t = "none"

            text = f"{text}  -{tag}: {last_t} - worst: {t:5f}\n"
        return text


if '__main__' == __name__:
    # test
    ll = [2,4,8,9,13,49,49,49,78,90]
    target = 13
    r = binary_search(ll, target)
    if r == 4:
        print(f"binary search ok for {target}")

    target = 2
    r = binary_search(ll, target)
    if r == 0:
        print(f"binary search ok for {target}")

    target = 90
    r = binary_search(ll, target)
    if r == len(ll) - 1:
        print(f"binary search ok for {target}")

    target = 33
    r = binary_search(ll, target)
    if r == -1:
        print(f"binary search ok for {target} not in the list")

    target = 22
    r = binary_search_l(ll, target)
    print(f' for {target} the insert idx is {r}')
    print(ll)
    cc = ll.copy()
    cc.insert(r, target)
    print(cc)
    if r == 5:
        print('ok for', target)
    else:
        print('error with ', target)

    target = 1
    r = binary_search_l(ll, target)
    print(f' for {target} the insert idx is {r}')
    print(ll)
    cc = ll.copy()
    cc.insert(r, target)
    print(cc)
    if r == 0:
        print('ok for', target)
    else:
        print('error with ', target)

    target = 110
    r = binary_search_l(ll, target)
    print(f' for {target} the insert idx is {r}')
    print(ll)
    cc = ll.copy()
    cc.insert(r, target)
    print(cc)
    if r == len(ll):
        print('ok for', target)
    else:
        print('error with ', target)


    target = 49
    r = binary_search_l(ll, target)
    print(f' for {target} the insert idx is {r}')
    print(ll)
    cc = ll.copy()
    cc.insert(r, target + 1)
    print(cc)
    if r == 5:
        print('ok for', target)
    else:
        print('error with left', target)

    target = 49
    r = binary_search_r(ll, target)
    print(f' for {target} the insert idx is {r}')
    print(ll)
    cc = ll.copy()
    cc.insert(r, target + 1)
    print(cc)
    if r == 8:
        print('ok for', target)
    else:
        print('error with right ', target)


    ## test time ago

    print(time_ago(datetime.now() - timedelta(days=400)))     # 1y 1m ago
    print(time_ago(datetime.now() - timedelta(days=40)))      # 1m 10d ago
    print(time_ago(datetime.now() - timedelta(hours=26)))     # 1d 2h ago
    print(time_ago(datetime.now() - timedelta(minutes=90)))   # 1h 30m ago
    print(time_ago(datetime.now() - timedelta(seconds=75)))   # 1m 15s ago
    print(time_ago(datetime.now() - timedelta(seconds=12)))   # 12s ago
