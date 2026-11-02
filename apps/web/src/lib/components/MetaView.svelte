<script lang="ts">
  import type { HoleInfo } from '../holes';
  import type { HoleRanks } from '../types';

  let { ranks, holes }: { ranks: HoleRanks | null; holes: HoleInfo[] } = $props();

  const SUB = '₀₁₂₃₄₅₆₇₈₉';
  const name = (path: number[]) => {
    const h = holes.find((x) => x.path.join('.') === path.join('.'));
    return h ? `□${[...String(h.index)].map((d) => SUB[Number(d)]).join('')}` : `at ${path.join('.') || 'root'}`;
  };
  const setText = (s: number[][]) => s.map(name).join(' + ');
</script>

<div class="wrap">
  <p class="lead">
    Before filling a hole, the meta analysis asks which holes could let the pruner reject the candidate soonest.
    A hole in <b>Rank 1</b> may prune the whole candidate on its own; <b>Rank 2</b> holes may prune once other holes are filled;
    otherwise the engine picks a hole at random and skips the pruning analysis.
  </p>
  {#if !ranks}
    <p class="empty">No ranking yet. The engine ranks the holes of each expanded candidate.</p>
  {:else}
    <div class="grid">
      <section><h3>Rank 1 <span>({ranks.rank1.length})</span></h3>
        {#if ranks.rank1.length}<ul>{#each ranks.rank1 as s, i (i)}<li class="mono">{setText(s)}</li>{/each}</ul>{:else}<p class="dim">none</p>{/if}
      </section>
      <section><h3>Rank 2 <span>({ranks.rank2.length})</span></h3>
        {#if ranks.rank2.length}<ul>{#each ranks.rank2 as s, i (i)}<li class="mono">{setText(s)}</li>{/each}</ul>{:else}<p class="dim">none</p>{/if}
      </section>
      <section class="picked"><h3>Picked</h3>
        <p class="mono">{ranks.picked.length ? setText(ranks.picked) : '–'}</p>
        {#if ranks.noprune}<p class="dim">No pruning possible: analysis skipped for this candidate.</p>{/if}
      </section>
    </div>
  {/if}
</div>

<style>
  .wrap { padding: 1.1rem; overflow: auto; flex: 1; min-height: 22rem; }
  .lead { color: var(--muted); font-size: 0.85rem; line-height: 1.65; max-width: 62ch; margin-bottom: 1.2rem; }
  b { color: var(--text); font-weight: 600; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(13rem, 1fr)); gap: 0.9rem; }
  section { border: 1px solid var(--line); background: var(--panel-2); border-radius: 12px; padding: 0.8rem 0.9rem; }
  section.picked { border-color: rgba(139, 108, 255, 0.5); background: var(--violet-soft); }
  h3 { font-size: 0.9rem; margin-bottom: 0.5rem; }
  h3 span { color: var(--muted); font-weight: 400; }
  ul { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.3rem; max-height: 12rem; overflow: auto; }
  li, p.mono { font-size: 0.85rem; color: #d9c8ff; }
  .dim, .empty { color: var(--muted); font-size: 0.82rem; }
</style>
