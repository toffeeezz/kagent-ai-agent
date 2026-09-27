# modules/logging_config.py
import logging
import logging.handlers
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def setup_logging(log_dir: Path | None = None, level: int = logging.INFO) -> None:
    if log_dir is None:
        log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(exist_ok=True, parents=True)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)  # let handlers filter; root stays permissive

    # Console: concise, human-readable
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%H:%M:%S",
        )
    )

    # File: verbose, rotated, includes DEBUG
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "app.log",
        maxBytes=10_000_000,
        backupCount=5,
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    root.addHandler(console)
    root.addHandler(file_handler)

    # Quiet down noisy third-party libs
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
