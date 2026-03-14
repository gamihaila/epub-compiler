#!/usr/bin/env python3
"""
txt2epub.py - Flexible EPUB creator with optional contents.yaml

Usage:
    python txt2epub.py /path/to/folder [--title "Fallback Title"] [--author "Fallback Author"]

If contents.yaml exists in the folder, it is used for structure and metadata.
Otherwise falls back to sorting chapter_*.txt files.
"""

import argparse
import os
import re
from pathlib import Path
import datetime

import yaml

from ebooklib import epub


def natural_sort_key(s: str) -> tuple:
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', s)]


def clean_text_to_html(text: str) -> str:
    """Very basic txt → HTML paragraphs"""
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

    html = "\n".join(f"<p>{p}</p>" for p in paragraphs if p)
    return html or "<p>(empty chapter)</p>"


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
        print(f"Error: Not a directory → {folder}")
        return 1

    config_path = folder / "contents.yaml"
    use_config = config_path.is_file()

    if use_config:
        try:
            with open(config_path, encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
            print("Using contents.yaml for book structure")
        except Exception as e:
            print(f"Error reading contents.yaml: {e}")
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

    book.set_identifier(f"book-{title.lower().replace(' ','-')}-{datetime.date.today().year}")
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
            print(f"Warning: cover file not found → {cover_file}")

    # ── Load chapters ────────────────────────────────────────────────────────────
    chapters = []
    toc_links = []

    if use_config:
        chapter_list = config.get("chapters", [])
        if not chapter_list:
            print("Error: contents.yaml has no 'chapters' list")
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

            with open(txt_path, encoding="utf-8") as f:
                content = f.read()

            body_html = clean_text_to_html(content)

            # Sanitized filename for EPUB
            safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', Path(filename).stem)
            epub_filename = f"content/{safe_name}.xhtml"

            chapter = epub.EpubHtml(title=chap_title, file_name=epub_filename, lang=lang)
            chapter.content = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" lang="{lang}">
<head>
    <meta charset="utf-8" />
    <title>{chap_title}</title>
</head>
<body>
    <h1>{chap_title}</h1>
{body_html}
</body>
</html>""".encode("utf-8")

            book.add_item(chapter)
            chapters.append(chapter)
            toc_links.append(epub.Link(epub_filename, chap_title, f"chap_{len(chapters)}"))

    else:
        # Fallback: sorted chapter_*.txt
        txt_files = sorted(
            [f for f in folder.glob("*.txt") if f.name.startswith("chapter_")],
            key=lambda p: natural_sort_key(p.name)
        )

        if not txt_files:
            print("No chapter_*.txt files found.")
            return 1

        for i, txt_path in enumerate(txt_files, 1):
            with open(txt_path, encoding="utf-8") as f:
                content = f.read()

            chap_title = f"Chapter {i}"
            body_html = clean_text_to_html(content)

            epub_filename = f"content/chapter_{i}.xhtml"

            chapter = epub.EpubHtml(title=chap_title, file_name=epub_filename, lang=lang)
            chapter.content = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" lang="{lang}">
<head>
    <meta charset="utf-8" />
    <title>{chap_title}</title>
</head>
<body>
    <h1>{chap_title}</h1>
{body_html}
</body>
</html>""".encode("utf-8")

            book.add_item(chapter)
            chapters.append(chapter)
            toc_links.append(epub.Link(epub_filename, chap_title, f"chap_{i}"))

    # ── Finalize book ────────────────────────────────────────────────────────────
    book.toc = tuple(toc_links)
    book.spine = ["nav"] + chapters

    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # Minimal CSS
    style = """
    body { margin: 5%; font-family: Georgia, serif; line-height: 1.6; }
    h1 { text-align: center; margin: 1.5em 0; }
    p { margin: 1em 0; text-indent: 1.2em; }
    """
    nav_css = epub.EpubItem(
        uid="style_nav",
        file_name="style/nav.css",
        media_type="text/css",
        content=style.encode("utf-8")
    )
    book.add_item(nav_css)

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
    import sys
    sys.exit(main())
    
