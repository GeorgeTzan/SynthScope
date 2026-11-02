<script lang="ts">
  import Icon, { type IconName } from './Icon.svelte';

  let { onedit }: { onedit: () => void } = $props();
  const items: { icon: IconName; label: string; href?: string }[] = [
    { icon: 'code', label: 'Synthesis', href: '#synthesis' },
    { icon: 'chart', label: 'Search progress', href: '#progress' },
    { icon: 'table', label: 'Benchmark summary', href: '#benchmarks' }
  ];
</script>

<nav class="rail" aria-label="Sections">
  {#each items as it, i (it.label)}
    <a class:on={i === 0} href={it.href} aria-label={it.label} title={it.label}><Icon name={it.icon} size={20} /></a>
  {/each}
  <button aria-label="Edit problem" title="Edit problem" onclick={onedit}><Icon name="pencil" size={20} /></button>
</nav>

<style>
  .rail { display: flex; flex-direction: column; gap: 0.45rem; padding: 0.9rem 0.55rem; border-right: 1px solid var(--line); background: rgba(9, 11, 24, 0.6); align-items: center; }
  a, button { width: 2.6rem; height: 2.6rem; display: grid; place-items: center; border-radius: 12px; color: var(--muted); border: 1px solid transparent; background: transparent; cursor: pointer; text-decoration: none; }
  a:hover, button:hover { color: var(--text); background: rgba(255, 255, 255, 0.04); }
  a.on { color: var(--violet-2); background: var(--violet-soft); border-color: rgba(139, 108, 255, 0.45); box-shadow: 0 0 18px -6px var(--violet); }
  @media (max-width: 900px) { .rail { flex-direction: row; border-right: 0; border-bottom: 1px solid var(--line); justify-content: center; } }
</style>
