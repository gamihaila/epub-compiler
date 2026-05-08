#!/usr/bin/env python3
"""
Converts ASCII quotes to Unicode curly quotes in text.

Double quotes " → " / "
Single quotes ' → ' / '  (apostrophes are handled contextually)

A quote is treated as opening when preceded by whitespace, a newline, an opening
bracket/paren, or the start of the string.  All other positions are treated as
closing (including apostrophes in contractions like "it's").

Usage:
    python curly_quotes.py <input_file> [output_file]

If no output file is specified, the result is printed to stdout.
"""

import re
import sys


# Unicode curly quote characters
OPEN_DOUBLE  = "“"   # "
CLOSE_DOUBLE = "”"   # "
OPEN_SINGLE  = "‘"   # '
CLOSE_SINGLE = "’"   # '

# Positions that indicate an *opening* quote: start-of-string, whitespace,
# opening punctuation, or a newline immediately before the quote character.
_OPEN_CONTEXT = re.compile(r'(?:^|[\s(\[{])\Z')


def convert_quotes(text: str) -> str:
    result = []
    for i, char in enumerate(text):
        if char in ('"', "'"):
            preceding = text[:i]
            if _OPEN_CONTEXT.search(preceding):
                result.append(OPEN_DOUBLE if char == '"' else OPEN_SINGLE)
            else:
                result.append(CLOSE_DOUBLE if char == '"' else CLOSE_SINGLE)
        else:
            result.append(char)
    return "".join(result)


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <input_file> [output_file]", file=sys.stderr)
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        with open(input_path, "r", encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        print(f"Error: File '{input_path}' not found.", file=sys.stderr)
        sys.exit(1)
    except UnicodeDecodeError:
        print(f"Error: Could not decode '{input_path}' as UTF-8.", file=sys.stderr)
        sys.exit(1)

    converted = convert_quotes(text)

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(converted)
        print(f"Saved to '{output_path}'.")
    else:
        print(converted)


if __name__ == "__main__":
    main()
