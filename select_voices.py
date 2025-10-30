#!/usr/bin/env python3
"""
Simple voice selector - Takes character file, outputs voice mapping
"""

import json
import sys

# Available voices (simplified list)
VOICES = [
    'zh-CN-XiaoxiaoNeural',   # 1 Female - Warm
    'zh-CN-XiaohanNeural',    # 2 Female - Gentle
    'zh-CN-XiaomoNeural',     # 3 Female - Deep
    'zh-CN-XiaoruiNeural',    # 4 Female - Confident
    'zh-CN-XiaoyanNeural',    # 5 Female - Warm
    'zh-CN-XiaoyiNeural',     # 6 Female - Bright
    'zh-CN-XiaochenNeural',   # 7 Female - Friendly
    'zh-CN-XiaomengNeural',   # 8 Female - Gentle
    'zh-CN-XiaoqiuNeural',    # 9 Female - Calm
    'zh-CN-XiaorouNeural',    # 10 Female - Cheerful
    'zh-CN-XiaoshuangNeural', # 11 Female - Crisp
    'zh-CN-XiaoyouNeural',    # 12 Female - Crisp
    'zh-CN-XiaozhenNeural',   # 13 Female - Calm
    'zh-CN-YunxiNeural',      # 14 Male - Bright
    'zh-CN-YunjianNeural',    # 15 Male - Deep
    'zh-CN-YunyangNeural',    # 16 Male - Formal
    'zh-CN-YunyeNeural',      # 17 Male - Casual
    'zh-CN-YunfengNeural',    # 18 Male - Confident
    'zh-CN-YunhaoNeural',     # 19 Male - Warm
    'zh-CN-YunjieNeural',     # 20 Male - Casual
    'zh-CN-YunxiaNeural',     # 21 Male - Cheerful
    'zh-CN-YunzeNeural',      # 22 Male - Deep
]


def main():
    if len(sys.argv) != 2:
        print("Usage: python select_voices.py <character_file>")
        sys.exit(1)

    character_file = sys.argv[1]

    # Read characters
    characters = []
    with open(character_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                # Handle format: name:alias1,alias2 - just take the name
                if ':' in line:
                    line = line.split(':')[0].strip()
                characters.append(line)

    print(f"\nFound {len(characters)} characters")
    print("\nAvailable voices:")
    print("-" * 40)
    for i, voice in enumerate(VOICES, 1):
        gender = "Female" if i <= 13 else "Male"
        print(f"{i:2}. {voice} ({gender})")
    print("-" * 40)

    # Select voice for each character
    voice_mapping = {}
    for char in characters:
        print(f"\nSelect voice for '{char}' (1-22): ", end="")
        choice = input().strip()

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(VOICES):
                voice_mapping[char] = VOICES[idx]
            else:
                voice_mapping[char] = VOICES[0]  # Default
                print(f"Using default voice")
        except:
            voice_mapping[char] = VOICES[0]  # Default
            print(f"Using default voice")

        print(f"  → {voice_mapping[char]}")

    # Save mapping
    with open('voice_mapping.json', 'w', encoding='utf-8') as f:
        json.dump(voice_mapping, f, ensure_ascii=False, indent=2)

    print("\n✓ Saved to voice_mapping.json")


if __name__ == "__main__":
    main()