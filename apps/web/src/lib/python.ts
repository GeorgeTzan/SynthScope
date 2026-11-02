import { parseProgram } from './sexpr';
import type { Tree } from './types';

/** Display translation of a solved program into Python. It is not the Python `ast` module and is never executed. */

type Kind = 'bv' | 'str';
interface Code {
  text: string;
  /** Binary-looking expression that may carry bits above the bitvector width until it is masked. */
  dirty: boolean;
  atom: boolean;
}

const INFIX_RING: Record<string, string> = { bvadd: '+', bvsub: '-', bvmul: '*', bvand: '&', bvor: '|', bvxor: '^' };
const INFIX_CLEAN: Record<string, string> = { bvlshr: '>>', '=': '==' };
// SMT-LIB semantics differ from Python (division by zero, signs), so these stay as named calls.
const CALLS = new Set(['bvudiv', 'bvurem', 'bvsdiv', 'bvsrem', 'bvashr']);

function constant(label: string): string | null {
  if (/^-?\d+$/.test(label)) return label;
  if (/^#b[01]+$/.test(label)) return BigInt(`0b${label.slice(2)}`).toString();
  if (/^#x[0-9a-f]+$/i.test(label)) return BigInt(`0x${label.slice(2)}`).toString();
  if (label === 'true') return 'True';
  if (label === 'false') return 'False';
  if (label.startsWith('"') && label.endsWith('"') && label.length >= 2) return JSON.stringify(label.slice(1, -1).replaceAll('""', '"'));
  return null;
}

const wrap = (c: Code): string => (c.atom ? c.text : `(${c.text})`);
const isIndex = (t: Tree): boolean => /^\d+$/.test(t.label) && t.children.length === 0;

function render(t: Tree, kind: Kind, width: number | null): Code {
  if (t.children.length === 0) {
    if (t.hole !== null) return { text: '...', dirty: false, atom: true };
    return { text: constant(t.label) ?? t.label, dirty: false, atom: true };
  }
  const mask = width === null ? '' : String((1n << BigInt(width)) - 1n);
  const clean = (c: Code): string => (c.dirty ? `(${c.text}) & ${mask}` : c.text);
  const cleanWrapped = (c: Code): string => (c.dirty ? `((${c.text}) & ${mask})` : wrap(c));
  const args = t.children.map((c) => render(c, kind, width));
  const op = t.label;
  const [a, b, c] = args;

  if (kind === 'bv') {
    if (op in INFIX_RING && args.length === 2) {
      // & stays within the width if either side does; | and ^ only if both do; + - * can overflow.
      const dirty = op === 'bvand' ? a.dirty && b.dirty : op === 'bvor' || op === 'bvxor' ? a.dirty || b.dirty : true;
      return { text: `${wrap(a)} ${INFIX_RING[op]} ${wrap(b)}`, dirty, atom: false };
    }
    if (op === 'bvnot' && args.length === 1) return { text: `~${wrap(a)}`, dirty: true, atom: false };
    if (op === 'bvneg' && args.length === 1) return { text: `-${wrap(a)}`, dirty: true, atom: false };
    if (op === 'bvshl' && args.length === 2) {
      return { text: `${cleanWrapped(a)} << ${cleanWrapped(b)} if ${cleanWrapped(b)} < ${width} else 0`, dirty: true, atom: false };
    }
    if (op in INFIX_CLEAN && args.length === 2) {
      return { text: `${cleanWrapped(a)} ${INFIX_CLEAN[op]} ${cleanWrapped(b)}`, dirty: false, atom: false };
    }
  } else {
    if (op === 'str.++' && args.length >= 2) return { text: args.map(wrap).join(' + '), dirty: false, atom: false };
    if ((op === '+' || op === '-' || op === '=') && args.length === 2) {
      return { text: `${wrap(a)} ${op === '=' ? '==' : op} ${wrap(b)}`, dirty: false, atom: false };
    }
    if (op === 'str.len' && args.length === 1) return { text: `len(${a.text})`, dirty: false, atom: true };
    if (op === 'str.at' && args.length === 2 && isIndex(t.children[1])) {
      return { text: `${wrap(a)}[${b.text}:${Number(b.text) + 1}]`, dirty: false, atom: true };
    }
    if (op === 'str.substr' && args.length === 3 && isIndex(t.children[1]) && isIndex(t.children[2])) {
      return { text: `${wrap(a)}[${b.text}:${Number(b.text) + Number(c.text)}]`, dirty: false, atom: true };
    }
    if (op === 'str.prefixof' && args.length === 2) return { text: `${wrap(b)}.startswith(${a.text})`, dirty: false, atom: true };
    if (op === 'str.suffixof' && args.length === 2) return { text: `${wrap(b)}.endswith(${a.text})`, dirty: false, atom: true };
    if (op === 'str.contains' && args.length === 2) return { text: `${wrap(b)} in ${wrap(a)}`, dirty: false, atom: false };
  }
  if (op === 'ite' && args.length === 3) {
    return { text: `${clean(b)} if ${clean(a)} else ${clean(c)}`, dirty: false, atom: false };
  }
  if (op === 'and' && args.length === 2) return { text: `${wrap(a)} and ${wrap(b)}`, dirty: false, atom: false };
  if (op === 'or' && args.length === 2) return { text: `${wrap(a)} or ${wrap(b)}`, dirty: false, atom: false };
  if (op === 'not' && args.length === 1) return { text: `not ${wrap(a)}`, dirty: false, atom: false };
  // Named call: bvudiv(a, b), str_replace(a, b, c). Arguments are reduced to the bitvector width first.
  const name = CALLS.has(op) ? op : op.replaceAll('.', '_');
  return { text: `${name}(${args.map((x) => (width === null ? x.text : clean(x))).join(', ')})`, dirty: false, atom: true };
}

/** Python expression for a program, e.g. `(bvmul x x)` becomes `(x * x) & 255` for 8-bit values. */
export function toPythonExpression(program: string, kind: Kind, width: number | null): string {
  const code = render(parseProgram(program), kind, width);
  if (!code.dirty || width === null) return code.text;
  const mask = (1n << BigInt(width)) - 1n;
  return /^[~-]?[\w.]+$/.test(code.text) ? `${code.text} & ${mask}` : `(${code.text}) & ${mask}`;
}

const HELPERS: Record<string, (mask: bigint | null) => string> = {
  str_at: () => 'def str_at(s, i):\n    return s[i] if 0 <= i < len(s) else ""',
  str_substr: () => 'def str_substr(s, i, n):\n    return s[i:i + n] if 0 <= i < len(s) and n > 0 else ""',
  str_indexof: () => 'def str_indexof(s, t, i):\n    return s.find(t, i) if 0 <= i <= len(s) else -1',
  str_replace: () => 'def str_replace(s, t, u):\n    return s.replace(t, u, 1)',
  bvudiv: (m) => `def bvudiv(a, b):\n    return a // b if b else ${m ?? 0}`,
  bvurem: () => 'def bvurem(a, b):\n    return a % b if b else a'
};

/** A complete runnable `def`, preceded by small helpers for operations whose SMT-LIB meaning differs from Python's. */
export function toPythonFunction(program: string, name: string, params: string[], kind: Kind, width: number | null): string {
  let expr: string;
  try {
    expr = toPythonExpression(program, kind, width);
  } catch {
    return `# could not translate: ${program}`;
  }
  const mask = width === null ? null : (1n << BigInt(width)) - 1n;
  const helpers = Object.keys(HELPERS).filter((h) => new RegExp(`\\b${h}\\(`).test(expr)).map((h) => HELPERS[h](mask));
  const body = `def ${name}(${params.join(', ')}):\n    return ${expr}`;
  return [...helpers, body].join('\n\n');
}
