"""Small SyGuS-IF reader: one synth-fun with an explicit grammar plus `(= (f lits) lit)` constraints.

[ponytail: hand-written S-expression reader, no parser library; only the subset the audited benchmarks use.]
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from hope_engine.concrete.bitvector import BINARY, UNARY, UnsupportedOperator
from hope_engine.concrete.string import OPS
from hope_engine.concrete.verify import Example
from hope_engine.enumeration.search import Problem
from hope_engine.syntax.ast import Const, Var
from hope_engine.syntax.grammar import Grammar, Production

BV_OPS = frozenset(UNARY) | frozenset(BINARY)


class SygusError(ValueError):
    def __init__(self, message: str, line: int, col: int) -> None:
        super().__init__(f"{line}:{col}: {message}")
        self.line, self.col = line, col


@dataclass(frozen=True)
class Tok:
    text: str
    line: int
    col: int
    is_str: bool = False


@dataclass(frozen=True)
class Atom:
    tok: Tok


@dataclass(frozen=True)
class SList:
    items: tuple[Sx, ...]
    tok: Tok


type Sx = Atom | SList

_TOKEN = re.compile(r'\s+|;[^\n]*|(?P<lp>\()|(?P<rp>\))|(?P<str>"(?:[^"]|"")*")|(?P<sym>[^\s()";]+)')


def _tokens(text: str) -> list[Tok]:
    out: list[Tok] = []
    pos, line, col = 0, 1, 1
    while pos < len(text):
        m = _TOKEN.match(text, pos)
        if m is None:
            raise SygusError("unterminated string or bad character", line, col)
        chunk = m.group(0)
        if m.lastgroup == "str":
            out.append(Tok(chunk[1:-1].replace('""', '"'), line, col, True))
        elif m.lastgroup in ("lp", "rp", "sym"):
            out.append(Tok(chunk, line, col))
        nl = chunk.count("\n")
        if nl:
            line += nl
            col = len(chunk) - chunk.rfind("\n")
        else:
            col += len(chunk)
        pos = m.end()
    return out


def _read(toks: list[Tok]) -> list[Sx]:
    stack: list[tuple[Tok, list[Sx]]] = []
    top: list[Sx] = []
    for t in toks:
        if t.text == "(" and not t.is_str:
            stack.append((t, top))
            top = []
        elif t.text == ")" and not t.is_str:
            if not stack:
                raise SygusError("unexpected ')'", t.line, t.col)
            open_tok, parent = stack.pop()
            parent.append(SList(tuple(top), open_tok))
            top = parent
        else:
            top.append(Atom(t))
    if stack:
        raise SygusError("unclosed '('", stack[-1][0].line, stack[-1][0].col)
    return top


def _pos(x: Sx) -> tuple[int, int]:
    return (x.tok.line, x.tok.col)


def _err(msg: str, x: Sx) -> SygusError:
    return SygusError(msg, *_pos(x))


def _sym(x: Sx) -> str:
    if not isinstance(x, Atom) or x.tok.is_str:
        raise _err("expected a symbol", x)
    return x.tok.text


def _literal(a: Atom) -> tuple[int | str, str] | None:
    t = a.tok
    if t.is_str:
        return t.text, "str"
    if re.fullmatch(r"#b[01]+", t.text):
        return int("0b" + t.text[2:], 0), "bv"
    if re.fullmatch(r"#x[0-9a-fA-F]+", t.text):
        return int(t.text.replace("#x", "0x"), 0), "bv"
    if re.fullmatch(r"-?\d+", t.text):
        return int(t.text), "int"
    if t.text.startswith("#"):
        raise _err(f"bad literal {t.text!r}", a)
    return None


def _sort(x: Sx) -> tuple[str, int | None]:
    if isinstance(x, SList):
        words = [_sym(i) for i in x.items]
        if words[:2] == ["_", "BitVec"] and len(words) == 3:  # SyGuS-IF v2: (_ BitVec n)
            return "bv", int(words[2])
        if words[:1] == ["BitVec"] and len(words) == 2:  # v1: (BitVec n)
            return "bv", int(words[1])
    if isinstance(x, Atom) and x.tok.text in ("String", "Int"):
        return "str", None
    raise _err("unsupported sort", x)


def _production(lhs: str, x: Sx, params: set[str], nts: set[str], domain: str) -> Production:
    if isinstance(x, Atom):
        lit = _literal(x)
        if lit is not None:
            return Production(lhs, Const(lit[0], lit[1]))
        if x.tok.text in params:
            return Production(lhs, Var(x.tok.text))
        raise _err("chain rules and unknown symbols are not supported", x)
    if not x.items:
        raise _err("empty production", x)
    op = _sym(x.items[0])
    known = BV_OPS if domain == "bv" else frozenset(OPS)
    if op not in known:
        raise UnsupportedOperator(f"{op} at {_pos(x)[0]}:{_pos(x)[1]}")
    rhs: list[str] = []
    for a in x.items[1:]:
        nt = _sym(a)
        if nt not in nts:
            raise _err(f"argument {nt!r} must be a nonterminal", a)
        rhs.append(nt)
    return Production(lhs, op, tuple(rhs))


def _constraint(x: Sx, fname: str, params: list[str], domain: str) -> Example:
    items = x.items if isinstance(x, SList) else ()
    if len(items) != 3 or _sym(items[0]) != "=":
        raise _err("only (= (f literals...) literal) constraints are supported", x)
    call, out = items[1], items[2]
    if isinstance(out, SList):
        call, out = out, call
    if not (isinstance(call, SList) and call.items and _sym(call.items[0]) == fname) or not isinstance(out, Atom):
        raise _err("constraint must compare a call of the synthesized function with a literal", x)
    args = call.items[1:]
    if len(args) != len(params):
        raise _err("wrong number of arguments", call)
    vals: list[int | str] = []
    for a in (*args, out):
        lit = _literal(a) if isinstance(a, Atom) else None
        if lit is None:
            raise _err("expected a literal", a)
        vals.append(lit[0])
    return Example(dict(zip(params, vals[:-1], strict=True)), vals[-1])


def parse_sygus(text: str) -> Problem:
    forms = _read(_tokens(text))
    synth: SList | None = None
    constraints: list[SList] = []
    for f in forms:
        if isinstance(f, SList) and f.items and isinstance(f.items[0], Atom):
            head = f.items[0].tok.text
            if head == "synth-fun":
                if synth is not None:
                    raise _err("only one synth-fun is supported", f)
                synth = f
            elif head == "constraint":
                constraints.append(f)
    if synth is None:
        raise SygusError("no synth-fun found", 1, 1)
    if len(synth.items) < 5 or not isinstance(synth.items[2], SList) or not isinstance(synth.items[4], SList):
        raise _err("synth-fun needs an explicit grammar", synth)
    fname = _sym(synth.items[1])
    params: list[str] = []
    domains: set[str] = set()
    width: int | None = None
    for p in synth.items[2].items:
        if not isinstance(p, SList) or len(p.items) != 2:
            raise _err("bad parameter", p)
        params.append(_sym(p.items[0]))
        d, w = _sort(p.items[1])
        domains.add(d)
        width = w if w is not None else width
    ret_d, ret_w = _sort(synth.items[3])
    domains.add(ret_d)
    if len(domains) != 1:
        raise _err("mixed bitvector and string signatures are not supported", synth)
    domain = domains.pop()
    width = ret_w if ret_w is not None else width
    rules = synth.items[4].items
    nts = {_sym(r.items[0]) for r in rules if isinstance(r, SList) and r.items}
    prods: list[Production] = []
    for r in rules:
        if not isinstance(r, SList) or len(r.items) != 3 or not isinstance(r.items[2], SList):
            raise _err("bad grammar rule", r)
        lhs = _sym(r.items[0])
        prods += [_production(lhs, alt, set(params), nts, domain) for alt in r.items[2].items]
    start = _sym(rules[0].items[0]) if isinstance(rules[0], SList) else ""
    examples = tuple(_constraint(c.items[1], fname, params, domain) for c in constraints if len(c.items) == 2)
    if not examples:
        raise _err("no constraints", synth)
    return Problem(Grammar(tuple(prods), start), examples, "bv" if domain == "bv" else "str", width)


def load_problem(path: Path) -> Problem:
    return parse_sygus(path.read_text(encoding="utf-8"))
