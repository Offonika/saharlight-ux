import { useState, type KeyboardEvent } from 'react';
import { HelpCircle } from 'lucide-react';

import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';

interface HelpHintProps {
  label: string;
  className?: string;
  side?: React.ComponentProps<typeof TooltipContent>['side'];
}

const HelpHint = ({ label, className, side }: HelpHintProps) => {
  const [open, setOpen] = useState(false);

  const handleKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
    if (event.key === 'Escape') {
      setOpen(false);
      event.currentTarget.blur();
    }
  };

  return (
    <Tooltip open={open} onOpenChange={setOpen}>
      <TooltipTrigger asChild>
        <button
          type="button"
          onKeyDown={handleKeyDown}
          className={cn('flex h-4 w-4 items-center justify-center text-muted-foreground', className)}
          aria-label={label}
        >
          <HelpCircle className="h-4 w-4" aria-hidden="true" />
        </button>
      </TooltipTrigger>
      <TooltipContent side={side}>{label}</TooltipContent>
    </Tooltip>
  );
};

export default HelpHint;
