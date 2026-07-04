import pytest
from txt2epub import clean_text_to_html, natural_sort_key
from curly_quotes import convert_quotes


class TestCleanTextToHtml:

    def test_single_paragraph(self):
        html, has_fn = clean_text_to_html("Hello world.")
        assert html == "<p>Hello world.</p>"
        assert has_fn is False

    def test_multiple_paragraphs(self):
        text = "First paragraph.\n\nSecond paragraph."
        html, _ = clean_text_to_html(text)
        assert "<p>First paragraph.</p>" in html
        assert "<p>Second paragraph.</p>" in html

    def test_wrapped_lines_join_into_paragraph(self):
        text = "This is a long\nsentence that wraps\nacross lines."
        html, _ = clean_text_to_html(text)
        assert html == "<p>This is a long sentence that wraps across lines.</p>"

    def test_empty_input(self):
        html, has_fn = clean_text_to_html("")
        assert html == "<p>(empty chapter)</p>"
        assert has_fn is False

    def test_whitespace_only_input(self):
        html, _ = clean_text_to_html("   \n\n   \n")
        assert html == "<p>(empty chapter)</p>"

    def test_multiple_blank_lines_between_paragraphs(self):
        text = "First.\n\n\n\nSecond."
        html, _ = clean_text_to_html(text)
        assert html.count("<p>") == 2

    def test_trailing_whitespace_stripped(self):
        text = "Hello world.   \n\nNext.  "
        html, _ = clean_text_to_html(text)
        assert "   " not in html


class TestFootnotes:

    def test_single_footnote(self):
        text = "Some text[^1] here.\n\n[^1]: A footnote."
        html, has_fn = clean_text_to_html(text, "ch1")
        assert has_fn is True
        assert 'epub:type="noteref">[1]</a></sup>' in html
        assert 'id="fn-ch1-1"' in html
        assert "A footnote." in html

    def test_multiple_footnotes(self):
        text = "First[^1] and second[^2].\n\n[^1]: Note one.\n[^2]: Note two."
        html, has_fn = clean_text_to_html(text, "ch1")
        assert has_fn is True
        assert "[1]" in html
        assert "[2]" in html
        assert "Note one." in html
        assert "Note two." in html

    def test_footnote_numbering_follows_appearance_order(self):
        text = "Ref A[^2] then ref B[^1].\n\n[^1]: First defined.\n[^2]: Second defined."
        html, _ = clean_text_to_html(text, "ch1")
        pos_1 = html.index('noteref">[1]')
        pos_2 = html.index('noteref">[2]')
        assert pos_1 < pos_2
        assert "Second defined." in html  # [^2] appears first, gets number 1

    def test_footnote_backlinks(self):
        text = "Text[^1].\n\n[^1]: A note."
        html, _ = clean_text_to_html(text, "ch1")
        assert 'id="fnref-ch1-1"' in html
        assert 'href="#fn-ch1-1"' in html
        assert 'href="#fnref-ch1-1"' in html

    def test_missing_footnote_definition(self):
        text = "Text[^99]."
        html, has_fn = clean_text_to_html(text, "ch1")
        assert has_fn is True
        assert "[missing footnote: 99]" in html

    def test_duplicate_reference_same_label(self):
        text = "First[^1] and again[^1].\n\n[^1]: Shared note."
        html, has_fn = clean_text_to_html(text, "ch1")
        assert has_fn is True
        assert html.count('epub:type="noteref"') == 2
        assert html.count('epub:type="footnote"') == 1

    def test_no_footnotes_without_chapter_id(self):
        text = "Text[^1].\n\n[^1]: A note."
        html, has_fn = clean_text_to_html(text)
        assert has_fn is False
        assert "[^1]" in html

    def test_footnote_definitions_stripped_from_body(self):
        text = "Body text.\n\n[^1]: Should not appear as paragraph."
        html, _ = clean_text_to_html(text, "ch1")
        assert html.count("<p>") == 1
        assert "<p>Body text.</p>" in html

    def test_word_label_footnote(self):
        text = "Text[^note].\n\n[^note]: A named note."
        html, has_fn = clean_text_to_html(text, "ch1")
        assert has_fn is True
        assert "A named note." in html

    def test_footnote_aside_structure(self):
        text = "Text[^1].\n\n[^1]: The note."
        html, _ = clean_text_to_html(text, "ch1")
        assert '<aside class="endnote"' in html
        assert 'epub:type="footnote">' in html
        assert "</aside>" in html


class TestNaturalSortKey:

    def test_numeric_ordering(self):
        names = ["chapter_10.txt", "chapter_2.txt", "chapter_1.txt"]
        result = sorted(names, key=natural_sort_key)
        assert result == ["chapter_1.txt", "chapter_2.txt", "chapter_10.txt"]

    def test_alpha_ordering(self):
        names = ["b.txt", "a.txt", "c.txt"]
        result = sorted(names, key=natural_sort_key)
        assert result == ["a.txt", "b.txt", "c.txt"]


class TestConvertQuotes:

    def test_simple_pair(self):
        assert convert_quotes('"hello"') == "“hello”"

    def test_no_quotes(self):
        assert convert_quotes("no quotes here") == "no quotes here"

    def test_multiple_pairs(self):
        result = convert_quotes('"one" and "two"')
        assert result == "“one” and “two”"

    def test_empty_string(self):
        assert convert_quotes("") == ""
