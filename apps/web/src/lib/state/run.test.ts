import { describe, expect, it } from 'vitest';
import type { RunConfig, SynthEvent } from '../types';
import { RunState } from './run.svelte';

class FakeSocket {
  static last: FakeSocket;
  sent: string[] = [];
  onmessage: ((e: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  constructor(public url: string) {
    FakeSocket.last = this;
  }
  send(s: string) {
    this.sent.push(s);
  }
  close() {
    this.onclose?.();
  }
  push(e: SynthEvent) {
    this.onmessage?.({ data: JSON.stringify(e) });
  }
}

const cfg: RunConfig = { policy: 'hope', max_holes: 2, max_nodes: 1000, timeout_s: 5, seed: 0 };
const ev = (seq: number, kind: string, payload: Record<string, unknown> = {}): SynthEvent => ({
  schema_version: 1,
  run_id: 'r1',
  seq,
  kind,
  payload
});

function make(ok = true) {
  const calls: { url: string; init?: RequestInit }[] = [];
  const fetch = (async (url: string, init?: RequestInit) => {
    calls.push({ url, init });
    return { ok, status: ok ? 200 : 422, json: async () => (ok ? { run_id: 'r1' } : { detail: 'bad' }) };
  }) as unknown as typeof globalThis.fetch;
  const state = new RunState({ fetch, WebSocket: FakeSocket as unknown as typeof WebSocket });
  return { state, calls };
}

describe('RunState', () => {
  it('starts a run, streams events in order and ends in a terminal status', async () => {
    const { state, calls } = make();
    await state.start('(synth-fun ...)', cfg);
    expect(calls[0].url).toBe('/api/runs');
    expect(JSON.parse(String(calls[0].init?.body)).config.max_holes).toBe(2);
    expect(state.status).toBe('running');
    const ws = FakeSocket.last;
    expect(ws.url).toContain('/api/runs/r1/ws');
    ws.push(ev(0, 'search_started'));
    ws.push(ev(1, 'candidate_expanded', { program: '(bvadd □:S □:S)', holes: 2 }));
    ws.push(ev(2, 'pruned', { position: [0], count: 4, reason: 'component' }));
    ws.push(ev(4, 'solution_found', { program: '(bvadd x 1)' }));
    ws.push(ev(5, 'run_finished', { status: 'solved', nodes: 3 }));
    expect(state.events.map((e) => e.seq)).toEqual([0, 1, 2, 4, 5]);
    expect(state.explored).toBe(1);
    expect(state.pruned).toBe(4);
    expect(state.best).toBe('(bvadd x 1)');
    expect(state.current).toBe('(bvadd □:S □:S)');
    expect(state.status).toBe('solved');
  });

  it('ignores duplicate or stale events', async () => {
    const { state } = make();
    await state.start('p', cfg);
    const ws = FakeSocket.last;
    ws.push(ev(0, 'search_started'));
    ws.push(ev(1, 'candidate_expanded', { program: 'a' }));
    ws.push(ev(1, 'candidate_expanded', { program: 'dup' }));
    ws.push(ev(0, 'search_started'));
    expect(state.events).toHaveLength(2);
    expect(state.current).toBe('a');
  });

  it('marks a dropped connection and resumes without duplicating events', async () => {
    const { state } = make();
    await state.start('p', cfg);
    const first = FakeSocket.last;
    first.push(ev(0, 'search_started'));
    first.push(ev(1, 'candidate_expanded', { program: 'a' }));
    first.close();
    expect(state.status).toBe('disconnected');
    state.reconnect();
    const second = FakeSocket.last;
    expect(second).not.toBe(first);
    expect(state.status).toBe('running');
    second.push(ev(0, 'search_started')); // server replays history
    second.push(ev(1, 'candidate_expanded', { program: 'a' }));
    second.push(ev(2, 'run_finished', { status: 'exhausted', nodes: 1 }));
    expect(state.events).toHaveLength(3);
    expect(state.status).toBe('exhausted');
  });

  it('a close after the run finished stays terminal', async () => {
    const { state } = make();
    await state.start('p', cfg);
    FakeSocket.last.push(ev(0, 'run_finished', { status: 'timeout', nodes: 9 }));
    FakeSocket.last.close();
    expect(state.status).toBe('timeout');
  });

  it('cancel sends the websocket command', async () => {
    const { state } = make();
    await state.start('p', cfg);
    state.cancel();
    expect(FakeSocket.last.sent.map((s) => JSON.parse(s))).toEqual([{ cmd: 'cancel' }]);
  });

  it('reports a rejected request without opening a socket', async () => {
    const { state } = make(false);
    await state.start('p', cfg);
    expect(state.status).toBe('error');
    expect(state.error).toContain('bad');
  });

  it('tracks the latest hole ranking', async () => {
    const { state } = make();
    await state.start('p', cfg);
    FakeSocket.last.push(ev(0, 'hole_ranked', { rank1: [[[0, 0], [0, 1]]], rank2: [], picked: [[0, 0], [0, 1]], noprune: false }));
    expect(state.ranks?.picked).toEqual([[0, 0], [0, 1]]);
  });

  it('replay rebuilds the same state as the live run', async () => {
    const live = make().state;
    await live.start('p', cfg);
    const evs = [
      ev(0, 'search_started'),
      ev(1, 'candidate_expanded', { program: 'a' }),
      ev(2, 'pruned', { count: 2, reason: 'component' }),
      ev(3, 'solution_found', { program: 'b' }),
      ev(4, 'run_finished', { status: 'solved', nodes: 2 })
    ];
    evs.forEach((e) => FakeSocket.last.push(e));
    const replayed = new RunState();
    replayed.replay(evs);
    expect([replayed.explored, replayed.pruned, replayed.best, replayed.status]).toEqual([
      live.explored,
      live.pruned,
      live.best,
      live.status
    ]);
    expect(replayed.series.at(-1)).toEqual(live.series.at(-1));
  });
});

describe('RunState run identity', () => {
  it('ignores events from another run', () => {
    const { state } = make();
    state.runId = 'r1';
    state.apply({ ...ev(0, 'candidate_expanded', { program: 'x' }), run_id: 'other' });
    expect(state.events.length).toBe(0);
  });

  it('closes the previous socket when a new run starts', async () => {
    const { state } = make();
    await state.start('p', cfg);
    const first = FakeSocket.last;
    let closed = false;
    first.close = () => {
      closed = true;
    };
    await state.start('p', cfg);
    expect(closed).toBe(true);
  });

  it('replays a recording even after a live run with another id', async () => {
    const { state } = make();
    await state.start('p', cfg);
    state.replay([{ ...ev(0, 'candidate_expanded', { program: 'x' }), run_id: 'recorded' }]);
    expect(state.events.length).toBe(1);
  });
});

describe('RunState derived views', () => {
  const at = (seq: number, t: number, kind: string, payload: Record<string, unknown> = {}): SynthEvent => ({
    ...ev(seq, kind, payload),
    t
  });

  it('follows event time for elapsed time and the progress series', () => {
    const s = new RunState();
    s.apply(at(0, 0, 'search_started'));
    s.apply(at(1, 0.013, 'candidate_expanded', { program: 'a', id: 0, parent: null, holes: 1 }));
    s.apply(at(2, 0.177, 'pruned', { count: 3, reason: 'component' }));
    expect(s.elapsed).toBeCloseTo(0.177);
    expect(s.series.at(-1)).toMatchObject({ t: 0.177, explored: 1, pruned: 3 });
  });

  it('builds the candidate tree with depths and marks infeasible candidates', () => {
    const s = new RunState();
    s.apply(at(0, 0, 'candidate_expanded', { program: '□:S', id: 0, parent: null, holes: 1 }));
    s.apply(at(1, 0.1, 'candidate_expanded', { program: '(f □:S)', id: 3, parent: 0, holes: 1 }));
    s.apply(at(2, 0.2, 'candidate_expanded', { program: '(f (f □:S))', id: 5, parent: 3, holes: 1 }));
    s.apply(at(3, 0.3, 'pruned', { program: '(f (f □:S))', reason: 'infeasible' }));
    expect(s.candidates.map((c) => [c.id, c.parent, c.depth, c.status])).toEqual([
      [0, null, 0, 'expanded'],
      [3, 0, 1, 'expanded'],
      [5, 3, 2, 'pruned']
    ]);
    expect(s.maxDepth).toBe(2);
  });

  it('keeps the latest abstract state and counts a solved run', () => {
    const s = new RunState();
    const nodes = [{ path: [], label: 'bvadd', state: '#x4' }];
    s.apply(at(0, 0, 'analysis', { inputs: { x: 3 }, output: 4, infeasible: false, nodes }));
    expect(s.analysis?.nodes).toEqual(nodes);
    expect(s.analysis?.inputs).toEqual({ x: 3 });
  });

  it('tolerates events without time or ids (older servers)', () => {
    const s = new RunState();
    s.apply(ev(0, 'candidate_expanded', { program: 'a' }));
    expect(s.elapsed).toBe(0);
    expect(s.candidates).toHaveLength(1);
    expect(s.candidates[0].parent).toBeNull();
  });
});
