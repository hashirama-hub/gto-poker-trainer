import numpy as np
import pytest

from gto.game import GameConfig
from gto.ranges import COMBO_INDEX, COMBOS
from gto.solver import Solver, SolverConfig


def make_solver(iterations: int, stack: int = 1500, push_fold: bool = True, seed: int = 1):
    cfg = GameConfig(stack=stack, push_fold=push_fold)
    scfg = SolverConfig(iterations=iterations, seed=seed, report_every=10**9)
    s = Solver(cfg, scfg)
    s.solve(verbose=False)
    return s


def avg_strategy_of(s, key, player, name):
    i = COMBO_INDEX[tuple(sorted((0, 28))) if name == "72o" else (48, 49)]
    return s.avg_strategy(s.nodes[key], player)[i]


def test_net_fold_payoff_sb():
    """SB fold loses only the small blind (net payoff, not gross pot)."""
    s = make_solver(100)
    root = s.nodes[s.root_key]
    fold = root.children[0]
    v = s._terminal_vec(fold, 0, 0, ())
    assert np.allclose(v, -50)


def test_net_fold_payoff_bb():
    """BB fold loses only the big blind."""
    s = make_solver(100)
    root = s.nodes[s.root_key]
    bb_node = root.children[1]
    fold = bb_node.children[0]
    v = s._terminal_vec(fold, 1, 0, ())
    assert np.allclose(v, -100)


def test_showdown_payoff_net_and_blockers():
    """Showdown values are net; hero hands sharing a board card are impossible."""
    s = make_solver(100)
    root = s.nodes[s.root_key]
    bb_node = root.children[1]
    showdown = bb_node.children[1]  # pot 3000, inv (1500, 1500)
    h_opp = COMBO_INDEX[(0, 28)]  # 7s2c, so the board below kills 2c/7s rows
    board = (50, 5, 17, 8, 33)  # Ah 3d 6d 4c 8d
    v = s._terminal_vec(showdown, 1, h_opp, board)
    assert v.shape == (1326,)
    # As5s beats 72o on this board: +1500 net, rescaled by 1/P(board avoids hero)
    i = COMBO_INDEX[(23, 48)]
    assert v[i] == pytest.approx(1500 / 0.8081632653061225)
    # a hand sharing the board (e.g. AhAs -> Ah on board) is impossible: 0
    i_dead = COMBO_INDEX[(50, 51)]
    assert v[i_dead] == 0
    # the rest of the vector is non-zero somewhere (scaled, not all blocked)
    assert (v != 0).sum() > 100


def test_push_fold_converges_low_exploitability():
    """15bb push/fold: SB shoves premiums, folds junk, exploitability small."""
    s = make_solver(30000)
    root = s.nodes[s.root_key]
    bb_node = root.children[1]
    avg0 = s.avg_strategy(root, 0)
    avg1 = s.avg_strategy(bb_node, 1)
    # AA shoves, 72o folds
    i_aa = COMBO_INDEX[(48, 49)]
    i_72 = COMBO_INDEX[(0, 28)]
    assert avg0[i_aa][1] > 0.99
    assert avg0[i_72][1] < 0.2
    # BB calls AA, folds 72o
    assert avg1[i_aa][1] > 0.99
    assert avg1[i_72][1] < 0.2
    br0, br1 = s.exploitability(trials=30, boards_per_trial=20)
    assert br0 + br1 < 300  # < 3bb over a 30bb pot game


def test_exploitability_known_good_profile_is_low():
    """A perfect shove/fold profile has ~0 exploitability.

    SB always shoves, BB calls only when ahead of range: here just check the
    estimator returns a small sum for the solved profile at higher iters.
    """
    s = make_solver(60000)
    br0, br1 = s.exploitability(trials=30, boards_per_trial=20)
    assert br0 + br1 < 300


def test_save_load_roundtrip_regrets():
    s = make_solver(3000)
    root = s.nodes[s.root_key]
    reg0_before = root.regrets[0].copy()
    s.save("/tmp/opencode/test_solver.pkl")
    s2 = Solver(s.cfg, s.scfg)
    s2.load("/tmp/opencode/test_solver.pkl")
    assert np.allclose(s2.nodes[s2.root_key].regrets[0], reg0_before)
    np.testing.assert_allclose(
        s2.avg_strategy(s2.nodes[s2.root_key], 0),
        s.avg_strategy(root, 0),
    )


def test_full_tree_builds_and_solves():
    cfg = GameConfig()
    scfg = SolverConfig(iterations=2000, seed=1, report_every=10**9)
    s = Solver(cfg, scfg)
    s.solve(verbose=False)
    root = s.nodes[s.root_key]
    avg0 = s.avg_strategy(root, 0)
    i_aa = COMBO_INDEX[(48, 49)]
    i_72 = COMBO_INDEX[(0, 28)]
    assert avg0[i_aa][1:].sum() > 0.9  # AA raises preflop
    assert avg0[i_72][0] > 0.5  # 72o folds


def test_br_vec_shapes_full_tree():
    """_br_vec returns per-action matrices at p's root and collapses at
    opponent roots (no broadcasting errors on deep trees)."""
    s = Solver(GameConfig(), SolverConfig(iterations=1))
    dead = set()
    h_opp = s._sample_opponent_hand(1, dead)
    c1, c2 = COMBOS[h_opp]
    dead.update([c1, c2])
    board = s._sample_board(dead)
    v0 = s._br_vec(s.nodes[s.root_key], 0, h_opp, board)
    assert v0.shape == (len(s.nodes[s.root_key].actions), 1326)
    v1 = s._br_vec(s.nodes[s.root_key], 1, h_opp, board)
    assert v1.shape == (1326,)