<script lang="ts">
  import { layoutTree } from '../layout';
  import type { Candidate, Tree } from '../types';

  let { candidates, cap = 60 }: { candidates: Candidate[]; cap?: number } = $props();

  let chosen = $state<number | null>(null);
  let scroller: HTMLDivElement | undefined = $state();
  let shown = $derived(candidates.slice(0, cap));
  let built = $derived.by(() => {
    if (shown.length === 0) return null;
    const trees = new Map<number, Tree>(shown.map((c) => [c.id, { label: `#${c.id}`, hole: null, children: [] }]));
    for (const c of shown) if (c.parent !== null) trees.get(c.parent)?.children.push(trees.get(c.id) as Tree);
    return layoutTree(trees.get(shown[0].id) as Tree);
  });
  let byLabel = $derived(new Map(shown.map((c) => [`#${c.id}`, c])));
  let latest = $derived(candidates.at(-1)?.id);
  let detail = $derived(chosen === null ? candidates.at(-1) : candidates.find((c) => c.id === chosen));

  // open the view on the root, not on the left edge of a wide tree
  $effect(() => {
    if (!scroller || !built) return;
    const root = built.nodes[0];
    scroller.scrollLeft = Math.max(0, root.x - scroller.clientWidth / 2);
  });

  function edge(a: { x: number; y: number; h: number }, b: { x: number; y: number }): string {
    const y1 = a.y + a.h, mid = (y1 + b.y) / 2;
    return `M${a.x} ${y1} C${a.x} ${mid} ${b.x} ${mid} ${b.x} ${b.y}`;
  }
</script>

<div class="wrap">
  {#if !built}
    <p class="empty">The search tree grows here: every expanded candidate hangs under the candidate it was filled from.</p>
  {:else}
    <p class="lead">
      {shown.length}{candidates.length > shown.length ? ` of ${candidates.length}` : ''} expanded candidates.
      <span class="key ok"></span> expanded <span class="key bad"></span> discarded as infeasible <span class="key cur"></span> latest
    </p>
    <div class="scroller" bind:this={scroller}>
      <svg width={built.width} height={built.height} viewBox={`0 0 ${built.width} ${built.height}`} role="img" aria-label="Search tree of expanded candidates">
        {#each built.nodes as n (n.label)}
          {#if n.parent !== null}<path d={edge(built.nodes[n.parent], n)} class="edge" />{/if}
        {/each}
        {#each built.nodes as n (n.label)}
          {@const c = byLabel.get(n.label)}
          <g
            transform={`translate(${n.x - n.w / 2} ${n.y})`}
            class="n"
            class:bad={c?.status === 'pruned'}
            class:cur={c?.id === latest}
            role="button"
            tabindex="0"
            aria-label={`candidate ${n.label}`}
            onclick={() => (chosen = c?.id ?? null)}
            onkeydown={(e) => e.key === 'Enter' && (chosen = c?.id ?? null)}
          >
            <rect width={n.w} height={n.h} rx="12" />
            <text x={n.w / 2} y={n.h / 2 + 5} text-anchor="middle">{n.label}</text>
          </g>
        {/each}
      </svg>
    </div>
    {#if detail}<p class="detail mono"><b>#{detail.id}</b> depth {detail.depth} · {detail.program}</p>{/if}
  {/if}
</div>

<style>
  .wrap { padding: 1rem; flex: 1; min-height: 22rem; display: flex; flex-direction: column; gap: 0.7rem; min-width: 0; }
  .lead { color: var(--muted); font-size: 0.82rem; display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }
  .key { width: 0.7rem; height: 0.7rem; border-radius: 3px; display: inline-block; margin-left: 0.6rem; }
  .key.ok { background: var(--teal); } .key.bad { background: var(--rose); } .key.cur { background: var(--violet); }
  .scroller { flex: 1; overflow: auto; border: 1px solid var(--line); border-radius: 12px; background: var(--panel-2); padding: 0.4rem; }
  svg { display: block; margin: 0 auto; }
  .edge { fill: none; stroke: rgba(139, 108, 255, 0.4); stroke-width: 1.6; }
  .n { cursor: pointer; }
  .n rect { fill: rgba(53, 224, 198, 0.1); stroke: var(--teal); stroke-width: 1.6; }
  .n.bad rect { fill: var(--rose-soft); stroke: var(--rose); }
  .n.cur rect { fill: var(--violet-soft); stroke: var(--violet-2); stroke-width: 2.2; }
  text { fill: var(--text); font-size: 13px; font-family: var(--mono); pointer-events: none; }
  .detail { color: var(--muted); font-size: 0.78rem; overflow-wrap: anywhere; }
  .detail b { color: var(--violet-2); }
  .empty { color: var(--muted); margin: auto; max-width: 36ch; text-align: center; }
</style>
