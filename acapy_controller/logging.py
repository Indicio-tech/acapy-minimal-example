"""Logging utilities."""

from contextlib import contextmanager
import logging
from os import get_terminal_size, getenv
import sys
from typing import Optional, TextIO

from blessings import Terminal


LOG_LEVEL = getenv("LOG_LEVEL", "debug")
LOGGING_SET = False


class ColorFormatter(logging.Formatter):
    """Colorizer for logging output."""

    def __init__(self, fmt: str):
        """Init formatter."""
        self.default = logging.Formatter(fmt)
        term = Terminal()
        self.formats = {
            logging.DEBUG: logging.Formatter(f"{term.dim}{fmt}{term.normal}"),
            logging.ERROR: logging.Formatter(f"{term.red}{fmt}{term.normal}"),
        }

    def format(self, record):
        """Format log record."""
        formatter = self.formats.get(record.levelno, self.default)
        return formatter.format(record)


def logging_to_stdout(*other: logging.Logger):
    """Set up logging to stdout."""

    global LOGGING_SET
    if LOGGING_SET:
        return

    if sys.stdout.isatty():
        for logger in (logging.getLogger("acapy_controller"), *other):
            logger.setLevel(LOG_LEVEL.upper())
            ch = logging.StreamHandler()
            ch.setLevel(LOG_LEVEL.upper())
            ch.setFormatter(ColorFormatter("[%(levelname)s] %(message)s"))
            logger.addHandler(ch)
    else:
        logging.basicConfig(
            stream=sys.stdout,
            level=LOG_LEVEL.upper(),
            format="[%(levelname)s] %(message)s",
        )

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


def pause_for_input(
    prompt: Optional[str] = None,
    file: TextIO = sys.stdout,
):
    """Pause the program and wait for the user to hit enter.

    This helps the user to see the output of the program before it proceeds
    past a step.
    """
    if file == sys.stdout and sys.stdout.isatty():
        term = Terminal()
        prompt = prompt or "Press Enter to continue..."
        print(f"{term.blue}{term.bold}", end="")
        input(prompt)
        print(f"{term.normal}", end="")
