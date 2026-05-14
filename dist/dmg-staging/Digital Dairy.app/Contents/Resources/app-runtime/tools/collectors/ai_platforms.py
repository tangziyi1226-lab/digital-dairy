from __future__ import annotations

from tools.browser_history import collect_ai_conversation_visits
from tools.common import GrowthDimension, LifeEvent


def collect_chatgpt(
    start,
    end,
    dimensions: list[GrowthDimension],
    settings: dict,
) -> list[LifeEvent]:
    return collect_ai_conversation_visits("chatgpt", start, end, dimensions, settings)


def collect_doubao(
    start,
    end,
    dimensions: list[GrowthDimension],
    settings: dict,
) -> list[LifeEvent]:
    return collect_ai_conversation_visits("doubao", start, end, dimensions, settings)


def collect_deepseek(
    start,
    end,
    dimensions: list[GrowthDimension],
    settings: dict,
) -> list[LifeEvent]:
    return collect_ai_conversation_visits("deepseek", start, end, dimensions, settings)


__all__ = ["collect_chatgpt", "collect_doubao", "collect_deepseek"]
