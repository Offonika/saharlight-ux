import { useState } from 'react';
import {
  Sheet,
  SheetTrigger,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';
import {
  Accordion,
  AccordionItem,
  AccordionTrigger,
  AccordionContent,
} from '@/components/ui/accordion';
import { Button } from '@/components/ui/button';
import { HelpCircle } from 'lucide-react';
import { useIsMobile } from '@/hooks/use-mobile';
import { useTranslation } from '@/i18n';

interface ProfileHelpSheetProps {
  therapyType?: string;
}

const sections = ['icr', 'cf', 'target', 'low', 'high', 'dia'] as const;

const ProfileHelpSheet = ({ therapyType }: ProfileHelpSheetProps) => {
  const [open, setOpen] = useState(false);
  const isMobile = useIsMobile();
  const { t } = useTranslation('profileHelp');

  const filtered =
    therapyType === 'tablets'
      ? sections.filter((s) => !['icr', 'cf', 'dia'].includes(s))
      : sections;

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button
          aria-label={t('help')}
          variant="ghost"
          size="icon"
        >
          <HelpCircle className="h-5 w-5" />
        </Button>
      </SheetTrigger>
      <SheetContent
        side={isMobile ? 'bottom' : 'right'}
        className="max-h-screen overflow-y-auto"
      >
        <SheetHeader>
          <SheetTitle>{t('help')}</SheetTitle>
        </SheetHeader>
        <Accordion type="single" collapsible className="w-full">
          {filtered.map((section) => (
            <AccordionItem key={section} value={section}>
              <AccordionTrigger>{t(`${section}.title`)}</AccordionTrigger>
              <AccordionContent>{t(`${section}.tooltip`)}</AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </SheetContent>
    </Sheet>
  );
};

export default ProfileHelpSheet;
