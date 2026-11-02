import { parseProblem } from '../problem';
import type { RunConfig } from '../types';

export const SAMPLES = {
  bitvector: `(set-logic BV)
(synth-fun f ((x (BitVec 4))) (BitVec 4)
  ((Start (BitVec 4) (x #x1 (bvand Start Start) (bvadd Start Start) (bvnot Start)))))
(constraint (= (f #b1011) #b1000))
(constraint (= (f #b0111) #b0000))
(check-synth)
`,
  string: `(set-logic SLIA)
(synth-fun f ((first String) (last String)) String
  ((Start String (first last "." (str.++ Start Start Start) (str.at Start Idx)))
   (Idx Int (0 1))))
(constraint (= (f "Jan" "Kotas") "J.K"))
(constraint (= (f "Marie" "Curie") "M.C"))
(check-synth)
`
} as const;

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
  selected = $state('sample:bitvector');
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
    this.problem = SAMPLES[domain];
    this.selected = `sample:${domain}`;
    this.loadError = null;
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

  /** `sample:bitvector`, `sample:string`, or `corpus/file.sl`. */
  async select(value: string): Promise<void> {
    if (value.startsWith('sample:')) {
      this.setDomain(value === 'sample:string' ? 'string' : 'bitvector');
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
