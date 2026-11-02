import type { LaidOutNode } from './layout';
import type { HoleRanks, Tree } from './types';

export interface HoleInfo {
  index: number; // 1-based, left to right
  path: number[];
  nonterminal: string;
  rank: 1 | 2 | 3 | null; // null before the engine has ranked anything
  picked: boolean;
}

const key = (path: number[]): string => path.join('.');
const inSets = (sets: number[][][], k: string): boolean => sets.some((s) => s.some((p) => key(p) === k));

export function holeInfos(nodes: LaidOutNode[], ranks: HoleRanks | null): HoleInfo[] {
  const picked = new Set((ranks?.picked ?? []).map(key));
  return nodes
    .filter((n) => n.hole !== null)
    .map((n, i): HoleInfo => {
      const k = key(n.path);
      const rank = ranks === null ? null : inSets(ranks.rank1, k) ? 1 : inSets(ranks.rank2, k) ? 2 : 3;
      return { index: i + 1, path: n.path, nonterminal: n.hole ?? '', rank, picked: picked.has(k) };
    });
}

const SUB = '₀₁₂₃₄₅₆₇₈₉';
const subscript = (n: number): string => [...String(n)].map((d) => SUB[Number(d)]).join('');

export interface Segment {
  text: string;
  kind: 'op' | 'hole' | 'leaf' | 'punct';
}

/** The call-style text of a program in coloured pieces: `bvadd(bvmul(x, □₁), □₂)`. */
export function callSegments(root: Tree): Segment[] {
  let next = 0;
  const out: Segment[] = [];
  const go = (t: Tree): void => {
    if (t.hole !== null) {
      out.push({ text: `□${subscript(++next)}`, kind: 'hole' });
    } else if (t.children.length === 0) {
      out.push({ text: t.label, kind: 'leaf' });
    } else {
      out.push({ text: t.label, kind: 'op' }, { text: '(', kind: 'punct' });
      t.children.forEach((c, i) => {
        if (i > 0) out.push({ text: ', ', kind: 'punct' });
        go(c);
      });
      out.push({ text: ')', kind: 'punct' });
    }
  };
  go(root);
  return out;
}

/** `(bvadd (bvmul x □:S) □:S)` as `bvadd(bvmul(x, □₁), □₂)`. */
export function callSyntax(root: Tree): string {
  return callSegments(root)
    .map((s) => s.text)
    .join('');
}

import { layoutTree, type Layout } from './layout';
import { parseProgram } from './sexpr';

export interface ProgramView {
  tree: Tree | null;
  layout: Layout | null;
  holes: HoleInfo[];
  call: string;
  error: string | null;
}

/** Everything the dashboard draws about one partial program, computed once. */
export function buildView(program: string | null, ranks: HoleRanks | null): ProgramView {
  if (!program) return { tree: null, layout: null, holes: [], call: '', error: null };
  try {
    const tree = parseProgram(program);
    const layout = layoutTree(tree);
    return { tree, layout, holes: holeInfos(layout.nodes, ranks), call: callSyntax(tree), error: null };
  } catch (e) {
    return { tree: null, layout: null, holes: [], call: '', error: e instanceof Error ? e.message : String(e) };
  }
}
