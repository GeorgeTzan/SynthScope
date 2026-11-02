<script lang="ts">
  import { formatElapsed } from '../format';
  import Icon, { type IconName } from './Icon.svelte';
  import Panel from './Panel.svelte';

  let { explored, pruned, elapsed, maxDepth, nodes }: { explored: number; pruned: number; elapsed: number; maxDepth: number; nodes: number | null } = $props();

  const nf = new Intl.NumberFormat('en-US');
  let share = $derived(explored + pruned > 0 ? ((pruned / (explored + pruned)) * 100).toFixed(1) : '0.0');
  let rows = $derived<{ icon: IconName; label: string; value: string; hint?: string }[]>([
    { icon: 'layers', label: 'Candidates explored', value: nf.format(explored) },
    { icon: 'trash', label: 'Candidates pruned', value: `${nf.format(pruned)} (${share}%)`, hint: 'share of all candidates and components the pruner looked at' },
    { icon: 'clock', label: 'Time elapsed', value: formatElapsed(elapsed) },
    { icon: 'tree', label: 'Search depth (max)', value: String(maxDepth) },
    ...(nodes === null ? [] : [{ icon: 'cube' as IconName, label: 'Nodes (engine total)', value: nf.format(nodes) }])
  ]);
</script>

<Panel title="Statistics" icon="chart">
  <dl>
    {#each rows as r (r.label)}
      <div title={r.hint}>
        <dt><Icon name={r.icon} size={16} /> {r.label}</dt>
        <dd class="mono">{r.value}</dd>
      </div>
    {/each}
  </dl>
</Panel>

<style>
  dl { margin: 0; display: grid; border: 1px solid var(--line); border-radius: 10px; overflow: hidden; background: var(--panel-2); }
  div { display: flex; justify-content: space-between; align-items: center; padding: 0.55rem 0.8rem; border-bottom: 1px solid rgba(255, 255, 255, 0.04); }
  div:last-child { border-bottom: 0; }
  dt { display: flex; align-items: center; gap: 0.6rem; color: var(--muted); font-size: 0.86rem; }
  dd { margin: 0; font-size: 0.88rem; }
</style>
