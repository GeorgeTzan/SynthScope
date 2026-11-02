import type { Tree } from './types';

export interface LaidOutNode {
  path: number[];
  label: string;
  hole: string | null;
  parent: number | null;
  x: number;
  y: number;
  w: number;
  h: number;
}
export interface Layout {
  nodes: LaidOutNode[];
  width: number;
  height: number;
}

const NODE_H = 44;
const ROW_GAP = 64;
const COL_GAP = 28;
const PAD = 24;

function nodeWidth(t: Tree): number {
  const text = t.hole ? `□ ${t.hole}` : t.label;
  const icon = t.children.length > 0 ? 28 : 0; // operators carry a cube icon before the label
  return Math.max(56, 28 + icon + text.length * 9.5);
}

/** Tidy top-down tree layout: leaves take successive slots, a parent is centred over its children. */
export function layoutTree(root: Tree): Layout {
  const nodes: LaidOutNode[] = [];
  let cursor = PAD;
  let maxDepth = 0;

  function place(t: Tree, path: number[], parent: number | null, depth: number): { index: number; x: number } {
    maxDepth = Math.max(maxDepth, depth);
    const index = nodes.length;
    const w = nodeWidth(t);
    nodes.push({ path, label: t.label, hole: t.hole, parent, x: 0, y: PAD + depth * (NODE_H + ROW_GAP), w, h: NODE_H });
    if (t.children.length === 0) {
      nodes[index].x = cursor + w / 2;
      cursor += w + COL_GAP;
    } else {
      const xs = t.children.map((c, i) => place(c, [...path, i], index, depth + 1).x);
      nodes[index].x = (xs[0] + xs[xs.length - 1]) / 2;
      // a wide label over narrow children must not hang off the left edge
      const left = nodes[index].x - w / 2;
      if (left < PAD) shift(index, PAD - left);
    }
    return { index, x: nodes[index].x };
  }

  function shift(index: number, dx: number): void {
    for (let i = index; i < nodes.length; i++) nodes[i].x += dx;
    cursor += dx;
  }

  place(root, [], null, 0);
  const right = Math.max(...nodes.map((n) => n.x + n.w / 2));
  return { nodes, width: right + PAD, height: PAD + (maxDepth + 1) * NODE_H + maxDepth * ROW_GAP + PAD };
}
