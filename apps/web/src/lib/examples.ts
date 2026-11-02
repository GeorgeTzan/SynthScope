import { buildNumbersProblem, type NumbersSpec } from './numbers';

/** Ready-made problems for the picker. Each one is solved by the engine within a second or two (checked in examples.test.ts). */
export interface Example {
  id: string;
  title: string;
  hint: string;
  domain: 'bitvector' | 'string';
  text: string;
}

const numbers = (id: string, title: string, hint: string, spec: NumbersSpec): Example => ({
  id,
  title,
  hint,
  domain: 'bitvector',
  text: buildNumbersProblem(spec)
});

const rows = (...pairs: number[][]): bigint[][] => pairs.map((r) => r.map(BigInt));

export const EXAMPLES: Example[] = [
  numbers('square', 'Square a number', '2→4, 3→9, 4→16', {
    width: 8, rows: rows([2, 4], [3, 9], [4, 16]), ops: ['bvadd', 'bvmul'], constants: [1n]
  }),
  numbers('double-plus-one', 'Double and add one', '1→3, 2→5, 5→11', {
    width: 8, rows: rows([1, 3], [2, 5], [5, 11], [10, 21]), ops: ['bvadd'], constants: [1n]
  }),
  numbers('times-three', 'Multiply by three', '1→3, 2→6, 5→15', {
    width: 8, rows: rows([1, 3], [2, 6], [5, 15], [7, 21]), ops: ['bvadd'], constants: []
  }),
  numbers('cube', 'Cube a number', '2→8, 3→27, 4→64', {
    width: 8, rows: rows([2, 8], [3, 27], [4, 64], [5, 125]), ops: ['bvmul'], constants: []
  }),
  numbers('square-minus-self', 'Square minus the number', '2→2, 3→6, 4→12', {
    width: 8, rows: rows([2, 2], [3, 6], [4, 12], [5, 20]), ops: ['bvsub', 'bvmul'], constants: []
  }),
  numbers('clear-lowest-bit', 'Clear the lowest 1-bit', '12→8, 7→6, 10→8', {
    width: 8, rows: rows([12, 8], [7, 6], [8, 0], [10, 8], [1, 0]), ops: ['bvand', 'bvsub'], constants: [1n]
  }),
  numbers('isolate-lowest-bit', 'Keep only the lowest 1-bit', '12→4, 7→1, 10→2', {
    width: 8, rows: rows([12, 4], [7, 1], [8, 8], [10, 2], [6, 2]), ops: ['bvand', 'bvneg'], constants: []
  }),
  numbers('sum-two', 'Add two numbers', '2, 3→5; 10, 4→14', {
    width: 8, rows: rows([2, 3, 5], [10, 4, 14], [7, 7, 14]), ops: ['bvadd', 'bvsub', 'bvmul'], constants: []
  }),
  {
    id: 'initials',
    title: 'Initials of a name',
    hint: '"Jan", "Kotas" → "J.K"',
    domain: 'string',
    text: `(set-logic SLIA)
(synth-fun f ((first String) (last String)) String
  ((Start String (first last "." (str.++ Start Start Start) (str.at Start Idx)))
   (Idx Int (0 1))))
(constraint (= (f "Jan" "Kotas") "J.K"))
(constraint (= (f "Marie" "Curie") "M.C"))
(check-synth)
`
  },
  {
    id: 'greeting',
    title: 'Greeting',
    hint: '"Ann" → "Hello, Ann!"',
    domain: 'string',
    text: `(set-logic SLIA)
(synth-fun f ((name String)) String
  ((Start String (name "Hello, " "!" (str.++ Start Start)))))
(constraint (= (f "Ann") "Hello, Ann!"))
(constraint (= (f "Bob") "Hello, Bob!"))
(check-synth)
`
  },
  {
    id: 'last-char',
    title: 'Last character',
    hint: '"hello" → "o"',
    domain: 'string',
    text: `(set-logic SLIA)
(synth-fun f ((s String)) String
  ((Start String (s (str.at Start Idx)))
   (Idx Int (0 1 (str.len Start) (- Idx Idx)))))
(constraint (= (f "hello") "o"))
(constraint (= (f "world") "d"))
(constraint (= (f "ab") "b"))
(check-synth)
`
  },
  {
    id: 'email-domain',
    title: 'Domain of an email',
    hint: '"ann@x.com" → "x.com"',
    domain: 'string',
    text: `(set-logic SLIA)
(synth-fun f ((s String)) String
  ((Start String (s (str.substr Start Idx Idx)))
   (At String ("@"))
   (Idx Int (1 (+ Idx Idx) (str.len Start) (str.indexof Start At Zero)))
   (Zero Int (0))))
(constraint (= (f "ann@x.com") "x.com"))
(constraint (= (f "bob@mail.org") "mail.org"))
(check-synth)
`
  }
];

export const DEFAULT_EXAMPLE = 'square';
