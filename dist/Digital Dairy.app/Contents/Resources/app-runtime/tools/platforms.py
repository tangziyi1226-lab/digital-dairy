from __future__ import annotations


AI_CHAT_HOSTS = {
    "chatgpt.com": "chatgpt",
    "chat.openai.com": "chatgpt",
    "doubao.com": "doubao",
    "www.doubao.com": "doubao",
    "deepseek.com": "deepseek",
    "chat.deepseek.com": "deepseek",
}

PLATFORM_HOSTS = {
    "github": ["github.com"],
    "bilibili": ["bilibili.com", "b23.tv"],
    "zhihu": ["zhihu.com"],
    "xiaohongshu": ["xiaohongshu.com", "xhslink.com"],
    "csdn": ["csdn.net"],
    "google_scholar": ["scholar.google.com"],
    "arxiv": ["arxiv.org"],
    "wechat_article": ["mp.weixin.qq.com"],
    "google_ai_studio": ["aistudio.google.com"],
    "aliyun": ["aliyun.com"],
    "openrouter": ["openrouter.ai"],
    "ucas": ["ucas.ac.cn"],
    "ict_cas": ["ict.cas.cn"],
    "baidu_netdisk": ["pan.baidu.com"],
}

INFORMATION_FLOW_PLATFORMS = {"bilibili", "zhihu", "xiaohongshu", "csdn", "wechat_article"}


def detect_ai_chat_source(host: str | None) -> str | None:
    if not host:
        return None
    normalized = host.lower()
    for domain, source in AI_CHAT_HOSTS.items():
        if normalized == domain or normalized.endswith("." + domain):
            return source
    return None


def is_ai_conversation_thread_url(ai_source: str, host: str | None, path: str | None) -> bool:
    """
    True when URL looks like an actual chat thread (not营销页/设置页等).
    Used so chatgpt/doubao/deepseek collectors only emit对话标题类记录。
    """
    h = (host or "").lower()
    p = (path or "").strip()
    if not p:
        return False
    if not p.startswith("/"):
        p = "/" + p
    pl = p.lower()
    if ai_source == "chatgpt":
        if not ("chatgpt.com" in h or "openai.com" in h):
            return False
        return "/c/" in pl or "/g/" in pl
    if ai_source == "doubao":
        return "doubao.com" in h and "/chat" in pl
    if ai_source == "deepseek":
        if "deepseek" not in h:
            return False
        return "/chat/" in pl or "/c/" in pl or "/a/chat/" in pl
    return False


def detect_platform(host: str | None) -> str | None:
    if not host:
        return None
    normalized = host.lower()
    for platform, domains in PLATFORM_HOSTS.items():
        if any(normalized == domain or normalized.endswith("." + domain) for domain in domains):
            return platform
    return None
