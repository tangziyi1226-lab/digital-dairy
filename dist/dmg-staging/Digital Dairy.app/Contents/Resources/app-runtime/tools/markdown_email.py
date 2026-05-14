from __future__ import annotations

import re
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

# <img ... src="...">（src 可在任意属性顺序）
_IMG_SRC = re.compile(
    r'(<img\b)(?P<pre>[^>]*?)(\ssrc=")(?P<src>[^"]+)(")',
    re.IGNORECASE,
)


def _embed_images(html_fragment: str, base_dir: Path) -> tuple[str, list[tuple[str, Path]]]:
    """Replace local file img src with cid:...; return (html, [(cid, path), ...])."""
    inline: list[tuple[str, Path]] = []
    cid_n = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal cid_n
        pre = match.group("pre")
        src = match.group("src")
        if src.startswith(("http://", "https://", "data:", "cid:")):
            return match.group(0)
        raw = Path(src)
        resolved = raw.resolve() if raw.is_absolute() else (base_dir / raw).resolve()
        if not resolved.is_file():
            return match.group(0)
        cid = f"pgosimg{cid_n}"
        cid_n += 1
        inline.append((cid, resolved))
        return f'{match.group(1)}{pre}{match.group(3)}cid:{cid}{match.group(5)}'

    return _IMG_SRC.sub(repl, html_fragment), inline


def build_markdown_mime(
    subject: str,
    from_addr: str,
    to_addr: str,
    markdown_body: str,
    base_dir: Path,
) -> MIMEMultipart:
    """multipart/related: alternative (plain+html) + inline images for local paths."""
    try:
        import markdown as md_lib
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "发送 Markdown 邮件需要安装: pip install markdown"
        ) from exc

    html_fragment = md_lib.markdown(
        markdown_body,
        extensions=["extra", "nl2br"],
        output_format="html",
    )
    html_with_cids, inline_images = _embed_images(html_fragment, base_dir.resolve())

    plain_fallback = (
        "此邮件为 HTML 格式（含 Markdown 渲染与内嵌图片）。\n"
        "若只能看到本段文字，请换用网页版或支持 HTML 的邮箱客户端。\n\n"
        + markdown_body[:8000]
    )
    if len(markdown_body) > 8000:
        plain_fallback += "\n\n…（正文过长已截断，请见 HTML 部分）"

    wrapped_html = (
        "<!DOCTYPE html><html><head><meta charset=\"utf-8\"/>"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"/>"
        "<style>body{font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;"
        "line-height:1.55;color:#222;max-width:40em;margin:12px auto;padding:0 8px;}"
        "img{max-width:100%;height:auto;border-radius:6px;}table{border-collapse:collapse;width:100%;}"
        "th,td{border:1px solid #ddd;padding:6px 8px;}pre,code{background:#f4f4f5;border-radius:4px;}"
        "pre{padding:10px;overflow:auto;}code{padding:2px 4px;}</style></head><body>"
        f"{html_with_cids}</body></html>"
    )

    root = MIMEMultipart("related")
    root["Subject"] = subject
    root["From"] = from_addr
    root["To"] = to_addr

    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(plain_fallback, "plain", "utf-8"))
    alt.attach(MIMEText(wrapped_html, "html", "utf-8"))
    root.attach(alt)

    for cid, img_path in inline_images:
        data = img_path.read_bytes()
        sub = img_path.suffix.lower().lstrip(".") or "png"
        if sub not in ("png", "jpeg", "jpg", "gif", "webp"):
            sub = "png"
        if sub == "jpg":
            sub = "jpeg"
        mime_img = MIMEImage(data, _subtype=sub)
        mime_img.add_header("Content-ID", f"<{cid}>")
        mime_img.add_header("Content-Disposition", "inline", filename=img_path.name)
        root.attach(mime_img)

    return root
