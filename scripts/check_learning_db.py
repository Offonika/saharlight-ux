from __future__ import annotations

import os

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


def main() -> None:
    url = os.environ["DATABASE_URL"]
    engine: Engine = create_engine(url)
    try:
        with engine.connect() as conn:
            lessons = conn.execute(text("SELECT count(*) FROM lessons")).scalar_one()
            steps = conn.execute(text("SELECT count(*) FROM lesson_steps")).scalar_one()
            quizzes = conn.execute(
                text("SELECT count(*) FROM quiz_questions")
            ).scalar_one()
        print(f"lessons={lessons}, steps={steps}, quizzes={quizzes}")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
