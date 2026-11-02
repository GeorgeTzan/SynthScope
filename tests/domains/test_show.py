from hope_engine.domains.bitvector.lattice import alpha as bv_alpha
from hope_engine.domains.bitvector.lattice import bottom, join, top
from hope_engine.domains.bitvector.ops import BitvectorDomain
from hope_engine.domains.string.lattice import BOT, INF, TOP, Itv, alpha, mk_str
from hope_engine.domains.string.ops import StringDomain


def test_bitvector_states_are_readable() -> None:
    d = BitvectorDomain(4)
    assert d.show(bv_alpha(4, 9)) == "#x9"
    assert d.show(top(4)) == "⊤"
    assert d.show(bottom(4)) == "⊥"
    s = d.show(join(bv_alpha(4, 0b0100), bv_alpha(4, 0b0110)))
    assert "[4, 6]" in s and "01?0" in s


def test_string_states_are_readable() -> None:
    d = StringDomain()
    assert d.show(alpha("ab")) == '"ab"'
    assert d.show(Itv(2, 5)) == "[2, 5]"
    assert d.show(Itv(0, INF)) == "[0, ∞)"
    assert d.show(TOP) == "⊤" and d.show(BOT) == "⊥"
    shown = d.show(mk_str("ab*", "yz", 4, INF))
    assert 'prefix "ab*"' in shown and 'suffix "yz"' in shown and "len [4, ∞)" in shown
