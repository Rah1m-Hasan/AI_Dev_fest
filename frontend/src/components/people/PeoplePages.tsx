import {FormEvent, useEffect, useState} from 'react';
import {Check, HandHeart, Plus, Send, ShieldCheck, UserPlus, UsersRound, X} from 'lucide-react';
import {Link} from 'react-router-dom';
import {api} from '../../api/client';
import {EmptyState, ErrorState, LoadingPage, PageHeader, Tag, TrustBadge} from '../ui';

type Contact = {id: number; name: string; phone_number: string; relationship: string; nickname?: string; is_trusted: boolean; trust_label?: 'Trusted' | 'Known' | 'New' | 'Needs verification'; last_transfer_amount?: number | null; last_transfer_date?: string | null};
type Helper = {id: number; helper_name: string; relationship: string; phone: string; can_view_pending_transaction: boolean; can_receive_alerts: boolean; can_view_balance: boolean; can_view_history: boolean; can_initiate: boolean};

function initials(name: string) { return name.split(' ').map((word) => word[0]).join('').slice(0, 2); }
function maskedPhone(phone: string) { return phone.length > 4 ? `${phone.slice(0, 2)}XXXXXXXX${phone.slice(-1)}` : 'Hidden number'; }

export function ContactsPage() {
  const [contacts, setContacts] = useState<Contact[]>();
  const [error, setError] = useState('');
  const [adding, setAdding] = useState(false);
  const [notice, setNotice] = useState('');
  const load = () => { setError(''); void api<{items: Contact[]}>('/trusted-contacts').then((data) => setContacts(data.items)).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : 'Unable to load contacts.')); };
  useEffect(load, []);
  const remove = async (id: number) => { await api(`/trusted-contacts/${id}`, {method: 'DELETE'}); setNotice('Contact removed.'); load(); };
  if (error) return <ErrorState message={error} retry={load} />;
  if (!contacts) return <LoadingPage label="Loading your people" />;
  return <div className="page people-page">
    <PageHeader eyebrow="People, not numbers" title="Your trusted circle" description="Recognize the people behind a payment before you send. Trust labels are based on your saved contacts." action={<button className="button" onClick={() => setAdding(true)}><UserPlus />Add person</button>} />
    <section className="people-hero"><UsersRound /><div><span className="eyebrow">SAFER PAYMENTS</span><h2>People make better payment decisions.</h2><p>AI Assist surfaces relationship and trust context before every transfer.</p></div><TrustBadge>You always confirm</TrustBadge></section>
    {notice && <div className="toast" role="status"><Check />{notice}</div>}
    {contacts.length ? <div className="contacts-grid">{contacts.map((contact) => <article className="contact-card" key={contact.id}><div className="contact-card__top"><span className="contact-avatar">{initials(contact.name)}</span><Tag tone={contact.trust_label === 'Trusted' ? 'positive' : 'warning'}>{contact.trust_label || (contact.is_trusted ? 'Trusted' : 'Known')}</Tag></div><h2>{contact.name}</h2><p className="contact-card__relationship">{contact.relationship} · {maskedPhone(contact.phone_number)}</p><div className="contact-card__context"><ShieldCheck /><span>{contact.last_transfer_amount ? `Last transfer: ৳${contact.last_transfer_amount.toLocaleString()} · ${contact.last_transfer_date || 'recently'}` : 'Saved contact — verify details before your first transfer'}</span></div><div className="contact-card__actions"><Link className="button" to="/coach/assistant"><Send />Send</Link><Link className="button button--secondary" to="/coach/assistant">Request</Link><button className="text-button" onClick={() => void remove(contact.id)}>Remove</button></div></article>)}</div> : <EmptyState title="No people saved yet" description="Add someone you trust to make future payments easier to recognize." />}
    {adding && <ContactForm close={() => setAdding(false)} done={() => {setAdding(false); setNotice('Person added to your trusted circle.'); load();}} />}
  </div>;
}

function ContactForm({close, done}: {close: () => void; done: () => void}) {
  const [name, setName] = useState(''); const [phone, setPhone] = useState(''); const [relationship, setRelationship] = useState('Family'); const [error, setError] = useState(''); const [saving, setSaving] = useState(false);
  const submit = async (event: FormEvent) => { event.preventDefault(); setSaving(true); setError(''); try { await api('/trusted-contacts', {method: 'POST', body: JSON.stringify({name, phone_number: phone, relationship, is_trusted: true})}); done(); } catch (reason) {setError(reason instanceof Error ? reason.message : 'Could not add this person.');} finally {setSaving(false);} };
  return <div className="backdrop" onMouseDown={close}><form className="people-form" onSubmit={(event) => void submit(event)} onMouseDown={(event) => event.stopPropagation()}><div className="sheet__header"><div><span className="eyebrow">Trusted circle</span><h2>Add a person</h2></div><button className="icon-button" onClick={close} type="button" aria-label="Close"><X /></button></div><p>Saved people are easier to verify before you transfer money.</p><label className="field"><span>Name</span><input required value={name} onChange={(event) => setName(event.target.value)} /></label><label className="field"><span>Mobile number</span><input required inputMode="tel" value={phone} onChange={(event) => setPhone(event.target.value)} /></label><label className="field"><span>Relationship</span><input required value={relationship} onChange={(event) => setRelationship(event.target.value)} /></label>{error && <p className="form-error">{error}</p>}<div className="wizard-actions"><button className="button button--ghost" type="button" onClick={close}>Cancel</button><button className="button" disabled={saving}>{saving ? 'Saving…' : 'Save person'}</button></div></form></div>;
}

export function TrustedHelperPage() {
  const [helpers, setHelpers] = useState<Helper[]>(); const [error, setError] = useState(''); const [adding, setAdding] = useState(false); const [notice, setNotice] = useState('');
  const load = () => {setError(''); void api<{items: Helper[]}>('/trusted-helpers').then((data) => setHelpers(data.items)).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : 'Unable to load trusted helpers.'));};
  useEffect(load, []);
  const remove = async (id: number) => { await api(`/trusted-helpers/${id}`, {method: 'DELETE'}); setNotice('Helper removed.'); load(); };
  if (error) return <ErrorState message={error} retry={load} />;
  if (!helpers) return <LoadingPage label="Loading trusted helper settings" />;
  return <div className="page helper-page"><PageHeader eyebrow="Trusted Helper Mode" title="Support, with clear boundaries" description="Choose people who can help explain and navigate. Your money and PIN remain under your control." action={<button className="button" onClick={() => setAdding(true)}><Plus />Add helper</button>} />
    <section className="helper-boundaries"><HandHeart /><div><h2>Helpers can guide. They cannot take over.</h2><div><span><Check />Help understand options</span><span><Check />Guide through screens</span><span><X />See your PIN</span><span><X />Confirm payments or send money for you</span></div></div></section>
    {notice && <div className="toast" role="status"><Check />{notice}</div>}
    {helpers.length ? <div className="helper-list">{helpers.map((helper) => <article key={helper.id}><span className="contact-avatar">{initials(helper.helper_name)}</span><div><h2>{helper.helper_name}</h2><p>{helper.relationship} · {helper.phone}</p><div className="permission-pills">{helper.can_view_pending_transaction && <Tag tone="ai">Can view pending transfer</Tag>}{helper.can_receive_alerts && <Tag tone="positive">Alerts</Tag>}{helper.can_view_balance && <Tag>Balance access</Tag>}{helper.can_view_history && <Tag>History access</Tag>}</div></div><button className="text-button" onClick={() => void remove(helper.id)}>Remove</button></article>)}</div> : <EmptyState title="No trusted helper yet" description="Add a family member or friend when you want guidance, never control." />}
    {adding && <HelperForm close={() => setAdding(false)} done={() => {setAdding(false); setNotice('Trusted Helper added with the selected permissions.'); load();}} />}
  </div>;
}

function HelperForm({close, done}: {close: () => void; done: () => void}) {
  const [name, setName] = useState(''); const [phone, setPhone] = useState(''); const [relationship, setRelationship] = useState('Family'); const [pending, setPending] = useState(true); const [alerts, setAlerts] = useState(true); const [error, setError] = useState(''); const [saving, setSaving] = useState(false);
  const submit = async (event: FormEvent) => {event.preventDefault(); setSaving(true); setError(''); try {await api('/trusted-helpers', {method: 'POST', body: JSON.stringify({helper_name: name, phone, relationship, can_view_pending_transaction: pending, can_receive_alerts: alerts, can_view_balance: false, can_view_history: false, can_initiate: false})}); done();} catch (reason) {setError(reason instanceof Error ? reason.message : 'Could not add this helper.');} finally {setSaving(false);}};
  return <div className="backdrop" onMouseDown={close}><form className="people-form" onSubmit={(event) => void submit(event)} onMouseDown={(event) => event.stopPropagation()}><div className="sheet__header"><div><span className="eyebrow">Permission setup</span><h2>Add a trusted helper</h2></div><button className="icon-button" onClick={close} type="button" aria-label="Close"><X /></button></div><label className="field"><span>Name</span><input required value={name} onChange={(event) => setName(event.target.value)} /></label><label className="field"><span>Mobile number</span><input required value={phone} onChange={(event) => setPhone(event.target.value)} /></label><label className="field"><span>Relationship</span><input required value={relationship} onChange={(event) => setRelationship(event.target.value)} /></label><label className="permission-toggle"><input type="checkbox" checked={pending} onChange={(event) => setPending(event.target.checked)} />Can view a transfer waiting for your confirmation</label><label className="permission-toggle"><input type="checkbox" checked={alerts} onChange={(event) => setAlerts(event.target.checked)} />Can receive alerts you choose</label><div className="permission-lock"><ShieldCheck />Helpers can never view your PIN, bypass confirmation, or send money silently.</div>{error && <p className="form-error">{error}</p>}<div className="wizard-actions"><button className="button button--ghost" type="button" onClick={close}>Cancel</button><button className="button" disabled={saving}>{saving ? 'Saving…' : 'Save helper'}</button></div></form></div>;
}
