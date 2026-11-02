import { callSyntax } from './holes';
import { parseProgram } from './sexpr';
import type { IconName } from './components/Icon.svelte';
import type { SynthEvent } from './types';

export interface LogLine {
  icon: IconName;
  title: string;
  detail: string;
  tone: 'neutral' | 'good' | 'bad' | 'info';
}
export interface LogContext {
  /** Depth of the candidate with this queue id, when known. */
  depthOf: (id: unknown) => number;
}

function readable(program: unknown): string {
  const text = String(program ?? '');
  try {
    return callSyntax(parseProgram(text));
  } catch {
    return text;
  }
}

const plural = (n: number, one: string, many = `${one}s`): string => `${n} ${n === 1 ? one : many}`;
const list = (v: unknown): unknown[] => (Array.isArray(v) ? v : []);

export function describeEvent(e: SynthEvent, ctx: LogContext): LogLine {
  const p = e.payload;
  switch (e.kind) {
    case 'search_started':
      return { icon: 'play', title: 'Start synthesis', detail: `start symbol ${String(p.start ?? '')}`, tone: 'neutral' };
    case 'candidate_expanded':
      return { icon: 'plus', title: `Candidate expansion (depth = ${ctx.depthOf(p.id)})`, detail: readable(p.program), tone: 'neutral' };
    case 'analysis': {
      const n = list(p.nodes).length;
      return {
        icon: 'search',
        title: 'Abstract analysis',
        detail: `${plural(n, 'node')}, ${p.infeasible ? 'empty abstract state (⊥)' : 'feasible'}`,
        tone: p.infeasible ? 'bad' : 'info'
      };
    }
    case 'hole_ranked': {
      const noprune = p.noprune ? ' · no pruning possible' : '';
      return {
        icon: 'zap',
        title: 'Hole ranking',
        detail: `picked ${plural(list(p.picked).length, 'hole')} · ${plural(list(p.rank1).length, 'rank-1 set')}, ${plural(list(p.rank2).length, 'rank-2 set')}${noprune}`,
        tone: 'info'
      };
    }
    case 'pruned':
      if (p.reason === 'infeasible') return { icon: 'xcircle', title: 'Prune (infeasible)', detail: 'Discard candidate: no program can satisfy the examples', tone: 'bad' };
      return {
        icon: 'xcircle',
        title: 'Prune (components)',
        detail: `Discard ${plural(Number(p.count ?? 1), 'component')} that ${Number(p.count ?? 1) === 1 ? 'contradicts' : 'contradict'} the examples`,
        tone: 'bad'
      };
    case 'hole_filled':
      return {
        icon: 'refresh',
        title: 'Fill holes',
        detail: `at ${list(p.positions).map((q) => (Array.isArray(q) && q.length ? q.join('.') : 'root')).join(', ')}`,
        tone: 'neutral'
      };
    case 'solution_found':
      return { icon: 'check', title: 'Solution found', detail: readable(p.program), tone: 'good' };
    case 'run_finished':
      return { icon: 'clock', title: `Run finished: ${String(p.status)}`, detail: `${Number(p.nodes ?? 0)} nodes expanded`, tone: p.status === 'solved' ? 'good' : 'neutral' };
    default:
      return { icon: 'info', title: e.kind, detail: '', tone: 'neutral' };
  }
}
