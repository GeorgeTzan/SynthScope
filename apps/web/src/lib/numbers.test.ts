import { describe, expect, it } from 'vitest';
import { buildNumbersProblem, parseConstants, parseInteger, parseRows } from './numbers';
import { parseProblem } from './problem';

describe('parseRows', () => {
  it('reads arrow rows, multi-input rows and bare rows', () => {
    expect(parseRows('2 -> 4\n3, 4 -> 12\n5 25')).toEqual([[2n, 4n], [3n, 4n, 12n], [5n, 25n]]);
  });
  it('accepts ; separators, hex, binary, negatives and comments', () => {
    expect(parseRows('# squares\n0x2 → 4; -1 -> 0b1')).toEqual([[2n, 4n], [-1n, 1n]]);
  });
  it('names the bad example', () => {
    expect(() => parseRows('2 -> 4\n3 -> x')).toThrow(/Example 2/);
    expect(() => parseRows('1 -> 2 -> 3')).toThrow(/more than one arrow/);
    expect(() => parseRows('1 -> 2 3')).toThrow(/exactly one output/);
  });
  it('parses integers and constants strictly', () => {
    expect(parseInteger('-7')).toBe(-7n);
    expect(() => parseInteger('1.5')).toThrow();
    expect(parseConstants('1, 2 3')).toEqual([1n, 2n, 3n]);
  });
});

describe('buildNumbersProblem', () => {
  const base = { width: 8, rows: [[2n, 4n], [3n, 9n], [4n, 16n]], ops: ['bvadd', 'bvmul'], constants: [1n] };
  it('produces SyGuS text that the dashboard parser reads back', () => {
    const p = parseProblem(buildNumbersProblem(base));
    expect(p?.domain).toBe('bitvector');
    expect(p?.examples).toHaveLength(3);
    expect(p?.examples[1]).toEqual({ inputs: ['#b00000011'], output: '#b00001001' });
    expect(p?.grammar.operators.map((o) => o.name)).toEqual(['bvadd', 'bvmul']);
  });
  it('wraps negative numbers as two\'s complement', () => {
    expect(buildNumbersProblem({ ...base, rows: [[-1n, 1n]] })).toContain('#b11111111');
  });
  it('rejects unusable specs with a readable message', () => {
    expect(() => buildNumbersProblem({ ...base, rows: [] })).toThrow(/at least one example/);
    expect(() => buildNumbersProblem({ ...base, ops: [] })).toThrow(/at least one operation/);
    expect(() => buildNumbersProblem({ ...base, ops: ['evil'] })).toThrow(/Unknown operation/);
    expect(() => buildNumbersProblem({ ...base, width: 7 })).toThrow(/Width/);
    expect(() => buildNumbersProblem({ ...base, rows: [[300n, 1n]] })).toThrow(/does not fit/);
    expect(() => buildNumbersProblem({ ...base, rows: [[1n, 2n], [1n, 3n]] })).toThrow(/Conflicting/);
    expect(() => buildNumbersProblem({ ...base, rows: [[1n, 2n], [1n, 2n, 3n]] })).toThrow(/same number/);
  });
});
