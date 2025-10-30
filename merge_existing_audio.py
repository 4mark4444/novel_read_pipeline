#!/usr/bin/env python3
"""
Recovery script to merge existing audio files when generation was interrupted
"""

import os
import sys
import argparse
from pathlib import Path
from voice import merge_audio_files

def find_audio_files(lines_dir: Path) -> list:
    """Find all generated MP3 files in the lines directory."""
    audio_files = []

    # Look for line_XXXX.mp3 files
    for mp3_file in sorted(lines_dir.glob("line_*.mp3")):
        if mp3_file.stat().st_size > 0:  # Only include non-empty files
            audio_files.append(str(mp3_file))

    return audio_files

def main():
    parser = argparse.ArgumentParser(
        description='Merge existing audio files from an interrupted generation'
    )
    parser.add_argument('lines_dir', help='Directory containing line_XXXX.mp3 files')
    parser.add_argument('output_file', help='Output merged MP3 file')

    args = parser.parse_args()

    lines_dir = Path(args.lines_dir)
    if not lines_dir.exists():
        print(f"Error: Directory not found: {lines_dir}", file=sys.stderr)
        sys.exit(1)

    # Find all audio files
    audio_files = find_audio_files(lines_dir)

    if not audio_files:
        print(f"No audio files found in {lines_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(audio_files)} audio files", file=sys.stderr)

    # Show gaps if any
    expected_count = len(audio_files)
    if audio_files:
        # Extract line numbers
        line_numbers = []
        for f in audio_files:
            try:
                # Extract number from line_XXXX.mp3
                base = os.path.basename(f)
                num = int(base.replace('line_', '').replace('.mp3', ''))
                line_numbers.append(num)
            except:
                pass

        if line_numbers:
            line_numbers.sort()
            max_line = max(line_numbers)

            # Check for gaps
            missing = []
            for i in range(1, max_line + 1):
                if i not in line_numbers:
                    missing.append(i)

            if missing:
                print(f"⚠️  Warning: Missing {len(missing)} lines:", file=sys.stderr)
                if len(missing) <= 20:
                    print(f"   Lines: {missing}", file=sys.stderr)
                else:
                    print(f"   Lines: {missing[:10]}... and {len(missing)-10} more", file=sys.stderr)

    # Merge the files
    print(f"Merging audio files...", file=sys.stderr)
    success = merge_audio_files(audio_files, args.output_file)

    if success:
        print(f"✅ Successfully merged to: {args.output_file}", file=sys.stderr)
    else:
        print(f"❌ Merge failed", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()