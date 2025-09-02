import { useState } from 'react';
import {
  Sheet,
  SheetTrigger,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetClose,
} from '@/components/ui/sheet';
import {
  Accordion,
  AccordionItem,
  AccordionTrigger,
  AccordionContent,
} from '@/components/ui/accordion';
import { Button } from '@/components/ui/button';
import { HelpCircle, X } from 'lucide-react';
import { useIsMobile } from '@/hooks/use-mobile';
import { useTranslation } from '@/i18n';

interface ProfileHelpSheetProps {
  therapyType?: 'insulin' | 'tablets' | 'none' | 'mixed';
}

interface HelpItem {
  key: string;
  titleKey: string;
  definitionKey: string;
  unitKey: string;
  rangeKey: string;
}

interface HelpSection {
  key: string;
  titleKey: string;
  items: HelpItem[];
}

const sections: HelpSection[] = [
  {
    key: 'targets',
    titleKey: 'profileHelp.sections.targets',
    items: [
      {
        key: 'target',
        titleKey: 'profileHelp.target.title',
        definitionKey: 'profileHelp.target.definition',
        unitKey: 'profileHelp.target.unit',
        rangeKey: 'profileHelp.target.range',
      },
      {
        key: 'low',
        titleKey: 'profileHelp.low.title',
        definitionKey: 'profileHelp.low.definition',
        unitKey: 'profileHelp.low.unit',
        rangeKey: 'profileHelp.low.range',
      },
      {
        key: 'high',
        titleKey: 'profileHelp.high.title',
        definitionKey: 'profileHelp.high.definition',
        unitKey: 'profileHelp.high.unit',
        rangeKey: 'profileHelp.high.range',
      },
    ],
  },
  {
    key: 'insulin',
    titleKey: 'profileHelp.sections.insulin',
    items: [
      {
        key: 'icr',
        titleKey: 'profileHelp.icr.title',
        definitionKey: 'profileHelp.icr.definition',
        unitKey: 'profileHelp.icr.unit',
        rangeKey: 'profileHelp.icr.range',
      },
      {
        key: 'cf',
        titleKey: 'profileHelp.cf.title',
        definitionKey: 'profileHelp.cf.definition',
        unitKey: 'profileHelp.cf.unit',
        rangeKey: 'profileHelp.cf.range',
      },
      {
        key: 'dia',
        titleKey: 'profileHelp.dia.title',
        definitionKey: 'profileHelp.dia.definition',
        unitKey: 'profileHelp.dia.unit',
        rangeKey: 'profileHelp.dia.range',
      },
      {
        key: 'preBolus',
        titleKey: 'profileHelp.preBolus.title',
        definitionKey: 'profileHelp.preBolus.definition',
        unitKey: 'profileHelp.preBolus.unit',
        rangeKey: 'profileHelp.preBolus.range',
      },
      {
        key: 'maxBolus',
        titleKey: 'profileHelp.maxBolus.title',
        definitionKey: 'profileHelp.maxBolus.definition',
        unitKey: 'profileHelp.maxBolus.unit',
        rangeKey: 'profileHelp.maxBolus.range',
      },
    ],
  },
  {
    key: 'other',
    titleKey: 'profileHelp.sections.other',
    items: [
      {
        key: 'roundStep',
        titleKey: 'profileHelp.roundStep.title',
        definitionKey: 'profileHelp.roundStep.definition',
        unitKey: 'profileHelp.roundStep.unit',
        rangeKey: 'profileHelp.roundStep.range',
      },
      {
        key: 'carbUnit',
        titleKey: 'profileHelp.carbUnit.title',
        definitionKey: 'profileHelp.carbUnit.definition',
        unitKey: 'profileHelp.carbUnit.unit',
        rangeKey: 'profileHelp.carbUnit.range',
      },
      {
        key: 'afterMealMinutes',
        titleKey: 'profileHelp.afterMealMinutes.title',
        definitionKey: 'profileHelp.afterMealMinutes.definition',
        unitKey: 'profileHelp.afterMealMinutes.unit',
        rangeKey: 'profileHelp.afterMealMinutes.range',
      },
      {
        key: 'timezone',
        titleKey: 'profileHelp.timezone.title',
        definitionKey: 'profileHelp.timezone.definition',
        unitKey: 'profileHelp.timezone.unit',
        rangeKey: 'profileHelp.timezone.range',
      },
    ],
  },
];

const ProfileHelpSheet = ({ therapyType }: ProfileHelpSheetProps) => {
  const [open, setOpen] = useState(false);
  const isMobile = useIsMobile();
  const { t } = useTranslation();

  const filtered =
    therapyType === 'tablets' || therapyType === 'none'
      ? sections.filter((s) => s.key !== 'insulin')
      : sections;

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button
          aria-label={t('profileHelp.help')}
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
        <SheetHeader className="flex-row items-center justify-between">
          <SheetTitle>{t('profileHelp.help')}</SheetTitle>
          <SheetClose asChild>
            <Button
              variant="ghost"
              size="icon"
              aria-label="Закрыть"
            >
              <X className="h-4 w-4" />
            </Button>
          </SheetClose>
        </SheetHeader>
        <Accordion type="single" collapsible className="w-full">
          {filtered.map((section) => (
            <AccordionItem key={section.key} value={section.key}>
              <AccordionTrigger>{t(section.titleKey)}</AccordionTrigger>
              <AccordionContent>
                <ul className="space-y-3">
                  {section.items.map((item) => (
                    <li key={item.key}>
                      <p className="font-medium">{t(item.titleKey)}</p>
                      <p className="text-sm text-muted-foreground">
                        {t(item.definitionKey)}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        {t('profileHelp.units')}: {t(item.unitKey)}; {t('profileHelp.range')}: {t(item.rangeKey)}
                      </p>
                    </li>
                  ))}
                </ul>
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </SheetContent>
    </Sheet>
  );
};

export default ProfileHelpSheet;

