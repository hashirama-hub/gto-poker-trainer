"""Heads-up NLHE betting tree builder.

The tree is a fixed-size (abstraction) game tree used by the CFR solver:
each decision node offers a discrete action set derived from bet sizes
configured per street. All amounts are integer chips; one big blind = 100.
"""
from __future__ import annotations

from dataclasses import dataclass, field

BB = 100
SB = BB // 2


@dataclass(frozen=True)
class GameConfig:
    stack: int = 100 * BB          # effective stack per player (chips)
    sb: int = SB
    bb: int = BB
    # postflop bet sizes: street (1=flop,2=turn,3=river) -> list of pot fractions
    bet_sizes: dict[int, tuple[float, ...]] = field(
        default_factory=lambda: {1: (0.33, 1.0), 2: (0.5, 1.0), 3: (0.5,)}
    )
    # raise sizes: street (0=preflop..3) -> fractions (see raise_to formula)
    raise_sizes: dict[int, tuple[float, ...]] = field(
        default_factory=lambda: {0: (0.5, 1.0), 1: (1.0,), 2: (1.0,), 3: (1.0,)}
    )
    # restricted tree: preflop only shove/fold (BB: call/fold) - MTT push/fold
    push_fold: bool = False

    def raise_to(self, pot: int, to_call: int, last_bet: int, frac: float) -> int:
        """Raise-to amount: pot after call + frac * last bet."""
        return pot + to_call + int(frac * last_bet)

    def bet_amount(self, pot: int, frac: float) -> int:
        return int(frac * pot)


# Action types
FOLD, CHECK, CALL, BET, RAISE = "f", "k", "c", "b", "r"
TERMINAL_FOLD, TERMINAL_SHOWDOWN = "fold", "showdown"

ACTION_LABELS = {
    FOLD: "fold",
    CHECK: "check",
    CALL: "call",
    BET: "bet",
    RAISE: "raise",
}


@dataclass(frozen=True)
class Action:
    type: str
    # for BET: chips to put in; for RAISE: total street investment target
    amount: int = 0

    def __str__(self) -> str:
        if self.type == BET:
            return f"bet {self.amount}"
        if self.type == RAISE:
            return f"raise to {self.amount}"
        return ACTION_LABELS[self.type]


@dataclass
class Node:
    key: tuple
    street: int          # 0=preflop .. 3=river
    to_act: int          # player to act (0 = SB/button, 1 = BB)
    pot: int             # chips in the middle
    inv: tuple[int, int] # chips invested this street by each player
    actions: list[Action] = field(default_factory=list)
    children: list[object] = field(default_factory=list)
    terminal: str | None = None
    winner: int | None = None   # for fold terminals
    # solver state: per-player arrays indexed by action
    regrets: dict[int, object] = field(default_factory=dict)
    strat_sum: dict[int, object] = field(default_factory=dict)


def state_key(street: int, pot: int, inv: tuple[int, int], to_act: int) -> tuple:
    return (street, pot, inv[0], inv[1], to_act)


def build_tree(
    cfg: GameConfig,
    start_street: int = 0,
    start_pot: int = 0,
    start_inv: tuple[int, int] = (0, 0),
) -> tuple[dict[tuple, Node], tuple]:
    """Build the abstracted heads-up betting tree. Returns (nodes, root_key)."""
    nodes: dict[tuple, Node] = {}

    def stacks(pot: int, inv: tuple[int, int]) -> tuple[int, int]:
        # chips remaining for players 0,1: total invested = pot - other's inv
        return (cfg.stack - pot + inv[1], cfg.stack - pot + inv[0])

    def expand(node: Node) -> None:
        p = node.to_act
        opp = 1 - p
        to_call = node.inv[opp] - node.inv[p]
        s = stacks(node.pot, node.inv)
        stack_p, stack_o = s[p], s[opp]
        if stack_p <= 0:
            # cannot act: fold is only possible if facing a bet
            node.terminal = TERMINAL_FOLD if to_call > 0 else TERMINAL_SHOWDOWN
            if node.terminal == TERMINAL_FOLD:
                node.winner = opp
            else:
                node.pot = node.pot + node.inv[0] + node.inv[1]
            return

        acts: list[Action] = []
        if to_call <= 0:
            acts.append(Action(CHECK, 0))
            if stack_o > 0:  # opponent has chips -> betting reopens
                for frac in cfg.bet_sizes.get(node.street, (0.5,)):
                    amt = min(cfg.bet_amount(node.pot, frac), stack_p)
                    if amt > 0:
                        acts.append(Action(BET, amt))
                # explicit all-in option (no-limit always allows it)
                acts.append(Action(BET, stack_p))
        else:
            acts.append(Action(FOLD, 0))
            acts.append(Action(CALL, 0))
            if stack_p > to_call and stack_o > 0:
                last_bet = node.inv[opp]  # total street contribution to re-raise on top
                for frac in cfg.raise_sizes.get(node.street, (1.0,)):
                    target = cfg.raise_to(node.pot, to_call, last_bet, frac)
                    target = max(target, node.inv[opp] + to_call)  # at least min-raise
                    amt = min(target, node.inv[p] + stack_p)       # cap at all-in
                    if amt > node.inv[opp]:
                        acts.append(Action(RAISE, amt))
                # explicit shove option
                acts.append(Action(RAISE, node.inv[p] + stack_p))

        # dedupe (e.g. two sizes capped to the same all-in)
        seen = set()
        uniq = []
        for a in acts:
            if (a.type, a.amount) not in seen:
                seen.add((a.type, a.amount))
                uniq.append(a)
        node.actions = uniq

        def _fold_child() -> None:
            node.children.append(
                Node(
                    (),
                    0,
                    0,
                    node.pot,
                    node.inv,
                    terminal=TERMINAL_FOLD,
                    winner=1 - p,
                )
            )

        def _child(a: Action) -> None:
            new_inv = list(node.inv)
            new_pot = node.pot
            if a.type == CHECK:
                pass
            elif a.type == CALL:
                new_pot += to_call
                new_inv[p] += to_call
            elif a.type == BET:
                new_pot += a.amount
                new_inv[p] += a.amount
            else:  # RAISE
                amt = a.amount - new_inv[p]
                new_pot += amt
                new_inv[p] = a.amount
            new_inv = tuple(new_inv)

            if new_inv[0] == new_inv[1]:
                if node.street == 3:
                    node.children.append(
                        Node(
                            (),
                            0,
                            0,
                            new_pot,
                            new_inv,
                            terminal=TERMINAL_SHOWDOWN,
                        )
                    )
                else:
                    k = state_key(node.street + 1, new_pot, (0, 0), 0)
                    child = nodes.get(k)
                    if child is None:
                        child = Node(k, node.street + 1, 0, new_pot, (0, 0))
                        nodes[k] = child
                    node.children.append(child)
            else:
                k = state_key(node.street, new_pot, new_inv, opp)
                child = nodes.get(k)
                if child is None:
                    child = Node(k, node.street, opp, new_pot, new_inv)
                    nodes[k] = child
                node.children.append(child)

        if cfg.push_fold and node.street == 0 and node.to_act == 0:
            # restricted tree: SB shoves or folds
            node.actions = [Action(FOLD, 0), Action(RAISE, node.inv[p] + stack_p)]
            _fold_child()
            _child(node.actions[1])
            return

        for a in uniq:
            if a.type == FOLD:
                _fold_child()
            else:
                _child(a)

    if start_street == 0 and start_inv == (0, 0):
        start_inv = (cfg.sb, cfg.bb)
        start_pot = cfg.sb + cfg.bb
    root_key = state_key(start_street, start_pot, start_inv, 0)
    root = Node(root_key, start_street, 0, start_pot, start_inv)
    nodes[root_key] = root
    frontier = [root]
    expanded = set()
    while frontier:
        n = frontier.pop()
        if n.key in expanded:
            continue
        expanded.add(n.key)
        expand(n)
        for child in n.children:
            if child.terminal is None and child.key not in expanded:
                frontier.append(child)
    return nodes, root_key


def tree_stats(nodes: dict[tuple, Node]) -> str:
    t = sum(1 for n in nodes.values() if n.terminal)
    return f"{len(nodes)} decision nodes, {t} terminal nodes"