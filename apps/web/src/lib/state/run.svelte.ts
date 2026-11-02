import type { AnalysisPayload, Candidate, HoleRanks, RunConfig, RunStatus, SynthEvent } from '../types';

export interface Deps {
  fetch: typeof fetch;
  WebSocket: typeof WebSocket;
}

export interface Point {
  seq: number;
  t: number;
  explored: number;
  pruned: number;
}

const TERMINAL = new Set<RunStatus>(['solved', 'exhausted', 'timeout', 'unsupported', 'cancelled', 'error']);

/** Run state fed only by engine events (live over the websocket, or replayed from a recording). */
export class RunState {
  events = $state<SynthEvent[]>([]);
  status = $state<RunStatus>('idle');
  runId = $state<string | null>(null);
  error = $state<string | null>(null);
  best = $state<string | null>(null);
  current = $state<string | null>(null);
  ranks = $state<HoleRanks | null>(null);
  nodes = $state<number | null>(null);
  explored = $state(0);
  pruned = $state(0);
  series = $state<Point[]>([]);
  elapsed = $state(0);
  maxDepth = $state(0);
  candidates = $state<Candidate[]>([]);
  analysis = $state<AnalysisPayload | null>(null);

  private lastSeq = -1;
  private depthOf = new Map<number, number>();
  private ws: WebSocket | null = null;
  private deps: Deps;

  constructor(deps?: Deps) {
    this.deps = deps ?? { fetch: globalThis.fetch?.bind(globalThis), WebSocket: globalThis.WebSocket };
  }

  private reset() {
    this.events = [];
    this.status = 'idle';
    this.error = null;
    this.best = null;
    this.current = null;
    this.ranks = null;
    this.nodes = null;
    this.explored = 0;
    this.pruned = 0;
    this.series = [];
    this.elapsed = 0;
    this.maxDepth = 0;
    this.candidates = [];
    this.analysis = null;
    this.depthOf = new Map();
    this.lastSeq = -1;
  }

  /** Apply one event; duplicates and stale sequence numbers (e.g. a replayed history) are ignored. */
  apply(e: SynthEvent) {
    if (this.runId !== null && e.run_id !== this.runId) return;
    if (e.seq <= this.lastSeq) return;
    this.lastSeq = e.seq;
    this.events.push(e);
    const p = e.payload;
    switch (e.kind) {
      case 'candidate_expanded': {
        this.explored += 1;
        this.current = String(p.program ?? '');
        const id = typeof p.id === 'number' ? p.id : this.candidates.length;
        const parent = typeof p.parent === 'number' ? p.parent : null;
        const depth = parent === null ? 0 : (this.depthOf.get(parent) ?? 0) + 1;
        this.depthOf.set(id, depth);
        this.maxDepth = Math.max(this.maxDepth, depth);
        this.candidates.push({ id, parent, program: this.current, holes: Number(p.holes ?? 0), depth, status: 'expanded' });
        break;
      }
      case 'pruned':
        this.pruned += typeof p.count === 'number' ? p.count : 1;
        if (p.reason === 'infeasible' && this.candidates.length > 0) this.candidates[this.candidates.length - 1].status = 'pruned';
        break;
      case 'analysis':
        this.analysis = p as unknown as AnalysisPayload;
        break;
      case 'hole_ranked':
        this.ranks = p as unknown as HoleRanks;
        break;
      case 'solution_found':
        this.best = String(p.program ?? '');
        break;
      case 'run_finished':
        this.status = String(p.status) as RunStatus;
        this.nodes = typeof p.nodes === 'number' ? p.nodes : null;
        break;
    }
    if (typeof e.t === 'number') this.elapsed = e.t;
    this.series.push({ seq: e.seq, t: this.elapsed, explored: this.explored, pruned: this.pruned });
  }

  replay(events: SynthEvent[]) {
    this.ws?.close();
    this.ws = null;
    this.runId = null;
    this.reset();
    this.status = 'running';
    for (const e of events) this.apply(e);
    if (!TERMINAL.has(this.status)) this.status = 'idle';
  }

  async start(problem: string, config: RunConfig) {
    this.ws?.close();
    this.ws = null;
    this.runId = null;
    this.reset();
    this.status = 'running';
    try {
      const res = await this.deps.fetch('/api/runs', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ problem, config })
      });
      const body = await res.json();
      if (!res.ok) {
        this.status = 'error';
        this.error = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail);
        return;
      }
      this.runId = body.run_id;
      this.connect();
    } catch (err) {
      this.status = 'error';
      this.error = err instanceof Error ? err.message : String(err);
    }
  }

  private connect() {
    const scheme = globalThis.location?.protocol === 'https:' ? 'wss' : 'ws';
    const host = globalThis.location?.host ?? 'localhost';
    const ws = new this.deps.WebSocket(`${scheme}://${host}/api/runs/${this.runId}/ws`);
    this.ws = ws;
    ws.onmessage = (m: MessageEvent | { data: string }) => this.apply(JSON.parse(String(m.data)) as SynthEvent);
    ws.onclose = () => {
      if (this.ws === ws && !TERMINAL.has(this.status)) this.status = 'disconnected';
    };
  }

  /** Reopen the stream for the current run; the server replays history and duplicates are dropped. */
  reconnect() {
    if (this.runId === null || TERMINAL.has(this.status)) return;
    this.status = 'running';
    this.connect();
  }

  cancel() {
    this.ws?.send(JSON.stringify({ cmd: 'cancel' }));
  }
}
