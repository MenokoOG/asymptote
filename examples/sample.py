"""Sample inputs for Asymptote, each function has a known Big-O."""


def constant_lookup(d, key):          # expected: O(1) time, O(1) space
    return d.get(key)


def linear_scan(items):               # expected: O(n) time
    total = 0
    for x in items:
        total += x
    return total


def quadratic_pairs(items):           # expected: O(n^2) time
    pairs = []
    for a in items:
        for b in items:
            pairs.append((a, b))
    return pairs


def sort_then_scan(items):            # expected: O(n log n) time
    ordered = sorted(items)
    for x in ordered:
        print(x)
    return ordered


def binary_search(items, target):     # expected: O(log n) time
    lo, hi = 0, len(items) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if items[mid] == target:
            return mid
        if items[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1


def fib(n):                           # expected: O(2^n) time (no memo)
    if n < 2:
        return n
    return fib(n - 1) + fib(n - 2)


def build_squares(n):                 # expected: O(n) time & space
    return [i * i for i in range(n)]
