<script lang="ts">
  import type { RunStatus } from '../types';

  let { program, status }: { program: string | null; status: RunStatus } = $props();
</script>

<section aria-label="Best candidate">
  <h3>Best candidate <span class="badge" class:ok={status === 'solved'}>{program ? 'solution' : status}</span></h3>
  {#if program}
    <code>{program}</code>
  {:else}
    <p class="muted">No solution yet.</p>
  {/if}
</section>

<style>
  h3 { margin: 0 0 0.5rem; font-size: 0.95rem; }
  .badge { font-size: 0.7rem; padding: 0.1rem 0.5rem; border-radius: 1rem; background: var(--line); margin-left: 0.5rem; }
  .ok { background: var(--teal); color: #04120f; }
  code { font-family: var(--mono); color: var(--teal); word-break: break-all; }
  .muted { color: var(--muted); }
</style>
