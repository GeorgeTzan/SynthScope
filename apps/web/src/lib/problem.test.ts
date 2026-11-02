import { describe, expect, it } from 'vitest';
import { parseProblem } from './problem';

const BV = `(set-logic BV)
(synth-fun f ((x (BitVec 4))) (BitVec 4)
  ((Start (BitVec 4) (x #x1 (bvand Start Start) (bvnot Start)))))
(constraint (= (f #b1011) #b1000))
(constraint (= (f #b0111) #b0000))
(check-synth)`;

const STR = `(set-logic SLIA)
(synth-fun f ((name String) (n Int)) String
  ((Start String (name "." (str.++ Start Start) (str.at Start Idx) (ite B Start Start)))
   (Idx Int (0 1 (+ Idx Idx)))
   (B Bool ((= Idx Idx) true))))
(constraint (= (f "Jan Kotas" 1) "J.K"))
(constraint (= (f "Ann ""A""" 2) "A.L"))`;

describe('parseProblem', () => {
  it('reads domain, parameters and examples of a bitvector problem', () => {
    const p = parseProblem(BV);
    expect(p).not.toBeNull();
    expect(p?.domain).toBe('bitvector');
    expect(p?.params).toEqual([{ name: 'x', sort: 'BitVec 4' }]);
    expect(p?.returnSort).toBe('BitVec 4');
    expect(p?.examples).toEqual([
      { inputs: ['#b1011'], output: '#b1000' },
      { inputs: ['#b0111'], output: '#b0000' }
    ]);
  });

  it('groups grammar productions into operators, constants and variables', () => {
    const g = parseProblem(BV)?.grammar;
    expect(g?.operators).toEqual([
      { name: 'bvand', args: ['Start', 'Start'], result: 'Start' },
      { name: 'bvnot', args: ['Start'], result: 'Start' }
    ]);
    expect(g?.constants).toEqual([{ value: '#x1', nonterminal: 'Start' }]);
    expect(g?.variables).toEqual([{ name: 'x', sort: 'BitVec 4' }]);
  });

  it('handles strings, ints, escaped quotes, several nonterminals and Bool literals', () => {
    const p = parseProblem(STR);
    expect(p?.domain).toBe('string');
    expect(p?.params).toEqual([
      { name: 'name', sort: 'String' },
      { name: 'n', sort: 'Int' }
    ]);
    expect(p?.examples[1]).toEqual({ inputs: ['"Ann ""A"""', '2'], output: '"A.L"' });
    const ops = p?.grammar.operators.map((o) => `${o.name}:${o.result}`);
    expect(ops).toEqual(['str.++:Start', 'str.at:Start', 'ite:Start', '+:Idx', '=:B']);
    expect(p?.grammar.constants.map((c) => c.value)).toEqual(['"."', '0', '1', 'true']);
  });

  it('understands the SyGuS v2 form with predeclared nonterminals', () => {
    const p = parseProblem(`(synth-fun f ((x (_ BitVec 8))) (_ BitVec 8)
      ((Start (_ BitVec 8))) ((Start (_ BitVec 8) (x (bvneg Start)))))
      (constraint (= (f #x01) #xff))`);
    expect(p?.params[0].sort).toBe('BitVec 8');
    expect(p?.grammar.operators.map((o) => o.name)).toEqual(['bvneg']);
  });

  it('reports a reference function instead of examples for specification problems', () => {
    const p = parseProblem(`(define-fun hd01 ((x (BitVec 8))) (BitVec 8) (bvand x (bvsub x #x01)))
      (synth-fun f ((x (BitVec 8))) (BitVec 8) ((Start (BitVec 8) (x (bvand Start Start)))))
      (declare-var x (BitVec 8))
      (constraint (= (hd01 x) (f x)))`);
    expect(p?.examples).toEqual([]);
    expect(p?.reference).toBe('hd01');
  });

  it('returns null for text that is not a synthesis problem', () => {
    expect(parseProblem('')).toBeNull();
    expect(parseProblem('(set-logic BV)')).toBeNull();
    expect(parseProblem('(synth-fun f')).toBeNull();
  });
});
