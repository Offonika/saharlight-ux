# Reminder Mapping: соответствие типов напоминаний и полей записи

Документ фиксирует единое соответствие между типами напоминаний и полями
записей дневника, чтобы команды API, UX и контента использовали одинаковые
названия.

| Reminder enum | Поле записи | UI label (RU) | `REMINDER_NAMES` (RU) | `REMINDER_ACTIONS` (RU) |
|---------------|-------------|----------------|------------------------|--------------------------|
| `insulin_short` | `insulin_short` | «Инсулин (короткий)» | «Короткий инсулин» | «Короткий инсулин» |
| `insulin_long` | `insulin_long` | «Инсулин (длинный)» | «Длинный инсулин» | «Длинный инсулин» |

## Проверочные точки

- `UI label (RU)` синхронизирован с выпадающими списками и списками шаблонов:
  `services/webapp/ui/src/features/reminders/pages/RemindersList.tsx`,
  `RemindersCreate.tsx`, `RemindersEdit.tsx` и `components/Templates.tsx`.
- Значения в колонках `REMINDER_NAMES` и `REMINDER_ACTIONS` копируют словари
  в `services/api/app/diabetes/handlers/reminder_handlers.py` и не должны
  расходиться при будущих изменениях.
- Любые новые варианты напоминаний по инсулину добавляются в эту таблицу перед
  тем, как попадут в UX или API.
