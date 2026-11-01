<script lang="ts">
  import AstView from '$lib/components/AstView.svelte';
  import BestCandidate from '$lib/components/BestCandidate.svelte';
  import HolesPanel from '$lib/components/HolesPanel.svelte';
  import ProgressChart from '$lib/components/ProgressChart.svelte';
  import RunControls from '$lib/components/RunControls.svelte';
  import Stats from '$lib/components/Stats.svelte';
  import SynthLog from '$lib/components/SynthLog.svelte';
  import { RunState } from '$lib/state/run.svelte';

  const SAMPLE = `(set-logic BV)
(synth-fun f ((x (BitVec 4))) (BitVec 4)
  ((Start (BitVec 4) (x #x1 (bvand Start Start) (bvadd Start Start) (bvnot Start)))))
(constraint (= (f #b1011) #b1000))
(constraint (= (f #b0111) #b0000))
(check-synth)
`;

  const run = new RunState();
  let problem = $state(SAMPLE);
</script>

<svelte:head><title>SynthScope</title></svelte:head>

<header>
  <h1>SynthScope</h1>
  <p>Live view of HOPE: meta-analysis-guided hole filling. Everything shown is an event from the engine.</p>
</header>

<main>
  <div class="panel left"><RunControls {run} bind:problem /></div>
  <div class="panel center">
    <h2>Partial program</h2>
    <AstView program={run.current ?? run.best} />
    <HolesPanel ranks={run.ranks} />
    <BestCandidate program={run.best} status={run.status} />
  </div>
  <div class="panel right">
    <SynthLog entries={run.events} />
    <Stats explored={run.explored} pruned={run.pruned} received={run.events.length} nodes={run.nodes} status={run.status} />
  </div>
  <div class="panel bottom"><ProgressChart series={run.series} /></div>
</main>

<style>
  :global(:root) {
    --bg: #0c0e17; --panel: #131626; --panel-2: #0f1220; --line: #252a42; --text: #e6e8f2;
    --muted: #8b90ab; --accent: #6d5dfc; --violet: #b18cff; --teal: #3fd9c0;
    --mono: ui-monospace, 'SFMono-Regular', Menlo, Consolas, monospace;
  }
  :global(body) { margin: 0; background: var(--bg); color: var(--text); font-family: system-ui, sans-serif; }
  header { padding: 1rem 1rem 0; }
  h1 { margin: 0; font-size: 1.3rem; }
  header p { margin: 0.2rem 0 0; color: var(--muted); font-size: 0.85rem; }
  main { display: grid; gap: 1rem; padding: 1rem; grid-template-columns: 1fr; }
  .panel { background: var(--panel); border: 1px solid var(--line); border-radius: 0.7rem; padding: 1rem; min-width: 0; }
  .panel h2 { margin: 0 0 0.6rem; font-size: 0.95rem; }
  @media (min-width: 1000px) {
    main { grid-template-columns: 1fr 1.4fr 1fr; }
    .bottom { grid-column: 1 / -1; }
  }
</style>
