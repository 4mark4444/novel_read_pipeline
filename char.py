#!/usr/bin/env python3
"""
Character assignment - Uses EXACT API logic from new_function/main.py
Takes cleaned text and assigns characters using Grok-4
"""

import json
import argparse
import os
import sys
import time
import httpx
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from openai import OpenAI

# EXACT same prompts from new_function/main.py
SYSTEM_PROMPT = """你是中文小说"台词归属"助手。
任务：把输入中的每一行分配给确切的角色名。
规则：
1) 旁白一律归于当前视角角色（即 POV 角色）。
2) 仅能从"角色清单"中选择 character；不可创造新名字。
3) 多人对话时结合上下文、谓语（"说/问/道/喊/答"）、动作描写、称谓与说话习惯进行推断。
4) 仅输出 id 和 character，无需重复 text 内容。
5) 严禁输出原文本、多余文字、注释或 Markdown 标记。
"""

USER_PROMPT_TEMPLATE = """## 视角
当前片段的视角角色（POV）：{pov}

## 角色清单（含别名）
仅能从下列 name 中选择 character（aliases 仅用于判断，不可作为输出）：
{roles_txt}

## 标注要求
- 输入已按行给出（含 id 与 text）。
- 台词（含「」/""/『』/— 起止等）按对话逻辑判人；
- 叙述/心理均视为旁白，直接标到当前视角角色；
- 对"长段对话"须依据前后轮次、呼唤对象、动作线索推断说话人。

## 输出格式
仅输出 JSON 数组（无反引号、无解释）。每个元素仅包含 id 和 character：
{{"id": 55, "character": "岛村抱月"}}
注意：不要输出 text 字段，仅需 id 和 character。

## 待标注文本
{lines_block}
请开始。
"""

# EXACT same configuration from new_function/main.py
TEMPERATURE = 0.3
BATCH_SIZE = 100
MAX_RETRIES = 3
RETRY_DELAY = 2


def detect_encoding(file_path: str) -> Optional[str]:
    """Detect file encoding."""
    encodings = ['utf-8', 'utf-16-le', 'utf-16-be', 'utf-16', 'gbk', 'gb18030', 'big5']

    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                f.read(1000)
            return encoding
        except (UnicodeDecodeError, UnicodeError):
            continue

    return None


def load_character_list(character_file: str) -> List[Dict[str, any]]:
    """Load character list from file - EXACT logic from new_function/main.py"""
    characters = []
    encoding = detect_encoding(character_file)
    if not encoding:
        raise ValueError(f"Unable to detect encoding for {character_file}")

    print(f"Character file encoding: {encoding}", file=sys.stderr)

    with open(character_file, 'r', encoding=encoding) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            # Remove BOM if present
            if line.startswith('\ufeff'):
                line = line[1:]

            # Check if line contains aliases
            if ':' in line:
                parts = line.split(':', 1)
                name = parts[0].strip()
                aliases = [alias.strip() for alias in parts[1].split(',') if alias.strip()]
                characters.append({'name': name, 'aliases': aliases})
            else:
                characters.append({'name': line, 'aliases': []})

    return characters


def format_character_list(characters: List[Dict]) -> str:
    """Format character list for prompt - EXACT from new_function/main.py"""
    lines = []
    for char in characters:
        if char['aliases']:
            lines.append(f"- {char['name']} (别名：{', '.join(char['aliases'])})")
        else:
            lines.append(f"- {char['name']}")
    return '\n'.join(lines)


def format_lines_for_prompt(lines: List[str], start_id: int) -> str:
    """Format text lines for prompt - EXACT from new_function/main.py"""
    formatted = []
    for i, line in enumerate(lines):
        formatted.append(f"id: {start_id + i}, text: {line}")
    return '\n'.join(formatted)


def call_grok_api(client: OpenAI, lines: List[str], start_id: int,
                  pov: str, characters: List[Dict]) -> List[Dict]:
    """Call Grok-4 API - EXACT logic from new_function/main.py"""
    roles_txt = format_character_list(characters)
    lines_block = format_lines_for_prompt(lines, start_id)

    user_prompt = USER_PROMPT_TEMPLATE.format(
        pov=pov,
        roles_txt=roles_txt,
        lines_block=lines_block
    )

    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model="grok-4-fast-reasoning",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=TEMPERATURE
            )

            # Parse the response
            content = response.choices[0].message.content.strip()

            # Clean up the response (remove markdown if present)
            if content.startswith('```json'):
                content = content[7:]
            if content.startswith('```'):
                content = content[3:]
            if content.endswith('```'):
                content = content[:-3]

            # Parse JSON
            result = json.loads(content)

            # Validate result
            if not isinstance(result, list):
                raise ValueError("API response is not a list")

            # Ensure all required fields are present and reconstruct with text
            reconstructed_result = []
            for item in result:
                if 'id' not in item or 'character' not in item:
                    raise ValueError(f"Missing required fields in item: {item}")

                # Validate character name
                valid_names = [char['name'] for char in characters]
                if item['character'] not in valid_names:
                    print(f"Warning: Character '{item['character']}' not in character list", file=sys.stderr)

                # Reconstruct the full item with original text
                line_index = item['id'] - start_id
                if 0 <= line_index < len(lines):
                    full_item = {
                        'id': item['id'],
                        'text': lines[line_index],
                        'character': item['character']
                    }
                    reconstructed_result.append(full_item)
                else:
                    raise ValueError(f"Invalid ID {item['id']} - out of range for current batch")

            return reconstructed_result

        except Exception as e:
            print(f"API call attempt {attempt + 1} failed: {e}", file=sys.stderr)
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (2 ** attempt))  # Exponential backoff
            else:
                raise


def process_text_file(text_file: str, characters: List[Dict], client: OpenAI,
                      output_file: str = None, pov: str = "视角角色") -> str:
    """Process a text file and assign characters."""
    print(f"Processing: {text_file}", file=sys.stderr)

    # Load text lines
    lines = []
    with open(text_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                lines.append(line)

    if not lines:
        print(f"No valid lines found in {text_file}", file=sys.stderr)
        return None

    print(f"Loaded {len(lines)} lines", file=sys.stderr)

    # Determine output file
    if not output_file:
        base_name = Path(text_file).stem
        output_file = f"{base_name}_assigned.json"

    # Check for existing progress (for resume capability)
    labeled_data = []
    start_index = 0
    checkpoint_file = output_file + ".checkpoint"

    if os.path.exists(checkpoint_file):
        try:
            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                labeled_data = json.load(f)
                start_index = len(labeled_data)
                print(f"Resuming from line {start_index + 1}", file=sys.stderr)
        except:
            print("Could not load checkpoint, starting fresh", file=sys.stderr)

    # Process in batches
    total_batches = (len(lines) - start_index + BATCH_SIZE - 1) // BATCH_SIZE

    for batch_num in range(total_batches):
        batch_start = start_index + batch_num * BATCH_SIZE
        batch_end = min(batch_start + BATCH_SIZE, len(lines))
        batch_lines = lines[batch_start:batch_end]

        print(f"Processing batch {batch_num + 1}/{total_batches} (lines {batch_start + 1}-{batch_end})",
              file=sys.stderr)

        try:
            # Call API
            batch_result = call_grok_api(
                client, batch_lines, batch_start + 1, pov, characters
            )

            # Add to results
            labeled_data.extend(batch_result)

            # Save checkpoint after each batch
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(labeled_data, f, ensure_ascii=False, indent=2)

            print(f"Saved progress: {len(labeled_data)}/{len(lines)} lines", file=sys.stderr)

        except Exception as e:
            print(f"Error processing batch: {e}", file=sys.stderr)
            print(f"Progress saved up to line {len(labeled_data)}", file=sys.stderr)
            break

    # Save final output
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(labeled_data, f, ensure_ascii=False, indent=2)

    # Remove checkpoint if complete
    if len(labeled_data) == len(lines) and os.path.exists(checkpoint_file):
        os.remove(checkpoint_file)

    print(f"✓ Completed: {len(labeled_data)} lines assigned", file=sys.stderr)
    print(f"✓ Output saved to: {output_file}", file=sys.stderr)
    return output_file


def main():
    parser = argparse.ArgumentParser(
        description='Character assignment using Grok-4 (EXACT logic from new_function/main.py)'
    )
    parser.add_argument('text_file', help='Cleaned text file to process')
    parser.add_argument('character_file', help='File containing character names')
    parser.add_argument('--output', help='Output JSON file')
    parser.add_argument('--pov', default='视角角色', help='POV character name')
    parser.add_argument('--api-key', help='X.AI API key (or set X_API_KEY environment variable)')

    args = parser.parse_args()

    # Validate inputs
    if not os.path.exists(args.text_file):
        print(f"Error: Text file not found: {args.text_file}", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(args.character_file):
        print(f"Error: Character file not found: {args.character_file}", file=sys.stderr)
        sys.exit(1)

    # Get API key
    api_key = "xai-Sn9oRVX7Enf0PVp96PMSGvlLyFjANHwI9c5ZpKL056ZsO41YiSRTg5ajDLroQadYhLzh73KXy43JRpcT"


    # Initialize API client
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.x.ai/v1",
        timeout=httpx.Timeout(300.0, connect=60.0)
    )

    # Load characters
    characters = load_character_list(args.character_file)
    print(f"Loaded {len(characters)} characters", file=sys.stderr)

    # Process file
    try:
        output_file = process_text_file(
            args.text_file,
            characters,
            client,
            args.output,
            args.pov
        )
        if output_file:
            print(output_file)  # Output filename to stdout for piping
    except KeyboardInterrupt:
        print("\nInterrupted by user. Progress has been saved.", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()