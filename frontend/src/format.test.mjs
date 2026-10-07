import {formatValue} from './format.ts';

const cases = [
  [2, 'currency', '৳2'],
  [2, 'months', '2 months'],
  [2, 'days', '2 days'],
  [2, 'percentage', '2%'],
  [72, 'score', '72/100'],
  ['2026-12-07', 'date', 'Dec 7, 2026'],
];

for (const [value, type, expected] of cases) {
  const actual = formatValue(value, type);
  if (actual !== expected) throw new Error(`${type}: expected ${expected}, received ${actual}`);
}
