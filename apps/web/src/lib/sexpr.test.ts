import { describe, expect, it } from 'vitest';
import { parseProgram } from './sexpr';

describe('parseProgram', () => {
  it('parses nested operators and holes', () => {
    const t = parseProgram('(bvadd □:S (bvnot x))');
    expect(t.label).toBe('bvadd');
    expect(t.children[0]).toEqual({ label: '□', hole: 'S', children: [] });
    expect(t.children[1].label).toBe('bvnot');
    expect(t.children[1].children[0].label).toBe('x');
  });
  it('parses a bare leaf and a quoted string with spaces', () => {
    expect(parseProgram('x').label).toBe('x');
    expect(parseProgram('(ConCat "J. K" x)').children[0].label).toBe('"J. K"');
  });
  it('rejects malformed text', () => {
    expect(() => parseProgram('(bvadd x')).toThrow();
    expect(() => parseProgram('x y')).toThrow();
    expect(() => parseProgram(')')).toThrow();
    expect(() => parseProgram('')).toThrow();
  });
});
