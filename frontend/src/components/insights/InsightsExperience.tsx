import {useEffect, useState} from 'react';
import {ArrowDown, ArrowRight, ArrowUp, CalendarClock, CheckCircle2, CircleAlert, MessageCircle, ReceiptText, Sparkles, TrendingUp, WalletCards} from 'lucide-react';
import {Link} from 'react-router-dom';
import {api} from '../../api/client';
import {formatBDT, formatDate} from '../../format';
import type {Change, Health, MoneyRunway, MoneyStory, SafeToSave, Transaction} from '../../types';
import {Sheet} from '../ui';
import {ExplainMetricButton} from '../ExplainMetricButton';

type Comparison = {categories: Change[]; summary: string; period: {start: string; end: string}};

const promptLink = (prompt: string) => `/coach/assistant?prompt=${encodeURIComponent(prompt)}`;
const directionMeta = (item: Change) => item.difference > 0
  ? {label: 'Increased', icon: ArrowUp, tone: 'up'}
  : item.difference < 0
    ? {label: 'Decreased', icon: ArrowDown, tone: 'down'}
    : {label: 'Stable', icon: ArrowRight, tone: 'flat'};

export function TopInsight({comparison, onEvidence}: {comparison: Comparison; onEvidence: () => void}) {
  const lead = comparison.categories[0];
  const increased = !!lead && lead.difference > 0;
  const delta = lead && lead.change_percent !== null ? `${lead.change_percent > 0 ? '+' : ''}${lead.change_percent}%` : 'New activity';
  return <section className="insights-hero" aria-labelledby="top-insight-title">
    <span className="insights-kicker">Your biggest change this month</span>
    {lead ? <>
      <div className="insights-hero__content">
        <div>
          <h2 id="top-insight-title">{lead.category} spending {increased ? 'rose sharply' : lead.difference < 0 ? 'came down' : 'stayed steady'}</h2>
          <p>You spent {formatBDT(Math.abs(lead.difference))} {increased ? 'more' : lead.difference < 0 ? 'less' : ''} on {lead.category} than in the previous 30 days.</p>
          <p className="insights-hero__meaning">{increased ? 'This is the clearest contributor to the change in your recent spending.' : 'This is the clearest shift in your recent spending pattern.'}</p>
        </div>
        <div className={`insights-hero__delta insights-hero__delta--${increased ? 'up' : 'down'}`}><strong>{delta}</strong><span>vs previous period</span></div>
      </div>
      <div className="insights-hero__actions"><button className="text-button" onClick={onEvidence}>See what changed <ArrowRight /></button><ExplainMetricButton metric={{metricId: 'spending_category_change', title: `${lead.category} Spending Change`, value: lead.difference, unit: 'BDT', source: 'insights', context: {category: lead.category, current: lead.current, previous: lead.previous, changePercent: lead.change_percent ?? 'New activity'}}} /></div>
    </> : <><h2 id="top-insight-title">Your spending is relatively stable</h2><p>Not enough category change was detected to call out one standout shift this period.</p><div className="insights-hero__actions"><button className="text-button" onClick={onEvidence}>View evidence <ArrowRight /></button></div></>}
  </section>;
}

export function ChangeRanking({changes, onSelect}: {changes: Change[]; onSelect: (item: Change) => void}) {
  const [expanded, setExpanded] = useState(false);
  const meaningful = changes.filter((item) => item.difference !== 0);
  const visible = expanded ? meaningful : meaningful.slice(0, 4);
  return <section className="insights-section change-ranking" aria-labelledby="ranked-changes-title">
    <div className="insights-section__heading"><div><h2 id="ranked-changes-title">What changed</h2><p>Compared with the previous 30 days</p></div></div>
    {visible.length ? <ol className="change-ranking__list">{visible.map((item) => {
      const meta = directionMeta(item); const Icon = meta.icon;
      return <li key={item.category}><button onClick={() => onSelect(item)}>
        <span className="change-ranking__number" aria-hidden="true">{meaningful.indexOf(item) + 1}</span>
        <span className={`change-ranking__signal change-ranking__signal--${meta.tone}`}><Icon aria-hidden="true" /><span>{meta.label}</span></span>
        <span className="change-ranking__category"><strong>{item.category}</strong><small>{formatBDT(item.current)} this period</small></span>
        <span className={`change-ranking__amount change-ranking__amount--${meta.tone}`}><strong>{formatBDT(item.difference, true)}</strong><small>{item.change_percent === null ? 'New activity' : `${item.change_percent > 0 ? '+' : ''}${item.change_percent}%`}</small></span>
      </button></li>;
    })}</ol> : <p className="empty-copy">Your spending pattern is relatively stable this period.</p>}
    {meaningful.length > 4 && <button className="text-button insights-inline-action" onClick={() => setExpanded(!expanded)}>{expanded ? 'Show fewer categories' : 'View all categories'} <ArrowRight /></button>}
  </section>;
}

export function InsightExplanation({comparison, safeToSave, runway}: {comparison: Comparison; safeToSave: SafeToSave; runway: MoneyRunway}) {
  const lead = comparison.categories.find((item) => item.difference > 0);
  const flexibility = safeToSave.high > 0 ? 'Some room remains' : 'Limited this week';
  return <section className="insights-section insight-explanation" aria-labelledby="why-it-matters-title">
    <div className="insights-section__heading"><div><h2 id="why-it-matters-title">Why this matters</h2></div></div>
    <p className="insight-explanation__copy">{lead ? <>Most of your additional spending came from <strong>{lead.category}</strong>, rather than a broad increase across every category. Looking at this one area is the most direct way to understand your current spending flexibility.</> : comparison.summary}</p>
    <div className="impact-summary" aria-label="Impact on your month"><span className="impact-summary__label">Impact on your month</span><div><small>Flexible spending</small><strong>{lead ? 'More pressure' : 'Steady'}</strong></div><div><small>Savings capacity</small><strong>{flexibility}</strong></div><div><small>Estimated runway</small><strong>~{runway.days} days</strong></div></div>
  </section>;
}

export function CategoryComparison({changes, onSelect}: {changes: Change[]; onSelect: (item: Change) => void}) {
  const [expanded, setExpanded] = useState(false);
  const visible = expanded ? changes : changes.slice(0, 5);
  const maximum = Math.max(...changes.flatMap((item) => [item.current, item.previous]), 1);
  return <section className="category-comparison" aria-labelledby="category-patterns-title">
    <div className="insights-section__heading"><div><h2 id="category-patterns-title">Spending patterns</h2><p>Current period compared with the previous 30 days</p></div></div>
    {visible.length ? <div className="category-comparison__list">{visible.map((item) => {
      const meta = directionMeta(item); const Icon = meta.icon;
      return <button className="category-comparison__row" key={item.category} onClick={() => onSelect(item)} aria-label={`View ${item.category} details`}>
        <span className="category-comparison__title"><strong>{item.category}</strong><small>{formatBDT(item.current)}</small></span>
        <span className="category-comparison__bars" aria-hidden="true"><i className="category-comparison__previous" style={{width: `${Math.max(item.previous ? 4 : 0, item.previous / maximum * 100)}%`}} /><i className="category-comparison__current" style={{width: `${Math.max(item.current ? 4 : 0, item.current / maximum * 100)}%`}} /></span>
        <span className={`category-comparison__delta category-comparison__delta--${meta.tone}`}><Icon /><strong>{formatBDT(item.difference, true)}</strong><small>{item.change_percent === null ? 'New activity' : `${item.change_percent > 0 ? '+' : ''}${item.change_percent}%`} · from {formatBDT(item.previous)}</small></span>
      </button>;
    })}</div> : <p className="empty-copy">Not enough transaction history yet to compare periods.</p>}
    {changes.length > 5 && <button className="text-button insights-inline-action" onClick={() => setExpanded(!expanded)}>{expanded ? 'Show fewer categories' : 'View all categories'} <ArrowRight /></button>}
  </section>;
}

function factorDetail(name: string) {
  const names: Record<string, string> = {
    'Saving behavior': 'Saving behavior', 'Cash-flow stability': 'Cash-flow stability', 'Budget adherence': 'Budget adherence', 'Liquidity buffer': 'Liquidity buffer', 'Recurring expense management': 'Recurring expenses',
  };
  return names[name] || name;
}

export function FinancialHealthSummary({health}: {health: Health}) {
  const helping = health.components.filter((item) => item.score / item.max >= .58).slice(0, 2);
  const attention = health.components.filter((item) => item.score / item.max < .58).slice(0, 3);
  return <section className="health-summary" aria-labelledby="health-summary-title">
    <div className="health-summary__header"><div><span className="insights-kicker">Financial Health</span><h2 id="health-summary-title">{health.label}</h2></div><div className="health-summary__score"><span>Overall indicator</span><strong>{health.score} <small>/ 100</small></strong><ExplainMetricButton metric={{metricId: 'financial_health_score', title: 'Financial Health Score', value: health.score, unit: '/ 100', source: 'insights', context: {label: health.label, components: health.components.map((item) => `${item.name}: ${item.score}/${item.max}`).join(', ')}}} /></div></div>
    <p>{health.what_improved}</p>
    <div className="health-factors"><div><h3><CheckCircle2 />What is helping</h3>{helping.length ? <ul>{helping.map((item) => <li key={item.name}>{factorDetail(item.name)}</li>)}</ul> : <p>Recent activity is still building a clearer pattern.</p>}</div><div><h3><CircleAlert />What needs attention</h3>{attention.length ? <ul>{attention.map((item) => <li key={item.name}>{factorDetail(item.name)}</li>)}</ul> : <p>Your current health factors are broadly balanced.</p>}</div></div>
    <details className="health-details"><summary>How this is calculated <ArrowRight /></summary><div>{health.components.map((item) => <span key={item.name}><small>{factorDetail(item.name)}</small><strong>{item.score} / {item.max}</strong></span>)}</div></details>
    <small className="health-disclaimer">This is not a credit score.</small>
  </section>;
}

function storyIcon(type: string) {
  if (type === 'income') return WalletCards;
  if (type === 'upcoming') return CalendarClock;
  if (type === 'change') return TrendingUp;
  if (type === 'spike') return ReceiptText;
  return Sparkles;
}

export function MoneyStoryTimeline({story}: {story: MoneyStory}) {
  const [expanded, setExpanded] = useState(false);
  const visible = expanded ? story.events : story.events.slice(0, 5);
  return <section className="money-story" aria-labelledby="money-story-title">
    <div className="insights-section__heading"><div><h2 id="money-story-title">Your Money Story</h2><p>{formatDate(story.period.start)}–{formatDate(story.period.end, true)}</p></div></div>
    {visible.length ? <div className="money-story__timeline">{visible.map((event, index) => { const Icon = storyIcon(event.type); return <div className="money-story__event" key={`${event.date}-${event.title}-${index}`}><time>{formatDate(event.date)}</time><span className={`money-story__icon money-story__icon--${event.type}`}><Icon aria-hidden="true" /></span><span><strong>{event.title}</strong><small>{event.detail}</small></span>{event.amount !== 0 && <strong className={event.type === 'income' || event.amount < 0 ? 'money-positive' : ''}>{formatBDT(event.amount, event.type === 'income' || event.type === 'change')}</strong>}</div>; })}</div> : <p className="empty-copy">No major financial events were detected this period.</p>}
    {story.events.length > 5 && <button className="text-button insights-inline-action" onClick={() => setExpanded(!expanded)}>{expanded ? 'Show fewer events' : 'View full Money Story'} <ArrowRight /></button>}
  </section>;
}

export function CategoryDetailDrawer({category, close}: {category: Change; close: () => void}) {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let alive = true; setLoading(true);
    void api<{items: Transaction[]}>(`/transactions?category=${encodeURIComponent(category.category)}&page_size=100`).then((data) => {if (alive) setTransactions(data.items.filter((item) => item.direction !== 'income').sort((a, b) => b.amount - a.amount).slice(0, 2));}).catch(() => {if (alive) setTransactions([]);}).finally(() => {if (alive) setLoading(false);});
    return () => {alive = false;};
  }, [category.category]);
  return <Sheet title={`${category.category} details`} close={close}>
    <div className="category-detail__metrics"><span><small>Current period</small><strong>{formatBDT(category.current)}</strong></span><span><small>Previous period</small><strong>{formatBDT(category.previous)}</strong></span><span><small>Difference</small><strong className={category.difference > 0 ? 'money-negative' : 'money-positive'}>{formatBDT(category.difference, true)}</strong></span></div>
    <ExplainMetricButton metric={{metricId: 'spending_category_change', title: `${category.category} Spending Change`, value: category.difference, unit: 'BDT', source: 'insights_category_detail', context: {category: category.category, current: category.current, previous: category.previous, changePercent: category.change_percent ?? 'New activity'}}} className="category-detail__explain" />
    <h3 className="category-detail__heading">Largest transactions</h3>
    {loading ? <p>Loading related transactions…</p> : transactions.length ? <div className="category-detail__transactions">{transactions.map((item) => <div key={item.id}><span><strong>{item.merchant_name}</strong><small>{formatDate(item.timestamp)}</small></span><strong>{formatBDT(item.amount)}</strong></div>)}</div> : <p>No transactions are available for this category yet.</p>}
    <Link className="button button--secondary" to={`/coach/transactions?category=${encodeURIComponent(category.category)}`}>View transactions <ArrowRight /></Link>
  </Sheet>;
}

export function ExploreActions({lead, onEvidence}: {lead?: Change; onEvidence: () => void}) {
  const prompt = lead ? `Help me understand the ${lead.category.toLowerCase()} spending change.` : 'Help me understand my spending pattern.';
  return <section className="insights-explore" aria-labelledby="explore-title"><div><h2 id="explore-title">Explore</h2><p>Review the activity behind these insights or ask a focused question.</p></div><div><Link className="button button--secondary" to="/coach/transactions">Transactions <ReceiptText /></Link><button className="button button--secondary" onClick={onEvidence}>View evidence <ArrowRight /></button><Link className="button" to={promptLink(prompt)}>Ask AI Assist <MessageCircle /></Link></div></section>;
}
