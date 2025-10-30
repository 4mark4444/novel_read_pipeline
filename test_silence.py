#!/usr/bin/env python3
"""
Test script to verify silence detection and handling
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from voice import is_silence_line, calculate_silence_duration

# Test cases that should be detected as silence
silence_test_cases = [
    '「……………………」',
    '「…」',
    '「……」',
    '「…………」',
    '……………………',
    '…',
    '「。。。。。。。。」',
    '「～～～～～」',
    '「———————」',
    '「ーーーーーー」',
    '（…………）',
    '『……………………』',
    '"………………"',
]

# Test cases that should NOT be detected as silence
non_silence_test_cases = [
    '「你好」',
    '「让我们开始吧。」',
    '这是一段旁白。',
    '「……你好」',  # Has actual text
    '「嗯…好吧」',  # Has actual text
]

print("Testing silence detection...")
print("=" * 60)

print("\n✅ Should be detected as SILENCE:")
for test in silence_test_cases:
    is_silence = is_silence_line(test)
    duration = calculate_silence_duration(test) if is_silence else 0
    status = "✓" if is_silence else "✗"
    print(f"{status} {test:30} -> Silence: {is_silence:5} Duration: {duration:.1f}s")

print("\n❌ Should NOT be detected as silence:")
for test in non_silence_test_cases:
    is_silence = is_silence_line(test)
    status = "✓" if not is_silence else "✗"
    print(f"{status} {test:30} -> Silence: {is_silence}")

print("\n" + "=" * 60)

# Count successes
silence_correct = sum(1 for test in silence_test_cases if is_silence_line(test))
non_silence_correct = sum(1 for test in non_silence_test_cases if not is_silence_line(test))

print(f"\nResults:")
print(f"Silence detection: {silence_correct}/{len(silence_test_cases)} correct")
print(f"Non-silence detection: {non_silence_correct}/{len(non_silence_test_cases)} correct")

if silence_correct == len(silence_test_cases) and non_silence_correct == len(non_silence_test_cases):
    print("\n✅ All tests passed!")
else:
    print("\n⚠️ Some tests failed!")
    sys.exit(1)