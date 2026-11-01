import type { HoleRanks, RunConfig, RunStatus, SynthEvent } from '../types';

export interface Deps {
  fetch: typeof fetch;
  WebSocket: typeof WebSocket;
}

export interface Point {
  seq: number;
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

  private lastSeq = -1;
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
    this.lastSeq = -1;
  }

  /** Apply one event; duplicates and stale sequence numbers (e.g. a replayed history) are ignored. */
  apply(e: SynthEvent) {
    if (e.seq <= this.lastSeq) return;
    this.lastSeq = e.seq;
    this.events.push(e);
    const p = e.payload;
    switch (e.kind) {
      case 'candidate_expanded':
        this.explored += 1;
        this.current = String(p.program ?? '');
        break;
      case 'pruned':
        this.pruned += typeof p.count === 'number' ? p.count : 1;
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
    this.series.push({ seq: e.seq, explored: this.explored, pruned: this.pruned });
  }

  replay(events: SynthEvent[]) {
    this.reset();
    this.status = 'running';
    for (const e of events) this.apply(e);
    if (!TERMINAL.has(this.status)) this.status = 'idle';
  }

  async start(problem: string, config: RunConfig) {
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
