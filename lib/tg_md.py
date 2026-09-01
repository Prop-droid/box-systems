"""Markdown -> Telegram HTML (parse_mode=HTML) for fleet bot output.

Telegram renders only a small HTML subset (b/i/s/u/code/pre/a/blockquote) and
counts the 4096-char limit AFTER entity parsing, so converting a <=4000-char
markdown chunk can never overflow. Unmatched markdown is left as escaped text.
Callers must fall back to plain text if sendMessage rejects the HTML.

CLI: python3 tg_md.py  (stdin markdown -> stdout HTML)
"""
import html
import re

# Fence tags that always mean real code (kept as <pre> boxes).
CODE_TAGS = {
    "python", "py", "bash", "sh", "shell", "zsh", "console", "js", "javascript",
    "ts", "typescript", "json", "yaml", "yml", "toml", "ini", "sql", "diff",
    "patch", "html", "css", "xml", "c", "cpp", "go", "rust", "java", "rb",
    "ruby", "php", "swift", "kotlin", "dockerfile", "makefile", "text", "txt",
}

_CODE_LINE = re.compile(
    r"^\s*(\$ |>>> |#!|#|//|sudo |git |curl |ssh |cd |ls |cat |grep |echo "
    r"|python|pip |npm |npx |node |docker |systemctl |journalctl |chmod |mkdir "
    r"|rm |mv |cp |def |class |import |from |return |if |for |while )"
    r"|[{}\[\];]{2}|[=<>!+-]=|=>|->|\|\||&&|::"
    r"|^\s*[\w.]+\s*=\s*\S|^\s{4,}\S|^[+-](?![\d\s])"
    r"|^\s*[{}\[\]();,]+\s*$|\"[\w-]+\"\s*:|'[\w-]+'\s*:"
    r"|^\s*(Traceback |File \")|\w+(Error|Exception)\b")


def _fence_is_code(tag: str, body: str) -> bool:
    if tag.lower() in CODE_TAGS:
        return True
    lines = [l for l in body.splitlines() if l.strip()]
    if not lines:
        return True
    codeish = sum(1 for l in lines if _CODE_LINE.search(l))
    return codeish / len(lines) >= 0.5


def unwrap_prose_fences(md: str) -> str:
    """Un-fence blocks that are prose/copy, not code.

    Models keep wrapping ad copy and drafts in ``` despite prompt rules; those
    render as monospace 'copy' boxes in Telegram (Tomas 2026-09-01). Genuine
    code (tagged, or majority code-shaped lines) keeps its fence.
    """
    def repl(m):
        tag, body = m.group(1), m.group(2)
        if _fence_is_code(tag, body):
            return m.group(0)
        return "\n" + body.strip("\n") + "\n"
    return re.sub(r"```([\w+-]*)[ \t]*\n?(.*?)```", repl, md, flags=re.S)


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
