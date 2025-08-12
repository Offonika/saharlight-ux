import { useEffect, useRef } from 'react';

interface SheetProps {
  open: boolean;
  onClose: () => void;
  side?: 'top' | 'bottom' | 'left' | 'right';
  children: React.ReactNode;
}

const Sheet = ({ open, onClose, side = 'bottom', children }: SheetProps) => {
  const overlayRef = useRef<HTMLDivElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!open) return;

    const selector =
      'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])';
    const focusable = panelRef.current?.querySelectorAll<HTMLElement>(selector);
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

    triggerRef.current = document.activeElement as HTMLElement;
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    document.addEventListener('keydown', handleKeyDown);
    (first || panelRef.current)?.focus();

    return () => {
      document.body.style.overflow = prevOverflow;
      document.removeEventListener('keydown', handleKeyDown);
      triggerRef.current?.focus();
    };
  }, [open, onClose]);

  const handleBackdrop = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === overlayRef.current) {
      onClose();
    }
  };

  if (!open) return null;

  const position =
    side === 'top'
      ? 'top-0 left-0 w-full'
      : side === 'left'
      ? 'left-0 top-0 h-full w-64'
      : side === 'right'
      ? 'right-0 top-0 h-full w-64'
      : 'bottom-0 left-0 w-full';

  return (
    <div
      ref={overlayRef}
      onMouseDown={handleBackdrop}
      className="fixed inset-0 z-50 bg-overlay"
    >
      <div
        ref={panelRef}
        tabIndex={-1}
        onMouseDown={(e) => e.stopPropagation()}
        className={`absolute bg-card shadow-[var(--shadow-soft)] outline-none ${position}`}
      >
        {children}
      </div>
    </div>
  );
};

export default Sheet;

