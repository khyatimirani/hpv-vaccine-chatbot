from abc import ABC
from typing import Any

from bot.client.prompt import SYSTEM_TEMPLATE


class GroqModelSettings(ABC):
    model_id: str
    system_template: str = SYSTEM_TEMPLATE
    config_answer: dict[str, Any] | None
    reasoning: bool = False
    reasoning_start_tag: str | None = None
    reasoning_stop_tag: str | None = None
