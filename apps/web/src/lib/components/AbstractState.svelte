<script lang="ts">
  import type { AnalysisPayload } from '../types';
  import Icon from './Icon.svelte';
  import Panel from './Panel.svelte';

  let { analysis, limit = 6 }: { analysis: AnalysisPayload | null; limit?: number } = $props();

  let example = $derived(
    analysis ? `${Object.entries(analysis.inputs).map(([k, v]) => `${k} = ${v}`).join(', ')} → ${analysis.output}` : ''
  );
</script>

<Panel title="Abstract Interpretation State" icon="layers">
  {#snippet right()}
    <span class="info" title="Abstract value of each node of the current candidate for the first example, after the forward and backward passes"><Icon name="info" size={16} /></span>
  {/snippet}
  {#if analysis}
    <p class="ex mono">example: {example}{#if analysis.infeasible}<span class="bad"> · ⊥ infeasible</span>{/if}</p>
    <table>
      <tbody>
        {#each analysis.nodes.slice(0, limit) as n (n.path.join('.') || 'root')}
          <tr>
            <th scope="row" class="mono" style:padding-left={`${0.7 + Math.min(n.path.length, 5) * 0.7}rem`}>{n.label}</th>
            <td class="mono">{n.state}</td>
          </tr>
        {/each}
      </tbody>
    </table>
    {#if analysis.nodes.length > limit}<p class="more">+ {analysis.nodes.length - limit} more nodes in the Analysis tab</p>{/if}
  {:else}
    <p class="empty">The abstract value of each node appears here after the first analysis.</p>
  {/if}
</Panel>

<style>
  .info { color: var(--muted); display: grid; cursor: help; }
  .ex { color: var(--muted); font-size: 0.76rem; margin-bottom: 0.5rem; }
  .bad { color: var(--rose); }
  table { width: 100%; border-collapse: collapse; background: var(--panel-2); border: 1px solid var(--line); border-radius: 10px; overflow: hidden; font-size: 0.83rem; }
  th, td { padding: 0.45rem 0.7rem; border-bottom: 1px solid rgba(255, 255, 255, 0.04); text-align: left; font-weight: 400; }
  th { color: var(--text); width: 45%; white-space: nowrap; }
  td { color: var(--violet-2); overflow-wrap: anywhere; }
  tr:last-child th, tr:last-child td { border-bottom: 0; }
  .more { color: var(--dim); font-size: 0.74rem; margin-top: 0.4rem; }
  .empty { color: var(--muted); font-size: 0.85rem; }
</style>
