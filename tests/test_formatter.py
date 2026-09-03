from __future__ import annotations

from app.formatter import markdown_to_telegram_html, split_telegram_message


class TestBold:
    def test_double_asterisk(self) -> None:
        assert markdown_to_telegram_html("Hello **world**") == "Hello <b>world</b>"

    def test_double_underscore(self) -> None:
        assert markdown_to_telegram_html("Hello __world__") == "Hello <b>world</b>"

    def test_bold_with_html_inside(self) -> None:
        result = markdown_to_telegram_html("**<b>nested</b>**")
        assert "<b>" in result
        assert "&lt;b&gt;" in result


class TestItalic:
    def test_single_asterisk(self) -> None:
        assert markdown_to_telegram_html("Hello *world*") == "Hello <i>world</i>"

    def test_single_underscore(self) -> None:
        assert markdown_to_telegram_html("Hello _world_") == "Hello <i>world</i>"

    def test_underscore_not_in_word(self) -> None:
        result = markdown_to_telegram_html("some_variable_name")
        assert "<i>" not in result


class TestStrikethrough:
    def test_double_tilde(self) -> None:
        assert markdown_to_telegram_html("Hello ~~world~~") == "Hello <s>world</s>"


class TestInlineCode:
    def test_inline_code(self) -> None:
        result = markdown_to_telegram_html("Use `pip install` here")
        assert "<code>pip install</code>" in result

    def test_code_not_bold(self) -> None:
        result = markdown_to_telegram_html("`**not bold**`")
        assert "**not bold**" in result
        assert "<b>" not in result


class TestCodeBlock:
    def test_fenced_code_block(self) -> None:
        text = "```\nprint('hello')\n```"
        result = markdown_to_telegram_html(text)
        assert "<pre>" in result
        assert "print('hello')" in result

    def test_fenced_code_block_with_language(self) -> None:
        text = "```python\nx = 1\n```"
        result = markdown_to_telegram_html(text)
        assert 'class="language-python"' in result

    def test_code_block_html_escaped(self) -> None:
        text = "```\n<div>test</div>\n```"
        result = markdown_to_telegram_html(text)
        assert "&lt;div&gt;" in result
        assert "<div>" not in result.replace("<pre>", "").replace("</pre>", "")


class TestLinks:
    def test_link(self) -> None:
        result = markdown_to_telegram_html("[click](https://example.com)")
        assert '<a href="https://example.com">click</a>' in result


class TestHeaders:
    def test_h1(self) -> None:
        result = markdown_to_telegram_html("# Title")
        assert "<b>Title</b>" in result

    def test_h3(self) -> None:
        result = markdown_to_telegram_html("### Subtitle")
        assert "<b>Subtitle</b>" in result


class TestHtmlEscaping:
    def test_escapes_angle_brackets(self) -> None:
        result = markdown_to_telegram_html("<script>alert('xss')</script>")
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_escapes_ampersand(self) -> None:
        result = markdown_to_telegram_html("Tom & Jerry")
        assert "&amp;" in result


class TestEdgeCases:
    def test_empty_string(self) -> None:
        assert markdown_to_telegram_html("") == ""

    def test_plain_text_unchanged(self) -> None:
        assert markdown_to_telegram_html("Hello world") == "Hello world"

    def test_multiple_formats(self) -> None:
        text = "**bold** and *italic* and `code`"
        result = markdown_to_telegram_html(text)
        assert "<b>bold</b>" in result
        assert "<i>italic</i>" in result
        assert "<code>code</code>" in result


class TestSplitTelegramMessage:
    def test_short_text_single_chunk(self) -> None:
        assert split_telegram_message("hello") == ["hello"]

    def test_empty_text(self) -> None:
        assert split_telegram_message("") == [""]

    def test_exact_limit(self) -> None:
        text = "x" * 4096
        assert split_telegram_message(text) == [text]

    def test_long_text_splits(self) -> None:
        text = "A" * 5000
        chunks = split_telegram_message(text)
        assert len(chunks) == 2
        assert "(1/2)" in chunks[0]
        assert "(2/2)" in chunks[1]
        for chunk in chunks:
            assert len(chunk) <= 4096

    def test_prefers_paragraph_split(self) -> None:
        text = "para1\n\npara2\n\n" + "X" * 3000
        chunks = split_telegram_message(text, limit=100)
        assert len(chunks) >= 2

    def test_splits_on_lines(self) -> None:
        lines = ["line " + str(i) for i in range(200)]
        text = "\n".join(lines)
        chunks = split_telegram_message(text, limit=500)
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk) <= 500

    def test_single_long_line_splits(self) -> None:
        text = "word " * 1000
        chunks = split_telegram_message(text, limit=200)
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk) <= 200
