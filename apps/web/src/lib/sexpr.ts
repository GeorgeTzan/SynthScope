import type { Tree } from './types';

const TOKEN = /\(|\)|"(?:[^"]|"")*"|[^\s()]+/g;

/** Parse the engine's `pretty()` output, e.g. `(bvadd □:S (bvnot x))`, into a tree. Holes print as □:Nonterminal. */
export function parseProgram(text: string): Tree {
  const tokens = text.match(TOKEN) ?? [];
  let i = 0;
  function node(): Tree {
    const t = tokens[i++];
    if (t === undefined) throw new Error('unexpected end of program text');
    if (t === '(') {
      const head = tokens[i++];
      if (head === undefined || head === '(' || head === ')') throw new Error('operator name expected');
      const children: Tree[] = [];
      while (tokens[i] !== ')') {
        if (tokens[i] === undefined) throw new Error('missing )');
        children.push(node());
      }
      i++;
      return { label: head, hole: null, children };
    }
    if (t === ')') throw new Error('unexpected )');
    if (t.startsWith('□:')) return { label: '□', hole: t.slice(2), children: [] };
    return { label: t, hole: null, children: [] };
  }
  const tree = node();
  if (i !== tokens.length) throw new Error('trailing tokens');
  return tree;
}
