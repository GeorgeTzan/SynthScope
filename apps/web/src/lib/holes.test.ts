import { describe, expect, it } from 'vitest';
import { callSyntax, holeInfos } from './holes';
import { layoutTree } from './layout';
import { parseProgram } from './sexpr';

const tree = parseProgram('(bvadd (bvmul x □:Start) □:Num)');

describe('holeInfos', () => {
  it('numbers holes left to right and keeps their nonterminal and path', () => {
    const infos = holeInfos(layoutTree(tree).nodes, null);
    expect(infos.map((h) => [h.index, h.path, h.nonterminal, h.rank, h.picked])).toEqual([
      [1, [0, 1], 'Start', null, false],
      [2, [1], 'Num', null, false]
    ]);
  });

  it('applies the engine ranking payload: best rank wins, picked positions are marked', () => {
    const ranks = { rank1: [[[0, 1]]], rank2: [[[1]]], picked: [[0, 1]], noprune: false };
    const infos = holeInfos(layoutTree(tree).nodes, ranks);
    expect(infos.map((h) => [h.rank, h.picked])).toEqual([
      [1, true],
      [2, false]
    ]);
  });

  it('treats a hole in a multi-hole set as ranked and unlisted holes as rank 3', () => {
    const ranks = { rank1: [[[0, 1], [1]]], rank2: [], picked: [[0, 1], [1]], noprune: false };
    expect(holeInfos(layoutTree(tree).nodes, ranks).map((h) => h.rank)).toEqual([1, 1]);
    const none = { rank1: [], rank2: [], picked: [[1]], noprune: true };
    expect(holeInfos(layoutTree(tree).nodes, none).map((h) => h.rank)).toEqual([3, 3]);
  });
});

describe('callSyntax', () => {
  it('writes operators as calls and numbers holes with subscripts', () => {
    expect(callSyntax(tree)).toBe('bvadd(bvmul(x, □₁), □₂)');
  });
  it('writes a lone leaf as itself and a long hole index with every digit', () => {
    expect(callSyntax(parseProgram('x'))).toBe('x');
    const wide = parseProgram(`(f ${Array.from({ length: 11 }, () => '□:S').join(' ')})`);
    expect(callSyntax(wide).endsWith('□₁₁)')).toBe(true);
  });
});

import { buildView } from './holes';

describe('buildView', () => {
  it('parses, lays out and numbers holes in one step', () => {
    const v = buildView('(bvadd □:S x)', { rank1: [[[0]]], rank2: [], picked: [[0]], noprune: false });
    expect(v.error).toBeNull();
    expect(v.layout?.nodes).toHaveLength(3);
    expect(v.holes.map((h) => [h.index, h.rank, h.picked])).toEqual([[1, 1, true]]);
    expect(v.call).toBe('bvadd(□₁, x)');
  });
  it('reports unreadable text and handles no program', () => {
    expect(buildView('(broken', null).error).toMatch(/\)|end/);
    const none = buildView(null, null);
    expect(none.layout).toBeNull();
    expect(none.error).toBeNull();
    expect(none.holes).toEqual([]);
  });
});

import { callSegments } from './holes';

describe('callSegments', () => {
  it('splits a program into coloured pieces that join back to the call text', () => {
    const segs = callSegments(tree);
    expect(segs.map((s) => s.text).join('')).toBe(callSyntax(tree));
    expect(segs.filter((s) => s.kind === 'op').map((s) => s.text)).toEqual(['bvadd', 'bvmul']);
    expect(segs.filter((s) => s.kind === 'hole').map((s) => s.text)).toEqual(['□₁', '□₂']);
    expect(segs.filter((s) => s.kind === 'leaf').map((s) => s.text)).toEqual(['x']);
  });
});
