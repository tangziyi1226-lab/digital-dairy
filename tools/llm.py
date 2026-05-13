from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


def resolve_api_key(settings: dict[str, object]) -> str:
    api = settings.get("api", {})
    if not isinstance(api, dict):
        api = {}
    env_name = str(api.get("api_key_env") or "DEEPSEEK_API_KEY")
    api_key = os.environ.get(env_name)
    if api_key:
        return api_key
    literal = str(api.get("api_key") or "")
    if literal and not literal.startswith("PUT_"):
        return literal
    raise RuntimeError(f"Missing API key. Set ${env_name} or config.api.api_key.")


def chat_completion(settings: dict[str, object], messages: list[dict[str, str]]) -> str:
    api = settings.get("api", {})
    if not isinstance(api, dict):
        api = {}
    base_url = str(api.get("base_url") or "https://api.deepseek.com")
    model = str(api.get("model") or "deepseek-chat")
    payload = {
        "model": model,
        "messages": messages,
        "temperature": float(api.get("temperature", 0.55)),
        "max_tokens": int(api.get("max_tokens", 4200)),
    }
    request = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {resolve_api_key(settings)}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"LLM API returned HTTP {error.code}: {detail}") from error
    return data["choices"][0]["message"]["content"]
