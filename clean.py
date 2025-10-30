#!/usr/bin/env python3
"""
Text cleaner wrapper - Uses existing data_cleaner to clean novel text
"""

import sys
import os
import json
from pathlib import Path

# Add parent directory to path to import from new_function
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from new_function.data_cleaner import NovelTextCleaner


def detect_encoding(file_path: str) -> str:
    """Detect file encoding."""
    encodings = ['utf-8', 'utf-16-le', 'utf-16-be', 'utf-16', 'gbk', 'gb18030', 'big5']

    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                f.read(1000)
            return encoding
        except (UnicodeDecodeError, UnicodeError):
            continue

    return 'utf-8'  # fallback


def clean_text_file(input_file: str, output_file: str = None):
    """
    Clean a text file using the NovelTextCleaner.

    Args:
        input_file: Path to input text file
        output_file: Path to output cleaned text file (optional)
    """
    # Initialize cleaner with all features enabled
    cleaner = NovelTextCleaner(
        separate_dialogue=True,
        remove_annotations=True,
        remove_empty_lines=True
    )

    # Detect encoding
    encoding = detect_encoding(input_file)
    print(f"Detected encoding: {encoding}", file=sys.stderr)

    # Process file
    cleaned_lines = []
    line_count = 0

    with open(input_file, 'r', encoding=encoding) as f:
        for line in f:
            line = line.strip()

            # Skip metadata lines
            if line.startswith('&&&&&&'):
                continue

            # Clean the line
            cleaned = cleaner.clean_line(line)

            # Add non-empty cleaned lines
            for clean_line in cleaned:
                if clean_line:
                    cleaned_lines.append(clean_line)
                    line_count += 1

    print(f"Cleaned {line_count} lines", file=sys.stderr)

    # Output
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            for line in cleaned_lines:
                f.write(line + '\n')
        print(f"Saved to: {output_file}", file=sys.stderr)
    else:
        # Output to stdout for piping
        for line in cleaned_lines:
            print(line)

    return cleaned_lines


def main():
    if len(sys.argv) < 2:
        print("Usage: python clean.py <input_file> [output_file]")
        print("  If output_file not specified, outputs to stdout")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    if not os.path.exists(input_file):
        print(f"Error: Input file not found: {input_file}", file=sys.stderr)
        sys.exit(1)

    clean_text_file(input_file, output_file)


if __name__ == "__main__":
    main()