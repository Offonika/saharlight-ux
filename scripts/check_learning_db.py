from __future__ import annotations

import logging
import os

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def main() -> None:
    url = os.environ.get("DATABASE_URL")
    if url is None:
        logger.error("DATABASE_URL environment variable is not set")
        raise SystemExit(1)

    engine: Engine = create_engine(url)
    try:
        with engine.connect() as conn:
            lessons = conn.execute(text("SELECT count(*) FROM lessons")).scalar_one()
            steps = conn.execute(text("SELECT count(*) FROM lesson_steps")).scalar_one()
            quizzes = conn.execute(
                text("SELECT count(*) FROM quiz_questions")
            ).scalar_one()
        logger.info(f"lessons={lessons}, steps={steps}, quizzes={quizzes}")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
