"""Range representation and parsing.

A Range is a float64 weight vector over the 1326 two-card combos
(canonical order: COMBOS[i]). Weights are typically 0..1 (proportion of the
combo the player plays) or counts for card-removal-aware training.
"""
from __future__ import annotations

import numpy as np
from .cards import RANK_NAMES, RANK_IDX, evaluate

# Canonical combo list: (c1, c2) with c1 < c2.
COMBOS = tuple(
    (c1, c2) for c1 in range(52) for c2 in range(c1 + 1, 52)
)
COMBO_INDEX = {combo: i for i, combo in enumerate(COMBOS)}
NUM_COMBOS = 1326

# Suit symmetry: canonical "broadcast" hands per rank pair.
# hand_type: 0=pair, 1=suited, 2=offsuit
HAND_TYPES = ("Pair", "Suited", "Offsuit")


def hand_of_combo(combo: tuple[int, int]) -> tuple[str, int, int, int]:
    """(name like 'AKs', hand_type, high_rank, low_rank)."""
    c1, c2 = combo
    r1, r2 = c1 // 4, c2 // 4
    if r1 == r2:
        return (RANK_NAMES[r1] * 2, 0, r1, r1)
    if c1 % 4 == c2 % 4:
        return (RANK_NAMES[max(r1, r2)] + RANK_NAMES[min(r1, r2)] + "s", 1, max(r1, r2), min(r1, r2))
    return (RANK_NAMES[max(r1, r2)] + RANK_NAMES[min(r1, r2)] + "o", 2, max(r1, r2), min(r1, r2))


class Range:
    """Weight vector over the 1326 combos."""

    __slots__ = ("weights",)

    def __init__(self, weights=None):
        if weights is None:
            self.weights = np.zeros(NUM_COMBOS, dtype=np.float64)
        else:
            self.weights = np.asarray(weights, dtype=np.float64)
            if self.weights.shape != (NUM_COMBOS,):
                raise ValueError(f"range must have {NUM_COMBOS} entries")

    def copy(self) -> "Range":
        return Range(self.weights.copy())

    def normalize(self) -> "Range":
        s = self.weights.sum()
        if s > 0:
            self.weights /= s
        return self

    def total(self) -> float:
        return float(self.weights.sum())

    def combos(self, min_weight: float = 0.5) -> list[tuple[int, int]]:
        """Combos present with weight >= min_weight (default: played)."""
        return [COMBOS[i] for i in range(NUM_COMBOS) if self.weights[i] >= min_weight]

    def add(self, other: "Range", scale: float = 1.0) -> "Range":
        self.weights += scale * other.weights
        return self

    def remove(self, other: "Range") -> "Range":
        self.weights -= other.weights
        np.maximum(self.weights, 0.0, out=self.weights)
        return self

    def mask_out_cards(self, cards) -> "Range":
        """Zero out any combo containing one of the given cards."""
        m = np.ones(NUM_COMBOS, dtype=bool)
        for c in cards:
            m &= np.array(
                [(c not in combo) for combo in COMBOS], dtype=bool
            )
        self.weights[m == False] = 0.0  # noqa: E712
        return self

    def __len__(self) -> int:
        return int((self.weights > 0).sum())

    def __repr__(self) -> str:
        return f"Range({len(self)} combos, total {self.total():.4f})"

    # ------------------------------------------------------------------ text

    def from_text(self, text: str) -> "Range":
        """Parse e.g. 'AA, AKs, A5s-A2s, KQo, 22-77, ATs+'."""
        self.weights[:] = 0.0
        for part in text.replace(",", " ").split():
            for combo in _expand_part(part):
                self.weights[COMBO_INDEX[combo]] = 1.0
        return self

    def to_text(self, min_weight: float = 0.5) -> str:
        """Compact name list, e.g. 'AA, AKs, AQs'."""
        names = {}
        for i in range(NUM_COMBOS):
            if self.weights[i] >= min_weight:
                name, *_ = hand_of_combo(COMBOS[i])
                names[name] = True
        return ", ".join(sorted(names, key=_sort_key))

    def grid(self, min_weight: float = 0.5) -> str:
        """13x13 grid (rows: high card A..2, cols: low card A..2)."""
        cells = [["--"] * 13 for _ in range(13)]
        for i in range(NUM_COMBOS):
            if self.weights[i] < min_weight:
                continue
            name, t, hi, lo = hand_of_combo(COMBOS[i])
            if t == 0:
                cells[12 - hi][12 - lo] = name
            elif t == 1:
                cells[12 - hi][12 - lo] = name
            else:
                cells[12 - lo][12 - hi] = name
        head = "    " + " ".join(f"{RANK_NAMES[r]:>2}" for r in reversed(range(13)))
        lines = [head]
        for i in range(13):
            lines.append(f"{RANK_NAMES[12 - i]:>2}  " + " ".join(f"{cells[i][j]:>2}" for j in range(13)))
        return "\n".join(lines)

    # ---------------------------------------------------------------- equity

    def equity_vs_combo(self, hero: tuple[int, int], board: tuple[int, ...] = ()) -> float:
        """Weighted equity of hero combo vs this range on a 3+ card board."""
        if len(board) < 3:
            raise ValueError("equity_vs_combo requires a flop or later board; use monte_carlo_equity preflop")
        weights = self.weights.copy()
        hero_set = set(hero)
        for i in range(NUM_COMBOS):
            c1, c2 = COMBOS[i]
            if c1 in hero_set or c2 in hero_set:
                weights[i] = 0.0
        if weights.sum() == 0:
            return 0.0
        wins = 0.0
        tot = 0.0
        hero_st = evaluate((*hero, *board))
        for i in range(NUM_COMBOS):
            w = weights[i]
            if w == 0:
                continue
            c1, c2 = COMBOS[i]
            v_st = evaluate((c1, c2, *board))
            if hero_st > v_st:
                wins += w
            elif hero_st == v_st:
                wins += 0.5 * w
            tot += w
        return wins / tot if tot else 0.0


def monte_carlo_equity(hero: tuple[int, int], villain: Range, board: tuple[int, ...] = (), trials: int = 20000, rng=None) -> float:
    """Monte Carlo equity of hero vs villain range."""
    import random as _random

    rng = rng or _random.Random()
    dead = set(hero) | set(board)
    weights = villain.weights.copy()
    idx = [i for i in range(NUM_COMBOS) if weights[i] > 0]
    weights = weights[idx]
    weights /= weights.sum()
    if not idx:
        return 0.0
    if trials < 0:
        raise ValueError("trials must be >= 0")
    wins = ties = 0.0
    deck = [c for c in range(52) if c not in dead]
    n_board = 5 - len(board)
    for _ in range(trials):
        vi = rng.choices(idx, weights=weights)[0]
        c1, c2 = COMBOS[vi]
        if c1 in dead or c2 in dead:
            continue
        remaining = [c for c in deck if c not in (c1, c2)]
        runout = board + tuple(rng.sample(remaining, n_board))
        hs, vs = evaluate((*hero, *runout)), evaluate((c1, c2, *runout))
        if hs > vs:
            wins += 1
        elif hs == vs:
            ties += 1
    return (wins + 0.5 * ties) / trials


def _expand_part(part: str) -> list[tuple[int, int]]:
    """Expand a single hand expression like 'AA', 'AKs', 'A5s-A2s', '22+'."""
    part = part.upper()
    if "-" in part:
        lo_s, hi_s = part.split("-")
        lo = _base_combo(lo_s)
        hi = _base_combo(hi_s)
        return _between(lo, hi)
    if part.endswith("+"):
        base = _base_combo(part[:-1])
        return _plus(base)
    return _combo_cards(*_base_combo(part))


def _base_combo(name: str) -> tuple[str, int, int]:
    if len(name) == 2:  # pair
        if name[0] not in RANK_IDX:
            raise ValueError(f"invalid hand: {name!r}")
        return (name, 0, RANK_IDX[name[0]], RANK_IDX[name[0]])
    if len(name) == 3 and name[2] == "S" and name[0] in RANK_IDX and name[1] in RANK_IDX:
        return (name, 1, RANK_IDX[name[0]], RANK_IDX[name[1]])
    if len(name) == 3 and name[2] == "O" and name[0] in RANK_IDX and name[1] in RANK_IDX:
        return (name, 2, RANK_IDX[name[0]], RANK_IDX[name[1]])
    raise ValueError(f"invalid hand: {name!r}")


def _combo_cards(name: str, t: int, hi: int, lo: int) -> list[tuple[int, int]]:
    out = []
    if t == 0:
        for s1 in range(4):
            for s2 in range(s1 + 1, 4):
                out.append((hi * 4 + s1, hi * 4 + s2))
        return out
    for s1 in range(4):
        for s2 in range(4):
            c1, c2 = hi * 4 + s1, lo * 4 + s2
            if t == 1 and s1 == s2:
                out.append((min(c1, c2), max(c1, c2)))
            elif t == 2 and s1 != s2:
                out.append((min(c1, c2), max(c1, c2)))
    return out


def _sort_key(name: str):
    hi = RANK_IDX[name[0]]
    lo = RANK_IDX[name[1]] if len(name) > 1 else hi
    return (-hi, -lo)


def _between(lo, hi) -> list[tuple[int, int]]:
    """All combos from hand lo to hand hi (same type)."""
    t = lo[1]
    hi_r, lo_r = max(lo[2], hi[2]), min(lo[2], hi[2])
    if t == 0:
        return [c for r in range(lo_r, hi_r + 1) for c in _combo_cards("", 0, r, r)]
    out = []
    for h in range(lo_r, hi_r + 1):
        for l in range(lo_r, h):
            out.extend(_combo_cards("", t, h, l))
    return out


def _plus(base) -> list[tuple[int, int]]:
    """'X+' -> all hands at least as strong as X in its family."""
    t, hi, lo = base[1], base[2], base[3]
    if t == 0:
        return [c for r in range(hi, 13) for c in _combo_cards("", 0, r, r)]
    out = []
    for h in range(hi, 13):
        for l in range(lo, h):
            out.extend(_combo_cards("", t, h, l))
    return out