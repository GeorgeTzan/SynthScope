<script lang="ts">
  import type { AnalysisPayload } from '../types';

  let { analysis }: { analysis: AnalysisPayload | null } = $props();
</script>

<div class="wrap">
  {#if !analysis}
    <p class="empty">No analysis yet. Each expanded candidate is analysed forward and backward against the first example.</p>
  {:else}
    <p class="lead">
      Abstract value of every node for <span class="mono">{Object.entries(analysis.inputs).map(([k, v]) => `${k} = ${v}`).join(', ')}</span> with expected output
      <span class="mono">{analysis.output}</span>.
      {#if analysis.infeasible}<strong class="bad">One node is empty (⊥), so the engine discards this candidate.</strong>{/if}
    </p>
    <table>
      <thead><tr><th>Position</th><th>Node</th><th>Abstract value</th></tr></thead>
      <tbody>
        {#each analysis.nodes as n (n.path.join('.') || 'root')}
          <tr><td class="mono dim">{n.path.length ? n.path.join('.') : 'root'}</td><td class="mono">{n.label}</td><td class="mono val">{n.state}</td></tr>
        {/each}
      </tbody>
    </table>
  {/if}
</div>

<style>
  .wrap { padding: 1rem; overflow: auto; flex: 1; min-height: 22rem; }
  .lead { color: var(--muted); font-size: 0.85rem; margin-bottom: 0.9rem; line-height: 1.6; }
  .bad { color: var(--rose); }
  table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
  th { text-align: left; color: var(--muted); font-weight: 500; padding: 0.45rem 0.7rem; border-bottom: 1px solid var(--line); }
  td { padding: 0.4rem 0.7rem; border-bottom: 1px solid rgba(255, 255, 255, 0.04); }
  .dim { color: var(--dim); }
  .val { color: var(--violet-2); }
  .empty { color: var(--muted); }
</style>
