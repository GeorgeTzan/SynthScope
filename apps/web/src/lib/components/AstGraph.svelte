<script lang="ts">
  import { formatValue } from '../format';
  import { buildView } from '../holes';
  import { opName } from '../opnames';
  import type { LaidOutNode } from '../layout';
  import type { HoleRanks } from '../types';
  import Icon from './Icon.svelte';

  let { program, ranks, running = false }: { program: string | null; ranks: HoleRanks | null; running?: boolean } = $props();

  const SUB = '₀₁₂₃₄₅₆₇₈₉';
  const sub = (n: number) => [...String(n)].map((d) => SUB[Number(d)]).join('');
  const DOTS = ['var(--violet)', 'var(--blue)', 'var(--teal)', 'var(--amber)', 'var(--rose)'];

  let view = $derived(buildView(program, ranks));
  let width = $state(0);
  let height = $state(0);
  let fit = $state(true);
  let manual = $state(1);
  let showHoles = $state(true);

  // the Holes card floats over the right edge: keep the graph clear of it
  let reserve = $derived(showHoles && width > 640 ? 280 : 0);

  let scale = $derived.by(() => {
    const l = view.layout;
    if (!l) return 1;
    if (!fit) return manual;
    return Math.max(0.35, Math.min(1.15, (width - 24 - reserve) / l.width, (height - 24) / l.height));
  });

  const holeAt = (n: LaidOutNode) => view.holes.find((h) => h.path.join('.') === n.path.join('.'));
  const isPicked = (n: LaidOutNode) => holeAt(n)?.picked ?? false;
  // a node with children is an operator, one without is a variable or constant
  let kinds = $derived(
    (view.layout?.nodes ?? []).map((n, i, all) => (n.hole !== null ? 'hole' : all.some((m) => m.parent === i) ? 'op' : 'leaf'))
  );

  function edge(from: LaidOutNode, to: LaidOutNode): string {
    const x1 = from.x, y1 = from.y + from.h, x2 = to.x, y2 = to.y;
    const mid = (y1 + y2) / 2;
    return `M${x1} ${y1} C${x1} ${mid} ${x2} ${mid} ${x2} ${y2}`;
  }

  function zoom(delta: number) {
    manual = Math.min(2.2, Math.max(0.3, (fit ? scale : manual) + delta));
    fit = false;
  }

  const ruleText = ['', 'may prune the whole candidate', 'may prune once other holes are filled', 'random choice'];
</script>

<div class="canvas" bind:clientWidth={width} bind:clientHeight={height}>
  {#if view.error}
    <p class="note" role="alert">Cannot draw program: {view.error}</p>
  {:else if view.layout}
    <div class="tools" role="group" aria-label="Zoom">
      <button aria-label="Fit to view" onclick={() => (fit = true)}><Icon name="expand" size={16} /></button>
      <span class="sep"></span>
      <button aria-label="Zoom out" onclick={() => zoom(-0.15)}><Icon name="minus" size={16} /></button>
      <output aria-label="Zoom level">{Math.round(scale * 100)}%</output>
      <button aria-label="Zoom in" onclick={() => zoom(0.15)}><Icon name="plus" size={16} /></button>
      <span class="sep"></span>
      <button aria-label="Reset zoom" onclick={() => { fit = false; manual = 1; }}><Icon name="target" size={16} /></button>
    </div>

    <div class="scroller" style:padding-right={`${reserve + 8}px`}>
      <svg
        width={view.layout.width * scale}
        height={view.layout.height * scale}
        viewBox={`0 0 ${view.layout.width} ${view.layout.height}`}
        role="img"
        aria-label={`Partial program ${view.call}`}
      >
        <defs>
          <filter id="glow" x="-40%" y="-60%" width="180%" height="220%">
            <feGaussianBlur stdDeviation="5" result="b" />
            <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
          <linearGradient id="edge" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stop-color="#8b6cff" stop-opacity="0.85" /><stop offset="1" stop-color="#35e0c6" stop-opacity="0.55" />
          </linearGradient>
          <linearGradient id="opfill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stop-color="#1b1f45" /><stop offset="1" stop-color="#12163a" />
          </linearGradient>
        </defs>

        {#each view.layout.nodes as n (n.path.join('.') || 'root')}
          {#if n.parent !== null}
            <path d={edge(view.layout.nodes[n.parent], n)} fill="none" stroke="url(#edge)" stroke-width="2" stroke-linecap="round" />
          {/if}
        {/each}

        {#each view.layout.nodes as n, i (n.path.join('.') || 'root')}
          {@const kind = kinds[i]}
          {@const hole = holeAt(n)}
          <g class="node {kind}" class:picked={isPicked(n)} transform={`translate(${n.x - n.w / 2} ${n.y})`}>
            {#if kind === 'hole'}
              <title>{`hole ${hole?.index ?? ''}: ${n.hole}`}</title>
              <rect width={n.w} height={n.h} rx="12" class="box" filter={isPicked(n) ? 'url(#glow)' : undefined} />
              <text x={n.w / 2} y={n.h / 2 + 6} text-anchor="middle" class="hole-text">□{hole ? sub(hole.index) : ''}</text>
              <text x={n.w / 2} y={n.h + 15} text-anchor="middle" class="nt">{n.hole}</text>
            {:else if kind === 'op'}
              <rect width={n.w} height={n.h} rx="12" class="box" filter="url(#glow)" fill="url(#opfill)" />
              <g transform="translate(11 11) scale(0.92)" class="cube" aria-hidden="true">
                <path d="M12 1.8 21 6.9v10.2L12 22.2 3 17.1V6.9z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" />
                <path d="M3 6.9 12 12l9-5.1M12 12v10.2" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" />
              </g>
              <title>{`${n.label}: ${opName(n.label).name}`}</title>
              <text x={n.w / 2 + 11} y={n.h / 2 + 6} text-anchor="middle" class="op-text">{opName(n.label).name}</text>
              {#if opName(n.label).name !== n.label}<text x={n.w / 2} y="-7" text-anchor="middle" class="nt">{n.label}</text>{/if}
            {:else}
              <rect width={n.w} height={n.h} rx="12" class="box" filter="url(#glow)" fill="url(#opfill)" />
              <text x={n.w / 2} y={n.h / 2 + 6} text-anchor="middle" class="leaf-text">{formatValue(n.label).main}</text>
            {/if}
          </g>
        {/each}
      </svg>
    </div>

    <aside class="holes" aria-label="Holes">
      <h3>
        <button class="fold" aria-expanded={showHoles} onclick={() => (showHoles = !showHoles)}>
          Holes <span>({view.holes.length})</span>
          <span class="chev" class:shut={!showHoles}><Icon name="chevron" size={14} /></span>
        </button>
      </h3>
      {#if !showHoles}
        <!-- folded away so the whole tree stays visible -->
      {:else if view.holes.length === 0}
        <p class="dim">Complete program: no holes left.</p>
      {:else}
        <ul>
          {#each view.holes as h (h.index)}
            <li class:sel={h.picked}>
              <div class="row1">
                <i style:background={DOTS[(h.index - 1) % DOTS.length]}></i>
                <span class="mono hn">□{sub(h.index)}</span>
                <span class="nt-name">({h.nonterminal})</span>
                {#if h.picked}<span class="badge">selected</span>{/if}
              </div>
              <p class="row2">
                <span class="zap"><Icon name="zap" size={13} /></span>
                {#if h.rank === null}Not ranked yet{:else}<b>Rank {h.rank}</b> <span class="dim">{ruleText[h.rank]}</span>{/if}
              </p>
            </li>
          {/each}
        </ul>
        {#if ranks?.noprune}<p class="dim small">No pruning possible: the engine skips the analysis for this candidate.</p>{/if}
      {/if}
    </aside>
  {:else}
    <div class="empty">
      <svg width="132" height="88" viewBox="0 0 132 88" aria-hidden="true">
        <path d="M66 22 28 62M66 22l38 40" stroke="#2c3463" stroke-width="2" fill="none" />
        <rect x="44" y="4" width="44" height="26" rx="9" fill="none" stroke="#8b6cff" stroke-width="1.6" stroke-dasharray="4 4" />
        <rect x="8" y="58" width="40" height="24" rx="9" fill="none" stroke="#8b6cff" stroke-width="1.6" stroke-dasharray="4 4" />
        <rect x="84" y="58" width="40" height="24" rx="9" fill="none" stroke="#8b6cff" stroke-width="1.6" stroke-dasharray="4 4" />
      </svg>
      <p>{running ? 'Waiting for the first candidate…' : 'Press Run to watch the search fill holes.'}</p>
    </div>
  {/if}
</div>

<style>
  .canvas {
    position: relative;
    flex: 1;
    min-height: 22rem;
    border-radius: 12px;
    background:
      radial-gradient(circle at 1px 1px, rgba(139, 108, 255, 0.16) 1px, transparent 0) 0 0 / 22px 22px,
      var(--panel-2);
    border: 1px solid var(--line);
    overflow: hidden;
    display: flex;
  }
  .scroller { flex: 1; overflow: auto; display: grid; place-items: center; padding: 0.5rem 0.5rem 0.5rem 0.5rem; }
  .scroller > svg { display: block; margin: auto; overflow: visible; }
  .tools { position: absolute; top: 0.7rem; right: 0.8rem; z-index: 2; display: flex; align-items: center; gap: 0.15rem; padding: 0.25rem; border: 1px solid var(--line-2); border-radius: 10px; background: rgba(12, 15, 32, 0.9); }
  .tools button { background: transparent; border: 0; color: var(--muted); padding: 0.35rem; border-radius: 7px; cursor: pointer; display: grid; place-items: center; }
  .tools button:hover { color: var(--text); background: rgba(255, 255, 255, 0.06); }
  .tools output { font-size: 0.8rem; min-width: 2.8rem; text-align: center; color: var(--text); }
  .sep { width: 1px; height: 1.1rem; background: var(--line-2); margin: 0 0.15rem; }

  .box { stroke-width: 1.8; }
  .op .box { stroke: #8b6cff; }
  .leaf .box { stroke: #35e0c6; }
  .hole .box { stroke: #b27cff; stroke-dasharray: 6 5; fill: rgba(139, 108, 255, 0.07); }
  .hole.picked .box { stroke: #d6bcff; fill: rgba(139, 108, 255, 0.2); stroke-dasharray: 7 4; animation: march 1.2s linear infinite; }
  @keyframes march { to { stroke-dashoffset: -22; } }
  .cube { color: #b79cff; }
  .op-text { fill: #f0edff; font-size: 17px; font-weight: 600; letter-spacing: -0.01em; font-family: var(--sans); }
  .leaf-text { fill: #cffcf3; font-size: 17px; font-style: italic; font-weight: 500; font-family: var(--sans); }
  .hole-text { fill: #cdb4ff; font-size: 18px; font-family: var(--mono); }
  .nt { fill: var(--dim); font-size: 11px; font-family: var(--mono); }

  .holes { position: absolute; right: 0.8rem; top: 3.7rem; width: 16.5rem; max-height: calc(100% - 4.5rem); overflow: auto; z-index: 2; border: 1px solid var(--line-2); background: rgba(14, 17, 38, 0.93); border-radius: 12px; padding: 0.75rem 0.85rem; backdrop-filter: blur(6px); }
  .holes h3 { font-size: 0.95rem; margin: 0; }
  .holes h3 + :global(*) { margin-top: 0.5rem; }
  .fold { display: flex; align-items: center; gap: 0.35rem; width: 100%; background: transparent; border: 0; padding: 0; color: inherit; font: inherit; font-weight: 600; cursor: pointer; }
  .chev { margin-left: auto; display: grid; color: var(--muted); transition: transform 0.15s; }
  .chev.shut { transform: rotate(-90deg); }
  .holes h3 span { color: var(--muted); font-weight: 500; }
  .holes ul { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.55rem; }
  li { display: block; padding: 0.45rem 0.55rem; border-radius: 9px; border: 1px solid transparent; }
  li.sel { background: var(--violet-soft); border-color: rgba(139, 108, 255, 0.35); }
  .row1 { display: flex; align-items: center; gap: 0.4rem; font-size: 0.86rem; }
  .row1 i { width: 0.55rem; height: 0.55rem; border-radius: 50%; flex: none; box-shadow: 0 0 8px currentColor; }
  .hn { color: #d9c8ff; }
  .nt-name { color: var(--muted); font-size: 0.8rem; }
  .badge { margin-left: auto; font-size: 0.68rem; padding: 0.05rem 0.45rem; border-radius: 6px; background: var(--violet); color: #fff; font-weight: 600; }
  .row2 { margin: 0.35rem 0 0; font-size: 0.78rem; line-height: 1.45; color: var(--text); }
  .row2 b { color: var(--amber); font-weight: 600; }
  .zap { color: var(--amber); display: inline-block; vertical-align: -2px; margin-right: 0.3rem; }
  .dim { color: var(--muted); }
  .small { font-size: 0.75rem; margin-top: 0.5rem; line-height: 1.4; }
  .empty { margin: auto; display: grid; justify-items: center; gap: 0.9rem; color: var(--muted); padding: 2rem; }
  .note { margin: auto; color: var(--rose); }
  @media (max-width: 900px) { .holes { position: static; width: auto; margin: 0.6rem; } .canvas { flex-direction: column; } }
</style>
