<script lang="ts">
  import { formatTick, niceTicks } from '../format';
  import type { Point } from '../state/run.svelte';
  import Panel from './Panel.svelte';

  let { series }: { series: Point[] } = $props();

  const W = 520, H = 262, L = 58, R = 16, T = 12, B = 44;
  const nf = new Intl.NumberFormat('en-US');

  let byTime = $derived(series.some((p) => p.t > 0));
  let xs = $derived(series.map((p) => (byTime ? p.t : p.seq)));
  let xTicks = $derived(niceTicks(Math.max(0, ...xs), 9));
  let yTicks = $derived(niceTicks(Math.max(0, ...series.map((p) => Math.max(p.explored, p.pruned))), 5));
  let xMax = $derived(xTicks[xTicks.length - 1]);
  let yMax = $derived(yTicks[yTicks.length - 1]);
  const px = (x: number, max: number) => L + (x / max) * (W - L - R);
  const py = (y: number, max: number) => H - B - (y / max) * (H - T - B);

  function path(f: (p: Point) => number, close = false): string {
    if (series.length === 0) return '';
    const pts = series.map((p, i) => `${px(xs[i], xMax).toFixed(1)},${py(f(p), yMax).toFixed(1)}`);
    const line = `M${pts.join(' L')}`;
    return close ? `${line} L${px(xs[xs.length - 1], xMax).toFixed(1)},${py(0, yMax)} L${px(xs[0], xMax).toFixed(1)},${py(0, yMax)} Z` : line;
  }

  let last = $derived(series.at(-1));
</script>

<Panel title="Search Progress: Explored vs. Pruned Candidates" icon="activity">
  {#if series.length === 0}
    <p class="empty">No data yet. The chart fills in as the engine reports progress.</p>
  {:else}
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Candidates explored and pruned over time">
      <defs>
        <linearGradient id="a-teal" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#35e0c6" stop-opacity="0.32" /><stop offset="1" stop-color="#35e0c6" stop-opacity="0" /></linearGradient>
        <linearGradient id="a-violet" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#8b6cff" stop-opacity="0.4" /><stop offset="1" stop-color="#8b6cff" stop-opacity="0" /></linearGradient>
      </defs>
      {#each yTicks as t (t)}
        <line x1={L} x2={W - R} y1={py(t, yMax)} y2={py(t, yMax)} class="grid" />
        <text x={L - 10} y={py(t, yMax) + 4} text-anchor="end" class="tick">{formatTick(t, yTicks[1] ?? 1)}</text>
      {/each}
      {#each xTicks as t (t)}
        <text x={px(t, xMax)} y={H - B + 18} text-anchor="middle" class="tick">{formatTick(t, xTicks[1] ?? 1)}</text>
      {/each}
      <path d={path((p) => p.explored, true)} fill="url(#a-teal)" />
      <path d={path((p) => p.pruned, true)} fill="url(#a-violet)" />
      <path d={path((p) => p.explored)} class="line teal" />
      <path d={path((p) => p.pruned)} class="line violet" />
      {#if last}
        <circle cx={px(xs[xs.length - 1], xMax)} cy={py(last.explored, yMax)} r="4" class="dot teal" />
        <circle cx={px(xs[xs.length - 1], xMax)} cy={py(last.pruned, yMax)} r="4" class="dot violet" />
      {/if}
      <text x={(L + W - R) / 2} y={H - 6} text-anchor="middle" class="axis">{byTime ? 'Time (s)' : 'Event number'}</text>
      <text x="14" y={(T + H - B) / 2} text-anchor="middle" class="axis" transform={`rotate(-90 14 ${(T + H - B) / 2})`}># Candidates</text>
      <g transform={`translate(${L + 12} ${T + 4})`}>
        <rect width="158" height="52" rx="9" class="legend" />
        <circle cx="14" cy="17" r="4" class="dot teal" /><text x="27" y="22" class="lt">Explored ({nf.format(last?.explored ?? 0)})</text>
        <circle cx="14" cy="36" r="4" class="dot violet" /><text x="27" y="41" class="lt">Pruned ({nf.format(last?.pruned ?? 0)})</text>
      </g>
    </svg>
  {/if}
</Panel>

<style>
  svg { width: 100%; height: auto; display: block; }
  .grid { stroke: rgba(255, 255, 255, 0.06); }
  .tick { fill: var(--muted); font-size: 12px; font-family: var(--sans); }
  .axis { fill: var(--muted); font-size: 12.5px; }
  .line { fill: none; stroke-width: 2.2; stroke-linejoin: round; stroke-linecap: round; }
  .line.teal { stroke: #35e0c6; }
  .line.violet { stroke: #8b6cff; }
  .dot.teal { fill: #35e0c6; stroke: #0b0e1c; stroke-width: 1.5; }
  .dot.violet { fill: #8b6cff; stroke: #0b0e1c; stroke-width: 1.5; }
  .legend { fill: rgba(13, 16, 36, 0.92); stroke: var(--line-2); }
  .lt { fill: var(--text); font-size: 12.5px; }
  .empty { color: var(--muted); font-size: 0.85rem; padding: 1.5rem 0.5rem; }
</style>
