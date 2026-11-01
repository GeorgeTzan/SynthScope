<script lang="ts">
  import type { RunState } from '../state/run.svelte';
  import type { RunConfig } from '../types';

  let { run, problem = $bindable() }: { run: RunState; problem: string } = $props();

  let config = $state<RunConfig>({ policy: 'hope', max_holes: 3, max_nodes: 50000, timeout_s: 30, seed: 0 });
  let running = $derived(run.status === 'running');
</script>

<section aria-label="Run controls">
  <h3>Problem (SyGuS-IF)</h3>
  <label class="sr-only" for="problem">SyGuS-IF problem text</label>
  <textarea id="problem" bind:value={problem} rows="10" spellcheck="false"></textarea>
  <div class="row">
    <label>Policy
      <select bind:value={config.policy}>
        <option value="hope">HOPE (meta analysis)</option>
        <option value="leftmost">Leftmost hole</option>
        <option value="meta_off">Meta off (random)</option>
      </select>
    </label>
    <label>Holes at once
      <input type="number" min="1" max="5" bind:value={config.max_holes} disabled={config.policy !== 'hope'} />
    </label>
  </div>
  <div class="row">
    <label>Max nodes <input type="number" min="1" max="1000000" bind:value={config.max_nodes} /></label>
    <label>Timeout (s) <input type="number" min="1" max="300" bind:value={config.timeout_s} /></label>
  </div>
  <div class="row">
    <button class="run" onclick={() => run.start(problem, { ...config })} disabled={running}>Run</button>
    <button onclick={() => run.cancel()} disabled={!running}>Cancel</button>
    {#if run.status === 'disconnected'}
      <button onclick={() => run.reconnect()}>Reconnect</button>
    {/if}
  </div>
  {#if run.error}<p role="alert" class="err">{run.error}</p>{/if}
</section>

<style>
  h3 { margin: 0 0 0.5rem; font-size: 0.95rem; }
  textarea { width: 100%; box-sizing: border-box; font-family: var(--mono); font-size: 0.8rem; background: var(--panel-2); color: var(--text); border: 1px solid var(--line); border-radius: 0.4rem; padding: 0.5rem; }
  .row { display: flex; gap: 0.75rem; flex-wrap: wrap; margin-top: 0.6rem; align-items: end; }
  label { display: flex; flex-direction: column; font-size: 0.75rem; color: var(--muted); gap: 0.2rem; }
  select, input { background: var(--panel-2); color: var(--text); border: 1px solid var(--line); border-radius: 0.3rem; padding: 0.3rem; width: 7.5rem; }
  button { background: var(--line); color: var(--text); border: 1px solid var(--line); border-radius: 0.4rem; padding: 0.45rem 1rem; cursor: pointer; }
  button.run { background: var(--accent); color: #fff; }
  button:disabled { opacity: 0.45; cursor: not-allowed; }
  button:focus-visible, select:focus-visible, input:focus-visible, textarea:focus-visible { outline: 2px solid var(--teal); outline-offset: 2px; }
  .err { color: #ff8a8a; }
  .sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
</style>
