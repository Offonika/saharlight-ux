BEGIN;

INSERT INTO lessons (slug, title, content, is_active)
VALUES (
    'xe_basics',
    'Bread Units Basics',
    'One bread unit (XE) equals 12 grams of carbohydrates.\nCount the XE in your meal to adjust insulin dose.\nCheck product labels to find carbohydrate amounts.',
    TRUE
)
ON CONFLICT (slug) DO NOTHING;

WITH lesson AS (
    SELECT id FROM lessons WHERE slug = 'xe_basics'
)
INSERT INTO lesson_steps (lesson_id, step_order, content)
SELECT lesson.id, s.step_order, s.content
FROM lesson
CROSS JOIN (
    VALUES
        (1, 'One bread unit (XE) equals 12 grams of carbohydrates.'),
        (2, 'Count the XE in your meal to adjust insulin dose.'),
        (3, 'Check product labels to find carbohydrate amounts.')
) AS s(step_order, content)
ON CONFLICT (lesson_id, step_order) DO NOTHING;

WITH lesson AS (
    SELECT id FROM lessons WHERE slug = 'xe_basics'
)
DELETE FROM quiz_questions WHERE lesson_id = (SELECT id FROM lesson);

WITH lesson AS (
    SELECT id FROM lessons WHERE slug = 'xe_basics'
)
INSERT INTO quiz_questions (lesson_id, question, options, correct_option)
SELECT lesson.id, q.question, q.options::jsonb, q.correct_option
FROM lesson
CROSS JOIN (
    VALUES
        ('How many grams of carbs are in 1 XE?', '["10 g","12 g","15 g"]', 1),
        ('Why count XE before meals?', '["To plan exercise","To adjust insulin dose","No need"]', 1),
        ('Where can you find carb info?', '["Product labels","Weather reports","Nowhere"]', 0)
) AS q(question, options, correct_option);

COMMIT;
