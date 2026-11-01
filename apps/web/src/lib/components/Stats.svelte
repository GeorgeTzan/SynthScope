<script lang="ts">
  import type { RunStatus } from '../types';

  let {
    explored,
    pruned,
    received,
    nodes,
    status
  }: { explored: number; pruned: number; received: number; nodes: number | null; status: RunStatus } = $props();
</script>

<section aria-label="Statistics">
  <h3>Statistics</h3>
  <dl>
    <dt>Status</dt><dd>{status}</dd>
    <dt>Candidates expanded (shown)</dt><dd>{explored}</dd>
    <dt>Candidates discarded (shown)</dt><dd>{pruned}</dd>
    <dt>Events received</dt><dd>{received}</dd>
    <dt>Nodes (engine total)</dt><dd>{nodes ?? '–'}</dd>
  </dl>
</section>

<style>
  h3 { margin: 0 0 0.5rem; font-size: 0.95rem; }
  dl { display: grid; grid-template-columns: 1fr auto; gap: 0.25rem 1rem; margin: 0; }
  dt { color: var(--muted); }
  dd { margin: 0; font-family: var(--mono); text-align: right; }
</style>
