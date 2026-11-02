<script lang="ts">
  import { onMount } from 'svelte';
  import AbstractState from '$lib/components/AbstractState.svelte';
  import BenchmarkSummary from '$lib/components/BenchmarkSummary.svelte';
  import BestCandidate from '$lib/components/BestCandidate.svelte';
  import CandidateProgram from '$lib/components/CandidateProgram.svelte';
  import CenterTabs from '$lib/components/CenterTabs.svelte';
  import ExamplesPanel from '$lib/components/ExamplesPanel.svelte';
  import GrammarPanel from '$lib/components/GrammarPanel.svelte';
  import ProblemDialog from '$lib/components/ProblemDialog.svelte';
  import ProgressChart from '$lib/components/ProgressChart.svelte';
  import Statistics from '$lib/components/Statistics.svelte';
  import SynthLog from '$lib/components/SynthLog.svelte';
  import TopBar from '$lib/components/TopBar.svelte';
  import { toPythonFunction } from '$lib/python';
  import { AppState } from '$lib/state/app.svelte';
  import { RunState } from '$lib/state/run.svelte';

  const app = new AppState();
  const run = new RunState();
  let editing = $state(false);

  let signature = $derived(app.parsed ? `${app.parsed.functionName}(${app.parsed.params.map((p) => p.name).join(', ')})` : 'f(x)');
  let python = $derived.by(() => {
    const p = app.parsed;
    if (!run.best || !p || run.best.includes('□')) return null;
    const bits = /BitVec (\d+)/.exec(p.returnSort);
    return toPythonFunction(run.best, p.functionName, p.params.map((q) => q.name), p.domain === 'bitvector' ? 'bv' : 'str', bits ? Number(bits[1]) : null);
  });
  let depthById = $derived(new Map(run.candidates.map((c) => [c.id, c.depth])));

  onMount(() => void app.loadLists());

  function start() {
    void run.start(app.problem, { ...app.config });
  }
  function reset() {
    run.replay([]);
    run.status = 'idle';
  }
</script>

<svelte:head><title>SynthScope</title></svelte:head>

<div class="shell">
  <TopBar {app} {run} onrun={start} onreset={reset} />
  <div class="body">
    <main>
      {#if app.loadError}<p class="banner" role="alert">{app.loadError}</p>{/if}
      {#if run.error}<p class="banner" role="alert">{run.error}</p>{/if}
      <div class="left">
        <ExamplesPanel problem={app.parsed} onedit={() => (editing = true)} />
        <GrammarPanel problem={app.parsed} />
      </div>
      <div class="mid">
        <CenterTabs {run} />
        <div class="pair">
          <CandidateProgram program={run.status === 'solved' ? (run.best ?? run.current) : (run.current ?? run.best)} />
          <AbstractState analysis={run.analysis} />
        </div>
        <div class="pair lower">
          <div id="progress"><ProgressChart series={run.series} /></div>
          <div id="benchmarks"><BenchmarkSummary rows={app.results} /></div>
        </div>
      </div>
      <div class="right">
        <SynthLog entries={run.events} status={run.status} elapsed={run.elapsed} depthOf={(id) => depthById.get(Number(id)) ?? 0} />
        <BestCandidate program={run.best} status={run.status} {signature} {python} verified={run.verified} />
        <Statistics explored={run.explored} pruned={run.pruned} elapsed={run.elapsed} maxDepth={run.maxDepth} nodes={run.nodes} />
      </div>
    </main>
  </div>
  <ProblemDialog bind:open={editing} bind:problem={app.problem} />
</div>

<style>
  .shell { min-height: 100vh; display: flex; flex-direction: column; }
  .body { display: grid; grid-template-columns: 1fr; flex: 1; min-height: 0; }
  main { display: grid; grid-template-columns: minmax(17rem, 21rem) minmax(0, 1fr) minmax(19rem, 24rem); gap: 0.9rem; padding: 0.9rem; align-items: start; }
  .left, .mid, .right { display: grid; gap: 0.9rem; min-width: 0; align-content: start; }
  .pair { display: grid; grid-template-columns: 1fr 1fr; gap: 0.9rem; align-items: start; }
  .pair > :global(*) { min-width: 0; }
  .lower { grid-template-columns: 1.15fr 1fr; }
  .banner { grid-column: 1 / -1; background: var(--rose-soft); border: 1px solid rgba(255, 107, 129, 0.4); color: #ffb3bf; padding: 0.6rem 0.9rem; border-radius: 10px; }
  @media (max-width: 1280px) {
    main { grid-template-columns: minmax(16rem, 20rem) minmax(0, 1fr); }
    .right { grid-column: 1 / -1; grid-template-columns: repeat(auto-fit, minmax(19rem, 1fr)); }
  }
  @media (max-width: 900px) {
    .body { grid-template-columns: 1fr; }
    main { grid-template-columns: 1fr; }
    .pair, .lower { grid-template-columns: 1fr; }
  }
</style>
