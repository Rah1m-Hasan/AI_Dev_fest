export const formatBDT = (value: number, signed = false) => {
  const amount = Number(value || 0);
  const sign = amount < 0 ? '-' : signed && amount > 0 ? '+' : '';
  return `${sign}৳${Math.abs(amount).toLocaleString('en-BD', {maximumFractionDigits: 0})}`;
};

export const formatDate = (value: string, withYear = false) =>
  new Intl.DateTimeFormat('en-BD', {
    day: 'numeric',
    month: 'short',
    ...(withYear ? {year: 'numeric'} : {}),
  }).format(new Date(value));

export const titleCase = (value: string) =>
  value.replace(/_/g, ' ').replace(/\b\w/g, (letter: string) => letter.toUpperCase());
