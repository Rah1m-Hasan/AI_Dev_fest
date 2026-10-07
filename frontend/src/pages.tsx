import {useEffect, useState} from 'react';
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import {
  ArrowRight,
  AlertTriangle,
  BookOpen,
  BrainCircuit,
  CalendarDays,
  Check,
  CheckCircle2,
  ChevronRight,
  CircleDollarSign,
  CircleHelp,
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
  SlidersHorizontal,
  TrendingUp,
  WalletCards,
  X,
  Zap,
  Bookmark,
  BookmarkCheck,
} from 'lucide-react';
import {Link, useNavigate} from 'react-router-dom';
import {api} from './api/client';
import {formatBDT, formatDate, titleCase} from './format';
import type {
  BudgetRecommendation,
  Change,
  DashboardSummary,
  DemoUser,
  Goal,
  MonthlyPlan,
  PlanWorkspace,
  Health,
  MoneyRunway,
  MoneyStory,
  SafeToSave,
  Transaction,
} from './types';
import { LearnExperience } from './components/learn/LearnExperience';
import { OffersExperience } from './components/offers/OffersExperience';
import {
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
import {FinancialHealthExperience, type FinancialHealthReport} from './components/health/FinancialHealthExperience';
import {SavingsGoalsExperience} from './components/goals/SavingsGoalsExperience';
import {ExplainMetricButton} from './components/ExplainMetricButton';
import {
  CategoryComparison,
  CategoryDetailDrawer,
  ChangeRanking,
  ExploreActions,
  FinancialHealthSummary,
  InsightExplanation,
  MoneyStoryTimeline as InsightsMoneyStory,
  TopInsight,
} from './components/insights/InsightsExperience';

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

function OverviewSectionHeader({title, description, action, headingId}: {title: string; description?: string; action?: React.ReactNode; headingId?: string}) {
  return <div className="overview-section-header"><div><h2 id={headingId}>{title}</h2>{description && <p>{description}</p>}</div>{action}</div>;
}

function FinancialIndicatorRow({data}: {data: DashboardSummary}) {
  const pulseTone = /tight|watch|attention/i.test(data.pulse.status) ? 'warning' : 'positive';
  return <div className="financial-indicators" aria-label="Financial health indicators">
    <div><span>Safe to spend</span><strong>{formatBDT(data.safe_to_spend.safe_to_spend)}</strong><ExplainMetricButton metric={{metricId: 'safe_to_spend', title: 'Safe to Spend', value: data.safe_to_spend.safe_to_spend, unit: 'BDT', source: 'overview', context: {currentBalance: data.safe_to_spend.current_balance, upcomingCommittedExpenses: data.safe_to_spend.upcoming_committed_expenses, recommendedReserve: data.safe_to_spend.recommended_reserve}}} /></div>
    <div><span>Money runway</span><strong>~{data.runway.days} days</strong><ExplainMetricButton metric={{metricId: 'money_runway', title: 'Money Runway', value: data.runway.days, unit: 'days', source: 'overview', context: {todayBalance: data.runway.today_balance, expected14DayExpenses: data.runway.expected_14_day_expenses, expected14DayIncome: data.runway.expected_14_day_income, confidence: data.runway.confidence}}} /></div>
    <div><span>Money pulse</span><strong className={`indicator-status indicator-status--${pulseTone}`}>{data.pulse.status}</strong><span className="financial-indicator__action" aria-hidden="true" /></div>
  </div>;
}

function FinancialSnapshot({data}: {data: DashboardSummary}) {
  const savingsRate = data.this_month.income > 0 ? Math.round(data.this_month.savings / data.this_month.income * 1000) / 10 : 0;
  const remainingBudget = Math.max(0, data.budget.limit - data.budget.used);
  return <section className="financial-snapshot" aria-labelledby="financial-snapshot-title">
    <div className="financial-snapshot__topline"><span id="financial-snapshot-title">Your financial picture</span><div className="financial-snapshot__budget"><small>Remaining budget</small><strong>{formatBDT(remainingBudget)}</strong><ExplainMetricButton metric={{metricId: 'remaining_budget', title: 'Remaining Budget', value: remainingBudget, unit: 'BDT', source: 'overview', context: {budgetLimit: data.budget.limit, budgetUsed: data.budget.used, utilization: data.budget.utilization}}} /><small>Last 30 days</small></div></div>
    <div className="financial-snapshot__main">
      <div className="available-balance"><span>Available balance</span><strong>{formatBDT(data.balance)}</strong></div>
      <div className="cashflow-metrics">
        <div><small>Income this month</small><strong>{formatBDT(data.this_month.income)}</strong><span className="metric-action-slot" aria-hidden="true" /></div>
        <div><small>Spending this month</small><strong>{formatBDT(data.this_month.spending)}</strong><div className="metric-action-slot"><ExplainMetricButton metric={{metricId: 'monthly_spending', title: 'Spent This Month', value: data.this_month.spending, unit: 'BDT', source: 'overview', context: {period: data.period_label}}} /></div></div>
        <div><small>Savings rate</small><strong className={savingsRate >= 0 ? 'money-positive' : 'money-negative'}>{savingsRate}%</strong><div className="metric-action-slot"><ExplainMetricButton metric={{metricId: 'savings_rate', title: 'Savings Rate', value: savingsRate, unit: '%', source: 'overview', context: {monthlyIncome: data.this_month.income, monthlySavings: data.this_month.savings}}} /></div></div>
      </div>
    </div>
    <FinancialIndicatorRow data={data} />
  </section>;
}

function PrimaryInsight({data, onEvidence}: {data: DashboardSummary; onEvidence: () => void}) {
  const increases = data.comparison.categories.filter((item) => item.difference > 0);
  const lead = increases[0] || data.comparison.categories[0];
  const supporting = increases[1];
  const change = lead?.change_percent === null ? 'new this period' : `${lead?.change_percent && lead.change_percent > 0 ? '+' : ''}${lead?.change_percent || 0}%`;
  const headline = lead ? `${lead.category} spending ${lead.difference > 0 ? 'increased' : 'changed'} ${change}` : 'Your spending is relatively stable this period.';
  const explanation = lead
    ? `You spent ${formatBDT(Math.abs(lead.difference))} ${lead.difference > 0 ? 'more' : 'less'} on ${lead.category}${supporting ? ` and ${formatBDT(Math.abs(supporting.difference))} more on ${supporting.category}` : ''} compared with the previous period.`
    : data.comparison.summary;
  const impact = data.pulse.headline || data.pulse.text || data.comparison.summary;
  return <section className="primary-insight" aria-labelledby="what-changed-title">
    <OverviewSectionHeader headingId="what-changed-title" title="What changed" description="The clearest shift in your recent activity." />
    <div className="primary-insight__grid">
      <article className="primary-insight__signal">
        <div className="primary-insight__signal-label"><span aria-hidden="true"><TrendingUp /></span><small>Change</small></div>
        <h3>{headline}</h3>
      </article>
      <div className="primary-insight__details">
        <section><small>Why it matters</small><p>{explanation}</p></section>
        <section><small>Impact</small><p>{impact}</p></section>
      </div>
    </div>
    <div className="primary-insight__actions"><button className="button button--small" onClick={onEvidence}>See breakdown <ArrowRight /></button>{lead && <ExplainMetricButton metric={{metricId: 'spending_category_change', title: `${lead.category} Spending Change`, value: lead.difference, unit: 'BDT', source: 'overview', context: {category: lead.category, current: lead.current, previous: lead.previous, changePercent: lead.change_percent ?? 'New activity'}}} />}</div>
  </section>;
}

function ForecastSection({data}: {data: DashboardSummary}) {
  const {runway, safe_to_save: safe} = data;
  const points = [{name: 'Today', balance: runway.today_balance}, {name: '7 days', balance: (runway.today_balance + runway.expected_14_day_balance) / 2}, {name: '14 days', balance: runway.expected_14_day_balance}];
  const safeRows = [
    ['Available balance', safe.breakdown.available_balance], ['Expected income', safe.breakdown.expected_income], ['Expected bills', -safe.breakdown.upcoming_bills], ['Typical spending', -safe.breakdown.typical_spending], ['Safety buffer', -safe.breakdown.safety_buffer],
  ] as const;
  return <section className="looking-ahead" aria-labelledby="looking-ahead-title">
    <OverviewSectionHeader title="Looking ahead" description="A simple estimate of what is likely to happen next." action={<Link className="text-button" to="/coach/assistant">View full forecast <ArrowRight /></Link>} />
    <div className="looking-ahead__grid">
      <article className="ahead-block runway-block"><div><span className="eyebrow">Money runway</span><h3 id="looking-ahead-title">~{runway.days} days</h3><p>At your recent spending pace.</p><ExplainMetricButton metric={{metricId: 'money_runway', title: 'Money Runway', value: runway.days, unit: 'days', source: 'overview_forecast', context: {todayBalance: runway.today_balance, expected14DayExpenses: runway.expected_14_day_expenses, expected14DayIncome: runway.expected_14_day_income, confidence: runway.confidence}}} /></div><small className="confidence">Estimated · confidence: {runway.confidence}</small>
        <div className="overview-runway-chart" role="img" aria-label={`Estimated balance from today to 14 days: ${formatBDT(runway.today_balance)} to ${formatBDT(runway.expected_14_day_balance)}`}><ResponsiveContainer width="100%" height="100%"><AreaChart data={points}><defs><linearGradient id="overviewRunwayFill" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#167da7" stopOpacity={0.22}/><stop offset="95%" stopColor="#167da7" stopOpacity={0}/></linearGradient></defs><XAxis dataKey="name" axisLine={false} tickLine={false} fontSize={11}/><Tooltip formatter={(value) => formatBDT(Number(value))}/><Area type="monotone" dataKey="balance" stroke="#075A8C" strokeWidth={2.5} fill="url(#overviewRunwayFill)" /></AreaChart></ResponsiveContainer></div>
        <details className="overview-details"><summary>Forecast details</summary><div className="metric-list"><span><small>Current</small><strong>{formatBDT(runway.today_balance)}</strong></span><span><small>Expected spending</small><strong>-{formatBDT(runway.expected_14_day_expenses)}</strong></span><span><small>Expected balance</small><strong>{formatBDT(runway.expected_14_day_balance)}</strong></span></div></details>
      </article>
      <article className="ahead-block commitments-block"><div className="card__header"><div><span className="eyebrow">Next 14 days</span><h3>Upcoming commitments</h3></div><CalendarDays aria-hidden="true" /></div>{runway.upcoming.length ? <div className="commitment-list">{runway.upcoming.slice(0, 4).map((item) => <div key={`${item.merchant}-${item.expected_date}`}><span><strong>{item.merchant}</strong><small>{formatDate(item.expected_date)} · recurring</small></span><strong>~{formatBDT(item.amount)}</strong></div>)}</div> : <p className="empty-copy">No recurring payments expected in the next 14 days.</p>}</article>
    </div>
    <div className="save-opportunity"><PiggyBank aria-hidden="true" /><div><span>Safe to save this week</span><strong>{safe.high > 0 ? `${formatBDT(safe.low)}–${formatBDT(safe.high)}` : 'Pause this week'}</strong><p>{safe.high > 0 ? `You could set this aside over the next ${safe.period_days} days without reducing your current buffer.` : 'Saving extra this week may reduce your current buffer.'}</p><details className="overview-details"><summary>See calculation</summary><div className="safe-breakdown">{safeRows.map(([label, value]) => <span key={label}><small>{label}</small><strong className={value < 0 ? 'money-negative' : ''}>{formatBDT(value, value > 0 && label === 'Expected income')}</strong></span>)}</div></details></div><Link className="text-button" to="/coach/goals">Add to savings goal <ArrowRight /></Link></div>
  </section>;
}

function SpendingBreakdown({items}: {items: DashboardSummary['spending_breakdown']}) {
  return <section className="spending-breakdown" aria-labelledby="spending-breakdown-title"><OverviewSectionHeader headingId="spending-breakdown-title" title="Where your money went" description="Your five largest spending categories." action={<Link className="text-button" to="/coach/transactions">View all categories <ArrowRight /></Link>} /><div className="category-bars">{items.slice(0, 5).map((item) => <div key={item.category}><span><strong>{item.category}</strong><small>{formatBDT(item.amount)}</small></span><progress value={item.percentage} max="100" aria-label={`${item.category}: ${item.percentage}% of spending`} /><small>{item.percentage}%</small></div>)}</div>{!items.length && <p className="empty-copy">No spending categories are available for this period.</p>}</section>;
}

function CompactMoneyStory({story}: {story: MoneyStory}) {
  const events = story.events.slice(-4);
  return <section className="companion-panel" aria-labelledby="money-story-title"><OverviewSectionHeader headingId="money-story-title" title="Your Money Story" description={`${formatDate(story.period.start)}–${formatDate(story.period.end, true)}`} action={<Link className="text-button" to="/coach/insights">View full story <ArrowRight /></Link>} /><div className="story-timeline">{events.length ? events.map((event, index) => <div className="story-event" key={`${event.date}-${event.title}-${index}`}><time>{formatDate(event.date)}</time><span className={`story-event__dot story-event__dot--${event.type}`} /><span><strong>{event.title}</strong><small>{event.detail}</small></span><strong className={event.type === 'income' || event.amount < 0 ? 'money-positive' : ''}>{formatBDT(event.amount, event.type === 'income')}</strong></div>) : <p className="empty-copy">Your financial story will appear as activity builds.</p>}</div></section>;
}

function RecentActivity({transactions}: {transactions: Transaction[]}) {
  return <section className="companion-panel recent-activity" aria-labelledby="recent-activity-title"><OverviewSectionHeader headingId="recent-activity-title" title="Recent activity" action={<Link className="text-button" to="/coach/transactions">View all transactions <ArrowRight /></Link>} /><div>{transactions.length ? transactions.slice(0, 5).map((transaction) => <TransactionRow transaction={transaction} key={transaction.id} />) : <p className="empty-copy">No recent activity yet.</p>}</div></section>;
}

export function PulsePage({user}: {user: DemoUser}) {
  const {data, error, reload} = useResource<DashboardSummary>('/dashboard/summary');
  const [evidence, setEvidence] = useState<Record<string, unknown>>();
  if (error) return <ErrorState message={error} retry={reload} />;
  if (!data) return <LoadingPage />;
  return <div className="page overview-page">
    <PageHeader eyebrow="Overview" title={`Financial picture, ${user.display_name.split(' ')[0]}.`} description="A calm summary of your money now, what changed, and what comes next." action={<Tag tone="demo">Demo data</Tag>} />
    <FinancialSnapshot data={data} />
    <PrimaryInsight data={data} onEvidence={() => setEvidence(data.comparison as unknown as Record<string, unknown>)} />
    <ForecastSection data={data} />
    <SpendingBreakdown items={data.spending_breakdown} />
    <div className="overview-companions"><CompactMoneyStory story={data.story} /><RecentActivity transactions={data.recent_transactions} /></div>
    {evidence && <EvidenceDrawer evidence={evidence} close={() => setEvidence(undefined)} />}
  </div>;
}

type Intelligence = {comparison: {categories: Change[]; summary: string; period: {start: string; end: string}}; safe_to_save: SafeToSave; runway: MoneyRunway; story: MoneyStory; health: Health};

export function InsightsPage() {
  const {data, error, reload} = useResource<Intelligence>('/intelligence/overview');
  const [evidence, setEvidence] = useState<Record<string, unknown>>();
  const [selectedCategory, setSelectedCategory] = useState<Change>();
  if (error) return <ErrorState message={error} retry={reload} />;
  if (!data) return <LoadingPage label="Loading calculated insights" />;
  const lead = data.comparison.categories[0];
  const comparisonEvidence = data.comparison as unknown as Record<string, unknown>;
  return <div className="page insights-page">
    <PageHeader eyebrow="Financial Insights" title="Understand what changed with your money" description="A clear read of recent behavior, what it means, and where to look next." />
    <TopInsight comparison={data.comparison} onEvidence={() => setEvidence(comparisonEvidence)} />
    <div className="insights-page__narrative">
      <ChangeRanking changes={data.comparison.categories} onSelect={setSelectedCategory} />
      <InsightExplanation comparison={data.comparison} safeToSave={data.safe_to_save} runway={data.runway} />
    </div>
    <div className="insights-page__two-column">
      <CategoryComparison changes={data.comparison.categories} onSelect={setSelectedCategory} />
      <FinancialHealthSummary health={data.health} />
    </div>
    <InsightsMoneyStory story={data.story} />
    <ExploreActions lead={lead} onEvidence={() => setEvidence(comparisonEvidence)} />
    {evidence && <EvidenceDrawer evidence={evidence} close={() => setEvidence(undefined)} />}
    {selectedCategory && <CategoryDetailDrawer category={selectedCategory} close={() => setSelectedCategory(undefined)} />}
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
  const [category, setCategory] = useState(() => new URLSearchParams(window.location.search).get('category') || '');
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

type PlanGoals = {items: Goal[]};
type PlanDraft = MonthlyPlan['allocations'] & {categories: Record<string, number>};
const rounded = (value: number) => Math.round(Number(value || 0) * 100) / 100;
const allocationTotal = (draft: PlanDraft) => rounded(draft.essentials + draft.flexible + draft.savings + draft.safety_buffer);

function PlanEditor({draft: initial, income, save, close}: {draft: PlanDraft; income: number; save: (draft: PlanDraft) => Promise<void>; close: () => void}) {
  const [draft, setDraft] = useState<PlanDraft>(initial); const [busy, setBusy] = useState(false); const [error, setError] = useState('');
  const total = allocationTotal(draft), remaining = rounded(income - total), categoryTotal = rounded(Object.values(draft.categories).reduce((sum, value) => sum + Number(value || 0), 0));
  const updateAllocation = (key: keyof MonthlyPlan['allocations'], value: number) => setDraft({...draft, [key]: Math.max(0, value)});
  const invalid = total > income || categoryTotal > draft.essentials + draft.flexible;
  const submit = async () => {setBusy(true); setError(''); try {await save(draft); close();} catch (reason) {setError(reason instanceof Error ? reason.message : 'Could not save your plan.');} finally {setBusy(false);}};
  return <Sheet title="Customize monthly plan" close={close} wide className="plan-editor"><p className="sheet__intro">Adjust your allocations and category targets. We check the same income and category rules on the server before saving.</p>
    <div className="plan-editor__allocations">{([['essentials','Essentials','Recurring bills and necessary expenses'],['flexible','Flexible','Food, transport and discretionary spending'],['savings','Savings','Available for active savings goals'],['safety_buffer','Safety buffer','Reserved for unexpected expenses']] as const).map(([key,label,description]) => <label className="field" key={key}><span>{label}<small>{description}</small></span><div className="money-input"><span>৳</span><input type="number" min="0" step="1" value={Math.round(draft[key])} onChange={(event) => updateAllocation(key, Number(event.target.value))} /></div><small>{income ? Math.round(draft[key] / income * 100) : 0}% of expected income</small></label>)}</div>
    <section className={`plan-impact ${invalid ? 'plan-impact--warning' : ''}`} aria-live="polite"><strong>{invalid ? 'This plan needs adjustment' : 'Plan impact preview'}</strong><span><small>Remaining after allocations</small><b>{formatBDT(remaining)}</b></span><span><small>Available category spending</small><b>{formatBDT(draft.essentials + draft.flexible)}</b></span><span><small>Goal savings capacity</small><b>{formatBDT(draft.savings)}</b></span>{total > income && <p><AlertTriangle />Your current allocations exceed expected income by {formatBDT(Math.abs(remaining))}.</p>}{categoryTotal > draft.essentials + draft.flexible && <p><AlertTriangle />Category targets exceed your essential and flexible spending by {formatBDT(categoryTotal - draft.essentials - draft.flexible)}.</p>}</section>
    <section className="plan-editor__categories"><div><span className="eyebrow">Category targets</span><h3>Fine-tune where spending goes</h3></div>{Object.entries(draft.categories).sort((a,b) => b[1] - a[1]).map(([name,value]) => <label className="field" key={name}><span>{name}</span><div className="money-input"><span>৳</span><input aria-label={`${name} target`} type="number" min="0" step="1" value={Math.round(value)} onChange={(event) => setDraft({...draft, categories: {...draft.categories, [name]: Math.max(0, Number(event.target.value))}})} /></div></label>)}</section>
    {error && <p className="form-error" role="alert">{error}</p>}<div className="plan-editor__actions"><button className="button button--ghost" onClick={close}>Cancel</button><button className="button" disabled={invalid || busy} onClick={() => void submit()}><Check />{busy ? 'Saving…' : 'Save custom plan'}</button></div>
  </Sheet>;
}

export function PlanPage() {
  const [workspace, setWorkspace] = useState<PlanWorkspace>(); const [dashboard, setDashboard] = useState<DashboardSummary>(); const [goals, setGoals] = useState<Goal[]>([]);
  const [editing, setEditing] = useState(false); const [notice, setNotice] = useState(''); const [error, setError] = useState(''); const [busy, setBusy] = useState(false);
  const load = async () => {setError(''); try {const [plan, dash, goalData] = await Promise.all([api<PlanWorkspace>('/budgets/plan'), api<DashboardSummary>('/dashboard/summary'), api<PlanGoals>('/goals')]); setWorkspace(plan); setDashboard(dash); setGoals(goalData.items);} catch (reason) {setError(reason instanceof Error ? reason.message : "We couldn't load your plan.");}};
  useEffect(() => {void load();}, []); useEffect(() => {if (!notice) return; const id=window.setTimeout(() => setNotice(''), 3500); return () => window.clearTimeout(id);}, [notice]);
  if (error) return <ErrorState message="We couldn't load your plan." retry={() => void load()} />;
  if (!workspace || !dashboard) return <div className="page plan-page"><div className="plan-skeleton" role="status" aria-label="Building your monthly plan"><div className="skeleton skeleton--hero" /><div className="skeleton-grid"><div className="skeleton" /><div className="skeleton" /><div className="skeleton" /></div></div></div>;
  const {recommendation, plan} = workspace; const allocation = plan.allocations; const income = recommendation.period_income; const total = allocationTotal({...allocation, categories: plan.categories}); const spending = allocation.essentials + allocation.flexible; const categoryTotal = Object.values(plan.categories).reduce((sum,value) => sum + value, 0);
  const empty = income <= 0 || !Object.keys(plan.categories).length;
  const draft: PlanDraft = {...allocation, categories: plan.categories}; const savingsRate = income ? allocation.savings / income * 100 : 0; const fixedRatio = income ? recommendation.fixed_recurring_costs / income * 100 : 0; const flexibleRatio = income ? allocation.flexible / income * 100 : 0; const bufferDays = spending ? allocation.safety_buffer / spending * 30.44 : 0;
  const saveDraft = async (next: PlanDraft) => {await api('/budgets/plan', {method: 'PUT', body: JSON.stringify(next)}); setNotice('Custom plan saved. Accept it when you are ready to use it across your budget.'); await load();};
  const accept = async () => {setBusy(true); try {await api('/budgets/plan/accept', {method: 'POST', body: JSON.stringify(draft)}); setNotice('Plan active. Your budget and related plan views now use these targets.'); await load();} catch (reason) {setError(reason instanceof Error ? reason.message : 'Could not activate your plan.');} finally {setBusy(false);}};
  if (empty) return <div className="page plan-page"><PageHeader eyebrow="Plan" title="Your Monthly Plan" description="A personalized plan built from your income, recurring expenses, spending behavior, goals, and financial stability." /><EmptyState title="We need a little more activity to build your monthly plan." description="Add income history, spending history, and recurring expenses so we can calculate a reliable plan." /></div>;
  const statusLabel = plan.status === 'accepted' ? 'Plan Active' : plan.status === 'customized' ? 'Customized plan' : 'Recommended plan';
  const statusTone = plan.status === 'accepted' ? 'positive' : plan.status === 'customized' ? 'warning' : 'ai';
  const warning = flexibleRatio > 50 ? 'Flexible spending is high relative to expected income.' : allocation.safety_buffer < recommendation.buffer_contribution ? 'Your safety buffer is below the calculated recommendation.' : allocation.savings < recommendation.savings_target ? 'Your savings target is below the calculated recommendation.' : '';
  const health = savingsRate >= 10 && allocation.safety_buffer >= recommendation.buffer_contribution ? 'Balanced' : savingsRate > 0 ? 'Needs review' : 'At risk';
  return <div className="page plan-page">
    <PageHeader eyebrow="Plan" title="Your Monthly Plan" description="A personalized plan built from your income, recurring expenses, spending behavior, goals, and financial stability." action={<div className="button-row plan-actions"><button className="button button--secondary" onClick={() => setEditing(true)}><SlidersHorizontal />{plan.status === 'accepted' ? 'Update Plan' : 'Customize Plan'}</button>{plan.status === 'accepted' ? <span className="plan-active-action"><CheckCircle2 />Plan Active</span> : <button className="button" disabled={busy || total > income || categoryTotal > spending} onClick={() => void accept()}><Check />{busy ? 'Activating…' : 'Accept Plan'}</button>}</div>} />
    {notice && <div className="toast" role="status"><CheckCircle2 />{notice}</div>}
    <section className="plan-status" aria-label="Plan status"><Tag tone={statusTone}>{statusLabel}</Tag><span>{plan.status === 'recommended' ? 'Generated from your recent financial behavior' : plan.status === 'accepted' && plan.accepted_at ? `Accepted ${formatDate(plan.accepted_at, true)}` : `Updated ${plan.updated_at ? formatDate(plan.updated_at, true) : 'just now'}`}</span><span><CircleHelp aria-hidden="true" />{titleCase(recommendation.confidence)} confidence based on available history</span></section>
    <section className="plan-hero" aria-labelledby="plan-summary-title"><div className="plan-hero__headline"><span>Recommended monthly spend</span><strong id="plan-summary-title">{formatBDT(spending)}</strong><small>From an estimated monthly income of {formatBDT(income)}</small></div><div className="plan-metrics">{([
      ['Essentials', allocation.essentials, 'Recurring bills and necessary expenses', 'essential'], ['Flexible', allocation.flexible, 'Shopping, food, transport and discretionary spending', 'flexible'], ['Savings', allocation.savings, 'Allocated toward your active goals', 'savings'], ['Safety buffer', allocation.safety_buffer, 'Reserved for unexpected expenses', 'buffer'],
    ] as const).map(([label,value,description,key]) => <div className={`plan-metric plan-metric--${key}`} key={label}><small>{label}</small><strong>{formatBDT(value)}</strong><b>{income ? Math.round(value / income * 100) : 0}% of income</b><span>{description}</span></div>)}</div>
      <div className="allocation-track" role="img" aria-label={`Allocation: essentials ${Math.round(allocation.essentials / income * 100)}%, flexible ${Math.round(allocation.flexible / income * 100)}%, savings ${Math.round(allocation.savings / income * 100)}%, safety buffer ${Math.round(allocation.safety_buffer / income * 100)}%`}>{([['Essentials',allocation.essentials,'essential'],['Flexible',allocation.flexible,'flexible'],['Savings',allocation.savings,'savings'],['Safety buffer',allocation.safety_buffer,'buffer']] as const).map(([label,value,key]) => <span className={`allocation-track__segment allocation-track__segment--${key}`} style={{width: `${income ? value / income * 100 : 0}%`}} title={`${label}: ${formatBDT(value)} (${income ? Math.round(value/income*100) : 0}% of income)`} key={label}><i /></span>)}</div>
      <div className="allocation-legend" aria-label="Allocation legend">{([['Essentials',allocation.essentials,'essential'],['Flexible',allocation.flexible,'flexible'],['Savings',allocation.savings,'savings'],['Safety Buffer',allocation.safety_buffer,'buffer']] as const).map(([label,value,key]) => <span key={label}><i className={`allocation-dot allocation-dot--${key}`} />{label} · {income ? Math.round(value / income * 100) : 0}%</span>)}</div>
    </section>
    {warning && <section className="plan-warning" role="status"><AlertTriangle /><span><strong>Plan check</strong>{warning}</span></section>}
    <section className="plan-health" aria-labelledby="plan-health-title"><div><span className="eyebrow">Plan health</span><h2 id="plan-health-title">{health}</h2><p>Based on your current allocation, not a credit decision.</p></div><div className="plan-health__metrics"><span><small>Savings rate</small><strong>{Math.round(savingsRate)}%</strong></span><span><small>Plan buffer coverage</small><strong>{bufferDays.toFixed(1)} days</strong></span><span><small>Fixed expense ratio</small><strong>{Math.round(fixedRatio)}%</strong></span><span><small>Flexible spend ratio</small><strong>{Math.round(flexibleRatio)}%</strong></span></div></section>
    <div className="plan-links"><Link to="/coach/goals"><Target /><span><strong>Your goals</strong><small>See whether this savings capacity fits your goals</small></span><ChevronRight /></Link><Link to="/coach/scenario"><Compass /><span><strong>Test this plan</strong><small>See what happens if income, spending, or savings changes</small></span><ChevronRight /></Link></div>
    <div className="dashboard-grid plan-workspace-grid"><section className="card grid-span-8 category-plan"><div className="card__header"><div><span className="eyebrow">Category plan</span><h2>Clear targets for each category</h2></div><Tag tone="ai">{titleCase(recommendation.confidence)} confidence</Tag></div><div className="category-plan__list">{Object.entries(plan.categories).sort((a,b) => b[1]-a[1]).map(([name, limit]) => {const actual = dashboard.spending_breakdown.find((item) => item.category === name); const spent=actual?.amount ?? 0; const used=limit ? spent / limit * 100 : 0; const status = !actual ? 'No data' : used > 100 ? 'Over target' : used >= 85 ? 'Near limit' : used < 45 ? 'Under target' : 'Within plan'; const tone=status === 'Over target' ? 'danger' : status === 'Near limit' ? 'warning' : status === 'Within plan' ? 'positive' : 'neutral'; return <article className="category-plan__row" key={name}><div className="category-plan__top"><div><h3>{name}</h3><small>Recommended {formatBDT(limit)} · target range unavailable</small></div><Tag tone={tone === 'danger' ? 'warning' : tone as 'neutral'|'positive'|'warning'}>{status}</Tag></div><div className="category-plan__data"><span><small>Current</small><strong>{actual ? formatBDT(spent) : 'No data'}</strong></span><span><small>Progress</small><strong>{actual ? `${Math.round(used)}% of target used` : '—'}</strong></span></div>{actual && <progress className={used > 100 ? 'over' : ''} value={Math.min(used, 100)} max="100" aria-label={`${name}: ${Math.round(used)}% of target used`} />}</article>;})}</div></section>
      <section className="card grid-span-4 explain-card"><div className="card__header"><div><span className="eyebrow">Explainability</span><h2>Why this plan?</h2></div><Eye /></div><p>{recommendation.reasoning}</p><dl><div><dt>Estimated income</dt><dd>{formatBDT(income)}</dd></div><div><dt>Fixed recurring costs</dt><dd>{formatBDT(recommendation.fixed_recurring_costs)}</dd></div><div><dt>Income stability</dt><dd>{titleCase(recommendation.income_stability)}</dd></div><div><dt>Available safety buffer</dt><dd>{formatBDT(recommendation.emergency_buffer)}</dd></div></dl><div className="explain-card__foot"><Tag tone="ai">Confidence: {titleCase(recommendation.confidence)}</Tag><Link className="text-button" to={`/coach/assistant?prompt=${encodeURIComponent(`Explain why my monthly plan recommends ${formatBDT(spending)} of spending. Use my estimated income of ${formatBDT(income)}, fixed recurring costs of ${formatBDT(recommendation.fixed_recurring_costs)}, savings target of ${formatBDT(allocation.savings)}, and safety buffer of ${formatBDT(allocation.safety_buffer)}.`)}`}><Sparkles />Ask AI to explain</Link></div></section></div>
    <div className="dashboard-grid plan-bottom-grid"><section className="card grid-span-7 plan-goals"><div className="card__header"><div><span className="eyebrow">Your goals</span><h2>What this plan supports</h2></div><Link className="text-button" to="/coach/goals">View goals <ArrowRight /></Link></div>{goals.filter(goal => goal.status === 'active').length ? <div className="plan-goals__list">{goals.filter(goal => goal.status === 'active').slice(0,3).map(goal => {const contribution=goal.planned_monthly_amount || goal.plan.selected_monthly_contribution || goal.plan.recommended_monthly_contribution; return <article key={goal.id}><div><strong>{goal.name}</strong><small>{formatBDT(goal.current_amount)} / {formatBDT(goal.target_amount)} · Target {formatDate(goal.target_date, true)}</small></div><div><b>{formatBDT(contribution)}/month</b><small>{goal.plan.feasible ? 'Goal pace fits calculated capacity' : 'Goal pace needs review'}</small></div><progress value={goal.progress_percent} max="100" aria-label={`${goal.name}: ${goal.progress_percent}% funded`} /></article>;})}</div> : <p className="quiet">No active savings goals yet. Create one to see its calculated contribution pace here.</p>}</section>
      <section className="card grid-span-5 plan-recommendations"><span className="eyebrow">Next best actions</span><h2>Focused recommendations</h2><div>{warning && <Link to="/coach/assistant?prompt=Can you help me make my monthly plan more realistic?"><AlertTriangle />{warning}<ArrowRight /></Link>}{dashboard.spending_breakdown.filter(item => (plan.categories[item.category] || 0) > 0 && item.amount > plan.categories[item.category]).slice(0,2).map(item => <Link key={item.category} to={`/coach/assistant?prompt=${encodeURIComponent(`Why is my ${item.category} spending above my monthly plan? Current spending is ${formatBDT(item.amount)} and my target is ${formatBDT(plan.categories[item.category])}.`)}`}><Sparkles />{item.category} is {formatBDT(item.amount - plan.categories[item.category])} above its target<ArrowRight /></Link>)}{!warning && !dashboard.spending_breakdown.some(item => item.amount > (plan.categories[item.category] || Infinity)) && <Link to="/coach/assistant?prompt=Can I safely save more based on my current monthly plan?"><Sparkles />Ask AI whether more of this plan can go to savings<ArrowRight /></Link>}</div></section></div>
    {editing && <PlanEditor draft={draft} income={income} save={saveDraft} close={() => setEditing(false)} />}
  </div>;
}

export function GoalsPage() {
  return <SavingsGoalsExperience />;
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

type ScenarioKind = 'purchase' | 'reduce_spending' | 'save_more' | 'unexpected_expense' | 'income_delay';
type ScenarioSnapshot = {balance: number; safe_to_spend: number; runway_days: number; monthly_spending: number; health_score: number};
type ScenarioResult = {
  kind: ScenarioKind; amount: number; days: number; category?: string | null; description?: string | null; impact_level: 'low' | 'moderate' | 'high'; explanation: string; warning?: string | null; disclaimer: string; basis: string;
  current: ScenarioSnapshot; projected: ScenarioSnapshot; deltas: {balance: number; safe_to_spend: number; runway_days: number; monthly_spending: number; health_score: number};
  timeline: Array<{day: number; date: string; current_balance: number; scenario_balance: number}>;
  goal_impact?: {name: string; current_progress: number; scenario_progress: number; current_completion?: string | null; scenario_completion?: string | null; outlook: string} | null;
  budget_impact: {has_budget: boolean; before_remaining?: number | null; after_remaining?: number | null; exceeded_by?: number | null};
  alternatives: Array<{label: string; amount: number; runway_days: number; projected_balance: number}>;
};

const scenarioOptions: Array<{value: ScenarioKind; label: string; note: string}> = [
  {value: 'purchase', label: 'Spend money', note: 'See the impact of a purchase today'},
  {value: 'reduce_spending', label: 'Spend less', note: 'Reduce a recurring weekly expense'},
  {value: 'save_more', label: 'Save more', note: 'Set aside more toward your goal'},
  {value: 'unexpected_expense', label: 'Unexpected expense', note: 'Test an emergency or unplanned cost'},
  {value: 'income_delay', label: 'Income delay', note: 'See whether your money lasts longer'},
];

function ScenarioMetric({label, current, projected, delta, format = 'money'}: {label: string; current: number; projected: number; delta: number; format?: 'money' | 'days' | 'score'}) {
  const show = (value: number) => format === 'money' ? formatBDT(value) : format === 'days' ? `${value} days` : `${value}/100`;
  const direction = delta === 0 ? 'neutral' : delta > 0 ? 'up' : 'down';
  const deltaValue = format === 'money' ? formatBDT(Math.abs(delta)) : format === 'days' ? `${Math.abs(delta)} days` : `${Math.abs(delta)} pts`;
  return <article className="scenario-metric"><span>{label}</span><div><strong>{show(current)}</strong><ArrowRight /><strong>{show(projected)}</strong></div><small className={`scenario-metric__delta scenario-metric__delta--${direction}`}>{direction === 'neutral' ? 'No material change' : `${direction === 'up' ? '↑' : '↓'} ${deltaValue}`}</small></article>;
}

export function ScenarioPage() {
  const navigate = useNavigate();
  const [kind, setKind] = useState<ScenarioKind>('purchase');
  const [amount, setAmount] = useState(15000);
  const [horizon, setHorizon] = useState(30);
  const [category, setCategory] = useState('Electronics');
  const [when, setWhen] = useState('today');
  const [description, setDescription] = useState('');
  const [result, setResult] = useState<ScenarioResult>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const selected = scenarioOptions.find((option) => option.value === kind)!;
  const amountLabel = kind === 'reduce_spending' ? 'Reduce each week' : kind === 'income_delay' ? 'Income delay (days)' : kind === 'save_more' ? 'Set aside this month' : 'If I spend';
  const isExpense = kind === 'purchase' || kind === 'unexpected_expense';
  const run = async (scenarioAmount = amount) => {
    if (!Number.isFinite(scenarioAmount) || scenarioAmount <= 0) { setError('Enter an amount greater than zero.'); return; }
    setBusy(true); setError('');
    try {
      const eventDate = when === 'next_week' ? new Date(Date.now() + 7 * 86400000).toISOString().slice(0, 10) : undefined;
      setResult(await api<ScenarioResult>('/scenarios/simulate', {method: 'POST', body: JSON.stringify({kind, amount: scenarioAmount, days: horizon, category: isExpense ? category : undefined, date: eventDate, description: description || undefined})}));
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Unable to run scenario.'); }
    finally { setBusy(false); }
  };
  const choose = (next: ScenarioKind) => { setKind(next); setResult(undefined); setError(''); if (next === 'income_delay') setAmount(7); else if (next === 'reduce_spending') setAmount(500); else if (next === 'save_more') setAmount(2000); else setAmount(15000); };
  const askAI = () => {
    if (!result) return;
    const prompt = `Explain this simulation only (do not make changes): I am exploring ${selected.label.toLowerCase()} of ${formatBDT(result.amount)} over ${result.days} days. Current balance ${formatBDT(result.current.balance)}, Safe to Spend ${formatBDT(result.current.safe_to_spend)}, runway ${result.current.runway_days} days. Scenario balance ${formatBDT(result.projected.balance)}, Safe to Spend ${formatBDT(result.projected.safe_to_spend)}, runway ${result.projected.runway_days} days. Why do these numbers change?`;
    navigate(`/coach/assistant?prompt=${encodeURIComponent(prompt)}`);
  };
  const examples = [
    {label: 'What if I spend ৳10,000 today?', kind: 'purchase' as ScenarioKind, amount: 10000},
    {label: 'What if I save ৳2,000 more this month?', kind: 'save_more' as ScenarioKind, amount: 2000},
    {label: 'What if income arrives 10 days late?', kind: 'income_delay' as ScenarioKind, amount: 10},
  ];
  return <div className="page scenario-page">
    <header className="scenario-page__header"><div><span className="eyebrow">Financial sandbox</span><h1>Scenario Lab</h1><p>See how financial decisions could affect your future without changing your actual account.</p></div><div><Tag tone="ai">Simulation only</Tag><small>Calculated from your current demo data</small></div></header>
    <div className="scenario-layout">
      <section className="card scenario-builder"><div className="card__header"><div><span className="eyebrow">Build a scenario</span><h2>What happens if…</h2></div><Compass /></div>
        <div className="scenario-options">{scenarioOptions.map((option) => <button type="button" className={kind === option.value ? 'active' : ''} onClick={() => choose(option.value)} key={option.value}><span><strong>{option.label}</strong><small>{option.note}</small></span><Check /></button>)}</div>
        <div className="scenario-form">
          <label className="field"><span>{amountLabel}{kind !== 'income_delay' && ' (৳)'}</span><input aria-label={amountLabel} type="number" min="1" max={kind === 'income_delay' ? 90 : 1000000} value={amount} onChange={(event) => setAmount(Number(event.target.value))} /></label>
          {isExpense && <><label className="field"><span>On</span><select value={category} onChange={(event) => setCategory(event.target.value)}><option>Electronics</option><option>Shopping</option><option>Healthcare</option><option>Education</option><option>Other</option></select></label><label className="field"><span>When</span><select value={when} onChange={(event) => setWhen(event.target.value)}><option value="today">Today</option><option value="next_week">In 7 days</option></select></label><label className="field"><span>Purchase name <small>(optional)</small></span><input maxLength={100} placeholder="e.g. New phone" value={description} onChange={(event) => setDescription(event.target.value)} /></label></>}
          <div className="scenario-horizon"><span>Projection period</span><div>{[[7, '7 days'], [30, '30 days'], [90, '3 months']].map(([value, label]) => <button type="button" className={horizon === value ? 'active' : ''} onClick={() => setHorizon(Number(value))} key={value}>{label}</button>)}</div></div>
          <button className="button button--full" disabled={busy || amount <= 0} onClick={() => void run()}><Zap />{busy ? 'Simulating your financial future…' : 'Run simulation'}</button>
        </div>
        <TrustBadge>Simulation only — no changes will be made to your account.</TrustBadge>{error && <p className="form-error" role="alert">{error}</p>}
      </section>
      {!result ? <section className="scenario-empty"><span><Compass /></span><h2>Explore a financial decision</h2><p>Choose a scenario and we’ll compare your current forecast with the simulated outcome. Nothing here changes your actual account.</p><div>{examples.map((example) => <button key={example.label} onClick={() => { choose(example.kind); setAmount(example.amount); }}>{example.label}<ArrowRight /></button>)}</div></section> : <section className="scenario-results">
        <div className="scenario-summary"><div><Tag tone={result.impact_level === 'high' ? 'warning' : result.impact_level === 'low' ? 'positive' : 'ai'}>{titleCase(result.impact_level)} impact</Tag><h2>If you {kind === 'income_delay' ? `delay income by ${result.amount} days` : `${kind === 'reduce_spending' ? 'spend less by' : kind === 'save_more' ? 'set aside' : 'spend'} ${formatBDT(result.amount)}`}</h2><p>{result.explanation}</p></div><button className="button button--secondary button--small" onClick={() => setResult(undefined)}><Edit3 />Edit scenario</button></div>
        {result.warning && <p className="scenario-warning">{result.warning}</p>}
        <div className="scenario-comparison"><ScenarioMetric label="Balance" current={result.current.balance} projected={result.projected.balance} delta={result.deltas.balance} /><ScenarioMetric label="Safe to Spend" current={result.current.safe_to_spend} projected={result.projected.safe_to_spend} delta={result.deltas.safe_to_spend} /><ScenarioMetric label="Money Runway" current={result.current.runway_days} projected={result.projected.runway_days} delta={result.deltas.runway_days} format="days" /><ScenarioMetric label="Monthly spending" current={result.current.monthly_spending} projected={result.projected.monthly_spending} delta={result.deltas.monthly_spending} /><ScenarioMetric label="Financial health" current={result.current.health_score} projected={result.projected.health_score} delta={result.deltas.health_score} format="score" /></div>
        <section className="scenario-chart"><div className="card__header"><div><span className="eyebrow">Estimated future</span><h2>Projected balance</h2></div><small>Current forecast vs scenario</small></div><div className="scenario-chart__canvas"><ResponsiveContainer width="100%" height="100%"><LineChart data={result.timeline} margin={{top: 10, right: 8, left: 0, bottom: 0}}><CartesianGrid vertical={false} stroke="#e7eef1" /><XAxis dataKey="day" tickFormatter={(value) => value === 0 ? 'Today' : `Day ${value}`} tickLine={false} axisLine={false} interval="preserveStartEnd" /><YAxis tickFormatter={(value) => `৳${Math.round(value / 1000)}k`} width={46} tickLine={false} axisLine={false} /><Tooltip formatter={(value, name) => [formatBDT(Number(value || 0)), name === 'Current forecast' ? 'Current forecast' : 'Scenario forecast']} labelFormatter={(value) => value === 0 ? 'Today' : `Day ${value}`} /><Line type="monotone" dataKey="current_balance" name="Current forecast" stroke="#7893a1" strokeWidth={2} dot={false} /><Line type="monotone" dataKey="scenario_balance" name="Scenario forecast" stroke="#087cb0" strokeWidth={2.5} dot={false} /></LineChart></ResponsiveContainer></div></section>
      </section>}</div>
    {result && <><div className="scenario-detail-grid"><section className="card scenario-detail"><span className="eyebrow">Monthly budget</span><h2>{result.budget_impact.has_budget ? 'Impact on your budget' : 'No active budget'}</h2>{result.budget_impact.has_budget ? <><div className="scenario-detail__numbers"><span><small>Before</small><strong>{formatBDT(result.budget_impact.before_remaining || 0)} remaining</strong></span><ArrowRight /><span><small>After</small><strong className={(result.budget_impact.after_remaining || 0) < 0 ? 'money-negative' : ''}>{formatBDT(result.budget_impact.after_remaining || 0)} remaining</strong></span></div><p>{(result.budget_impact.exceeded_by || 0) > 0 ? `This simulation would exceed your remaining monthly budget by ${formatBDT(result.budget_impact.exceeded_by || 0)}.` : 'This estimate stays within the remaining budget based on your current month.'}</p></> : <p>Create a monthly plan to see how a scenario affects remaining budget.</p>}</section>
      <section className="card scenario-detail"><span className="eyebrow">Savings goals</span><h2>{result.goal_impact ? result.goal_impact.name : 'No active goal'}</h2>{result.goal_impact ? <><div className="scenario-detail__numbers"><span><small>Current progress</small><strong>{result.goal_impact.current_progress}%</strong></span><ArrowRight /><span><small>Scenario outlook</small><strong>{result.goal_impact.scenario_progress}%</strong></span></div><p>{result.goal_impact.outlook === 'improved' ? 'The simulated change improves your estimated goal outlook.' : result.goal_impact.outlook === 'at_risk' ? 'The simulated cost could reduce the pace available for this goal.' : 'No meaningful progress change is assumed for this scenario.'}</p></> : <p>No active savings goal is available to include in this simulation.</p>}</section>
      <section className="card scenario-detail scenario-learning"><span className="eyebrow">What this teaches</span><h2>{kind === 'reduce_spending' ? 'Recurring changes add up' : 'Money runway protects flexibility'}</h2><p>{kind === 'reduce_spending' ? 'A weekly change affects every future week, so even a modest reduction can improve your estimated financial flexibility.' : 'Money runway estimates how long available money may last at your current spending pattern. Larger costs can lower both your balance and the days it is expected to cover.'}</p></section></div>
      {result.alternatives.length > 0 && <section className="scenario-alternatives"><div><span className="eyebrow">Explore alternatives</span><h2>Compare a lower-impact choice</h2></div><div>{result.alternatives.map((alternative) => <button key={alternative.label} onClick={() => {setAmount(alternative.amount); void run(alternative.amount);}}><span><strong>{alternative.label}</strong><small>Try {formatBDT(alternative.amount)} · estimated runway {alternative.runway_days} days</small></span><ArrowRight /></button>)}</div></section>}
      <section className="scenario-ai-action"><Sparkles /><div><strong>Ask AI about this scenario</strong><span>AI Assist will explain these deterministic results; it will not calculate or change your account.</span></div><button className="button" onClick={askAI}>Ask AI <ArrowRight /></button></section>
      <div className="scenario-reset"><button className="text-button" onClick={() => {setResult(undefined); setDescription('');}}>Reset simulation</button><small>{result.disclaimer}</small></div></>}
  </div>;
}

export function ReportsPage() {
  const report = useResource<FinancialHealthReport>('/reports/monthly');
  const history = useResource<{history: Array<{month: string; score: number}>; note?: string}>('/financial-health/history');
  if (report.error) return <ErrorState message={report.error} retry={report.reload} />;
  if (!report.data) return <LoadingPage label="Preparing your financial health assessment" />;
  return <FinancialHealthExperience report={report.data} history={history.data} />;
}

export function LearnPage() {
  return <LearnExperience />;
}

export function OffersPage() {
  return <OffersExperience />;
}
