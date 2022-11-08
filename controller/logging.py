import logging
from os import getenv, get_terminal_size
import sys
from contextlib import contextmanager
from typing import Optional, TextIO


from blessings import Terminal


LOG_LEVEL = getenv("LOG_LEVEL", "debug")
LOGGING_SET = False


class ColorFormatter(logging.Formatter):
    def __init__(self, fmt: str):
        self.default = logging.Formatter(fmt)
        term = Terminal()
        self.formats = {
            logging.DEBUG: logging.Formatter(f"{term.dim}{fmt}{term.normal}"),
            logging.ERROR: logging.Formatter(f"{term.red}{fmt}{term.normal}"),
        }

    def format(self, record):
        formatter = self.formats.get(record.levelno, self.default)
        return formatter.format(record)


def logging_to_stdout():
    global LOGGING_SET
    if LOGGING_SET:
        return

    if sys.stdout.isatty():
        logger = logging.getLogger("controller")
        logger.setLevel(LOG_LEVEL.upper())
        ch = logging.StreamHandler()
        ch.setLevel(LOG_LEVEL.upper())
        ch.setFormatter(ColorFormatter("[%(levelname)s] %(message)s"))
        logger.addHandler(ch)
    else:
        logging.basicConfig(
            stream=sys.stdout,
            level=logging.WARNING,
            format="[%(levelname)s] %(message)s",
        )
        logging.getLogger("controller").setLevel(LOG_LEVEL.upper())

    LOGGING_SET = True


@contextmanager
def section(
    title: str,
    character: str = "=",
    close: Optional[str] = None,
    file: TextIO = sys.stdout,
):
    """Mark a section in output."""
    if file == sys.stdout and sys.stdout.isatty():
        term = Terminal()
        size = get_terminal_size()
        left = character * (int(size.columns / 2) - int((len(title) + 1) / 2))
        right = character * (size.columns - (len(left) + len(title) + 2))
        print(f"{term.blue}{term.bold}{left} {title} {right}{term.normal}")
        yield
        if close:
            print(f"{term.blue}{close * size.columns}{term.normal}")
    else:
        print(title, file=file)
        yield
