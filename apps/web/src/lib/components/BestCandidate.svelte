<script lang="ts">
  import { callSegments } from '../holes';
  import { parseProgram } from '../sexpr';
  import type { RunStatus } from '../types';
  import Icon from './Icon.svelte';
  import Panel from './Panel.svelte';

  const EMPTY: Partial<Record<RunStatus, string>> = {
    running: 'Searching…',
    timeout: 'No solution found: the time limit ran out first. Try a longer timeout, more nodes or a smaller grammar.',
    exhausted: 'No solution found: the search ended (queue empty or node limit hit). This does not prove none exists.',
    unsupported: 'This problem uses something the engine does not support.',
    cancelled: 'Run cancelled before a solution was found.',
    error: 'The run failed.',
    disconnected: 'Connection lost before a solution arrived.'
  };

  let { program, status, signature, python = null, verified = null }: { program: string | null; status: RunStatus; signature: string; python?: string | null; verified?: boolean | null } = $props();

  let segments = $derived.by(() => {
    if (!program) return null;
    try {
      return callSegments(parseProgram(program));
    } catch {
      return [{ text: program, kind: 'leaf' as const }];
    }
  });
  let copied = $state(false);
  const emptyText = (st: RunStatus): string => EMPTY[st] ?? 'No solution yet.';

  async function copy() {
    const text = python ?? `${signature} = ${segments?.map((s) => s.text).join('') ?? ''}`;
    try {
      await navigator.clipboard.writeText(text);
      copied = true;
      setTimeout(() => (copied = false), 1500);
    } catch {
      /* clipboard blocked: nothing to do */
    }
  }
</script>

<Panel title="Best Candidate" icon="trophy">
  {#snippet right()}
    {#if status === 'solved'}
      {#if verified === true}<span class="badge" title="Z3 found no counterexample to the reference function">Verified</span>
      {:else if verified === false}<span class="badge warn" title="Z3 could not decide; only the examples are checked">Matches examples only</span>
      {:else}<span class="badge">Solution</span>{/if}
    {/if}
  {/snippet}
  {#if segments}
    {#if python}
      <div class="code py">
        <pre aria-label="Python">{python}</pre>
        <button aria-label="Copy solution" onclick={copy}>{#if copied}<Icon name="check" size={16} />{:else}<Icon name="copy" size={16} />{/if}</button>
      </div>
    {/if}
    <div class="code" class:alt={python}>
      <code><span class="sig">{signature}</span> = {#each segments as s, i (i)}<span class={s.kind}>{s.text}</span>{/each}</code>
      {#if !python}<button aria-label="Copy solution" onclick={copy}>{#if copied}<Icon name="check" size={16} />{:else}<Icon name="copy" size={16} />{/if}</button>{/if}
    </div>
  {:else}
    <p class="empty">{emptyText(status)}</p>
  {/if}
</Panel>

<style>
  .badge { font-size: 0.75rem; font-weight: 600; color: var(--teal); background: var(--teal-soft); border: 1px solid rgba(53, 224, 198, 0.4); border-radius: 999px; padding: 0.1rem 0.7rem; }
  .badge.warn { color: var(--amber); background: rgba(255, 190, 80, 0.12); border-color: rgba(255, 190, 80, 0.4); }
  .code { display: flex; align-items: center; gap: 0.5rem; background: var(--panel-2); border: 1px solid var(--line); border-radius: 10px; padding: 0.7rem 0.8rem; }
  .code + .code { margin-top: 0.5rem; }
  .alt { background: transparent; padding: 0.45rem 0.8rem; }
  .alt code { font-size: 0.78rem; color: var(--muted); }
  pre { flex: 1; margin: 0; font-family: var(--mono); font-size: 0.88rem; line-height: 1.5; overflow-x: auto; color: var(--teal); }
  code { flex: 1; font-size: 0.9rem; overflow-x: auto; white-space: nowrap; }
  .sig { color: var(--text); }
  .op { color: var(--violet-2); }
  .hole { color: #ff9be0; }
  .leaf { color: var(--teal); }
  .punct { color: var(--muted); }
  button { background: transparent; border: 0; color: var(--muted); cursor: pointer; padding: 0.25rem; border-radius: 7px; display: grid; }
  button:hover { color: var(--text); }
  .empty { color: var(--muted); font-size: 0.85rem; }
</style>
