import {FormEvent, useEffect, useRef, useState} from 'react';
import {Accessibility, ArrowDown, ArrowRight, ArrowUp, CheckCircle2, LockKeyhole, Sparkles} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {useLocation, useNavigate} from 'react-router-dom';
import {api} from '../../api/client';
import {formatBDT, formatValue, type ValueType} from '../../format';
import {formatExplainMetricValue, isExplainMetricContext, metricExplanationPayload} from '../../metricExplanation';
import {CoachAvatar} from '../ui';
import {PinConfirmationModal} from './PinConfirmationModal';
import {TransactionDraftCard} from './CoachComponents';
import type {DemoUser, ExplainMetricContext} from '../../types';

type Response = {conversation_id?: string; type: string; message: string; intent?: string; status?: string; data?: Record<string, unknown>; result?: Record<string, unknown>; action?: {id: string; name?: string; status?: string}; preview?: Record<string, unknown>; options?: Array<{id: number; name: string; relationship: string}>; transactions?: Array<{id: number; merchant_name: string; amount: number; direction: string; category: string}>};
type Message = {id: string; role: 'user' | 'ai'; text?: string; response?: Response};
type TrustedPayment = {id: number; name: string; phone: string; relationship: string; verification_status: 'verified'|'unverified'|'needs_review'; last_transfer_amount?: number | null; last_transfer_date?: string | null};
type DirectDraft = {draft_id: number; recipient: {id: number | null; name: string; phone: string | null}; relationship: string; relationship_evidence: string[]; amount: number; fee: number; total: number; balance_after: number; state: string};
type LearningLessonContext = {type: 'learning_lesson'; lessonId: number; title: string; concept: string};
const processLabel = 'Understanding your request…';

export function CoachPanel({user: _user}: {user: DemoUser}) {
  const location = useLocation();
  const navigate = useNavigate();
  const explainMetric = getExplainMetric(location.state);
  const learningLesson = getLearningLesson(location.state);
  const [messages, setMessages] = useState<Message[]>([]), [conversationId, setConversationId] = useState<string>(), [input, setInput] = useState(() => new URLSearchParams(location.search).get('prompt') || ''), [busy, setBusy] = useState(false), [guided, setGuided] = useState(false), [pinAction, setPinAction] = useState<Response>(), [reviewing, setReviewing] = useState<Response>(), [pinError, setPinError] = useState<string>(), [showJump, setShowJump] = useState(false), [trustedPayment, setTrustedPayment] = useState<TrustedPayment>();
  const viewport = useRef<HTMLDivElement>(null);
  const explainedLocations = useRef(new Set<string>());
  const append = (message: Message) => setMessages((items) => [...items, message]);
  useEffect(() => { const prompt = new URLSearchParams(location.search).get('prompt'); if (prompt && !messages.length) setInput(prompt); }, [location.search, messages.length]);
  useEffect(() => { const payment = (location.state as {trustedPayment?: TrustedPayment} | null)?.trustedPayment; if (payment) {setTrustedPayment(payment); navigate(location.pathname, {replace: true, state: null});} }, [location.key, location.pathname, location.state, navigate]);
  useEffect(() => { const node = viewport.current; if (node && !showJump) node.scrollTo({top: node.scrollHeight, behavior: 'smooth'}); }, [messages, busy, showJump]);
  const send = async (value = input) => {
    const text = value.trim(); if (!text || busy) return;
    setInput(''); append({id: crypto.randomUUID(), role: 'user', text}); setBusy(true);
    try { const response = await api<Response>('/assistant/message', {method: 'POST', body: JSON.stringify({conversation_id: conversationId, message: text})}); setConversationId(response.conversation_id || conversationId); append({id: crypto.randomUUID(), role: 'ai', response}); }
    catch { append({id: crypto.randomUUID(), role: 'ai', response: {type: 'error', message: 'We could not reach AI Assist. Please try again.'}}); }
    finally { setBusy(false); }
  };
  const requestExplanation = async (metric: ExplainMetricContext, language?: 'en' | 'bn') => {
    if (busy) return;
    setBusy(true);
    try { const response = await api<Response>('/assistant/message', {method: 'POST', body: JSON.stringify({conversation_id: conversationId, message: `Explain ${metric.title}`, explain_metric: metricExplanationPayload(metric, language)})}); setConversationId(response.conversation_id || conversationId); append({id: crypto.randomUUID(), role: 'ai', response}); }
    catch { append({id: crypto.randomUUID(), role: 'ai', response: {type: 'error', message: "I couldn't load the explanation right now. You can still ask me about this metric below."}}); }
    finally { setBusy(false); }
  };
  useEffect(() => {
    if (!explainMetric || explainedLocations.current.has(location.key)) return;
    explainedLocations.current.add(location.key);
    void requestExplanation(explainMetric);
  // location.key is a new navigation entry. Tracking it prevents repeat messages from re-renders and focus changes.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.key]);
  const confirm = async (response: Response) => {
    if (!response.action?.id || busy) return; setBusy(true);
    try { const next = await api<Response>(`/assistant/actions/${response.action.id}/confirm`, {method: 'POST'}); if (next.type === 'authorization_required') setPinAction({...response, action: next.action}); else append({id: crypto.randomUUID(), role: 'ai', response: next}); setReviewing(undefined); }
    catch { append({id: crypto.randomUUID(), role: 'ai', response: {type: 'error', message: 'This action could not be confirmed. Please try again.'}}); }
    finally { setBusy(false); }
  };
  const cancel = async (response: Response) => { if (!response.action?.id) return; setReviewing(undefined); try { append({id: crypto.randomUUID(), role: 'ai', response: await api<Response>(`/assistant/actions/${response.action.id}`, {method: 'DELETE'})}); } catch { append({id: crypto.randomUUID(), role: 'ai', response: {type: 'error', message: 'This action could not be cancelled.'}}); } };
  const authorize = async (pin: string) => { if (!pinAction?.action?.id) return; setBusy(true); try { const next = await api<Response>(`/assistant/actions/${pinAction.action.id}/authorize`, {method: 'POST', body: JSON.stringify({pin})}); if (next.type === 'error') { setPinError(next.message); return; } setPinAction(undefined); append({id: crypto.randomUUID(), role: 'ai', response: next}); } catch { setPinError('PIN verification failed. Please try again.'); } finally { setBusy(false); } };
  const onScroll = () => { const node = viewport.current; if (node) setShowJump(node.scrollHeight - node.scrollTop - node.clientHeight > 120); };
  return <div className={`coach-page ai-assist-page ${messages.length ? 'ai-assist-page--active' : 'ai-assist-page--empty'} ${guided ? 'ai-assist-page--guided' : ''}`}>
    <section className="assist-workspace" aria-label="AI Assist conversation">
      <button className="workspace-guided-toggle" type="button" aria-pressed={guided} onClick={() => setGuided(!guided)}><Accessibility />{guided ? 'Guided mode on' : 'Guided mode'}</button>
      <div className="conversation-viewport" ref={viewport} onScroll={onScroll} aria-live="polite">
        <div className="conversation-column">
          {explainMetric && <ExplainingContext metric={explainMetric} busy={busy} explainInBangla={() => void requestExplanation(explainMetric, 'bn')} />}
          {!messages.length && !explainMetric && (learningLesson ? <LearningContext lesson={learningLesson} /> : <Welcome ask={(prompt) => void send(prompt)} />)}
          {messages.map((message) => <MessageBlock key={message.id} message={message} review={() => setReviewing(message.response)} cancel={() => message.response && void cancel(message.response)} select={(name) => void send(`Send ${Number(message.response?.preview?.amount || 0)} taka to ${name}`)} />)}
          {busy && <Processing />}
        </div>
      </div>
      {showJump && <button className="jump-latest" onClick={() => {viewport.current?.scrollTo({top: viewport.current.scrollHeight, behavior: 'smooth'}); setShowJump(false);}}><ArrowDown />Jump to latest</button>}
      <div className="composer-area"><Composer input={input} busy={busy} setInput={setInput} submit={() => void send()} /></div>
    </section>
    {reviewing && <ConfirmationCard response={reviewing} back={() => setReviewing(undefined)} confirm={() => void confirm(reviewing)} />}
    {pinAction && <PinConfirmationModal recipient={String((pinAction.preview?.recipient as {name?: string})?.name || '')} amount={Number(pinAction.preview?.amount || 0)} total={Number(pinAction.preview?.total || pinAction.preview?.amount || 0)} onConfirm={authorize} onCancel={() => {setPinAction(undefined); void cancel(pinAction);}} error={pinError} busy={busy} />}
    {trustedPayment && <TrustedPaymentFlow contact={trustedPayment} close={() => setTrustedPayment(undefined)} />}
  </div>;
}

function TrustedPaymentFlow({contact, close}: {contact: TrustedPayment; close: () => void}) {
  const [amount, setAmount] = useState(''); const [reference, setReference] = useState(''); const [confirmedDetails, setConfirmedDetails] = useState(contact.verification_status === 'verified'); const [draft, setDraft] = useState<DirectDraft>(); const [pin, setPin] = useState(false); const [success, setSuccess] = useState(''); const [error, setError] = useState(''); const [busy, setBusy] = useState(false);
  const prepare = async (event: FormEvent) => {event.preventDefault(); setError(''); setBusy(true); try {const created=await api<DirectDraft>('/transactions/draft',{method:'POST',body:JSON.stringify({recipient_id:contact.id,recipient_name:contact.name,recipient_phone:contact.phone,amount:Number(amount),reference:reference || null,recognition_confirmed:confirmedDetails})}); setDraft(created);} catch(reason) {setError(reason instanceof Error ? reason.message : 'Could not prepare this transfer.');} finally {setBusy(false);}};
  const confirm = async () => {if (!draft) return; setError(''); setBusy(true); try {await api(`/transactions/draft/${draft.draft_id}/review`,{method:'POST'}); await api(`/transactions/draft/${draft.draft_id}/confirm`,{method:'POST'}); setPin(true);} catch(reason) {setError(reason instanceof Error ? reason.message : 'Could not confirm this transfer.');} finally {setBusy(false);}};
  const authorize = async (value:string) => {if (!draft) return; setError(''); setBusy(true); try {const result=await api<{success:boolean;message:string}>(`/transactions/draft/${draft.draft_id}/execute`,{method:'POST',body:JSON.stringify({pin:value})}); if (!result.success) {setError(result.message); return;} setPin(false); setSuccess(result.message);} catch(reason) {setError(reason instanceof Error ? reason.message : 'PIN verification failed.');} finally {setBusy(false);}};
  if (success) return <div className="confirmation-overlay"><section className="confirmation-card" role="dialog" aria-modal="true"><CheckCircle2 /><span className="eyebrow">TRANSFER COMPLETED</span><h2>Money sent to {contact.name}</h2><p>{success} Trusted People activity will now show this transfer.</p><button className="button" onClick={close}>Done</button></section></div>;
  return <><div className="confirmation-overlay"><section className="confirmation-card trusted-payment-flow" role="dialog" aria-modal="true" aria-label="Send money"><button className="icon-button trusted-payment-flow__close" onClick={close} aria-label="Close"><ArrowDown /></button>{!draft ? <form onSubmit={(event) => void prepare(event)}><span className="eyebrow">SEND MONEY</span><h2>Recognize the recipient</h2><div className="trusted-payment-flow__recipient"><span>{contact.name.split(' ').map((word) => word[0]).join('').slice(0,2)}</span><div><strong>{contact.name}</strong><small>{contact.relationship} · {contact.phone}</small><em className={contact.verification_status === 'verified' ? 'verified' : ''}>{contact.verification_status === 'verified' ? 'Verified by you' : 'Needs verification'}</em></div></div>{contact.last_transfer_amount ? <p className="draft-evidence">Last transfer: {formatBDT(contact.last_transfer_amount)} · {contact.last_transfer_date}</p> : <p className="draft-evidence">First transfer to this saved contact. Verify the recipient details carefully.</p>}{contact.verification_status !== 'verified' && <label className="recognition-check"><input type="checkbox" checked={confirmedDetails} onChange={(event) => setConfirmedDetails(event.target.checked)} />I confirm this name and phone number are correct.</label>}<label className="field"><span>Amount</span><input required min="1" type="number" inputMode="decimal" value={amount} onChange={(event) => setAmount(event.target.value)} autoFocus /></label><label className="field"><span>Reference <small>Optional</small></span><input value={reference} maxLength={140} onChange={(event) => setReference(event.target.value)} /></label>{error && <p className="form-error">{error}</p>}<div className="confirmation-card__actions"><button className="button button--secondary" type="button" onClick={close}>Cancel</button><button className="button" disabled={busy || !confirmedDetails}>{busy ? 'Preparing…' : 'Review transfer'}</button></div></form> : <><span className="eyebrow">FINAL REVIEW</span><h2>Send to {draft.recipient.name}</h2><div className="trusted-payment-flow__recipient"><span>{contact.name.split(' ').map((word) => word[0]).join('').slice(0,2)}</span><div><strong>{contact.name}</strong><small>{contact.relationship} · {contact.phone}</small><em className={contact.verification_status === 'verified' ? 'verified' : ''}>{contact.verification_status === 'verified' ? 'Verified by you' : 'Confirmed before this transfer'}</em></div></div><div className="direct-draft-values"><span>Amount <b>{formatBDT(draft.amount)}</b></span><span>Fee <b>{formatBDT(draft.fee)}</b></span><strong>Total <b>{formatBDT(draft.total)}</b></strong></div>{error && <p className="form-error">{error}</p>}<p>This is a simulated transfer. You will enter your PIN yourself before it completes.</p><div className="confirmation-card__actions"><button className="button button--secondary" onClick={() => setDraft(undefined)}>Back</button><button className="button" disabled={busy} onClick={() => void confirm()}>{busy ? 'Confirming…' : 'Confirm transfer'}</button></div></>}</section></div>{pin && draft && <PinConfirmationModal recipient={draft.recipient.name} amount={draft.amount} total={draft.total} onConfirm={authorize} onCancel={() => setPin(false)} error={error} busy={busy} />}</>;
}

function getExplainMetric(state: unknown): ExplainMetricContext | undefined {
  const metric = (state as {explainMetric?: unknown} | null)?.explainMetric;
  if (!metric || typeof metric !== 'object') return undefined;
  return isExplainMetricContext(metric as Partial<ExplainMetricContext>) ? metric as ExplainMetricContext : undefined;
}
function getLearningLesson(state: unknown): LearningLessonContext | undefined {
  const lesson = (state as {learningLesson?: unknown} | null)?.learningLesson;
  if (!lesson || typeof lesson !== 'object') return undefined;
  const value = lesson as Partial<LearningLessonContext>;
  return value.type === 'learning_lesson' && typeof value.lessonId === 'number' && typeof value.title === 'string' && typeof value.concept === 'string' ? value as LearningLessonContext : undefined;
}
function ExplainingContext({metric, busy, explainInBangla}: {metric: ExplainMetricContext; busy: boolean; explainInBangla: () => void}) { return <div className="explain-context" aria-label={`Explaining ${metric.title}`}><span>Explaining</span><strong>{metric.title} · {formatExplainMetricValue(metric)}</strong><button className="text-button" type="button" disabled={busy} onClick={explainInBangla}>বাংলায় বুঝিয়ে বলুন</button></div>; }
function LearningContext({lesson}: {lesson: LearningLessonContext}) { return <div className="explain-context" aria-label={`Asking AI about ${lesson.title}`}><span>Learning context</span><strong>{lesson.title} · {lesson.concept}</strong><p>AI Assist can explain this concept in simpler words or বাংলা. Calculations and recommendations remain based on your financial data.</p></div>; }

function Welcome({ask}: {ask: (prompt: string) => void}) { const prompts=['Why did my spending increase?','How much can I safely spend?','How long will my money last?','Help me save for something','Analyze my food spending','Show my recent transactions','Create a budget','Run a spending scenario']; return <div className="assist-welcome"><span className="assist-welcome__orb"><Sparkles /></span><h1>How can I help?</h1><p>Ask about your money, savings, or simply tell me what you want to do.</p><small>English • বাংলা • mixed</small><div className="assistant-starters" aria-label="Starter prompts">{prompts.map((prompt) => <button type="button" key={prompt} onClick={() => ask(prompt)}>{prompt}</button>)}</div><div className="welcome-examples"><span>Examples:</span> “Send 500 taka to Fuad” <i>·</i> “Help me save for a laptop”</div></div>; }
function Processing() { return <div className="assistant-block assistant-block--processing"><CoachAvatar /><div><span className="processing-label">{processLabel}</span><span className="typing" aria-label={processLabel}><i /><i /><i /></span></div></div>; }
function MessageBlock({message, review, cancel, select}: {message: Message; review: () => void; cancel: () => void; select: (name: string) => void}) { return <div className={`assistant-block assistant-block--${message.role}`}>{message.role === 'ai' && <CoachAvatar />}<div>{message.role === 'user' ? <p>{message.text}</p> : message.response && <ResponseView response={message.response} review={review} cancel={cancel} select={select} />}</div></div>; }
function ResponseView({response, review, cancel, select}: {response: Response; review: () => void; cancel: () => void; select: (name: string) => void}) {
  if (response.type === 'action_preview' && response.preview) {
    if (response.action?.name === 'send_money') return <div className="action-card-wrap"><p className="assistant-copy">{response.message}</p><ActionSteps /><TransactionDraftCard draft={{recipient_name: String((response.preview.recipient as {name?: string})?.name || ''), relationship: String(response.preview.relationship || 'Known'), amount: Number(response.preview.amount), fee: Number(response.preview.fee), total: Number(response.preview.total), balance_after: Number(response.preview.balance_after), safe_to_spend_before: Number((response.preview.safe_to_spend_before as {safe_to_spend?: number})?.safe_to_spend), safe_to_spend_after: Number(response.preview.safe_to_spend_after)}} onReview={review} onCancel={cancel} /></div>;
    return <StructuredCard response={response} review={review} cancel={cancel} label="Review update" />;
  }
  if (response.type === 'savings_plan') return <StructuredCard response={response} review={review} cancel={cancel} label="Create goal" goal />;
  if (response.type === 'selection') return <section className="selection-card"><strong>{response.message}</strong><div>{response.options?.map((option) => <button key={option.id} onClick={() => select(option.name)}><span>{option.name.slice(0, 2).toUpperCase()}</span><b>{option.name}<small>{option.relationship}</small></b><ArrowRight /></button>)}</div></section>;
  if (response.type === 'transaction_list') return <section className="insight-card"><h3>{response.message}</h3>{response.transactions?.map((item) => <div className="transaction-mini" key={item.id}><span>{item.merchant_name}<small>{item.category}</small></span><b className={item.direction === 'income' ? 'money-positive' : 'money-negative'}>{item.direction === 'income' ? '+' : '-'}{formatBDT(item.amount)}</b></div>)}</section>;
  if (response.type === 'financial_insight') return <section className="insight-card"><span className="eyebrow">CALCULATED INSIGHT</span><ReactMarkdown remarkPlugins={[remarkGfm]}>{response.message}</ReactMarkdown>{response.data && <EvidenceSummary data={response.data} />}</section>;
  if (response.type === 'success') return <section className="receipt-card"><CheckCircle2 /><div><span>COMPLETED</span><h3>{response.message}</h3>{response.result?.balance_after !== undefined && <strong>Balance {formatBDT(Number(response.result.balance_after))}</strong>}</div></section>;
  return <section className={response.type === 'error' ? 'assistant-error' : 'clarification-card'}><p>{response.message}</p></section>;
}
function evidenceValueType(key: string): ValueType {
  if (/(amount|balance|spend|income|budget|limit|saving|purchase|expense|shortfall)/i.test(key)) return 'currency';
  if (/(?:^|_)days?(?:_|$)|runway/i.test(key)) return 'days';
  if (/(?:percent|percentage|rate|utilization)/i.test(key)) return 'percentage';
  if (/(?:^|_)score(?:_|$)/i.test(key)) return 'score';
  if (/(?:date|until)$/i.test(key)) return 'date';
  return 'number';
}
function EvidenceSummary({data}: {data: Record<string, unknown>}) { const rows=Object.entries(data).filter(([, value]) => typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean').slice(0, 6); if (!rows.length) return null; return <details className="evidence-summary"><summary>Calculation details</summary><dl>{rows.map(([key,value]) => { const type = evidenceValueType(key); return <div key={key}><dt>{key.replace(/_/g,' ')}</dt><dd>{typeof value === 'number' || (typeof value === 'string' && type === 'date') ? formatValue(value, type) : String(value)}</dd></div>; })}</dl></details>; }
function ActionSteps() { return <div className="action-steps"><span>✓ Understood</span><span>✓ Calculated impact</span><span>○ Waiting for review</span></div>; }
type DisplayField = {key: string; label: string; value: string | number | boolean; value_type: ValueType};

function isDisplayField(value: unknown): value is DisplayField {
  if (!value || typeof value !== 'object') return false;
  const field = value as Partial<DisplayField>;
  return typeof field.key === 'string' && typeof field.label === 'string' && typeof field.value_type === 'string' && ['currency', 'months', 'days', 'percentage', 'date', 'number', 'score', 'text'].includes(field.value_type);
}

function feasibilityCopy(status: unknown): string {
  if (status === 'on_track') return 'This goal looks achievable within your selected timeline.';
  if (status === 'stretch') return 'This goal may require tighter spending.';
  if (status === 'timeline_too_short') return 'Your selected timeline may be too aggressive.';
  return 'Add your financial information to estimate affordability.';
}

function StructuredCard({response, review, cancel, label, goal = false}: {response: Response; review: () => void; cancel: () => void; label: string; goal?: boolean}) {
  const preview = response.preview || {};
  const fields = Array.isArray(preview.display_fields) ? preview.display_fields.filter(isDisplayField) : [];
  const goalName = String(preview.goal_name || 'Savings');
  const required = Number(preview.required_monthly_contribution || 0);
  const affordable = Number(preview.affordable_monthly_contribution || 0);
  const capacityUsed = affordable > 0 ? Math.min(100, Math.round(required / affordable * 100)) : 100;
  const genericFields: DisplayField[] = Object.entries(preview)
    .filter(([key, value]) => key !== 'display_fields' && (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean'))
    .slice(0, 5)
    .map(([key, value]) => ({key, label: key.replace(/_/g, ' '), value: value as string | number | boolean, value_type: key.includes('amount') || key.includes('limit') ? 'currency' : 'text'}));
  const visibleFields = goal ? fields : genericFields;
  return <section className={`structured-action-card ${goal ? 'structured-action-card--goal' : ''}`}>
    <div className="structured-action-card__head"><span>{goal ? 'SAVINGS PLAN' : 'ACTION PREVIEW'}</span><b>{goal ? `${goalName} goal` : 'Budget update'}</b></div>
    <p>{response.message}</p>
    <div className="structured-metrics">{visibleFields.map((field) => <span key={field.key}><small>{field.label}</small><strong>{formatValue(field.value, field.value_type)}{field.key.endsWith('_contribution') ? '/month' : ''}</strong></span>)}</div>
    {goal && <div className="goal-progress" aria-label="Goal feasibility">
      <i style={{width: `${capacityUsed}%`}} />
      <small>{affordable > 0 ? `Monthly capacity used: ${capacityUsed}% · ${feasibilityCopy(preview.feasibility_status)}` : feasibilityCopy(preview.feasibility_status)}</small>
    </div>}
    <div className="structured-action-card__actions"><button className="button button--secondary" onClick={cancel}>Cancel</button><button className="button" onClick={review}>{label} <ArrowRight /></button></div>
  </section>;
}
function ConfirmationCard({response, back, confirm}: {response: Response; back: () => void; confirm: () => void}) { const p=response.preview || {}; const recipient=(p.recipient as {name?: string})?.name; return <div className="confirmation-overlay"><section className="confirmation-card" role="dialog" aria-modal="true" aria-labelledby="confirm-action-title"><LockKeyhole /><span className="eyebrow">FINAL REVIEW</span><h2 id="confirm-action-title">Confirm {response.action?.name === 'send_money' ? 'transfer' : 'action'}</h2><p>You are about to {response.action?.name === 'send_money' ? `send ${formatBDT(Number(p.amount))} to ${recipient}. Total deduction: ${formatBDT(Number(p.total))}.` : response.message}</p><div className="confirmation-card__actions"><button className="button button--secondary" onClick={back}>Back</button><button className="button" onClick={confirm}>Confirm {response.action?.name === 'send_money' ? 'transfer' : 'action'}</button></div></section></div>; }
function Composer({input, busy, setInput, submit}: {input: string; busy: boolean; setInput: (value: string) => void; submit: () => void}) {
  const textarea = useRef<HTMLTextAreaElement>(null);
  useEffect(() => { const node = textarea.current; if (!node) return; node.style.height = 'auto'; node.style.height = `${Math.min(node.scrollHeight, 156)}px`; }, [input]);
  return <form className="assist-composer" onSubmit={(event: FormEvent) => {event.preventDefault(); submit();}}><label className="sr-only" htmlFor="coach-input">Tell AI Assist what you want to do</label><textarea ref={textarea} id="coach-input" rows={1} maxLength={500} value={input} onChange={(event) => setInput(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); submit(); } }} placeholder="Ask anything about your money…" /><div><small>English • বাংলা • mixed</small><button type="submit" disabled={!input.trim() || busy} aria-label={busy ? 'Preparing your request' : 'Send message'}>{busy ? <span className="composer-spinner" /> : <ArrowUp size={19} />}</button></div></form>;
}
