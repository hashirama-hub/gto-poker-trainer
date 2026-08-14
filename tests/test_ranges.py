import pytest

from gto.ranges import Range


@pytest.mark.parametrize(
    "text,count",
    [
        ("AA", 6),
        ("KK", 6),
        ("AKs", 4),
        ("AKo", 12),
        ("22-77", 36),
        ("ATs+", 16),
        ("KQo+", 36),  # KQo, AQo, AKo (GTO Wizard convention)
        ("22+", 78),
        ("QQ-KK", 12),
        ("", 0),
        ("AKs, AKo", 16),
    ],
)
def test_parse_counts(text, count):
    assert len(Range().from_text(text)) == count


def test_invalid_hand_raises():
    with pytest.raises(ValueError):
        Range().from_text("AXs")


def test_mask_out_cards():
    r = Range().from_text("AA").mask_out_cards([48, 49])  # remove As, Ah
    assert len(r) == 1
    r = Range().from_text("AA").mask_out_cards([48])
    assert len(r) == 3


def test_normalize_total():
    r = Range().from_text("AKs")
    assert r.total() == 4.0
    r.normalize()
    assert abs(r.total() - 1.0) < 1e-9


def test_add_remove():
    a = Range().from_text("AA")
    b = Range().from_text("AA")
    assert a.add(b).total() == 12.0
    assert a.remove(Range().from_text("AA")).total() == 6.0


def test_equity_sanity():
    r = Range().from_text("AA")
    board = (0, 4, 8)  # 2c 2d 2h -> trip deuces
    e = r.equity_vs_combo((48, 49), board)  # AsAh vs AA
    assert 0.0 <= e <= 1.0
    # 22 makes a pair on disconnected board -> crushes A-high
    r2 = Range().from_text("22")
    e2 = r2.equity_vs_combo((48, 49), (20, 24, 28))  # Kc 4s 6c
    assert e2 > 0.9


def test_equity_requires_board():
    with pytest.raises(ValueError):
        Range().from_text("AA").equity_vs_combo((48, 49))


def test_grid_output():
    g = Range().from_text("AA, KQs").grid()
    assert "AA" in g and "KQs" in g and "KQo" not in g


def test_roundtrip_text():
    r = Range().from_text("AA, AKs, 22-77, KQo")
    out = r.to_text()
    for name in ("AA", "AKs", "KQo"):
        assert name in out
    assert "66" in out