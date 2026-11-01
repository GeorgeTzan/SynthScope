<script lang="ts">
  import type { HoleRanks } from '../types';

  let { ranks }: { ranks: HoleRanks | null } = $props();

  const show = (set: number[][]) => '{' + set.map((p) => p.join('.') || 'root').join(', ') + '}';
</script>

<section aria-label="Hole ranking">
  <h3>Holes</h3>
  {#if !ranks}
    <p class="muted">No ranking yet.</p>
  {:else}
    {#if ranks.rank1.length}
      <p><strong>Rank 1</strong> (may prune the whole candidate)</p>
      <ul>{#each ranks.rank1 as s}<li>{show(s)}</li>{/each}</ul>
    {/if}
    {#if ranks.rank2.length}
      <p><strong>Rank 2</strong> (may prune components of other holes)</p>
      <ul>{#each ranks.rank2 as s}<li>{show(s)}</li>{/each}</ul>
    {/if}
    {#if ranks.noprune}
      <p class="muted">No pruning possible: analysis skipped for this step.</p>
    {/if}
    <p class="picked"><strong>Picked</strong> <code>{ranks.picked.map((p) => p.join('.') || 'root').join(' + ')}</code></p>
  {/if}
</section>

<style>
  h3 { margin: 0 0 0.5rem; font-size: 0.95rem; }
  ul { margin: 0 0 0.5rem; padding-left: 1.1rem; font-family: var(--mono); }
  .muted { color: var(--muted); }
  .picked code { color: var(--violet); }
</style>
