"""MCCFR (Monte Carlo Counterfactual Regret Minimization) solver.

Chance-sampled external sampling with **traverser hand enumeration**:
each iteration samples
  - the opponent's hole cards (from their range, proportional to weight)
  - the full board runout
then traverses the game tree. At every traverser decision node, values are
computed as vectors over ALL of the traverser's hands (1326 combos), so each
iteration updates the regrets of every hand. Opponent actions are sampled.
"""
from __future__ import annotations

import random
import time

import numpy as np

from .cards import evaluate_7_batch
from .game import (
    BET,
    CALL,
    CHECK,
    FOLD,
    RAISE,
    TERMINAL_FOLD,
    TERMINAL_SHOWDOWN,
    GameConfig,
    build_tree,
)
from .ranges import COMBOS, NUM_COMBOS


class SolverConfig:
    def __init__(
        self,
        iterations: int = 100_000,
        seed: int = 1,
        report_every: int = 5_000,
        ranges: tuple = (None, None),
        board: tuple = (),
        start_pot: int = 0,
        start_inv: tuple = (0, 0),
        payoff=None,
    ):
        self.iterations = iterations
        self.seed = seed
        self.report_every = report_every
        self.ranges = ranges
        self.board = board
        self.start_pot = start_pot
        self.start_inv = start_inv
        self.payoff = payoff


class Solver:
    def __init__(self, cfg: GameConfig, scfg: SolverConfig):
        self.cfg = cfg
        self.scfg = scfg
        self.nodes, self.root_key = build_tree(
            cfg,
            start_street=len(scfg.board) and {3: 1, 4: 2, 5: 3}[len(scfg.board)] or 0,
            start_pot=scfg.start_pot,
            start_inv=scfg.start_inv,
        )
        self.board0 = tuple(scfg.board)
        self.rng = random.Random(scfg.seed)

        # per-player combo lists proportional to range weights
        self.hand_lists: list[list[int]] = []
        self.hand_weights: list[list[float]] = []
        self._cum: list[list[float]] = []
        self._valid: list[np.ndarray] = []
        for i in range(2):
            r = scfg.ranges[i]
            if r is None:
                w = np.ones(NUM_COMBOS)
            else:
                w = r.weights.copy()
                if len(scfg.board) >= 3:
                    dead = set(scfg.board)
                    for j in range(NUM_COMBOS):
                        if COMBOS[j][0] in dead or COMBOS[j][1] in dead:
                            w[j] = 0.0
            valid = w > 0
            self._valid.append(valid)
            self.hand_lists.append([j for j in range(NUM_COMBOS) if valid[j]])
            cw = [0.0]
            for x in w[w > 0]:
                cw.append(cw[-1] + x)
            self._cum.append(cw)

        for node in self.nodes.values():
            n_act = max(len(node.actions), 1)
            node.regrets = {
                0: np.zeros((NUM_COMBOS, n_act)),
                1: np.zeros((NUM_COMBOS, n_act)),
            }
            node.strat_sum = {
                0: np.zeros((NUM_COMBOS, n_act)),
                1: np.zeros((NUM_COMBOS, n_act)),
            }

        self._strength_cache: dict[tuple, np.ndarray] = {}
        self._strength_combos = np.array(COMBOS, dtype=np.int16)

    # ------------------------------------------------------------------ utils

    def _sample_opponent_hand(self, p: int, dead: set) -> int | None:
        """Sample one hand for player p, avoiding cards in `dead`."""
        import bisect

        lst, cw = self.hand_lists[p], self._cum[p]
        if not lst:
            return None
        for _ in range(300):
            x = self.rng.random() * cw[-1]
            j = bisect.bisect_right(cw, x) - 1
            pick = lst[min(j, len(lst) - 1)]
            c1, c2 = COMBOS[pick]
            if c1 not in dead and c2 not in dead:
                return pick
        return None

    def _sample_board(self, dead: set) -> tuple:
        """Sample the full runout for this traversal (once per iteration)."""
        avail = [c for c in range(52) if c not in dead]
        return self.board0 + tuple(self.rng.sample(avail, 5 - len(self.board0)))

    def strengths(self, board: tuple) -> np.ndarray:
        """7-card strength vector over all 1326 combos for a river board."""
        v = self._strength_cache.get(board)
        if v is None:
            v = evaluate_7_batch(self._strength_combos, np.array(board))
            if len(self._strength_cache) < 4000:
                self._strength_cache[board] = v
        return v

    def strategy(self, node, player: int) -> np.ndarray:
        """Current regret-matching strategy, vector over hands."""
        reg = node.regrets[player]
        pos = np.maximum(reg, 0)
        s = pos.sum(axis=1, keepdims=True)
        zero = s[:, 0] <= 0
        out = pos / np.where(s > 0, s, 1.0)
        if zero.any():
            out[zero] = 1.0 / len(node.actions)
        return out

    def avg_strategy(self, node, player: int) -> np.ndarray:
        """Average strategy, vector over hands."""
        ss = node.strat_sum[player]
        s = ss.sum(axis=1, keepdims=True)
        zero = s[:, 0] <= 0
        out = ss / np.where(s > 0, s, 1.0)
        if zero.any():
            out[zero] = 1.0 / len(node.actions)
        return out

    # ------------------------------------------------------------- traversal

    def _cfr(self, node, p: int, h_opp: int, board: tuple, opp_reach: float) -> np.ndarray:
        """Traverser-enumerated external sampling.

        Returns a value vector over all hands of the traverser p.
        """
        if node.terminal is not None:
            return self._terminal_vec(node, p, h_opp, board)

        player = node.to_act
        if player == p:
            strat = self.strategy(node, p)
            vals = np.empty((NUM_COMBOS, len(node.actions)))
            for a, child in enumerate(node.children):
                vals[:, a] = self._cfr(child, p, h_opp, board, opp_reach)
            v = (strat * vals).sum(axis=1)
            node.regrets[p] += opp_reach * (vals - v[:, None])
            node.strat_sum[p] += strat
            return v
        else:
            # opponent node: sample one action with the opponent hand's strategy
            strat = self.strategy(node, player)
            probs = strat[h_opp]
            a = self.rng.choices(range(len(node.actions)), weights=probs)[0]
            return self._cfr(
                node.children[a], p, h_opp, board, opp_reach * probs[a]
            )

    def _terminal_vec(self, node, p: int, h_opp: int, board: tuple) -> np.ndarray:
        if self.scfg.payoff is not None:
            return self._terminal_icm(node, p, h_opp, board)
        # net payoffs: winner gets pot back minus own total contribution;
        # contributions split equally for pre-street chips (heads-up, matched).
        pot = node.pot
        inv0, inv1 = node.inv
        base = (pot - inv0 - inv1) // 2  # each player's pre-street contribution
        contrib = base + (inv0 if p == 0 else inv1)
        if node.terminal == TERMINAL_FOLD:
            return np.full(NUM_COMBOS, pot - contrib if node.winner == p else -contrib)
        # showdown: `hero` below = the traverser p's hands.
        # The board is sampled excluding the opponent's hand, so a hero hand
        # sharing a board card is impossible -> value 0 (not a loss), and the
        # win/lose values are re-weighted by P(board avoids hero's cards).
        s_opp = self.strengths(board)[h_opp]
        s_hero = self.strengths(board)
        out = np.where(
            s_hero > s_opp,
            pot - contrib,
            np.where(s_hero == s_opp, pot // 2 - contrib, -contrib),
        )
        valid = s_hero > 0
        if valid.all():
            return out.astype(np.float64)
        out = out.astype(np.float64)
        out[~valid] = 0.0
        # P(board avoids 2 fixed cards | board avoids opp's hand) = C(d-2,t)/C(d,t)
        d = 52 - len(self.board0) - 2  # remaining unknown cards
        t = 5 - len(self.board0)
        p_avoid = (d - 2) / d
        for k in range(1, t):
            p_avoid *= (d - 2 - k) / (d - k)
        out[valid] /= p_avoid
        return out

    def _terminal_icm(self, node, p: int, h_opp: int, board: tuple) -> np.ndarray:
        """ICM payoffs: value over all hero hands (caller provides payoff fn)."""
        fn = self.scfg.payoff
        out = np.zeros(NUM_COMBOS)
        s_opp = self.strengths(board)[h_opp]
        s_hero = self.strengths(board)
        pot = node.pot
        if node.terminal == TERMINAL_FOLD:
            winner = node.winner
            return np.full(
                NUM_COMBOS, fn(p, pot, winner == 0, winner == 1, node, self.cfg)
            )
        for i in range(NUM_COMBOS):
            if s_hero[i] <= 0:
                continue  # hero hand shares a board card -> impossible
            if s_hero[i] > s_opp:
                out[i] = fn(p, pot, True, False, node, self.cfg)
            elif s_hero[i] == s_opp:
                out[i] = fn(p, pot, False, False, node, self.cfg)
            else:
                out[i] = fn(p, pot, False, True, node, self.cfg)
        # re-weight for boards avoiding hero's cards (same constant as showdown)
        d = 52 - len(self.board0) - 2
        t = 5 - len(self.board0)
        p_avoid = (d - 2) / d
        for k in range(1, t):
            p_avoid *= (d - 2 - k) / (d - k)
        valid = s_hero > 0
        out[valid] /= p_avoid
        return out

    # ------------------------------------------------------------------ solve

    def solve(self, verbose=True, save_every: int | None = None, save_path: str | None = None):
        t0 = time.time()
        iterations = self.scfg.iterations
        for it in range(1, iterations + 1):
            p = it % 2  # alternating traverser
            opp = 1 - p
            dead = set(self.board0)
            h_opp = self._sample_opponent_hand(opp, dead)
            if h_opp is None:
                continue
            c1, c2 = COMBOS[h_opp]
            dead.add(c1)
            dead.add(c2)
            board = self._sample_board(dead)
            self._cfr(self.nodes[self.root_key], p, h_opp, board, 1.0)
            if verbose and it % self.scfg.report_every == 0:
                self._report(it, t0)
            if save_every and save_path and it % save_every == 0:
                self.save(save_path)
        if verbose:
            self._report(iterations, t0)
        return self

    def _report(self, it: int, t0: float):
        el = time.time() - t0
        print(
            f"iter {it:>7} | {it / el:,.0f} it/s | {el:.0f}s"
        )

    # ---------------------------------------------------------------- queries

    def strategy_for_hand(self, key: tuple, player: int, hand_name: str) -> dict[str, float]:
        """Probabilities per action for a named hand (e.g. 'AKs', 'AA')."""
        from .ranges import COMBO_INDEX, _base_combo, _combo_cards

        node = self.nodes[key]
        spec = _base_combo(hand_name.upper())
        combos = _combo_cards(*spec)
        labels = [str(a) for a in node.actions]
        out: dict[str, float] = {}
        n = 0
        for combo in combos:
            i = COMBO_INDEX.get(combo)
            if i is None:
                continue
            probs = self.avg_strategy(node, player)[i]
            for label, pr in zip(labels, probs):
                out[label] = out.get(label, 0.0) + pr
            n += 1
        return {k: v / n for k, v in out.items()} if n else out

    # ----------------------------------------------------------- validation

    def _br_vec(self, node, p: int, h_opp: int, board: tuple) -> np.ndarray:
        """Best-response value vector over p's hands vs avg strategies.

        Returns the per-action value vectors at p's decision nodes so the
        caller can average over samples first and then take the max (taking
        the max before averaging would bias the estimate upward).
        """
        if node.terminal is not None:
            v = self._terminal_vec(node, p, h_opp, board)
            return np.tile(v, (max(len(node.actions), 1), 1))
        player = node.to_act
        if player == p:
            vals = np.empty((len(node.actions), NUM_COMBOS))
            for a, child in enumerate(node.children):
                vals[a] = self._br_vec(child, p, h_opp, board).max(axis=0)
            return vals
        strat = self.avg_strategy(node, player)[h_opp]
        out = None
        for a, child in enumerate(node.children):
            v = self._br_vec(child, p, h_opp, board) * strat[a]
            out = v if out is None else out + v
        return out

    def exploitability(self, trials: int = 25, boards_per_trial: int = 25) -> tuple[float, float]:
        """(br0, br1): mean best-response EVs over sampled opponent hands.

        For a zero-sum game, (br0 + br1) -> 0 at equilibrium. Values are
        averaged over `boards_per_trial` runouts per opponent hand to cut
        the variance of single-board showdown samples.
        """
        br = [0.0, 0.0]
        n = [0, 0]
        for _ in range(trials):
            for p in (0, 1):
                opp = 1 - p
                dead = set(self.board0)
                h_opp = self._sample_opponent_hand(opp, dead)
                if h_opp is None:
                    continue
                c1, c2 = COMBOS[h_opp]
                dead.add(c1)
                dead.add(c2)
                acc = None
                for _ in range(boards_per_trial):
                    board = self._sample_board(dead)
                    vals = self._br_vec(self.nodes[self.root_key], p, h_opp, board)
                    acc = vals if acc is None else acc + vals
                valid = self._valid[p]
                br[p] += (acc / boards_per_trial).max(axis=0)[valid].mean()
                n[p] += 1
        return (br[0] / n[0] if n[0] else 0.0), (br[1] / n[1] if n[1] else 0.0)

    # ------------------------------------------------------------------ I/O

    def save(self, path: str):
        import pickle

        data = {}
        for key, node in self.nodes.items():
            data[key] = (
                node.regrets[0],
                node.regrets[1],
                node.strat_sum[0],
                node.strat_sum[1],
            )
        with open(path, "wb") as f:
            pickle.dump(data, f)

    def load(self, path: str):
        import pickle

        with open(path, "rb") as f:
            data = pickle.load(f)
        for key, (r0, r1, s0, s1) in data.items():
            node = self.nodes[key]
            node.regrets[0][:] = r0
            node.regrets[1][:] = r1
            node.strat_sum[0][:] = s0
            node.strat_sum[1][:] = s1
        return self