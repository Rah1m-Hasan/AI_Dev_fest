import {CircleHelp} from 'lucide-react';
import {useNavigate} from 'react-router-dom';
import {isExplainMetricContext, openMetricExplanation} from '../metricExplanation';
import type {ExplainMetricContext} from '../types';

/** A deliberately small, reusable hand-off to the existing AI Assist conversation. */
export function ExplainMetricButton({metric, variant = 'inline', className = ''}: {metric: ExplainMetricContext; variant?: 'inline' | 'compact'; className?: string}) {
  const navigate = useNavigate();
  if (!isExplainMetricContext(metric)) return null;
  return <button className={`explain-metric-button explain-metric-button--${variant} ${className}`.trim()} type="button" onClick={() => openMetricExplanation(navigate, metric)} aria-label={`Explain ${metric.title}`}><CircleHelp aria-hidden="true" size={16} />Explain</button>;
}
