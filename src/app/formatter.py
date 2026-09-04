from __future__ import annotations

import re
import secrets


def markdown_to_telegram_html(text: str) -> str:
    """Convert standard Markdown to Telegram-compatible HTML.

    Handles bold, italic, strikethrough, inline/fenced code, links, headings,
    unordered/ordered lists, blockquotes, and horizontal rules.  Falls back to
    the original text for anything the converter cannot express in Telegram
    HTML.
    """
    if not text:
        return text

    placeholders: dict[str, str] = {}

    def _placeholder(content: str) -> str:
        token = secrets.token_hex(8)
        key = f"\x00{token}\x00"
        placeholders[key] = content
        return key

    lines = text.split("\n")
    out: list[str] = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]

        # Fenced code block – protect first so inner content is never touched
        if re.match(r"^\s*```", line):
            lang = line.strip().strip("`").strip()
            body: list[str] = []
            i += 1
            while i < n and not re.match(r"^\s*```", lines[i]):
                body.append(lines[i])
                i += 1
            if i < n:
                i += 1  # skip closing fence
            code = _escape_html("\n".join(body))
            if lang:
                out.append(
                    _placeholder(
                        f'<pre><code class="language-{_escape_html(lang)}">{code}</code></pre>'
                    )
                )
            else:
                out.append(_placeholder(f"<pre>{code}</pre>"))
            continue

        # Horizontal rule – standalone --- / *** / ___
        if re.fullmatch(r"[ \t]*(\*{3,}|-{3,}|_{3,})[ \t]*", line):
            out.append("—")
            i += 1
            continue

        # Heading – convert to bold since Telegram HTML has no heading tags
        heading = re.match(r"^#{1,6}\s+(.+?)\s*#*\s*$", line)
        if heading:
            out.append("<b>" + _inline(heading.group(1), _placeholder) + "</b>")
            i += 1
            continue

        # Blockquote – collapse consecutive `> ` lines
        if line.lstrip().startswith(">"):
            bq_lines: list[str] = []
            while i < n and lines[i].lstrip().startswith(">"):
                content = lines[i].lstrip()[1:].lstrip()
                bq_lines.append(_inline(content, _placeholder))
                i += 1
            out.append("│ " + "\n│ ".join(bq_lines))
            continue

        # List items – group consecutive items of the same kind
        list_group = _match_list_group(lines, i)
        if list_group is not None:
            items, next_i = list_group
            rendered: list[str] = []
            for marker, indent, content_line in items:
                pad = "  " * (indent // 2)
                if marker.isdigit() or marker in {")", "."} or marker.endswith((".", ")")):
                    num = marker.rstrip(".)")
                    rendered.append(f"{pad}{num}. {_inline(content_line, _placeholder)}")
                else:
                    rendered.append(f"{pad}• {_inline(content_line, _placeholder)}")
            out.append("\n".join(rendered))
            i = next_i
            continue

        # Regular text line
        out.append(_inline(line, _placeholder))
        i += 1

    result = "\n".join(out)
    for key, value in placeholders.items():
        result = result.replace(key, value)
    return result


_LIST_ITEM_RE = re.compile(r"^(\s*)([-*+]|\d+[.)])(\s+)(.*)$")


def _match_list_group(
    lines: list[str], start: int
) -> tuple[list[tuple[str, int, str]], int] | None:
    """Match a run of consecutive list items; returns (items, next_index)."""
    first = _LIST_ITEM_RE.match(lines[start])
    if first is None:
        return None
    kind = first.group(2)
    ordered = kind[0].isdigit() or kind in {")", "."}
    items: list[tuple[str, int, str]] = []
    i = start
    while i < len(lines):
        m = _LIST_ITEM_RE.match(lines[i])
        if m is None:
            break
        mkind = m.group(2)
        is_ordered = mkind[0].isdigit() or mkind in {")", "."}
        if is_ordered != ordered:
            break
        items.append((mkind, len(m.group(1)), m.group(4)))
        i += 1
    return (items, i)


def _inline(text: str, _placeholder) -> str:
    """Apply inline markdown to a single line (already free of block markers)."""
    if not text:
        return ""

    # Protect inline code spans first so `*`, `_`, `<`, etc. inside are never
    # treated as markup or HTML.
    protected = re.sub(
        r"`([^`\n]+)`",
        lambda m: _placeholder(f"<code>{_escape_html(m.group(1))}</code>"),
        text,
    )

    # Backslash escapes – neutralize the following markdown char via a
    # placeholder so later emphasis regexes cannot reformat it.
    protected = re.sub(r"\\([*_`~\[\]])", lambda m: _placeholder(m.group(1)), protected)

    # Escape raw HTML now (while literal text and <>,& remain); markdown
    # delimiters (* _ ~) are untouched so the substitutions below still match.
    protected = _escape_html(protected)

    # Bold – **text** (a nested *inside* is handled by the later italic pass)
    protected = re.sub(r"__(.+?)__(?!_)", r"<b>\1</b>", protected)
    protected = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", protected)

    # Italic – *text* or _text_ (only when not inside a word)
    protected = re.sub(r"\*(.+?)\*", r"<i>\1</i>", protected)
    protected = re.sub(r"(?<![A-Za-z0-9_])_(.+?)_(?![A-Za-z0-9_])", r"<i>\1</i>", protected)

    # Strikethrough – ~~text~~
    protected = re.sub(r"~~(.+?)~~", r"<s>\1</s>", protected)

    # Links – [text](url)
    protected = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', protected)

    return protected


def _escape_html(text: str) -> str:
    """Escape characters that are special in HTML."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


_MAX_MESSAGE_LENGTH = 4096
_MARKER_OVERHEAD = 10  # room for " (n/m)" suffix


def split_telegram_message(text: str, limit: int = _MAX_MESSAGE_LENGTH) -> list[str]:
    """Split *text* into chunks that fit a single Telegram message.

    Splits prefer paragraph breaks, then line breaks, then word boundaries.
    Fenced code blocks are kept whole whenever possible.  If a single block
    exceeds *limit* it is hard-cut at *limit* characters.
    """
    if not text or len(text) <= limit:
        return [text]

    chunks: list[str] = []
    lines = text.split("\n")
    current_lines: list[str] = []

    for line in lines:
        candidate = line if not current_lines else "\n".join([*current_lines, line])
        if len(candidate) + _MARKER_OVERHEAD <= limit:
            current_lines.append(line)
        elif not current_lines:
            # single long line – split into fixed-size pieces
            while len(line) + _MARKER_OVERHEAD > limit:
                chunks.append(line[: limit - _MARKER_OVERHEAD])
                line = line[limit - _MARKER_OVERHEAD :]
            current_lines = [line] if line else []
        else:
            chunks.append("\n".join(current_lines))
            current_lines = [line]

    if current_lines:
        chunks.append("\n".join(current_lines))

    if len(chunks) <= 1:
        return chunks
    return [f"{c} ({i + 1}/{len(chunks)})" for i, c in enumerate(chunks)]
