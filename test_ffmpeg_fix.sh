#!/bin/bash

# Test script to verify ffmpeg path fix

set -e

echo "Testing FFmpeg path fix..."
echo "=========================="

# Create test directory
TEST_DIR="test_ffmpeg"
rm -rf "$TEST_DIR"
mkdir -p "$TEST_DIR/lines"

# Create dummy MP3 files using ffmpeg
echo "Creating test audio files..."
for i in {1..5}; do
    ffmpeg -f lavfi -i "sine=frequency=440:duration=0.5" \
           -q:a 9 -acodec mp3 -y \
           "$TEST_DIR/lines/line_$(printf "%04d" $i).mp3" 2>/dev/null
done

# Create test JSON
cat > "$TEST_DIR/test.json" << 'EOF'
[
  {"id": 1, "text": "Test line 1", "character": "Character1"},
  {"id": 2, "text": "Test line 2", "character": "Character1"},
  {"id": 3, "text": "Test line 3", "character": "Character1"},
  {"id": 4, "text": "Test line 4", "character": "Character1"},
  {"id": 5, "text": "Test line 5", "character": "Character1"}
]
EOF

# Create voice mapping
cat > "$TEST_DIR/voices.json" << 'EOF'
{"Character1": "zh-CN-XiaoxiaoNeural"}
EOF

echo ""
echo "Test files created in $TEST_DIR/"
echo "Files created:"
ls -la "$TEST_DIR/lines/" | head -7

echo ""
echo "Now test the merge functionality directly..."

# Test merging with Python
python3 -c "
import sys
import os
sys.path.append('.')
from voice import merge_audio_files

# Get list of test files
test_files = ['$TEST_DIR/lines/line_{:04d}.mp3'.format(i) for i in range(1, 6)]

# Test merge
print('Testing merge with absolute paths...')
success = merge_audio_files(test_files, '$TEST_DIR/merged.mp3')

if success:
    print('✅ Merge successful!')
    if os.path.exists('$TEST_DIR/merged.mp3'):
        size_kb = os.path.getsize('$TEST_DIR/merged.mp3') / 1024
        print(f'Output file size: {size_kb:.1f} KB')
else:
    print('❌ Merge failed!')
    sys.exit(1)
"

echo ""
echo "Test completed successfully!"

# Clean up
rm -rf "$TEST_DIR"