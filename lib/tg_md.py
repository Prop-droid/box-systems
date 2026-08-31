"""Markdown -> Telegram HTML (parse_mode=HTML) for fleet bot output.

Telegram renders only a small HTML subset (b/i/s/u/code/pre/a/blockquote) and
counts the 4096-char limit AFTER entity parsing, so converting a <=4000-char
markdown chunk can never overflow. Unmatched markdown is left as escaped text.
Callers must fall back to plain text if sendMessage rejects the HTML.

CLI: python3 tg_md.py  (stdin markdown -> stdout HTML)
"""
import html
import re


def md_to_html(md: str) -> str:
    fences: list[str] = []
    spans: list[str] = []
    md = re.sub(r"```[\w+-]*\n?(.*?)```",
                lambda m: fences.append(m.group(1)) or f"\x00{len(fences)-1}\x00",
                md, flags=re.S)
    md = re.sub(r"`([^`\n]+)`",
                lambda m: spans.append(m.group(1)) or f"\x01{len(spans)-1}\x01",
                md)
    t = html.escape(md, quote=False)
    t = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2">\1</a>', t)
    t = re.sub(r"^#{1,6}\s+(.+)$", r"<b>\1</b>", t, flags=re.M)
    t = re.sub(r"^(\s*)[-*]\s+", r"\1• ", t, flags=re.M)
    t = re.sub(r"\*\*([^\n]+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"__([^\n]+?)__", r"<b>\1</b>", t)
    t = re.sub(r"(?<![\w*])\*(?!\s)([^\n*]+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", t)
    t = re.sub(r"(?<![\w_])_(?!\s)([^\n_]+?)(?<!\s)_(?![\w_])", r"<i>\1</i>", t)
    t = re.sub(r"~~([^\n]+?)~~", r"<s>\1</s>", t)
    t = re.sub(r"\x01(\d+)\x01",
               lambda m: f"<code>{html.escape(spans[int(m.group(1))], quote=False)}</code>", t)
    t = re.sub(r"\x00(\d+)\x00",
               lambda m: f"<pre>{html.escape(fences[int(m.group(1))], quote=False)}</pre>", t)
    return t


if __name__ == "__main__":
    import sys
    sys.stdout.write(md_to_html(sys.stdin.read()))
