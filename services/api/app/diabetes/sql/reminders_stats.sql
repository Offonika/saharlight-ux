SELECT reminder_id,
       MAX(event_time) AS last_fired_at,
       SUM(CASE WHEN event_time >= :since THEN 1 ELSE 0 END) AS fires7d
FROM reminder_logs
WHERE telegram_id = :telegram_id
GROUP BY reminder_id;
