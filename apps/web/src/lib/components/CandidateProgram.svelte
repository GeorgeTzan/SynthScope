<script lang="ts">
  import { buildView, callSegments } from '../holes';
  import Icon from './Icon.svelte';
  import Panel from './Panel.svelte';

  let { program }: { program: string | null } = $props();

  let view = $derived(buildView(program, null));
  let segments = $derived(view.tree ? callSegments(view.tree) : []);
  let copied = $state(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(view.call);
      copied = true;
      setTimeout(() => (copied = false), 1500);
    } catch {
      /* clipboard blocked */
    }
  }
</script>

<Panel title="Candidate Program" icon="code">
  {#snippet right()}
    {#if view.call}<button aria-label="Copy candidate" onclick={copy}>{#if copied}<Icon name="check" size={16} />{:else}<Icon name="copy" size={16} />{/if}</button>{/if}
  {/snippet}
  {#if view.error}
    <p class="empty" role="alert">Cannot read program: {view.error}</p>
  {:else if view.tree}
    <div class="code"><span class="ln">1</span><code>{#each segments as s, i (i)}<span class={s.kind}>{s.text}</span>{/each}</code></div>
    <div class="chips">
      <span class="chip" class:done={view.holes.length === 0}>{view.holes.length === 0 ? 'Complete program' : 'Partial program'}</span>
      {#if view.holes.length}<span class="chip plain">{view.holes.length} {view.holes.length === 1 ? 'hole' : 'holes'}</span>{/if}
    </div>
  {:else}
    <p class="empty">The candidate being expanded shows up here.</p>
  {/if}
</Panel>

<style>
  .code { display: flex; gap: 1rem; align-items: baseline; background: var(--panel-2); border: 1px solid var(--line); border-radius: 10px; padding: 0.8rem 0.9rem; overflow-x: auto; }
  .ln { color: var(--dim); font-family: var(--mono); font-size: 0.8rem; }
  code { font-size: 0.95rem; white-space: nowrap; }
  .op { color: var(--violet-2); }
  .hole { color: #ff9be0; }
  .leaf { color: var(--teal); }
  .punct { color: var(--muted); }
  .chips { display: flex; gap: 0.5rem; margin-top: 0.7rem; }
  .chip { font-size: 0.78rem; padding: 0.15rem 0.7rem; border-radius: 8px; background: var(--violet-soft); color: var(--violet-2); border: 1px solid rgba(139, 108, 255, 0.35); }
  .chip.done { background: var(--teal-soft); color: var(--teal); border-color: rgba(53, 224, 198, 0.35); }
  .chip.plain { background: rgba(255, 255, 255, 0.05); color: var(--text); border-color: var(--line-2); }
  button { background: transparent; border: 0; color: var(--muted); cursor: pointer; padding: 0.25rem; border-radius: 7px; display: grid; }
  button:hover { color: var(--text); }
  .empty { color: var(--muted); font-size: 0.85rem; }
</style>
