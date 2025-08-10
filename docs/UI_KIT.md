# UI Kit

Этот документ описывает базовые правила и примеры использования компонентов интерфейса проекта.

## Правила оформления

### Отступы
- Используем **2 пробела** для одного уровня вложенности.
- Табуляция и смешанные отступы запрещены.

### Именование пропсов
- Все пропсы записываются в `camelCase`.
- Обработчики событий начинаются с `on`: `onClose`, `onChange`.
- Булевы значения используют префиксы `is`/`has`: `isOpen`, `hasFooter`.

### Светлая и тёмная тема
- Цвета задаём через дизайн‑токены и утилитарные классы Tailwind: `bg-background`, `text-foreground`, `border-border` и т.д.
- Не задаём цвет напрямую; используем переменные, чтобы интерфейс автоматически подстраивался под `light`/`dark` темы.
- Проверяем контраст и читаемость в обеих темах.

## Примеры использования

### Modal
```tsx
import { useState } from 'react';
import { Modal } from '@/components';

export const ExampleModal = () => {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button onClick={() => setOpen(true)}>Открыть</button>
      <Modal
        open={open}
        onClose={() => setOpen(false)}
        title="Диалог"
        footer={<button onClick={() => setOpen(false)}>OK</button>}
      >
        Содержимое модального окна
      </Modal>
    </>
  );
};
```

### SegmentedControl
```tsx
import { useState } from 'react';
import { SegmentedControl } from '@/components';

const items = [
  { value: 'day', label: 'День' },
  { value: 'week', label: 'Неделя' },
  { value: 'month', label: 'Месяц' }
];

export const ExampleSegmented = () => {
  const [period, setPeriod] = useState('day');

  return (
    <SegmentedControl
      value={period}
      onChange={setPeriod}
      items={items}
    />
  );
};
```

Компонент помечен атрибутом `role="radiogroup"`, а элементы — `role="radio"`.
Поддерживается навигация по сегментам с помощью клавиш стрелок, **Home** и
**End**.
