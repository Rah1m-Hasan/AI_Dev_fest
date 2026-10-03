import {FormEvent, useEffect, useRef, useState} from 'react';
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import {
  ArrowRight,
  BookOpen,
  BrainCircuit,
  CalendarDays,
  Check,
  ChevronRight,
  CircleDollarSign,
  Compass,
  Edit3,
  ExternalLink,
  Eye,
  Gift,
  Lightbulb,
  ListFilter,
  MessageCircle,
  PiggyBank,
  Plus,
  ReceiptText,
  Search,
  Send,
  Sparkles,
  Target,
  TrendingUp,
  WalletCards,
  X,
  Zap,
} from 'lucide-react';
import {Link} from 'react-router-dom';
import {api} from './api/client';
import {formatBDT, formatDate, titleCase} from './format';
import type {
  BudgetRecommendation,
  Change,
  CoachMessage,
  DashboardSummary,
  DemoUser,
  Goal,
  Health,
  MoneyRunway,
  MoneyStory,
  SafeToSave,
  Transaction,
} from './types';
import {
  CoachAvatar,
  EmptyState,
  ErrorState,
  EvidenceDrawer,
  HealthScoreCard,
  LoadingPage,
  MoneyStoryTimeline,
  PageHeader,
  Sheet,
  Tag,
  TransactionRow,
  TrustBadge,
  WhatChangedCard,
} from './components/ui';

type LoadState<T> = {data?: T; error?: string};

function useResource<T>(path: string) {
  const [state, setState] = useState<LoadState<T>>({});
  const load = () => {
    setState({});
    void api<T>(path).then((data) => setState({data})).catch((reason: unknown) => setState({error: reason instanceof Error ? reason.message : 'Unable to load data.'}));
  };
  useEffect(load, [path]);
  return {...state, reload: load};
}

function MoneyPulseCard({data, ask}: {data: DashboardSummary; ask: () => void}) {
  const pulse = data.pulse;
  return <section className="card money-pulse">
    <div className="card__header"><div><Tag tone={pulse.status === 'Stable' ? 'positive' : 'warning'}>{pulse.status}</Tag><h2><Sparkles />Money Pulse</h2></div><TrustBadge>Calculated</TrustBadge></div>
    <p className="money-pulse__headline">{pulse.headline || pulse.text}</p>
    <div className="pulse-drivers">{pulse.why.slice(0, 2).map((driver) => <div key={driver.label}><span className="pulse-driver__icon"><TrendingUp /></span><span><strong>{driver.label}</strong><small>{driver.detail}</small></span></div>)}</div>
    <div className="pulse-next"><Lightbulb /><span>{pulse.next}</span></div>
    <div className="card__actions"><Link className="button button--secondary" to="/coach/insights">Why?</Link><button className="button" onClick={ask}><MessageCircle />Ask AI</button></div>
  </section>;
}

function RunwayCard({runway}: {runway: MoneyRunway}) {
  const points = [{name: 'Today', balance: runway.today_balance}, {name: '7 days', balance: (runway.today_balance + runway.expected_14_day_balance) / 2}, {name: '14 days', balance: runway.expected_14_day_balance}];
  return <section className="card runway-card">
    <div className="card__header"><div><span className="eyebrow">Forecast · {runway.confidence} confidence</span><h2>Money Runway</h2></div><Tag tone="ai">Estimate</Tag></div>
    <div className="runway-card__value"><strong>~{runway.days}</strong><span>days</span></div>
    <p>How long your current money may comfortably last at the recent pace.</p>
    <div className="mini-chart" aria-label="14-day balance forecast"><ResponsiveContainer width="100%" height="100%"><AreaChart data={points}><defs><linearGradient id="runwayFill" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#179EC1" stopOpacity={0.24}/><stop offset="95%" stopColor="#179EC1" stopOpacity={0}/></linearGradient></defs><XAxis dataKey="name" axisLine={false} tickLine={false} fontSize={11}/><Tooltip formatter={(value) => formatBDT(Number(value))}/><Area type="monotone" dataKey="balance" stroke="#075A8C" strokeWidth={3} fill="url(#runwayFill)" /></AreaChart></ResponsiveContainer></div>
    <div className="metric-list"><span><small>Current</small><strong>{formatBDT(runway.today_balance)}</strong></span><span><small>Expected 14-day spending</small><strong>-{formatBDT(runway.expected_14_day_expenses)}</strong></span><span><small>Expected balance</small><strong>{formatBDT(runway.expected_14_day_balance)}</strong></span></div>
  </section>;
}

function SafeToSaveCard({safe}: {safe: SafeToSave}) {
  const rows = [
    ['Available balance', safe.breakdown.available_balance],
    ['Expected income', safe.breakdown.expected_income],
    ['Expected bills', -safe.breakdown.upcoming_bills],
    ['Typical spending', -safe.breakdown.typical_spending],
    ['Safety buffer', -safe.breakdown.safety_buffer],
    ['Recent cash-flow cap', safe.breakdown.disposable_cash_flow_cap],
  ] as const;
  return <section className="card safe-card">
    <div className="card__header"><div><span className="eyebrow">Demo allocation</span><h2>Safe-to-Save</h2></div><PiggyBank /></div>
    <strong className="safe-card__range">{safe.high > 0 ? `${formatBDT(safe.low)}–${formatBDT(safe.high)}` : 'Pause this week'}</strong><p>{safe.high > 0 ? `Estimated flexible amount for the next ${safe.period_days} days.` : 'Recent cash flow does not show a comfortable amount to move into savings right now.'}</p>
    <div className="safe-breakdown">{rows.map(([label, value]) => <span key={label}><small>{label}</small><strong className={value < 0 ? 'money-negative' : ''}>{formatBDT(value, value > 0 && label === 'Expected income')}</strong></span>)}<span className="safe-breakdown__total"><small>Estimated flexibility</small><strong>{formatBDT(safe.breakdown.estimated_flexibility)}</strong></span></div>
    <Link className="button button--secondary button--full" to="/coach/goals">Add to a demo goal <ArrowRight /></Link>
    <TrustBadge>Nothing is transferred</TrustBadge>
  </section>;
}

export function PulsePage({user}: {user: DemoUser}) {
  const {data, error, reload} = useResource<DashboardSummary>('/dashboard/summary');
  const [evidence, setEvidence] = useState<Record<string, unknown>>();
  if (error) return <ErrorState message={error} retry={reload} />;
  if (!data) return <LoadingPage />;
  return <div className="page">
    <PageHeader eyebrow="Your financial picture" title={`Here’s what changed, ${user.display_name.split(' ')[0]}.`} description="A clear view of the last 30 days, what may happen next, and what you can explore." action={<Tag tone="demo">Demo data</Tag>} />
    <section className="balance-hero">
      <div><span>Available balance</span><strong>{formatBDT(data.balance)}</strong><small>Calculated from synthetic wallet activity</small></div>
      <div className="balance-stats"><span><small>Income</small><strong>{formatBDT(data.this_month.income)}</strong></span><span><small>Spent</small><strong>{formatBDT(data.this_month.spending)}</strong></span><span><small>Net cash flow</small><strong className={data.this_month.savings >= 0 ? 'money-positive-light' : 'money-negative-light'}>{formatBDT(data.this_month.savings, true)}</strong></span></div>
    </section>
    <div className="dashboard-grid">
      <div className="grid-span-8"><MoneyPulseCard data={data} ask={() => window.location.assign('/coach/assistant')} /></div>
      <div className="grid-span-4"><RunwayCard runway={data.runway} /></div>
      <div className="grid-span-7"><WhatChangedCard changes={data.comparison.categories} summary={data.comparison.summary} onEvidence={() => setEvidence(data.comparison as unknown as Record<string, unknown>)} /></div>
      <div className="grid-span-5"><SafeToSaveCard safe={data.safe_to_save} /></div>
      <section className="card grid-span-7 category-card"><div className="card__header"><div><span className="eyebrow">Where it went</span><h2>Spending by category</h2></div><Link className="text-button" to="/history">Transactions <ArrowRight /></Link></div><div className="category-bars">{data.spending_breakdown.slice(0, 6).map((item) => <div key={item.category}><span><strong>{item.category}</strong><small>{formatBDT(item.amount)}</small></span><progress value={item.percentage} max="100" /><small>{item.percentage}%</small></div>)}</div></section>
      <section className="card grid-span-5 upcoming-card"><div className="card__header"><div><span className="eyebrow">Next 14 days</span><h2>Upcoming activity</h2></div><CalendarDays /></div>{data.runway.upcoming.length ? data.runway.upcoming.slice(0, 4).map((item) => <div className="upcoming-row" key={`${item.merchant}-${item.expected_date}`}><span><strong>{item.merchant}</strong><small>{formatDate(item.expected_date)} · recurring</small></span><strong>~{formatBDT(item.amount)}</strong></div>) : <EmptyState title="No upcoming bills found" description="No recurring payment is expected in this forecast window." />}</section>
      <div className="grid-span-7"><MoneyStoryTimeline story={data.story} compact /></div>
      <section className="card grid-span-5 recent-card"><div className="card__header"><div><span className="eyebrow">Recent activity</span><h2>Latest transactions</h2></div><Link className="text-button" to="/history">View all <ArrowRight /></Link></div>{data.recent_transactions.slice(0, 5).map((transaction) => <TransactionRow transaction={transaction} key={transaction.id} />)}</section>
    </div>
    {evidence && <EvidenceDrawer evidence={evidence} close={() => setEvidence(undefined)} />}
  </div>;
}

type Intelligence = {comparison: {categories: Change[]; summary: string; period: {start: string; end: string}}; safe_to_save: SafeToSave; runway: MoneyRunway; story: MoneyStory; health: Health};

export function InsightsPage() {
  const {data, error, reload} = useResource<Intelligence>('/intelligence/overview');
  const [evidence, setEvidence] = useState<Record<string, unknown>>();
  if (error) return <ErrorState message={error} retry={reload} />;
  if (!data) return <LoadingPage label="Loading calculated insights" />;
  const maximum = Math.max(...data.comparison.categories.map((item) => item.current), 1);
  return <div className="page">
    <PageHeader eyebrow="Insights" title="What your money is telling you" description="Patterns with context—not judgments. Every insight links back to calculated activity." />
    <div className="dashboard-grid">
      <div className="grid-span-7"><WhatChangedCard changes={data.comparison.categories} summary={data.comparison.summary} onEvidence={() => setEvidence(data.comparison as unknown as Record<string, unknown>)} /></div>
      <section className="card grid-span-5 pattern-card"><div className="card__header"><div><span className="eyebrow">Spending patterns</span><h2>Current category mix</h2></div><Tag tone="ai">30 days</Tag></div>{data.comparison.categories.slice(0, 6).map((item) => <div className="comparison-bar" key={item.category}><span><strong>{item.category}</strong><small>{formatBDT(item.current)}</small></span><div><i style={{width: `${Math.max(2, item.current / maximum * 100)}%`}} /></div><small>{formatBDT(item.previous)} before</small></div>)}</section>
      <div className="grid-span-5"><HealthScoreCard health={data.health} /></div>
      <div className="grid-span-7"><MoneyStoryTimeline story={data.story} /></div>
      <section className="card grid-span-12 integration-card"><div><Tag tone="demo">History integration</Tag><h2>Smart Insights beside your transaction history</h2><p>See category changes, recurring costs, and Money Story without leaving the familiar History flow.</p></div><Link className="button" to="/history">Open History <ArrowRight /></Link></section>
    </div>
    {evidence && <EvidenceDrawer evidence={evidence} close={() => setEvidence(undefined)} />}
  </div>;
}

type TransactionsResponse = {items: Transaction[]; total: number};
type SpendingSummary = {total_spending: number; recurring_expenses: number; category_totals: Array<{category: string; amount: number}>; data_period: {start: string; end: string}};
type Cashflow = {income: number; expense: number; net: number};
type TransactionContext = {transaction: Transaction; category_total: number; share_of_category_percent: number; comparison: Change | null; period: {start: string; end: string}; source: string};

export function HistoryPage() {
  const [tab, setTab] = useState<'details'|'summary'|'insights'>('details');
  const [transactions, setTransactions] = useState<TransactionsResponse>();
  const [summary, setSummary] = useState<SpendingSummary>();
  const [cashflow, setCashflow] = useState<Cashflow>();
  const [categories, setCategories] = useState<string[]>([]);
  const [query, setQuery] = useState('');
  const [direction, setDirection] = useState('');
  const [category, setCategory] = useState('');
  const [recurringOnly, setRecurringOnly] = useState(false);
  const [selected, setSelected] = useState<TransactionContext>();
  const [error, setError] = useState('');
  const load = async () => {
    setError('');
    const params = new URLSearchParams({page_size: '100'});
    if (query.trim()) params.set('q', query.trim());
    if (direction) params.set('direction', direction);
    if (category) params.set('category', category);
    try {
      const [items, spend, flow, categoryData] = await Promise.all([
        api<TransactionsResponse>(`/transactions?${params}`), api<SpendingSummary>('/transactions/summary'), api<Cashflow>('/analytics/cashflow'), api<{categories: string[]}>('/transactions/categories'),
      ]);
      setTransactions(items); setSummary(spend); setCashflow(flow); setCategories(categoryData.categories);
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Unable to load transactions.'); }
  };
  useEffect(() => { void load(); }, [direction, category]);
  const openTransaction = async (transaction: Transaction) => setSelected(await api<TransactionContext>(`/transactions/${transaction.id}/context`));
  const correctCategory = async (newCategory: string) => {
    if (!selected) return;
    await api(`/transactions/${selected.transaction.id}/category`, {method: 'PATCH', body: JSON.stringify({category: newCategory})});
    setSelected(undefined); await load();
  };
  if (error) return <ErrorState message={error} retry={() => void load()} />;
  if (!transactions || !summary || !cashflow) return <LoadingPage label="Loading transaction history" />;
  const visible = recurringOnly ? transactions.items.filter((item) => item.is_recurring) : transactions.items;
  const largest = visible.reduce((max, item) => item.direction === 'income' ? max : Math.max(max, item.amount), 0);
  return <div className="page">
    <PageHeader eyebrow="upay History" title="Your money activity" description="Transactions, summaries, and a new Smart Insights layer in one familiar place." />
    <div className="history-tabs" role="tablist">{[['details','Transaction details'],['summary','Transaction summary'],['insights','Smart Insights']].map(([value, label]) => <button role="tab" aria-selected={tab === value} className={tab === value ? 'active' : ''} onClick={() => setTab(value as typeof tab)} key={value}>{label}{value === 'insights' && <Sparkles />}</button>)}</div>
    {tab === 'details' && <>
      <div className="summary-strip"><span><small>Spent</small><strong>{formatBDT(cashflow.expense)}</strong></span><span><small>Income</small><strong>{formatBDT(cashflow.income)}</strong></span><span><small>Recurring</small><strong>{formatBDT(summary.recurring_expenses)}</strong></span><span><small>Largest transaction</small><strong>{formatBDT(largest)}</strong></span></div>
      <section className="transaction-panel">
        <div className="transaction-toolbar"><form onSubmit={(event) => {event.preventDefault(); void load();}}><Search /><input aria-label="Search merchant" placeholder="Search merchant" value={query} onChange={(event) => setQuery(event.target.value)} /><button className="button button--small">Search</button></form><label><ListFilter /><select value={category} onChange={(event) => setCategory(event.target.value)} aria-label="Filter by category"><option value="">All categories</option>{categories.map((item) => <option key={item}>{item}</option>)}</select></label></div>
        <div className="filter-chips">{[['','All'],['income','Money in'],['expense','Money out']].map(([value, label]) => <button className={direction === value && !recurringOnly ? 'active' : ''} onClick={() => {setRecurringOnly(false); setDirection(value);}} key={label}>{label}</button>)}<button className={recurringOnly ? 'active' : ''} onClick={() => {setRecurringOnly(true); setDirection('');}}>Recurring</button></div>
        <div className="transaction-table"><div className="transaction-table__head"><span>Merchant</span><span>Date</span><span>Type</span><span>Amount</span></div>{visible.length ? visible.map((transaction) => <TransactionRow transaction={transaction} onClick={() => void openTransaction(transaction)} key={transaction.id} />) : <EmptyState title="No transactions found" description="Try a different search or filter." />}</div>
      </section>
    </>}
    {tab === 'summary' && <div className="dashboard-grid"><section className="card grid-span-7"><div className="card__header"><div><span className="eyebrow">Last 30 days</span><h2>Category summary</h2></div><Tag tone="ai">Calculated</Tag></div><div className="category-bars">{summary.category_totals.map((item) => <div key={item.category}><span><strong>{item.category}</strong><small>{formatBDT(item.amount)}</small></span><progress value={item.amount} max={summary.total_spending} /><small>{Math.round(item.amount / summary.total_spending * 100)}%</small></div>)}</div></section><section className="card grid-span-5"><span className="eyebrow">Cash flow</span><h2>Money in and out</h2><div className="big-metrics"><span><small>Money in</small><strong className="money-positive">{formatBDT(cashflow.income)}</strong></span><span><small>Money out</small><strong>{formatBDT(cashflow.expense)}</strong></span><span><small>Net</small><strong className={cashflow.net >= 0 ? 'money-positive' : 'money-negative'}>{formatBDT(cashflow.net, true)}</strong></span></div></section></div>}
    {tab === 'insights' && <HistoryInsights />}
    {selected && <Sheet title="Transaction details" close={() => setSelected(undefined)}>
      <div className="transaction-detail"><span className="merchant-icon">{selected.transaction.merchant_name[0]}</span><h3>{selected.transaction.merchant_name}</h3><strong>{formatBDT(selected.transaction.direction === 'income' ? selected.transaction.amount : -selected.transaction.amount, true)}</strong><p>{formatDate(selected.transaction.timestamp, true)} · {titleCase(selected.transaction.transaction_type)}</p></div>
      <dl className="detail-list"><div><dt>Category</dt><dd>{selected.transaction.category}</dd></div><div><dt>Description</dt><dd>{selected.transaction.description}</dd></div><div><dt>Data source</dt><dd>Demo transaction</dd></div></dl>
      <div className="ai-context"><Sparkles /><div><span className="eyebrow">AI context</span><h3>This belongs to {selected.transaction.category}</h3><p>You spent {formatBDT(selected.category_total)} in this category during the current period. This transaction represents {selected.share_of_category_percent}% of that total.</p>{selected.comparison && <p>Compared with the previous period: <strong>{formatBDT(selected.comparison.difference, true)}</strong>.</p>}</div></div>
      <label className="field"><span>Change category</span><select defaultValue={selected.transaction.category} onChange={(event) => void correctCategory(event.target.value)}>{categories.map((item) => <option key={item}>{item}</option>)}</select></label>
    </Sheet>}
  </div>;
}

function HistoryInsights() {
  const {data, error, reload} = useResource<Intelligence>('/intelligence/overview');
  if (error) return <ErrorState message={error} retry={reload} />;
  if (!data) return <LoadingPage />;
  return <div className="dashboard-grid history-insights"><div className="grid-span-7"><WhatChangedCard changes={data.comparison.categories} summary={data.comparison.summary} /></div><section className="card grid-span-5"><span className="eyebrow">Recurring costs</span><h2>{formatBDT(data.safe_to_save.breakdown.upcoming_bills)} expected soon</h2><p>Included in your runway and safe-to-save calculation.</p><Link className="button button--secondary" to="/coach/assistant">Ask AI about this</Link></section><div className="grid-span-12"><MoneyStoryTimeline story={data.story} /></div></div>;
}

type CurrentBudget = {id: number; total_limit: number; categories: Record<string, number>; used: number; remaining: number; status: string} | null;

export function PlanPage() {
  const [recommendation, setRecommendation] = useState<BudgetRecommendation>();
  const [current, setCurrent] = useState<CurrentBudget>();
  const [dashboard, setDashboard] = useState<DashboardSummary>();
  const [editing, setEditing] = useState(false);
  const [limits, setLimits] = useState<Record<string, number>>({});
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const load = async () => {
    try { const [rec, saved, dash] = await Promise.all([api<BudgetRecommendation>('/budgets/recommendation'), api<CurrentBudget>('/budgets/current'), api<DashboardSummary>('/dashboard/summary')]); setRecommendation(rec); setCurrent(saved); setDashboard(dash); setLimits(rec.category_limits); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Unable to load your plan.'); }
  };
  useEffect(() => { void load(); }, []);
  if (error) return <ErrorState message={error} retry={() => void load()} />;
  if (!recommendation || !dashboard) return <LoadingPage label="Building your monthly plan" />;
  const total = Math.round(Object.values(limits).reduce((sum, value) => sum + Number(value || 0), 0) * 100) / 100;
  const remaining = recommendation.period_income - total;
  const save = async () => {
    const categories = Object.fromEntries(Object.entries(limits).map(([name, value]) => [name, Math.round(Number(value) * 100) / 100]));
    const body = {total_limit: total, categories};
    if (current) await api(`/budgets/${current.id}`, {method: 'PUT', body: JSON.stringify(body)}); else await api('/budgets', {method: 'POST', body: JSON.stringify(body)});
    setNotice('Your demo plan was saved.'); setEditing(false); await load();
  };
  return <div className="page">
    <PageHeader eyebrow="Plan" title="Your monthly plan" description="Built from your recent income, regular expenses, spending pattern, and income stability." action={<div className="button-row">{editing ? <><button className="button button--ghost" onClick={() => {setLimits(recommendation.category_limits); setEditing(false);}}>Reset</button><button className="button" disabled={total <= 0 || total > recommendation.period_income} onClick={() => void save()}><Check />Save plan</button></> : <><button className="button button--secondary" onClick={() => setEditing(true)}><Edit3 />Customize</button><button className="button" onClick={() => void save()}><Check />Accept plan</button></>}</div>} />
    {notice && <div className="toast" role="status"><Check />{notice}</div>}
    <section className="plan-hero"><div><span>Recommended spend</span><strong>{formatBDT(total)}</strong><small>Expected income {formatBDT(recommendation.period_income)}</small></div><div className="plan-metrics"><span><small>Essentials</small><strong>{formatBDT(recommendation.essential_budget)}</strong></span><span><small>Flexible</small><strong>{formatBDT(recommendation.flexible_budget)}</strong></span><span><small>Savings target</small><strong>{formatBDT(Math.max(0, remaining - recommendation.buffer_contribution))}</strong></span><span><small>Safety buffer</small><strong>{formatBDT(recommendation.buffer_contribution)}</strong></span></div><div className="allocation-track"><i style={{width: `${Math.min(100, recommendation.essential_budget / recommendation.period_income * 100)}%`}} /><i style={{width: `${Math.min(100, recommendation.flexible_budget / recommendation.period_income * 100)}%`}} /><i style={{width: `${Math.min(100, recommendation.savings_target / recommendation.period_income * 100)}%`}} /></div></section>
    <div className="plan-links"><Link to="/coach/goals"><Target /><span><strong>Your goals</strong><small>Check feasibility and alternatives</small></span><ChevronRight /></Link><Link to="/coach/scenario"><Compass /><span><strong>Scenario Lab</strong><small>Explore what happens if something changes</small></span><ChevronRight /></Link></div>
    <div className="dashboard-grid">
      <section className="card grid-span-8"><div className="card__header"><div><span className="eyebrow">Category plan</span><h2>Targets based on recent behavior</h2></div><Tag tone="ai">{recommendation.confidence} confidence</Tag></div><div className="budget-list">{Object.entries(limits).sort((a,b) => b[1]-a[1]).map(([name, limit]) => {const spent = dashboard.spending_breakdown.find((item) => item.category === name)?.amount || 0; const percent = limit ? Math.min(120, spent / limit * 100) : 0; return <div className="budget-item" key={name}><span><strong>{name}</strong><small>{formatBDT(spent)} of {formatBDT(limit)}</small></span>{editing ? <input aria-label={`${name} budget`} type="number" min="0" value={Math.round(limit)} onChange={(event) => setLimits({...limits, [name]: Number(event.target.value)})} /> : <strong>{Math.round(percent)}%</strong>}<progress className={percent > 100 ? 'over' : ''} value={percent} max="100" /></div>;})}</div>{editing && <div className={`allocation-status ${remaining < 0 ? 'allocation-status--error' : ''}`}><span>Unallocated income</span><strong>{formatBDT(remaining)}</strong></div>}</section>
      <section className="card grid-span-4 explain-card"><div className="card__header"><div><span className="eyebrow">Explainability</span><h2>Why these numbers?</h2></div><Eye /></div><p>{recommendation.reasoning}</p><dl><div><dt>Recent income estimate</dt><dd>{formatBDT(recommendation.period_income)}</dd></div><div><dt>Fixed recurring costs</dt><dd>{formatBDT(recommendation.fixed_recurring_costs)}</dd></div><div><dt>Income pattern</dt><dd>{titleCase(recommendation.income_stability)}</dd></div><div><dt>Emergency buffer</dt><dd>{formatBDT(recommendation.emergency_buffer)}</dd></div></dl><TrustBadge>Calculated recommendation</TrustBadge></section>
    </div>
  </div>;
}

export function GoalsPage() {
  const [goals, setGoals] = useState<Goal[]>();
  const [budget, setBudget] = useState<BudgetRecommendation>();
  const [open, setOpen] = useState(false);
  const [error, setError] = useState('');
  const load = async () => { try { const [goalData, rec] = await Promise.all([api<{items: Goal[]}>('/goals'), api<BudgetRecommendation>('/budgets/recommendation')]); setGoals(goalData.items); setBudget(rec); } catch (reason) { setError(reason instanceof Error ? reason.message : 'Unable to load goals.'); } };
  useEffect(() => { void load(); }, []);
  if (error) return <ErrorState message={error} retry={() => void load()} />;
  if (!goals || !budget) return <LoadingPage label="Loading savings goals" />;
  return <div className="page">
    <PageHeader eyebrow="Plan · Goals" title="Goals that fit your cash flow" description="See the contribution required, whether it fits recent flexibility, and alternatives you can explore." action={<button className="button" onClick={() => setOpen(true)}><Plus />New goal</button>} />
    {goals.length ? <div className="goal-grid">{goals.map((goal) => <section className="card goal-card" key={goal.id}><div className="card__header"><span className="goal-icon"><Target /></span><Tag tone={goal.plan.feasible ? 'positive' : 'warning'}>{goal.plan.feasible ? 'On track' : 'Needs adjustment'}</Tag></div><h2>{goal.name}</h2><div className="goal-amount"><strong>{formatBDT(goal.current_amount)}</strong><span>of {formatBDT(goal.target_amount)}</span><b>{goal.progress_percent}%</b></div><progress value={goal.progress_percent} max="100" /><div className="goal-details"><span><small>Recommended</small><strong>{formatBDT(goal.plan.recommended_weekly_contribution)}/week</strong></span><span><small>Target</small><strong>{formatDate(goal.target_date, true)}</strong></span></div><p>{goal.plan.feasible ? 'The required contribution fits your recent calculated savings capacity.' : 'The target needs more monthly saving than your recent free cash flow supports.'}</p>{!goal.plan.feasible && <div className="alternatives"><strong>Explore alternatives</strong>{goal.plan.alternatives.map((item) => <Link to="/coach/scenario" key={item}>{item}<ArrowRight /></Link>)}</div>}</section>)}</div> : <EmptyState title="You haven’t created a savings goal yet" description="Create one to see a cash-flow-based contribution plan." />}
    {open && <GoalWizard budget={budget} close={() => setOpen(false)} done={() => {setOpen(false); void load();}} />}
  </div>;
}

function GoalWizard({budget, close, done}: {budget: BudgetRecommendation; close: () => void; done: () => void}) {
  const [step, setStep] = useState(1);
  const [kind, setKind] = useState('Emergency Fund');
  const [amount, setAmount] = useState(50000);
  const [current, setCurrent] = useState(0);
  const defaultDeadline = new Date(Date.now() + 240 * 86400000).toISOString().slice(0,10);
  const [deadline, setDeadline] = useState(defaultDeadline);
  const [error, setError] = useState('');
  const months = Math.max(1, (new Date(deadline).getTime() - Date.now()) / (30.44 * 86400000));
  const required = Math.max(0, amount - current) / months;
  const feasible = required <= budget.savings_target;
  const create = async () => { try { await api('/goals', {method: 'POST', body: JSON.stringify({goal_name: kind, target_amount: amount, optional_current_savings: current, deadline})}); done(); } catch (reason) { setError(reason instanceof Error ? reason.message : 'Unable to create goal.'); } };
  const choices = ['Emergency Fund','Education','Device','Travel','Family','Other'];
  return <div className="backdrop"><section className="goal-wizard" role="dialog" aria-modal="true" aria-labelledby="goal-title"><div className="sheet__header"><div><span className="eyebrow">Step {step} of 3</span><h2 id="goal-title">Create a savings goal</h2></div><button className="icon-button" onClick={close} aria-label="Close"><X /></button></div><div className="wizard-progress"><i className="active" /><i className={step >= 2 ? 'active' : ''} /><i className={step >= 3 ? 'active' : ''} /></div>
    {step === 1 && <div className="wizard-step"><h3>What are you saving for?</h3><div className="goal-types">{choices.map((choice) => <button className={kind === choice ? 'active' : ''} onClick={() => setKind(choice)} key={choice}><Target />{choice}</button>)}</div></div>}
    {step === 2 && <div className="wizard-step"><h3>Set your target</h3><label className="field"><span>Target amount</span><input type="number" min="1" value={amount} onChange={(event) => setAmount(Number(event.target.value))} /></label><label className="field"><span>Target date</span><input type="date" min={new Date(Date.now()+86400000).toISOString().slice(0,10)} value={deadline} onChange={(event) => setDeadline(event.target.value)} /></label><label className="field"><span>Already saved</span><input type="number" min="0" max={amount} value={current} onChange={(event) => setCurrent(Number(event.target.value))} /></label></div>}
    {step === 3 && <div className="wizard-step"><Tag tone={feasible ? 'positive' : 'warning'}>{feasible ? 'Looks achievable' : 'May be difficult'}</Tag><h3>Your feasibility preview</h3><div className="big-metrics"><span><small>Required per month</small><strong>{formatBDT(required)}</strong></span><span><small>Recent savings capacity</small><strong>{formatBDT(budget.savings_target)}</strong></span></div><p>{feasible ? 'The monthly amount fits within your calculated savings target.' : 'Consider extending the deadline, lowering the target, or testing a spending change in Scenario Lab.'}</p><TrustBadge>The backend recalculates the final plan after creation</TrustBadge></div>}
    {error && <p className="form-error" role="alert">{error}</p>}<div className="wizard-actions">{step > 1 && <button className="button button--ghost" onClick={() => setStep(step - 1)}>Back</button>}<button className="button" onClick={() => step < 3 ? setStep(step + 1) : void create()}>{step < 3 ? 'Continue' : 'Create goal'}<ArrowRight /></button></div></section></div>;
}

type ScenarioResult = {kind: string; amount: number; projected_balance: number; safe_to_save_high: number; baseline_balance: number; baseline_safe_to_save_high: number; difference: number; before: {projected_balance: number; safe_to_save_high: number; goal_target_date: string | null}; after: {projected_balance: number; safe_to_save_high: number; estimated_goal_weeks_earlier: number}; explanation: string; disclaimer: string};

export function ScenarioPage() {
  const [kind, setKind] = useState('reduce_spending');
  const [amount, setAmount] = useState(500);
  const [result, setResult] = useState<ScenarioResult>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const options = [
    ['reduce_spending','Spend less each week','Reduce a weekly category amount'],
    ['save_more','Save more this month','Allocate more toward a goal'],
    ['purchase','Buy an item','Test a one-time purchase'],
    ['income_delay','Income arrives late','Make the forecast more conservative'],
  ];
  const run = async () => { setBusy(true); setError(''); try { setResult(await api<ScenarioResult>('/scenarios/simulate', {method: 'POST', body: JSON.stringify({kind, amount, days: 7})})); } catch (reason) { setError(reason instanceof Error ? reason.message : 'Unable to run scenario.'); } finally { setBusy(false); } };
  return <div className="page">
    <PageHeader eyebrow="Plan · Scenario Lab" title="What happens if I change something?" description="Compare a choice with the current forecast. Nothing here changes your wallet, budget, or goal." />
    <div className="scenario-layout"><section className="card scenario-controls"><div className="card__header"><div><span className="eyebrow">Choose one change</span><h2>Explore an outcome</h2></div><Compass /></div><div className="scenario-options">{options.map(([value, label, note]) => <button className={kind === value ? 'active' : ''} onClick={() => setKind(value)} key={value}><span><strong>{label}</strong><small>{note}</small></span><Check /></button>)}</div><label className="field"><span>{kind === 'reduce_spending' ? 'Weekly amount' : 'Amount'} (৳)</span><input type="number" min="1" value={amount} onChange={(event) => setAmount(Number(event.target.value))} /></label><button className="button button--full" disabled={busy || amount <= 0} onClick={() => void run()}><Zap />{busy ? 'Calculating…' : 'Run scenario'}</button><TrustBadge>Deterministic estimate · no account changes</TrustBadge>{error && <p className="form-error">{error}</p>}</section>
      <section className={`scenario-result ${result ? 'scenario-result--ready' : ''}`}>{result ? <><Tag tone="ai">Scenario result</Tag><h2>{options.find(([value]) => value === kind)?.[1]}</h2><p>{result.explanation}</p><div className="scenario-compare"><div><span>Current</span><small>Projected balance</small><strong>{formatBDT(result.before.projected_balance)}</strong><small>Safe-to-save high</small><b>{formatBDT(result.before.safe_to_save_high)}</b></div><ArrowRight /><div><span>Scenario</span><small>Projected balance</small><strong>{formatBDT(result.after.projected_balance)}</strong><small>Safe-to-save high</small><b>{formatBDT(result.after.safe_to_save_high)}</b></div></div><div className="scenario-difference"><TrendingUp /><span><small>Difference</small><strong>{formatBDT(result.difference, true)} projected balance</strong>{result.after.estimated_goal_weeks_earlier > 0 && <small>About {result.after.estimated_goal_weeks_earlier} weeks of goal contribution</small>}</span></div><TrustBadge>{result.disclaimer}</TrustBadge></> : <><span className="scenario-result__icon"><Compass /></span><h2>Try a scenario</h2><p>Your current forecast and scenario result will appear side by side.</p></>}</section></div>
  </div>;
}

export function CoachPage({user}: {user: DemoUser}) {
  const initial: CoachMessage = {id: 'welcome', role: 'ai', text: `Hi ${user.display_name.split(' ')[0]}. I can explain what changed, what may happen next, and what you can realistically plan for.`};
  const [messages, setMessages] = useState<CoachMessage[]>([initial]);
  const [question, setQuestion] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [evidence, setEvidence] = useState<Record<string, unknown>>();
  const chatBody = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const body = chatBody.current;
    if (body) body.scrollTo({top: body.scrollHeight, behavior: messages.length > 1 ? 'smooth' : 'auto'});
  }, [messages, busy]);
  const prompts = ['Why is my balance lower?','Where did I spend most?','How much can I safely save?','Can I reach my goal?','What expenses are coming?','Help me make a budget.'];
  const ask = async (text: string) => {
    const clean = text.trim(); if (!clean || busy) return;
    setMessages((items) => [...items, {id: crypto.randomUUID(), role: 'user', text: clean}]); setQuestion(''); setBusy(true); setError('');
    try { const result = await api<{answer: {text: string; provider: string}; intent: string; structured_context: Record<string, unknown>}>('/coach/chat', {method: 'POST', body: JSON.stringify({question: clean, language: 'en'})}); setMessages((items) => [...items, {id: crypto.randomUUID(), role: 'ai', text: result.answer.text, evidence: result.structured_context, provider: result.answer.provider, intent: result.intent}]); }
      catch (reason) { setError(reason instanceof Error ? reason.message : 'The coach could not answer.'); }
    finally { setBusy(false); }
  };
  const submit = (event: FormEvent) => {event.preventDefault(); void ask(question);};
  return <div className="page coach-page">
    <PageHeader eyebrow="Coach" title="Ask about your own money" description="Grounded in calculated financial activity. You stay in control; AI only explains and suggests." />
    <section className="chat-shell">
      <header className="chat-header"><CoachAvatar /><span><strong>AI Financial Coach</strong><small><i /> Grounded in your financial activity</small></span><TrustBadge>Informational guidance</TrustBadge></header>
      <div className="chat-body" ref={chatBody} aria-live="polite">{messages.map((message) => <div className={`chat-message chat-message--${message.role}`} key={message.id}>{message.role === 'ai' && <CoachAvatar />}<div>{message.provider && <Tag tone={message.provider === 'groq_grounded' ? 'ai' : 'neutral'}>{message.provider === 'groq_grounded' ? 'AI explanation' : 'Calculated fallback'}</Tag>}<p>{message.text}</p>{message.evidence && <div className="message-actions"><button className="text-button" onClick={() => setEvidence(message.evidence)}><Eye />See evidence</button>{message.intent === 'spending_analysis' && <Link className="text-button" to="/coach/scenario"><Compass />Try What-If</Link>}</div>}</div></div>)}{busy && <div className="chat-message chat-message--ai"><CoachAvatar /><div className="typing" aria-label="Coach is thinking"><i /><i /><i /></div></div>}{error && <div className="chat-error" role="alert"><span>AI wording is unavailable right now.</span><button onClick={() => {const userMessages=messages.filter((item) => item.role === 'user'); void ask(userMessages[userMessages.length-1]?.text || 'What changed?');}}>Try again</button></div>}</div>
      {messages.length < 3 && <div className="prompt-grid">{prompts.map((prompt) => <button onClick={() => void ask(prompt)} key={prompt}>{prompt}<ArrowRight /></button>)}</div>}
      <form className="chat-composer" onSubmit={submit}><label className="sr-only" htmlFor="coach-question">Ask about your money</label><input id="coach-question" maxLength={500} placeholder="Ask about your money…" value={question} onChange={(event) => setQuestion(event.target.value)} /><button disabled={!question.trim() || busy} aria-label="Send question"><Send /></button></form>
    </section>
    {evidence && <EvidenceDrawer evidence={evidence} close={() => setEvidence(undefined)} />}
  </div>;
}

type Report = {period_range: {start: string; end: string}; snapshot: {income: number; spent: number; net: number}; spending: SpendingSummary; comparison: {categories: Change[]; summary: string}; story: MoneyStory; budget: CurrentBudget; goals: Goal[]; health: Health; forecast: {expected_closing_balance: number; confidence_range: {low: number; high: number}}; ai_summary: {text: string}};

export function ReportsPage() {
  const {data, error, reload} = useResource<Report>('/reports/monthly');
  if (error) return <ErrorState message={error} retry={reload} />;
  if (!data) return <LoadingPage label="Preparing your monthly report" />;
  return <div className="page">
    <PageHeader eyebrow="Reports" title="Your month in money" description={`${formatDate(data.period_range.start)}–${formatDate(data.period_range.end, true)} · Historical totals are calculated; forecasts are estimates.`} />
    <div className="report-snapshot"><span><small>Income</small><strong>{formatBDT(data.snapshot.income)}</strong></span><span><small>Spent</small><strong>{formatBDT(data.snapshot.spent)}</strong></span><span><small>Net</small><strong className={data.snapshot.net >= 0 ? 'money-positive-light' : 'money-negative-light'}>{formatBDT(data.snapshot.net, true)}</strong></span></div>
    <div className="dashboard-grid"><section className="card grid-span-7"><div className="card__header"><div><span className="eyebrow">Top categories</span><h2>Where money went</h2></div><Tag tone="ai">Calculated</Tag></div><div className="chart chart--bar"><ResponsiveContainer width="100%" height="100%"><BarChart data={data.spending.category_totals.slice(0, 6)} layout="vertical" margin={{left: 8, right: 18}}><CartesianGrid horizontal={false} stroke="#EDF0F2"/><XAxis type="number" hide/><YAxis type="category" dataKey="category" width={92} axisLine={false} tickLine={false} fontSize={12}/><Tooltip formatter={(value) => formatBDT(Number(value))}/><Bar dataKey="amount" fill="#179EC1" radius={[0,6,6,0]} /></BarChart></ResponsiveContainer></div></section><section className="card grid-span-5 report-ai"><Sparkles /><span className="eyebrow">AI summary</span><h2>What mattered most</h2><p>{data.ai_summary.text}</p><TrustBadge>Based on your transaction history</TrustBadge></section><div className="grid-span-7"><WhatChangedCard changes={data.comparison.categories} summary={data.comparison.summary} /></div><div className="grid-span-5"><HealthScoreCard health={data.health} /></div><div className="grid-span-12"><MoneyStoryTimeline story={data.story} /></div></div>
  </div>;
}

type Lesson = {id: string; title: string; trigger_reason: string; duration_minutes: number; content: string; action: string};

export function LearnPage() {
  const {data, error, reload} = useResource<{lessons: Lesson[]}>('/learning/recommended');
  const [selected, setSelected] = useState<Lesson>();
  const [completed, setCompleted] = useState<string[]>([]);
  if (error) return <ErrorState message={error} retry={reload} />;
  if (!data) return <LoadingPage label="Finding relevant lessons" />;
  const complete = async (lesson: Lesson) => { await api(`/learning/${lesson.id}/complete`, {method: 'POST'}); setCompleted([...completed, lesson.id]); setSelected(undefined); };
  return <div className="page"><PageHeader eyebrow="Learn" title="Learn from your own money" description="Short lessons triggered by patterns in your synthetic demo activity." /><div className="lesson-grid">{data.lessons.map((lesson) => <article className="card lesson-card" key={lesson.id}><div className="lesson-card__icon"><BookOpen /></div><Tag tone="ai">{lesson.duration_minutes} min read</Tag><h2>{lesson.title}</h2><p>{lesson.content}</p><div className="lesson-trigger"><span>Why you’re seeing this</span><strong>{lesson.trigger_reason}</strong></div><button className="button button--secondary" onClick={() => setSelected(lesson)}>{completed.includes(lesson.id) ? <><Check />Completed</> : <>Learn <ArrowRight /></>}</button></article>)}</div>{selected && <Sheet title={selected.title} close={() => setSelected(undefined)}><Tag tone="ai">{selected.duration_minutes} min read</Tag><div className="lesson-content"><p>{selected.content}</p><h3>Try this</h3><p>{selected.action}</p><p>A small weekly target can be easier to notice and adjust than one large monthly number. Use it as a guide, not a restriction.</p></div><button className="button button--full" onClick={() => void complete(selected)}><Check />Mark complete</button></Sheet>}</div>;
}

type Offer = {id: string; title: string; terms: string; typical_purchase: number; potential_saving: number; purchase_count: number; why: string};

export function OffersPage() {
  const {data, error, reload} = useResource<{opt_in: boolean; offers: Offer[]; disclaimer: string}>('/offers/recommended');
  const [enabled, setEnabled] = useState(true);
  const [selected, setSelected] = useState<Offer>();
  useEffect(() => { if (data) setEnabled(data.opt_in); }, [data]);
  const toggle = async (value: boolean) => { setEnabled(value); await api(`/offers/preferences?enabled=${value}`, {method: 'PATCH'}); };
  if (error) return <ErrorState message={error} retry={reload} />;
  if (!data) return <LoadingPage label="Checking relevant savings" />;
  return <div className="page"><PageHeader eyebrow="upay Offers · Smart layer" title="Relevant savings" description="Offers appear only when they relate to spending you already make." action={<label className="switch"><input type="checkbox" checked={enabled} onChange={(event) => void toggle(event.target.checked)} /><span />Personalized offers</label>} />{enabled ? data.offers.length ? <div className="offer-grid">{data.offers.map((offer) => <article className="card offer-card" key={offer.id}><div className="offer-card__visual"><Gift /><Tag tone="positive">If you’re already buying</Tag></div><h2>{offer.title}</h2><p>{offer.terms}</p><div className="offer-metrics"><span><small>Typical purchase</small><strong>{formatBDT(offer.typical_purchase)}</strong></span><span><small>Potential saving</small><strong className="money-positive">~{formatBDT(offer.potential_saving)}</strong></span></div><div className="offer-why"><Lightbulb /><span><small>Why this appeared</small><strong>{offer.why}</strong></span></div><button className="button button--secondary" onClick={() => setSelected(offer)}>View upay Offer <ExternalLink /></button></article>)}</div> : <EmptyState title="No relevant savings right now" description="We’ll only show an offer when it matches spending you already make." /> : <EmptyState title="Personalized offers are off" description="Turn them on when you want to see relevant savings opportunities." />}{selected && <Sheet title={selected.title} close={() => setSelected(undefined)}><div className="offer-detail"><Gift /><p>{selected.terms}</p><div className="offer-metrics"><span><small>Typical purchase</small><strong>{formatBDT(selected.typical_purchase)}</strong></span><span><small>Potential saving</small><strong>{formatBDT(selected.potential_saving)}</strong></span></div><p>{data.disclaimer}</p><TrustBadge>Concept offer integration</TrustBadge></div></Sheet>}</div>;
}
