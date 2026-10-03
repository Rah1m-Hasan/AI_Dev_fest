import { FormEvent, useEffect, useRef, useState } from 'react';
import { Send, Accessibility, ShieldCheck } from 'lucide-react';
import {useSearchParams} from 'react-router-dom';
import { api } from '../../api/client';
import { CoachAvatar } from '../ui';
import { Tag, TrustBadge } from '../ui';
import { QuickActionChips, TransactionDraftCard, TransferReviewCard, SafeToSpendCard, IncomeAdaptiveCard, GuidedProgress, TrustedContactsList, WarningCard, SuccessCard } from './CoachComponents';
import { PinConfirmationModal } from './PinConfirmationModal';
import type {DemoUser, IncomeAdaptive, SafeToSpend} from '../../types';

type ChatMessageType = {
  id: string;
  role: 'user' | 'ai';
  text: string;
  cardType?: string;
  cardData?: unknown;
  provider?: string;
  intent?: string;
};

interface ParsedIntent {
  intent: string;
  recipient_query: string | null;
  amount: number | null;
  currency: string;
  confidence: number;
  language: string;
}

interface Recipient {
  id: number;
  name: string;
  phone_number: string;
  relationship: string;
  is_trusted: boolean;
}

interface TransactionDraft {
  recipient_name: string;
  relationship: string;
  amount: number;
  fee: number;
  total: number;
  balance_after: number;
  safe_to_spend_before?: number;
  safe_to_spend_after?: number;
  runway_before_days?: number;
  runway_after_days?: number;
  relationship_evidence?: string[];
}

type DraftResponse = {draft_id: number; recipient: {id: number | null; name: string; phone: string | null}; relationship: string; relationship_evidence: string[]; amount: number; fee: number; total: number; available_balance: number; balance_after: number; safe_to_spend_before?: SafeToSpend; safe_to_spend_after?: number; runway_before_days?: number; runway_after_days?: number; state: string};

type FlowState = 'idle' | 'intent_received' | 'recipient_search' | 'awaiting_amount' | 'draft_ready' | 'reviewed' | 'awaiting_pin' | 'completed';

export function CoachPanel({ user }: { user: DemoUser }) {
  const [searchParams] = useSearchParams();
  const [messages, setMessages] = useState<ChatMessageType[]>([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [flowState, setFlowState] = useState<FlowState>('idle');
  const [intent, setIntent] = useState<ParsedIntent | null>(null);
  const [recipients, setRecipients] = useState<Recipient[]>([]);
  const [selectedRecipient, setSelectedRecipient] = useState<Recipient | null>(null);
  const [draft, setDraft] = useState<TransactionDraft | null>(null);
  const [draftId, setDraftId] = useState<number | null>(null);
  const [showPinModal, setShowPinModal] = useState(false);
  const [pinError, setPinError] = useState<string | null>(null);
  const [guided, setGuided] = useState(searchParams.get('guided') === '1');
  const [executing, setExecuting] = useState(false);
  const chatBodyRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (chatBodyRef.current) {
      chatBodyRef.current.scrollTop = chatBodyRef.current.scrollHeight;
    }
  }, [messages]);

  useEffect(() => {
    if (guided && !recipients.length) {
      void api<{items: Recipient[]}>('/trusted-contacts').then((data) => setRecipients(data.items)).catch(() => undefined);
    }
  }, [guided, recipients.length]);

  const addMessage = (msg: ChatMessageType) => {
    setMessages(prev => [...prev, msg]);
  };

  const handleQuickAction = async (action: string) => {
    const textMap: Record<string, string> = {
      send_money: 'I want to send money',
      safe_to_spend: 'How much can I safely spend?',
      spending: 'Why did I spend more?',
      check_balance: 'What is my current balance?',
      trusted_people: 'Find someone I trust',
      income: 'Help me save',
      runway: 'Will my balance last until my next income?',
      help: 'Help me with my finances',
    };
    await handleSend(textMap[action] || action);
  };

  const handleSend = async (text?: string) => {
    const messageText = (text || input).trim();
    if (!messageText || busy) return;

    setInput('');
    addMessage({ id: crypto.randomUUID(), role: 'user', text: messageText });
    setBusy(true);

    try {
      // Parse intent first
      const intentResult = await api<ParsedIntent>('/coach/parse-intent', {
        method: 'POST',
        body: JSON.stringify({ question: messageText, language: 'en' }),
      });

      setIntent(intentResult);

      if (intentResult.intent === 'send_money' || intentResult.intent === 'guided_send_money') {
        if (intentResult.intent === 'guided_send_money') setGuided(true);
        await handleSendMoneyIntent(intentResult, messageText);
      } else if (intentResult.intent === 'safe_to_spend') {
        await handleSafeToSpend();
      } else if (intentResult.intent === 'spending_analysis') {
        await handleRunOutAnalysis();
      } else if (intentResult.intent === 'money_runway') {
        await handleRunway();
      } else if (intentResult.intent === 'savings_help') {
        await handleFallbackChat('Help me save');
      } else if (intentResult.intent === 'check_balance') {
        await handleCheckBalance();
      } else if (messageText.toLowerCase().includes('income')) {
        await handleIncome();
      } else if (intentResult.intent === 'recipient_lookup') {
        await handleRecipientLookup(intentResult.recipient_query);
      } else {
        // Fallback to existing chat
        await handleFallbackChat(messageText);
      }
    } catch (err) {
      addMessage({
        id: crypto.randomUUID(),
        role: 'ai',
        text: "I couldn't process that right now. Please try again.",
      });
    } finally {
      setBusy(false);
    }
  };

  const handleSendMoneyIntent = async (intent: ParsedIntent, originalText: string) => {
    // Load trusted contacts
    const contactsResult = await api<{ items: Recipient[] }>('/trusted-contacts');
    setRecipients(contactsResult.items);

    if (intent.recipient_query && intent.amount) {
      // Both recipient and amount provided - create draft directly
      const resolved = await resolveRecipient(intent.recipient_query);
      if (resolved.contact) {
        setSelectedRecipient(resolved.contact);
        await createDraft(resolved.contact.id, resolved.contact.name, resolved.contact.phone_number, intent.amount);
      } else {
        addMessage({
          id: crypto.randomUUID(),
          role: 'ai',
          text: `I understood you want to send ৳${intent.amount.toLocaleString()} to "${intent.recipient_query}". Let me find that person in your contacts...`,
        });
        if (resolved.matches.length > 1) {
          addMessage({
            id: crypto.randomUUID(),
            role: 'ai',
            text: `I found multiple people matching "${intent.recipient_query}". Which did you mean?`,
            cardType: 'trusted_people',
            cardData: { contacts: resolved.matches },
          });
        } else {
          addMessage({
            id: crypto.randomUUID(),
            role: 'ai',
            text: `I couldn't find "${intent.recipient_query}" in your trusted contacts. Would you like me to search more broadly or choose someone else?`,
          });
        }
      }
    } else if (intent.recipient_query) {
      // Only recipient - ask for amount
      const resolved = await resolveRecipient(intent.recipient_query);
      if (resolved.contact) {
        setSelectedRecipient(resolved.contact);
        addMessage({
          id: crypto.randomUUID(),
          role: 'ai',
          text: `You usually send money to ${resolved.contact.name} — ${resolved.contact.relationship} · Trusted contact. How much would you like to send?`,
        });
        setFlowState('awaiting_amount');
      } else if (resolved.matches.length > 1) {
        addMessage({
          id: crypto.randomUUID(),
          role: 'ai',
          text: `I found multiple people matching "${intent.recipient_query}". Which did you mean?`,
          cardType: 'trusted_people',
          cardData: { contacts: resolved.matches },
        });
      } else {
        addMessage({
          id: crypto.randomUUID(),
          role: 'ai',
          text: `I couldn't find "${intent.recipient_query}" in your trusted contacts. Could you try a different name?`,
        });
      }
    } else if (intent.amount) {
      // Only amount - ask for recipient
      addMessage({
        id: crypto.randomUUID(),
        role: 'ai',
        text: `You want to send ৳${intent.amount.toLocaleString()}. Who would you like to send it to?`,
        cardType: 'trusted_people',
        cardData: { contacts: contactsResult.items },
      });
      setFlowState('recipient_search');
    } else {
      // Neither - ask for recipient first
      addMessage({
        id: crypto.randomUUID(),
        role: 'ai',
        text: "I can help you send money. Who would you like to send money to?",
        cardType: 'trusted_people',
        cardData: { contacts: contactsResult.items },
      });
      setFlowState('recipient_search');
    }
  };

  const handleSafeToSpend = async () => {
    const data = await api<{
      current_balance: number;
      upcoming_committed_expenses: number;
      recommended_reserve: number;
      safe_to_spend: number;
      breakdown: Record<string, number>;
    }>('/coach/safe-to-spend');

    addMessage({
      id: crypto.randomUUID(),
      role: 'ai',
      text: `You have about ৳${data.safe_to_spend.toLocaleString()} available after expected bills, your savings commitment, and a safety reserve. This is an estimate, not a spending guarantee.`,
      cardType: 'safe_to_spend',
      cardData: data,
    });
  };

  const handleRunOutAnalysis = async () => {
    const result = await api<{explanation: {text: string; provider: string}}>('/coach/run-out-analysis', {method: 'POST'});
    addMessage({id: crypto.randomUUID(), role: 'ai', text: result.explanation.text, provider: result.explanation.provider, intent: 'spending_analysis'});
  };

  const handleRunway = async () => {
    const data = await api<{runway: {days: number; upcoming: Array<{merchant: string; amount: number}>}}>('/dashboard/summary');
    const strongest = data.runway.upcoming[0];
    addMessage({id: crypto.randomUUID(), role: 'ai', text: `At your recent flexible spending pace, your balance may last about ${data.runway.days} days after known commitments.${strongest ? ` The strongest near-term factor is ${strongest.merchant} (about ৳${strongest.amount.toLocaleString()}).` : ''} This is a projection, not a guarantee.`, provider: 'deterministic_fallback', intent: 'money_runway'});
  };

  const resolveRecipient = async (query: string): Promise<{contact: Recipient | null; matches: Recipient[]}> => {
    const result = await api<{status: string; contact: Recipient | null; matches: Recipient[]}>(`/recipients/resolve?q=${encodeURIComponent(query)}`);
    return {contact: result.contact, matches: result.matches};
  };

  const handleCheckBalance = async () => {
    addMessage({
      id: crypto.randomUUID(),
      role: 'ai',
      text: `Your current available balance is ৳${user.balance.toLocaleString()}.\n\nIs there anything specific you'd like to know about your finances?`,
    });
  };

  const handleIncome = async () => {
    const data = await api<IncomeAdaptive>('/coach/income-adaptive');
    addMessage({id: crypto.randomUUID(), role: 'ai', text: data.explanation, cardType: 'income_insight', cardData: data});
  };

  const handleRecipientLookup = async (query: string | null) => {
    if (!query) {
      const contacts = await api<{ items: Recipient[] }>('/trusted-contacts');
      addMessage({
        id: crypto.randomUUID(),
        role: 'ai',
        text: 'Here are your trusted contacts:',
        cardType: 'trusted_people',
        cardData: { contacts: contacts.items },
      });
      return;
    }

    const results = await api<{ items: Recipient[] }>(`/recipients/search?q=${encodeURIComponent(query)}`);
    if (results.items.length === 1) {
      const contact = results.items[0];
      const relInfo = await api(`/recipients/${contact.id}/relationship`);
      addMessage({
        id: crypto.randomUUID(),
        role: 'ai',
        text: `${contact.name} is your ${contact.relationship}. ${(relInfo as any).evidence?.join(' ') || ''}`,
      });
    } else if (results.items.length > 1) {
      addMessage({
        id: crypto.randomUUID(), role: 'ai',
        text: `I found ${results.items.length} contacts matching "${query}". Which one do you mean?`,
        cardType: 'trusted_people', cardData: {contacts: results.items},
      });
    } else {
      addMessage({
        id: crypto.randomUUID(),
        role: 'ai',
        text: `I couldn't find a contact matching "${query}".`,
      });
    }
  };

  const handleFallbackChat = async (question: string) => {
    const result = await api<{
      answer: { text: string; provider: string };
      intent: string;
      structured_context: Record<string, unknown>;
    }>('/coach/chat', {
      method: 'POST',
      body: JSON.stringify({ question, language: 'en' }),
    });

    addMessage({
      id: crypto.randomUUID(),
      role: 'ai',
      text: result.answer.text,
      provider: result.answer.provider,
      intent: result.intent,
    });
  };

  const createDraft = async (recipientId: number, recipientName: string, recipientPhone: string, amount: number) => {
    try {
      const params = new URLSearchParams({recipient_id: String(recipientId), recipient_name: recipientName, recipient_phone: recipientPhone, amount: String(amount)});
      const draftData = await api<DraftResponse>(`/transactions/draft?${params}`, {method: 'POST'});
      const safeBefore = draftData.safe_to_spend_before?.safe_to_spend;
      const presentationDraft: TransactionDraft = {recipient_name: draftData.recipient.name, relationship: draftData.relationship, amount: draftData.amount, fee: draftData.fee, total: draftData.total, balance_after: draftData.balance_after, safe_to_spend_before: safeBefore, safe_to_spend_after: draftData.safe_to_spend_after, runway_before_days: draftData.runway_before_days, runway_after_days: draftData.runway_after_days, relationship_evidence: draftData.relationship_evidence};

      setDraft(presentationDraft);
      setDraftId(draftData.draft_id);
      setFlowState('draft_ready');

      // Check if amount exceeds safe-to-spend
      const impact = await api<{ warning: string | null }>(`/transactions/check-impact?amount=${encodeURIComponent(String(amount))}`, {method: 'POST'});

      addMessage({
        id: crypto.randomUUID(),
        role: 'ai',
        text: `I've prepared the transfer. Please review the details below.`,
        cardType: 'transaction_draft',
        cardData: presentationDraft,
      });

      if (impact.warning) {
        addMessage({
          id: crypto.randomUUID(),
          role: 'ai',
          text: impact.warning,
          cardType: 'warning',
        });
      }
    } catch (err) {
      addMessage({
        id: crypto.randomUUID(),
        role: 'ai',
        text: "I couldn't create the transfer. Please try again.",
      });
    }
  };

  const handleReviewDraft = async () => {
    if (!draftId) return;
    try {
      await api(`/transactions/draft/${draftId}/review`, {method: 'POST'});
      setFlowState('reviewed');
      addMessage({id: crypto.randomUUID(), role: 'ai', text: 'Please check the transfer summary. AI Assist cannot confirm it for you.', cardType: 'transaction_review', cardData: draft});
    } catch {
      addMessage({id: crypto.randomUUID(), role: 'ai', text: "I couldn't open this transfer for review. Please try again."});
    }
  };

  const handleConfirmDraft = async () => {
    if (!draftId) return;
    try {
      await api(`/transactions/draft/${draftId}/confirm`, {method: 'POST'});
      setPinError(null);
      setShowPinModal(true);
      setFlowState('awaiting_pin');
    } catch (err) {
      addMessage({
        id: crypto.randomUUID(),
        role: 'ai',
        text: "I couldn't confirm the transfer. Please try again.",
      });
    }
  };

  const handlePinSubmit = async (pin: string) => {
    if (!draftId) return;
    setExecuting(true);
    try {
      const result = await api<{ success: boolean; message: string; balance_after?: number }>(
        `/transactions/draft/${draftId}/execute`,
        {
          method: 'POST',
          body: JSON.stringify({ draft_id: draftId, pin }),
        }
      );

      setShowPinModal(false);

      if (result.success) {
        setFlowState('completed');
        addMessage({
          id: crypto.randomUUID(),
          role: 'ai',
          text: `৳${draft?.amount.toLocaleString()} was sent successfully in this demo.\n\nBalance: ৳${result.balance_after?.toLocaleString()}`,
          cardType: 'success',
        });
      } else {
        setPinError(result.message);
      }
    } catch (err) {
      setPinError("Incorrect PIN. Please try again.");
    } finally {
      setExecuting(false);
    }
  };

  const cancelDraft = async () => {
    if (draftId) await api(`/transactions/draft/${draftId}`, {method: 'DELETE'}).catch(() => undefined);
    setDraft(null); setDraftId(null); setFlowState('idle');
    addMessage({id: crypto.randomUUID(), role: 'ai', text: 'This transfer draft was cancelled. No money was moved.'});
  };

  const handleSelectRecipient = (recipient: Recipient) => {
    setSelectedRecipient(recipient);
    if (flowState === 'recipient_search' || flowState === 'awaiting_amount') {
      if (intent?.amount) {
        createDraft(recipient.id, recipient.name, recipient.phone_number, intent.amount);
      } else {
        addMessage({
          id: crypto.randomUUID(),
          role: 'ai',
          text: `You selected ${recipient.name}. How much would you like to send?`,
        });
        setFlowState('awaiting_amount');
      }
    }
  };

  const startGuidedRecipient = (recipient: Recipient) => {
    setSelectedRecipient(recipient);
    setFlowState('awaiting_amount');
    addMessage({id: crypto.randomUUID(), role: 'ai', text: `You chose ${recipient.name}. How much would you like to send?`});
  };

  const handleAmountInput = async (text: string) => {
    const match = text.match(/[\d,]+/);
    if (!match) {
      addMessage({
        id: crypto.randomUUID(),
        role: 'ai',
        text: "I couldn't understand the amount. Please enter a number like 500 or 2000.",
      });
      return;
    }

    const amount = parseFloat(match[0].replace(/,/g, ''));
    if (amount <= 0) {
      addMessage({
        id: crypto.randomUUID(),
        role: 'ai',
        text: "Please enter an amount greater than zero.",
      });
      return;
    }

    if (selectedRecipient) {
      await createDraft(selectedRecipient.id, selectedRecipient.name, selectedRecipient.phone_number, amount);
    } else {
      addMessage({
        id: crypto.randomUUID(),
        role: 'ai',
        text: "Who would you like to send ৳" + amount.toLocaleString() + " to?",
      });
      setFlowState('recipient_search');
    }
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (flowState === 'awaiting_amount') {
      handleAmountInput(input);
    } else {
      void handleSend();
    }
  };

  return (
    <div className={`coach-page ai-assist-page ${guided ? 'ai-assist-page--guided' : ''}`}>
      <div className="ai-assist-intro"><div><span className="eyebrow">UPAY AI ASSIST</span><h1>{guided ? 'Let’s do this one step at a time.' : 'AI Assist'}</h1><p>{guided ? 'Large, simple steps for a secure transfer. You can go back or cancel at any time.' : 'Your money, made clearer.'}</p></div><button className="guided-toggle" onClick={() => setGuided(!guided)}><Accessibility />{guided ? 'Guided Mode on' : 'Try Guided Mode'}</button></div>
      {guided && <GuidedProgress step={flowState === 'idle' || flowState === 'recipient_search' ? 1 : flowState === 'awaiting_amount' ? 2 : flowState === 'draft_ready' ? 3 : 4} total={4} label={flowState === 'draft_ready' ? 'Review transfer' : flowState === 'awaiting_pin' ? 'Confirm securely' : 'Send money'} />}
      <section className="chat-shell">
        <header className="chat-header">
          <CoachAvatar />
          <span>
            <strong>AI Assist</strong>
            <small><i /> Grounded in your financial activity</small>
          </span>
          <TrustBadge>Informational guidance</TrustBadge>
        </header>

        <div className="chat-body" ref={chatBodyRef} aria-live="polite">
          {!messages.length && !busy && (guided ? <div className="guided-start">
            <span className="eyebrow">STEP 1</span><h2>Who do you want to send money to?</h2><p>Choose a saved person, or search your contacts.</p>
            <div className="guided-start__choices">{recipients.slice(0, 2).map((recipient) => <button key={recipient.id} onClick={() => startGuidedRecipient(recipient)}><span className="trusted-contact-avatar">{recipient.name.split(' ').map((part) => part[0]).join('').slice(0, 2)}</span><span><strong>{recipient.name}</strong><small>{recipient.relationship}</small></span></button>)}<button onClick={() => void handleQuickAction('send_money')}><span className="trusted-contact-avatar">+</span><span><strong>Search contact</strong><small>Choose someone else</small></span></button></div>
          </div> : <div className="ai-assist-welcome">
            <span className="ai-assist-welcome__mark"><ShieldCheck /></span>
            <span className="eyebrow">UPAY AI ASSIST</span>
            <h2>How can I help?</h2>
            <p>I can prepare a payment, explain recent spending, or help you make a simple plan. You review every money action.</p>
          </div>)}
          {messages.map((msg) => (
            <div key={msg.id} className={`chat-message chat-message--${msg.role}`}>
              {msg.role === 'ai' && <CoachAvatar />}
              <div>
                {msg.provider && (
                  <Tag tone={msg.provider === 'groq_grounded' ? 'ai' : 'neutral'}>
                    {msg.provider === 'groq_grounded' ? 'AI explanation' : 'Calculated fallback'}
                  </Tag>
                )}
                <p>{msg.text}</p>

                {msg.cardType === 'transaction_draft' && !!msg.cardData && (
                  <div className="chat-card">
                    <TransactionDraftCard
                      draft={msg.cardData as TransactionDraft}
                      onReview={flowState === 'draft_ready' ? handleReviewDraft : undefined}
                      onCancel={() => void cancelDraft()}
                    />
                  </div>
                )}

                {msg.cardType === 'transaction_review' && !!msg.cardData && <div className="chat-card"><TransferReviewCard draft={msg.cardData as TransactionDraft} onConfirm={handleConfirmDraft} onCancel={() => void cancelDraft()} /></div>}

                {msg.cardType === 'safe_to_spend' && !!msg.cardData && (
                  <div className="chat-card">
                    <SafeToSpendCard data={msg.cardData as SafeToSpend} />
                  </div>
                )}

                {msg.cardType === 'trusted_people' && !!msg.cardData && (
                  <div className="chat-card">
                    <TrustedContactsList
                      contacts={(msg.cardData as {contacts: Recipient[]}).contacts}
                      onSelect={(id) => {
                        const contact = (msg.cardData as {contacts: Recipient[]}).contacts.find((c) => c.id === id);
                        if (contact) handleSelectRecipient(contact);
                      }}
                    />
                  </div>
                )}

                {msg.cardType === 'warning' && (
                  <div className="chat-card">
                    <WarningCard message={msg.text} />
                  </div>
                )}

                {msg.cardType === 'income_insight' && !!msg.cardData && <div className="chat-card"><IncomeAdaptiveCard data={msg.cardData as IncomeAdaptive} /></div>}

                {msg.cardType === 'success' && (
                  <div className="chat-card">
                    <SuccessCard message={msg.text} />
                  </div>
                )}
              </div>
            </div>
          ))}

          {busy && (
            <div className="chat-message chat-message--ai">
              <CoachAvatar />
              <div className="typing" aria-label="AI Assist is thinking">
                <i /><i /><i />
              </div>
            </div>
          )}
        </div>

        {messages.length < 2 && (
          <QuickActionChips onAction={handleQuickAction} />
        )}

        <form className="chat-composer" onSubmit={handleSubmit}>
          <label className="sr-only" htmlFor="coach-input">Ask about your money</label>
          <input
            id="coach-input"
            maxLength={500}
            placeholder="Ask about your money…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
          />
          <button type="submit" disabled={!input.trim() || busy} aria-label="Send question">
            <Send size={18} />
          </button>
        </form>
      </section>

      {showPinModal && (
        <PinConfirmationModal
          onConfirm={handlePinSubmit}
          onCancel={() => setShowPinModal(false)}
          error={pinError}
          recipient={draft?.recipient_name || 'your recipient'}
          amount={draft?.amount || 0}
          total={draft?.total || 0}
          busy={executing}
        />
      )}
    </div>
  );
}
