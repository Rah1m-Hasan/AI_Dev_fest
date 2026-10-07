import type {NavigateFunction} from 'react-router-dom';
import type {ExplainMetricContext} from './types';

export const AI_ASSIST_ROUTE = '/coach/assistant';
const explainMetricIds = new Set<ExplainMetricContext['metricId']>([
  'safe_to_spend', 'monthly_spending', 'savings_rate', 'money_runway', 'financial_health_score', 'financial_health_factor', 'savings_goal_progress', 'spending_category_change', 'remaining_budget',
]);

/**
 * Keeps every metric explanation hand-off on the same route and state shape.
 * Invalid or incomplete context is intentionally not sent to AI Assist.
 */
export function isExplainMetricContext(metric: Partial<ExplainMetricContext> | undefined | null): metric is ExplainMetricContext {
  if (!metric || !metric.metricId || !explainMetricIds.has(metric.metricId) || !metric.title?.trim() || !metric.source?.trim()) return false;
  if ((typeof metric.value !== 'string' && typeof metric.value !== 'number') || (typeof metric.value === 'string' && !metric.value.trim())) return false;
  if (typeof metric.value === 'number' && !Number.isFinite(metric.value)) return false;
  return !metric.context || Object.values(metric.context).every((value) => value === null || ['string', 'number', 'boolean'].includes(typeof value));
}

export function openMetricExplanation(navigate: NavigateFunction, metric: ExplainMetricContext) {
  if (!isExplainMetricContext(metric)) return;
  navigate(AI_ASSIST_ROUTE, {state: {explainMetric: metric}});
}

/** The API uses snake_case while UI components keep TypeScript-friendly camelCase. */
export function metricExplanationPayload(metric: ExplainMetricContext, language?: 'en' | 'bn') {
  const payload = {
    metric_id: metric.metricId,
    title: metric.title,
    value: metric.value,
    source: metric.source,
    ...(metric.unit ? {unit: metric.unit} : {}),
    ...(metric.context ? {context: metric.context} : {}),
    ...(language ? {language} : {}),
  };
  return payload;
}

export function formatExplainMetricValue(metric: ExplainMetricContext) {
  if (metric.unit === 'BDT') return `৳${typeof metric.value === 'number' ? metric.value.toLocaleString('en-US') : metric.value}`;
  return `${metric.value}${metric.unit ? ` ${metric.unit}` : ''}`;
}
