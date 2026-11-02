<script lang="ts">
  import type { ParsedProblem } from '../problem';
  import { formatValue } from '../format';
  import Icon from './Icon.svelte';
  import Panel from './Panel.svelte';

  let { problem, onedit }: { problem: ParsedProblem | null; onedit: () => void } = $props();

  let inputHeader = $derived(problem ? problem.params.map((p) => p.name).join(', ') : 'x');
</script>

<Panel title="Examples" icon="table" count={problem?.examples.length ?? 0}>
  {#snippet right()}
    <button class="tool" aria-label="Edit problem" title="Edit problem" onclick={onedit}><Icon name="pencil" size={16} /></button>
  {/snippet}
  {#if problem === null}
    <p class="empty">The problem text could not be read. Open the editor to fix it.</p>
  {:else if problem.examples.length === 0}
    <p class="empty">
      {#if problem.reference}
        This problem is given as a reference function, <code>{problem.reference}</code>. The engine samples examples from it and checks the result with Z3.
      {:else}
        This problem has no input/output examples.
      {/if}
    </p>
  {:else}
    <div class="scroll">
      <table>
        <thead>
          <tr><th class="n">#</th><th title={`Input (${inputHeader})`}>Input</th><th class="arrow"></th><th title={`Output f(${inputHeader})`}>Output</th></tr>
        </thead>
        <tbody>
          {#each problem.examples as ex, i (i)}
            <tr>
              <td class="n">{i + 1}</td>
              <td class="mono" title={ex.inputs.map((v) => formatValue(v).raw ?? v).join(', ')}>{ex.inputs.map((v) => formatValue(v).main).join(', ')}</td>
              <td class="arrow"><Icon name="arrow" size={14} /></td>
              <td class="mono out" title={formatValue(ex.output).raw ?? ex.output}>{formatValue(ex.output).main}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</Panel>

<style>
  .tool { background: transparent; border: 0; color: var(--muted); padding: 0.3rem; border-radius: 8px; cursor: pointer; display: grid; place-items: center; }
  .tool:hover { color: var(--text); background: rgba(255, 255, 255, 0.05); }
  .scroll { max-height: 15rem; overflow: auto; border: 1px solid var(--line); border-radius: 10px; background: var(--panel-2); }
  table { width: 100%; border-collapse: collapse; font-size: 0.85rem; table-layout: fixed; }
  th { text-align: left; font-weight: 500; color: var(--muted); padding: 0.55rem 0.7rem; border-bottom: 1px solid var(--line); position: sticky; top: 0; background: var(--panel-2); }
  td { padding: 0.5rem 0.7rem; border-bottom: 1px solid rgba(255, 255, 255, 0.04); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  tr:last-child td { border-bottom: 0; }
  .n { width: 2.2rem; color: var(--muted); }
  .arrow { width: 1.6rem; color: var(--dim); text-align: center; padding-left: 0; padding-right: 0; }
  .out { color: var(--violet-2); }
  .empty { color: var(--muted); font-size: 0.85rem; line-height: 1.55; }
  code { color: var(--violet-2); font-family: var(--mono); }
</style>
