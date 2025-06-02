import json


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
