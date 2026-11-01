"""Meta abstract interpreter Analyze# (paper §4.3, Example 4.1)."""

from __future__ import annotations

from collections.abc import Collection

from hope_engine.meta.lattice import MetaDomain
from hope_engine.syntax.ast import Const, Hole, Node, Op, Path, Var


def meta_analyze[M](
    domain: MetaDomain[M], partial: Node, hypo: Collection[Path]
) -> dict[Path, tuple[M, M]]:
    """Return (forward, backward) meta values per position, with the holes in `hypo` hypothetically filled.

    X is the least state above both initial states closed under F## and B## (the limit of the paper's
    alternating chain, computed by chaotic iteration from bottom). Then
    A_F = I_F ⊔ F##(X) and A_B = I_B ⊔ B##(X).
    """
    nodes: dict[Path, Node] = {}
    parent: dict[Path, tuple[Path, int]] = {}

    def walk(n: Node, p: Path) -> None:
        nodes[p] = n
        if isinstance(n, Op):
            for i, a in enumerate(n.args):
                parent[(*p, i)] = (p, i)
                walk(a, (*p, i))

    walk(partial, ())
    hypo_set = set(hypo)
    bot, must, may = domain.bottom(), domain.must(), domain.may()

    def init_f(p: Path) -> M:
        return may if p in hypo_set or isinstance(nodes[p], Const | Var) else bot

    def init_b(p: Path) -> M:
        return may if p == () else must

    def f_sharp(x: dict[Path, M], p: Path) -> M:
        n = nodes[p]
        if isinstance(n, Hole):
            return bot if p in hypo_set else must
        if isinstance(n, Op):
            return domain.forward(n.name, [x[(*p, i)] for i in range(len(n.args))])
        return bot

    def b_sharp(x: dict[Path, M], p: Path) -> M:
        if p not in parent:
            return must
        q, i = parent[p]
        n = nodes[q]
        assert isinstance(n, Op)
        return domain.backward(n.name, x[q], [x[(*q, j)] for j in range(len(n.args))], i)

    x: dict[Path, M] = {p: bot for p in nodes}
    changed = True
    while changed:
        changed = False
        for p in nodes:
            new = domain.join(x[p], domain.join(domain.join(init_f(p), f_sharp(x, p)), domain.join(init_b(p), b_sharp(x, p))))
            if new != x[p]:
                x[p], changed = new, True
    return {
        p: (domain.join(init_f(p), f_sharp(x, p)), domain.join(init_b(p), b_sharp(x, p))) for p in nodes
    }
