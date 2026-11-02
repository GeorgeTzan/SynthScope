<script lang="ts">
  import { buildView } from '../holes';
  import type { RunState } from '../state/run.svelte';
  import AnalysisTable from './AnalysisTable.svelte';
  import AstGraph from './AstGraph.svelte';
  import Icon, { type IconName } from './Icon.svelte';
  import MetaView from './MetaView.svelte';
  import SearchTreeView from './SearchTreeView.svelte';

  let { run }: { run: RunState } = $props();

  const tabs: { id: string; label: string; icon: IconName }[] = [
    { id: 'ast', label: 'AST (Partial Program)', icon: 'tree' },
    { id: 'tree', label: 'Search Tree', icon: 'cube' },
    { id: 'analysis', label: 'Analysis', icon: 'search' },
    { id: 'meta', label: 'Meta-analysis', icon: 'zap' }
  ];
  let tab = $state('ast');
  let program = $derived(run.current ?? run.best);
  let holes = $derived(buildView(program, run.ranks).holes);

  function key(e: KeyboardEvent) {
    const i = tabs.findIndex((t) => t.id === tab);
    if (e.key === 'ArrowRight') tab = tabs[(i + 1) % tabs.length].id;
    else if (e.key === 'ArrowLeft') tab = tabs[(i + tabs.length - 1) % tabs.length].id;
  }
</script>

<section class="card center" aria-label="Search views" id="synthesis">
  <div class="tabs" role="tablist" aria-label="Views" tabindex="-1" onkeydown={key}>
    {#each tabs as t (t.id)}
      <button role="tab" id={`tab-${t.id}`} aria-selected={tab === t.id} aria-controls={`panel-${t.id}`} tabindex={tab === t.id ? 0 : -1} class:on={tab === t.id} onclick={() => (tab = t.id)}>
        <Icon name={t.icon} size={16} /> {t.label}
      </button>
    {/each}
  </div>
  <div class="view" role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`}>
    {#if tab === 'ast'}
      <AstGraph {program} ranks={run.ranks} running={run.status === 'running'} />
    {:else if tab === 'tree'}
      <SearchTreeView candidates={run.candidates} />
    {:else if tab === 'analysis'}
      <AnalysisTable analysis={run.analysis} />
    {:else}
      <MetaView ranks={run.ranks} {holes} />
    {/if}
  </div>
</section>

<style>
  .center { display: flex; flex-direction: column; padding: 0.35rem 0.6rem 0.8rem; }
  .tabs { display: flex; gap: 0.2rem; border-bottom: 1px solid var(--line); margin: 0 0.2rem 0.7rem; overflow-x: auto; }
  button { display: flex; align-items: center; gap: 0.5rem; background: transparent; border: 0; border-bottom: 2px solid transparent; color: var(--muted); padding: 0.75rem 1rem; cursor: pointer; white-space: nowrap; margin-bottom: -1px; }
  button:hover { color: var(--text); }
  button.on { color: var(--text); border-bottom-color: var(--violet); background: linear-gradient(180deg, transparent, rgba(139, 108, 255, 0.13)); }
  .view { display: flex; flex-direction: column; flex: 1; min-height: 0; min-width: 0; }
</style>
