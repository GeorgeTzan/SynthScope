<script lang="ts">
  import type { SynthEvent } from '../types';

  let { entries, limit = 200 }: { entries: SynthEvent[]; limit?: number } = $props();

  let shown = $derived(entries.slice(-limit));

  function text(e: SynthEvent): string {
    const p = e.payload;
    if (typeof p.program === 'string') return p.program;
    if (e.kind === 'pruned') return `discarded ${p.count ?? 1} (${p.reason ?? ''})`;
    if (e.kind === 'run_finished') return `${p.status}, ${p.nodes} nodes`;
    return '';
  }
</script>

<section aria-label="Synthesis log">
  <h3>Synthesis log</h3>
  <ol>
    {#each shown as e (e.seq)}
      <li><span class="seq">{e.seq}</span> <span class="kind">{e.kind}</span> <code>{text(e)}</code></li>
    {/each}
  </ol>
</section>

<style>
  h3 { margin: 0 0 0.5rem; font-size: 0.95rem; }
  ol { list-style: none; margin: 0; padding: 0; max-height: 18rem; overflow: auto; font-size: 0.8rem; }
  li { padding: 0.15rem 0; border-bottom: 1px solid var(--line); }
  .seq { color: var(--muted); margin-right: 0.4rem; }
  .kind { color: var(--accent); margin-right: 0.4rem; }
  code { font-family: var(--mono); color: var(--text); word-break: break-all; }
</style>
