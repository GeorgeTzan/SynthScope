export interface SynthEvent {
  schema_version: number;
  run_id: string;
  seq: number;
  kind: string;
  payload: Record<string, unknown>;
  /** Seconds since the run started (absent on older servers). */
  t?: number;
}

/** One node of the candidate tree: a partial program the search expanded, and where it came from. */
export interface Candidate {
  id: number;
  parent: number | null;
  program: string;
  holes: number;
  depth: number;
  status: 'expanded' | 'pruned';
}

/** Payload of an `analysis` event: the abstract value of every node of a partial program, for one example. */
export interface AnalysisNode {
  path: number[];
  label: string;
  state: string;
}
export interface AnalysisPayload {
  inputs: Record<string, number | string>;
  output: number | string | null;
  infeasible: boolean;
  nodes: AnalysisNode[];
}

export type RunStatus =
  | 'idle'
  | 'running'
  | 'solved'
  | 'exhausted'
  | 'timeout'
  | 'unsupported'
  | 'cancelled'
  | 'error'
  | 'disconnected';

export interface RunConfig {
  policy: 'hope' | 'leftmost' | 'meta_off';
  max_holes: number;
  max_nodes: number;
  timeout_s: number;
  seed: number;
}

/** Payload of a `hole_ranked` event: sets of positions (each position is a path of child indexes). */
export interface HoleRanks {
  rank1: number[][][];
  rank2: number[][][];
  picked: number[][];
  noprune: boolean;
}

export interface Tree {
  label: string;
  hole: string | null;
  children: Tree[];
}

/** One example evaluated by the engine: the value at every node of the solved program, keyed by dotted child path ('' = root). */
export interface EvaluatedExample {
  inputs: Record<string, number | string>;
  expected: number | string;
  values: Record<string, number | string | null>;
}
