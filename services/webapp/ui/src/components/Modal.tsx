import { useEffect, useRef, type ReactNode } from 'react';
import { Button } from '@/components/ui/button';

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  footer?: ReactNode;
  children: ReactNode;
}

const Modal = ({ open, onClose, title, footer, children }: ModalProps) => {
  const overlayRef = useRef<HTMLDivElement>(null);
  const modalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;

    const focusableSelectors =
      'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])';
    const focusable = modalRef.current?.querySelectorAll<HTMLElement>(focusableSelectors);
    const first = focusable?.[0];
    const last = focusable?.[focusable.length - 1];

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      } else if (e.key === 'Tab' && focusable && focusable.length) {
        if (e.shiftKey) {
          if (document.activeElement === first) {
            e.preventDefault();
            last?.focus();
          }
        } else if (document.activeElement === last) {
          e.preventDefault();
          first?.focus();
        }
      }
    };

    const root = document.documentElement;
    const previousOverflow = root.style.overflow;

    document.addEventListener('keydown', handleKeyDown);
    root.style.overflow = 'hidden';
    (first || modalRef.current)?.focus();

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      root.style.overflow = previousOverflow;
    };
  }, [open, onClose]);

  const handleOverlayClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === overlayRef.current) {
      onClose();
    }
  };

  if (!open) {
    return null;
  }

  return (
    <div
      ref={overlayRef}
      onMouseDown={handleOverlayClick}
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center bg-overlay"
    >
      <div ref={modalRef} className="modal-card">
        <div className="flex items-center justify-between p-4 border-b border-border">
          {title && <h2 className="text-lg font-semibold">{title}</h2>}
          <Button
            onClick={onClose}
            variant="ghost"
            size="icon"
            aria-label="Close"
          >
            ×
          </Button>
        </div>
        <div className="p-4">{children}</div>
        {footer && <div className="p-4 border-t border-border">{footer}</div>}
      </div>
    </div>
  );
};

export default Modal;

