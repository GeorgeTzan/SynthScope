<script lang="ts">
  import type { Snippet } from 'svelte';
  import Icon, { type IconName } from './Icon.svelte';

  let {
    title,
    icon,
    count,
    right,
    children,
    flush = false
  }: { title: string; icon: IconName; count?: number; right?: Snippet; children: Snippet; flush?: boolean } = $props();
</script>

<section class="panel card" aria-label={title}>
  <header>
    <span class="ico"><Icon name={icon} size={17} /></span>
    <h2>{title}</h2>
    {#if count !== undefined}<span class="count">{count}</span>{/if}
    <span class="spacer"></span>
    {#if right}{@render right()}{/if}
  </header>
  <div class="body" class:flush>{@render children()}</div>
</section>

<style>
  .panel { display: flex; flex-direction: column; }
  header { display: flex; align-items: center; gap: 0.6rem; padding: 0.85rem 1rem 0.7rem; }
  .ico { color: var(--violet-2); display: grid; place-items: center; }
  h2 { font-size: 1.02rem; font-weight: 600; letter-spacing: -0.01em; }
  .count { background: var(--violet-soft); color: var(--violet-2); border-radius: 6px; padding: 0 0.45rem; font-size: 0.75rem; font-weight: 600; line-height: 1.5; }
  .spacer { flex: 1; }
  .body { padding: 0 1rem 1rem; min-height: 0; flex: 1; display: flex; flex-direction: column; }
  .body.flush { padding: 0; }
</style>
