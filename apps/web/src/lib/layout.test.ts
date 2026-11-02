import { describe, expect, it } from 'vitest';
import { layoutTree } from './layout';
import { parseProgram } from './sexpr';

describe('layoutTree', () => {
  const tree = parseProgram('(bvadd (bvmul x □:S) □:S)');

  it('gives every node a path, an index of its parent and a position', () => {
    const l = layoutTree(tree);
    expect(l.nodes.map((n) => n.path)).toEqual([[], [0], [0, 0], [0, 1], [1]]);
    expect(l.nodes[0].parent).toBeNull();
    expect(l.nodes[2].parent).toBe(1);
    expect(l.nodes.filter((n) => n.hole !== null)).toHaveLength(2);
  });

  it('puts children below parents, parents centred over their children, siblings apart', () => {
    const l = layoutTree(tree);
    const [root, mul, x, hole1, hole2] = l.nodes;
    expect(mul.y).toBeGreaterThan(root.y);
    expect(x.y).toBeGreaterThan(mul.y);
    expect(x.x).toBeLessThan(hole1.x);
    expect(mul.x).toBeCloseTo((x.x + hole1.x) / 2);
    expect(root.x).toBeCloseTo((mul.x + hole2.x) / 2);
    for (const n of l.nodes) {
      expect(n.x - n.w / 2).toBeGreaterThanOrEqual(0);
      expect(n.x + n.w / 2).toBeLessThanOrEqual(l.width);
      expect(n.y + n.h).toBeLessThanOrEqual(l.height);
    }
  });

  it('never overlaps nodes of the same level', () => {
    const l = layoutTree(parseProgram('(f (g a b) (g c d) (g e f))'));
    const byY = new Map<number, typeof l.nodes>();
    for (const n of l.nodes) byY.set(n.y, [...(byY.get(n.y) ?? []), n]);
    for (const row of byY.values()) {
      const sorted = [...row].sort((a, b) => a.x - b.x);
      for (let i = 1; i < sorted.length; i++) {
        expect(sorted[i].x - sorted[i].w / 2).toBeGreaterThanOrEqual(sorted[i - 1].x + sorted[i - 1].w / 2);
      }
    }
  });

  it('lays out a single node', () => {
    const l = layoutTree(parseProgram('x'));
    expect(l.nodes).toHaveLength(1);
    expect(l.nodes[0].x).toBeCloseTo(l.width / 2);
  });
});
