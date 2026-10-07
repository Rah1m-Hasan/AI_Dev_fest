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
  ml?: MlSummary;
};

export type MlSummary = {
  predicted_7_day_spending: number;
  predicted_30_day_spending: number;
  predicted_month_end_balance: number;
  financial_risk: 'LOW' | 'MEDIUM' | 'HIGH';
  risk_probability?: number;
  safe_to_spend: number;
  safe_to_spend_per_day: number;
  money_runway_days: number;
  forecast_source: 'ml' | 'deterministic_fallback';
  risk_source: 'ml' | 'deterministic_fallback';
};

export type MlMetrics = {
  available: boolean;
  training_samples?: number;
  test_samples?: number;
  test_split?: number;
  spending_forecast?: {algorithm: string; mae: number; rmse: number; r2: number};
  risk_classifier?: {algorithm: string; accuracy: number; precision: number; recall: number; f1: number; roc_auc?: number | null};
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

export type MonthlyPlan = {
  status: 'recommended' | 'customized' | 'accepted';
  allocations: {essentials: number; flexible: number; savings: number; safety_buffer: number};
  categories: Record<string, number>;
  accepted_at: string | null;
  updated_at: string | null;
  customized: boolean;
};

export type PlanWorkspace = {recommendation: BudgetRecommendation; plan: MonthlyPlan};

export type Goal = {
  id: number;
  name: string;
  target_amount: number;
  current_amount: number;
  target_date: string;
  status: 'active' | 'paused' | 'completed';
  category: string;
  saving_preference: 'weekly' | 'monthly' | 'flexible';
  note?: string | null;
  planned_monthly_amount?: number | null;
  progress_percent: number;
  plan: {
    recommended_weekly_contribution: number;
    recommended_monthly_contribution: number;
    comfortable_weekly_low: number;
    comfortable_weekly_high: number;
    selected_monthly_contribution?: number | null;
    feasible: boolean;
    status: 'on_track' | 'needs_adjustment' | 'completed' | 'paused' | 'deadline_passed';
    remaining_amount: number;
    days_remaining: number;
    projected_completion_date?: string | null;
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

/** Context produced by existing deterministic product calculations for AI Assist to explain. */
export type ExplainMetricContext = {
  metricId: 'safe_to_spend' | 'monthly_spending' | 'savings_rate' | 'money_runway' | 'financial_health_score' | 'financial_health_factor' | 'savings_goal_progress' | 'spending_category_change' | 'remaining_budget';
  title: string;
  value: number | string;
  unit?: string;
  source: string;
  context?: Record<string, string | number | boolean | null>;
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

// --- Learn types ---
export type QuizOption = { key: string; text: string };
export type Quiz = { question: string; options: QuizOption[]; correct_key: string };
export type LessonCard = {
  id: number;
  title: string;
  summary: string;
  category: string;
  difficulty: string;
  duration_minutes: number;
  trigger_type: string | null;
  trigger_reason: string | null;
  completed: boolean;
  started: boolean;
};
export type LessonDetail = LessonCard & {
  content: string;
  content_bn: string | null;
  personalized_section: string | null;
  personalized_section_bn: string | null;
  initial_language?: 'en' | 'bn';
  quiz: Quiz | null;
  completed: boolean;
  started: boolean;
};
export type LessonProgressSummary = { category: string; completed: number; total: number };
export type LearningResponse = {
  featured: LessonCard | null;
  for_you: LessonCard[];
  tabs: string[];
  progress: LessonProgressSummary[];
};
export type LessonCompleteResult = { completed: boolean; quiz_score: number | null };

// --- Offers types ---
export type OfferCard = {
  id: number;
  title: string;
  terms: string;
  terms_bn: string | null;
  category: string;
  min_spend: number | null;
  discount_percent: number | null;
  discount_fixed: number | null;
  max_discount: number | null;
  typical_purchase: number | null;
  typical_merchant: string | null;
  potential_saving: number | null;
  expiry_date: string | null;
  eligibility_notes: string | null;
  fit_status: 'good_fit' | 'conditional_fit' | 'not_useful' | null;
  is_saved: boolean;
  learning_lesson_id: number | null;
  state?: 'active' | 'upcoming' | 'expired';
  why_relevant?: string | null;
};
export type OfferDetail = OfferCard & { why_relevant: string | null };
export type OfferPreferences = { personalized_offers_enabled: boolean };
export type OffersResponse = { offers: OfferCard[]; preferences: OfferPreferences; available_categories: string[]; state: string };
