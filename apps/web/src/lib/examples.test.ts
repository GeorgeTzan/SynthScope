import { describe, expect, it } from 'vitest';
import { EXAMPLES } from './examples';
import { parseProblem } from './problem';

describe('built-in examples', () => {
  it('have unique ids and parse', () => {
    expect(new Set(EXAMPLES.map((e) => e.id)).size).toBe(EXAMPLES.length);
    for (const e of EXAMPLES) {
      const p = parseProblem(e.text);
      expect(p, e.id).not.toBeNull();
      expect(p?.domain, e.id).toBe(e.domain);
      expect(p?.examples.length, e.id).toBeGreaterThan(0);
    }
  });
  it('cover both domains', () => {
    expect(EXAMPLES.some((e) => e.domain === 'bitvector')).toBe(true);
    expect(EXAMPLES.some((e) => e.domain === 'string')).toBe(true);
  });
});
