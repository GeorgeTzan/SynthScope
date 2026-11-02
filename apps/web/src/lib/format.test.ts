import { describe, expect, it } from 'vitest';
import { formatElapsed, formatStamp, formatTick, niceTicks } from './format';

describe('formatStamp', () => {
  it('writes minutes, seconds and milliseconds', () => {
    expect(formatStamp(0)).toBe('00:00.000');
    expect(formatStamp(0.177)).toBe('00:00.177');
    expect(formatStamp(75.5)).toBe('01:15.500');
  });
});

describe('formatElapsed', () => {
  it('uses milliseconds below a second and seconds above', () => {
    expect(formatElapsed(0.177)).toBe('177 ms');
    expect(formatElapsed(1.234)).toBe('1.23 s');
  });
});

describe('niceTicks', () => {
  it('rounds the axis to friendly steps and covers the maximum', () => {
    expect(niceTicks(1248)).toEqual([0, 250, 500, 750, 1000, 1250]);
    expect(niceTicks(7)).toEqual([0, 2, 4, 6, 8]);
  });
  it('never returns an empty or degenerate axis', () => {
    expect(niceTicks(0)).toEqual([0, 1]);
    const t = niceTicks(0.18);
    expect(t[0]).toBe(0);
    expect(t.at(-1)).toBeGreaterThanOrEqual(0.18);
  });
  it('formats ticks with as many decimals as the step needs', () => {
    expect(formatTick(250, 250)).toBe('250');
    expect(formatTick(0.04, 0.02)).toBe('0.04');
    expect(formatTick(1500, 500)).toBe('1,500');
  });
});
