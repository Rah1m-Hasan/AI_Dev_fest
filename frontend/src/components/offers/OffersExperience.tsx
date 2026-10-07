import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Gift, Info } from 'lucide-react';
import { EmptyState, ErrorState, LoadingPage, PageHeader } from '../ui';
import { offersAPI } from '../../api/client';
import type { OfferCard, OfferDetail, OffersResponse } from '../../types';
import { OfferCardComponent } from './OfferCard';
import { OfferDetailSheet } from './OfferDetailSheet';
import { CategoryTabs } from '../ui/CategoryTabs';

type OfferView = 'active' | 'saved' | 'used' | 'expired';
const VIEW_LABELS: Record<OfferView, string> = { active: 'Active', saved: 'Saved', used: 'Used', expired: 'Expired' };

export function OffersExperience() {
  const navigate = useNavigate();
  const [data, setData] = useState<OffersResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState('For You');
  const [view, setView] = useState<OfferView>('active');
  const [personalized, setPersonalized] = useState(true);
  const [selectedOffer, setSelectedOffer] = useState<OfferCard | null>(null);
  const [detail, setDetail] = useState<OfferDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [saving, setSaving] = useState<number | null>(null);

  const load = async (category = activeTab, nextView = view) => {
    const response = await offersAPI.list(category !== 'For You' ? category : undefined, nextView);
    setData(response); setPersonalized(response.preferences.personalized_offers_enabled);
    return response;
  };

  useEffect(() => { void load().catch(() => setError('Could not load relevant offers.')); }, [activeTab, view]);

  const handleToggle = async (value: boolean) => {
    setPersonalized(value);
    try { await offersAPI.updatePreferences(value); await load(); }
    catch { setError('Could not update your offer preference.'); }
  };

  const handleOfferClick = async (offer: OfferCard) => {
    setSelectedOffer(offer); setDetail(null); setDetailLoading(true);
    try { setDetail(await offersAPI.detail(offer.id)); }
    catch { setError('Could not load this offer.'); }
    finally { setDetailLoading(false); }
  };

  const handleSave = async (offerId: number) => {
    setSaving(offerId);
    const offer = data?.offers.find((item) => item.id === offerId);
    try {
      if (offer?.is_saved) await offersAPI.unsave(offerId); else await offersAPI.save(offerId);
      await load();
      if (detail?.id === offerId) setDetail(await offersAPI.detail(offerId));
    } catch { setError('Could not update saved offers.'); }
    finally { setSaving(null); }
  };

  if (error) return <ErrorState message={error} retry={() => { setError(null); void load().catch(() => setError('Could not load relevant offers.')); }} />;
  if (!data) return <LoadingPage label="Finding relevant offers…" />;

  const categories = ['For You', ...data.available_categories];
  const detailOffer = detail || (selectedOffer ? { ...selectedOffer, why_relevant: selectedOffer.why_relevant ?? null } : null);

  return <div className="page offers-page">
    <PageHeader
      title="Offers"
      description="Savings opportunities that match spending you already make."
      action={<div className="offers-toggle"><label className="switch"><input type="checkbox" checked={personalized} onChange={(event) => void handleToggle(event.target.checked)} /><span /><b>Personalized offers</b></label><small><Info size={13} />{personalized ? 'Uses your spending categories to rank relevant offers.' : 'General offers — your activity is not used for ranking.'}</small></div>}
    />

    <div className="offers-filter-row">
      <CategoryTabs tabs={categories} active={activeTab} onChange={setActiveTab} />
      <div className="offer-view-tabs" aria-label="Offer state">
        {(Object.keys(VIEW_LABELS) as OfferView[]).map((item) => <button key={item} className={view === item ? 'active' : ''} onClick={() => setView(item)}>{VIEW_LABELS[item]}</button>)}
      </div>
    </div>

    <div className="offers-section-heading"><div><span className="eyebrow">{personalized ? 'Recommended for you' : 'General offers'}</span><h2>{view === 'saved' ? 'Saved offers' : view === 'expired' ? 'Expired offers' : view === 'used' ? 'Used offers' : 'Offers to consider'}</h2></div><span className="offers-count">{data.offers.length} available</span></div>

    {data.offers.length ? <div className="offer-grid">{data.offers.map((offer) => <OfferCardComponent key={offer.id} offer={offer} personalized={personalized} onClick={() => void handleOfferClick(offer)} onSave={() => void handleSave(offer.id)} saving={saving === offer.id} />)}</div> : view === 'used' ? <EmptyState title="No offer usage recorded" description="Viewing or saving an offer never counts as redemption in this demo." /> : <EmptyState title={view === 'saved' ? 'No saved offers yet' : 'No relevant offers right now'} description={view === 'saved' ? 'Save an offer to find it here later.' : "We won't recommend spending just to use an offer."} />}

    {selectedOffer && <OfferDetailSheet offer={detailOffer} loading={detailLoading} saving={saving !== null} personalized={personalized} onClose={() => { setSelectedOffer(null); setDetail(null); }} onSave={() => detailOffer && void handleSave(detailOffer.id)} onLearnMore={(lessonId) => { navigate(`/coach/learn?lesson=${lessonId}`); }} />}
  </div>;
}
