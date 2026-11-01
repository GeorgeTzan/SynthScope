<script lang="ts">
  import { parseProgram } from '../sexpr';
  import type { Tree } from '../types';

  let { program }: { program: string | null } = $props();

  let parsed = $derived.by((): { tree: Tree | null; error: string | null } => {
    if (!program) return { tree: null, error: null };
    try {
      return { tree: parseProgram(program), error: null };
    } catch (e) {
      return { tree: null, error: e instanceof Error ? e.message : String(e) };
    }
  });
</script>

{#snippet branch(t: Tree)}
  <li>
    {#if t.hole}
      <span class="node hole" role="img" aria-label={`hole ${t.hole}`}>□ <small>{t.hole}</small></span>
    {:else}
      <span class="node" class:leaf={t.children.length === 0}>{t.label}</span>
    {/if}
    {#if t.children.length}
      <ul>
        {#each t.children as c}
          {@render branch(c)}
        {/each}
      </ul>
    {/if}
  </li>
{/snippet}

<section aria-label="Partial program">
  {#if parsed.error}
    <p role="alert">Cannot draw program: {parsed.error}</p>
  {:else if parsed.tree}
    <ul class="tree root">
      {@render branch(parsed.tree)}
    </ul>
  {:else}
    <p class="muted">No candidate yet.</p>
  {/if}
</section>

<style>
  ul { list-style: none; margin: 0; padding-left: 1.4rem; border-left: 1px dashed var(--line); }
  ul.root { border-left: none; padding-left: 0; }
  li { margin: 0.35rem 0; }
  .node { display: inline-block; padding: 0.15rem 0.6rem; border: 1px solid var(--accent); border-radius: 0.5rem; font-family: var(--mono); }
  .leaf { border-color: var(--teal); }
  .hole { border-style: dashed; border-color: var(--violet); color: var(--violet); }
  .muted { color: var(--muted); }
</style>
