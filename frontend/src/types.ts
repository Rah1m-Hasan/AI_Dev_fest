export type DemoUser = {
  id: number;
  email: string;
  display_name: string;
  persona: string;
  preferred_language: string;
  balance: number;
};

export type Transaction = {
  id: number;
  merchant_name: string;
  category: string;
  amount: number;
  direction: 'income' | 'expense' | 'out';
  transaction_type: string;
  timestamp: string;
  is_recurring: boolean;
  description: string;
  source: string;
};

export type Change = {
  category: string;
  current: number;
  previous: number;
  difference: number;
  change_percent: number | null;
  direction: 'up' | 'down' | 'flat';
};

export type MoneyPulse = {
  status: string;
  headline: string;
  text: string;
  why: Array<{label: string; detail: string}>;
  next: string;
  money_runway_days: number;
  confidence: string;
};

export type MoneyRunway = {
  days: number;
  projected_until: string;
  today_balance: number;
  expected_14_day_expenses: number;
  expected_14_day_income: number;
  expected_14_day_balance: number;
  buffer: number;
  confidence: string;
  label: string;
  upcoming: Array<{merchant: string; amount: number; expected_date: string; expected_in_days: number}>;
};

export type SafeToSave = {
  period_days: number;
  low: number;
  high: number;
  recommended: number;
  breakdown: {
    available_balance: number;
    expected_income: number;
    upcoming_bills: number;
    typical_spending: number;
    safety_buffer: number;
    liquidity_after_needs: number;
    disposable_cash_flow_cap: number;
    estimated_flexibility: number;
  };
  label: string;
  basis: string;
};

export type Health = {
  score: number;
  label: string;
  disclaimer: string;
  what_improved: string;
  components: Array<{name: string; score: number; max: number}>;
};

export type StoryEvent = {
  date: string;
  type: string;
  title: string;
  detail: string;
  amount: number;
};

export type MoneyStory = {
  period: {start: string; end: string};
  events: StoryEvent[];
  today: {date: string; balance: number};
  source: string;
};

export type DashboardSummary = {
  period_label: string;
  balance: number;
  this_month: {income: number; spending: number; savings: number};
  budget: {limit: number; used: number; utilization: number};
  health: Health;
  spending_breakdown: Array<{category: string; amount: number; percentage: number; previous_amount: number; change_percent: number | null}>;
  weekly_spend: Array<{week: string; amount: number}>;
  recent_transactions: Transaction[];
  forecast: Record<string, unknown>;
  pulse: MoneyPulse;
  runway: MoneyRunway;
  safe_to_spend: SafeToSpend;
  comparison: {period: {start: string; end: string}; categories: Change[]; summary: string; source: string};
  safe_to_save: SafeToSave;
  story: MoneyStory;
};

export type BudgetRecommendation = {
  recommended_total_spending: number;
  essential_budget: number;
  flexible_budget: number;
  savings_target: number;
  category_limits: Record<string, number>;
  buffer_contribution: number;
  emergency_buffer: number;
  income_stability: string;
  confidence: string;
  reasoning: string;
  period_income: number;
  fixed_recurring_costs: number;
};

export type Goal = {
  id: number;
  name: string;
  target_amount: number;
  current_amount: number;
  target_date: string;
  progress_percent: number;
  plan: {
    recommended_weekly_contribution: number;
    recommended_monthly_contribution: number;
    feasible: boolean;
    alternatives: string[];
    basis: string;
  };
};

export type CoachMessage = {
  id: string;
  role: 'user' | 'ai';
  text: string;
  evidence?: Record<string, unknown>;
  provider?: string;
  intent?: string;
};

export type TrustedContact = {
  id: number;
  name: string;
  phone_number: string;
  relationship: string;
  nickname?: string;
  is_trusted: boolean;
};

export type TransactionDraft = {
  draft_id?: number;
  recipient: {
    id: number | null;
    name: string;
    phone: string | null;
  };
  relationship: string;
  amount: number;
  fee: number;
  total: number;
  available_balance: number;
  balance_after: number;
  safe_to_spend_before?: number;
  reference?: string;
  state: string;
};

export type SafeToSpend = {
  current_balance: number;
  upcoming_committed_expenses: number;
  recommended_reserve: number;
  safe_to_spend: number;
  breakdown: Record<string, number>;
};

export type IncomeAdaptive = {
  income_last_7_days: number;
  average_weekly_income: number;
  difference_percent: number;
  income_pattern: string;
  suggested_savings_min: number;
  suggested_savings_max: number;
  explanation: string;
};
