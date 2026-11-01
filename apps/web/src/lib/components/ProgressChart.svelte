<script lang="ts">
  import type { Point } from '../state/run.svelte';

  let { series }: { series: Point[] } = $props();

  const W = 480;
  const H = 160;
  let pts = $derived.by(() => {
    const maxX = Math.max(1, ...series.map((p) => p.seq));
    const maxY = Math.max(1, ...series.map((p) => Math.max(p.explored, p.pruned)));
    const line = (f: (p: Point) => number) =>
      series.map((p) => `${((p.seq / maxX) * W).toFixed(1)},${(H - (f(p) / maxY) * H).toFixed(1)}`).join(' ');
    return { explored: line((p) => p.explored), pruned: line((p) => p.pruned) };
  });
</script>

<section aria-label="Search progress">
  <h3>Search progress: expanded vs discarded</h3>
  {#if series.length === 0}
    <p class="muted">No data yet.</p>
  {:else}
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Candidates expanded and discarded over events">
      <polyline points={pts.explored} fill="none" stroke="var(--teal)" stroke-width="2" />
      <polyline points={pts.pruned} fill="none" stroke="var(--violet)" stroke-width="2" />
    </svg>
    <p class="legend"><span style="color: var(--teal)">expanded</span> <span style="color: var(--violet)">discarded</span> (x: event number)</p>
  {/if}
</section>

<style>
  h3 { margin: 0 0 0.5rem; font-size: 0.95rem; }
  svg { width: 100%; height: auto; background: var(--panel-2); border-radius: 0.4rem; }
  .muted, .legend { color: var(--muted); font-size: 0.8rem; }
</style>
