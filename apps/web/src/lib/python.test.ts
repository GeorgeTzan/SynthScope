import { describe, expect, it } from 'vitest';
import { formatValue } from './format';
import { toPythonExpression, toPythonFunction } from './python';

describe('toPythonExpression (bitvector)', () => {
  it('writes ring operations infix and masks once at the end', () => {
    expect(toPythonExpression('(bvmul x x)', 'bv', 8)).toBe('(x * x) & 255');
    expect(toPythonExpression('(bvadd (bvmul x x) 1)', 'bv', 4)).toBe('((x * x) + 1) & 15');
  });
  it('needs no mask when the value cannot leave the width', () => {
    expect(toPythonExpression('(bvand x (bvadd x 1))', 'bv', 4)).toBe('x & (x + 1)');
  });
  it('reduces operands of non-ring operations', () => {
    expect(toPythonExpression('(bvlshr (bvadd x 1) 1)', 'bv', 4)).toBe('((x + 1) & 15) >> 1');
  });
  it('keeps SMT-LIB-specific operations as named calls', () => {
    expect(toPythonExpression('(bvudiv x 3)', 'bv', 8)).toBe('bvudiv(x, 3)');
  });
  it('turns constants into decimals and ite into a conditional', () => {
    expect(toPythonExpression('(ite (= x #x0a) #b0001 x)', 'bv', 8)).toBe('1 if x == 10 else x');
  });
});

describe('toPythonExpression (string)', () => {
  it('concatenates, slices and quotes', () => {
    expect(toPythonExpression('(str.++ (str.at first 0) ".")', 'str', null)).toBe('first[0:1] + "."');
    expect(toPythonExpression('(str.len x)', 'str', null)).toBe('len(x)');
    expect(toPythonExpression('(str.prefixof "a" x)', 'str', null)).toBe('x.startswith("a")');
  });
  it('keeps a call when the slice index is not a literal', () => {
    expect(toPythonExpression('(str.at x (str.len y))', 'str', null)).toBe('str_at(x, len(y))');
  });
});

describe('toPythonFunction and formatValue', () => {
  it('wraps the expression in a def', () => {
    expect(toPythonFunction('(bvmul x x)', 'f', ['x'], 'bv', 8)).toBe('def f(x):\n    return (x * x) & 255');
  });
  it('adds exact helpers for operations Python does not share', () => {
    const code = toPythonFunction('(str.at s (str.len s))', 'f', ['s'], 'str', null);
    expect(code).toContain('def str_at(s, i):');
    expect(code.endsWith('def f(s):\n    return str_at(s, len(s))')).toBe(true);
    expect(toPythonFunction('(bvudiv x 3)', 'f', ['x'], 'bv', 8)).toContain('else 255');
  });
  it('degrades to a comment on unparseable text', () => {
    expect(toPythonFunction('(bvadd', 'f', ['x'], 'bv', 8)).toMatch(/^# could not translate/);
  });
  it('shows bit patterns as decimal', () => {
    expect(formatValue('#b1011')).toEqual({ main: '11', raw: '#b1011' });
    expect(formatValue('#x0f')).toEqual({ main: '15', raw: '#x0f' });
    expect(formatValue('"J.K"')).toEqual({ main: '"J.K"', raw: null });
  });
});
