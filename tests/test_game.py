from collections import Counter

from gto.game import (
    BB,
    SB,
    BET,
    CALL,
    CHECK,
    FOLD,
    RAISE,
    TERMINAL_FOLD,
    TERMINAL_SHOWDOWN,
    Action,
    GameConfig,
    build_tree,
)


def build(cfg=None, **kw):
    cfg = cfg or GameConfig(**kw)
    return build_tree(cfg)


def test_root_blinds():
    nodes, root = build()
    r = nodes[root]
    assert r.street == 0
    assert r.to_act == 0
    assert r.pot == SB + BB
    assert r.inv == (SB, BB)


def test_sb_actions():
    nodes, root = build()
    r = nodes[root]
    types = [a.type for a in r.actions]
    assert types == [FOLD, CALL, RAISE, RAISE, RAISE]
    assert r.actions[0].type == FOLD
    assert r.actions[2].amount == 250  # 2.5x open
    assert r.actions[3].amount == 300  # 3x open
    assert r.actions[4].amount == 10000  # all-in shove


def test_bb_vs_open():
    nodes, root = build()
    bb = nodes[(0, 350, 250, 100, 1)]
    assert [a.type for a in bb.actions] == [FOLD, CALL, RAISE, RAISE, RAISE]
    assert bb.actions[2].amount == 625  # 0.5 pot raise
    assert bb.actions[3].amount == 750  # 1.0 pot raise
    assert bb.actions[4].amount == 10000  # shove


def test_flop_starts_after_call():
    nodes, root = build()
    flop = nodes[(1, 500, 0, 0, 0)]
    assert flop.pot == 500
    assert [a.type for a in flop.actions] == [CHECK, BET, BET, BET]
    assert flop.actions[1].amount == 165  # 0.33 * 500
    assert flop.actions[2].amount == 500  # pot bet
    assert flop.actions[3].amount == 9500  # all-in bet


def test_no_duplicate_keys_or_actions():
    nodes, root = build()
    keys = [n.key for n in nodes.values() if n.terminal is None]
    assert len(keys) == len(set(keys))
    for node in nodes.values():
        acts = [(a.type, a.amount) for a in node.actions]
        assert len(acts) == len(set(acts))


def test_all_nonterminal_have_actions():
    nodes, root = build()
    for node in nodes.values():
        if node.terminal is None:
            assert node.actions, f"node {node.key} has no actions"


def test_terminal_types():
    nodes, root = build()
    terms = Counter(n.terminal for n in nodes.values())
    assert terms.get(TERMINAL_SHOWDOWN, 0) > 0
    # fold terminals are inline children (key=())
    folds = 0
    for n in nodes.values():
        for child in n.children:
            if child.terminal == TERMINAL_FOLD:
                folds += 1
    assert folds > 0


def test_stack_conservation():
    cfg = GameConfig()
    nodes, root = build(cfg)
    for node in nodes.values():
        for i, child in enumerate(node.children):
            if child.terminal is None:
                a = node.actions[i]
                if a.type == FOLD:
                    continue
                # pot delta matches the chips added by the action
                if a.type == CALL:
                    delta = node.inv[1 - node.to_act] - node.inv[node.to_act]
                elif a.type == BET:
                    delta = a.amount
                else:  # RAISE
                    delta = a.amount - node.inv[node.to_act]
                assert child.pot - node.pot == delta
                # nobody invests more than stack
                for p in (0, 1):
                    invested = child.pot - child.inv[1 - p]
                    assert invested <= cfg.stack


def test_allin_fold_or_showdown():
    nodes, root = build()
    for node in nodes.values():
        if node.terminal is None:
            for child in node.children:
                assert child.terminal in (None, TERMINAL_FOLD, TERMINAL_SHOWDOWN)


def test_short_stack_pushfold():
    nodes, root = build(GameConfig(stack=1500))
    # SB shove = 1500 -> pot 1600, BB faces call 1400
    sb = nodes[root]
    assert [a.type for a in sb.actions] == [FOLD, CALL, RAISE, RAISE, RAISE]
    assert sb.actions[4].amount == 1500  # direct shove
    bb = nodes[(0, 1600, 1500, 100, 1)]
    assert [a.type for a in bb.actions] == [FOLD, CALL]


def test_raise_to_formula():
    cfg = GameConfig()
    # pot 350, call 150, last bet 250, frac 1.0
    assert cfg.raise_to(350, 150, 250, 1.0) == 750
    assert cfg.raise_to(350, 150, 250, 0.5) == 625
    assert cfg.bet_amount(500, 0.33) == 165