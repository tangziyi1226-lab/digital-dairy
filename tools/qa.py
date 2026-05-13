from __future__ import annotations

from pathlib import Path

from tools.common import DATA_DIR
from tools.llm import chat_completion


def latest_summary_date() -> str | None:
    summary_dir = DATA_DIR / "summaries"
    if not summary_dir.exists():
        return None
    files = sorted(summary_dir.glob("*-summary.md"))
    if not files:
        return None
    return files[-1].name.replace("-summary.md", "")


def build_qa_messages(question: str, summary: str, events: str) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": "你是 Personal Growth OS 的私人问答助手。只根据本地 data 内容回答，温和、具体、不编造。",
        },
        {
            "role": "user",
            "content": (
                f"用户问题：{question}\n\n"
                f"当天总结：\n{summary}\n\n"
                f"当天事件 JSON：\n```json\n{events}\n```"
            ),
        },
    ]


def answer_question(settings: dict[str, object], date_text: str, question: str) -> tuple[str, Path]:
    events_path = DATA_DIR / "events" / f"{date_text}-events.json"
    summary_path = DATA_DIR / "summaries" / f"{date_text}-summary.md"
    events = events_path.read_text(encoding="utf-8") if events_path.exists() else "[]"
    summary = summary_path.read_text(encoding="utf-8") if summary_path.exists() else ""
    answer = chat_completion(settings, build_qa_messages(question, summary, events)).strip()
    reply_dir = DATA_DIR / "replies"
    reply_dir.mkdir(parents=True, exist_ok=True)
    reply_path = reply_dir / f"{date_text}-reply.md"
    reply_path.write_text(answer + "\n", encoding="utf-8")
    return answer, reply_path

