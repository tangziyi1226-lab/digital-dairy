from __future__ import annotations

from tools.collectors.ai_platforms import collect_chatgpt, collect_deepseek, collect_doubao
from tools.collectors.browsers import collect_chrome, collect_edge
from tools.collectors.ides import collect_cursor, collect_vscode
from tools.collectors.imports import collect_health_imports, collect_manual_imports, collect_mobile_imports
from tools.collectors.productivity import collect_ticktick_focus


TOOL_REGISTRY = {
    "chrome": collect_chrome,
    "edge": collect_edge,
    "ticktick_focus": collect_ticktick_focus,
    "cursor": collect_cursor,
    "vscode": collect_vscode,
    "chatgpt": collect_chatgpt,
    "doubao": collect_doubao,
    "deepseek": collect_deepseek,
    "manual_imports": collect_manual_imports,
    "mobile_imports": collect_mobile_imports,
    "mi_health": collect_health_imports,
}

TOOL_CATEGORIES = {
    "browsers": ["chrome", "edge"],
    "productivity": ["ticktick_focus"],
    "ides": ["cursor", "vscode"],
    "ai_platforms": ["chatgpt", "doubao", "deepseek"],
    "imports": ["manual_imports", "mobile_imports", "mi_health"],
}
