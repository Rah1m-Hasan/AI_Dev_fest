import {Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis} from 'recharts';
import {ArrowRight, Check, CircleAlert, MessageCircle, Sparkles, TrendingUp} from 'lucide-react';
import {Link} from 'react-router-dom';
import {formatBDT, formatDate} from '../../format';
import type {Change, Health, MoneyStory} from '../../types';
import {ExplainMetricButton} from '../ExplainMetricButton';

type Spending = {category_totals: Array<{category: string; amount: number}>};
type HealthHistory = {history: Array<{month: string; score: number}>; note?: string};

export type FinancialHealthReport = {
  period_range: {start: string; end: string};
  snapshot: {income: number; spent: number; net: number};
  spending: Spending;
  comparison: {categories: Change[]; summary: string};
  story: MoneyStory;
  health: Health;
};

type Props = {report: FinancialHealthReport; history?: HealthHistory};

const factorCopy: Record<string, string> = {
  'Saving behavior': 'Regular saving supports your overall financial resilience.',
  'Cash-flow stability': 'More predictable money in and money out helps you plan with confidence.',
  'Budget adherence': 'Keeping spending within your plan protects room for your priorities.',
  'Liquidity buffer': 'Available funds provide a cushion for upcoming needs.',
  'Recurring expense management': 'Keeping repeating costs manageable leaves more flexibility.',
};

function ratio(item: Health['components'][number]) { return item.max ? item.score / item.max : 0; }
function statusFor(item: Health['components'][number]) {
  const value = ratio(item);
  if (value >= .82) return 'Strong';
  if (value >= .6) return 'Stable';
  if (value >= .4) return 'Watch';
  return 'Needs attention';
}
function shortName(name: string) { return name === 'Recurring expense management' ? 'Recurring expenses' : name; }
function scoreText(score: number) { return Number.isInteger(score) ? String(score) : score.toFixed(1); }

function HealthScale({score}: {score: number}) {
  return <div className="health-scale" role="progressbar" aria-label={`Financial health: ${score} out of 100`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={score}>
    <div className="health-scale__labels" aria-hidden="true"><span>Needs attention</span><span>Improving</span><span>Stable</span><span>Strong</span></div>
    <div className="health-scale__track"><i style={{'--health-position': `${Math.max(3, Math.min(score, 97))}%`} as React.CSSProperties}><b>{score}</b></i></div>
  </div>;
}

function HealthSummaryHero({health, previous}: {health: Health; previous?: number}) {
  const strengths = health.components.filter((item) => ratio(item) >= .6);
  const weakest = [...health.components].sort((a, b) => ratio(a) - ratio(b))[0];
  const leadStrength = strengths.find((item) => item.name === 'Saving behavior') || strengths[0];
  const currentMessage = leadStrength
    ? `${shortName(leadStrength.name)} is helping most. ${weakest ? `${shortName(weakest.name)} is your clearest opportunity to improve.` : ''}`
    : `Your recent wallet activity is still building a clearer financial pattern.${weakest ? ` Start with ${shortName(weakest.name)}.` : ''}`;
  const change = previous === undefined ? undefined : health.score - previous;
  return <section className="health-hero" aria-labelledby="health-status-title">
    <div className="health-hero__intro">
      <span className="health-hero__kicker">Personal financial wellness</span>
      <h2 id="health-status-title">{health.label}</h2>
      <p>Your finances are assessed from recent wallet activity and financial behavior. {currentMessage}</p>
      {change !== undefined && change !== 0 && <span className={`health-hero__change ${change > 0 ? 'is-positive' : 'is-watch'}`}><TrendingUp aria-hidden="true" />{change > 0 ? '+' : ''}{change} compared with the previous period</span>}
    </div>
    <div className="health-hero__score">
      <strong>{health.score}<small> / 100</small></strong>
      <span>Financial Health</span>
      <ExplainMetricButton metric={{metricId: 'financial_health_score', title: 'Financial Health Score', value: health.score, unit: '/ 100', source: 'financial_health', context: {label: health.label, components: health.components.map((item) => `${item.name}: ${scoreText(item.score)}/${item.max}`).join(', ')}}} />
    </div>
    <div className="health-hero__scale"><HealthScale score={health.score} /></div>
    <p className="health-hero__disclaimer">Based on recent wallet activity and financial behavior. This is an informational indicator, not a credit score.</p>
  </section>;
}

function StrengthsAndRisks({health, comparison}: {health: Health; comparison: Props['report']['comparison']}) {
  const helping = health.components.filter((item) => ratio(item) >= .6).sort((a, b) => ratio(b) - ratio(a)).slice(0, 4);
  const needsAttention = health.components.filter((item) => ratio(item) < .6).sort((a, b) => ratio(a) - ratio(b)).slice(0, 3);
  const rising = comparison.categories.filter((item) => item.difference > 0).sort((a, b) => b.difference - a.difference)[0];
  return <div className="health-signals">
    <section className="health-signal health-signal--positive" aria-labelledby="helping-title">
      <div><span className="eyebrow">Your strengths</span><h2 id="helping-title">What’s helping you</h2></div>
      {helping.length ? <ul>{helping.map((item) => <li key={item.name}><Check aria-hidden="true" />{shortName(item.name)}</li>)}</ul> : <p>More activity will help reveal the habits currently supporting you.</p>}
    </section>
    <section className="health-signal health-signal--watch" aria-labelledby="attention-title">
      <div><span className="eyebrow">Areas to improve</span><h2 id="attention-title">What needs attention</h2></div>
      <ul>
        {needsAttention.map((item) => <li key={item.name}><CircleAlert aria-hidden="true" />{shortName(item.name)}</li>)}
        {rising && <li><CircleAlert aria-hidden="true" />{rising.category} spending is up{rising.change_percent !== null ? ` ${rising.change_percent > 0 ? '+' : ''}${Math.round(rising.change_percent)}%` : ''}</li>}
        {!needsAttention.length && !rising && <li><CircleAlert aria-hidden="true" />Keep your habits consistent as activity changes.</li>}
      </ul>
    </section>
  </div>;
}

function Recommendation({health}: {health: Health}) {
  const priority = [...health.components].sort((a, b) => ratio(a) - ratio(b))[0];
  if (!priority) return null;
  const prompt = encodeURIComponent(`Help me improve my financial health. My next priority is ${shortName(priority.name)} (${scoreText(priority.score)} of ${priority.max}). Give me a practical plan based on my wallet activity.`);
  return <section className="health-recommendation" aria-labelledby="priority-title">
    <span className="health-recommendation__icon"><Sparkles aria-hidden="true" /></span>
    <div><span className="eyebrow">Your next priority</span><h2 id="priority-title">Improve {shortName(priority.name).toLowerCase()}</h2><p>{factorCopy[priority.name]} Focus here first because it is the lowest-scoring part of your health indicator.</p></div>
    <Link className="button" to={`/coach/assistant?prompt=${prompt}`}>Build an improvement plan <MessageCircle /></Link>
  </section>;
}

function FactorList({health}: {health: Health}) {
  return <section className="health-factors-card" aria-labelledby="health-factors-title">
    <div className="health-section-heading"><div><span className="eyebrow">What affects your indicator</span><h2 id="health-factors-title">Health factors</h2><p>Each factor is assessed independently so you can see where change will matter most.</p></div></div>
    <div className="health-factor-list">
      {health.components.map((item) => <article className="health-factor" key={item.name}>
        <div className="health-factor__name"><h3>{shortName(item.name)}</h3><span className={`health-status health-status--${statusFor(item).toLowerCase().replace(/ /g, '-')}`}>{statusFor(item)}</span></div>
        <div className="health-factor__score"><strong>{scoreText(item.score)}<small> / {item.max}</small></strong><progress value={item.score} max={item.max} aria-label={`${shortName(item.name)}: ${scoreText(item.score)} of ${item.max}`} /></div>
        <p>{factorCopy[item.name]}</p>
        <ExplainMetricButton metric={{metricId: 'financial_health_factor', title: shortName(item.name), value: item.score, unit: 'points', source: 'financial_health', context: {factor: item.name, score: item.score, maximum: item.max, status: statusFor(item)}}} />
      </article>)}
    </div>
    <details className="health-calculation">
      <summary>See how this is calculated <ArrowRight aria-hidden="true" /></summary>
      <p>The overall indicator combines the five weighted factors below. It is designed to help you reflect on financial habits, not determine eligibility for financial products.</p>
      <div>{health.components.map((item) => <span key={item.name}><small>{shortName(item.name)}</small><strong>{scoreText(item.score)} / {item.max}</strong></span>)}</div>
    </details>
  </section>;
}

function Trend({health, history}: {health: Health; history?: HealthHistory}) {
  const points = history?.history || [];
  const previous = points.length > 1 ? points[points.length - 2]?.score : undefined;
  const change = previous === undefined ? undefined : health.score - previous;
  return <section className="health-trend" aria-labelledby="health-trend-title">
    <div className="health-section-heading"><div><span className="eyebrow">Health over time</span><h2 id="health-trend-title">Health trend</h2><p>{change === undefined || change === 0 ? 'Your indicator is steady compared with the previous period.' : `Your health indicator has ${change > 0 ? 'improved' : 'changed'} by ${Math.abs(change)} point${Math.abs(change) === 1 ? '' : 's'} since the previous period.`}</p></div>{points.length > 1 && <div className="health-trend__comparison"><span>Current</span><strong>{health.score}</strong><small>{change !== undefined && `${change > 0 ? '+' : ''}${change} from previous`}</small></div>}</div>
    {points.length > 1 ? <div className="health-trend__chart" role="img" aria-label={`Financial health trend: ${points.map((point) => `${point.month} ${point.score}`).join(', ')}`}>
      <ResponsiveContainer width="100%" height="100%"><AreaChart data={points} margin={{top: 12, right: 8, left: -26, bottom: 0}}><defs><linearGradient id="healthTrendFill" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="#167da7" stopOpacity=".22"/><stop offset="100%" stopColor="#167da7" stopOpacity="0"/></linearGradient></defs><XAxis dataKey="month" axisLine={false} tickLine={false} tick={{fontSize: 12, fill: '#71828d'}}/><YAxis domain={[0, 100]} hide/><Tooltip formatter={(value) => [`${value} / 100`, 'Financial Health']} labelStyle={{color: '#536878'}} contentStyle={{borderRadius: 10, borderColor: '#dbe5e9'}}/><Area type="monotone" dataKey="score" stroke="#167da7" strokeWidth={3} fill="url(#healthTrendFill)" /></AreaChart></ResponsiveContainer>
    </div> : <p className="empty-copy">Your trend will appear after another assessment period.</p>}
    {history?.note && <small className="health-trend__note">{history.note}</small>}
  </section>;
}

function SupportingEvidence({report}: {report: Props['report']}) {
  const rising = report.comparison.categories.filter((item) => item.difference > 0).sort((a, b) => b.difference - a.difference)[0];
  const relevantEvents = report.story.events.slice(0, 3);
  return <section className="health-evidence" aria-labelledby="health-evidence-title">
    <div className="health-section-heading"><div><span className="eyebrow">The evidence behind your assessment</span><h2 id="health-evidence-title">Supporting evidence</h2><p>{formatDate(report.period_range.start)}–{formatDate(report.period_range.end, true)}</p></div></div>
    <div className="health-evidence__cashflow"><span><small>Income</small><strong>{formatBDT(report.snapshot.income)}</strong></span><span><small>Spent</small><strong>{formatBDT(report.snapshot.spent)}</strong></span><span><small>Net cash flow</small><strong className={report.snapshot.net >= 0 ? 'money-positive' : 'money-negative'}>{formatBDT(report.snapshot.net, true)}</strong></span></div>
    {rising && <div className="spending-pressure"><div><span className="eyebrow">Spending pressure</span><h3>{rising.category} is the largest rising category this period</h3><p>{formatBDT(rising.current)} spent{rising.change_percent !== null ? ` · ${rising.change_percent > 0 ? '+' : ''}${Math.round(rising.change_percent)}% versus the previous period` : ''}. This can affect spending stability more than your other categories.</p></div><Link className="text-button" to="/coach/insights">View spending breakdown <ArrowRight /></Link></div>}
    {relevantEvents.length > 0 && <div className="health-events"><div><span className="eyebrow">Events affecting your health</span><h3>Recent activity</h3></div><div>{relevantEvents.map((event, index) => <article key={`${event.date}-${event.title}-${index}`}><time>{formatDate(event.date)}</time><span><strong>{event.title}</strong><small>{event.detail}</small></span>{event.amount !== 0 && <b className={event.type === 'income' || event.amount < 0 ? 'money-positive' : ''}>{formatBDT(event.amount, event.type === 'income' || event.amount < 0)}</b>}</article>)}</div><Link className="text-button" to="/coach/insights">View full Money Story <ArrowRight /></Link></div>}
  </section>;
}

export function FinancialHealthExperience({report, history}: Props) {
  const previous = history?.history.length && history.history.length > 1 ? history.history[history.history.length - 2].score : undefined;
  return <div className="financial-health-page">
    <header className="financial-health-page__header"><span className="eyebrow">Financial Health</span><h1>Your financial health</h1><p>Understand your current financial condition, what is influencing it, and one practical place to start.</p></header>
    <HealthSummaryHero health={report.health} previous={previous} />
    <StrengthsAndRisks health={report.health} comparison={report.comparison} />
    <Recommendation health={report.health} />
    <FactorList health={report.health} />
    <Trend health={report.health} history={history} />
    <SupportingEvidence report={report} />
  </div>;
}
