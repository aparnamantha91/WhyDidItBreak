"""LeetCode-style practice problems.

Each problem names a function the user must write. `tests` are argument lists; the
expected answers come from running `solution`. `topic` points at a lesson in
lessons.py, which is offered as sample code to look up.
"""
from __future__ import annotations

_LINKED_NOTE = '''\
# A linked list node (already defined for you):
# class ListNode:
#     def __init__(self, val=0, next=None):
#         self.val = val
#         self.next = next

'''
_TREE_NOTE = '''\
# A binary tree node (already defined for you):
# class TreeNode:
#     def __init__(self, val=0, left=None, right=None):
#         self.val = val
#         self.left = left
#         self.right = right

'''


def P(id, title, level, topic, fn, params, statement, solution, tests, *, visible=3, constraints=(),
      hints=(), explain=(), compare="exact", output="return", kinds=None, ret=None, returns=None):
    kinds = kinds or {}
    used = set(kinds.values()) | ({ret} if ret else set())
    note = (_LINKED_NOTE if "linked" in used else "") + (_TREE_NOTE if "tree" in used else "")
    what = returns or ("Change the input in place; nothing needs to be returned." if output == "arg0"
                       else "Return the answer.")
    starter = f"{note}def {fn}({', '.join(params)}):\n    # Write your solution here. {what}\n    pass\n"
    return {
        "id": id, "title": title, "level": level, "topic": topic, "fn": fn, "params": list(params),
        "statement": statement, "solution": solution, "tests": tests, "visible": visible,
        "constraints": list(constraints), "hints": list(hints), "explain": list(explain),
        "compare": compare, "output": output, "kinds": kinds, "ret": ret, "starter": starter,
    }


B, I, A = "Beginner", "Intermediate", "Advanced"

PROBLEMS: list[dict] = [
    # ================================================================ Beginner
    P("running-sum", "Running Sum", B, "loops", "running_sum", ["nums"],
      "Given a list `nums`, return a new list where position `i` holds the sum of `nums[0]` through `nums[i]`.",
      '''\
def running_sum(nums):
    out = []
    total = 0
    for x in nums:
        total += x
        out.append(total)
    return out
''',
      [[[1, 2, 3, 4]], [[3, 1, 2, 10, 1]], [[5]], [[]], [[-1, 1, -1, 1]], [[0, 0, 0]], [[10, -3, 4, -8, 2, 7]]],
      explain=["1, 1+2, 1+2+3, 1+2+3+4"],
      constraints=["`0 <= len(nums) <= 1000`"],
      hints=["Keep one variable holding the total so far.", "Append the total after adding each number."]),

    P("max-profit", "Best Time to Buy and Sell Stock", B, "loops", "max_profit", ["prices"],
      "`prices[i]` is the price of a stock on day `i`. Buy on one day and sell on a *later* day. "
      "Return the largest profit you can make, or `0` if no profit is possible.",
      '''\
def max_profit(prices):
    best = 0
    lowest = float("inf")
    for p in prices:
        if p < lowest:
            lowest = p
        elif p - lowest > best:
            best = p - lowest
    return best
''',
      [[[7, 1, 5, 3, 6, 4]], [[7, 6, 4, 3, 1]], [[2, 4, 1]], [[1]], [[]], [[3, 3, 3]], [[2, 1, 2, 1, 0, 1, 2]],
       [[1, 2, 3, 4, 5]]],
      explain=["Buy at 1 (day 1), sell at 6 (day 4).", "Prices only fall, so don't trade."],
      hints=["You only need the lowest price seen *so far*.",
             "At each day, the best sale is today's price minus that lowest price."]),

    P("find-index", "Find the Target", B, "linear-search", "find_index", ["nums", "target"],
      "Return the index of the first occurrence of `target` in `nums`, or `-1` if it is not there. "
      "Don't use `list.index`.",
      '''\
def find_index(nums, target):
    for i in range(len(nums)):
        if nums[i] == target:
            return i
    return -1
''',
      [[[7, 2, 9, 4, 1], 4], [[7, 2, 9, 4, 1], 5], [[3, 3, 3], 3], [[], 1], [[8], 8], [[1, 2, 3, 4, 5], 5],
       [[5, 4, 5, 4], 4]],
      hints=["What should happen when the loop finishes without finding it?"]),

    P("binary-search", "Binary Search", B, "binary-search", "search", ["nums", "target"],
      "`nums` is sorted in increasing order with no duplicates. Return the index of `target`, or `-1` if it is "
      "missing. Your solution should take O(log n) steps.",
      '''\
def search(nums, target):
    lo, hi = 0, len(nums) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if nums[mid] == target:
            return mid
        if nums[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
''',
      [[[-1, 0, 3, 5, 9, 12], 9], [[-1, 0, 3, 5, 9, 12], 2], [[5], 5], [[5], -5], [[], 3], [[1, 3], 3], [[1, 3], 1],
       [[1, 3, 5, 7, 9, 11, 13, 15], 15], [[1, 3, 5, 7, 9, 11, 13, 15], 16], [[1, 3, 5, 7, 9, 11, 13, 15], 0]],
      hints=["Keep two indexes, `lo` and `hi`, around the part that can still contain the target.",
             "After checking `mid`, move *past* it: `lo = mid + 1` or `hi = mid - 1`. Otherwise the range may never shrink."]),

    P("search-insert", "Search Insert Position", B, "binary-search", "search_insert", ["nums", "target"],
      "`nums` is sorted with no duplicates. Return the index of `target` if present; otherwise return the index "
      "where it would be inserted to keep the list sorted.",
      '''\
def search_insert(nums, target):
    lo, hi = 0, len(nums)
    while lo < hi:
        mid = (lo + hi) // 2
        if nums[mid] < target:
            lo = mid + 1
        else:
            hi = mid
    return lo
''',
      [[[1, 3, 5, 6], 5], [[1, 3, 5, 6], 2], [[1, 3, 5, 6], 7], [[1, 3, 5, 6], 0], [[], 4], [[1], 1], [[1], 2],
       [[2, 4, 6, 8, 10], 9]],
      hints=["This is binary search for the first element that is `>= target`."]),

    P("sort-list", "Sort a List", B, "bubble-sort", "sort_list", ["nums"],
      "Sort `nums` in increasing order **in place**, without using `sort` or `sorted`. "
      "Any algorithm is fine; bubble sort and insertion sort are good first choices.",
      '''\
def sort_list(nums):
    for i in range(1, len(nums)):
        key = nums[i]
        j = i - 1
        while j >= 0 and nums[j] > key:
            nums[j + 1] = nums[j]
            j -= 1
        nums[j + 1] = key
''',
      [[[5, 1, 4, 2, 8, 3]], [[3, 2, 1]], [[1]], [[]], [[2, 2, 1, 1]], [[1, 2, 3, 4]], [[-3, 7, 0, -8, 5, 5, 1]],
       [[9, 8, 7, 6, 5, 4, 3, 2, 1]]],
      output="arg0",
      hints=["Bubble sort: compare neighbours `nums[j]` and `nums[j + 1]`, swap when out of order.",
             "Be careful that `j + 1` never reaches `len(nums)`."]),

    P("move-zeroes", "Move Zeroes", B, "insertion-sort", "move_zeroes", ["nums"],
      "Move every `0` in `nums` to the end **in place**, keeping the other numbers in their original order.",
      '''\
def move_zeroes(nums):
    write = 0
    for read in range(len(nums)):
        if nums[read] != 0:
            nums[write], nums[read] = nums[read], nums[write]
            write += 1
''',
      [[[0, 1, 0, 3, 12]], [[0]], [[1, 2, 3]], [[0, 0, 1]], [[]], [[4, 0, 5, 0, 0, 6]], [[1, 0]], [[0, 0, 0]]],
      output="arg0",
      hints=["Use two indexes: one reads every element, one marks where the next non-zero goes."]),

    # ================================================================ Intermediate
    P("two-sum-sorted", "Two Sum II (sorted input)", I, "two-pointers", "two_sum_sorted", ["nums", "target"],
      "`nums` is sorted in increasing order. Exactly one pair of numbers adds up to `target`. "
      "Return their indexes `[i, j]` with `i < j` (0-based).",
      '''\
def two_sum_sorted(nums, target):
    i, j = 0, len(nums) - 1
    while i < j:
        s = nums[i] + nums[j]
        if s == target:
            return [i, j]
        if s < target:
            i += 1
        else:
            j -= 1
    return []
''',
      [[[2, 7, 11, 15], 9], [[2, 3, 4], 6], [[-1, 0], -1], [[1, 2, 3, 4, 4, 9, 56, 90], 8], [[1, 3, 5, 7], 12],
       [[-5, -3, 0, 2, 8], -8]],
      hints=["Start one pointer at each end.", "If the sum is too small, only moving the left pointer can raise it."]),

    P("valid-palindrome", "Valid Palindrome", I, "two-pointers", "is_palindrome", ["s"],
      "Return `True` if `s` reads the same forwards and backwards when you ignore case and skip every character "
      "that is not a letter or digit.",
      '''\
def is_palindrome(s):
    i, j = 0, len(s) - 1
    while i < j:
        if not s[i].isalnum():
            i += 1
        elif not s[j].isalnum():
            j -= 1
        else:
            if s[i].lower() != s[j].lower():
                return False
            i += 1
            j -= 1
    return True
''',
      [["A man, a plan, a canal: Panama"], ["race a car"], [" "], ["ab"], ["a."], ["0P"], ["No lemon, no melon"],
       [".,"]],
      hints=["`ch.isalnum()` tells you whether a character counts.", "Move a pointer inwards from each end."]),

    P("container-water", "Container With Most Water", I, "two-pointers", "max_area", ["height"],
      "`height[i]` is the height of a vertical line at position `i`. Pick two lines; together with the x-axis they "
      "hold `min(height[i], height[j]) * (j - i)` water. Return the largest amount possible.",
      '''\
def max_area(height):
    i, j = 0, len(height) - 1
    best = 0
    while i < j:
        best = max(best, min(height[i], height[j]) * (j - i))
        if height[i] < height[j]:
            i += 1
        else:
            j -= 1
    return best
''',
      [[[1, 8, 6, 2, 5, 4, 8, 3, 7]], [[1, 1]], [[4, 3, 2, 1, 4]], [[1, 2, 1]], [[2, 3, 10, 5, 7, 8, 9]], [[5]]],
      explain=["Lines at index 1 (height 8) and 8 (height 7): min 7 × width 7 = 49."],
      hints=["Start with the widest container.", "Moving the *taller* line inwards can never help. Move the shorter one."]),

    P("max-window-sum", "Maximum Sum of a Window", I, "sliding-window", "max_window_sum", ["nums", "k"],
      "Return the largest sum of any `k` consecutive numbers in `nums`. You may assume `1 <= k <= len(nums)`.",
      '''\
def max_window_sum(nums, k):
    window = sum(nums[:k])
    best = window
    for i in range(k, len(nums)):
        window += nums[i] - nums[i - k]
        best = max(best, window)
    return best
''',
      [[[2, 1, 5, 1, 3, 2], 3], [[2, 3, 4, 1, 5], 2], [[5], 1], [[-1, -2, -3, -4], 2], [[1, 2, 3], 3],
       [[4, -1, 2, 1, -7, 5, 3], 3], [[1, 1, 1, 1, 9], 1]],
      explain=["The window `[5, 1, 3]` sums to 9."],
      hints=["Don't re-add the whole window each time: add the number entering and subtract the one leaving.",
             "Careful with negative numbers: `best` should not start at 0."]),

    P("longest-unique", "Longest Substring Without Repeating Characters", I, "sliding-window",
      "longest_unique", ["s"],
      "Return the length of the longest substring of `s` in which no character appears twice.",
      '''\
def longest_unique(s):
    last = {}
    start = 0
    best = 0
    for i, ch in enumerate(s):
        if ch in last and last[ch] >= start:
            start = last[ch] + 1
        last[ch] = i
        best = max(best, i - start + 1)
    return best
''',
      [["abcabcbb"], ["bbbbb"], ["pwwkew"], [""], ["abba"], ["dvdf"], ["tmmzuxt"], ["a"]],
      explain=['"abc"', '"b"', '"wke"'],
      hints=["Grow a window to the right; when a character repeats, move the left edge past its previous position.",
             'Try "abba": the left edge must never move backwards.']),

    P("valid-parentheses", "Valid Parentheses", I, "stack", "is_valid", ["s"],
      "`s` contains only the characters `()[]{}`. Return `True` if every bracket is closed by the same kind of "
      "bracket, in the correct order.",
      '''\
def is_valid(s):
    pairs = {")": "(", "]": "[", "}": "{"}
    stack = []
    for ch in s:
        if ch in pairs:
            if not stack or stack.pop() != pairs[ch]:
                return False
        else:
            stack.append(ch)
    return not stack
''',
      [["()[]{}"], ["(]"], ["([{}])"], ["]"], ["(("], [""], ["([)]"], ["{[]}()"], ["())"]],
      hints=["Push every opening bracket on a stack.",
             "On a closing bracket the stack might be empty. Check before you pop.",
             "At the end, anything left on the stack was never closed."]),

    P("daily-temperatures", "Daily Temperatures", I, "stack", "daily_temperatures", ["temps"],
      "For each day, return how many days you have to wait for a warmer temperature. "
      "Use `0` when no later day is warmer.",
      '''\
def daily_temperatures(temps):
    answer = [0] * len(temps)
    stack = []
    for i, t in enumerate(temps):
        while stack and temps[stack[-1]] < t:
            j = stack.pop()
            answer[j] = i - j
        stack.append(i)
    return answer
''',
      [[[73, 74, 75, 71, 69, 72, 76, 73]], [[30, 40, 50, 60]], [[30, 60, 90]], [[90, 60, 30]], [[]], [[50]],
       [[70, 70, 71]], [[55, 38, 53, 81, 61, 93, 97, 32, 43, 78]]],
      hints=["Keep a stack of *indexes* of days still waiting for a warmer day.",
             "When today is warmer than the day on top of the stack, that day has its answer."]),

    P("buy-tickets", "Time Needed to Buy Tickets", I, "queue", "time_to_buy", ["tickets", "k"],
      "People stand in a queue; person `i` wants `tickets[i]` tickets. Buying one ticket takes 1 second, after "
      "which the person goes to the back of the queue (or leaves when they need no more). "
      "Return how many seconds pass until person `k` has bought all their tickets.",
      '''\
from collections import deque


def time_to_buy(tickets, k):
    queue = deque(range(len(tickets)))
    left = list(tickets)
    seconds = 0
    while queue:
        person = queue.popleft()
        left[person] -= 1
        seconds += 1
        if left[person] == 0:
            if person == k:
                return seconds
        else:
            queue.append(person)
    return seconds
''',
      [[[2, 3, 2], 2], [[5, 1, 1, 1], 0], [[1], 0], [[1, 1, 1], 1], [[3, 1], 0], [[2, 6, 3, 4, 5], 2]],
      hints=["Simulate it with `collections.deque`: `popleft()` the front, `append()` to the back.",
             "Keep the indexes in the queue so you know when it is person `k`."]),

    P("two-sum", "Two Sum", I, "hashmap", "two_sum", ["nums", "target"],
      "Return the indexes of the two numbers in `nums` that add up to `target`. Exactly one pair works, and you "
      "may not use the same element twice. The two indexes can be in either order.",
      '''\
def two_sum(nums, target):
    seen = {}
    for i, x in enumerate(nums):
        if target - x in seen:
            return [seen[target - x], i]
        seen[x] = i
    return []
''',
      [[[2, 7, 11, 15], 9], [[3, 2, 4], 6], [[3, 3], 6], [[1, 5, 8, -3], 5], [[0, 4, 3, 0], 0],
       [[-1, -2, -3, -4, -5], -8], [[5, 75, 25], 100]],
      compare="unordered",
      hints=["Brute force: try every pair `i < j`.",
             "Faster: for each number, ask whether `target - x` was seen earlier. A dict from value to index answers that.",
             "With `[3, 2, 4]` and target 6, make sure you don't pair the 3 with itself."]),

    P("first-unique", "First Unique Character", I, "hashmap", "first_unique", ["s"],
      "Return the index of the first character in `s` that appears exactly once, or `-1` if there is none.",
      '''\
def first_unique(s):
    count = {}
    for ch in s:
        count[ch] = count.get(ch, 0) + 1
    for i, ch in enumerate(s):
        if count[ch] == 1:
            return i
    return -1
''',
      [["leetcode"], ["loveleetcode"], ["aabb"], [""], ["z"], ["abcabcd"], ["aadadaad"]],
      hints=["Count every character first, then scan again.",
             "`count[ch] += 1` fails for a character you haven't seen. Try `count.get(ch, 0) + 1`."]),

    P("group-anagrams", "Group Anagrams", I, "hashmap", "group_anagrams", ["words"],
      "Group the words that are anagrams of each other. Return a list of groups; the groups and the words inside "
      "them can be in any order.",
      '''\
def group_anagrams(words):
    groups = {}
    for w in words:
        key = "".join(sorted(w))
        if key not in groups:
            groups[key] = []
        groups[key].append(w)
    return list(groups.values())
''',
      [[["eat", "tea", "tan", "ate", "nat", "bat"]], [[""]], [["a"]], [[]], [["ab", "ba", "abc", "cab", "b"]],
       [["aab", "aba", "baa", "abb"]]],
      compare="unordered2",
      hints=["Two words are anagrams when their sorted letters are equal.", "Use the sorted letters as a dict key."]),

    P("reverse-list", "Reverse Linked List", I, "linked-list", "reverse_list", ["head"],
      "Reverse a singly linked list and return the new head.",
      '''\
def reverse_list(head):
    prev = None
    cur = head
    while cur:
        nxt = cur.next
        cur.next = prev
        prev = cur
        cur = nxt
    return prev
''',
      [[[1, 2, 3, 4, 5]], [[1, 2]], [[]], [[7]], [[3, 3, 1]], [[1, 2, 3, 4, 5, 6]]],
      kinds={"head": "linked"}, ret="linked", returns="Return the new head node.",
      hints=["Walk the list with `cur`, keeping the node behind it in `prev`.",
             "Save `cur.next` *before* you overwrite it, or you lose the rest of the list.",
             "When the loop ends, `cur` is `None`. Which variable holds the new head?"]),

    P("middle-node", "Middle of the Linked List", I, "linked-list", "middle_node", ["head"],
      "Return the middle node of a non-empty linked list. If there are two middle nodes, return the second one. "
      "(The answer is shown as the list starting at that node.)",
      '''\
def middle_node(head):
    slow = fast = head
    while fast and fast.next:
        slow = slow.next
        fast = fast.next.next
    return slow
''',
      [[[1, 2, 3, 4, 5]], [[1, 2, 3, 4, 5, 6]], [[1]], [[1, 2]], [[9, 8, 7]]],
      kinds={"head": "linked"}, ret="linked", returns="Return the middle node.",
      hints=["Move one pointer one step and another two steps at a time.",
             "`fast.next.next` crashes if `fast.next` is `None`. Check both `fast` and `fast.next`."]),

    P("merge-lists", "Merge Two Sorted Lists", I, "linked-list", "merge_lists", ["a", "b"],
      "`a` and `b` are the heads of two sorted linked lists. Splice them into one sorted list and return its head.",
      '''\
def merge_lists(a, b):
    dummy = ListNode()
    tail = dummy
    while a and b:
        if a.val <= b.val:
            tail.next = a
            a = a.next
        else:
            tail.next = b
            b = b.next
        tail = tail.next
    tail.next = a or b
    return dummy.next
''',
      [[[1, 2, 4], [1, 3, 4]], [[], []], [[], [0]], [[5], [1, 2, 3]], [[1, 1], [1]], [[2, 6, 9], [1, 7, 8, 10]]],
      kinds={"a": "linked", "b": "linked"}, ret="linked", returns="Return the head of the merged list.",
      hints=["A dummy head node saves you from special-casing the first node.",
             "When one list runs out, attach the remainder of the other."]),

    P("fibonacci", "Fibonacci Number", I, "recursion", "fib", ["n"],
      "Return the `n`-th Fibonacci number, where `fib(0) = 0`, `fib(1) = 1` and "
      "`fib(n) = fib(n - 1) + fib(n - 2)`.",
      '''\
def fib(n):
    if n < 2:
        return n
    return fib(n - 1) + fib(n - 2)
''',
      [[4], [0], [1], [2], [7], [10]],
      constraints=["`0 <= n <= 12`"],
      hints=["Every recursive function needs a base case that returns without calling itself.",
             "There are two base cases here: `n == 0` and `n == 1`."]),

    P("power", "Fast Power", I, "recursion", "power", ["x", "n"],
      "Return `x` raised to the power `n` (`n >= 0`, integers) without using `**` or `pow`. "
      "Aim for O(log n) multiplications.",
      '''\
def power(x, n):
    if n == 0:
        return 1
    half = power(x, n // 2)
    if n % 2 == 0:
        return half * half
    return half * half * x
''',
      [[2, 10], [3, 3], [5, 0], [1, 50], [-2, 3], [7, 1], [2, 15], [0, 4]],
      hints=["`x**n` is `(x**(n//2))**2`, times one more `x` when `n` is odd.",
             "Compute the half power *once* and reuse it."]),

    P("merge-sorted", "Merge Two Sorted Arrays", I, "merge-sort", "merge", ["a", "b"],
      "`a` and `b` are sorted lists. Return one sorted list containing all their elements. Don't use `sort`.",
      '''\
def merge(a, b):
    out = []
    i = j = 0
    while i < len(a) and j < len(b):
        if a[i] <= b[j]:
            out.append(a[i])
            i += 1
        else:
            out.append(b[j])
            j += 1
    out.extend(a[i:])
    out.extend(b[j:])
    return out
''',
      [[[1, 4, 7], [2, 3, 9]], [[], [1]], [[1], []], [[], []], [[1, 1, 1], [1, 1]], [[5, 6], [1, 2, 3]],
       [[-3, 0, 4], [-5, -3, 10, 12]]],
      hints=["Keep one index into each list and repeatedly take the smaller front element.",
             "When one list is used up, the rest of the other still has to be copied."]),

    P("sort-colors", "Sort Colors", I, "quick-sort", "sort_colors", ["nums"],
      "`nums` contains only `0`, `1` and `2`. Sort it **in place** in a single pass, without `sort`.",
      '''\
def sort_colors(nums):
    lo, mid, hi = 0, 0, len(nums) - 1
    while mid <= hi:
        if nums[mid] == 0:
            nums[lo], nums[mid] = nums[mid], nums[lo]
            lo += 1
            mid += 1
        elif nums[mid] == 1:
            mid += 1
        else:
            nums[mid], nums[hi] = nums[hi], nums[mid]
            hi -= 1
''',
      [[[2, 0, 2, 1, 1, 0]], [[2, 0, 1]], [[0]], [[]], [[1, 1, 1]], [[2, 2, 0, 0]], [[1, 2, 0, 1, 2, 0, 0, 1]]],
      output="arg0",
      hints=["This is the partition step of quick sort with three regions: 0s, 1s and 2s.",
             "After swapping a 2 to the back, don't advance `mid`: the element that arrived is unchecked."]),

    # ================================================================ Advanced
    P("max-depth", "Maximum Depth of Binary Tree", A, "bst", "max_depth", ["root"],
      "Return the number of nodes on the longest path from the root down to a leaf. An empty tree has depth 0.",
      '''\
def max_depth(root):
    if root is None:
        return 0
    return 1 + max(max_depth(root.left), max_depth(root.right))
''',
      [[[3, 9, 20, None, None, 15, 7]], [[1, None, 2]], [[]], [[1]], [[1, 2, 3, 4, None, None, None, 5]],
       [[1, 2, 3, 4, 5, 6, 7]]],
      kinds={"root": "tree"},
      hints=["The depth of a tree is 1 plus the deeper of its two subtrees.", "What is the depth of `None`?"]),

    P("invert-tree", "Invert Binary Tree", A, "bst", "invert_tree", ["root"],
      "Mirror a binary tree: swap the left and right child of every node. Return the root.",
      '''\
def invert_tree(root):
    if root is None:
        return None
    root.left, root.right = invert_tree(root.right), invert_tree(root.left)
    return root
''',
      [[[4, 2, 7, 1, 3, 6, 9]], [[2, 1, 3]], [[]], [[1, 2]], [[1, None, 2, None, 3]]],
      kinds={"root": "tree"}, ret="tree", returns="Return the root.",
      hints=["Swap the two children, then do the same inside each child.", "Don't forget to return the root."]),

    P("validate-bst", "Validate Binary Search Tree", A, "bst", "is_valid_bst", ["root"],
      "Return `True` if the tree is a valid binary search tree: for every node, **all** values in its left subtree "
      "are smaller and **all** values in its right subtree are larger.",
      '''\
def is_valid_bst(root):
    def check(node, lo, hi):
        if node is None:
            return True
        if not (lo < node.val < hi):
            return False
        return check(node.left, lo, node.val) and check(node.right, node.val, hi)

    return check(root, float("-inf"), float("inf"))
''',
      [[[2, 1, 3]], [[5, 1, 4, None, None, 3, 6]], [[5, 4, 6, None, None, 3, 7]], [[]], [[1]], [[2, 2, 2]],
       [[10, 5, 15, 2, 7, 12, 20]], [[3, 1, 5, 0, 4]]],
      kinds={"root": "tree"},
      hints=["Comparing a node only with its direct children is not enough. Look at the third example.",
             "Pass down the range `(lo, hi)` that every value in the subtree must stay inside."]),

    P("kth-largest", "Kth Largest Element", A, "heap", "kth_largest", ["nums", "k"],
      "Return the `k`-th largest element of `nums` (`k = 1` is the maximum). Duplicates count separately. "
      "Try it with a heap of size `k` instead of sorting.",
      '''\
import heapq


def kth_largest(nums, k):
    heap = []
    for x in nums:
        heapq.heappush(heap, x)
        if len(heap) > k:
            heapq.heappop(heap)
    return heap[0]
''',
      [[[3, 2, 1, 5, 6, 4], 2], [[3, 2, 3, 1, 2, 4, 5, 5, 6], 4], [[1], 1], [[2, 1], 2], [[7, 7, 7], 2],
       [[-1, -5, -3], 1], [[9, 3, 8, 4, 7, 5, 6], 7]],
      hints=["Keep a min-heap holding the `k` largest numbers seen so far.",
             "When the heap grows past `k`, pop the smallest. The answer is then `heap[0]`."]),

    P("last-stone", "Last Stone Weight", A, "heap", "last_stone", ["stones"],
      "Repeatedly smash the two heaviest stones together. If they weigh the same both are destroyed; otherwise "
      "the lighter one is destroyed and the heavier loses that much weight. Return the weight of the last stone, "
      "or `0` if none is left.",
      '''\
import heapq


def last_stone(stones):
    heap = [-s for s in stones]
    heapq.heapify(heap)
    while len(heap) > 1:
        a = -heapq.heappop(heap)
        b = -heapq.heappop(heap)
        if a != b:
            heapq.heappush(heap, -(a - b))
    return -heap[0] if heap else 0
''',
      [[[2, 7, 4, 1, 8, 1]], [[1]], [[3, 3]], [[]], [[10, 4, 2, 10]], [[1, 3]], [[5, 5, 5]]],
      hints=["`heapq` is a min-heap. Store negated weights to pop the heaviest first.",
             "The heap can end up empty. What should you return then?"]),

    P("num-islands", "Number of Islands", A, "bfs", "num_islands", ["grid"],
      "`grid` is a 2D list of `1` (land) and `0` (water). An island is a group of land cells connected "
      "horizontally or vertically. Return the number of islands.",
      '''\
from collections import deque


def num_islands(grid):
    if not grid:
        return 0
    rows, cols = len(grid), len(grid[0])
    seen = set()
    count = 0
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == 1 and (r, c) not in seen:
                count += 1
                seen.add((r, c))
                queue = deque([(r, c)])
                while queue:
                    y, x = queue.popleft()
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < rows and 0 <= nx < cols and grid[ny][nx] == 1 and (ny, nx) not in seen:
                            seen.add((ny, nx))
                            queue.append((ny, nx))
    return count
''',
      [[[[1, 1, 0, 0], [1, 0, 0, 1], [0, 0, 1, 1]]], [[[1, 0, 1], [0, 1, 0], [1, 0, 1]]], [[[0, 0], [0, 0]]],
       [[]], [[[1]]], [[[1, 1, 1], [1, 0, 1], [1, 1, 1]]], [[[1, 0, 0, 1, 1], [0, 0, 0, 0, 1], [1, 1, 0, 0, 0]]]],
      hints=["Scan every cell. Each time you find unvisited land, that's a new island: flood it with BFS or DFS.",
             "Check that a neighbour is inside the grid *before* reading `grid[ny][nx]`. "
             "Negative indexes don't crash in Python, they wrap around."]),

    P("level-order", "Binary Tree Level Order Traversal", A, "bfs", "level_order", ["root"],
      "Return the values of the tree level by level, top to bottom, each level left to right, "
      "as a list of lists.",
      '''\
from collections import deque


def level_order(root):
    if root is None:
        return []
    out = []
    queue = deque([root])
    while queue:
        level = []
        for _ in range(len(queue)):
            node = queue.popleft()
            level.append(node.val)
            if node.left:
                queue.append(node.left)
            if node.right:
                queue.append(node.right)
        out.append(level)
    return out
''',
      [[[3, 9, 20, None, None, 15, 7]], [[1]], [[]], [[1, 2, 3, 4, 5]], [[1, None, 2, None, 3]]],
      kinds={"root": "tree"},
      hints=["BFS with a queue visits nodes level by level.",
             "The queue's length at the start of a round is exactly the size of that level."]),

    P("flood-fill", "Flood Fill", A, "dfs", "flood_fill", ["image", "sr", "sc", "color"],
      "Starting at pixel `(sr, sc)`, repaint it and every pixel connected to it (up, down, left, right) that has "
      "the same original colour with `color`. Return the image.",
      '''\
def flood_fill(image, sr, sc, color):
    old = image[sr][sc]
    if old == color:
        return image

    def fill(r, c):
        if r < 0 or c < 0 or r >= len(image) or c >= len(image[0]) or image[r][c] != old:
            return
        image[r][c] = color
        fill(r + 1, c)
        fill(r - 1, c)
        fill(r, c + 1)
        fill(r, c - 1)

    fill(sr, sc)
    return image
''',
      [[[[1, 1, 1], [1, 1, 0], [1, 0, 1]], 1, 1, 2], [[[0, 0, 0], [0, 0, 0]], 0, 0, 0], [[[5]], 0, 0, 7],
       [[[1, 2], [2, 1]], 0, 0, 3], [[[0, 1, 0], [1, 1, 1], [0, 1, 0]], 1, 1, 9]],
      visible=2,
      hints=["Recursive DFS: paint the cell, then recurse into the four neighbours.",
             "If the new colour equals the old one, the recursion never stops. See the second example."]),

    P("count-components", "Number of Connected Components", A, "dfs", "count_components", ["n", "edges"],
      "There are `n` nodes numbered `0` to `n - 1` and a list of undirected `edges`. "
      "Return how many connected components the graph has.",
      '''\
def count_components(n, edges):
    graph = {i: [] for i in range(n)}
    for a, b in edges:
        graph[a].append(b)
        graph[b].append(a)
    seen = set()

    def dfs(node):
        seen.add(node)
        for nxt in graph[node]:
            if nxt not in seen:
                dfs(nxt)

    count = 0
    for i in range(n):
        if i not in seen:
            count += 1
            dfs(i)
    return count
''',
      [[5, [[0, 1], [1, 2], [3, 4]]], [5, [[0, 1], [1, 2], [2, 3], [3, 4]]], [1, []], [4, []], [0, []],
       [6, [[0, 1], [2, 3], [4, 5], [1, 2]]], [3, [[0, 1], [1, 2], [2, 0]]]],
      hints=["Build an adjacency dict first, with an entry for *every* node, even isolated ones.",
             "Each DFS started from an unvisited node discovers exactly one component.",
             "Union-Find solves this too."]),

    P("network-delay", "Network Delay Time", A, "dijkstra", "network_delay", ["times", "n", "k"],
      "A network has nodes `1..n`. Each entry of `times` is `[u, v, w]`: a signal takes `w` time to travel from "
      "`u` to `v` (one direction). A signal starts at node `k`. Return the time until **all** nodes have received "
      "it, or `-1` if some node is unreachable.",
      '''\
import heapq


def network_delay(times, n, k):
    graph = {i: [] for i in range(1, n + 1)}
    for u, v, w in times:
        graph[u].append((v, w))
    dist = {}
    heap = [(0, k)]
    while heap:
        d, node = heapq.heappop(heap)
        if node in dist:
            continue
        dist[node] = d
        for nxt, w in graph[node]:
            if nxt not in dist:
                heapq.heappush(heap, (d + w, nxt))
    return max(dist.values()) if len(dist) == n else -1
''',
      [[[[2, 1, 1], [2, 3, 1], [3, 4, 1]], 4, 2], [[[1, 2, 1]], 2, 1], [[[1, 2, 1]], 2, 2], [[], 1, 1],
       [[[1, 2, 5], [1, 3, 1], [3, 2, 1], [2, 4, 2]], 4, 1], [[[1, 2, 1], [2, 1, 3]], 2, 2]],
      hints=["This is Dijkstra: the answer is the largest of the shortest distances from `k`.",
             "Pop the closest unfinished node from a heap of `(distance, node)`.",
             "If fewer than `n` nodes were reached, return -1."]),

    P("provinces", "Number of Provinces", A, "union-find", "find_provinces", ["connected"],
      "`connected[i][j] == 1` means city `i` and city `j` are directly connected. A province is a group of cities "
      "connected directly or indirectly. Return the number of provinces.",
      '''\
def find_provinces(connected):
    n = len(connected)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    count = n
    for i in range(n):
        for j in range(i + 1, n):
            if connected[i][j]:
                a, b = find(i), find(j)
                if a != b:
                    parent[a] = b
                    count -= 1
    return count
''',
      [[[[1, 1, 0], [1, 1, 0], [0, 0, 1]]], [[[1, 0, 0], [0, 1, 0], [0, 0, 1]]], [[[1]]],
       [[[1, 1, 1], [1, 1, 1], [1, 1, 1]]], [[[1, 0, 0, 1], [0, 1, 1, 0], [0, 1, 1, 1], [1, 0, 1, 1]]], [[]]],
      hints=["Union-Find: start with `n` groups and merge two groups whenever cities are connected.",
             "Only count a merge when the two cities had *different* roots.",
             "In `find`, make sure `x` actually moves towards the root, or the loop never ends."]),

    P("unique-paths", "Unique Paths", A, "dp-grid", "unique_paths", ["m", "n"],
      "A robot starts in the top-left cell of an `m` × `n` grid and can only move right or down. "
      "Return how many different paths reach the bottom-right cell.",
      '''\
def unique_paths(m, n):
    dp = [[1] * n for _ in range(m)]
    for r in range(1, m):
        for c in range(1, n):
            dp[r][c] = dp[r - 1][c] + dp[r][c - 1]
    return dp[m - 1][n - 1]
''',
      [[3, 3], [3, 2], [1, 1], [1, 5], [4, 4], [2, 6], [5, 3]],
      constraints=["`1 <= m, n <= 6`"],
      hints=["Paths into a cell = paths into the cell above + paths into the cell to the left.",
             "Every cell in the first row and first column has exactly one path.",
             "`[[0] * n] * m` makes `m` references to the *same* row. Build each row separately."]),

    P("min-path-sum", "Minimum Path Sum", A, "dp-grid", "min_path_sum", ["grid"],
      "Move from the top-left to the bottom-right of a non-empty `grid` of non-negative numbers, going only right "
      "or down. Return the smallest possible sum of the cells on the path.",
      '''\
def min_path_sum(grid):
    rows, cols = len(grid), len(grid[0])
    dp = [[0] * cols for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            if r == 0 and c == 0:
                best = 0
            elif r == 0:
                best = dp[r][c - 1]
            elif c == 0:
                best = dp[r - 1][c]
            else:
                best = min(dp[r - 1][c], dp[r][c - 1])
            dp[r][c] = grid[r][c] + best
    return dp[rows - 1][cols - 1]
''',
      [[[[1, 3, 1], [1, 5, 1], [4, 2, 1]]], [[[1, 2, 3], [4, 5, 6]]], [[[7]]], [[[1, 2, 3]]], [[[1], [2], [3]]],
       [[[5, 1, 9], [1, 1, 9], [9, 1, 1]]]],
      explain=["1 → 3 → 1 → 1 → 1"],
      hints=["`dp[r][c]` = cheapest way to reach that cell.",
             "The first row and first column each have only one way in. `dp[r - 1]` with `r = 0` silently reads the "
             "*last* row."]),

    P("climb-stairs", "Climbing Stairs", A, "dp-memo", "climb_stairs", ["n"],
      "You climb a staircase of `n` steps, taking 1 or 2 steps at a time. Return the number of distinct ways to "
      "reach the top.",
      '''\
def climb_stairs(n):
    a, b = 1, 1
    for _ in range(n):
        a, b = b, a + b
    return a
''',
      [[2], [3], [1], [5], [10], [20], [30]],
      explain=["1+1, 2", "1+1+1, 1+2, 2+1"],
      hints=["The last move was either 1 step or 2 steps: `ways(n) = ways(n - 1) + ways(n - 2)`.",
             "Plain recursion is too slow for `n = 30`. Remember answers in a dict, or build up from the bottom."]),

    P("house-robber", "House Robber", A, "dp-memo", "rob", ["nums"],
      "`nums[i]` is the money in house `i` along a street. You can't rob two adjacent houses. "
      "Return the most money you can take.",
      '''\
def rob(nums):
    take, skip = 0, 0
    for x in nums:
        take, skip = skip + x, max(skip, take)
    return max(take, skip)
''',
      [[[1, 2, 3, 1]], [[2, 7, 9, 3, 1]], [[]], [[5]], [[2, 1, 1, 2]], [[4, 4]], [[10, 1, 1, 10, 1, 1, 10]]],
      explain=["Rob houses 0 and 2: 1 + 3.", "Rob houses 0, 2 and 4: 2 + 9 + 1."],
      hints=["For each house: either rob it (plus the best up to two houses back) or skip it.",
             "Try `[2, 1, 1, 2]`. Taking every other house isn't always best."]),

    P("coin-change", "Coin Change", A, "dp-memo", "coin_change", ["coins", "amount"],
      "Return the fewest coins needed to make exactly `amount` using any number of each coin in `coins`, "
      "or `-1` if it can't be done.",
      '''\
def coin_change(coins, amount):
    INF = float("inf")
    dp = [0] + [INF] * amount
    for a in range(1, amount + 1):
        for c in coins:
            if c <= a and dp[a - c] + 1 < dp[a]:
                dp[a] = dp[a - c] + 1
    return dp[amount] if dp[amount] != INF else -1
''',
      [[[1, 2, 5], 11], [[2], 3], [[1], 0], [[1, 3, 4], 6], [[5, 10], 3], [[2, 5, 10, 1], 27], [[3, 7], 13]],
      explain=["5 + 5 + 1"],
      hints=["`dp[a]` = fewest coins for amount `a`; try every coin as the last one used.",
             "Greedy (always the biggest coin) fails on `[1, 3, 4]`, amount 6.",
             "Guard `a - c >= 0`: a negative index reads from the end of the list."]),

    P("subsets", "Subsets", A, "backtracking", "subsets", ["nums"],
      "`nums` has distinct numbers. Return every possible subset, including the empty one. Any order is fine.",
      '''\
def subsets(nums):
    result = []
    path = []

    def backtrack(start):
        result.append(path[:])
        for i in range(start, len(nums)):
            path.append(nums[i])
            backtrack(i + 1)
            path.pop()

    backtrack(0)
    return result
''',
      [[[1, 2, 3]], [[0]], [[]], [[4, 5]], [[1, 2, 3, 4]]],
      compare="unordered2",
      hints=["For each number choose: in or out.",
             "Append a *copy* (`path[:]`). Appending `path` itself stores the same list over and over.",
             "Undo your choice (`path.pop()`) after the recursive call."]),

    P("permutations", "Permutations", A, "backtracking", "permute", ["nums"],
      "`nums` has distinct numbers. Return all of their orderings, in any order.",
      '''\
def permute(nums):
    result = []
    path = []
    used = [False] * len(nums)

    def backtrack():
        if len(path) == len(nums):
            result.append(path[:])
            return
        for i in range(len(nums)):
            if not used[i]:
                used[i] = True
                path.append(nums[i])
                backtrack()
                path.pop()
                used[i] = False

    backtrack()
    return result
''',
      [[[1, 2, 3]], [[0, 1]], [[1]], [[]], [[5, 6, 7, 8]]],
      compare="unordered",
      hints=["Build the ordering one position at a time, skipping numbers already used.",
             "When the path is full, save a copy and return."]),
]

LEVELS = [B, I, A]


def by_id(problem_id: str) -> dict | None:
    for p in PROBLEMS:
        if p["id"] == problem_id:
            return p
    return None
