"""Seed curriculum. Each lesson has a working solution and a deliberately buggy variant."""
from __future__ import annotations

LESSONS: list[dict] = [
    # ------------------------------------------------------------ Beginner
    {
        "id": "loops", "level": "Beginner", "title": "Variables & loops",
        "concept": "A loop repeats a block. Watch the loop variable and the running total change on every step.",
        "code": """\
nums = [4, 8, 15, 16, 23]
total = 0
for i in range(len(nums)):
    total += nums[i]
print("sum =", total)
""",
        "buggy": """\
nums = [4, 8, 15, 16, 23]
total = 0
for i in range(len(nums) + 1):
    total += nums[i]
print("sum =", total)
""",
    },
    {
        "id": "linear-search", "level": "Beginner", "title": "Linear search",
        "concept": "Check every element in order until you find the target. O(n) comparisons in the worst case.",
        "code": """\
def linear_search(arr, target):
    for i in range(len(arr)):
        if arr[i] == target:
            return i
    return -1

print(linear_search([7, 2, 9, 4, 1], 4))
""",
        "buggy": """\
def linear_search(arr, target):
    i = 0
    while arr[i] != target:
        i += 1
    return i

print(linear_search([7, 2, 9, 4, 1], 5))
""",
    },
    {
        "id": "binary-search", "level": "Beginner", "title": "Binary search",
        "concept": "On a sorted array, look at the middle and throw away the half that can't contain the target. "
                   "O(log n). Watch lo, mid and hi close in.",
        "code": """\
def binary_search(a, target):
    lo, hi = 0, len(a) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if a[mid] == target:
            return mid
        elif a[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1

print(binary_search([1, 3, 5, 7, 9, 11, 13, 15], 11))
""",
        "buggy": """\
def binary_search(a, target):
    lo, hi = 0, len(a) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if a[mid] == target:
            return mid
        elif a[mid] < target:
            lo = mid
        else:
            hi = mid
    return -1

print(binary_search([1, 3, 5, 7, 9, 11, 13, 15], 10))
""",
    },
    {
        "id": "bubble-sort", "level": "Beginner", "title": "Bubble sort",
        "concept": "Repeatedly compare neighbours and swap them if they're out of order; the largest value "
                   "bubbles to the end each pass. O(n²).",
        "code": """\
a = [5, 1, 4, 2, 8, 3]
n = len(a)
for i in range(n):
    for j in range(n - 1 - i):
        if a[j] > a[j + 1]:
            a[j], a[j + 1] = a[j + 1], a[j]
print(a)
""",
        "buggy": """\
a = [5, 1, 4, 2, 8, 3]
n = len(a)
for i in range(n):
    for j in range(n - i):
        if a[j] > a[j + 1]:
            a[j], a[j + 1] = a[j + 1], a[j]
print(a)
""",
    },
    {
        "id": "insertion-sort", "level": "Beginner", "title": "Insertion sort",
        "concept": "Grow a sorted prefix: take the next value and shift bigger values right until it fits.",
        "code": """\
a = [7, 3, 9, 1, 6, 2]
for i in range(1, len(a)):
    key = a[i]
    j = i - 1
    while j >= 0 and a[j] > key:
        a[j + 1] = a[j]
        j -= 1
    a[j + 1] = key
print(a)
""",
        "buggy": """\
a = [7, 3, 9, 1, 6, 2]
for i in range(1, len(a)):
    key = a[i]
    j = i - 1
    while a[j] > key:
        a[j + 1] = a[j]
        j -= 1
    a[j + 1] = key
print(a)
""",
    },
    # ------------------------------------------------------------ Intermediate
    {
        "id": "two-pointers", "level": "Intermediate", "title": "Two pointers",
        "concept": "On a sorted array, move a left and right pointer toward each other to find a pair with a "
                   "given sum in O(n).",
        "code": """\
def pair_sum(a, target):
    l, r = 0, len(a) - 1
    while l < r:
        s = a[l] + a[r]
        if s == target:
            return (a[l], a[r])
        if s < target:
            l += 1
        else:
            r -= 1
    return None

print(pair_sum([1, 2, 4, 6, 8, 11, 15], 14))
""",
        "buggy": """\
def pair_sum(a, target):
    l, r = 0, len(a)
    while l < r:
        s = a[l] + a[r]
        if s == target:
            return (a[l], a[r])
        if s < target:
            l += 1
        else:
            r -= 1
    return None

print(pair_sum([1, 2, 4, 6, 8, 11, 15], 14))
""",
    },
    {
        "id": "sliding-window", "level": "Intermediate", "title": "Sliding window",
        "concept": "Keep a running window sum: add the element entering on the right, subtract the one "
                   "leaving on the left. Max sum of k consecutive numbers in O(n).",
        "code": """\
def max_window(a, k):
    window = sum(a[:k])
    best = window
    for right in range(k, len(a)):
        window += a[right] - a[right - k]
        best = max(best, window)
    return best

print(max_window([2, 1, 5, 1, 3, 2, 9, 1], 3))
""",
        "buggy": """\
def max_window(a, k):
    window = sum(a[:k])
    best = window
    for right in range(k, len(a) + 1):
        window += a[right] - a[right - k]
        best = max(best, window)
    return best

print(max_window([2, 1, 5, 1, 3, 2, 9, 1], 3))
""",
    },
    {
        "id": "stack", "level": "Intermediate", "title": "Stack: balanced brackets",
        "concept": "A stack is last-in, first-out. Push opening brackets; each closing bracket must match "
                   "the top of the stack.",
        "code": """\
def balanced(s):
    pairs = {')': '(', ']': '[', '}': '{'}
    stack = []
    for ch in s:
        if ch in '([{':
            stack.append(ch)
        elif ch in pairs:
            if not stack or stack.pop() != pairs[ch]:
                return False
    return not stack

print(balanced("{[()()]}"))
print(balanced("([)]"))
""",
        "buggy": """\
def balanced(s):
    pairs = {')': '(', ']': '[', '}': '{'}
    stack = []
    for ch in s:
        if ch in '([{':
            stack.append(ch)
        elif ch in pairs:
            if stack.pop() != pairs[ch]:
                return False
    return not stack

print(balanced("())"))
""",
    },
    {
        "id": "queue", "level": "Intermediate", "title": "Queue: hot potato",
        "concept": "A queue is first-in, first-out. collections.deque gives O(1) appends and pops at both ends.",
        "code": """\
from collections import deque

players = deque(["Ana", "Ben", "Cy", "Dee", "Eve"])
while len(players) > 1:
    for _ in range(2):
        players.append(players.popleft())
    out = players.popleft()
    print("out:", out)
print("winner:", players[0])
""",
        "buggy": """\
from collections import deque

players = deque(["Ana", "Ben", "Cy", "Dee", "Eve"])
while len(players) > 0:
    for _ in range(2):
        players.append(players.popleft())
    out = players.popleft()
    print("out:", out)
print("winner:", players[0])
""",
    },
    {
        "id": "hashmap", "level": "Intermediate", "title": "Hash map: two sum",
        "concept": "Store each value's index in a dict; for each number check if its complement was seen. O(n).",
        "code": """\
def two_sum(nums, target):
    seen = {}
    for i, x in enumerate(nums):
        need = target - x
        if need in seen:
            return [seen[need], i]
        seen[x] = i
    return []

print(two_sum([3, 8, 11, 5, 2], 13))
""",
        "buggy": """\
def count_words(words):
    counts = {}
    for w in words:
        counts[w] += 1
    return counts

print(count_words(["to", "be", "or", "not", "to", "be"]))
""",
    },
    {
        "id": "linked-list", "level": "Intermediate", "title": "Linked list: reverse",
        "concept": "Each node points to the next. Reverse by walking the list and flipping each pointer, "
                   "tracking prev, cur and nxt.",
        "code": """\
class Node:
    def __init__(self, val, next=None):
        self.val = val
        self.next = next

head = Node(1, Node(2, Node(3, Node(4))))

prev, cur = None, head
while cur:
    nxt = cur.next
    cur.next = prev
    prev = cur
    cur = nxt
head = prev

node = head
while node:
    print(node.val, end=" ")
    node = node.next
""",
        "buggy": """\
class Node:
    def __init__(self, val, next=None):
        self.val = val
        self.next = next

head = Node(1, Node(2, Node(3, Node(4, Node(5, Node(6))))))

# find the middle with slow/fast pointers
slow = fast = head
while fast.next:
    slow = slow.next
    fast = fast.next.next
print("middle:", slow.val)
""",
    },
    {
        "id": "recursion", "level": "Intermediate", "title": "Recursion: factorial & fib",
        "concept": "A function that calls itself on a smaller input, with a base case that stops it. "
                   "Watch the call tree grow and unwind.",
        "code": """\
def fib(n):
    if n <= 1:
        return n
    return fib(n - 1) + fib(n - 2)

print(fib(5))
""",
        "buggy": """\
def fact(n):
    if n == 1:
        return 1
    return n * fact(n - 1)

print(fact(0))
""",
    },
    {
        "id": "merge-sort", "level": "Intermediate", "title": "Merge sort",
        "concept": "Split in half, sort each half recursively, then merge two sorted lists. O(n log n).",
        "code": """\
def merge_sort(a):
    if len(a) <= 1:
        return a
    mid = len(a) // 2
    left = merge_sort(a[:mid])
    right = merge_sort(a[mid:])
    merged = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            merged.append(left[i]); i += 1
        else:
            merged.append(right[j]); j += 1
    merged += left[i:] + right[j:]
    return merged

print(merge_sort([6, 2, 9, 1, 5, 3]))
""",
        "buggy": """\
def merge_sort(a):
    if len(a) <= 1:
        return a
    mid = len(a) // 2
    left = merge_sort(a[:mid])
    right = merge_sort(a[mid:])
    merged = []
    i = j = 0
    while i < len(left) or j < len(right):
        if left[i] <= right[j]:
            merged.append(left[i]); i += 1
        else:
            merged.append(right[j]); j += 1
    return merged

print(merge_sort([6, 2, 9, 1, 5, 3]))
""",
    },
    {
        "id": "quick-sort", "level": "Intermediate", "title": "Quick sort (in place)",
        "concept": "Pick a pivot, partition smaller values to its left and bigger to its right, recurse. "
                   "Average O(n log n).",
        "code": """\
def partition(a, lo, hi):
    pivot = a[hi]
    i = lo
    for j in range(lo, hi):
        if a[j] < pivot:
            a[i], a[j] = a[j], a[i]
            i += 1
    a[i], a[hi] = a[hi], a[i]
    return i

def quick_sort(a, lo, hi):
    if lo < hi:
        p = partition(a, lo, hi)
        quick_sort(a, lo, p - 1)
        quick_sort(a, p + 1, hi)

a = [7, 2, 9, 4, 1, 6]
quick_sort(a, 0, len(a) - 1)
print(a)
""",
        "buggy": """\
def partition(a, lo, hi):
    pivot = a[hi]
    i = lo
    for j in range(lo, hi):
        if a[j] < pivot:
            a[i], a[j] = a[j], a[i]
            i += 1
    a[i], a[hi] = a[hi], a[i]
    return i

def quick_sort(a, lo, hi):
    if lo < hi:
        p = partition(a, lo, hi)
        quick_sort(a, lo, p)
        quick_sort(a, p + 1, hi)

a = [7, 2, 9, 4, 1, 6]
quick_sort(a, 0, len(a) - 1)
print(a)
""",
    },
    # ------------------------------------------------------------ Advanced
    {
        "id": "bst", "level": "Advanced", "title": "Binary search tree",
        "concept": "Smaller keys go left, bigger go right. Insert and search walk one root-to-leaf path: "
                   "O(height).",
        "code": """\
class Node:
    def __init__(self, key):
        self.key = key
        self.left = None
        self.right = None

def insert(root, key):
    if root is None:
        return Node(key)
    if key < root.key:
        root.left = insert(root.left, key)
    else:
        root.right = insert(root.right, key)
    return root

def inorder(root, out):
    if root:
        inorder(root.left, out)
        out.append(root.key)
        inorder(root.right, out)
    return out

root = None
for k in [8, 3, 10, 1, 6, 14, 4]:
    root = insert(root, k)
print(inorder(root, []))
""",
        "buggy": """\
class Node:
    def __init__(self, key):
        self.key = key
        self.left = None
        self.right = None

def insert(root, key):
    if root is None:
        return Node(key)
    if key < root.key:
        root.left = insert(root.left, key)
    else:
        root.right = insert(root.right, key)

root = None
for k in [8, 3, 10, 1]:
    root = insert(root, k)
print(root.key)
""",
    },
    {
        "id": "heap", "level": "Advanced", "title": "Heap: k smallest",
        "concept": "A min-heap keeps the smallest item at index 0. heappush/heappop are O(log n). "
                   "Shown both as a tree and as the underlying array.",
        "code": """\
import heapq

nums = [9, 4, 7, 1, 8, 2, 6]
heap = []
for x in nums:
    heapq.heappush(heap, x)

smallest = []
for _ in range(3):
    smallest.append(heapq.heappop(heap))
print(smallest)
""",
        "buggy": """\
import heapq

nums = [9, 4, 7]
heap = []
for x in nums:
    heapq.heappush(heap, x)

smallest = []
for _ in range(4):
    smallest.append(heapq.heappop(heap))
print(smallest)
""",
    },
    {
        "id": "bfs", "level": "Advanced", "title": "Graph BFS",
        "concept": "Breadth-first search explores level by level with a queue. It finds shortest paths in "
                   "unweighted graphs.",
        "code": """\
from collections import deque

graph = {
    'A': ['B', 'C'],
    'B': ['A', 'D', 'E'],
    'C': ['A', 'F'],
    'D': ['B'],
    'E': ['B', 'F'],
    'F': ['C', 'E'],
}

def bfs(start):
    visited = {start}
    queue = deque([start])
    order = []
    while queue:
        node = queue.popleft()
        order.append(node)
        for nb in graph[node]:
            if nb not in visited:
                visited.add(nb)
                queue.append(nb)
    return order

print(bfs('A'))
""",
        "buggy": """\
from collections import deque

graph = {
    'A': ['B', 'C'],
    'B': ['A', 'D'],
    'C': ['A', 'G'],
    'D': ['B'],
}

def bfs(start):
    visited = {start}
    queue = deque([start])
    order = []
    while queue:
        node = queue.popleft()
        order.append(node)
        for nb in graph[node]:
            if nb not in visited:
                visited.add(nb)
                queue.append(nb)
    return order

print(bfs('A'))
""",
    },
    {
        "id": "dfs", "level": "Advanced", "title": "Graph DFS (recursive)",
        "concept": "Depth-first search goes as deep as possible before backtracking. The call stack is the "
                   "implicit stack.",
        "code": """\
graph = {1: [2, 3], 2: [4], 3: [4, 5], 4: [6], 5: [6], 6: []}

def dfs(node, visited, order):
    visited.add(node)
    order.append(node)
    for nb in graph[node]:
        if nb not in visited:
            dfs(nb, visited, order)
    return order

print(dfs(1, set(), []))
""",
        "buggy": """\
graph = {1: [2, 3], 2: [1, 4], 3: [1], 4: [2]}

def dfs(node, visited, order):
    order.append(node)
    for nb in graph[node]:
        if nb not in visited:
            dfs(nb, visited, order)
    return order

print(dfs(1, set(), []))
""",
    },
    {
        "id": "dijkstra", "level": "Advanced", "title": "Dijkstra's shortest path",
        "concept": "Always expand the closest unfinished node (min-heap by distance) and relax its edges. "
                   "Works with non-negative weights.",
        "code": """\
import heapq

graph = {
    'S': {'A': 4, 'B': 1},
    'A': {'C': 1},
    'B': {'A': 2, 'C': 5},
    'C': {'T': 3},
    'T': {},
}

def dijkstra(src):
    dist = {node: float('inf') for node in graph}
    dist[src] = 0
    pq = [(0, src)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist[u]:
            continue
        for v, w in graph[u].items():
            if d + w < dist[v]:
                dist[v] = d + w
                heapq.heappush(pq, (dist[v], v))
    return dist

print(dijkstra('S'))
""",
        "buggy": """\
import heapq

graph = {
    'S': {'A': 4, 'B': 1},
    'A': {'C': 1},
    'B': {'A': 2, 'C': 5},
    'C': {'T': 3},
}

def dijkstra(src):
    dist = {node: float('inf') for node in graph}
    dist[src] = 0
    pq = [(0, src)]
    while pq:
        d, u = heapq.heappop(pq)
        for v, w in graph[u].items():
            if d + w < dist[v]:
                dist[v] = d + w
                heapq.heappush(pq, (dist[v], v))
    return dist

print(dijkstra('S'))
""",
    },
    {
        "id": "union-find", "level": "Advanced", "title": "Union-Find",
        "concept": "Track groups with a parent array. find() follows parents to the root (with path "
                   "compression); union() links two roots.",
        "code": """\
parent = list(range(6))

def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x

def union(a, b):
    ra, rb = find(a), find(b)
    if ra != rb:
        parent[rb] = ra

for a, b in [(0, 1), (2, 3), (1, 3), (4, 5)]:
    union(a, b)
print([find(i) for i in range(6)])
""",
        "buggy": """\
parent = list(range(6))

def find(x):
    while parent[x] != x:
        x = parent[x]
    return x

def union(a, b):
    parent[a] = b
    parent[b] = a

for a, b in [(0, 1), (2, 3)]:
    union(a, b)
print([find(i) for i in range(6)])
""",
    },
    {
        "id": "dp-grid", "level": "Advanced", "title": "DP: grid paths",
        "concept": "Dynamic programming fills a table where each cell reuses answers to smaller "
                   "sub-problems: paths(r, c) = paths(r-1, c) + paths(r, c-1).",
        "code": """\
rows, cols = 4, 5
dp = [[0] * cols for _ in range(rows)]
for r in range(rows):
    for c in range(cols):
        if r == 0 or c == 0:
            dp[r][c] = 1
        else:
            dp[r][c] = dp[r - 1][c] + dp[r][c - 1]
print(dp[rows - 1][cols - 1])
""",
        "buggy": """\
rows, cols = 4, 5
dp = [[0] * cols for _ in range(rows)]
for r in range(rows):
    for c in range(cols):
        dp[r][c] = dp[r - 1][c] + dp[r][c - 1]
        if r == 0 or c == 0:
            dp[r][c] = 1
print(dp[rows][cols - 1])
""",
    },
    {
        "id": "dp-memo", "level": "Advanced", "title": "DP: memoized climbing stairs",
        "concept": "Memoization caches results of recursive calls so each sub-problem is solved once. "
                   "Compare the call tree with plain recursion.",
        "code": """\
memo = {}

def ways(n):
    if n <= 1:
        return 1
    if n in memo:
        return memo[n]
    memo[n] = ways(n - 1) + ways(n - 2)
    return memo[n]

print(ways(6))
""",
        "buggy": """\
memo = {}

def ways(n):
    if n in memo:
        return memo[n]
    memo[n] = ways(n - 1) + ways(n - 2)
    return memo[n]

print(ways(6))
""",
    },
    {
        "id": "backtracking", "level": "Advanced", "title": "Backtracking: subsets",
        "concept": "Build a solution step by step: choose, explore, un-choose. The call tree shows every "
                   "branch explored.",
        "code": """\
def subsets(nums):
    result, path = [], []
    def backtrack(i):
        if i == len(nums):
            result.append(path[:])
            return
        path.append(nums[i])
        backtrack(i + 1)
        path.pop()
        backtrack(i + 1)
    backtrack(0)
    return result

print(subsets([1, 2, 3]))
""",
        "buggy": """\
def subsets(nums):
    result, path = [], []
    def backtrack(i):
        if i == len(nums):
            result.append(path)
            return
        path.append(nums[i])
        backtrack(i + 1)
        backtrack(i + 1)
    backtrack(0)
    return result

print(subsets([1, 2, 3]))
""",
    },
]

LEVELS = ["Beginner", "Intermediate", "Advanced"]


def by_id(lesson_id: str) -> dict | None:
    for lesson in LESSONS:
        if lesson["id"] == lesson_id:
            return lesson
    return None
