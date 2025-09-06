import { useState, type KeyboardEvent, type ReactNode } from 'react';
import { HelpCircle } from 'lucide-react';

import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
  TooltipProvider,
} from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import { useTranslation } from '@/i18n';

interface HelpHintProps {
  label?: string;
  children: ReactNode;
  className?: string;
  side?: React.ComponentProps<typeof TooltipContent>['side'];
}

const HelpHint = ({
  label,
  children,
  className,
  side = 'right',
}: HelpHintProps) => {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);

  const handleKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
    if (event.key === 'Escape') {
      setOpen(false);
      event.currentTarget.blur();
    }
  };

  return (
    <TooltipProvider delayDuration={150}>
      <Tooltip open={open} onOpenChange={setOpen}>
        <TooltipTrigger asChild>
          <button
            type="button"
            onClick={() => setOpen((prev) => !prev)}
            onKeyDown={handleKeyDown}
            className={cn(
              'flex h-4 w-4 items-center justify-center text-muted-foreground',
              className,
            )}
            aria-label={t(label ?? 'profileHelp.help')}
          >
            <HelpCircle className="h-4 w-4" aria-hidden="true" />
          </button>
        </TooltipTrigger>
        <TooltipContent side={side}>{children}</TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
};

export default HelpHint;
