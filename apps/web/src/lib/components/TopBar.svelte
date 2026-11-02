<script lang="ts">
  import type { AppState } from '../state/app.svelte';
  import type { RunState } from '../state/run.svelte';
  import Icon from './Icon.svelte';

  let { app, run, onrun, onreset }: { app: AppState; run: RunState; onrun: () => void; onreset: () => void } = $props();

  let running = $derived(run.status === 'running');
  let settingsOpen = $state(false);
  let corpus = $derived(app.selected.includes('/') ? app.selected.split('/')[0] : '');
  let corpusNames = $derived(Object.keys(app.corpora));

  function pickCorpus(name: string) {
    if (name === '') app.setDomain(app.parsed?.domain ?? 'bitvector');
    else void app.select(`${name}/${app.corpora[name][0]}`);
  }
</script>

<header class="bar">
  <div class="brand">
    <svg width="34" height="34" viewBox="0 0 34 34" aria-hidden="true">
      <defs>
        <linearGradient id="lg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#b79cff" /><stop offset="1" stop-color="#35e0c6" /></linearGradient>
      </defs>
      <path d="M17 2 30 9.5v15L17 32 4 24.5v-15z" fill="none" stroke="url(#lg)" stroke-width="2.2" stroke-linejoin="round" />
      <path d="M17 9.5 23.5 13v8L17 24.5 10.5 21v-8z" fill="url(#lg)" opacity="0.9" />
    </svg>
    <span class="name">SynthScope</span>
    <span class="tag">HOPE: program synthesis via hole-guided<br />abstract interpretation</span>
  </div>

  <div class="chip project"><Icon name="folder" size={16} /> HOPE (reproduction)</div>

  <div class="group" role="group" aria-label="Domain">
    <span class="lab">Domain:</span>
    <div class="seg">
      <button class:on={app.parsed?.domain === 'bitvector'} onclick={() => app.setDomain('bitvector')} disabled={running}>Bitvector</button>
      <button class:on={app.parsed?.domain === 'string'} onclick={() => app.setDomain('string')} disabled={running}>String</button>
    </div>
  </div>

  <div class="group">
    <label class="lab" for="corpus">Benchmark:</label>
    <select id="corpus" value={corpus} onchange={(e) => pickCorpus(e.currentTarget.value)} disabled={running}>
      <option value="">Built-in samples</option>
      {#each corpusNames as c (c)}<option value={c}>{c} ({app.corpora[c].length})</option>{/each}
    </select>
    {#if corpus}
      <select aria-label="Problem file" value={app.selected.split('/')[1]} onchange={(e) => void app.select(`${corpus}/${e.currentTarget.value}`)} disabled={running}>
        {#each app.corpora[corpus] as f (f)}<option value={f}>{f}</option>{/each}
      </select>
    {/if}
  </div>

  <div class="spacer"></div>

  <button class="run" onclick={onrun} disabled={running || app.parsed === null}><Icon name="play" size={15} /> Run</button>
  <button class="ghost" onclick={() => run.cancel()} disabled={!running}><Icon name="stop" size={14} /> Cancel</button>
  <button class="ghost" onclick={onreset} disabled={running}><Icon name="reset" size={15} /> Reset</button>

  <div class="chip meta" class:off={!app.metaEnabled}>
    <Icon name="activity" size={16} /> {app.metaEnabled ? 'Meta-analysis enabled' : app.config.policy === 'leftmost' ? 'Leftmost order' : 'Meta-analysis off'}
  </div>

  <div class="settings">
    <button class="icon" aria-label="Run settings" aria-expanded={settingsOpen} onclick={() => (settingsOpen = !settingsOpen)}><Icon name="gear" size={19} /></button>
    {#if settingsOpen}
      <div class="pop" role="dialog" aria-label="Run settings">
        <label>Hole policy
          <select bind:value={app.config.policy}>
            <option value="hope">HOPE (meta analysis)</option>
            <option value="leftmost">Leftmost hole</option>
            <option value="meta_off">Meta off (random hole)</option>
          </select>
        </label>
        <label>Holes filled at once
          <input type="number" min="1" max="5" bind:value={app.config.max_holes} disabled={app.config.policy !== 'hope'} />
        </label>
        <label>Max nodes <input type="number" min="1" max="1000000" bind:value={app.config.max_nodes} /></label>
        <label>Timeout (seconds) <input type="number" min="1" max="300" bind:value={app.config.timeout_s} /></label>
        <label>Seed <input type="number" bind:value={app.config.seed} /></label>
      </div>
    {/if}
  </div>
</header>

<style>
  .bar { display: flex; align-items: center; gap: 0.7rem; padding: 0.7rem 1.1rem; border-bottom: 1px solid var(--line); background: rgba(9, 11, 24, 0.75); backdrop-filter: blur(8px); flex-wrap: wrap; position: relative; z-index: 5; }
  .brand { display: flex; align-items: center; gap: 0.6rem; padding-right: 0.9rem; border-right: 1px solid var(--line); }
  .name { font-size: 1.35rem; font-weight: 650; letter-spacing: -0.02em; }
  .tag { font-size: 0.68rem; color: var(--muted); line-height: 1.25; max-width: 14rem; margin-left: 0.5rem; }
  .chip { display: flex; align-items: center; gap: 0.5rem; border: 1px solid var(--line-2); border-radius: 10px; padding: 0.5rem 0.8rem; background: rgba(255, 255, 255, 0.02); color: var(--text); font-size: 0.85rem; }
  .project { color: var(--text); }
  .group { display: flex; align-items: center; gap: 0.5rem; }
  .lab { color: var(--muted); font-size: 0.82rem; }
  .seg { display: flex; border: 1px solid var(--line-2); border-radius: 10px; overflow: hidden; }
  .seg button { background: transparent; border: 0; padding: 0.5rem 0.95rem; color: var(--muted); cursor: pointer; }
  .seg button.on { background: linear-gradient(180deg, #7b5cf5, #6444e0); color: #fff; box-shadow: 0 0 18px -4px var(--violet); }
  .seg button:disabled { cursor: not-allowed; opacity: 0.6; }
  select, input { background: var(--panel-2); color: var(--text); border: 1px solid var(--line-2); border-radius: 9px; padding: 0.45rem 0.6rem; font: inherit; font-size: 0.85rem; max-width: 13rem; }
  .spacer { flex: 1; }
  button.run { display: flex; align-items: center; gap: 0.45rem; background: linear-gradient(180deg, #8b6cff, #6a47ea); border: 1px solid #a48cff; color: #fff; border-radius: 10px; padding: 0.55rem 1.15rem; font-weight: 600; cursor: pointer; box-shadow: 0 6px 22px -8px var(--violet); }
  button.ghost { display: flex; align-items: center; gap: 0.45rem; background: rgba(255, 255, 255, 0.03); border: 1px solid var(--line-2); border-radius: 10px; padding: 0.55rem 1rem; cursor: pointer; color: var(--text); }
  button:disabled { opacity: 0.45; cursor: not-allowed; }
  .meta { color: var(--teal); border-color: rgba(53, 224, 198, 0.35); background: var(--teal-soft); }
  .meta.off { color: var(--amber); border-color: rgba(255, 180, 84, 0.35); background: rgba(255, 180, 84, 0.1); }
  .settings { position: relative; }
  button.icon { background: transparent; border: 0; color: var(--muted); padding: 0.4rem; border-radius: 8px; cursor: pointer; display: grid; place-items: center; }
  button.icon:hover { color: var(--text); }
  .pop { position: absolute; right: 0; top: 2.6rem; width: 16rem; background: var(--panel); border: 1px solid var(--line-2); border-radius: 12px; padding: 0.9rem; display: grid; gap: 0.7rem; box-shadow: 0 20px 50px -10px rgba(0, 0, 0, 0.8); }
  .pop label { display: grid; gap: 0.25rem; color: var(--muted); font-size: 0.78rem; }
  .pop select, .pop input { max-width: none; width: 100%; }
  @media (max-width: 1900px) { .tag { display: none; } }
</style>
