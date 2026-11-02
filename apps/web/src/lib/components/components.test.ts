import { fireEvent, render, screen } from '@testing-library/svelte';
import { beforeAll, describe, expect, it } from 'vitest';
import { parseProblem } from '../problem';
import { SAMPLES } from '../state/app.svelte';
import type { SynthEvent } from '../types';
import AstGraph from './AstGraph.svelte';
import BenchmarkSummary from './BenchmarkSummary.svelte';
import BestCandidate from './BestCandidate.svelte';
import ExamplesPanel from './ExamplesPanel.svelte';
import GrammarPanel from './GrammarPanel.svelte';
import Statistics from './Statistics.svelte';
import ProblemDialog from './ProblemDialog.svelte';
import SynthLog from './SynthLog.svelte';

const ev = (seq: number, kind: string, payload: Record<string, unknown>): SynthEvent => ({
  schema_version: 1,
  run_id: 'r',
  seq,
  kind,
  payload
});

describe('AstGraph', () => {
  beforeAll(() => {
    // jsdom has no ResizeObserver; the graph only uses it to fit the view
    globalThis.ResizeObserver ??= class {
      observe() {}
      unobserve() {}
      disconnect() {}
    };
  });
  it('draws operators, leaves and holes from the engine program text', () => {
    render(AstGraph, { program: '(bvadd □:S (bvnot x))', ranks: null });
    expect(screen.getByText('add')).toBeTruthy();
    expect(screen.getByText('bitwise not')).toBeTruthy();
    expect(screen.getByText('bvadd')).toBeTruthy(); // raw operator kept as a caption
    expect(screen.getByText('x')).toBeTruthy();
    expect(screen.getByLabelText('Holes')).toBeTruthy();
  });
  it('shows a prompt before any candidate', () => {
    render(AstGraph, { program: null, ranks: null });
    expect(screen.getByText(/press run/i)).toBeTruthy();
  });
  it('says so when the program text cannot be parsed', () => {
    render(AstGraph, { program: '(bvadd', ranks: null });
    expect(screen.getByRole('alert').textContent).toMatch(/cannot draw program/i);
  });
});

describe('ExamplesPanel and GrammarPanel', () => {
  const problem = parseProblem(SAMPLES.bitvector);
  it('lists the examples of a parsed problem', () => {
    render(ExamplesPanel, { problem, onedit: () => {} });
    expect(screen.getByText('Input')).toBeTruthy();
    expect(screen.getByText('Output')).toBeTruthy();
  });
  it('lists operators and variables of the grammar', () => {
    render(GrammarPanel, { problem });
    expect(screen.getByText('bvmul')).toBeTruthy();
    expect(screen.getByText(/Operators \(/)).toBeTruthy();
  });
  it('handles a missing problem', () => {
    render(GrammarPanel, { problem: null });
    expect(screen.getByText(/no grammar/i)).toBeTruthy();
  });
});

describe('SynthLog', () => {
  it('renders one line per event and the elapsed time', () => {
    render(SynthLog, {
      entries: [ev(1, 'run_started', { policy: 'hope' }), ev(2, 'solution_found', { program: '(bvnot x)' })],
      status: 'solved',
      elapsed: 0.5
    });
    expect(screen.getAllByRole('listitem').length).toBeGreaterThanOrEqual(2);
  });
  it('is empty and idle without events', () => {
    render(SynthLog, { entries: [], status: 'idle', elapsed: 0 });
    expect(screen.getByText('Idle')).toBeTruthy();
  });
});

describe('BestCandidate, Statistics, BenchmarkSummary', () => {
  it('shows the solution call', () => {
    render(BestCandidate, { program: '(bvnot x)', status: 'solved', signature: 'f(x)', python: 'def f(x):\n    return ~x & 15' });
    expect(screen.getByText('bvnot')).toBeTruthy();
    expect(screen.getByLabelText('Python').textContent).toContain('def f(x)');
  });
  it('shows counters and the pruned share', () => {
    render(Statistics, { explored: 10, pruned: 30, elapsed: 1.5, maxDepth: 3, nodes: 40 });
    expect(screen.getByText(/75/)).toBeTruthy();
  });
  it('shows an empty state without results and grouped rows with them', () => {
    const { unmount } = render(BenchmarkSummary, { rows: [] });
    expect(screen.getByText(/no benchmark runs/i)).toBeTruthy();
    unmount();
    render(BenchmarkSummary, {
      rows: [{ corpus: 'duet', config: 'hope_h1', total: 24, solved: 5, validated: 5, mean_seconds_solved: 3.4, total_nodes: 100 }]
    });
    expect(screen.getByText('String (Duet)')).toBeTruthy();
    expect(screen.getByText('HOPE, 1 hole')).toBeTruthy();
  });
});

describe('ProblemDialog numbers tab', () => {
  beforeAll(() => {
    // jsdom has no modal dialogs
    HTMLDialogElement.prototype.showModal ??= function (this: HTMLDialogElement) {
      this.setAttribute('open', '');
    };
    HTMLDialogElement.prototype.close ??= function (this: HTMLDialogElement) {
      this.removeAttribute('open');
    };
  });
  it('offers the number inputs with the squares example prefilled', () => {
    render(ProblemDialog, { open: true, problem: '' });
    expect(screen.getByRole('tab', { name: 'Numbers' })).toBeTruthy();
    expect((screen.getByRole('checkbox', { name: /bvmul/ }) as HTMLInputElement).checked).toBe(true);
    expect((screen.getByRole('textbox', { name: /examples/i }) as HTMLTextAreaElement).value).toContain('3 -> 9');
  });
  it('explains a bad example instead of closing', async () => {
    render(ProblemDialog, { open: true, problem: '' });
    const box = screen.getByRole('textbox', { name: /examples/i }) as HTMLTextAreaElement;
    await fireEvent.input(box, { target: { value: '2 -> x' } });
    await fireEvent.click(screen.getByRole('button', { name: /use these examples/i }));
    expect(screen.getByRole('alert').textContent).toMatch(/Example 1/);
  });
});
