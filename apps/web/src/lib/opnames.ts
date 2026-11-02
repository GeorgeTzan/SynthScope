/** Plain-English names for the engine's operators, so the graph can say "multiply" instead of "bvmul". */
export interface OpName {
  name: string;
  symbol: string;
}

const NAMES: Record<string, OpName> = {
  bvadd: { name: 'add', symbol: '+' },
  bvsub: { name: 'subtract', symbol: '−' },
  bvmul: { name: 'multiply', symbol: '×' },
  bvudiv: { name: 'divide', symbol: '÷' },
  bvurem: { name: 'remainder', symbol: '%' },
  bvsdiv: { name: 'signed divide', symbol: '÷' },
  bvsrem: { name: 'signed remainder', symbol: '%' },
  bvand: { name: 'bitwise and', symbol: '&' },
  bvor: { name: 'bitwise or', symbol: '|' },
  bvxor: { name: 'bitwise xor', symbol: '^' },
  bvnot: { name: 'bitwise not', symbol: '~' },
  bvneg: { name: 'negate', symbol: '−x' },
  bvshl: { name: 'shift left', symbol: '<<' },
  bvlshr: { name: 'shift right', symbol: '>>' },
  bvashr: { name: 'arithmetic shift', symbol: '>>' },
  ite: { name: 'if / else', symbol: '?:' },
  '=': { name: 'equals', symbol: '==' },
  and: { name: 'and', symbol: '&&' },
  or: { name: 'or', symbol: '||' },
  not: { name: 'not', symbol: '!' },
  '+': { name: 'add', symbol: '+' },
  '-': { name: 'subtract', symbol: '−' },
  'str.++': { name: 'join text', symbol: '+' },
  ConCat: { name: 'join text', symbol: '+' },
  'str.at': { name: 'character at', symbol: '[i]' },
  CharAt0: { name: 'first character', symbol: '[0]' },
  'str.substr': { name: 'substring', symbol: '[a:b]' },
  'str.len': { name: 'length', symbol: 'len' },
  'str.indexof': { name: 'find position', symbol: 'find' },
  'str.replace': { name: 'replace', symbol: 'replace' },
  'str.prefixof': { name: 'starts with', symbol: 'starts' },
  'str.suffixof': { name: 'ends with', symbol: 'ends' },
  'str.contains': { name: 'contains', symbol: 'in' },
  'str.to.int': { name: 'text to number', symbol: 'int' },
  'int.to.str': { name: 'number to text', symbol: 'str' }
};

/** Friendly name for an operator, or the raw label when there is none (unknown operators stay readable). */
export function opName(label: string): OpName {
  return NAMES[label] ?? { name: label, symbol: label };
}
