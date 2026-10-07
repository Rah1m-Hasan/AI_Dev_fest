import {useEffect, useRef} from 'react';
import {
  ArrowDownRight,
  ArrowUpRight,
  BrainCircuit,
  CheckCircle2,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  X,
} from 'lucide-react';
import {formatBDT, formatDate, titleCase} from '../format';
import type {Change, Health, MoneyStory, Transaction} from '../types';

export function Brand({compact = false}: {compact?: boolean}) {
  return <div className={`brand ${compact ? 'brand--compact' : ''}`} aria-label="upay AI Assist">
    <span className="brand__mark">u</span>
    <strong>upay</strong>
    {!compact && <><i /><span>AI Assist</span></>}
  </div>;
}

export function Tag({children, tone = 'neutral', className = ''}: {children: React.ReactNode; tone?: 'neutral'|'positive'|'warning'|'ai'|'demo'; className?: string}) {
  return <span className={`tag tag--${tone} ${className}`}>{children}</span>;
}

export function TrustBadge({children}: {children: React.ReactNode}) {
  return <span className="trust"><ShieldCheck size={14} aria-hidden="true" />{children}</span>;
}

export function PageHeader({eyebrow, title, description, action}: {eyebrow?: string; title: string; description?: string; action?: React.ReactNode}) {
  return <header className="page-header">
    <div>
      {eyebrow && <span className="eyebrow">{eyebrow}</span>}
      <h1>{title}</h1>
      {description && <p>{description}</p>}
    </div>
    {action && <div className="page-header__action">{action}</div>}
  </header>;
}

export function LoadingPage({label = 'Loading your financial picture'}: {label?: string}) {
  return <div className="loading-page" role="status" aria-label={label}>
    <div className="skeleton skeleton--hero" />
    <div className="skeleton-grid"><div className="skeleton" /><div className="skeleton" /><div className="skeleton" /></div>
    <span className="sr-only">{label}</span>
  </div>;
}

export function ErrorState({message = "We couldn't load this financial view.", retry}: {message?: string; retry?: () => void}) {
  return <div className="state-card" role="alert">
    <div className="state-card__icon"><RefreshCw aria-hidden="true" /></div>
    <h2>Something didn’t load</h2>
    <p>{message}</p>
    {retry && <button className="button button--secondary" onClick={retry}><RefreshCw size={16} />Try again</button>}
  </div>;
}

export function EmptyState({title, description}: {title: string; description: string}) {
  return <div className="state-card state-card--empty"><Sparkles aria-hidden="true" /><h2>{title}</h2><p>{description}</p></div>;
}

export function Sheet({title, children, close, wide = false, className = ''}: {title: string; children: React.ReactNode; close: () => void; wide?: boolean; className?: string}) {
  const panel = useRef<HTMLElement>(null);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const focusable = () => Array.from(panel.current?.querySelectorAll<HTMLElement>('button, a[href], input, select, [tabindex]:not([tabindex="-1"])') || []).filter((item) => !item.hasAttribute('disabled'));
    focusable()[0]?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') close();
      if (event.key === 'Tab') {
        const items = focusable(); if (!items.length) return;
        const first = items[0], last = items[items.length - 1];
        if (event.shiftKey && document.activeElement === first) {event.preventDefault(); last.focus();}
        else if (!event.shiftKey && document.activeElement === last) {event.preventDefault(); first.focus();}
      }
    };
    window.addEventListener('keydown', onKey);
    return () => {window.removeEventListener('keydown', onKey); previous?.focus();};
  }, [close]);
  return <div className="backdrop" role="presentation" onMouseDown={close}>
    <section className={`sheet ${wide ? 'sheet--wide' : ''} ${className}`} ref={panel} role="dialog" aria-modal="true" aria-labelledby="sheet-title" onMouseDown={(event) => event.stopPropagation()}>
      <div className="sheet__header"><div><span className="eyebrow">Calculated evidence</span><h2 id="sheet-title">{title}</h2></div><button className="icon-button" onClick={close} aria-label="Close"><X /></button></div>
      <div className="sheet__body">{children}</div>
    </section>
  </div>;
}

export function EvidenceDrawer({evidence, close}: {evidence: Record<string, unknown>; close: () => void}) {
  const rows: Array<[string, string]> = [];
  const object = (value: unknown) => value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : undefined;
  const number = (value: unknown) => typeof value === 'number' ? value : undefined;
  const add = (label: string, value: string | undefined) => {if (value && rows.length < 12) rows.push([label, value]);};
  const period = object(evidence.period);
  if (period?.start && period?.end) add('Period', `${formatDate(String(period.start))}–${formatDate(String(period.end), true)}`);
  if (number(evidence.transactions_analyzed) !== undefined) add('Transactions analyzed', String(evidence.transactions_analyzed));
  if (number(evidence.total_expense) !== undefined) add('Current spending', formatBDT(Number(evidence.total_expense)));
  if (number(evidence.previous_period_expense) !== undefined) add('Previous spending', formatBDT(Number(evidence.previous_period_expense)));
  if (number(evidence.expense_change_percent) !== undefined) add('Spending change', `${Number(evidence.expense_change_percent) > 0 ? '+' : ''}${evidence.expense_change_percent}%`);
  const largest = object(evidence.largest_category_increase);
  if (largest?.category) add('Largest category change', `${largest.category} · ${formatBDT(Number(largest.current || 0) - Number(largest.previous || 0), true)}`);
  if (number(evidence.recurring_expenses) !== undefined) add('Recurring expenses', formatBDT(Number(evidence.recurring_expenses)));

  const categories = Array.isArray(evidence.categories) ? evidence.categories.map(object).filter(Boolean) as Record<string, unknown>[] : [];
  if (categories.length) {
    const current = categories.reduce((sum, item) => sum + Number(item.current || 0), 0);
    const previous = categories.reduce((sum, item) => sum + Number(item.previous || 0), 0);
    const leading = categories.find((item) => Number(item.difference || 0) > 0) || categories[0];
    add('Current spending', formatBDT(current)); add('Previous spending', formatBDT(previous)); add('Total change', formatBDT(current - previous, true));
    if (leading) add('Largest category change', `${leading.category} · ${formatBDT(Number(leading.difference || 0), true)}`);
  }

  const safe = object(evidence.safe_to_save);
  const safeBreakdown = object(safe?.breakdown);
  if (safe && safeBreakdown) {
    add('Period', `Next ${safe.period_days} days`); add('Available balance', formatBDT(Number(safeBreakdown.available_balance || 0)));
    add('Upcoming bills', formatBDT(Number(safeBreakdown.upcoming_bills || 0))); add('Typical spending', formatBDT(Number(safeBreakdown.typical_spending || 0)));
    add('Safety buffer', formatBDT(Number(safeBreakdown.safety_buffer || 0))); add('Recent cash-flow cap', formatBDT(Number(safeBreakdown.disposable_cash_flow_cap || 0)));
    add('Estimated flexible range', `${formatBDT(Number(safe.low || 0))}–${formatBDT(Number(safe.high || 0))}`);
  }
  const runway = object(evidence.runway);
  if (runway) {add('Estimated runway', `${runway.days} days`); add('Current balance', formatBDT(Number(runway.today_balance || 0))); add('Expected 14-day spending', formatBDT(Number(runway.expected_14_day_expenses || 0))); add('Expected 14-day balance', formatBDT(Number(runway.expected_14_day_balance || 0))); add('Forecast confidence', titleCase(String(runway.confidence || '')));}
  if (!rows.length) add('Calculation', 'Structured financial facts from your synthetic demo activity');
  return <Sheet title="How this answer was calculated" close={close} wide>
    <p className="sheet__intro">AI Assist receives only the calculated facts needed for this answer. It does not invent these values.</p>
    <div className="evidence-grid">{rows.map(([label, value]) => <div key={`${label}-${value}`}><span>{label}</span><strong>{value}</strong></div>)}</div>
    <div className="evidence-foot"><CheckCircle2 size={18} /><span>Calculated from synthetic demo transactions. Forecasts are estimates.</span></div>
  </Sheet>;
}

export function TransactionRow({transaction, onClick}: {transaction: Transaction; onClick?: () => void}) {
  const incoming = transaction.direction === 'income';
  return <button className="transaction-row" onClick={onClick} aria-label={`Open ${transaction.merchant_name} transaction`}>
    <span className={`merchant-icon merchant-icon--${incoming ? 'in' : 'out'}`}>{transaction.merchant_name.slice(0, 1)}</span>
    <span className="transaction-row__merchant"><strong>{transaction.merchant_name}</strong><small>{transaction.category}{transaction.is_recurring ? ' · Recurring' : ''}</small></span>
    <span className="transaction-row__date">{formatDate(transaction.timestamp)}</span>
    <span className="transaction-row__type">{titleCase(transaction.transaction_type)}</span>
    <strong className={incoming ? 'money-positive' : 'money-negative'}>{formatBDT(incoming ? transaction.amount : -transaction.amount, true)}</strong>
  </button>;
}

export function WhatChangedCard({changes, summary, onEvidence}: {changes: Change[]; summary: string; onEvidence?: () => void}) {
  const visible = changes.filter((item) => item.difference !== 0).slice(0, 4);
  const lead = visible[0];
  return <section className="card change-card">
    <div className="card__header"><div><span className="eyebrow">Current vs previous 30 days</span><h2>Watch spending</h2></div><Tag tone="ai">Calculated</Tag></div>
    {lead && <div className="change-list">{[lead].map((item) => {
      const up = item.difference > 0;
      return <div className="change-item" key={item.category}>
        <span className={`trend-icon ${up ? 'trend-icon--up' : 'trend-icon--down'}`}>{up ? <ArrowUpRight /> : <ArrowDownRight />}</span>
        <span><strong>{item.category}</strong><small>{formatBDT(item.current)} this period</small></span>
        <span className={up ? 'money-negative' : 'money-positive'}>{formatBDT(item.difference, true)}<small>{item.change_percent === null ? 'new activity' : `${item.change_percent > 0 ? '+' : ''}${item.change_percent}%`}</small></span>
      </div>;
    })}</div>}
    <p className="card__summary">{summary}</p>
    {visible.length > 1 && <details className="card-details"><summary>See more categories</summary><div className="change-list">{visible.slice(1).map((item) => { const up = item.difference > 0; return <div className="change-item" key={item.category}><span className={`trend-icon ${up ? 'trend-icon--up' : 'trend-icon--down'}`}>{up ? <ArrowUpRight /> : <ArrowDownRight />}</span><span><strong>{item.category}</strong><small>{formatBDT(item.current)} this period</small></span><span className={up ? 'money-negative' : 'money-positive'}>{formatBDT(item.difference, true)}</span></div>; })}</div></details>}
    {onEvidence && <button className="text-button" onClick={onEvidence}>See comparison evidence <ArrowUpRight size={15} /></button>}
  </section>;
}

export function HealthScoreCard({health}: {health: Health}) {
  return <section className="card health-card">
    <div className="card__header"><div><span className="eyebrow">Informational only</span><h2>Financial Health</h2></div><Tag tone={health.score >= 70 ? 'positive' : 'warning'}>{health.label}</Tag></div>
    <div className="health-score"><div className="health-score__ring" style={{'--score': `${health.score * 3.6}deg`} as React.CSSProperties}><strong>{health.score}</strong><span>/ 100</span></div><p>{health.what_improved}</p></div>
    <div className="health-breakdown">{health.components.map((item) => <div key={item.name}><span>{item.name}</span><strong>{item.score} / {item.max}</strong><progress value={item.score} max={item.max} /></div>)}</div>
    <TrustBadge>Not a credit score</TrustBadge>
  </section>;
}

export function MoneyStoryTimeline({story, compact = false}: {story: MoneyStory; compact?: boolean}) {
  const events = compact ? story.events.slice(-4) : story.events;
  return <section className="card story-card">
    <div className="card__header"><div><span className="eyebrow">{formatDate(story.period.start)}–{formatDate(story.period.end, true)}</span><h2>Your Money Story</h2></div><Tag tone="ai">Derived events</Tag></div>
    <div className="story-timeline">{events.map((event, index) => <div className="story-event" key={`${event.date}-${event.title}-${index}`}>
      <time>{formatDate(event.date)}</time><span className={`story-event__dot story-event__dot--${event.type}`} />
      <span><strong>{event.title}</strong><small>{event.detail}</small></span>
      <strong className={event.type === 'income' || event.amount < 0 ? 'money-positive' : ''}>{formatBDT(event.amount, event.type === 'income')}</strong>
    </div>)}</div>
  </section>;
}

export function CoachAvatar() {
  return <span className="coach-avatar"><BrainCircuit size={18} aria-hidden="true" /></span>;
}
