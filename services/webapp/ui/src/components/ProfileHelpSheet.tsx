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
import type { TherapyType } from '@/features/profile/types';

interface ProfileHelpSheetProps {
  therapyType?: TherapyType;
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
        key: 'rapidInsulinType',
        titleKey: 'profileHelp.rapidInsulinType.title',
        definitionKey: 'profileHelp.rapidInsulinType.definition',
        unitKey: 'profileHelp.rapidInsulinType.unit',
        rangeKey: 'profileHelp.rapidInsulinType.range',
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
        key: 'therapyType',
        titleKey: 'profileHelp.therapyType.title',
        definitionKey: 'profileHelp.therapyType.definition',
        unitKey: 'profileHelp.therapyType.unit',
        rangeKey: 'profileHelp.therapyType.range',
      },
      {
        key: 'carbUnits',
        titleKey: 'profileHelp.carbUnits.title',
        definitionKey: 'profileHelp.carbUnits.definition',
        unitKey: 'profileHelp.carbUnits.unit',
        rangeKey: 'profileHelp.carbUnits.range',
      },
      {
        key: 'gramsPerXe',
        titleKey: 'profileHelp.gramsPerXe.title',
        definitionKey: 'profileHelp.gramsPerXe.definition',
        unitKey: 'profileHelp.gramsPerXe.unit',
        rangeKey: 'profileHelp.gramsPerXe.range',
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

  const sectionsByTherapy = sections.filter(
    (section) =>
      section.key !== 'insulin' ||
      (therapyType !== undefined &&
        therapyType !== 'tablets' &&
        therapyType !== 'none'),
  );

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button
          aria-label={t('profileHelp.help')}
          variant="outline"
          size="sm"
          className="gap-2"
        >
          <HelpCircle className="h-5 w-5" />
          {t('profileHelp.help')}
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
              aria-label={t('profileHelp.close')}
            >
              <X className="h-4 w-4" />
            </Button>
          </SheetClose>
        </SheetHeader>
        <Accordion type="multiple" className="w-full">
          {sectionsByTherapy.map((section) => (
            <AccordionItem key={section.key} value={section.key}>
              <AccordionTrigger>{t(section.titleKey)}</AccordionTrigger>
              <AccordionContent>
                <ul className="space-y-3">
                  {section.items.map((item) => {
                    const unit = t(item.unitKey);
                    const range = t(item.rangeKey);

                    return (
                      <li key={item.key}>
                        <p className="font-medium">{t(item.titleKey)}</p>
                        <p className="text-sm text-muted-foreground">
                          {t(item.definitionKey)}
                        </p>
                        {unit !== '—' && (
                          <p className="text-sm text-muted-foreground">
                            {t('profileHelp.units')}: {unit}
                          </p>
                        )}
                        {range !== '—' && (
                          <p className="text-sm text-muted-foreground">
                            {t('profileHelp.range')}: {range}
                          </p>
                        )}
                      </li>
                    );
                  })}
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

