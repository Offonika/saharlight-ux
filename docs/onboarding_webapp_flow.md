# Onboarding WebApp Flow

Краткий гайд по онбордингу через WebApp без `timezone.html` и кнопки в меню.

## Старт
- Пользователь открывает ссылку вида `https://t.me/<bot>?startapp=onboarding` или
  жмёт кнопку после команды `/start`.
- WebApp при загрузке отправляет событие `onboarding_started`.

## События
| Событие | Шаг | Описание |
| --- | --- | --- |
| `onboarding_started` | `profile` | WebApp открыт в режиме онбординга |
| `profile_saved` | `profile` | Пользователь сохранил профиль |
| `first_reminder_created` | `reminders` | Создано первое напоминание |
| `onboarding_completed` | `reminders` | Завершение; при пропуске напоминаний передаётся `skippedReminders: true` |

## Завершение
Онбординг считается завершённым, когда профиль валиден и:
- создано хотя бы одно напоминание, **или**
- отправлено `onboarding_completed` с `skippedReminders = true`.

## Проверка статуса
```bash
curl -H 'Authorization: tg <init-data>' \
  http://localhost:8000/api/onboarding/status
```
Возвращает `completed`, `step` и `missing`.
