import { useEffect, useRef, useState } from 'react';
import { X, Lock, AlertCircle, ShieldCheck } from 'lucide-react';
import {formatBDT} from '../../format';

interface PinConfirmationModalProps {
  onConfirm: (pin: string) => void;
  onCancel: () => void;
  error?: string | null;
  recipient: string;
  amount: number;
  total: number;
  busy?: boolean;
}

export function PinConfirmationModal({ onConfirm, onCancel, error, recipient, amount, total, busy = false }: PinConfirmationModalProps) {
  const [pin, setPin] = useState('');
  const [showError, setShowError] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !busy) onCancel();
    };
    window.addEventListener('keydown', closeOnEscape);
    return () => window.removeEventListener('keydown', closeOnEscape);
  }, [busy, onCancel]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (pin.length === 4) {
      onConfirm(pin);
    } else {
      setShowError(true);
    }
  };

  const handlePinChange = (value: string) => {
    const cleaned = value.replace(/\D/g, '').slice(0, 4);
    setPin(cleaned);
    setShowError(false);
  };

  return (
    <div className="pin-modal-backdrop" role="presentation" onMouseDown={onCancel}>
      <div className="pin-modal" role="dialog" aria-modal="true" aria-labelledby="pin-modal-title" onMouseDown={(event) => event.stopPropagation()}>
        <button className="pin-modal__close" onClick={onCancel} aria-label="Cancel">
          <X size={20} />
        </button>

        <div className="pin-modal__header">
          <div className="pin-modal__icon">
            <Lock size={24} />
          </div>
          <h2 id="pin-modal-title">Confirm your transfer</h2>
          <p>Review the details, then enter your PIN.</p>
        </div>

        <div className="pin-transfer-summary"><span><small>To</small><strong>{recipient}</strong></span><span><small>Amount</small><strong>{formatBDT(amount)}</strong></span><span className="pin-transfer-summary__total"><small>Total to pay</small><strong>{formatBDT(total)}</strong></span></div>

        <div className="pin-modal__demo-note">
          <AlertCircle size={14} />
          <span>Demo PIN: <strong>1234</strong></span>
        </div>

        <form onSubmit={handleSubmit} className="pin-modal__form">
          <div className="pin-input-group">
            <input
              ref={inputRef}
              aria-label="Four digit demo PIN"
              type="password"
              inputMode="numeric"
              pattern="[0-9]*"
              maxLength={4}
              value={pin}
              onChange={(e) => handlePinChange(e.target.value)}
              placeholder="••••"
              className={`pin-input ${showError || error ? 'pin-input--error' : ''}`}
            />
          </div>

          {(showError || error) && (
            <p className="pin-modal__error">
              {error || 'Please enter a 4-digit PIN'}
            </p>
          )}

          <div className="pin-modal__actions">
            <button type="button" className="button button--secondary pin-modal__cancel" onClick={onCancel}>
              Cancel
            </button>
            <button
              type="submit"
              className="button pin-modal__confirm"
              disabled={pin.length !== 4 || busy}
            >
              {busy ? 'Confirming…' : 'Confirm transfer'}
            </button>
          </div>
        </form>

        <p className="pin-modal__disclaimer">
          <ShieldCheck size={13} /> Demo transaction — no real money moves. Your confirmation is still required.
        </p>
      </div>
    </div>
  );
}
