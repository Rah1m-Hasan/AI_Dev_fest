import {useEffect, useState} from 'react';
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
  Bus,
  Car,
  CircleDollarSign,
  HeartHandshake,
  School,
  Shield,
  Ticket,
} from 'lucide-react';
import {Link, Navigate, NavLink, Route, Routes, useLocation, useNavigate} from 'react-router-dom';
import {api, token} from './api/client';
import {Brand, Tag, TrustBadge} from './components/ui';
import type {DashboardSummary, DemoUser} from './types';
import {formatBDT} from './format';
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
      <Brand />
      <Tag tone="demo">Concept integration prototype</Tag>
      <h1>Understand your money.<br />Choose what happens next.</h1>
      <p>See why your balance changed, what may happen next, and what you can realistically do—using synthetic demo activity.</p>
      <div className="trust-callout"><ShieldCheck /><span><strong>You stay in control.</strong> AI Assist explains and suggests. It never moves money without your confirmation.</span></div>
      <div className="profile-list" aria-label="Choose a demo profile">{profiles.map((profile) => <button className="profile-choice" disabled={Boolean(busy)} onClick={() => void choose(profile.email)} key={profile.email}>
        <span className="avatar">{profile.name[0]}</span><span><strong>{profile.name}</strong><small>{profile.persona} · {profile.story}</small></span><span>{busy === profile.email ? 'Loading…' : 'Try demo'} </span>
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

function UpayHome({user}: {user: DemoUser}) {
  const [summary, setSummary] = useState<DashboardSummary>();
  const [hidden, setHidden] = useState(false);
  useEffect(() => { void api<DashboardSummary>('/dashboard/summary').then(setSummary).catch(() => undefined); }, []);
  const services = [
    ['Send Money', Send, '/coach/assistant'], ['Mobile Recharge', Smartphone, '/coach/assistant'], ['Cash Out', Landmark, '/coach/assistant'], ['Pay Bill', ReceiptText, '/coach/assistant'],
    ['Add Money', WalletCards, '/coach/assistant'], ['Savings', PiggyBank, '/coach/goals'], ['Fund Transfer', ArrowUpRight, '/coach/assistant'], ['Request Money', CircleDollarSign, '/coach/assistant'],
    ['Make Payment', ShieldCheck, '/coach/assistant'], ['AI Assist', Sparkles, '/coach/assistant'], ['NPSB', Landmark, '/coach/assistant'], ['More', MoreHorizontal, '/coach/plan'],
  ] as const;
  const balance = summary?.balance ?? user.balance;
  return <div className="home-dashboard page">
    <section className="upay-account-strip">
      <span className="upay-avatar" aria-hidden="true"><span>u</span></span>
      <div className="upay-account-strip__identity"><strong>{user.display_name}</strong><small>01•••••••••</small></div>
      <button className="upay-balance-button" onClick={() => setHidden(!hidden)} aria-label={hidden ? 'Show balance' : 'Hide balance'}>Balance</button>
      <button className="upay-notification" aria-label="Notifications preview"><Bell /></button>
      <div className="upay-balance-popover"><small>Available balance</small><strong>{hidden ? '৳ ••••••' : formatBDT(balance)}</strong><button onClick={() => setHidden(!hidden)} aria-label={hidden ? 'Show balance' : 'Hide balance'}>{hidden ? <Eye /> : <EyeOff />}</button></div>
    </section>
    <section className="home-section home-actions"><div className="section-title"><h2>upay Services</h2><Link to="/coach/assistant">Ask AI Assist</Link></div><div className="service-grid" aria-label="upay services">{services.map(([name, Icon, to]) => <Link className={`service-item ${name === 'AI Assist' ? 'service-item--assist' : ''}`} to={to} key={name}><span><Icon /></span><small>{name}</small></Link>)}</div></section>
    {summary && <section className="money-today home-section"><div className="section-title"><h2>Your Money Today</h2><Link to="/coach">View full insights <ArrowUpRight /></Link></div><div className="home-intelligence"><Link to="/coach/assistant" className="safe-spend-glance"><small>SAFE TO SPEND</small><strong>{formatBDT(summary.safe_to_spend.safe_to_spend)}</strong><span>After known commitments <ArrowUpRight /></span></Link><Link to="/coach" className="runway-glance"><small>MONEY RUNWAY</small><strong>~{summary.runway.days} days</strong><span>Based on recent spending <ArrowUpRight /></span></Link><Link to="/coach/insights" className="pulse-glance"><span className="pulse-glance__icon"><Sparkles /></span><span><small>MONEY PULSE</small><strong>{summary.pulse.why[0]?.label || summary.pulse.status}</strong><em>{summary.pulse.why[0]?.detail || summary.pulse.headline}</em></span><ArrowUpRight /></Link></div></section>}
    <section className="home-section"><div className="section-title"><h2>Recent transactions</h2><Link to="/history">See all</Link></div><div className="home-activity">{summary?.recent_transactions.slice(0, 3).map((transaction) => <Link to="/history" key={transaction.id}><span className="merchant-icon">{transaction.merchant_name[0]}</span><span><strong>{transaction.merchant_name}</strong><small>{transaction.category} · Today</small></span><strong className={transaction.direction === 'income' ? 'money-positive' : 'money-negative'}>{transaction.direction === 'income' ? '+' : '-'}{formatBDT(transaction.amount)}</strong></Link>) || <div className="home-placeholder"><History /><span><strong>Your recent activity will appear here</strong><small>Loading your demo wallet activity.</small></span></div>}</div></section>
    <section className="home-section home-secondary"><div className="section-title"><h2>Support & planning</h2></div><div className="home-shortcuts"><Link to="/people"><UsersRound /><span><strong>People, not numbers</strong><small>Recognize who you are paying</small></span></Link><Link to="/coach/assistant?guided=1"><Accessibility /><span><strong>Guided Mode</strong><small>One calm step at a time</small></span></Link></div></section>
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
  const primary = [
    {to: '/', label: 'Home', icon: Home, end: true},
    {to: '/coach', label: 'Pulse', icon: Zap, end: true},
    {to: '/coach/plan', label: 'Plan', icon: Target},
    {to: '/coach/assistant', label: 'AI Assist', icon: MessageCircle},
  ];
  const secondary = [
    {to: '/history', label: 'Transactions', icon: History},
    {to: '/coach/insights', label: 'Insights', icon: Lightbulb},
    {to: '/coach/reports', label: 'Reports', icon: FileBarChart},
    {to: '/coach/learn', label: 'Learn', icon: BookOpen},
    {to: '/offers', label: 'Relevant savings', icon: Gift},
    {to: '/people', label: 'People', icon: UsersRound},
    {to: '/trusted-helper', label: 'Trusted Helper', icon: HandHeart},
  ];
  const changeProfile = async (email: string) => {
    setSwitching(email);
    await switchUser(email);
    setProfileOpen(false); setSwitching(''); navigate('/coach');
  };
  const pageTitle = location.pathname === '/' ? `Good morning, ${user.display_name.split(' ')[0]}.` : location.pathname === '/coach' ? 'Your money, made clearer.' : location.pathname === '/coach/assistant' ? 'AI Assist' : 'upay AI Assist';
  return <div className="app-shell">
    <aside className="sidebar">
      <Link to="/" className="sidebar__brand"><Brand /></Link>
      <span className="sidebar__concept">Concept integration prototype</span>
      <nav aria-label="Main navigation">{primary.map(({to, label, icon: Icon, end}) => <NavLink end={end} to={to} key={to}><Icon />{label}</NavLink>)}</nav>
      <div className="sidebar__divider" />
      <nav aria-label="More financial tools">{secondary.map(({to, label, icon: Icon}) => <NavLink to={to} key={to}><Icon />{label}</NavLink>)}</nav>
      <button className="tour-button" onClick={() => setTourOpen(true)}><CircleHelp />Demo tour</button>
      <TrustBadge>Synthetic demo data</TrustBadge>
    </aside>
    <div className="app-content">
      <header className="topbar">
        <div><span>UPAY · AI ASSIST</span><strong>{pageTitle}</strong></div>
        <div className="topbar__actions">
          <span className="icon-button" aria-label="Notifications preview"><Bell /></span>
          <div className="profile-menu">
            <button className="profile-button" aria-expanded={profileOpen} onClick={() => setProfileOpen(!profileOpen)}><span className="avatar">{user.display_name[0]}</span><span><strong>{user.display_name}</strong><small>{user.persona}</small></span><ChevronDown /></button>
            {profileOpen && <div className="profile-popover"><span>Switch demo profile</span>{profiles.map((profile) => <button disabled={Boolean(switching)} onClick={() => void changeProfile(profile.email)} key={profile.email}><span className="avatar">{profile.name[0]}</span><span><strong>{profile.name}</strong><small>{profile.persona} · {profile.story}</small></span>{switching === profile.email && <small>Switching…</small>}</button>)}</div>}
          </div>
        </div>
      </header>
      <main className="main-content">
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
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/offers" element={<OffersPage />} />
          <Route path="/people" element={<ContactsPage />} />
          <Route path="/trusted-helper" element={<TrustedHelperPage />} />
          <Route path="*" element={<Navigate to="/coach" replace />} />
        </Routes>
      </main>
    </div>
    <nav className="bottom-nav" aria-label="Mobile navigation"><NavLink end to="/"><Home /><span>Home</span></NavLink><NavLink to="/history"><History /><span>Activity</span></NavLink><NavLink className="bottom-nav__assist" to="/coach/assistant"><MessageCircle /><span>AI Assist</span></NavLink><NavLink to="/coach/plan"><Target /><span>Plan</span></NavLink><button className={moreOpen ? 'active' : ''} onClick={() => setMoreOpen(!moreOpen)}><MoreHorizontal /><span>More</span></button></nav>
    {moreOpen && <div className="mobile-more"><div><span>More</span><button className="icon-button" onClick={() => setMoreOpen(false)} aria-label="Close more menu"><X /></button></div>{secondary.map(({to, label, icon: Icon}) => <Link to={to} onClick={() => setMoreOpen(false)} key={to}><Icon />{label}</Link>)}<button onClick={() => {setMoreOpen(false); setTourOpen(true);}}><CircleHelp />Demo tour</button></div>}
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
