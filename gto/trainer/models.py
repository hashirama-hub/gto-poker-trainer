"""Model loading, caching and on-demand subgame solving.

Pre-solved models live in `solutions/` (gitignored, built by the solver):
  - pushfold_10bb/15bb/20bb.pkl  (chip-EV SB push/fold, 60k iters each)
  - full100_sb_bb_50k_checkpoint.pkl (full preflop+postflop tree, 100bb)

ICM push/fold and board-specific flop subgames depend on the exact stacks /
board, so they are solved on demand (a couple of minutes) and cached in
memory for the session.
"""
from __future__ import annotations

from pathlib import Path

from ..game import GameConfig
from ..icm import ICMPayoff
from ..solver import Solver, SolverConfig

# Default 8-max MTT payout structure (sums to 1.0)
MTT8_PAYOUTS = (0.40, 0.25, 0.15, 0.10, 0.05, 0.03, 0.015, 0.005)

SOLUTIONS_DIR = Path(__file__).resolve().parent.parent.parent / "solutions"
PUSH_FOLD_DEPTHS = (10, 15, 20)

_icm_cache: dict = {}
_flop_cache: dict = {}
_pushfold_cache: dict = {}


def _solver(cfg: GameConfig, scfg: SolverConfig) -> Solver:
    s = Solver(cfg, scfg)
    s.solve(verbose=False)
    return s


def pushfold_model(depth_bb: float) -> Solver:
    """Nearest pre-solved chip-EV push/fold model (10/15/20bb)."""
    d = min(PUSH_FOLD_DEPTHS, key=lambda x: abs(x - depth_bb))
    if d not in _pushfold_cache:
        path = SOLUTIONS_DIR / f"pushfold_{d}bb.pkl"
        if not path.exists():
            raise FileNotFoundError(
                f"pre-solved model {path} missing — run gto-trainer solve-pushfold first"
            )
        s = Solver(GameConfig(stack=d * 100, push_fold=True), SolverConfig(iterations=1))
        s.load(str(path))
        _pushfold_cache[d] = s
    return _pushfold_cache[d]


def full100_model(path: str | Path | None = None) -> Solver:
    """Full 100bb SB vs BB tree (preflop + postflop), board-averaged."""
    path = Path(path) if path else SOLUTIONS_DIR / "full100_sb_bb_50k_checkpoint.pkl"
    if not path.exists():
        raise FileNotFoundError(
            f"full-tree model {path} missing — solve it first (see AGENTS.md)"
        )
    s = Solver(GameConfig(), SolverConfig(iterations=1))
    s.load(str(path))
    return s


def icm_pushfold(stacks, payouts=None, iterations: int = 60_000) -> Solver:
    """On-demand ICM push/fold solve for a full table; cached per config.

    stacks: list of chips for [SB, BB, other players...]; effective stack
    (min of the two confronters) is what the betting tree plays.
    """
    if payouts is None:
        payouts = MTT8_PAYOUTS
    key = (tuple(stacks), tuple(payouts), iterations)
    if key not in _icm_cache:
        eff = min(stacks[0], stacks[1])
        scfg = SolverConfig(
            iterations=iterations,
            seed=1,
            report_every=10**9,
            payoff=ICMPayoff(stacks, payouts),
        )
        _icm_cache[key] = _solver(GameConfig(stack=eff, push_fold=True), scfg)
    return _icm_cache[key]


def flop_subgame(board, iterations: int = 20_000) -> Solver:
    """On-demand board-specific flop subgame.

    Spot: SB raises 2.5x, BB calls -> flop, pot 500, SB (player 0) to act.
    Cached per board for a session.
    """
    key = (tuple(board), iterations)
    if key not in _flop_cache:
        scfg = SolverConfig(
            iterations=iterations,
            seed=1,
            report_every=10**9,
            board=board,
            start_pot=500,
            start_inv=(0, 0),
        )
        _flop_cache[key] = _solver(GameConfig(), scfg)
    return _flop_cache[key]


def save_checkpoint(solver: Solver, path: str | Path):
    solver.save(str(path))
