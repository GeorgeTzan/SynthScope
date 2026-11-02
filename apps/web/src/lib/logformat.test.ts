import { describe, expect, it } from 'vitest';
import { describeEvent } from './logformat';
import type { SynthEvent } from './types';

const ev = (kind: string, payload: Record<string, unknown> = {}): SynthEvent => ({ schema_version: 1, run_id: 'r', seq: 0, kind, payload, t: 0.5 });
const ctx = { depthOf: (id: unknown) => (id === 7 ? 2 : 0) };

describe('describeEvent', () => {
  it('describes an expansion with depth and call-style program text', () => {
    const d = describeEvent(ev('candidate_expanded', { program: '(bvadd □:S x)', id: 7 }), ctx);
    expect(d.title).toBe('Candidate expansion (depth = 2)');
    expect(d.detail).toBe('bvadd(□₁, x)');
    expect(d.icon).toBe('plus');
  });

  it('falls back to the raw text when a program cannot be read', () => {
    expect(describeEvent(ev('candidate_expanded', { program: '(broken' }), ctx).detail).toBe('(broken');
  });

  it('describes pruning by reason', () => {
    const c = describeEvent(ev('pruned', { count: 8, reason: 'component' }), ctx);
    expect(c.title).toBe('Prune (components)');
    expect(c.detail).toBe('Discard 8 components that contradict the examples');
    expect(c.tone).toBe('bad');
    expect(describeEvent(ev('pruned', { count: 1, reason: 'component' }), ctx).detail).toBe('Discard 1 component that contradicts the examples');
    expect(describeEvent(ev('pruned', { reason: 'infeasible', program: '(f □:S)' }), ctx).title).toBe('Prune (infeasible)');
  });

  it('describes analysis, ranking and filling', () => {
    expect(describeEvent(ev('analysis', { infeasible: true, nodes: [{}, {}, {}] }), ctx).detail).toBe('3 nodes, empty abstract state (⊥)');
    expect(describeEvent(ev('analysis', { infeasible: false, nodes: [{}] }), ctx).detail).toBe('1 node, feasible');
    const r = describeEvent(ev('hole_ranked', { rank1: [[[0]], [[1]]], rank2: [], picked: [[0]], noprune: false }), ctx);
    expect(r.detail).toBe('picked 1 hole · 2 rank-1 sets, 0 rank-2 sets');
    expect(describeEvent(ev('hole_ranked', { rank1: [], rank2: [], picked: [[0]], noprune: true }), ctx).detail).toContain('no pruning possible');
    expect(describeEvent(ev('hole_filled', { positions: [[0, 1], []] }), ctx).detail).toBe('at 0.1, root');
  });

  it('marks the solution and the end of the run', () => {
    const s = describeEvent(ev('solution_found', { program: '(bvadd x 1)' }), ctx);
    expect([s.title, s.detail, s.tone]).toEqual(['Solution found', 'bvadd(x, 1)', 'good']);
    const f = describeEvent(ev('run_finished', { status: 'timeout', nodes: 99 }), ctx);
    expect([f.title, f.detail]).toEqual(['Run finished: timeout', '99 nodes expanded']);
  });

  it('shows unknown kinds instead of failing', () => {
    expect(describeEvent(ev('future_thing'), ctx).title).toBe('future_thing');
  });
});

describe('verification events', () => {
  const ctx = { depthOf: () => 0 };
  const ev = (kind: string, payload: Record<string, unknown>) => ({ schema_version: 1, run_id: 'r', seq: 0, kind, payload });
  it('explains a counterexample and a verified result', () => {
    const cex = describeEvent(ev('counterexample', { program: '(bvnot x)', inputs: { x: 3 } }), ctx);
    expect(cex.title).toBe('Counterexample found');
    expect(cex.detail).toContain('x = 3');
    expect(describeEvent(ev('verified', { verified: true }), ctx).tone).toBe('good');
    expect(describeEvent(ev('verified', { verified: false }), ctx).title).toBe('Not verified');
  });
  it('summarises the evaluation event', () => {
    expect(describeEvent(ev('evaluation', { examples: [{}, {}] }), ctx).detail).toBe('2 examples, value at every node');
  });
});
