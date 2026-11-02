/** Read a SyGuS-IF problem for display (examples table, grammar panel). The engine does the real parsing. */

export type SExp = string | SExp[];

export interface Example {
  inputs: string[];
  output: string;
}
export interface OperatorRule {
  name: string;
  args: string[];
  result: string;
}
export interface ConstantRule {
  value: string;
  nonterminal: string;
}
export interface VariableRule {
  name: string;
  sort: string;
}
export interface ParsedProblem {
  domain: 'bitvector' | 'string';
  functionName: string;
  params: VariableRule[];
  returnSort: string;
  start: string;
  examples: Example[];
  /** Name of the reference function when the problem is given as a specification instead of examples. */
  reference: string | null;
  grammar: { operators: OperatorRule[]; constants: ConstantRule[]; variables: VariableRule[] };
}

const TOKEN = /;[^\n]*|\(|\)|"(?:[^"]|"")*"|[^\s()";]+/g;

function read(text: string): SExp[] | null {
  const tokens = (text.match(TOKEN) ?? []).filter((t) => !t.startsWith(';'));
  const stack: SExp[][] = [[]];
  for (const t of tokens) {
    if (t === '(') stack.push([]);
    else if (t === ')') {
      const done = stack.pop();
      if (stack.length === 0 || done === undefined) return null;
      stack[stack.length - 1].push(done);
    } else stack[stack.length - 1].push(t);
  }
  return stack.length === 1 ? stack[0] : null;
}

function sortName(s: SExp | undefined): string {
  if (s === undefined) return '?';
  return typeof s === 'string' ? s : s.filter((x) => x !== '_').map(sortName).join(' ');
}

const isList = (x: SExp | undefined): x is SExp[] => Array.isArray(x);

function headOf(x: SExp): string | null {
  return isList(x) && typeof x[0] === 'string' ? x[0] : null;
}

export function parseProblem(text: string): ParsedProblem | null {
  const forms = read(text);
  if (forms === null) return null;
  const synth = forms.find((f) => headOf(f) === 'synth-fun');
  if (!isList(synth) || synth.length < 5) return null;
  const name = synth[1];
  const paramList = synth[2];
  const grammar = synth[synth.length >= 6 ? 5 : 4];
  if (typeof name !== 'string' || !isList(paramList) || !isList(grammar)) return null;

  const params: VariableRule[] = paramList.flatMap((p) =>
    isList(p) && typeof p[0] === 'string' ? [{ name: p[0], sort: sortName(p[1]) }] : []
  );
  const returnSort = sortName(synth[3]);
  const rules = grammar.filter(isList);
  const nonterminals = new Set(rules.map((r) => String(r[0])));
  const paramNames = new Set(params.map((p) => p.name));

  const operators: OperatorRule[] = [];
  const constants: ConstantRule[] = [];
  const variables = new Map<string, VariableRule>();
  for (const rule of rules) {
    const lhs = String(rule[0]);
    const alternatives = rule[2];
    if (!isList(alternatives)) continue;
    for (const alt of alternatives) {
      if (isList(alt)) {
        const op = { name: String(alt[0]), args: alt.slice(1).map(String), result: lhs };
        if (!operators.some((o) => o.name === op.name && o.result === lhs && o.args.join() === op.args.join())) operators.push(op);
      } else if (paramNames.has(alt)) {
        const p = params.find((q) => q.name === alt);
        if (p) variables.set(alt, p);
      } else if (!nonterminals.has(alt)) {
        if (!constants.some((c) => c.value === alt && c.nonterminal === lhs)) constants.push({ value: alt, nonterminal: lhs });
      }
    }
  }

  const examples: Example[] = [];
  let reference: string | null = null;
  for (const form of forms) {
    if (headOf(form) !== 'constraint' || !isList(form) || !isList(form[1])) continue;
    const eq = form[1];
    if (eq[0] !== '=' || eq.length !== 3) continue;
    const [a, b] = [eq[1], eq[2]];
    const aIsCall: boolean = isList(a) && a[0] === name;
    const bIsCall: boolean = isList(b) && b[0] === name;
    if (!aIsCall && !bIsCall) continue;
    const call = (aIsCall ? a : b) as SExp[];
    const other: SExp | undefined = aIsCall ? b : a;
    if (other === undefined) continue;
    if (isList(other)) {
      if (typeof other[0] === 'string' && other[0] !== name) reference = other[0];
      continue;
    }
    examples.push({ inputs: call.slice(1).map((v) => (typeof v === 'string' ? v : '?')), output: other });
  }

  return {
    domain: paramList.some((p) => isList(p) && /BitVec/.test(sortName(p[1]))) || /BitVec/.test(returnSort) ? 'bitvector' : 'string',
    functionName: name,
    params,
    returnSort,
    start: rules.length ? String(rules[0][0]) : '',
    examples,
    reference,
    grammar: { operators, constants, variables: [...variables.values()] }
  };
}
