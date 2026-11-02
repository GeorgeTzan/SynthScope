<script lang="ts">
  import type { ParsedProblem } from '../problem';
  import { opName } from '../opnames';
  import { formatValue } from '../format';
  import Icon from './Icon.svelte';
  import Panel from './Panel.svelte';

  let { problem }: { problem: ParsedProblem | null } = $props();
  let g = $derived(problem?.grammar);
</script>

<Panel title="Grammar" icon="cube">
  {#if !g}
    <p class="empty">No grammar to show.</p>
  {:else}
    <div class="scroll">
      <details open>
        <summary><Icon name="chevron" size={15} /> Operators ({g.operators.length})</summary>
        <ul>
          {#each g.operators as op (`${op.result}:${op.name}:${op.args.join()}`)}
            <li>
              <span class="f">f</span>
              <span class="mono sig" title={opName(op.name).name}><span class="name">{op.name}</span>({op.args.join(', ')})</span>
              <span class="mono type" title={`${op.args.join(' × ')} → ${op.result}`}>→ {op.result}</span>
            </li>
          {/each}
        </ul>
      </details>
      <details open>
        <summary><Icon name="chevron" size={15} /> Constants ({g.constants.length})</summary>
        <ul class="chips">
          {#each g.constants as c (`${c.nonterminal}:${c.value}`)}
            <li class="mono chip" title={formatValue(c.value).raw ?? `in ${c.nonterminal}`}>{formatValue(c.value).main}</li>
          {/each}
        </ul>
      </details>
      <details open>
        <summary><Icon name="chevron" size={15} /> Variables ({g.variables.length})</summary>
        <ul>
          {#each g.variables as v (v.name)}
            <li><span class="f hash">x</span><span class="mono sig">{v.name}</span><span class="mono type">: {v.sort}</span></li>
          {/each}
        </ul>
      </details>
    </div>
  {/if}
</Panel>

<style>
  .scroll { overflow: auto; max-height: 22rem; display: grid; gap: 0.4rem; }
  details { border-radius: 10px; }
  summary { display: flex; align-items: center; gap: 0.4rem; cursor: pointer; list-style: none; padding: 0.45rem 0.6rem; border-radius: 9px; background: rgba(255, 255, 255, 0.035); font-weight: 600; font-size: 0.88rem; }
  summary::-webkit-details-marker { display: none; }
  details:not([open]) summary :global(svg) { transform: rotate(-90deg); }
  ul { list-style: none; margin: 0.35rem 0 0; padding: 0; display: grid; gap: 0.25rem; }
  li { display: flex; flex-wrap: wrap; align-items: baseline; gap: 0.55rem; padding: 0.25rem 0.4rem; font-size: 0.83rem; min-width: 0; }
  .f { flex: none; width: 1.55rem; height: 1.55rem; display: grid; place-items: center; border-radius: 6px; background: var(--violet-soft); color: var(--violet-2); font-family: var(--mono); font-style: italic; font-size: 0.78rem; align-self: center; }
  .f.hash { font-style: normal; background: var(--teal-soft); color: var(--teal); }
  .sig { overflow-wrap: anywhere; min-width: 0; }
  .name { color: var(--violet-2); }
  .type { color: var(--muted); font-size: 0.76rem; margin-left: auto; white-space: nowrap; }
  ul.chips { display: flex; flex-wrap: wrap; gap: 0.35rem; }
  .chip { display: block; padding: 0.15rem 0.5rem; border-radius: 7px; background: var(--teal-soft); color: var(--teal); font-size: 0.78rem; }
  .empty { color: var(--muted); }
</style>
