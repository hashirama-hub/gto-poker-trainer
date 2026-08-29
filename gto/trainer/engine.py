"""Question generation and scoring for the 8-max MTT trainer.

Scoring is EV-based: score = (EV(chosen) - EV(worst)) / (EV(best) - EV(worst)).
This gives partial credit for close-but-not-perfect decisions and zero for
the worst action, which is the natural scale for GTO training.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

from ..game import BB
from ..solver import Solver
from .models import flop_subgame, full100_model, icm_pushfold, pushfold_model

RANKS = "23456789TJQKA"
_HAND_NAMES: list[str] | None = None

# 8-max final-table structure (fractions of the pool, sum to 1)
MTT8_PAYOUTS = (0.40, 0.25, 0.15, 0.10, 0.05, 0.03, 0.015, 0.005)

FLOP_SPOT_POT = 500  # SB raise 2.5x + BB call


@dataclass
class Question:
    prompt: str
    player: int
    hand: str
    actions: list[str]
    gto: dict[str, float]    # action label -> GTO probability
    ev: dict[str, float]     # action label -> EV in bb (avg strategies)
    best: str                # GTO best action label


def _hand_names() -> list[str]:
    global _HAND_NAMES
    if _HAND_NAMES is None:
        names = []
        for hi in range(12, -1, -1):
            for lo in range(hi, -1, -1):
                if hi == lo:
                    names.append(RANKS[hi] * 2)
                else:
                    names.append(RANKS[hi] + RANKS[lo] + "S")
                    names.append(RANKS[hi] + RANKS[lo] + "O")
        _HAND_NAMES = names
    return _HAND_NAMES


def random_hand_name(rng: random.Random) -> str:
    return rng.choice(_hand_names())


def score_choice(choice: str, ev: dict[str, float]) -> float:
    best, worst = max(ev.values()), min(ev.values())
    if best == worst:
        return 100.0
    return max(0.0, min(100.0, (ev[choice] - worst) / (best - worst) * 100.0))


def _question(solver: Solver, key: tuple, player: int, hand: str, prompt: str) -> Question:
    node = solver.nodes[key]
    ev = solver.ev_actions(key, player, hand, samples=250)
    strat = solver.strategy_for_hand(key, player, hand)
    gto = {a: max(0.0, min(1.0, strat.get(a, 0.0))) for a in ev}
    best = max(ev, key=ev.get)
    return Question(
        prompt=prompt,
        player=player,
        hand=hand,
        actions=list(ev),
        gto=gto,
        ev=ev,
        best=best,
    )


# ---------------------------------------------------------------- push/fold

def make_pushfold_question(rng: random.Random, depth_bb: float = 0, player: int = 0) -> Question:
    """Chip-EV SB push/fold (player 0 = SB decision, player 1 = BB vs shove)."""
    if not depth_bb:
        depth_bb = float(rng.randint(8, 25))
    solver = pushfold_model(depth_bb)
    eff = solver.cfg.stack // BB  # the model's own depth (nearest 10/15/20)
    hand = random_hand_name(rng)
    if player == 0:
        key = solver.root_key
        prompt = f"SB @ {eff}bb, hand {hand} — shove or fold?"
    else:
        key = solver.nodes[solver.root_key].children[1].key
        prompt = f"BB @ {eff}bb, SB shoved, you have {hand} — call or fold?"
    return _question(solver, key, player, hand, prompt)


# --------------------------------------------------------------------- ICM

def make_icm_pushfold_question(
    rng: random.Random,
    stacks: list[int] | None = None,
    payouts=MTT8_PAYOUTS,
    iterations: int = 60_000,
    player: int = 0,
) -> tuple[Question, list[int]]:
    """ICM push/fold on a full 8-max table (hero = SB, player 0).

    Returns (question, stacks) so the session can reuse the same table for
    several hands (the solve is cached and takes ~1-2 minutes).
    """
    if stacks is None:
        eff = rng.randint(8, 25) * BB
        stacks = [eff]
        stacks.append(max(eff, rng.randint(eff // BB, 40) * BB))
        for _ in range(6):
            stacks.append(rng.randint(5, 50) * BB)
        rng.shuffle(stacks[2:])
    solver = icm_pushfold(stacks, payouts, iterations)
    hand = random_hand_name(rng)
    eff = solver.cfg.stack // BB
    if player == 0:
        key = solver.root_key
        prompt = f"ICM final table, SB @ {eff}bb (effective), hand {hand} — shove or fold?"
    else:
        key = solver.nodes[solver.root_key].children[1].key
        prompt = f"ICM final table, BB @ {eff}bb (effective), SB shoved, {hand} — call or fold?"
    return _question(solver, key, player, hand, prompt), list(stacks)


# ---------------------------------------------------------------- preflop

PREFLOP_BB_NODE = (0, 250, 50, 250, 1)  # BB facing a 2.5x open


def make_preflop_question(
    rng: random.Random, solver: Solver | None = None, player: int = 0
) -> Question:
    """100bb SB vs BB preflop decisions (SB open / BB vs 2.5x)."""
    solver = solver or full100_model()
    hand = random_hand_name(rng)
    if player == 0:
        key = solver.root_key
        prompt = f"SB @ 100bb, hand {hand} — open or fold?"
    else:
        key = PREFLOP_BB_NODE
        prompt = f"BB @ 100bb, SB opens 2.5x, you have {hand} — respond?"
    return _question(solver, key, player, hand, prompt)


# ------------------------------------------------------------------- flop

def make_flop_question(
    rng: random.Random,
    board: tuple | None = None,
    iterations: int = 20_000,
    player: int = 0,
) -> tuple[Question, tuple]:
    """Board-specific flop spot: SB opens 2.5x, BB calls.

    The subgame is solved on demand (a few minutes) and cached per board.
    Hero's hand is drawn so it never collides with the board.
    """
    if board is None:
        board = tuple(sorted(rng.sample(range(52), 3)))
    solver = flop_subgame(board, iterations)
    hand = random_hand_name(rng)
    from ..ranges import COMBO_INDEX, _base_combo, _combo_cards

    dead = set(board)
    for _ in range(100):
        if not (set(_combo_cards(*_base_combo(hand))[0]) & dead):
            break
        hand = random_hand_name(rng)
    key = (1, FLOP_SPOT_POT, 0, 0, 0)
    prompt = (
        f"SB raise 2.5x, BB calls. Flop {fmt_board(board)}, pot {FLOP_SPOT_POT // BB}bb, "
        f"you (SB) have {hand} — play?"
    )
    return _question(solver, key, player, hand, prompt), board


def fmt_board(board: tuple) -> str:
    s = "c d h s"
    return " ".join(
        "23456789TJQKA"[c // 4] + s[c % 4] for c in board
    )
