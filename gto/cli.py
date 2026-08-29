"""gto-trainer CLI: interactive 8-max MTT GTO training quizzes.

Subcommands:
  pushfold       chip-EV SB push/fold quiz (pre-solved models, instant)
  icm            ICM push/fold quiz on a full 8-max table (solved on demand)
  preflop        100bb SB vs BB preflop decisions (full-tree model)
  flop           board-specific flop decisions (subgame solved on demand)
  info           print the GTO strategy + EV of a hand from a saved model
  solve-pushfold solve chip-EV push/fold models (10/15/20bb)
  solve-full100  solve/resume full 100bb SB vs BB tree
"""
from __future__ import annotations

import argparse
import random
import sys
import time
from pathlib import Path

from .game import BB, GameConfig
from .solver import Solver, SolverConfig
from .trainer.engine import (
    Question,
    fmt_board,
    make_flop_question,
    make_icm_pushfold_question,
    make_preflop_question,
    make_pushfold_question,
    score_choice,
)
from .trainer.models import PUSH_FOLD_DEPTHS, SOLUTIONS_DIR, full100_model, pushfold_model

ANSI = {"bold": "\033[1m", "dim": "\033[2m", "green": "\033[92m", "red": "\033[91m", "end": "\033[0m"}


def _style(text: str, code: str) -> str:
    return f"{ANSI[code]}{text}{ANSI['end']}" if sys.stdout.isatty() else text


def _print_question(q: Question, index: int, total: int) -> None:
    print("\n" + "─" * 60)
    print(f"Q{index}/{total} — {q.prompt}")
    print("-" * 60)
    for i, label in enumerate(q.actions, 1):
        gto_pct = q.gto.get(label, 0.0) * 100
        ev = q.ev.get(label, 0.0)
        print(f"  [{i}] {label:<18} GTO {gto_pct:5.1f}%    EV {ev:+.2f}bb")
    print("-" * 60)


def _read_choice(q: Question) -> str | None:
    while True:
        try:
            raw = input(_style(f"  your play (1-{len(q.actions)}, q = quit): ", "bold"))
        except (EOFError, KeyboardInterrupt):
            return None
        raw = raw.strip().lower()
        if raw in ("q", "quit", "exit"):
            return None
        if raw.isdigit() and 1 <= int(raw) <= len(q.actions):
            return q.actions[int(raw) - 1]
        print("  invalid choice")


def _print_result(q: Question, choice: str | None) -> float | None:
    if choice is None:
        return None
    score = score_choice(choice, q.ev)
    best, worst = q.best, min(q.ev, key=q.ev.get)
    verdict = "GTO" if choice == best else ("terrible" if choice == worst else "ok")
    color = "green" if score >= 90 else "red"
    print(f"  {_style('GTO: ' + best, 'bold')} ({q.gto.get(best, 0) * 100:.0f}%)  "
          f"{_style(f'verdict: {verdict}', color)}  "
          f"score {_style(f'{score:.0f}/100', 'bold')}")
    return score


def _summary(scores: list[float], elapsed: float) -> None:
    if not scores:
        print("\nno questions answered")
        return
    avg = sum(scores) / len(scores)
    bar = "█" * int(avg / 5)
    print("\n" + "═" * 60)
    print(f"  {len(scores)} hands | average score {avg:.0f}/100  {bar}")
    print(f"  time {elapsed:.0f}s | 100 = always plays exactly GTO EV")
    print("═" * 60)


def _run(make_question, hands: int, title: str, quiet_load: bool = False):
    rng = random.Random()
    scores: list[float] = []
    t0 = time.time()
    if not quiet_load:
        print(title)
    for i in range(1, hands + 1):
        t_q = time.time()
        q = make_question(rng)
        if not quiet_load:
            print(f"(question generated in {time.time() - t_q:.0f}s)")
        _print_question(q, i, hands)
        choice = _read_choice(q)
        score = _print_result(q, choice)
        if score is None:
            break
        scores.append(score)
    _summary(scores, time.time() - t0)
    return scores


def _cmd_pushfold(args) -> None:
    if args.bb and (args.bb < 8 or args.bb > 25):
        sys.exit("--bb must be within 8-25")
    player = 0 if args.position == "sb" else 1
    fixed = float(args.bb) if args.bb else 0.0
    _run(lambda rng: make_pushfold_question(rng, fixed, player), args.hands,
         f"=== Chip-EV push/fold quiz ({'SB' if player == 0 else 'BB'} vs "
         f"{'BB' if player == 0 else 'SB'} shove) ===")


def _cmd_icm(args) -> None:
    stacks = None
    if args.table:
        vals = [float(x) for x in args.table.split(",")]
        if len(vals) < 2:
            sys.exit("--table needs at least 2 stacks in bb, e.g. 12,15,8,20,10,25,9,14")
        stacks = [int(v * BB) for v in vals[:8]]
    payouts = tuple(float(x) for x in args.payouts.split(",")) if args.payouts else None
    if payouts and abs(sum(payouts) - 1.0) > 1e-6:
        sys.exit("--payouts must sum to 1.0 (e.g. 0.4,0.25,0.15,0.1,0.05,0.03,0.015,0.005)")

    def make(rng):
        q, used_stacks = make_icm_pushfold_question(
            rng, stacks, payouts, iterations=args.iterations,
            player=0 if args.position == "sb" else 1,
        )
        return q

    print(f"=== ICM push/fold quiz (8-max, solving {args.iterations} iterations — "
          f"~1-2 min) ===")
    _run(make, args.hands, "=== ICM push/fold quiz ===", quiet_load=True)


def _cmd_preflop(args) -> None:
    solver = full100_model(args.model) if args.model else full100_model()
    player = 0 if args.position == "sb" else 1
    _run(lambda rng: make_preflop_question(rng, solver, player), args.hands,
         "=== 100bb preflop quiz (SB vs BB) ===")


def _cmd_flop(args) -> None:
    iterations = 6_000 if args.fast else 20_000
    board = tuple(int(x) for x in args.board.split(",")) if args.board else None
    if board is not None and len(board) != 3:
        sys.exit("--board needs 3 cards 0-51, e.g. 0,15,33")
    print(f"=== Flop quiz (SRP 2.5x, solving board subgame {iterations} iters — "
          f"{'~1-2 min' if args.fast else '~4-6 min'}) ===")

    def make(rng):
        q, used_board = make_flop_question(rng, board, iterations)
        return q

    _run(make, args.hands, "=== Flop quiz ===", quiet_load=True)


def _cmd_info(args) -> None:
    depth = args.depth
    if depth:
        s = pushfold_model(depth)
        eff = s.cfg.stack // BB
        samples = 400
    else:
        s = full100_model(args.model)
        eff = 100
        samples = 30
    key = s.root_key
    for hand in args.hands.split():
        strat = s.strategy_for_hand(key, 0, hand.upper())
        ev = s.ev_actions(key, 0, hand.upper(), samples=samples)
        print(f"{hand.upper()} @ {eff}bb, SB:")
        for label in ev:
            print(f"  {label:<16} GTO {strat.get(label, 0) * 100:5.1f}%   EV {ev[label]:+.2f}bb")


def _cmd_solve_pushfold(args) -> None:
    for depth in args.depths:
        print(f"=== Solving push/fold {depth}bb ({args.iterations} iterations) ===")
        cfg = GameConfig(stack=depth * BB, push_fold=True)
        scfg = SolverConfig(
            iterations=args.iterations,
            seed=args.seed,
            report_every=args.report_every,
        )
        s = Solver(cfg, scfg)
        s.solve(verbose=True, save_every=args.save_every, save_path=str(SOLUTIONS_DIR / f"pushfold_{depth}bb.pkl"))
        s.save(str(SOLUTIONS_DIR / f"pushfold_{depth}bb.pkl"))
        print(f"Saved to solutions/pushfold_{depth}bb.pkl")


def _cmd_solve_full100(args) -> None:
    path = Path(args.model) if args.model else SOLUTIONS_DIR / "full100_sb_bb_50k_checkpoint.pkl"
    if not path.exists():
        print(f"Checkpoint {path} not found. Creating fresh model...")
        cfg = GameConfig()
        scfg = SolverConfig(iterations=1, seed=args.seed, report_every=args.report_every)
        s = Solver(cfg, scfg)
    else:
        print(f"Resuming from {path}...")
        cfg = GameConfig()
        scfg = SolverConfig(iterations=args.iterations, seed=args.seed, report_every=args.report_every)
        s = Solver(cfg, scfg)
        s.load(str(path))
    s.solve(verbose=True, save_every=args.save_every, save_path=str(path))
    s.save(str(path))
    print(f"Saved to {path}")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(
        prog="gto-trainer",
        description="GTO poker trainer for 8-max MTT (heads-up solver + quizzes)",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("pushfold", help="chip-EV SB push/fold quiz (instant)")
    p.add_argument("--hands", type=int, default=10)
    p.add_argument("--bb", type=float, default=0, help="fixed depth 8-25 (default random)")
    p.add_argument("--position", choices=["sb", "bb"], default="sb")
    p.set_defaults(fn=_cmd_pushfold)

    p = sub.add_parser("icm", help="ICM push/fold quiz, 8-max table (solved on demand)")
    p.add_argument("--hands", type=int, default=8)
    p.add_argument("--iterations", type=int, default=60_000)
    p.add_argument("--position", choices=["sb", "bb"], default="sb")
    p.add_argument("--table", help="stacks in bb, e.g. '12,15,8,20,10,25,9,14'")
    p.add_argument("--payouts", help="prizes summing to 1.0, e.g. '0.4,0.25,0.15,0.1,0.05,0.03,0.015,0.005'")
    p.set_defaults(fn=_cmd_icm)

    p = sub.add_parser("preflop", help="100bb SB vs BB preflop quiz (full tree)")
    p.add_argument("--hands", type=int, default=10)
    p.add_argument("--position", choices=["sb", "bb"], default="sb")
    p.add_argument("--model", help="path to full-tree checkpoint")
    p.set_defaults(fn=_cmd_preflop)

    p = sub.add_parser("flop", help="board-specific flop quiz (subgame solved on demand)")
    p.add_argument("--hands", type=int, default=5)
    p.add_argument("--fast", action="store_true", help="fewer iterations (~1-2 min)")
    p.add_argument("--board", help="3 card ids 0-51, e.g. '0,15,33'")
    p.set_defaults(fn=_cmd_flop)

    p = sub.add_parser("info", help="GTO strategy + EV of a hand in a model")
    p.add_argument("hands", help="space-separated hands, e.g. 'AA A5s 72o'")
    p.add_argument("--depth", type=float, help="push/fold depth 8-25 (uses pre-solved)")
    p.add_argument("--model", help="path to full-tree checkpoint")
    p.set_defaults(fn=_cmd_info)

    p = sub.add_parser("solve-pushfold", help="solve chip-EV push/fold models (10/15/20bb)")
    p.add_argument("--depths", nargs="+", type=int, default=[10, 15, 20], help="depths in bb to solve")
    p.add_argument("--iterations", type=int, default=60_000)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--report-every", type=int, default=5_000)
    p.add_argument("--save-every", type=int, default=10_000)
    p.set_defaults(fn=_cmd_solve_pushfold)

    p = sub.add_parser("solve-full100", help="solve/resume full 100bb SB vs BB tree")
    p.add_argument("--model", help="checkpoint path (default: solutions/full100_sb_bb_50k_checkpoint.pkl)")
    p.add_argument("--iterations", type=int, default=25_000, help="iterations this run")
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--report-every", type=int, default=10_000)
    p.add_argument("--save-every", type=int, default=10_000)
    p.set_defaults(fn=_cmd_solve_full100)

    args = ap.parse_args(argv)
    try:
        args.fn(args)
    except KeyboardInterrupt:
        print("\nbye")
    except FileNotFoundError as e:
        sys.exit(f"error: {e}")


if __name__ == "__main__":
    main()
