import { describe, expect, it } from 'vitest';
import { opName } from './opnames';

describe('opName', () => {
  it('names common operators in plain words', () => {
    expect(opName('bvmul')).toEqual({ name: 'multiply', symbol: '×' });
    expect(opName('str.++').name).toBe('join text');
    expect(opName('ite').name).toBe('if / else');
  });
  it('falls back to the raw label for unknown operators', () => {
    expect(opName('mystery')).toEqual({ name: 'mystery', symbol: 'mystery' });
  });
});
