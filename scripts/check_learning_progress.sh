# scripts/check_learning_progress.sh
#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:?DATABASE_URL environment variable is required}"
: "${UID:?UID environment variable is required}"

echo "== learning_user_profile =="
psql "$DATABASE_URL" -v uid="$UID" -c "
  SELECT *
  FROM learning_user_profile
  WHERE user_id = :uid;
"

echo "== learning_plans (последние) =="
psql "$DATABASE_URL" -v uid="$UID" -c "
  SELECT id, user_id, current_topic, total_steps, created_at, updated_at
  FROM learning_plans
  WHERE user_id = :uid
  ORDER BY updated_at DESC
  LIMIT 5;
"

echo "== learning_progress (динамика) =="
psql "$DATABASE_URL" -v uid="$UID" -c "
  SELECT user_id, plan_id, topic_slug, step_idx,
         progress_json->>'last_sent_step_id' AS last_sent_step_id,
         updated_at
  FROM learning_progress
  WHERE user_id = :uid
  ORDER BY updated_at DESC
  LIMIT 20;
"

echo "== lesson_progress (legacy, статические уроки) =="
psql "$DATABASE_URL" -v uid="$UID" -c "
  SELECT l.slug, lp.step_idx, lp.completed, lp.updated_at
  FROM lesson_progress lp
  JOIN lessons l ON l.id = lp.lesson_id
  WHERE lp.user_id = :uid
  ORDER BY lp.updated_at DESC
  LIMIT 20;
"

echo "== quiz_questions по статическим урокам (если используются) =="
psql "$DATABASE_URL" -v uid="$UID" -c "
  SELECT l.slug, q.id AS question_id, LEFT(q.question, 80) AS question_head, q.correct_option
  FROM lesson_progress lp
  JOIN lessons l ON l.id = lp.lesson_id
  JOIN quiz_questions q ON q.lesson_id = l.id
  WHERE lp.user_id = :uid
  ORDER BY l.id, q.id
  LIMIT 50;
"

echo "== пересечение режимов для пользователя =="
psql "$DATABASE_URL" -v uid="$UID" -c "
  SELECT
    EXISTS(SELECT 1 FROM learning_progress WHERE user_id = :uid) AS has_learning,
    EXISTS(SELECT 1 FROM lesson_progress   WHERE user_id = :uid) AS has_lesson;
"

echo "== дубли в learning_progress по ключу (user_id, plan_id, topic_slug) =="
psql "$DATABASE_URL" -v uid="$UID" -c "
  SELECT user_id, plan_id, topic_slug, COUNT(*) AS cnt
  FROM learning_progress
  WHERE user_id = :uid
  GROUP BY user_id, plan_id, topic_slug
  HAVING COUNT(*) > 1
  ORDER BY cnt DESC;
"
