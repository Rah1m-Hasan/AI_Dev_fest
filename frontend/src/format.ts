export type ValueType = 'currency' | 'months' | 'days' | 'percentage' | 'date' | 'number' | 'score' | 'text';

export const formatCurrency = (value: number, signed = false) => {
  const amount = Number(value || 0);
  const sign = amount < 0 ? '-' : signed && amount > 0 ? '+' : '';
  return `${sign}৳${Math.abs(amount).toLocaleString('en-BD', {maximumFractionDigits: 0})}`;
};

// Compatibility name for existing money-only call sites. New action cards use
// formatValue with a declared semantic type instead of formatting all numbers.
export const formatBDT = formatCurrency;

export const formatNumber = (value: number) => Number(value || 0).toLocaleString('en-BD', {maximumFractionDigits: 2});
export const formatPercent = (value: number) => `${formatNumber(value)}%`;
export const formatMonths = (value: number) => `${formatNumber(value)} ${Number(value) === 1 ? 'month' : 'months'}`;
export const formatDays = (value: number) => `${formatNumber(value)} ${Number(value) === 1 ? 'day' : 'days'}`;
export const formatScore = (value: number) => `${formatNumber(value)}/100`;

export const formatDate = (value: string, withYear = false) =>
  new Intl.DateTimeFormat('en-US', {
    day: 'numeric',
    month: 'short',
    ...(withYear ? {year: 'numeric'} : {}),
  }).format(new Date(`${value.slice(0, 10)}T12:00:00`));

export const formatValue = (value: string | number | boolean | null | undefined, type: ValueType): string => {
  if (value === null || value === undefined) return '—';
  if (type === 'text') return String(value);
  if (type === 'date') return formatDate(String(value), true);
  const number = Number(value);
  if (!Number.isFinite(number)) return String(value);
  switch (type) {
    case 'currency': return formatCurrency(number);
    case 'months': return formatMonths(number);
    case 'days': return formatDays(number);
    case 'percentage': return formatPercent(number);
    case 'score': return formatScore(number);
    default: return formatNumber(number);
  }
};

export const titleCase = (value: string) =>
  value.replace(/_/g, ' ').replace(/\b\w/g, (letter: string) => letter.toUpperCase());
