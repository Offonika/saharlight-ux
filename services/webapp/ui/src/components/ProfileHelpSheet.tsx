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

interface HelpItem {
  key: string;
  title: string;
  definition: string;
  unit: string;
  range: string;
}

interface HelpSection {
  key: string;
  title: string;
  items: HelpItem[];
}

const sections: HelpSection[] = [
  {
    key: 'targets',
    title: 'Цели сахара',
    items: [
      {
        key: 'target',
        title: 'Целевой уровень сахара',
        definition:
          'Желаемый уровень глюкозы, к которому стремится приложение при расчётах',
        unit: 'ммоль/л',
        range: '4.0–7.0',
      },
      {
        key: 'low',
        title: 'Нижний порог',
        definition:
          'При достижении этого уровня бот предупредит о гипогликемии',
        unit: 'ммоль/л',
        range: '3.0–4.5',
      },
      {
        key: 'high',
        title: 'Верхний порог',
        definition:
          'При превышении этого уровня бот предупредит о гипергликемии',
        unit: 'ммоль/л',
        range: '7.0–15.0',
      },
    ],
  },
  {
    key: 'insulin',
    title: 'Инсулин',
    items: [
      {
        key: 'icr',
        title: 'ICR (Инсулино-углеводное соотношение)',
        definition:
          'Показывает, сколько граммов углеводов покрывает 1 единица быстрого инсулина',
        unit: 'г/Ед',
        range: '1–50',
      },
      {
        key: 'cf',
        title: 'Коэффициент коррекции (КЧ)',
        definition:
          'На сколько ммоль/л снижает уровень глюкозы 1 единица быстрого инсулина',
        unit: 'ммоль/л',
        range: '0.1–10',
      },
      {
        key: 'dia',
        title: 'DIA (длительность действия инсулина)',
        definition: 'Сколько часов действует введённый инсулин',
        unit: 'ч',
        range: '1–12',
      },
      {
        key: 'preBolus',
        title: 'Пре-болюс',
        definition: 'За сколько минут до еды вводить инсулин',
        unit: 'мин',
        range: '0–60',
      },
      {
        key: 'maxBolus',
        title: 'Максимальный болюс',
        definition: 'Максимальная доза болюсного инсулина за один раз',
        unit: 'Ед',
        range: '1–25',
      },
    ],
  },
  {
    key: 'other',
    title: 'Прочее',
    items: [
      {
        key: 'roundStep',
        title: 'Шаг округления',
        definition: 'Шаг округления дозы инсулина',
        unit: 'Ед',
        range: '0.1–5',
      },
      {
        key: 'carbUnit',
        title: 'Единица углеводов',
        definition: 'Единица измерения углеводов в расчётах',
        unit: 'г или ХЕ',
        range: 'г, ХЕ',
      },
      {
        key: 'afterMealMinutes',
        title: 'Минут после еды',
        definition:
          'Через сколько минут после еды напомнить о замере сахара',
        unit: 'мин',
        range: '0–180',
      },
      {
        key: 'timezone',
        title: 'Часовой пояс',
        definition: 'Часовой пояс по стандарту IANA',
        unit: 'UTC±ч:м',
        range: 'UTC−12:00 — UTC+14:00',
      },
    ],
  },
];

const ProfileHelpSheet = ({ therapyType }: ProfileHelpSheetProps) => {
  const [open, setOpen] = useState(false);
  const isMobile = useIsMobile();
  const { t } = useTranslation();

  const filtered =
    therapyType === 'tablets'
      ? sections.filter((s) => s.key !== 'insulin')
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
              <AccordionContent>
                <ul className="space-y-3">
                  {section.items.map((item) => (
                    <li key={item.key}>
                      <p className="font-medium">{t(item.title)}</p>
                      <p className="text-sm text-muted-foreground">
                        {t(item.definition)}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        {t('Единицы')}: {item.unit}; {t('Диапазон')}: {item.range}
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

