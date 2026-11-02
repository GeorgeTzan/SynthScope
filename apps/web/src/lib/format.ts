/** Timestamp for the synthesis log: mm:ss.mmm */
export function formatStamp(seconds: number): string {
  const ms = Math.round(seconds * 1000);
  const m = Math.floor(ms / 60000);
  const s = Math.floor((ms % 60000) / 1000);
  const r = ms % 1000;
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}.${String(r).padStart(3, '0')}`;
}

export function formatElapsed(seconds: number): string {
  return seconds < 1 ? `${Math.round(seconds * 1000)} ms` : `${seconds.toFixed(2)} s`;
}

/** Axis ticks from 0 to a friendly value at or above `max`, in friendly steps (1, 2, 2.5, 5 times a power of ten). */
export function niceTicks(max: number, count = 5): number[] {
  if (!(max > 0)) return [0, 1];
  const raw = max / count;
  const base = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * base).find((s) => s >= raw) ?? 10 * base;
  const n = Math.ceil(max / step - 1e-9);
  return Array.from({ length: n + 1 }, (_, i) => Number((i * step).toFixed(10)));
}

export function formatTick(value: number, step: number): string {
  const decimals = step >= 1 ? 0 : Math.min(6, Math.ceil(-Math.log10(step)));
  return value.toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}
