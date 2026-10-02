# job.py - request contract for starting task jobs
#
# A job body is any task config (see ccgen.core.tasks.configs) tagged by its "task" field. The
# configs validate themselves, so these helpers only turn pydantic errors into plain sentences
# the UI can show as they are.

from typing import Any

from pydantic import ValidationError

from ccgen.core.tasks import TASK_CONFIG
from ccgen.core.tasks.configs import TaskConfigBase

_VALUE_ERROR_PREFIX = "Value error, "


def parse_task_config(body: dict[str, Any]) -> TaskConfigBase:
    """Validate a job body into its task config. Raises ValueError with readable messages."""
    try:
        return TASK_CONFIG.validate_python(body)
    except ValidationError as e:
        raise ValueError(" ".join(_messages(e))) from e


def config_errors(body: dict[str, Any]) -> list[str]:
    """Return every reason the job body can't run, or an empty list when it is valid."""
    try:
        TASK_CONFIG.validate_python(body)
    except ValidationError as e:
        return _messages(e)
    return []


def _messages(error: ValidationError) -> list[str]:
    """Flatten pydantic errors into sentences, naming the field for type errors."""
    messages: list[str] = []
    for item in error.errors():
        message = str(item.get("msg", ""))
        if message.startswith(_VALUE_ERROR_PREFIX):
            message = message[len(_VALUE_ERROR_PREFIX):]
        else:
            location = ".".join(str(part) for part in item.get("loc", ()) if not isinstance(part, int))
            message = f"{location}: {message}" if location else message
        if message not in messages:
            messages.append(message)
    return messages
