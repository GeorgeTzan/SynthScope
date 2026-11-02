import { DEFAULT_EXAMPLE, EXAMPLES } from '../examples';
import { parseProblem } from '../problem';
import type { RunConfig } from '../types';

const example = (id: string): string => EXAMPLES.find((e) => e.id === id)?.text ?? '';
export const SAMPLES = { bitvector: example('square'), string: example('initials') } as const;

export interface ResultRow {
  corpus: string;
  config: string;
  total: number;
  solved: number;
  validated: number;
  mean_seconds_solved: number | null;
  total_nodes: number;
}

/** Problem text, run configuration and the benchmark picker. The live run itself lives in RunState. */
export class AppState {
  problem = $state<string>(SAMPLES.bitvector);
  selected = $state(`example:${DEFAULT_EXAMPLE}`);
  config = $state<RunConfig>({ policy: 'hope', max_holes: 3, max_nodes: 50000, timeout_s: 30, seed: 0 });
  corpora = $state<Record<string, string[]>>({});
  results = $state<ResultRow[]>([]);
  loadError = $state<string | null>(null);

  parsed = $derived(parseProblem(this.problem));
  metaEnabled = $derived(this.config.policy === 'hope');

  private fetcher: typeof fetch;

  constructor(fetcher?: typeof fetch) {
    this.fetcher = fetcher ?? globalThis.fetch.bind(globalThis);
  }

  setDomain(domain: 'bitvector' | 'string'): void {
    const first = EXAMPLES.find((e) => e.domain === domain);
    if (first) this.pickExample(first.id);
  }

  async loadLists(): Promise<void> {
    try {
      const [b, r] = await Promise.all([this.fetcher('/api/benchmarks'), this.fetcher('/api/results')]);
      this.corpora = b.ok ? ((await b.json()) as { corpora: Record<string, string[]> }).corpora : {};
      this.results = r.ok ? ((await r.json()) as { results: ResultRow[] }).results : [];
    } catch {
      this.corpora = {};
      this.results = [];
    }
  }

  pickExample(id: string): void {
    const found = EXAMPLES.find((e) => e.id === id);
    if (!found) return;
    this.problem = found.text;
    this.selected = `example:${id}`;
    this.loadError = null;
  }

  /** `example:<id>`, or `corpus/file.sl`. */
  async select(value: string): Promise<void> {
    if (value.startsWith('example:')) {
      this.pickExample(value.slice('example:'.length));
      return;
    }
    const [corpus, name] = value.split('/');
    try {
      const res = await this.fetcher(`/api/benchmarks/${encodeURIComponent(corpus)}/${encodeURIComponent(name)}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      this.problem = ((await res.json()) as { text: string }).text;
      this.selected = value;
      this.loadError = null;
    } catch {
      this.loadError = `Could not load ${name}`;
    }
  }
}
