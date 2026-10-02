# callbacks.py - safe invocation of the optional progress/segment callbacks every engine accepts
#
# Callbacks come from the UI layer (job_manager, CLI) and must never crash a long-running
# transcription, so ordinary exceptions they raise are logged and dropped. JobCancelled is the one
# exception that deliberately escapes: a callback raises it to unwind a job the user cancelled.

import logging
from typing import Any, Callable, Optional

_log = logging.getLogger(__name__)

StatusCallback = Optional[Callable[[str], None]]
ProgressCallback = Optional[Callable[[int, int], None]]
SegmentCallback = Optional[Callable[[Any], None]]


class JobCancelled(Exception):
    """Raised from a callback to stop the running pipeline at the next safe point."""


def emit_status(fn: StatusCallback, message: str) -> None:
    """Send a human-readable status message to `fn` when present."""
    _invoke(fn, message)


def emit_progress(fn: ProgressCallback, done: int, total: int) -> None:
    """Send a (done, total) progress pair to `fn` when present."""
    _invoke(fn, done, total)


def emit_segment(fn: SegmentCallback, segment: Any) -> None:
    """Send one finished segment to `fn` when present."""
    _invoke(fn, segment)


def _invoke(fn: Optional[Callable[..., None]], *args: Any) -> None:
    """Call `fn(*args)`, re-raising JobCancelled and logging anything else."""
    if fn is None:
        return
    try:
        fn(*args)
    except JobCancelled:
        raise
    except Exception:
        _log.debug("Callback %r raised", fn, exc_info=True)
