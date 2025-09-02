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
  therapyType?: 'insulin' | 'tablets' | 'none' | 'mixed';
}

const sections = [
  {
    key: 'icr',
    title: 'ICR (Инсулино-углеводное соотношение)',
    content:
      'Показывает, сколько граммов углеводов покрывает 1 единица быстрого инсулина',
  },
  {
    key: 'cf',
    title: 'Коэффициент коррекции (КЧ)',
    content:
      'На сколько ммоль/л снижает уровень глюкозы 1 единица быстрого инсулина',
  },
  {
    key: 'target',
    title: 'Целевой уровень сахара',
    content:
      'Желаемый уровень глюкозы, к которому стремится приложение при расчётах',
  },
  {
    key: 'low',
    title: 'Нижний порог',
    content: 'При достижении этого уровня бот предупредит о гипогликемии',
  },
  {
    key: 'high',
    title: 'Верхний порог',
    content: 'При превышении этого уровня бот предупредит о гипергликемии',
  },
  {
    key: 'dia',
    title: 'DIA (длительность действия инсулина)',
    content: 'Сколько часов действует введённый инсулин',
  },
];

const ProfileHelpSheet = ({ therapyType }: ProfileHelpSheetProps) => {
  const [open, setOpen] = useState(false);
  const isMobile = useIsMobile();
  const { t } = useTranslation();

  const filtered =
    therapyType === 'tablets'
      ? sections.filter((s) => !['icr', 'cf', 'dia'].includes(s.key))
      : sections;

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button
          aria-label={t('Справка')}
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
          <SheetTitle>{t('Справка')}</SheetTitle>
        </SheetHeader>
        <Accordion type="single" collapsible className="w-full">
          {filtered.map((section) => (
            <AccordionItem key={section.key} value={section.key}>
              <AccordionTrigger>{t(section.title)}</AccordionTrigger>
              <AccordionContent>{t(section.content)}</AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </SheetContent>
    </Sheet>
  );
};

export default ProfileHelpSheet;
