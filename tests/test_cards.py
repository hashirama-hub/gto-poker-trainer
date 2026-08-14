import itertools
import random

import pytest

from gto import cards as C


def test_card_encoding_roundtrip():
    for c in range(52):
        assert C.make_card(c // 4, c % 4) == c
        assert C.parse_card(C.card_str(c)) == c


def test_parse_errors():
    with pytest.raises(ValueError):
        C.parse_card("Xx")
    with pytest.raises(ValueError):
        C.parse_card("A")


def test_strength_density():
    values = {C.evaluate_5(c) for c in itertools.combinations(range(52), 5)}
    assert values == set(range(1, 7463))


def test_categories():
    cases = [
        ("As Ks Qs Js Ts", "Straight Flush", 7462),
        ("2h 3h 4h 5h 6h", "Straight Flush", None),
        ("Ah Ac Ad As Kd", "Four of a Kind", None),
        ("As Ah Ad Kc Kd", "Full House", None),
        ("2h 3c 4h 5h 6h 9s Kd", "Straight", None),
        ("7c 5c 4c 3c 2c", "Flush", None),
        ("Th Td Tc 2h 7d Qs 3c", "Three of a Kind", None),
        ("Ah As Kd Kc 2h 7d Qs", "Two Pair", None),
        ("7c 5d 4h 3s 2c 9d Kh", "High Card", None),
    ]
    for text, cat, want in cases:
        v = C.evaluate(C.parse_cards(text))
        assert C.category_of(v) == cat
        if want is not None:
            assert v == want


def test_monotonic_vs_brute():
    random.seed(11)

    def brute(hole):
        best = (0, ())
        for combo in itertools.combinations(hole, 5):
            rs = tuple(sorted(c // 4 for c in combo))
            suited = len({c % 4 for c in combo}) == 1
            k = C._pattern_key(rs)
            if suited and k[0] == 4:
                cat = 8
            elif suited and k[0] == 0:
                cat = 5
            else:
                cat = k[0]
            best = max(best, (cat, k[1]))
        return best

    for _ in range(3000):
        a, b = random.sample(range(52), 7), random.sample(range(52), 7)
        assert (C.evaluate(a) > C.evaluate(b)) == (brute(a) > brute(b))


def test_evaluate_memoized():
    cards = C.parse_cards("As Kh 2c 3d 4h 9s Jd")
    assert C.evaluate(cards) == C.evaluate(tuple(cards))


def test_deck():
    d = C.Deck(seed=42)
    assert len(d.deal(2)) == 2 and len(d.deal(5)) == 5
    with pytest.raises(ValueError):
        C.Deck().deal(53)


def test_vectorized():
    import numpy as np

    hands = np.array([[48, 49], [40, 41]])
    board = np.array([0, 4, 8, 12, 16])
    out = C.evaluate_vectorized(hands, board)
    assert out.shape == (2, 1)
    assert out[0, 0] == C.evaluate((48, 49, 0, 4, 8, 12, 16))