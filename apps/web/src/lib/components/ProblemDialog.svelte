<script lang="ts">
  import { buildNumbersProblem, NUMBER_OPS, parseConstants, parseRows, WIDTHS } from '../numbers';
  import Icon from './Icon.svelte';

  let { open = $bindable(false), problem = $bindable() }: { open: boolean; problem: string } = $props();
  let dialog: HTMLDialogElement | undefined = $state();
  let tab = $state<'numbers' | 'sygus'>('numbers');

  let width = $state(8);
  let examples = $state('2 -> 4\n3 -> 9\n4 -> 16');
  let ops = $state<string[]>(['bvadd', 'bvmul']);
  let constants = $state('1');
  let error = $state<string | null>(null);

  $effect(() => {
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  });

  function apply() {
    try {
      problem = buildNumbersProblem({ width, rows: parseRows(examples), ops, constants: parseConstants(constants) });
      error = null;
      open = false;
    } catch (e) {
      error = (e as Error).message;
    }
  }
</script>

<dialog bind:this={dialog} onclose={() => (open = false)} aria-label="Edit problem">
  <header>
    <div class="tabs" role="tablist" aria-label="Input format">
      <button role="tab" aria-selected={tab === 'numbers'} onclick={() => (tab = 'numbers')}>Numbers</button>
      <button role="tab" aria-selected={tab === 'sygus'} onclick={() => (tab = 'sygus')}>SyGuS-IF</button>
    </div>
    <button class="x" aria-label="Close" onclick={() => (open = false)}><Icon name="x" size={18} /></button>
  </header>

  {#if tab === 'numbers'}
    <div class="form">
      <label class="field">
        <span>Examples, one per line</span>
        <textarea bind:value={examples} spellcheck="false" rows="6" placeholder={'2 -> 4\n3 -> 9'}></textarea>
        <small>Write <code>input -> output</code>. Several inputs: <code>2, 3 -> 6</code>. Whole numbers, negatives allowed.</small>
      </label>
      <div class="row">
        <label class="field">
          <span>Bit width</span>
          <select bind:value={width}>{#each WIDTHS as w (w)}<option value={w}>{w} bits</option>{/each}</select>
          <small>Results wrap around at 2<sup>{width}</sup>.</small>
        </label>
        <label class="field grow">
          <span>Constants the program may use</span>
          <input bind:value={constants} spellcheck="false" />
        </label>
      </div>
      <fieldset>
        <legend>Operations the program may use</legend>
        <div class="ops">
          {#each NUMBER_OPS as o (o.name)}
            <label class="op"><input type="checkbox" bind:group={ops} value={o.name} /><span class="mono">{o.symbol}</span><small>{o.name}</small></label>
          {/each}
        </div>
      </fieldset>
      {#if error}<p class="err" role="alert">{error}</p>{/if}
    </div>
    <footer>
      <p>The search builds a program from these operations. The result is shown as a graph and as Python.</p>
      <button class="done" onclick={apply}>Use these examples</button>
    </footer>
  {:else}
    <label class="sr" for="problem-text">SyGuS-IF problem text</label>
    <textarea id="problem-text" bind:value={problem} spellcheck="false" rows="16"></textarea>
    <footer>
      <p>One <code>synth-fun</code> with an explicit grammar, plus <code>constraint</code> examples or a reference function.</p>
      <button class="done" onclick={() => (open = false)}>Done</button>
    </footer>
  {/if}
</dialog>

<style>
  dialog { background: var(--panel); color: var(--text); border: 1px solid var(--line-2); border-radius: 16px; padding: 1.1rem 1.2rem; width: min(46rem, 94vw); box-shadow: 0 30px 80px -20px rgba(0, 0, 0, 0.9); }
  dialog::backdrop { background: rgba(4, 5, 12, 0.7); backdrop-filter: blur(3px); }
  header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.7rem; }
  .tabs { display: inline-flex; gap: 0.2rem; padding: 0.2rem; border-radius: 10px; background: var(--panel-2); border: 1px solid var(--line); }
  .tabs button { background: transparent; border: 0; color: var(--muted); padding: 0.35rem 0.9rem; border-radius: 8px; cursor: pointer; font-weight: 500; }
  .tabs button[aria-selected='true'] { background: var(--violet-soft); color: var(--text); }
  .form { display: grid; gap: 0.9rem; }
  .field { display: grid; gap: 0.3rem; font-size: 0.82rem; color: var(--muted); }
  .field > span, legend { color: var(--text); font-weight: 500; font-size: 0.85rem; }
  .field small { font-size: 0.75rem; }
  .row { display: flex; gap: 1rem; align-items: start; }
  .grow { flex: 1; }
  input:not([type='checkbox']), select { background: var(--panel-2); color: var(--text); border: 1px solid var(--line-2); border-radius: 9px; padding: 0.5rem 0.65rem; font-family: var(--mono); font-size: 0.85rem; }
  fieldset { border: 1px solid var(--line); border-radius: 10px; padding: 0.6rem 0.8rem 0.8rem; margin: 0; }
  .ops { display: grid; grid-template-columns: repeat(auto-fill, minmax(8.5rem, 1fr)); gap: 0.4rem; margin-top: 0.4rem; }
  .op { display: flex; align-items: baseline; gap: 0.45rem; padding: 0.3rem 0.5rem; border-radius: 8px; background: var(--panel-2); border: 1px solid var(--line); cursor: pointer; }
  .op small { color: var(--muted); font-size: 0.7rem; margin-left: auto; }
  .op:has(input:checked) { border-color: rgba(139, 108, 255, 0.55); background: var(--violet-soft); }
  .err { margin: 0; color: #ffb3bf; background: var(--rose-soft); border: 1px solid rgba(255, 107, 129, 0.4); border-radius: 9px; padding: 0.5rem 0.7rem; font-size: 0.82rem; }
  textarea { width: 100%; background: var(--panel-2); color: var(--text); border: 1px solid var(--line-2); border-radius: 10px; padding: 0.8rem; font-family: var(--mono); font-size: 0.82rem; line-height: 1.5; resize: vertical; }
  footer { display: flex; justify-content: space-between; align-items: center; gap: 1rem; margin-top: 0.8rem; color: var(--muted); font-size: 0.8rem; }
  code { font-family: var(--mono); color: var(--violet-2); }
  .done { white-space: nowrap; flex: none; background: linear-gradient(180deg, #8b6cff, #6a47ea); border: 1px solid #a48cff; color: #fff; border-radius: 10px; padding: 0.5rem 1.3rem; font-weight: 600; cursor: pointer; }
  .x { background: transparent; border: 0; color: var(--muted); cursor: pointer; padding: 0.3rem; border-radius: 8px; }
  .sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
</style>
