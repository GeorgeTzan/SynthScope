import itertools

from hope_engine.meta.bitvector import BitvectorMeta
from hope_engine.meta.lattice import Meta

ALL = list(Meta)
D = BitvectorMeta()


def test_order_is_bot_must_may() -> None:
    assert Meta.BOT < Meta.MUST_TOP < Meta.MAY_NOT_TOP


def test_join_laws() -> None:
    for a, b, c in itertools.product(ALL, repeat=3):
        assert D.join(a, b) == D.join(b, a)
        assert D.join(D.join(a, b), c) == D.join(a, D.join(b, c))
    for a in ALL:
        assert D.join(a, a) == a and D.join(a, D.bottom()) == a


def test_predicates() -> None:
    assert D.is_may(Meta.MAY_NOT_TOP) and not D.is_must(Meta.MAY_NOT_TOP)
    assert D.is_must(Meta.MUST_TOP) and not D.is_may(Meta.MUST_TOP)
    assert not D.is_may(Meta.BOT) and not D.is_must(Meta.BOT)
