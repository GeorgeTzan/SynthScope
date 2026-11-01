export interface SynthEvent {
  schema_version: number;
  run_id: string;
  seq: number;
  kind: string;
  payload: Record<string, unknown>;
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
