import { describe, expect, it } from 'vitest';
import { AppState, SAMPLES } from './app.svelte';

function fakeFetch(routes: Record<string, unknown>, calls: string[] = []) {
  return (async (url: string) => {
    calls.push(url);
    if (!(url in routes)) return { ok: false, status: 404, json: async () => ({ detail: 'nope' }) };
    return { ok: true, status: 200, json: async () => routes[url] };
  }) as unknown as typeof fetch;
}

describe('AppState', () => {
  it('starts on the bitvector sample and parses it', () => {
    const app = new AppState(fakeFetch({}));
    expect(app.problem).toBe(SAMPLES.bitvector);
    expect(app.parsed?.domain).toBe('bitvector');
    expect(app.parsed?.examples).toHaveLength(2);
  });

  it('switches domain by loading that domain’s sample', () => {
    const app = new AppState(fakeFetch({}));
    app.setDomain('string');
    expect(app.parsed?.domain).toBe('string');
    expect(app.selected).toBe('sample:string');
    app.setDomain('bitvector');
    expect(app.problem).toBe(SAMPLES.bitvector);
  });

  it('lists corpora and result rows from the API', async () => {
    const results = [{ corpus: 'duet', config: 'hope_h3', total: 24, solved: 3, validated: 3, mean_seconds_solved: 1.2, total_nodes: 99 }];
    const app = new AppState(fakeFetch({ '/api/benchmarks': { corpora: { duet: ['a.sl', 'b.sl'] } }, '/api/results': { results } }));
    await app.loadLists();
    expect(app.corpora).toEqual({ duet: ['a.sl', 'b.sl'] });
    expect(app.results).toEqual(results);
  });

  it('survives an unreachable API with empty lists', async () => {
    const app = new AppState((async () => {
      throw new Error('offline');
    }) as unknown as typeof fetch);
    await app.loadLists();
    expect(app.corpora).toEqual({});
    expect(app.results).toEqual([]);
  });

  it('loads a benchmark file into the editor', async () => {
    const calls: string[] = [];
    const text = '(synth-fun f ((x (BitVec 4))) (BitVec 4) ((Start (BitVec 4) (x))))\n(constraint (= (f #x1) #x1))';
    const app = new AppState(fakeFetch({ '/api/benchmarks/duet/a.sl': { text } }, calls));
    await app.select('duet/a.sl');
    expect(app.problem).toBe(text);
    expect(app.selected).toBe('duet/a.sl');
    expect(calls).toEqual(['/api/benchmarks/duet/a.sl']);
  });

  it('keeps the current problem and reports an error when a benchmark cannot be loaded', async () => {
    const app = new AppState(fakeFetch({}));
    const before = app.problem;
    await app.select('duet/missing.sl');
    expect(app.problem).toBe(before);
    expect(app.loadError).toContain('missing.sl');
  });

  it('describes the policy for the top bar', () => {
    const app = new AppState(fakeFetch({}));
    expect(app.metaEnabled).toBe(true);
    app.config.policy = 'leftmost';
    expect(app.metaEnabled).toBe(false);
  });
});
