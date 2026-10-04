import logging
import logging.handlers
from pathlib import Path

from rich.logging import RichHandler

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

CONSOLE_KEYWORDS = [
    "Say:",
    "Tool call:",
    "Tool result:",
    "Tool failed:",
    "Run start:",
    "Run complete:",
    "Run failed:",
    "Recording failure:",
]


def setup_logging(log_dir: Path | None = None, level: int = logging.INFO) -> None:
    if log_dir is None:
        log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(exist_ok=True, parents=True)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    # Console: colored, wrapped, readable. Rich draws the time and level
    # columns itself, so the formatter only adds the logger name.
    console = RichHandler(
        level=level,
        show_time=True,
        show_level=True,
        show_path=False,
        omit_repeated_times=False,
        log_time_format="%H:%M:%S",
        # Messages contain things like "[User John]", which Rich would try to
        # read as markup styles, so markup must stay off.
        markup=False,
        rich_tracebacks=True,
        tracebacks_show_locals=False,
        keywords=CONSOLE_KEYWORDS,
    )
    console.setFormatter(logging.Formatter(fmt="%(name)s | %(message)s"))

    # File: verbose, rotated, includes DEBUG, plain text (no Rich formatting)
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

