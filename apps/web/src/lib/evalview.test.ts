import { describe, expect, it } from 'vitest';
import { describeInputs, formatNodeValue, matches } from './evalview';

describe('evalview', () => {
  it('formats numbers, strings, missing values', () => {
    expect(formatNodeValue(9)).toBe('9');
    expect(formatNodeValue('J')).toBe('"J"');
    expect(formatNodeValue('abcdefghijklmnopqrstuvwxyz')).toBe('"abcdefghijklm…"');
    expect(formatNodeValue(null)).toBe('?');
  });
  it('describes inputs and compares the root with the expected output', () => {
    const row = { inputs: { x: 3, s: 'a' }, expected: 9, values: { '': 9 } };
    expect(describeInputs(row)).toBe('x = 3, s = "a"');
    expect(matches(row)).toBe(true);
    expect(matches({ ...row, expected: 8 })).toBe(false);
  });
});
