from __future__ import annotations

import re
import secrets


def markdown_to_telegram_html(text: str) -> str:
    """Convert standard Markdown to Telegram-compatible HTML.

    Handles bold, italic, strikethrough, inline code, fenced code blocks,
    and links.  Falls back to the original text for anything the converter
    cannot express in Telegram HTML.
    """
    if not text:
        return text

    placeholders: dict[str, str] = {}

    def _placeholder(content: str) -> str:
        token = secrets.token_hex(8)
        key = f"\x00{token}\x00"
        placeholders[key] = content
        return key

    # Escape HTML first so any raw `<`, `>`, `&` in the input can never pass
    # through as markup.  Everything we generate below is produced from the
    # already-escaped text or stored in placeholders.
    result = _escape_html(text)

    # Fenced code blocks – protect first so inner content is never touched
    result = re.sub(
        r"```(\w*)[\n\r]+(.*?)\n*```",
        lambda m: _placeholder(
            f"<pre><code class=\"language-{m.group(1)}\">{m.group(2)}</code></pre>"
            if m.group(1)
            else f"<pre>{m.group(2)}</pre>"
        ),
        result,
        flags=re.DOTALL,
    )

    # Inline code
    result = re.sub(
        r"`([^`\n]+)`",
        lambda m: _placeholder(f"<code>{m.group(1)}</code>"),
        result,
    )

    # Bold – **text**
    result = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", result)
    result = re.sub(r"__(.+?)__", r"<b>\1</b>", result)

    # Italic – *text* or _text_
    result = re.sub(r"<b>\*(.*?)\*</b>", r"<b>\1</b>", result)  # * within bold
    result = re.sub(r"\*(.+?)\*", r"<i>\1</i>", result)
    result = re.sub(r"(?<!\w)_(.+?)_(?!\w)", r"<i>\1</i>", result)

    # Strikethrough – ~~text~~
    result = re.sub(r"~~(.+?)~~", r"<s>\1</s>", result)

    # Links – [text](url)
    result = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', result)

    # Headers – convert to bold since Telegram HTML has no heading tags
    result = re.sub(r"^#{1,6}\s+(.+)$", r"<b>\1</b>", result, flags=re.MULTILINE)

    # Restore placeholders (their content was escaped above)
    for key, value in placeholders.items():
        result = result.replace(key, value)

    return result


def _escape_html(text: str) -> str:
    """Escape characters that are special in HTML."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
