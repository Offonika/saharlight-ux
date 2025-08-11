import { useEffect, useRef } from 'react';
import {
  Sheet as SheetPrimitive,
  SheetContent,
} from '@/components/ui/sheet';

interface SheetProps {
  open: boolean;
  onClose: () => void;
  side?: 'top' | 'bottom' | 'left' | 'right';
  children: React.ReactNode;
}

const Sheet = ({ open, onClose, side = 'right', children }: SheetProps) => {
  const contentRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!open) return;

    const previousOverflow = document.body.style.overflow;
    const focusableSelector =
      'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])';
    const firstFocusable = contentRef.current?.querySelector<HTMLElement>(
      focusableSelector,
    );
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    triggerRef.current = document.activeElement as HTMLElement;
    document.body.style.overflow = 'hidden';
    document.addEventListener('keydown', handleKeyDown);
    (firstFocusable || contentRef.current)?.focus();

    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener('keydown', handleKeyDown);
      triggerRef.current?.focus();
    };
  }, [open, onClose]);

  return (
    <SheetPrimitive
      open={open}
      onOpenChange={(o) => {
        if (!o) onClose();
      }}
    >
      <SheetContent ref={contentRef} side={side} tabIndex={-1}>
        {children}
      </SheetContent>
    </SheetPrimitive>
  );
};

export default Sheet;

