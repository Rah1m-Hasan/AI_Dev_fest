import { Check, AlertTriangle, ArrowRight, X, ShieldCheck, User, Users, Clock, DollarSign, PiggyBank, TrendingUp, HelpCircle } from 'lucide-react';
import { formatBDT } from '../../format';

export type CardType = 'recipient_card' | 'transaction_draft' | 'safe_to_spend' | 'income_insight' | 'trusted_helper' | 'quick_actions' | 'warning' | 'success' | 'guided_progress';

interface BaseCardProps {
  onAction?: (action: string) => void;
}

export function RecipientCard({ contact, onAction }: { contact: { id: number; name: string; phone_number: string; relationship: string; is_trusted: boolean }; onAction?: (action: string) => void }) {
  return (
    <div className="coach-card coach-card--recipient">
      <div className="coach-card__header">
        <span className="coach-card__icon"><User size={18} /></span>
        <span className="coach-card__title">Recipient</span>
        {contact.is_trusted && <span className="coach-card__badge"><ShieldCheck size={12} /> Trusted</span>}
      </div>
      <div className="coach-card__body">
        <h3>{contact.name}</h3>
        <p className="coach-card__meta">{contact.relationship} · {contact.phone_number}</p>
      </div>
      {onAction && (
        <div className="coach-card__actions">
          <button className="button button--small" onClick={() => onAction('change')}>Change</button>
        </div>
      )}
    </div>
  );
}

export function TransactionDraftCard({
  draft,
  onReview,
  onChange,
  onCancel,
}: {
  draft: {
    recipient_name: string;
    relationship: string;
    amount: number;
    fee: number;
    total: number;
    balance_after: number;
  safe_to_spend_before?: number;
  safe_to_spend_after?: number;
  relationship_evidence?: string[];
  };
  onReview?: () => void;
  onChange?: () => void;
  onCancel?: () => void;
}) {
  return (
    <div className="coach-card coach-card--draft">
      <div className="coach-card__header">
        <span className="coach-card__icon"><DollarSign size={18} /></span>
        <span className="coach-card__title">Send Money</span>
      </div>
      <div className="coach-card__body">
        <div className="draft-recipient"><span className="trusted-contact-avatar">{draft.recipient_name.split(' ').map((name) => name[0]).join('').slice(0, 2)}</span><span><small>Sending to</small><strong>{draft.recipient_name}</strong><em><ShieldCheck size={12} /> {draft.relationship}</em></span></div>
        {draft.relationship_evidence?.length ? <p className="draft-evidence">{draft.relationship_evidence[0]}</p> : null}
        <div className="draft-row">
          <span>Amount</span>
          <strong className="money-positive">{formatBDT(draft.amount)}</strong>
        </div>
        <div className="draft-row">
          <span>Fee</span>
          <strong>{formatBDT(draft.fee)}</strong>
        </div>
        <div className="draft-row draft-row--total">
          <span>Total</span>
          <strong>{formatBDT(draft.total)}</strong>
        </div>
        <div className="draft-row">
          <span>Balance after</span>
          <strong>{formatBDT(draft.balance_after)}</strong>
        </div>
        {draft.safe_to_spend_before !== undefined && (
          <div className="draft-impact"><span><small>Safe to spend</small><strong>{formatBDT(draft.safe_to_spend_before)}</strong></span><ArrowRight size={16} /><span><small>After transfer</small><strong>{formatBDT(draft.safe_to_spend_after || 0)}</strong></span></div>
        )}
      </div>
      <div className="coach-card__actions">
        {onChange && <button className="button button--small button--ghost" onClick={onChange}>Edit</button>}
        {onCancel && <button className="button button--small button--ghost" onClick={onCancel}>Cancel</button>}
        {onReview && <button className="button button--small" onClick={onReview}>Review transfer <ArrowRight size={14} /></button>}
      </div>
    </div>
  );
}

export function TransferReviewCard({draft, onConfirm, onCancel}: {draft: {
  recipient_name: string; relationship: string; amount: number; fee: number; total: number;
  balance_after: number; safe_to_spend_before?: number; safe_to_spend_after?: number;
  runway_before_days?: number; runway_after_days?: number;
}; onConfirm: () => void; onCancel: () => void}) {
  return <div className="coach-card coach-card--review">
    <div className="coach-card__header"><span className="coach-card__icon"><ShieldCheck size={18} /></span><span className="coach-card__title">Review transfer</span></div>
    <div className="coach-card__body">
      <div className="draft-recipient"><span className="trusted-contact-avatar">{draft.recipient_name.split(' ').map((name) => name[0]).join('').slice(0, 2)}</span><span><small>To</small><strong>{draft.recipient_name}</strong><em><ShieldCheck size={12} /> {draft.relationship}</em></span></div>
      <div className="draft-row"><span>Amount</span><strong>{formatBDT(draft.amount)}</strong></div>
      <div className="draft-row"><span>Fee</span><strong>{formatBDT(draft.fee)}</strong></div>
      <div className="draft-row draft-row--total"><span>Total</span><strong>{formatBDT(draft.total)}</strong></div>
      <div className="draft-row"><span>Balance after</span><strong>{formatBDT(draft.balance_after)}</strong></div>
      {draft.safe_to_spend_after !== undefined && <div className="draft-row"><span>Safe-to-Spend after</span><strong>{formatBDT(draft.safe_to_spend_after)}</strong></div>}
      {draft.runway_before_days !== undefined && <div className="draft-impact"><span><small>Estimated runway</small><strong>{draft.runway_before_days} days</strong></span><ArrowRight size={16} /><span><small>After transfer</small><strong>{draft.runway_after_days} days</strong></span></div>}
      <p className="review-note">This is a simulated transfer. You will enter your PIN yourself before it completes.</p>
    </div>
    <div className="coach-card__actions"><button className="button button--small button--ghost" onClick={onCancel}>Cancel</button><button className="button button--small" onClick={onConfirm}>Confirm <ArrowRight size={14} /></button></div>
  </div>;
}

export function SafeToSpendCard({ data }: { data: { current_balance: number; upcoming_committed_expenses: number; recommended_reserve: number; reserved_savings?: number; safe_to_spend: number; breakdown: Record<string, number> } }) {
  return (
    <div className="coach-card coach-card--safe">
      <div className="coach-card__header">
        <span className="coach-card__icon"><PiggyBank size={18} /></span>
        <span className="coach-card__title">Safe-to-Spend</span>
      </div>
      <div className="coach-card__body">
        <div className="safe-amount">
          <strong>{formatBDT(data.safe_to_spend)}</strong>
          <small>Estimated flexible amount</small>
        </div>
        <div className="safe-breakdown">
          <div className="safe-row">
            <span>Current balance</span>
            <span>{formatBDT(data.current_balance)}</span>
          </div>
          <div className="safe-row">
            <span>Upcoming expenses</span>
            <span>-{formatBDT(data.upcoming_committed_expenses)}</span>
          </div>
          <div className="safe-row">
            <span>Safety reserve</span>
            <span>-{formatBDT(data.recommended_reserve)}</span>
          </div>
          {(data.reserved_savings || 0) > 0 && <div className="safe-row"><span>Savings commitment</span><span>-{formatBDT(data.reserved_savings || 0)}</span></div>}
        </div>
        <details className="answer-trust"><summary>Why this answer?</summary><p>Known bills, savings settings, and transaction history were calculated first. AI only explains this result; it cannot move money or access your PIN.</p></details>
      </div>
      <div className="coach-card__footer">
        <ShieldCheck size={12} />
        <span>Based on known commitments and recent synthetic activity.</span>
      </div>
    </div>
  );
}

export function IncomeAdaptiveCard({ data }: { data: { income_last_7_days: number; average_weekly_income: number; difference_percent: number; suggested_savings_min: number; suggested_savings_max: number; explanation: string } }) {
  const isUp = data.difference_percent > 0;
  return (
    <div className="coach-card coach-card--income">
      <div className="coach-card__header">
        <span className="coach-card__icon"><TrendingUp size={18} /></span>
        <span className="coach-card__title">Income This Week</span>
      </div>
      <div className="coach-card__body">
        <div className="income-amount">
          <strong>{formatBDT(data.income_last_7_days)}</strong>
          <small className={isUp ? 'money-positive' : 'money-negative'}>
            {isUp ? '+' : ''}{data.difference_percent.toFixed(0)}% vs usual
          </small>
        </div>
        <div className="income-compare">
          <div className="income-row">
            <span>Usual weekly income</span>
            <span>{formatBDT(data.average_weekly_income)}</span>
          </div>
        </div>
        <div className="income-savings">
          <span className="income-savings__label">Suggested saving</span>
          <strong>{formatBDT(data.suggested_savings_min)}–{formatBDT(data.suggested_savings_max)}</strong>
        </div>
        <p className="income-explanation">{data.explanation}</p>
      </div>
    </div>
  );
}

export function GuidedProgress({ step, total, label }: { step: number; total: number; label: string }) {
  return (
    <div className="guided-progress">
      <div className="guided-progress__header">
        <span>Step {step} of {total}</span>
        <span className="guided-progress__label">{label}</span>
      </div>
      <div className="guided-progress__bar">
        <div className="guided-progress__fill" style={{ width: `${(step / total) * 100}%` }} />
      </div>
    </div>
  );
}

export function QuickActionChips({ onAction }: { onAction: (action: string) => void }) {
  const actions = [
    { id: 'send_money', label: 'Send Money', icon: DollarSign },
    { id: 'safe_to_spend', label: 'Can I afford something?', icon: PiggyBank },
    { id: 'spending', label: 'Why did I spend more?', icon: TrendingUp },
    { id: 'income', label: 'Help me save', icon: Users },
    { id: 'runway', label: 'Check my money runway', icon: Clock },
    { id: 'trusted_people', label: 'Find someone I trust', icon: HelpCircle },
  ];

  return (
    <div className="quick-actions">
      {actions.map(({ id, label, icon: Icon }) => (
        <button key={id} className="quick-action-chip" onClick={() => onAction(id)}>
          <Icon size={14} />
          <span>{label}</span>
        </button>
      ))}
    </div>
  );
}

export function TrustedContactsList({ contacts, onSelect }: { contacts: Array<{ id: number; name: string; relationship: string; phone_number: string; is_trusted: boolean }>; onSelect?: (id: number) => void }) {
  return (
    <div className="trusted-contacts-list">
      <h3>Trusted People</h3>
      <div className="trusted-contacts-grid">
        {contacts.map((contact) => (
          <button key={contact.id} className="trusted-contact-card" onClick={() => onSelect?.(contact.id)}>
            <span className="trusted-contact-avatar">{contact.name.split(' ').map(n => n[0]).join('').slice(0, 2)}</span>
            <div className="trusted-contact-info">
              <strong>{contact.name}</strong>
              <small>{contact.relationship}</small>
            </div>
            {contact.is_trusted && <ShieldCheck size={14} className="trusted-badge" />}
          </button>
        ))}
      </div>
    </div>
  );
}

export function WarningCard({ message, onContinue }: { message: string; onContinue?: () => void }) {
  return (
    <div className="coach-card coach-card--warning">
      <div className="coach-card__header">
        <span className="coach-card__icon"><AlertTriangle size={18} /></span>
        <span className="coach-card__title">Note</span>
      </div>
      <div className="coach-card__body">
        <p>{message}</p>
      </div>
      {onContinue && (
        <div className="coach-card__actions">
          <button className="button button--small" onClick={onContinue}>Continue Anyway</button>
        </div>
      )}
    </div>
  );
}

export function SuccessCard({ message }: { message: string }) {
  return (
    <div className="coach-card coach-card--success">
      <div className="coach-card__header">
        <span className="coach-card__icon"><Check size={18} /></span>
        <span className="coach-card__title">Success</span>
      </div>
      <div className="coach-card__body">
        <p>{message}</p>
      </div>
    </div>
  );
}
