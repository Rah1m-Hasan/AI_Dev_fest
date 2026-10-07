import { Bookmark, BookmarkCheck, ReceiptText, ShoppingBasket, Smartphone, Tag as TagIcon, TrainFront } from 'lucide-react';
import { Tag } from '../ui';
import { formatBDT } from '../../format';
import type { OfferCard } from '../../types';

interface Props {
  offer: OfferCard;
  personalized: boolean;
  onClick: () => void;
  onSave: () => void;
  saving: boolean;
}

const FIT_LABELS: Record<string, { label: string; tone: 'positive' | 'warning' | 'neutral' }> = {
  good_fit: { label: 'Good fit', tone: 'positive' },
  conditional_fit: { label: 'Conditional fit', tone: 'warning' },
  not_useful: { label: 'Not currently useful', tone: 'neutral' },
};
const ICONS: Record<string, typeof ShoppingBasket> = { Groceries: ShoppingBasket, Bills: ReceiptText, Recharge: Smartphone, Transport: TrainFront, Shopping: TagIcon, Entertainment: TagIcon };

export function OfferCardComponent({ offer, personalized, onClick, onSave, saving }: Props) {
  const fit = offer.fit_status ? FIT_LABELS[offer.fit_status] : null;
  const Icon = ICONS[offer.category] || TagIcon;
  const discount = offer.discount_percent ? `${offer.discount_percent}% off` : offer.discount_fixed ? `${formatBDT(offer.discount_fixed)} off` : 'Special offer';
  const expired = offer.state === 'expired';

  return <article className={`card offer-card${expired ? ' offer-card--expired' : ''}`} onClick={onClick}>
    <div className="offer-card__header">
      <span className="offer-card__category-icon"><Icon size={19} /></span>
      <div className="offer-card__header-right">
        {expired ? <Tag tone="neutral">Expired</Tag> : fit && <Tag tone={fit.tone}>{fit.label}</Tag>}
        <button className="offer-card__save" onClick={(event) => { event.stopPropagation(); onSave(); }} disabled={saving} aria-label={offer.is_saved ? 'Unsave offer' : 'Save offer'}>{offer.is_saved ? <BookmarkCheck size={18} /> : <Bookmark size={18} />}</button>
      </div>
    </div>
    <div className="offer-card__category-row"><span>{offer.category}</span>{personalized && offer.why_relevant && <span>Relevant</span>}</div>
    <h3 className="offer-card__title">{offer.title}</h3>
    <div className="offer-card__offer-line"><strong>{discount}</strong>{offer.min_spend && <span>Min spend {formatBDT(offer.min_spend)}</span>}</div>

    {personalized && offer.fit_status === 'conditional_fit' && <p className="offer-card__fit-warning">Your typical purchase is below the {formatBDT(offer.min_spend || 0)} minimum. This may not save you money unless you already planned a larger purchase.</p>}

    {personalized && <div className="offer-card__metrics">
      <div className="offer-card__metric"><span>Your typical purchase</span><strong>{offer.typical_purchase ? formatBDT(offer.typical_purchase) : 'No recent match'}</strong></div>
      {offer.potential_saving && <div className="offer-card__metric offer-card__metric--saving"><span>{offer.fit_status === 'conditional_fit' ? 'At minimum spend' : 'Estimated saving'}</span><strong>~{formatBDT(offer.potential_saving)}</strong></div>}
    </div>}

    <div className="offer-card__why">{personalized && offer.why_relevant ? <><b>Why this is relevant</b><span>{offer.why_relevant}</span></> : <span>General offer — review the terms before you decide.</span>}</div>
    <div className="offer-card__footer"><button className="text-button" onClick={(event) => { event.stopPropagation(); onClick(); }}>View offer <span aria-hidden="true">→</span></button><button className="text-button" onClick={(event) => { event.stopPropagation(); onSave(); }} disabled={saving}>{offer.is_saved ? 'Saved' : 'Save'}</button></div>
  </article>;
}
