#!/usr/bin/env python3
"""
Test actual silence audio generation
"""

import asyncio
import os
import json
from pathlib import Path

async def test_silence_generation():
    """Test generating audio for silence lines"""

    # Create test data
    test_json = [
        {"id": 1, "text": "「你好世界」", "character": "主角"},
        {"id": 2, "text": "「……………………」", "character": "主角"},  # This should generate silence
        {"id": 3, "text": "「让我们开始吧」", "character": "配角"},
        {"id": 4, "text": "「…」", "character": "配角"},  # This should generate silence
        {"id": 5, "text": "旁白描述", "character": "旁白"}
    ]

    # Create test voice mapping
    voice_mapping = {
        "主角": "zh-CN-XiaoxiaoNeural",
        "配角": "zh-CN-YunxiNeural",
        "旁白": "zh-CN-XiaohanNeural"
    }

    # Create test directory
    test_dir = Path("test_silence_output")
    test_dir.mkdir(exist_ok=True)

    # Save test files
    assignments_file = test_dir / "test_assignments.json"
    voice_file = test_dir / "test_voices.json"

    with open(assignments_file, 'w', encoding='utf-8') as f:
        json.dump(test_json, f, ensure_ascii=False, indent=2)

    with open(voice_file, 'w', encoding='utf-8') as f:
        json.dump(voice_mapping, f, ensure_ascii=False, indent=2)

    print("Test files created in test_silence_output/")
    print("\nTo test silence handling, run:")
    print(f"  python3 voice.py {assignments_file} {voice_file} --output test_silence.mp3")
    print("\nExpected behavior:")
    print("  - Line 2 (「……………………」) should generate 2.6s silence")
    print("  - Line 4 (「…」) should generate 1.2s silence")
    print("  - Other lines should generate normal TTS audio")

if __name__ == "__main__":
    asyncio.run(test_silence_generation())