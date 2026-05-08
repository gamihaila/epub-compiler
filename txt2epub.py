#!/usr/bin/env python3
"""
txt2epub.py - Flexible EPUB creator with optional contents.yaml

Usage:
    python txt2epub.py /path/to/folder [--title "Fallback Title"] [--author "Fallback Author"]

If contents.yaml exists in the folder, it is used for structure and metadata.
Otherwise falls back to sorting chapter_*.txt files.
"""

import argparse
import html
import re
import sys
import uuid
from pathlib import Path

import yaml

from ebooklib import epub
from curly_quotes import convert_quotes


def natural_sort_key(s: str) -> list:
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', s)]


def clean_text_to_html(text: str, chapter_id: str = "") -> tuple:
    """Convert txt → HTML paragraphs, handling inline footnotes.

    Inline footnotes use the syntax: [^ footnote text here]
    They are auto-numbered in order of appearance and placed at the
    bottom of the chapter as <aside epub:type="footnote"> elements.

    Footnote text cannot contain ']' characters.

    Returns (html_str, has_footnotes) where has_footnotes is a bool.
    """
    lines = [line.rstrip() for line in text.splitlines()]
    paragraphs = []
    current = []

    for line in lines:
        if line.strip() == "":
            if current:
                paragraphs.append(" ".join(current).strip())
                current = []
        else:
            current.append(line)

    if current:
        paragraphs.append(" ".join(current).strip())

    html_str = "\n".join(f"<p>{html.escape(p)}</p>" for p in paragraphs if p)

    # Extract inline footnotes [^ ...] and replace with auto-numbered superscripts.
    # Note: footnote text must not contain ']' — the pattern stops at the first ']'.
    footnotes = []
    counter = 0

    def replace_footnote(m):
        nonlocal counter
        counter += 1
        n = counter
        footnotes.append((n, html.escape(m.group(1).strip())))
        return (f'<sup><a id="fnref-{chapter_id}-{n}" '
                f'href="#fn-{chapter_id}-{n}" '
                f'epub:type="noteref">[{n}]</a></sup>')

    if chapter_id:
        html_str = re.sub(r'\[\^\s*([^\]]+?)\s*\]', replace_footnote, html_str)

    # Append footnote asides at the bottom of the chapter
    if footnotes:
        footnote_parts = []
        for n, text in footnotes:
            footnote_parts.append(
                f'<aside class="endnote" id="fn-{chapter_id}-{n}" epub:type="footnote">'
                f'<p><a href="#fnref-{chapter_id}-{n}">[{n}]</a> '
                f'{text}</p></aside>'
            )
        html_str += "\n" + "\n".join(footnote_parts)

    return (html_str or "<p>(empty chapter)</p>"), bool(footnotes)


def build_chapter(txt_path: Path, chap_title: str, epub_filename: str,
                  chapter_id: str, lang: str, nav_css: epub.EpubItem) -> epub.EpubHtml:
    """Read a text file and return a fully configured EpubHtml chapter item."""
    with open(txt_path, encoding="utf-8") as f:
        content = convert_quotes(f.read())

    body_html, has_footnotes = clean_text_to_html(content, chapter_id)

    xmlns_epub = ' xmlns:epub="http://www.idpf.org/2007/ops"' if has_footnotes else ''
    safe_title = html.escape(chap_title)

    chapter = epub.EpubHtml(title=chap_title, file_name=epub_filename, lang=lang)
    chapter.content = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml"{xmlns_epub} lang="{lang}">
<head>
    <meta charset="utf-8" />
    <title>{safe_title}</title>
    <link rel="stylesheet" type="text/css" href="../style/nav.css" />
</head>
<body>
    <h1>{safe_title}</h1>
{body_html}
</body>
</html>""".encode("utf-8")

    return chapter


def main():
    parser = argparse.ArgumentParser(description="Convert text files to EPUB with optional contents.yaml")
    parser.add_argument("folder", help="Folder containing text files and optional contents.yaml")
    parser.add_argument("--title", default="Untitled Book", help="Fallback title if no contents.yaml")
    parser.add_argument("--author", default="Anonymous", help="Fallback author")
    parser.add_argument("--output", "-o", help="Output EPUB filename")
    parser.add_argument("--lang", default="en", help="Fallback language")

    args = parser.parse_args()
    folder = Path(args.folder).expanduser().resolve()

    if not folder.is_dir():
        print(f"Error: Not a directory → {folder}", file=sys.stderr)
        return 1

    config_path = folder / "contents.yaml"
    use_config = config_path.is_file()

    if use_config:
        try:
            with open(config_path, encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
            print("Using contents.yaml for book structure")
        except Exception as e:
            print(f"Error reading contents.yaml: {e}", file=sys.stderr)
            return 1
    else:
        print("No contents.yaml found → falling back to sorted chapter_*.txt files")
        config = {}

    # ── Prepare book ─────────────────────────────────────────────────────────────
    book = epub.EpubBook()

    # Metadata
    title = config.get("title", args.title)
    author = config.get("author", args.author)
    lang = config.get("language", args.lang)

    book.set_identifier(str(uuid.uuid4()))
    book.set_title(title)
    book.set_language(lang)
    book.add_author(author)

    # Optional cover
    cover_path = config.get("cover")
    if cover_path:
        cover_file = folder / cover_path
        if cover_file.is_file():
            book.set_cover(cover_path, cover_file.read_bytes())
            print(f"Added cover: {cover_path}")
        else:
            print(f"Warning: cover file not found → {cover_file}", file=sys.stderr)

    # ── CSS ───────────────────────────────────────────────────────────────────────
    style = """
    body { margin: 5%; font-family: Georgia, serif; line-height: 1.6; }
    h1 { text-align: center; margin: 1.5em 0; }
    p { margin: 1em 0; text-indent: 1.2em; }
    sup a { text-decoration: none; color: #0066cc; }
    .endnote { margin: 0.5em 0; text-indent: 0; }
    """
    nav_css = epub.EpubItem(
        uid="style_nav",
        file_name="style/nav.css",
        media_type="text/css",
        content=style.encode("utf-8")
    )
    book.add_item(nav_css)

    # ── Load chapters ────────────────────────────────────────────────────────────
    chapters = []
    toc_links = []

    if use_config:
        chapter_list = config.get("chapters", [])
        if not chapter_list:
            print("Error: contents.yaml has no 'chapters' list", file=sys.stderr)
            return 1

        for entry in chapter_list:
            filename = entry.get("file")
            chap_title = entry.get("title") or f"Untitled ({filename})"

            if not filename:
                print(f"Skipping entry with no file: {entry}")
                continue

            txt_path = folder / filename
            if not txt_path.is_file():
                print(f"File not found, skipping: {txt_path}")
                continue

            safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', Path(filename).stem)
            epub_filename = f"content/{safe_name}.xhtml"
            chapter_id = f"chap_{len(chapters) + 1}"

            chapter = build_chapter(txt_path, chap_title, epub_filename, chapter_id, lang, nav_css)
            book.add_item(chapter)
            chapters.append(chapter)
            toc_links.append(epub.Link(epub_filename, chap_title, chapter_id))

    else:
        # Fallback: sorted chapter_*.txt
        txt_files = sorted(
            [f for f in folder.glob("*.txt") if f.name.startswith("chapter_")],
            key=lambda p: natural_sort_key(p.name)
        )

        if not txt_files:
            print("No chapter_*.txt files found.", file=sys.stderr)
            return 1

        for i, txt_path in enumerate(txt_files, 1):
            chap_title = f"Chapter {i}"
            epub_filename = f"content/chapter_{i}.xhtml"
            chapter_id = f"chap_{i}"

            chapter = build_chapter(txt_path, chap_title, epub_filename, chapter_id, lang, nav_css)
            book.add_item(chapter)
            chapters.append(chapter)
            toc_links.append(epub.Link(epub_filename, chap_title, chapter_id))

    # ── Finalize book ────────────────────────────────────────────────────────────
    book.toc = tuple(toc_links)
    book.spine = ["nav"] + chapters

    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # Output
    if args.output:
        epub_path = Path(args.output).resolve()
    else:
        safe_title = "".join(c for c in title if c.isalnum() or c in " -_").strip() or "book"
        epub_path = folder.parent / f"{safe_title}.epub"

    epub.write_epub(str(epub_path), book)
    print(f"EPUB created:\n  → {epub_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
