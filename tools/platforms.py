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


def detect_platform(host: str | None) -> str | None:
    if not host:
        return None
    normalized = host.lower()
    for platform, domains in PLATFORM_HOSTS.items():
        if any(normalized == domain or normalized.endswith("." + domain) for domain in domains):
            return platform
    return None
