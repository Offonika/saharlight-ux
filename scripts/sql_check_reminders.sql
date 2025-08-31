-- scripts/sql_check_reminders.sql
-- Перед запуском подставь свой telegram_id через \set:
--   \set tg_id 448794918

-- 1) Напоминания пользователя + его TZ
SELECT r.id, r.enabled, r.time AS reminder_time,
       COALESCE(u.timezone,'(null)') AS user_tz
FROM reminders r
LEFT JOIN users u ON u.telegram_id = r.telegram_id
WHERE r.telegram_id = :tg_id
ORDER BY r.time;

-- 2) Должно ли было сработать сегодня по MSK и когда следующее
WITH now_msk AS (SELECT (now() AT TIME ZONE 'Europe/Moscow') AS ts)
SELECT
  r.id,
  r.time AS reminder_time,
  (SELECT ts FROM now_msk) AS now_msk,
  (date_trunc('day',(SELECT ts FROM now_msk))::date + r.time) AS scheduled_today_msk,
  ((SELECT ts FROM now_msk) >= (date_trunc('day',(SELECT ts FROM now_msk))::date + r.time)) AS should_have_fired_today,
  CASE
    WHEN ((SELECT ts FROM now_msk) >= (date_trunc('day',(SELECT ts FROM now_msk))::date + r.time))
      THEN (date_trunc('day',(SELECT ts FROM now_msk))::date + r.time + INTERVAL '1 day')
      ELSE (date_trunc('day',(SELECT ts FROM now_msk))::date + r.time)
  END AS next_run_msk
FROM reminders r
WHERE r.telegram_id = :tg_id
ORDER BY r.time;

-- 3) Последние попытки отправки
SELECT id, reminder_id, telegram_id,
       sent_at AT TIME ZONE 'Europe/Moscow' AS sent_at_msk,
       status,
       SUBSTRING(COALESCE(error,''),1,200) AS error_short
FROM reminder_logs
WHERE telegram_id = :tg_id
ORDER BY sent_at DESC
LIMIT 50;
