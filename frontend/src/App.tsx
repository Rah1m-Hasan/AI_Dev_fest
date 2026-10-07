import {useEffect, useState, type FocusEvent, type MouseEvent} from 'react';
import {
  Bell,
  BookOpen,
  BrainCircuit,
  ChevronDown,
  CircleHelp,
  FileBarChart,
  Gift,
  History,
  Home,
  Landmark,
  Lightbulb,
  Menu,
  MessageCircle,
  MoreHorizontal,
  PiggyBank,
  ReceiptText,
  Send,
  ShieldCheck,
  Smartphone,
  Sparkles,
  Target,
  UserRound,
  WalletCards,
  X,
  Zap,
  UsersRound,
  Accessibility,
  HandHeart,
  Eye,
  EyeOff,
  ArrowUpRight,
  ArrowRight,
  CircleDollarSign,
  Compass,
  HeartHandshake,
  Activity,
  CalendarDays,
  TrendingDown,
} from 'lucide-react';
import {Link, Navigate, NavLink, Route, Routes, useLocation, useNavigate} from 'react-router-dom';
import {api, token} from './api/client';
import {Brand, Tag, TrustBadge} from './components/ui';
import {ExplainMetricButton} from './components/ExplainMetricButton';
import type {DashboardSummary, DemoUser, MlMetrics, MlSummary} from './types';
import {formatBDT, titleCase} from './format';
import {
  GoalsPage,
  HistoryPage,
  InsightsPage,
  LearnPage,
  OffersPage,
  PlanPage,
  PulsePage,
  ReportsPage,
  ScenarioPage,
} from './pages';
import {CoachPanel} from './components/coach/CoachPanel';
import {ContactsPage, TrustedHelperPage} from './components/people/PeoplePages';

const profiles = [
  {email: 'demo.student@upay.local', name: 'Arif', persona: 'Student', story: 'Month-end pressure'},
  {email: 'demo.salary@upay.local', name: 'Nadia', persona: 'Salaried', story: 'Stable monthly income'},
  {email: 'demo.freelancer@upay.local', name: 'Samiha', persona: 'Freelancer', story: 'Variable income'},
];

type LoginResult = {access_token: string; user: DemoUser};

function Login({onLogin}: {onLogin: (email: string) => Promise<void>}) {
  const [error, setError] = useState('');
  const [busy, setBusy] = useState('');
  const choose = async (email: string) => {
    setBusy(email); setError('');
    try { await onLogin(email); } catch (reason) { setError(reason instanceof Error ? reason.message : 'Unable to start the demo.'); }
    finally { setBusy(''); }
  };
  return <main className="login-screen">
    <section className="login-panel">
      <div className="login-panel__brand">
        <span className="brand__mark">u</span>
        <strong>upay</strong>
        <span className="login-panel__divider" aria-hidden="true" />
        <span>AI Assist</span>
      </div>
      <Tag tone="demo">Hackathon concept prototype · Synthetic data only</Tag>
      <h1>Your money, explained simply.</h1>
      <p>See why your balance changed, what may happen next, and what you can realistically do. No real money moves. No account linked.</p>
      <div className="trust-callout"><ShieldCheck /><span><strong>You stay in control.</strong> AI only explains and suggests — never moves money without your explicit confirmation and PIN.</span></div>
      <p className="login-panel__choose">Choose a demo profile to begin</p>
      <div className="profile-list" aria-label="Choose a demo profile">{profiles.map((profile) => <button className="profile-choice" disabled={Boolean(busy)} onClick={() => void choose(profile.email)} key={profile.email}>
        <span className="avatar">{profile.name[0]}</span><span><strong>{profile.name}</strong><small>{profile.persona} · {profile.story}</small></span><span className="profile-choice__arrow">{busy === profile.email ? 'Loading…' : <ArrowRight />}</span>
      </button>)}</div>
      {error && <p className="form-error" role="alert">{error}</p>}
    </section>
    <aside className="login-visual" aria-hidden="true">
      <div className="phone-preview">
        <div className="phone-preview__top"><span>9:41</span><span>•••</span></div>
        <div className="phone-preview__brand"><span className="brand__mark">u</span><b>upay</b><Bell /></div>
        <small>AVAILABLE BALANCE</small><strong>৳33,502</strong>
        <div className="preview-pulse"><Sparkles /><span><small>MONEY PULSE</small><b>Stable, but spending accelerated this week.</b></span></div>
        <div className="preview-actions"><span><Send />Send money</span><span><Smartphone />Recharge</span><span><BrainCircuit />AI Assist</span></div>
      </div>
    </aside>
  </main>;
}

type ServiceTone = 'gold' | 'blue' | 'green' | 'indigo' | 'amber' | 'teal' | 'cyan' | 'navy' | 'neutral';
type Service = {
  name: string;
  description: string;
  icon: typeof Send;
  to: string;
  tone: ServiceTone;
  featured?: boolean;
  badge?: string;
};

function SectionHeader({title, action}: {title: string; action?: React.ReactNode}) {
  return <div className="section-title"><h2>{title}</h2>{action && <div className="section-title__action">{action}</div>}</div>;
}

function HomeMetric({label, value, tone = 'default', metric}: {label: string; value?: string; tone?: 'default'|'positive'|'negative'; metric?: import('./types').ExplainMetricContext}) {
  return <div className={`home-metric home-metric--${tone}`}>
    <span>{label}</span>
    {value ? <strong>{value}</strong> : <i className="dashboard-skeleton dashboard-skeleton--metric" aria-label={`Loading ${label}`} />}
    <div className="home-metric__action">{metric && <ExplainMetricButton metric={metric} variant="compact" />}</div>
  </div>;
}

function ServiceGrid({services}: {services: Service[]}) {
  return <div className="service-grid" aria-label="upay services">
    {services.map(({name, description, icon: Icon, to, tone, featured, badge}) => <Link className={`service-item service-item--${tone}${featured ? ' service-item--assist' : ''}`} to={to} key={name}>
      <span className="service-item__icon"><Icon aria-hidden="true" /></span>
      <span className="service-item__copy"><strong>{name}</strong><small>{description}</small></span>
      {badge && <span className="service-item__badge">{badge}</span>}
    </Link>)}
  </div>;
}

function QuickActionsSection({services}: {services: Service[]}) {
  return <section className="home-section home-actions" aria-labelledby="quick-actions-title">
    <div className="quick-actions__header">
      <div>
        <h2 id="quick-actions-title">Quick Actions</h2>
        <p>Your most-used money actions</p>
      </div>
      <Link className="quick-actions__view-all" to="/coach/plan">View all <ArrowRight aria-hidden="true" /></Link>
    </div>
    <ServiceGrid services={services} />
  </section>;
}

function FeatureCard({to, icon: Icon, title, description}: {to: string; icon: typeof UsersRound; title: string; description: string}) {
  return <Link className="feature-card" to={to}>
    <span className="feature-card__icon"><Icon aria-hidden="true" /></span>
    <span className="feature-card__copy"><strong>{title}</strong><small>{description}</small></span>
    <ArrowRight aria-hidden="true" />
  </Link>;
}

function HomeOverview({summary, balance, hidden, onToggle, error}: {summary?: DashboardSummary; balance: number; hidden: boolean; onToggle: () => void; error?: boolean}) {
  const mask = (amount: number) => hidden ? '৳ ••••••' : formatBDT(amount);
  return <section className="home-overview" aria-label="Financial overview">
    <div className="home-overview__main">
      <div>
        <span className="overview-label">Available balance</span>
        <strong>{mask(balance)}</strong>
        <small>Your upay wallet balance</small>
      </div>
      <button className="overview-visibility" onClick={onToggle} aria-label={hidden ? 'Show balance' : 'Hide balance'}>{hidden ? <Eye /> : <EyeOff />}</button>
    </div>
    <div className="home-overview__metrics">
      <HomeMetric label="Income this month" value={summary ? mask(summary.this_month.income) : error ? 'Unavailable' : undefined} tone="positive" />
      <HomeMetric label="Spent this month" value={summary ? mask(summary.this_month.spending) : error ? 'Unavailable' : undefined} tone="negative" metric={summary ? {metricId: 'monthly_spending', title: 'Monthly Spending', value: summary.this_month.spending, unit: 'BDT', source: 'home_overview', context: {period: summary.period_label}} : undefined} />
      <HomeMetric label="Safe to spend" value={summary ? mask(summary.safe_to_spend.safe_to_spend) : error ? 'Unavailable' : undefined} tone="positive" metric={summary ? {metricId: 'safe_to_spend', title: 'Safe to Spend', value: summary.safe_to_spend.safe_to_spend, unit: 'BDT', source: 'home_overview', context: {currentBalance: summary.safe_to_spend.current_balance, upcomingCommittedExpenses: summary.safe_to_spend.upcoming_committed_expenses, recommendedReserve: summary.safe_to_spend.recommended_reserve}} : undefined} />
    </div>
  </section>;
}

function FinancialSignals({summary}: {summary: DashboardSummary}) {
  const pulse = summary.pulse.why[0];
  return <section className="home-section">
    <SectionHeader title="Smart financial signals" action={<Link to="/coach/insights">View insights <ArrowRight /></Link>} />
    <div className="signal-grid">
      <article className="signal-card signal-card--safe">
        <span className="signal-card__icon"><ShieldCheck /></span><span className="signal-card__label">Safe to spend</span>
        <strong>{formatBDT(summary.safe_to_spend.safe_to_spend)}</strong><small>After commitments</small><div className="signal-card__actions"><ExplainMetricButton metric={{metricId: 'safe_to_spend', title: 'Safe to Spend', value: summary.safe_to_spend.safe_to_spend, unit: 'BDT', source: 'home_signal', context: {currentBalance: summary.safe_to_spend.current_balance, upcomingCommittedExpenses: summary.safe_to_spend.upcoming_committed_expenses, recommendedReserve: summary.safe_to_spend.recommended_reserve}}} /></div>
      </article>
      <article className="signal-card">
        <span className="signal-card__icon"><CalendarDays /></span><span className="signal-card__label">Money runway</span>
        <strong>~{summary.runway.days} <em>days</em></strong><small>At your current pace</small><div className="signal-card__actions"><ExplainMetricButton metric={{metricId: 'money_runway', title: 'Money Runway', value: summary.runway.days, unit: 'days', source: 'home_signal', context: {todayBalance: summary.runway.today_balance, expected14DayExpenses: summary.runway.expected_14_day_expenses, expected14DayIncome: summary.runway.expected_14_day_income, confidence: summary.runway.confidence}}} /><Link className="signal-card__link" to="/coach">See forecast <ArrowRight /></Link></div>
      </article>
      <Link to="/coach/insights" className="signal-card signal-card--pulse">
        <span className="signal-card__icon"><Activity /></span><span className="signal-card__label">Money pulse</span>
        <strong>{pulse?.label || summary.pulse.status}</strong><small>{pulse?.detail || summary.pulse.headline || 'No new money insights right now.'}</small><span className="signal-card__link">See why <ArrowRight /></span>
      </Link>
    </div>
  </section>;
}

function AIFinancialForecast({forecast}: {forecast?: MlSummary}) {
  const [metrics, setMetrics] = useState<MlMetrics>();
  useEffect(() => { void api<MlMetrics>('/ml/metrics').then(setMetrics).catch(() => undefined); }, []);
  if (!forecast) return null;
  const riskTone = forecast.financial_risk.toLowerCase();
  return <section className="home-section ai-financial-forecast" aria-labelledby="ai-financial-forecast-title">
    <div className="ai-financial-forecast__header"><div><span className="eyebrow">ML-enhanced estimate</span><h2 id="ai-financial-forecast-title">AI Financial Forecast</h2><p>Behavior prediction supports your existing safety calculations.</p></div><Tag tone={forecast.financial_risk === 'LOW' ? 'positive' : 'warning'}>{forecast.financial_risk} risk</Tag></div>
    <div className="ai-financial-forecast__grid">
      <div><small>Predicted spending</small><strong>{formatBDT(forecast.predicted_7_day_spending)}</strong><span>Next 7 days</span></div>
      <div><small>Predicted spending</small><strong>{formatBDT(forecast.predicted_30_day_spending)}</strong><span>Next 30 days</span></div>
      <div className={`ai-risk ai-risk--${riskTone}`}><small>Financial risk</small><strong>{forecast.financial_risk}</strong><span>{forecast.risk_probability === undefined ? 'Liquidity signal' : `${Math.round(forecast.risk_probability * 100)}% model confidence`}</span></div>
      <div><small>Expected month-end balance</small><strong>{formatBDT(forecast.predicted_month_end_balance)}</strong><span>Estimate, not a guarantee</span></div>
      <div><small>Money runway</small><strong>{forecast.money_runway_days} days</strong><span>Using predicted pace</span></div>
      <div><small>Safe-to-spend</small><strong>{formatBDT(forecast.safe_to_spend_per_day)}</strong><span>Per day after reserves</span></div>
    </div>
    <details className="ai-model-metrics"><summary>Model performance for judges</summary>{metrics?.available && metrics.spending_forecast && metrics.risk_classifier ? <div className="ai-model-metrics__grid"><div><strong>Spending Forecast Model</strong><span>{metrics.spending_forecast.algorithm}</span><small>MAE {formatBDT(metrics.spending_forecast.mae)} · RMSE {formatBDT(metrics.spending_forecast.rmse)} · R² {metrics.spending_forecast.r2.toFixed(3)}</small></div><div><strong>Financial Risk Model</strong><span>{metrics.risk_classifier.algorithm}</span><small>Accuracy {(metrics.risk_classifier.accuracy * 100).toFixed(1)}% · Precision {(metrics.risk_classifier.precision * 100).toFixed(1)}% · Recall {(metrics.risk_classifier.recall * 100).toFixed(1)}% · F1 {(metrics.risk_classifier.f1 * 100).toFixed(1)}%{metrics.risk_classifier.roc_auc === null || metrics.risk_classifier.roc_auc === undefined ? '' : ` · ROC-AUC ${metrics.risk_classifier.roc_auc.toFixed(3)}`}</small></div><p>{metrics.training_samples?.toLocaleString()} synthetic training samples · {(metrics.test_split || .2) * 100}% holdout test split</p></div> : <p>Saved model metrics are unavailable; deterministic calculations remain active.</p>}</details>
  </section>;
}

function RecentTransactions({summary, error, retry}: {summary?: DashboardSummary; error?: boolean; retry: () => void}) {
  return <section className="home-section">
    <SectionHeader title="Recent transactions" action={<Link to="/coach/transactions">See all <ArrowRight /></Link>} />
    <div className="home-activity">
      {!summary && !error && <div className="transaction-skeletons" aria-label="Loading recent transactions"><i /><i /><i /><i /></div>}
      {error && <div className="home-empty-state"><TrendingDown /><span><strong>Couldn’t load recent activity.</strong><small>Your wallet balance is still available. Try again to refresh transactions.</small></span><button className="text-button" onClick={retry}>Try again</button></div>}
      {summary?.recent_transactions.length === 0 && <div className="home-empty-state"><History /><span><strong>No recent transactions yet.</strong><small>New wallet activity will appear here.</small></span></div>}
      {summary?.recent_transactions.slice(0, 5).map((transaction) => {
        const incoming = transaction.direction === 'income';
        return <Link to="/coach/transactions" key={transaction.id} className="home-transaction">
          <span className={`merchant-icon merchant-icon--${incoming ? 'in' : 'out'}`}>{transaction.merchant_name[0]}</span>
          <span><strong>{transaction.merchant_name}</strong><small>{titleCase(transaction.transaction_type)} · {new Date(transaction.timestamp).toDateString() === new Date().toDateString() ? 'Today' : transaction.category}</small></span>
          <strong className={incoming ? 'money-positive' : 'money-negative'}><b aria-hidden="true">{incoming ? '+' : '−'}</b>{formatBDT(transaction.amount)}</strong>
        </Link>;
      })}
    </div>
  </section>;
}

function UpayHome({user}: {user: DemoUser}) {
  const [summary, setSummary] = useState<DashboardSummary>();
  const [loadError, setLoadError] = useState(false);
  const [hidden, setHidden] = useState(false);
  const loadSummary = () => { setLoadError(false); void api<DashboardSummary>('/dashboard/summary').then(setSummary).catch(() => setLoadError(true)); };
  useEffect(loadSummary, []);
  const services: Service[] = [
    {name: 'Send Money', description: 'Transfer instantly', icon: Send, to: '/coach/assistant', tone: 'gold'},
    {name: 'Mobile Recharge', description: 'Top up a number', icon: Smartphone, to: '/coach/assistant', tone: 'blue'},
    {name: 'Pay Bill', description: 'Pay on time', icon: ReceiptText, to: '/coach/assistant', tone: 'indigo'},
    {name: 'Cash Out', description: 'Find an agent', icon: Landmark, to: '/coach/assistant', tone: 'green'},
    {name: 'Add Money', description: 'Bring money in', icon: WalletCards, to: '/coach/assistant', tone: 'amber'},
    {name: 'Fund Transfer', description: 'To another bank', icon: ArrowUpRight, to: '/coach/assistant', tone: 'blue'},
    {name: 'Savings', description: 'Plan and grow', icon: PiggyBank, to: '/coach/goals', tone: 'teal'},
    {name: 'Request Money', description: 'Ask to be paid', icon: CircleDollarSign, to: '/coach/assistant', tone: 'cyan'},
    {name: 'AI Assist', description: 'Tell me what you need', icon: Sparkles, to: '/coach/assistant', tone: 'navy', featured: true, badge: 'Smart'},
    {name: 'Make Payment', description: 'Pay securely', icon: ShieldCheck, to: '/coach/assistant', tone: 'indigo'},
    {name: 'NPSB', description: 'Bank network', icon: Landmark, to: '/coach/assistant', tone: 'blue'},
    {name: 'More', description: 'See all services', icon: MoreHorizontal, to: '/coach/plan', tone: 'neutral'},
  ];
  const balance = summary?.balance ?? user.balance;
  return <div className="home-dashboard page">
    <HomeOverview summary={summary} balance={balance} hidden={hidden} error={loadError} onToggle={() => setHidden(!hidden)} />
    {summary ? <FinancialSignals summary={summary} /> : loadError ? <section className="home-section"><SectionHeader title="Smart financial signals" /><div className="home-signals-error"><Activity /><span><strong>Money signals couldn’t be refreshed.</strong><small>Try again to load your personalized financial picture.</small></span><button className="text-button" onClick={loadSummary}>Try again</button></div></section> : <section className="home-section"><SectionHeader title="Smart financial signals" /><div className="signal-grid signal-grid--loading"><i /><i /><i /></div></section>}
    <AIFinancialForecast forecast={summary?.ml} />
    <QuickActionsSection services={services} />
    <RecentTransactions summary={summary} error={loadError} retry={loadSummary} />
    <section className="home-section home-secondary">
      <SectionHeader title="Planning & support" />
      <div className="home-shortcuts">
        <FeatureCard to="/people" icon={UsersRound} title="Trusted People" description="Recognize people you pay" />
        <FeatureCard to="/coach/assistant?guided=1" icon={Accessibility} title="Guided Mode" description="One calm step at a time" />
        <FeatureCard to="/coach/scenario" icon={Compass} title="Scenario Lab" description="See how a decision may affect your future" />
        <FeatureCard to="/coach/goals" icon={PiggyBank} title="Savings Goals" description="Build toward a target" />
      </div>
    </section>

    <p className="concept-note">Concept integration prototype · Synthetic demo data · Not an official production upay service</p>
  </div>;
}

function DemoTour({close}: {close: () => void}) {
  const [step, setStep] = useState(0);
  const steps = [
    ['A familiar place to start', 'This concept begins inside an upay-style home, not in a separate finance dashboard.'],
    ['Money Pulse', 'AI Assist turns activity into one clear signal, with calculated drivers you can inspect.'],
    ['Ask why', 'AI Assist answers using structured evidence from the financial tools.'],
    ['Explore a choice', 'Scenario Lab compares the current projection with a change—without changing the account.'],
    ['You decide', 'Safe-to-Save and goals are estimates and demo allocations. Nothing happens automatically.'],
  ];
  return <div className="tour" role="dialog" aria-modal="true" aria-labelledby="tour-title">
    <button className="icon-button" onClick={close} aria-label="Close demo tour"><X /></button>
    <span className="tour__count">{step + 1} / {steps.length}</span><Sparkles className="tour__spark" />
    <h2 id="tour-title">{steps[step][0]}</h2><p>{steps[step][1]}</p>
    <div className="tour__dots">{steps.map((_, index) => <i className={index === step ? 'active' : ''} key={index} />)}</div>
    <div className="tour__actions"><button className="button button--ghost" onClick={close}>Skip</button><button className="button" onClick={() => step === steps.length - 1 ? close() : setStep(step + 1)}>{step === steps.length - 1 ? 'Finish' : 'Next'}</button></div>
  </div>;
}

function AppShell({user, switchUser}: {user: DemoUser; switchUser: (email: string) => Promise<void>}) {
  const location = useLocation();
  const navigate = useNavigate();
  const [profileOpen, setProfileOpen] = useState(false);
  const [moreOpen, setMoreOpen] = useState(false);
  const [tourOpen, setTourOpen] = useState(false);
  const [switching, setSwitching] = useState('');
  const [sidebarExpanded, setSidebarExpanded] = useState(false);
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false);
  const [sidebarTooltip, setSidebarTooltip] = useState<{label: string; top: number} | null>(null);
  const isSidebarExpanded = sidebarExpanded || mobileDrawerOpen;

  const navConfig = [
    {
      section: 'MAIN',
      items: [
        {to: '/', label: 'Home', icon: Home, end: true},
        {to: '/coach/plan', label: 'Plan', icon: Target},
        {to: '/coach/assistant', label: 'AI Assist', icon: MessageCircle},
        {to: '/coach/scenario', label: 'Scenario Lab', icon: Compass},
        {to: '/coach', label: 'Overview', icon: Zap, end: true},
      ],
    },
    {
      section: 'FINANCIAL TOOLS',
      items: [
        {to: '/coach/transactions', label: 'Transactions', icon: History},
        {to: '/coach/insights', label: 'Insights', icon: Lightbulb},
        {to: '/coach/reports', label: 'Financial Health', icon: FileBarChart},
        {to: '/coach/goals', label: 'Savings', icon: PiggyBank},
      ],
    },
    {
      section: 'LEARN & SAVE',
      items: [
        {to: '/coach/learn', label: 'Learn', icon: BookOpen},
        {to: '/offers', label: 'Offers', icon: Gift},
      ],
    },
    {
      section: 'PEOPLE & SAFETY',
      items: [
        {to: '/people', label: 'Trusted People', icon: UsersRound},
        {to: '/trusted-helper', label: 'Helper Mode', icon: HandHeart},
      ],
    },
  ];

  const changeProfile = async (email: string) => {
    setSwitching(email);
    await switchUser(email);
    setProfileOpen(false); setSwitching(''); navigate('/coach');
  };

  useEffect(() => {
    setMobileDrawerOpen(false);
    setMoreOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    if (!mobileDrawerOpen) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setMobileDrawerOpen(false);
    };
    window.addEventListener('keydown', closeOnEscape);
    return () => window.removeEventListener('keydown', closeOnEscape);
  }, [mobileDrawerOpen]);

  useEffect(() => {
    if (isSidebarExpanded) setSidebarTooltip(null);
  }, [isSidebarExpanded]);

  const showSidebarTooltip = (label: string, event: MouseEvent<HTMLElement> | FocusEvent<HTMLElement>) => {
    if (isSidebarExpanded) return;
    const rect = event.currentTarget.getBoundingClientRect();
    setSidebarTooltip({label, top: rect.top + rect.height / 2});
  };

  const getPageTitle = () => {
    const path = location.pathname;
    if (path === '/') return `Good morning, ${user.display_name.split(' ')[0]}.`;
    if (path === '/coach') return 'Your money, made clearer.';
    if (path === '/coach/assistant') return 'AI Assist';
    if (path === '/coach/insights') return 'Financial Insights';
    if (path === '/coach/transactions' || path === '/history') return 'Transactions';
    if (path === '/coach/plan') return 'Plan';
    if (path === '/coach/scenario') return 'Scenario Lab';
    if (path === '/coach/goals') return 'Goals';
    if (path === '/coach/reports') return 'Financial Health';
    if (path === '/coach/learn') return 'Learn';
    if (path === '/offers') return 'Offers';
    if (path === '/people') return 'Trusted People';
    if (path === '/trusted-helper') return 'Helper Mode';
    return 'upay AI Assist';
  };

  return <div className="app-shell">
    <aside className={`sidebar ${sidebarExpanded ? 'sidebar--expanded' : ''} ${mobileDrawerOpen ? 'sidebar--mobile-open' : ''}`}>
      <div className="sidebar__header">
        <Link to="/" className="sidebar__brand" onClick={() => setMobileDrawerOpen(false)}><Brand compact /></Link>
        {isSidebarExpanded && <span className="sidebar__brand-label">AI Assist</span>}
        <button
          className="sidebar__toggle"
          onClick={() => { setSidebarExpanded(!sidebarExpanded); setSidebarTooltip(null); }}
          aria-label={sidebarExpanded ? 'Collapse sidebar' : 'Expand sidebar'}
        >
          {sidebarExpanded ? '‹' : '›'}
        </button>
        <button className="sidebar__drawer-close" onClick={() => setMobileDrawerOpen(false)} aria-label="Close navigation"><X /></button>
      </div>

      <nav className="sidebar__nav" aria-label="Main navigation">
        {navConfig.map((group) => (
          <div key={group.section} className="sidebar__group">
            {isSidebarExpanded && <span className="sidebar__group-label">{group.section}</span>}
            {group.items.map(({to, label, icon: Icon, end}) => (
              <div key={to} className="sidebar__item-wrapper" onMouseEnter={(event) => showSidebarTooltip(label, event)} onMouseLeave={() => setSidebarTooltip(null)}>
                <NavLink
                  end={end}
                  to={to}
                  className={({isActive}) => `sidebar__link ${isActive ? 'active' : ''}`}
                  aria-label={label}
                  onClick={() => setMobileDrawerOpen(false)}
                  onFocus={(event) => showSidebarTooltip(label, event)}
                  onBlur={() => setSidebarTooltip(null)}
                >
                  <Icon className="sidebar__icon" />
                  {isSidebarExpanded && <span className="sidebar__label">{label}</span>}
                </NavLink>
              </div>
            ))}
          </div>
        ))}
      </nav>

      <div className="sidebar__footer">
        <div className="sidebar__item-wrapper" onMouseEnter={(event) => showSidebarTooltip('Demo tour', event)} onMouseLeave={() => setSidebarTooltip(null)}>
          <button className="sidebar__link" onClick={() => setTourOpen(true)} aria-label="Demo tour" onFocus={(event) => showSidebarTooltip('Demo tour', event)} onBlur={() => setSidebarTooltip(null)}>
            <CircleHelp className="sidebar__icon" />
            {isSidebarExpanded && <span className="sidebar__label">Demo tour</span>}
          </button>
        </div>
        {isSidebarExpanded && <TrustBadge>Synthetic demo data</TrustBadge>}
      </div>
      {sidebarTooltip && <span className="sidebar__tooltip sidebar__tooltip--portal" role="tooltip" style={{top: sidebarTooltip.top}}>{sidebarTooltip.label}</span>}
    </aside>
    {mobileDrawerOpen && <button className="sidebar-backdrop" aria-label="Close navigation" onClick={() => setMobileDrawerOpen(false)} />}
    <div className={`app-main ${location.pathname === '/coach/assistant' ? 'app-main--assistant' : ''}`}>
      <header className="topbar">
        <div className="topbar__title"><button className="topbar__menu-button icon-button" onClick={() => setMobileDrawerOpen(true)} aria-label="Open navigation"><Menu /></button><div>{location.pathname === '/coach/assistant' ? <><strong>AI Assist</strong><span>Ask naturally in English, বাংলা, or both</span></> : location.pathname === '/' ? <><strong>{getPageTitle()}</strong><span>Your wallet at a glance</span></> : <><span>upay AI Assist</span><strong>{getPageTitle()}</strong></>}</div></div>
        <div className="topbar__actions">
          <button className="topbar__notification icon-button" aria-label="Notifications"><Bell /></button>
          <div className="profile-menu">
            <button className="profile-button" aria-expanded={profileOpen} aria-haspopup="menu" aria-label={`Account menu for ${user.display_name}, ${user.persona}`} onClick={() => setProfileOpen(!profileOpen)}><span className="avatar">{user.display_name[0]}</span><span><strong>{user.display_name}</strong><small>{user.persona}</small></span><ChevronDown aria-hidden="true" /></button>
            {profileOpen && <div className="profile-popover"><span>Switch demo profile</span>{profiles.map((profile) => <button disabled={Boolean(switching)} onClick={() => void changeProfile(profile.email)} key={profile.email}><span className="avatar">{profile.name[0]}</span><span><strong>{profile.name}</strong><small>{profile.persona} · {profile.story}</small></span>{switching === profile.email && <small>Switching…</small>}</button>)}</div>}
          </div>
        </div>
      </header>
      <main className={`main-content ${location.pathname === '/coach/assistant' ? 'main-content--assistant' : ''}`}>
        <Routes key={user.id}>
          <Route path="/" element={<UpayHome user={user} />} />
          <Route path="/coach" element={<PulsePage user={user} />} />
          <Route path="/coach/insights" element={<InsightsPage />} />
          <Route path="/coach/plan" element={<PlanPage />} />
          <Route path="/coach/goals" element={<GoalsPage />} />
          <Route path="/coach/scenario" element={<ScenarioPage />} />
          <Route path="/coach/assistant" element={<CoachPanel user={user} />} />
          <Route path="/coach/reports" element={<ReportsPage />} />
          <Route path="/coach/learn" element={<LearnPage />} />
          <Route path="/coach/transactions" element={<HistoryPage />} />
          <Route path="/history" element={<Navigate to="/coach/transactions" replace />} />
          <Route path="/offers" element={<OffersPage />} />
          <Route path="/people" element={<ContactsPage />} />
          <Route path="/trusted-helper" element={<TrustedHelperPage />} />
          <Route path="*" element={<Navigate to="/coach" replace />} />
        </Routes>
      </main>
    </div>
    <nav className="bottom-nav" aria-label="Mobile navigation"><NavLink end to="/"><Home /><span>Home</span></NavLink><NavLink to="/coach/transactions"><History /><span>Activity</span></NavLink><NavLink className="bottom-nav__assist" to="/coach/assistant"><MessageCircle /><span>AI Assist</span></NavLink><NavLink to="/coach/plan"><Target /><span>Plan</span></NavLink><button className={moreOpen ? 'active' : ''} onClick={() => setMoreOpen(!moreOpen)}><MoreHorizontal /><span>More</span></button></nav>
    {moreOpen && <div className="mobile-more"><div><span>More</span><button className="icon-button" onClick={() => setMoreOpen(false)} aria-label="Close more menu"><X /></button></div>{navConfig.flatMap(g => g.items).map(({to, label, icon: Icon}) => <Link to={to} onClick={() => setMoreOpen(false)} key={to}><Icon />{label}</Link>)}<button onClick={() => {setMoreOpen(false); setTourOpen(true);}}><CircleHelp />Demo tour</button></div>}
    {tourOpen && <><div className="tour-backdrop" onClick={() => setTourOpen(false)} /><DemoTour close={() => setTourOpen(false)} /></>}
  </div>;
}

export default function App() {
  const [user, setUser] = useState<DemoUser | null>(null);
  const [checking, setChecking] = useState(Boolean(token()));
  const location = useLocation();
  const loadUser = async () => {
    try { setUser(await api<DemoUser>('/auth/me')); }
    catch { localStorage.removeItem('upay_token'); setUser(null); }
    finally { setChecking(false); }
  };
  useEffect(() => { if (token()) void loadUser(); }, []);
  const login = async (email: string) => {
    const result = await api<LoginResult>('/auth/login', {method: 'POST', body: JSON.stringify({email})});
    localStorage.setItem('upay_token', result.access_token);
    await loadUser();
  };
  useEffect(() => {
    if (user || token()) return;
    const requested = new URLSearchParams(window.location.search).get('demo');
    const profile = profiles.find((item) => item.name.toLowerCase() === requested?.toLowerCase());
    if (profile) {
      setChecking(true);
      void login(profile.email).finally(() => window.history.replaceState({}, '', window.location.pathname));
    }
  }, [user]);
  if (checking) return <div className="app-loading"><Brand /><span>Preparing AI Assist…</span></div>;
  if (!user) return <Login onLogin={login} />;
  return <AppShell user={user} switchUser={login} />;
}
