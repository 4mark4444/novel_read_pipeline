#!/usr/bin/env python3
"""
Voice synthesis with hallucination handling
Takes character assignments and generates audio with proper voice mapping
Handles unmapped characters (AI hallucinations) gracefully
"""

import os
import sys
import json
import asyncio
import argparse
import tempfile
import subprocess
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
import edge_tts
from tqdm import tqdm

# Configuration
DEFAULT_PAUSE = 0.5
MAX_RETRIES = 10  # Increased for aggressive retry
MAX_CONCURRENT = 3
BASE_DELAY = 1.0  # Base delay for exponential backoff
TIMEOUT_PER_LINE = 30  # Timeout in seconds for each line


def is_silence_line(text: str) -> bool:
    """Check if a line represents silence/pause (ellipsis only)."""
    # Remove quotes and whitespace
    cleaned = text.strip()
    for quote in ['「', '」', '"', '"', '『', '』', ''', ''', '【', '】', '(', ')', '（', '）']:
        cleaned = cleaned.replace(quote, '')

    cleaned = cleaned.strip()

    # Check if it's empty after removing quotes
    if not cleaned:
        return False

    # Check if it contains only ellipsis/dots/dashes
    # Common patterns: …, ., -, ー, ～, 。
    silence_chars = set('…．.・‥―—－ー～~。、')

    # Check if all characters are silence indicators
    return all(c in silence_chars or c.isspace() for c in cleaned)


def calculate_silence_duration(text: str) -> float:
    """Calculate silence duration based on the number of ellipsis/dots."""
    # Count ellipsis and dot characters
    ellipsis_count = text.count('…') + text.count('．') + text.count('.')

    # Base duration of 1 second, plus 0.2 seconds per ellipsis
    # Cap at 3 seconds maximum
    duration = min(1.0 + (ellipsis_count * 0.2), 3.0)

    return duration


async def generate_silence_audio(output_file: str, duration: float) -> bool:
    """Generate a silence audio file using ffmpeg."""
    try:
        cmd = [
            'ffmpeg',
            '-f', 'lavfi',
            '-i', f'anullsrc=r=44100:cl=mono',
            '-t', str(duration),
            '-q:a', '9',
            '-acodec', 'mp3',
            '-y',
            output_file
        ]

        # Run ffmpeg asynchronously
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )

        await process.communicate()

        # Verify file was created
        return os.path.exists(output_file) and os.path.getsize(output_file) > 0

    except Exception as e:
        print(f"Error generating silence: {e}", file=sys.stderr)
        return False


def load_voice_mapping(mapping_file: str) -> Dict[str, str]:
    """Load voice mapping from JSON file."""
    with open(mapping_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_assignments(assignment_file: str) -> List[Dict]:
    """Load character assignments from JSON file."""
    with open(assignment_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def find_unmapped_characters(assignments: List[Dict], voice_mapping: Dict[str, str]) -> Set[str]:
    """Find characters that don't have voice mappings (AI hallucinations)."""
    unmapped = set()
    for item in assignments:
        character = item.get('character', '')
        if character and character not in voice_mapping:
            unmapped.add(character)
    return unmapped


def handle_unmapped_characters(unmapped: Set[str]) -> Dict[str, str]:
    """Handle unmapped characters by prompting user for voice selection."""
    if not unmapped:
        return {}

    print("\n" + "="*60, file=sys.stderr)
    print("WARNING: Found unmapped characters (AI hallucinations):", file=sys.stderr)
    print("="*60, file=sys.stderr)

    for char in unmapped:
        print(f"  - {char}", file=sys.stderr)

    print("\nOptions:", file=sys.stderr)
    print("1. Add voice mappings for these characters", file=sys.stderr)
    print("2. Skip these lines (will create incomplete audio)", file=sys.stderr)
    print("3. Abort", file=sys.stderr)

    choice = input("\nChoice (1/2/3): ").strip()

    if choice == "1":
        # Simple voice selection for unmapped characters
        VOICES = [
            'zh-CN-XiaoxiaoNeural',   # 1 Female
            'zh-CN-XiaohanNeural',    # 2 Female
            'zh-CN-XiaomoNeural',     # 3 Female
            'zh-CN-XiaoyanNeural',    # 4 Female
            'zh-CN-YunfengNeural',    # 5 Male
            'zh-CN-YunjieNeural',     # 6 Male
        ]

        print("\nAvailable voices:", file=sys.stderr)
        for i, voice in enumerate(VOICES, 1):
            gender = "Female" if i <= 4 else "Male"
            print(f"{i}. {voice} ({gender})", file=sys.stderr)

        new_mapping = {}
        for char in unmapped:
            print(f"\nSelect voice for '{char}' (1-6): ", end='', file=sys.stderr)
            try:
                idx = int(input().strip()) - 1
                if 0 <= idx < len(VOICES):
                    new_mapping[char] = VOICES[idx]
                else:
                    new_mapping[char] = VOICES[0]  # Default
            except:
                new_mapping[char] = VOICES[0]  # Default

        return new_mapping

    elif choice == "2":
        print("Skipping unmapped characters...", file=sys.stderr)
        return {}
    else:
        print("Aborting...", file=sys.stderr)
        sys.exit(1)


async def generate_line_audio(text: str, voice: str, output_file: str,
                              semaphore: asyncio.Semaphore, line_id: int = 0) -> bool:
    """Generate audio for a single line with aggressive retry and timeout."""
    async with semaphore:
        # Check if this is a silence line first
        if is_silence_line(text):
            duration = calculate_silence_duration(text)
            print(f"Line {line_id}: Detected as silence ({duration:.1f}s)", file=sys.stderr)

            # Generate silence audio
            success = await generate_silence_audio(output_file, duration)
            if success:
                return True
            else:
                print(f"Line {line_id}: Failed to generate silence audio", file=sys.stderr)
                return False

        # Clean text for TTS
        text = text.strip()

        # Remove quotes
        for quote in ['「', '」', '"', '"', '『', '』', ''', ''', '【', '】']:
            text = text.replace(quote, '')

        if not text:
            return False
        for attempt in range(MAX_RETRIES):
            try:
                # Create communicate object
                communicate = edge_tts.Communicate(text, voice)

                # Apply timeout to the save operation
                await asyncio.wait_for(
                    communicate.save(output_file),
                    timeout=TIMEOUT_PER_LINE
                )

                # Verify file exists and has content
                if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                    if attempt > 0:
                        print(f"Line {line_id}: Success after {attempt + 1} attempts", file=sys.stderr)
                    return True
                else:
                    print(f"Line {line_id}: Attempt {attempt + 1} - File created but empty", file=sys.stderr)
                    if os.path.exists(output_file):
                        os.remove(output_file)

            except asyncio.TimeoutError:
                print(f"Line {line_id}: Attempt {attempt + 1} - Timeout after {TIMEOUT_PER_LINE}s", file=sys.stderr)
                if os.path.exists(output_file):
                    os.remove(output_file)

            except Exception as e:
                print(f"Line {line_id}: Attempt {attempt + 1} - Error: {e}", file=sys.stderr)

                # Log detailed info on first failure
                if attempt == 0:
                    print(f"Line {line_id}: FULL TEXT: {text}", file=sys.stderr)
                    print(f"Line {line_id}: Text length: {len(text)} characters", file=sys.stderr)
                    print(f"Line {line_id}: Text repr: {repr(text)}", file=sys.stderr)

                if os.path.exists(output_file):
                    os.remove(output_file)

            # Exponential backoff with max delay of 30 seconds
            if attempt < MAX_RETRIES - 1:
                delay = min(BASE_DELAY * (2 ** attempt), 30)
                print(f"Line {line_id}: Waiting {delay:.1f}s before retry {attempt + 2}/{MAX_RETRIES}...", file=sys.stderr)
                await asyncio.sleep(delay)

                # Force a small delay to allow connection reset
                await asyncio.sleep(0.5)

    print(f"Line {line_id}: Failed after {MAX_RETRIES} attempts - THIS SHOULD NOT HAPPEN!", file=sys.stderr)
    return False


async def generate_all_audio(assignments: List[Dict], voice_mapping: Dict[str, str],
                             lines_dir: Path) -> List[str]:
    """Generate audio for all lines."""
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    audio_files = []

    # Create tasks and track line info for potential failures
    tasks = []
    line_info_map = {}  # Map line_id to full assignment info

    for i, item in enumerate(assignments):
        line_id = i + 1
        text = item.get('text', '')
        character = item.get('character', '')

        # Store full info for potential failure reporting
        line_info_map[line_id] = {
            'id': line_id,
            'text': text,
            'character': character
        }

        if character in voice_mapping:
            voice = voice_mapping[character]
            output_file = lines_dir / f"line_{line_id:04d}.mp3"

            # Skip if already exists
            if output_file.exists() and output_file.stat().st_size > 0:
                audio_files.append(str(output_file))
                continue

            task = generate_line_audio(text, voice, str(output_file), semaphore, line_id)
            tasks.append((line_id, task, str(output_file)))

    # Process with progress bar
    if tasks:
        print(f"Generating {len(tasks)} audio files...", file=sys.stderr)
        failed_count = 0
        failed_lines_info = []  # Collect detailed info about failed lines

        with tqdm(total=len(tasks), desc="Generating audio", file=sys.stderr) as pbar:
            for line_id, task, output_file in tasks:
                success = await task
                if success:
                    audio_files.append(output_file)
                else:
                    failed_count += 1
                    # Collect failed line info for detailed reporting
                    failed_lines_info.append(line_info_map[line_id])
                    print(f"\n⚠️ WARNING: Line {line_id} failed permanently after {MAX_RETRIES} retries!\n", file=sys.stderr)

                # Update progress bar with status
                pbar.set_postfix({'failed': failed_count})
                pbar.update(1)

        if failed_count > 0:
            print(f"\n⚠️ {failed_count} lines failed to generate audio after {MAX_RETRIES} attempts each!", file=sys.stderr)
            print("This should not happen - please check network connectivity and try again.", file=sys.stderr)

            # Print detailed failure report
            print("\n" + "="*80, file=sys.stderr)
            print("FAILED LINES DETAILS:", file=sys.stderr)
            print("="*80, file=sys.stderr)
            for info in failed_lines_info:
                print(f"\nLine {info['id']} (Character: {info['character']}):", file=sys.stderr)
                print(f"FULL TEXT: {info['text']}", file=sys.stderr)
                print(f"Text length: {len(info['text'])} characters", file=sys.stderr)
                print("-"*40, file=sys.stderr)
            print("="*80 + "\n", file=sys.stderr)

    # Return sorted list
    return sorted(audio_files)


def merge_audio_files(audio_files: List[str], output_file: str) -> bool:
    """Merge individual audio files into one."""
    if not audio_files:
        print("No audio files to merge", file=sys.stderr)
        return False

    try:
        # Create file list for ffmpeg
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            list_file = f.name
            for audio_file in audio_files:
                # Convert to absolute path to avoid path resolution issues
                abs_path = os.path.abspath(audio_file)
                f.write(f"file '{abs_path}'\n")
                f.write(f"duration {DEFAULT_PAUSE}\n")  # Add pause

        # Merge using ffmpeg
        cmd = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-i', list_file,
            '-c', 'copy',
            '-y',
            output_file
        ]

        print(f"Merging {len(audio_files)} files...", file=sys.stderr)

        # Debug: Show first few files being merged
        if len(audio_files) > 0:
            print(f"  First file: {os.path.abspath(audio_files[0])}", file=sys.stderr)
            if len(audio_files) > 1:
                print(f"  Last file: {os.path.abspath(audio_files[-1])}", file=sys.stderr)

        result = subprocess.run(cmd, capture_output=True, text=True)

        # Clean up temp file regardless of success
        if os.path.exists(list_file):
            os.unlink(list_file)

        if result.returncode == 0:
            # Verify output file exists and has content
            if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                output_size_mb = os.path.getsize(output_file) / (1024 * 1024)
                print(f"✓ Audio saved to: {output_file} ({output_size_mb:.1f} MB)", file=sys.stderr)
                return True
            else:
                print(f"Error: Output file not created or empty", file=sys.stderr)
                return False
        else:
            print(f"FFmpeg merge failed!", file=sys.stderr)
            print(f"Command: {' '.join(cmd)}", file=sys.stderr)
            if result.stderr:
                # Show only the last few lines of error for clarity
                error_lines = result.stderr.strip().split('\n')
                relevant_errors = [line for line in error_lines if 'Error' in line or 'Impossible' in line]
                if relevant_errors:
                    print("Relevant errors:", file=sys.stderr)
                    for error in relevant_errors[-5:]:  # Show last 5 error lines
                        print(f"  {error}", file=sys.stderr)
                else:
                    print(f"Full stderr: {result.stderr[-500:]}", file=sys.stderr)  # Last 500 chars
            return False

    except Exception as e:
        print(f"Error merging audio: {e}", file=sys.stderr)
        return False


async def main_async():
    parser = argparse.ArgumentParser(
        description='Voice synthesis with hallucination handling'
    )
    parser.add_argument('assignment_file', help='Character assignment JSON file')
    parser.add_argument('voice_mapping', help='Voice mapping JSON file')
    parser.add_argument('--output', required=True, help='Output audio file')
    parser.add_argument('--lines-dir', help='Directory for individual line audio files')

    args = parser.parse_args()

    # Load files
    assignments = load_assignments(args.assignment_file)
    voice_mapping = load_voice_mapping(args.voice_mapping)

    print(f"Loaded {len(assignments)} lines", file=sys.stderr)
    print(f"Loaded {len(voice_mapping)} voice mappings", file=sys.stderr)

    # Find unmapped characters (hallucinations)
    unmapped = find_unmapped_characters(assignments, voice_mapping)

    if unmapped:
        new_mapping = handle_unmapped_characters(unmapped)
        voice_mapping.update(new_mapping)

        # Save updated mapping
        if new_mapping:
            updated_file = args.voice_mapping.replace('.json', '_updated.json')
            with open(updated_file, 'w', encoding='utf-8') as f:
                json.dump(voice_mapping, f, ensure_ascii=False, indent=2)
            print(f"Updated voice mapping saved to: {updated_file}", file=sys.stderr)

    # Create lines directory
    if args.lines_dir:
        lines_dir = Path(args.lines_dir)
    else:
        output_path = Path(args.output)
        lines_dir = output_path.parent / f"{output_path.stem}_lines"

    lines_dir.mkdir(parents=True, exist_ok=True)

    # Generate audio files
    audio_files = await generate_all_audio(assignments, voice_mapping, lines_dir)

    if not audio_files:
        print("No audio files generated", file=sys.stderr)
        sys.exit(1)

    # Merge into final audio
    success = merge_audio_files(audio_files, args.output)

    if success:
        print(args.output)  # Output filename to stdout for piping
    else:
        sys.exit(1)


def main():
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()