"""Exact Malmuth-Harville ICM (Independent Chip Model).

`icm_equities(stacks, payouts)` returns each player's tournament equity
(probability-weighted share of the payout pool, summing to sum(payouts)),
computed exactly via the Harville recursion with memoization.

`ICMPayoff` plugs into the MCCFR solver as `SolverConfig.payoff`: it maps a
hand outcome (win/lose/split/fold) to the player's tournament-equity delta
in big blinds, which is exactly what the solver's regret minimisation needs
for 8-max MTT push/fold spots.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np

from .game import BB


@lru_cache(maxsize=None)
def _finish_prob(S: tuple, i: int, k: int) -> float:
    """P(player i finishes exactly k-th) among the players in S.

    Harville recursion: someone else wins first, then i must finish (k-1)-th
    among the rest. Chips tie-break naturally through the probabilities.
    """
    total_chips = sum(S)
    if total_chips == 0:
        return 0.0
    if k == 1:
        return S[i] / total_chips
    total = 0.0
    for j in range(len(S)):
        if j == i:
            continue
        pj = S[j] / total_chips
        if pj == 0:
            continue
        S2 = S[:j] + S[j + 1 :]
        i2 = i if i < j else i - 1
        total += pj * _finish_prob(S2, i2, k - 1)
    return total


def icm_equities(stacks, payouts) -> np.ndarray:
    """Exact ICM equities (share of payout pool) for each player.

    stacks:  iterable of int chips; payouts: iterable of prizes (1st, 2nd, ...).
    A player with 0 chips gets 0 equity. The result sums to sum(payouts).
    """
    stacks = tuple(int(s) for s in stacks)
    payouts = tuple(float(p) for p in payouts)
    if len(stacks) < 2:
        raise ValueError("need at least 2 players")
    if len(payouts) < len(stacks):
        payouts = payouts + (0.0,) * (len(stacks) - len(payouts))
    n = len(stacks)
    eqs = np.zeros(n)
    for i in range(n):
        eq = 0.0
        for k in range(1, n + 1):
            eq += _finish_prob(stacks, i, k) * payouts[k - 1]
        eqs[i] = eq
    return eqs


def chip_equities(stacks) -> np.ndarray:
    """ChipEV: equity when payouts are exactly proportional to chips."""
    s = np.asarray(stacks, dtype=float)
    return s / s.sum()


class ICMPayoff:
    """Solver payoff hook: tournament equity delta in bb for a hand outcome.

    The solver alternates the traverser (0 = SB, 1 = BB); this callable is
    symmetric, so the returned value is always the *traverser's* equity delta.

    Usage:
        payoff = ICMPayoff(stacks=[s0..s7], payouts=[p1..p8])
        scfg = SolverConfig(..., payoff=payoff)
    """

    def __init__(self, stacks, payouts, bb: int = BB, indices=(0, 1)):
        self.stacks = tuple(int(s) for s in stacks)
        self.payouts = tuple(payouts)
        self.bb = bb
        self.i0, self.i1 = indices
        if self.i0 >= len(self.stacks) or self.i1 >= len(self.stacks):
            raise ValueError("player indices out of range")
        self.total = sum(self.stacks)
        self.base_eq = icm_equities(self.stacks, self.payouts)

    def __call__(self, p: int, pot: int, hero_wins: bool, villain_wins: bool,
                 node, cfg) -> float:
        """Equity delta (bb) of the traverser p for one hand outcome."""
        inv0, inv1 = node.inv
        base = (pot - inv0 - inv1) // 2
        contrib = base + (inv0 if p == 0 else inv1)
        st = list(self.stacks)
        if hero_wins:
            st[p] += pot - contrib
            st[1 - p] -= contrib
        elif villain_wins:
            st[p] -= contrib
            st[1 - p] += pot - contrib
        else:  # split pot
            st[p] += pot // 2 - contrib
            st[1 - p] += pot // 2 - contrib
        eq = icm_equities(tuple(st), self.payouts)
        return (eq[p] - self.base_eq[p]) * self.total / self.bb

    def describe(self) -> str:
        bb = self.bb
        stacks = " ".join(f"{s / bb:g}bb" for s in self.stacks)
        pays = " ".join(f"{p * 100:.0f}%" for p in self.payouts[: len(self.stacks)])
        return f"ICM table [{stacks}] payouts [{pays}]"
