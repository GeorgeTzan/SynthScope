<script lang="ts">
  import { describeEvent } from '../logformat';
  import { formatElapsed, formatStamp } from '../format';
  import type { RunStatus, SynthEvent } from '../types';
  import Icon from './Icon.svelte';
  import Panel from './Panel.svelte';

  let {
    entries,
    status,
    elapsed,
    depthOf = () => 0,
    limit = 200
  }: { entries: SynthEvent[]; status: RunStatus; elapsed: number; depthOf?: (id: unknown) => number; limit?: number } = $props();

  let shown = $derived(entries.slice(-limit).map((e) => ({ e, line: describeEvent(e, { depthOf }) })));
  let list: HTMLOListElement | undefined = $state();

  $effect(() => {
    void shown.length;
    if (list) list.scrollTop = list.scrollHeight;
  });

  const live = $derived(status === 'running');
</script>

<Panel title="Synthesis Log" icon="activity" flush>
  {#snippet right()}
    <span class="pill" class:live>{#if live}<i></i>{/if}{live ? 'Live' : status === 'idle' ? 'Idle' : status}</span>
    {#if entries.length}<span class="time">{formatElapsed(elapsed)}</span>{/if}
  {/snippet}
  {#if shown.length === 0}
    <p class="empty">Events from the engine appear here as the search runs.</p>
  {:else}
    <ol bind:this={list}>
      {#each shown as { e, line } (e.seq)}
        <li class={line.tone}>
          <span class="ts mono">[{formatStamp(e.t ?? 0)}]</span>
          <span class="ico"><Icon name={line.icon} size={16} /></span>
          <div class="txt">
            <span class="title">{line.title}</span>
            {#if line.detail}<span class="detail mono">↳ {line.detail}</span>{/if}
          </div>
        </li>
      {/each}
    </ol>
  {/if}
</Panel>

<style>
  .pill { display: inline-flex; align-items: center; gap: 0.35rem; font-size: 0.76rem; color: var(--muted); border: 1px solid var(--line-2); padding: 0.1rem 0.55rem; border-radius: 999px; }
  .pill.live { color: var(--teal); border-color: rgba(53, 224, 198, 0.4); background: var(--teal-soft); }
  .pill i { width: 0.42rem; height: 0.42rem; border-radius: 50%; background: var(--teal); box-shadow: 0 0 8px var(--teal); animation: pulse 1.4s ease-in-out infinite; }
  @keyframes pulse { 50% { opacity: 0.35; } }
  .time { font-size: 0.74rem; color: var(--muted); background: rgba(255, 255, 255, 0.05); padding: 0.1rem 0.5rem; border-radius: 7px; }
  ol { list-style: none; margin: 0; padding: 0 0.6rem 0.8rem; overflow: auto; max-height: 24.5rem; display: grid; gap: 0.1rem; align-content: start; }
  li { display: grid; grid-template-columns: auto 1.4rem 1fr; gap: 0.5rem; align-items: start; padding: 0.4rem 0.45rem; border-radius: 9px; }
  .ts { color: var(--dim); font-size: 0.7rem; padding-top: 0.2rem; white-space: nowrap; }
  .ico { color: var(--amber); padding-top: 0.12rem; }
  li.good .ico { color: var(--teal); }
  li.bad .ico { color: var(--rose); }
  li.info .ico { color: var(--blue); }
  li.good { background: linear-gradient(90deg, rgba(53, 224, 198, 0.2), rgba(53, 224, 198, 0.05)); border: 1px solid rgba(53, 224, 198, 0.35); }
  .txt { display: grid; min-width: 0; }
  .title { font-size: 0.88rem; font-weight: 500; }
  .detail { color: var(--muted); font-size: 0.74rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .empty { padding: 0.5rem 1rem 1rem; color: var(--muted); font-size: 0.85rem; }
</style>
