import { Gift } from 'lucide-react';
import { Sheet, Tag } from '../ui';
import { formatBDT } from '../../format';
import type { OfferDetail } from '../../types';

interface Props {
  offer: OfferDetail | null;
  loading: boolean;
  saving: boolean;
  personalized: boolean;
  onClose: () => void;
  onSave: () => void;
  onLearnMore: (lessonId: number) => void;
}

const FIT_MESSAGES: Record<string, { headline: string; body: string } | null> = {
  good_fit: {
    headline: 'This looks like a good match for your spending.',
    body: 'You typically spend enough to qualify for this offer.',
  },
  conditional_fit: {
    headline: 'Conditional fit — check the details.',
    body: 'Your typical purchase is below the minimum spend. The offer may not save you money unless you already planned a larger purchase.',
  },
  not_useful: {
    headline: 'This offer may not be useful right now.',
    body: 'Based on your recent spending, this offer may not directly benefit your spending patterns.',
  },
};

export function OfferDetailSheet({ offer, loading, saving, personalized, onClose, onSave, onLearnMore }: Props) {
  if (!offer) return null;

  const fit = FIT_MESSAGES[offer.fit_status ?? ''];
  const discount = offer.discount_percent
    ? `${offer.discount_percent}% off`
    : offer.discount_fixed
    ? `৳${offer.discount_fixed} cashback`
    : 'Special offer';

  const potentialAtMin = offer.min_spend && offer.discount_percent
    ? Math.round(offer.min_spend * (offer.discount_percent / 100))
    : offer.discount_fixed ?? null;

  return (
    <Sheet
      title={offer.title}
      close={onClose}
      className="offer-detail-sheet"
    >
      {loading && (
        <div className="skeleton" style={{ height: 200 }} />
      )}

      {!loading && offer && (
        <div className="offer-detail">
          {/* Header badge */}
          <div className="offer-detail__header">
            <Tag tone="positive">{discount}</Tag>
          {offer.state === 'expired' ? <Tag tone="neutral">Expired</Tag> : offer.fit_status && (
              <Tag
                tone={
                  offer.fit_status === 'good_fit' ? 'positive'
                  : offer.fit_status === 'conditional_fit' ? 'warning'
                  : 'neutral'
                }
              >
                {offer.fit_status === 'good_fit' ? 'Good fit' :
                 offer.fit_status === 'conditional_fit' ? 'Conditional fit' : 'Not useful'}
              </Tag>
            )}
          </div>

          {/* Fit status message */}
          {personalized && fit && (
            <div className={`offer-detail__fit-msg offer-detail__fit-msg--${offer.fit_status}`}>
              <strong>{fit.headline}</strong>
              <p>{fit.body}</p>
            </div>
          )}

          {/* Terms */}
          <section className="offer-detail__section">
            <h3>Offer details</h3>
            <p className="offer-detail__terms">{offer.terms}</p>
            {offer.terms_bn && (
              <p className="offer-detail__terms offer-detail__terms--bn quiet">{offer.terms_bn}</p>
            )}
          </section>

          {personalized && offer.why_relevant && <section className="offer-detail__section offer-detail__relevance">
            <h3>Why it matches you</h3>
            <p>{offer.why_relevant}</p>
          </section>}

          {/* Spending analysis */}
          {personalized && <section className="offer-detail__section">
            <h3>Your typical spending</h3>
            <div className="offer-detail__spending">
              <div className="offer-detail__spending-row">
                <span className="quiet">Your typical {offer.category.toLowerCase()} purchase</span>
                <strong>{offer.typical_purchase ? formatBDT(offer.typical_purchase) : '—'}</strong>
              </div>
              {offer.min_spend && (
                <div className="offer-detail__spending-row">
                  <span className="quiet">Minimum spend to qualify</span>
                  <strong>{formatBDT(offer.min_spend)}</strong>
                </div>
              )}
              {offer.fit_status === 'conditional_fit' && potentialAtMin && (
                <div className="offer-detail__spending-row offer-detail__spending-row--warning">
                  <span className="quiet">Estimated saving at minimum spend</span>
                  <strong>~{formatBDT(potentialAtMin)}</strong>
                </div>
              )}
              {offer.fit_status === 'good_fit' && offer.potential_saving && (
                <div className="offer-detail__spending-row offer-detail__spending-row--positive">
                  <span className="quiet">Potential saving</span>
                  <strong className="money-positive">~{formatBDT(offer.potential_saving)}</strong>
                </div>
              )}
              {offer.max_discount && (
                <div className="offer-detail__spending-row">
                  <span className="quiet">Maximum discount</span>
                  <strong>{formatBDT(offer.max_discount)}</strong>
                </div>
              )}
            </div>
          </section>}

          {/* Guardrail: explicit warning for conditional_fit */}
          {personalized && offer.fit_status === 'conditional_fit' && (
            <div className="offer-detail__guardrail">
              <strong>Important:</strong> Do not spend more just to unlock this offer.
              Only use it if you were already planning a purchase at or above the minimum spend.
            </div>
          )}

          {/* Expiry */}
          {offer.expiry_date && (
            <section className="offer-detail__section">
              <h3>Valid until</h3>
              <p>{new Date(offer.expiry_date).toLocaleDateString('en-BD', {
                day: 'numeric', month: 'long', year: 'numeric'
              })}</p>
            </section>
          )}

          {/* Learn link */}
          {offer.learning_lesson_id && (
            <button
              className="button button--secondary button--full"
              style={{ marginTop: 8 }}
              onClick={() => onLearnMore(offer.learning_lesson_id!)}
            >
              Before using this offer: learn why discounts don't always mean spending less
            </button>
          )}

          {/* Actions */}
          <div className="offer-detail__actions">
            <button
              className="button"
              onClick={onSave}
              disabled={saving}
            >
              {offer.is_saved ? 'Saved ✓' : saving ? 'Saving…' : 'Save offer'}
            </button>
            {offer.learning_lesson_id && (
              <button
                className="button button--ghost"
                onClick={() => onLearnMore(offer.learning_lesson_id!)}
              >
                Learn more
              </button>
            )}
          </div>

          <p className="offer-detail__disclaimer quiet">
            This is a concept offer for the demo. Actual offers may differ.
          </p>
        </div>
      )}
    </Sheet>
  );
}
