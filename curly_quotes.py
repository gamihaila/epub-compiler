#!/usr/bin/env python3
"""
Converts ASCII double quotes (") to Unicode curly quotes (" and ")
in a text file. The first quote opens a section, the next closes it,
alternating from there.

Usage:
    python curly_quotes.py <input_file> [output_file]

If no output file is specified, the result is printed to stdout.
"""

import sys


OPEN_QUOTE = "\u201C"   # "
CLOSE_QUOTE = "\u201D"  # "


def convert_quotes(text: str) -> str:
    result = []
    opening = True  # First quote is always an open quote

    for char in text:
        if char == '"':
            result.append(OPEN_QUOTE if opening else CLOSE_QUOTE)
            opening = not opening
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
