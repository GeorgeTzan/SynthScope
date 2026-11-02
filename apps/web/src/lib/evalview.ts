import type { EvaluatedExample } from './types';

const MAX_TEXT = 14;

/** Short display text for a value shown on a node. Strings are quoted and cut; null means the engine could not compute it. */
export function formatNodeValue(v: number | string | null | undefined): string {
  if (v === null || v === undefined) return '?';
  if (typeof v === 'number') return String(v);
  const cut = v.length > MAX_TEXT ? `${v.slice(0, MAX_TEXT - 1)}…` : v;
  return JSON.stringify(cut);
}

/** `x = 3, y = 4` */
export function describeInputs(row: EvaluatedExample): string {
  return Object.entries(row.inputs).map(([k, v]) => `${k} = ${typeof v === 'string' ? JSON.stringify(v) : v}`).join(', ');
}

/** Did the program's root value equal the expected output on this example? */
export function matches(row: EvaluatedExample): boolean {
  return row.values[''] === row.expected;
}
