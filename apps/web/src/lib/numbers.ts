/** Build a SyGuS-IF bitvector problem from plain number examples (`2 -> 4`), so nobody has to write binary literals. */

export const NUMBER_OPS = [
  { name: 'bvadd', symbol: '+', arity: 2 },
  { name: 'bvsub', symbol: '-', arity: 2 },
  { name: 'bvmul', symbol: '×', arity: 2 },
  { name: 'bvand', symbol: '&', arity: 2 },
  { name: 'bvor', symbol: '|', arity: 2 },
  { name: 'bvxor', symbol: '^', arity: 2 },
  { name: 'bvshl', symbol: '<<', arity: 2 },
  { name: 'bvlshr', symbol: '>>', arity: 2 },
  { name: 'bvudiv', symbol: '÷', arity: 2 },
  { name: 'bvurem', symbol: '%', arity: 2 },
  { name: 'bvnot', symbol: '~', arity: 1 },
  { name: 'bvneg', symbol: '−x', arity: 1 }
] as const;

export const WIDTHS = [4, 8, 16, 32] as const;
export const MAX_NUMBER_ROWS = 50;
const PARAM_NAMES = ['x', 'y', 'z'];
const OPS = new Map<string, number>(NUMBER_OPS.map((o) => [o.name, o.arity]));

export interface NumbersSpec {
  width: number;
  /** One row per example: the inputs, then the output. */
  rows: bigint[][];
  ops: string[];
  constants: bigint[];
}

/** A plain-number literal: decimal, 0x.., 0b.., optionally negative. Throws on anything else. */
export function parseInteger(token: string): bigint {
  const m = /^(-?)(0x[0-9a-f]+|0b[01]+|\d+)$/i.exec(token.trim());
  if (!m) throw new Error(`"${token}" is not a whole number`);
  const value = BigInt(m[2]);
  return m[1] ? -value : value;
}

/** One example per line (or `;`): `2 -> 4`, `2, 3 -> 6`, or `2 4` (last number is the output). */
export function parseRows(text: string): bigint[][] {
  const rows: bigint[][] = [];
  const lines = text.split(/[\n;]/).map((l) => l.trim()).filter((l) => l !== '' && !l.startsWith('#'));
  lines.forEach((line, i) => {
    const where = `Example ${i + 1}`;
    const parts = line.split(/->|=>|→/);
    if (parts.length > 2) throw new Error(`${where}: more than one arrow`);
    const tokens = (s: string) => s.split(/[\s,]+/).filter(Boolean);
    try {
      if (parts.length === 2) {
        const out = tokens(parts[1]);
        if (out.length !== 1) throw new Error('exactly one output is expected after the arrow');
        rows.push([...tokens(parts[0]).map(parseInteger), parseInteger(out[0])]);
      } else rows.push(tokens(line).map(parseInteger));
    } catch (e) {
      throw new Error(`${where}: ${(e as Error).message}`);
    }
  });
  return rows;
}

export function parseConstants(text: string): bigint[] {
  return text.split(/[\s,]+/).filter(Boolean).map(parseInteger);
}

function literal(value: bigint, width: number): string {
  const lo = -(1n << BigInt(width - 1));
  const hi = (1n << BigInt(width)) - 1n;
  if (value < lo || value > hi) throw new Error(`${value} does not fit in ${width} bits (${lo} to ${hi})`);
  const bits = (value & ((1n << BigInt(width)) - 1n)).toString(2).padStart(width, '0');
  return `#b${bits}`;
}

/** SyGuS-IF text for the spec. Throws an Error with a user-readable message when the spec is not usable. */
export function buildNumbersProblem(spec: NumbersSpec): string {
  const { width, rows, ops, constants } = spec;
  if (!(WIDTHS as readonly number[]).includes(width)) throw new Error(`Width must be one of ${WIDTHS.join(', ')}`);
  if (rows.length === 0) throw new Error('Add at least one example');
  if (rows.length > MAX_NUMBER_ROWS) throw new Error(`At most ${MAX_NUMBER_ROWS} examples`);
  const arity = rows[0].length - 1;
  if (arity < 1 || arity > PARAM_NAMES.length) throw new Error(`Use between 1 and ${PARAM_NAMES.length} inputs per example`);
  if (rows.some((r) => r.length !== arity + 1)) throw new Error('Every example needs the same number of inputs');
  if (ops.length === 0) throw new Error('Pick at least one operation');
  const unknown = ops.find((o) => !OPS.has(o));
  if (unknown) throw new Error(`Unknown operation ${unknown}`);

  const seen = new Map<string, bigint>();
  for (const r of rows) {
    const key = r.slice(0, -1).join(',');
    const out = r[arity];
    if (seen.has(key) && seen.get(key) !== out) throw new Error(`Conflicting outputs for input ${key}`);
    seen.set(key, out);
  }

  const params = PARAM_NAMES.slice(0, arity);
  const sort = `(BitVec ${width})`;
  const alternatives = [
    ...params,
    ...constants.map((c) => literal(c, width)),
    ...ops.map((o) => `(${o}${' Start'.repeat(OPS.get(o) ?? 0)})`)
  ];
  const constraints = rows.map((r) => `(constraint (= (f ${r.slice(0, -1).map((v) => literal(v, width)).join(' ')}) ${literal(r[arity], width)}))`);
  return [
    '(set-logic BV)',
    `(synth-fun f (${params.map((p) => `(${p} ${sort})`).join(' ')}) ${sort}`,
    `  ((Start ${sort} (${alternatives.join(' ')}))))`,
    ...constraints,
    '(check-synth)',
    ''
  ].join('\n');
}
