#!/usr/bin/env bash
# scripts/check_learning_progress.sh
set -euo pipefail

: "${DATABASE_URL:?DATABASE_URL environment variable is required}"
: "${UID:?UID environment variable is required}"

psql "$DATABASE_URL" -c "
  SELECT *
  FROM learning_user_profile
  WHERE user_id = ${UID};
"

psql "$DATABASE_URL" -c "
  SELECT l.slug, lp.completed, lp.current_step, lp.current_question, lp.quiz_score
  FROM lesson_progress lp
  JOIN lessons l ON l.id = lp.lesson_id
  WHERE lp.user_id = ${UID}
  ORDER BY l.id;
"

psql "$DATABASE_URL" -c "
  SELECT l.slug, q.id AS question_id, q.question, q.correct_option
  FROM lesson_progress lp
  JOIN lessons l ON l.id = lp.lesson_id
  JOIN quiz_questions q ON q.lesson_id = l.id
  WHERE lp.user_id = ${UID}
  ORDER BY l.id, q.id;
"
