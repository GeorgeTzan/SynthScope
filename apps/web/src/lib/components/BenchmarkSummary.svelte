<script lang="ts">
  import type { ResultRow } from '../state/app.svelte';
  import Panel from './Panel.svelte';

  let { rows }: { rows: ResultRow[] } = $props();

  const CORPUS: Record<string, string> = { duet: 'String (Duet)', 'bitvec-cond': 'Bitvec-cond', deobfusc: 'Deobfusc', hd44: "Hacker's Delight" };
  const CONFIG: Record<string, string> = { hope_h1: 'HOPE, 1 hole', hope_h3: 'HOPE, up to 3 holes', leftmost: 'Leftmost hole', meta_off: 'Meta analysis off' };

  let groups = $derived.by(() => {
    const by = new Map<string, ResultRow[]>();
    for (const r of rows) by.set(r.corpus, [...(by.get(r.corpus) ?? []), r]);
    return [...by.entries()].map(([corpus, rs]) => ({ corpus, rows: rs, best: Math.max(...rs.map((r) => r.solved)) }));
  });
</script>

<Panel title="Benchmark Summary" icon="table">
  {#if rows.length === 0}
    <p class="empty">No benchmark runs yet. <code>scripts/run_paper_ablations.sh</code> writes them to <code>results/</code>.</p>
  {:else}
    <div class="scroll">
      <table>
        <thead><tr><th>Configuration</th><th class="r">Solved</th><th class="r">Time (s)</th></tr></thead>
        <tbody>
          {#each groups as g (g.corpus)}
            <tr class="grp"><th colspan="3">{CORPUS[g.corpus] ?? g.corpus}</th></tr>
            {#each g.rows as r (r.config)}
              <tr class:best={r.solved === g.best && g.best > 0}>
                <td>{CONFIG[r.config] ?? r.config}</td>
                <td class="r mono">{r.solved} / {r.total} ({r.total ? ((r.solved / r.total) * 100).toFixed(0) : 0}%)</td>
                <td class="r mono">{r.mean_seconds_solved === null ? '–' : r.mean_seconds_solved.toFixed(2)}</td>
              </tr>
            {/each}
          {/each}
        </tbody>
      </table>
    </div>
    <p class="foot">Seeded random samples with a per-problem timeout. Time is the mean over solved problems.</p>
  {/if}
</Panel>

<style>
  .scroll { overflow: auto; max-height: 15rem; border: 1px solid var(--line); border-radius: 10px; background: var(--panel-2); }
  table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
  th { text-align: left; color: var(--muted); font-weight: 500; padding: 0.5rem 0.7rem; position: sticky; top: 0; background: var(--panel-2); border-bottom: 1px solid var(--line); }
  td { padding: 0.45rem 0.7rem; border-bottom: 1px solid rgba(255, 255, 255, 0.04); white-space: nowrap; }
  .r { text-align: right; }
  tr.best td { background: var(--violet-soft); }
  tr.grp th { position: static; background: rgba(255, 255, 255, 0.04); color: var(--text); font-weight: 600; padding: 0.4rem 0.7rem; }
  .foot { color: var(--dim); font-size: 0.72rem; margin-top: 0.5rem; }
  .empty { color: var(--muted); font-size: 0.85rem; line-height: 1.6; }
  code { font-family: var(--mono); color: var(--violet-2); font-size: 0.78rem; }
</style>
