import logging
import os
from config import OPENAI_PROXY, validate_tokens


def setup() -> logging.Logger:
    """Configure logging and validate tokens."""
    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(message)s",
        level=logging.INFO,
        handlers=[
            logging.FileHandler("bot.log"),
            logging.StreamHandler(),
        ],
    )
    logger = logging.getLogger("bot")

    validate_tokens()
    # os.environ["HTTP_PROXY"] = OPENAI_PROXY
    # os.environ["HTTPS_PROXY"] = OPENAI_PROXY

    for name in ("httpcore", "httpx", "telegram", "telegram.ext"):
        logging.getLogger(name).setLevel(logging.WARNING)

    logging.info("=== Bot started ===")
    logger.info("Логгер настроен, бот запускается")
    return logger
