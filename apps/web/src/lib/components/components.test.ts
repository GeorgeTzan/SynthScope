import { render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import type { SynthEvent } from '../types';
import AstView from './AstView.svelte';
import BestCandidate from './BestCandidate.svelte';
import HolesPanel from './HolesPanel.svelte';
import ProgressChart from './ProgressChart.svelte';
import Stats from './Stats.svelte';
import SynthLog from './SynthLog.svelte';

const ev = (seq: number, kind: string, payload: Record<string, unknown>): SynthEvent => ({
  schema_version: 1,
  run_id: 'r',
  seq,
  kind,
  payload
});

describe('AstView', () => {
  it('draws operators, leaves and holes from the engine program text', () => {
    render(AstView, { program: '(bvadd □:S (bvnot x))' });
    expect(screen.getByText('bvadd')).toBeTruthy();
    expect(screen.getByText('bvnot')).toBeTruthy();
    expect(screen.getByText('x')).toBeTruthy();
    expect(screen.getAllByLabelText('hole S')).toHaveLength(1);
  });
  it('shows a placeholder before any candidate and an error for unparseable text', () => {
    const { unmount } = render(AstView, { program: null });
    expect(screen.getByText(/no candidate yet/i)).toBeTruthy();
    unmount();
    render(AstView, { program: '(broken' });
    expect(screen.getByRole('alert')).toBeTruthy();
  });
});

describe('HolesPanel', () => {
  it('lists ranked hole sets and marks the picked one (engine payload shape)', () => {
    render(HolesPanel, {
      ranks: { rank1: [[[0, 0], [0, 1]]], rank2: [[[1]]], picked: [[0, 0], [0, 1]], noprune: false }
    });
    expect(screen.getByText(/rank 1/i)).toBeTruthy();
    expect(screen.getByText(/rank 2/i)).toBeTruthy();
    expect(screen.getByText(/picked/i).parentElement?.textContent).toContain('0.0 + 0.1');
    expect(screen.queryByText(/no pruning possible/i)).toBeNull();
  });
  it('says so when no ranked hole exists (noprune)', () => {
    render(HolesPanel, { ranks: { rank1: [], rank2: [], picked: [[0]], noprune: true } });
    expect(screen.getByText(/no pruning possible/i)).toBeTruthy();
  });
  it('renders nothing meaningful without ranks', () => {
    render(HolesPanel, { ranks: null });
    expect(screen.getByText(/no ranking yet/i)).toBeTruthy();
  });
});

describe('SynthLog', () => {
  it('shows only the most recent events and keeps their order', () => {
    const events = Array.from({ length: 500 }, (_, i) => ev(i, 'candidate_expanded', { program: `p${i}` }));
    render(SynthLog, { entries: events, limit: 50 });
    expect(screen.queryByText(/p0$/)).toBeNull();
    expect(screen.getByText(/p499$/)).toBeTruthy();
    expect(screen.getAllByRole('listitem')).toHaveLength(50);
  });
});

describe('BestCandidate, Stats, ProgressChart', () => {
  it('shows the solution', () => {
    render(BestCandidate, { program: '(bvadd x 1)', status: 'solved' });
    expect(screen.getByText('(bvadd x 1)')).toBeTruthy();
  });
  it('shows counters', () => {
    render(Stats, { explored: 12, pruned: 30, received: 99, nodes: 77, status: 'running' });
    expect(screen.getByText('12')).toBeTruthy();
    expect(screen.getByText('30')).toBeTruthy();
    expect(screen.getByText('77')).toBeTruthy();
  });
  it('plots one polyline per series', () => {
    const { container } = render(ProgressChart, {
      series: [
        { seq: 0, explored: 0, pruned: 0 },
        { seq: 5, explored: 3, pruned: 1 }
      ]
    });
    expect(container.querySelectorAll('polyline')).toHaveLength(2);
  });
  it('handles an empty series', () => {
    render(ProgressChart, { series: [] });
    expect(screen.getByText(/no data/i)).toBeTruthy();
  });
});
