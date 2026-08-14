"""Card primitives and a 7-card hand evaluator (Cactus Kev style).

Card encoding: int 0..51. rank = card // 4 (0=2 ... 12=A), suit = card % 4.
Suit order: 0=clubs, 1=diamonds, 2=hearts, 3=spades.
Hand strength: 1 (worst) .. 7462 (royal flush), monotonic with hand value.
"""
from __future__ import annotations

from itertools import combinations

RANK_NAMES = "23456789TJQKA"
SUIT_NAMES = "cdhs"
RANK_IDX = {r: i for i, r in enumerate(RANK_NAMES)}
SUIT_IDX = {s: i for i, s in enumerate(SUIT_NAMES)}
PRIMES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41)

# Category names ordered weakest -> strongest, matching value ranges below.
CATEGORIES = (
    "High Card",
    "One Pair",
    "Two Pair",
    "Three of a Kind",
    "Straight",
    "Flush",
    "Full House",
    "Four of a Kind",
    "Straight Flush",
)

# Category value ranges (1-based, contiguous, ordered by strength).
_CAT_RANGES = (
    (1, 1277),          # High Card (1277)
    (1278, 4137),       # One Pair (2860)
    (4138, 4995),       # Two Pair (858)
    (4996, 5853),       # Three of a Kind (858)
    (5854, 5863),       # Straight (10)
    (5864, 7140),       # Flush (1277)
    (7141, 7296),       # Full House (156)
    (7297, 7452),       # Four of a Kind (156)
    (7453, 7462),       # Straight Flush (10)
)

NONFLUSH = {}  # prime product of 5 ranks -> strength
FLUSH = {}     # 13-bit mask of 5 ranks -> strength


def make_card(rank: str | int, suit: str | int) -> int:
    """Build a card from rank ('2'..'A' or 0..12) and suit ('c','d','h','s' or 0..3)."""
    if isinstance(rank, str):
        if rank not in RANK_IDX:
            raise ValueError(f"invalid rank: {rank!r}")
        rank = RANK_IDX[rank]
    if isinstance(suit, str):
        if suit not in SUIT_IDX:
            raise ValueError(f"invalid suit: {suit!r}")
        suit = SUIT_IDX[suit]
    return rank * 4 + suit


def parse_card(text: str) -> int:
    """Parse 'As', 'Td', '2c' etc. -> int card."""
    text = text.strip()
    if len(text) != 2:
        raise ValueError(f"invalid card: {text!r}")
    return make_card(text[0], text[1])


def parse_cards(text: str) -> list[int]:
    return [parse_card(c) for c in text.replace(",", " ").split()]


def card_str(card: int) -> str:
    return RANK_NAMES[card // 4] + SUIT_NAMES[card % 4]


def hand_str(cards) -> str:
    return " ".join(card_str(c) for c in cards)


def card_mask(cards) -> int:
    """Bitmask over 52 cards (bit i set iff card i present)."""
    m = 0
    for c in cards:
        m |= 1 << c
    return m


def is_royal_flush(cards) -> bool:
    return evaluate(cards) == 7462


def _rank_counts(ranks: tuple[int, ...]) -> list[int]:
    counts = [0] * 13
    for r in ranks:
        counts[r] += 1
    return counts


def _pattern_key(ranks: tuple[int, ...]) -> tuple[int, tuple]:
    """Sortable key for a 5-card rank multiset: (category, within-category)."""
    counts = _rank_counts(ranks)
    freq = sorted(counts, reverse=True)

    def straight_high(rs) -> int:
        s = sorted(rs)
        if s == [0, 1, 2, 3, 12]:
            return 3  # wheel
        if all(s[i + 1] - s[i] == 1 for i in range(4)):
            return s[4]
        return -1

    if freq[0] == 4:
        quad = next(r for r in range(13) if counts[r] == 4)
        kicker = next(r for r in range(13) if counts[r] == 1)
        return (7, (quad, kicker))
    if freq[0] == 3 and freq[1] == 2:
        trip = next(r for r in range(13) if counts[r] == 3)
        pair = next(r for r in range(13) if counts[r] == 2)
        return (6, (trip, pair))
    if freq[0] == 3:
        trip = next(r for r in range(13) if counts[r] == 3)
        kickers = tuple(sorted((r for r in range(13) if counts[r] == 1), reverse=True))
        return (3, (trip,) + kickers)
    if freq[0] == 2 and freq[1] == 2:
        pairs = tuple(sorted((r for r in range(13) if counts[r] == 2), reverse=True))
        kicker = next(r for r in range(13) if counts[r] == 1)
        return (2, pairs + (kicker,))
    if freq[0] == 2:
        pair = next(r for r in range(13) if counts[r] == 2)
        kickers = tuple(sorted((r for r in range(13) if counts[r] == 1), reverse=True))
        return (1, (pair,) + kickers)
    sh = straight_high(ranks)
    if sh >= 0:
        return (4, (sh,))
    desc = tuple(sorted(ranks, reverse=True))
    return (0, desc)


def _build_tables() -> None:
    """Generate the 5-card lookup tables.

    NONFLUSH: prime product of a 5-rank multiset -> strength 1..7462.
    FLUSH: 13-bit mask of 5 distinct ranks -> strength 1..7462.
    Values within each category are assigned sequentially by pattern key, so
    both tables produce a globally consistent total order.
    """
    from itertools import combinations_with_replacement
    from collections import defaultdict

    def product(combo) -> int:
        p = 1
        for r in combo:
            p *= PRIMES[r]
        return p

    groups: dict[int, list] = defaultdict(list)
    for combo in combinations_with_replacement(range(13), 5):
        if max(_rank_counts(combo)) > 4:
            continue  # impossible: a rank appears 5 times in one hand
        groups[_pattern_key(combo)[0]].append(combo)
    for cat in range(9):
        lo, _ = _CAT_RANGES[cat]
        for j, combo in enumerate(sorted(groups[cat], key=_pattern_key)):
            NONFLUSH[product(combo)] = lo + j

    # FLUSH: non-straight rank sets fill the flush range; straight rank sets
    # fill the straight-flush range (same ordering as the straight group).
    flush_sets = [c for c in combinations(range(13), 5) if _pattern_key(c)[0] != 4]
    lo, _ = _CAT_RANGES[5]
    for j, combo in enumerate(sorted(flush_sets, key=_pattern_key)):
        mask = 0
        for r in combo:
            mask |= 1 << r
        FLUSH[mask] = lo + j
    lo, _ = _CAT_RANGES[8]
    for j, combo in enumerate(sorted(groups[4], key=_pattern_key)):
        mask = 0
        for r in combo:
            mask |= 1 << r
        FLUSH[mask] = lo + j


_build_tables()
del _build_tables


def evaluate_5(cards) -> int:
    """Evaluate exactly 5 cards -> strength 1..7462."""
    r0, r1, r2, r3, r4 = (c // 4 for c in cards)
    if (cards[0] & 3) == (cards[1] & 3) == (cards[2] & 3) == (cards[3] & 3) == (cards[4] & 3):
        return FLUSH[(1 << r0) | (1 << r1) | (1 << r2) | (1 << r3) | (1 << r4)]
    return NONFLUSH[PRIMES[r0] * PRIMES[r1] * PRIMES[r2] * PRIMES[r3] * PRIMES[r4]]


# ------------------------------------------------------------------ batched
# Dense lookup tables for vectorized evaluation.
STRENGTH5: "np.ndarray | None" = None      # index = rank0*13^4+...+rank4 (any order)
FLUSH5: "np.ndarray | None" = None         # index = 13-bit rank mask
_SUBSET_IDX: "np.ndarray | None" = None    # (21, 5) indices of 5-of-7 subsets


def _build_dense():
    """Lazily build dense 5-card tables + subset indices (once)."""
    global STRENGTH5, FLUSH5, _SUBSET_IDX
    import numpy as np
    from itertools import combinations_with_replacement, permutations

    if STRENGTH5 is not None:
        return
    s5 = np.zeros(13 ** 5, dtype=np.int16)
    for combo in combinations_with_replacement(range(13), 5):
        if max(_rank_counts(combo)) > 4:
            continue  # 5-of-a-kind impossible in a real deck
        p = 1
        for r in combo:
            p *= PRIMES[r]
        val = NONFLUSH[p]
        for perm in permutations(combo):
            idx = 0
            for r in perm:
                idx = idx * 13 + r
            s5[idx] = val
    STRENGTH5 = s5
    f5 = np.zeros(1 << 13, dtype=np.int16)
    for mask, val in FLUSH.items():
        f5[mask] = val
    FLUSH5 = f5
    _SUBSET_IDX = np.array(list(combinations(range(7), 5)), dtype=np.int16)


def evaluate_7_batch(hand_cards, board_cards) -> "np.ndarray":
    """Vectorized 7-card evaluation: (N, 2) hands vs one 5-card board -> (N,).

    Hands that share a card with the board return 0.
    """
    import numpy as np

    _build_dense()
    hands = np.asarray(hand_cards, dtype=np.int16)
    board = np.asarray(board_cards, dtype=np.int16)
    n = hands.shape[0]
    ranks = np.empty((n, 7), dtype=np.int16)
    suits = np.empty((n, 7), dtype=np.int16)
    ranks[:, :2] = hands // 4
    ranks[:, 2:] = board // 4
    suits[:, :2] = hands % 4
    suits[:, 2:] = board % 4

    r5 = ranks[:, _SUBSET_IDX]            # (n, 21, 5)
    s5 = suits[:, _SUBSET_IDX]
    idx = np.zeros((n, 21), dtype=np.int32)
    mask = np.zeros((n, 21), dtype=np.int16)
    for k in range(5):
        idx = idx * 13 + r5[:, :, k]
        mask |= 1 << r5[:, :, k]
    is_flush = (s5 == s5[:, :, :1]).all(axis=2)
    best = np.where(is_flush, FLUSH5[mask], STRENGTH5[idx]).max(axis=1)

    dead = np.isin(hands, board).any(axis=1)
    best[dead] = 0
    return best.astype(np.int32)


_CACHE: dict[tuple[int, ...], int] = {}


def evaluate(cards) -> int:
    """Evaluate 5, 6 or 7 cards -> best 5-card strength (memoized)."""
    key = tuple(sorted(cards))
    cached = _CACHE.get(key)
    if cached is not None:
        return cached
    n = len(key)
    best = 0
    if n == 5:
        best = evaluate_5(key)
    else:
        for combo in combinations(key, 5):
            v = evaluate_5(combo)
            if v > best:
                best = v
    if len(_CACHE) < 4_000_000:
        _CACHE[key] = best
    return best


def evaluate_vectorized(hand_cards: "np.ndarray", board_cards: "np.ndarray"):
    """Evaluate many hands vs a single board.

    hand_cards: (N, 2) int array, board_cards: (K, 5) int array or None.
    Returns (N, K) strength array.
    """
    import numpy as np

    hands, boards = np.asarray(hand_cards), np.asarray(board_cards)
    N = hands.shape[0]
    K = 1 if boards.ndim == 1 else boards.shape[0]
    out = np.empty((N, K), dtype=np.int32)
    for i in range(N):
        h = hands[i]
        for j in range(K):
            b = boards if boards.ndim == 1 else boards[j]
            out[i, j] = evaluate((int(h[0]), int(h[1]), int(b[0]), int(b[1]), int(b[2]), int(b[3]), int(b[4])))
    return out


def category_of(strength: int) -> str:
    for name, (lo, hi) in zip(CATEGORIES, _CAT_RANGES):
        if lo <= strength <= hi:
            return name
    raise ValueError(f"invalid strength {strength}")


class Deck:
    """Standard 52-card deck with deterministic seeding."""

    def __init__(self, seed: int | None = None):
        self.cards = list(range(52))
        if seed is not None:
            import random

            random.Random(seed).shuffle(self.cards)

    def deal(self, n: int) -> list[int]:
        if n > len(self.cards):
            raise ValueError("not enough cards")
        dealt = self.cards[:n]
        del self.cards[:n]
        return dealt