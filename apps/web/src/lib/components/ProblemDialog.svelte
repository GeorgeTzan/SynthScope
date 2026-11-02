<script lang="ts">
  import Icon from './Icon.svelte';

  let { open = $bindable(false), problem = $bindable() }: { open: boolean; problem: string } = $props();
  let dialog: HTMLDialogElement | undefined = $state();

  $effect(() => {
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  });
</script>

<dialog bind:this={dialog} onclose={() => (open = false)} aria-label="Edit problem">
  <header>
    <h2>Problem (SyGuS-IF)</h2>
    <button class="x" aria-label="Close" onclick={() => (open = false)}><Icon name="x" size={18} /></button>
  </header>
  <label class="sr" for="problem-text">SyGuS-IF problem text</label>
  <textarea id="problem-text" bind:value={problem} spellcheck="false" rows="16"></textarea>
  <footer>
    <p>One <code>synth-fun</code> with an explicit grammar, plus <code>constraint</code> examples or a reference function.</p>
    <button class="done" onclick={() => (open = false)}>Done</button>
  </footer>
</dialog>

<style>
  dialog { background: var(--panel); color: var(--text); border: 1px solid var(--line-2); border-radius: 16px; padding: 1.1rem 1.2rem; width: min(46rem, 94vw); box-shadow: 0 30px 80px -20px rgba(0, 0, 0, 0.9); }
  dialog::backdrop { background: rgba(4, 5, 12, 0.7); backdrop-filter: blur(3px); }
  header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.7rem; }
  h2 { font-size: 1.05rem; }
  textarea { width: 100%; background: var(--panel-2); color: var(--text); border: 1px solid var(--line-2); border-radius: 10px; padding: 0.8rem; font-family: var(--mono); font-size: 0.82rem; line-height: 1.5; resize: vertical; }
  footer { display: flex; justify-content: space-between; align-items: center; gap: 1rem; margin-top: 0.8rem; color: var(--muted); font-size: 0.8rem; }
  code { font-family: var(--mono); color: var(--violet-2); }
  .done { background: linear-gradient(180deg, #8b6cff, #6a47ea); border: 1px solid #a48cff; color: #fff; border-radius: 10px; padding: 0.5rem 1.3rem; font-weight: 600; cursor: pointer; }
  .x { background: transparent; border: 0; color: var(--muted); cursor: pointer; padding: 0.3rem; border-radius: 8px; }
  .sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
</style>
