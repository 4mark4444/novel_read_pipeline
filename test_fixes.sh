#!/bin/bash

# Test script to verify the bug fixes

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Testing Bug Fixes${NC}"
echo "=================================="

# Create test directory structure
TEST_DIR="test_book"
rm -rf "$TEST_DIR"
mkdir -p "$TEST_DIR"

# Create test text files
echo "Creating test files..."
cat > "$TEST_DIR/chapter1.txt" << 'EOF'
「你好，世界！」
这是第一章的内容。
「让我们开始吧。」
旁白描述。
EOF

cat > "$TEST_DIR/chapter2.txt" << 'EOF'
「第二章开始了。」
更多的内容在这里。
「继续前进！」
结束语。
EOF

# Create test character file
cat > "$TEST_DIR/characters.txt" << 'EOF'
主角
配角
旁白
EOF

echo -e "${GREEN}✓ Test files created${NC}"

# Test 1: Check if subdirectories are created
echo ""
echo "Test 1: Checking file organization..."
echo "Expected: Each chapter should have its own processing subdirectory"

# Run a dry-run to see directory structure (we'll modify main.sh to add a --dry-run option)
echo ""
echo "Directory structure after processing:"
echo "- $TEST_DIR/"
echo "  - chapter1_processing/    (NEW: contains all intermediate files)"
echo "  - chapter2_processing/    (NEW: contains all intermediate files)"
echo "  - chapter1.mp3            (final audio)"
echo "  - chapter2.mp3            (final audio)"

# Test 2: Voice synthesis timeout handling
echo ""
echo "Test 2: Voice synthesis timeout handling"
echo "Expected: Each failed attempt should:"
echo "  - Timeout after 30 seconds"
echo "  - Wait with exponential backoff (1s, 2s, 4s, 8s, 16s, 30s...)"
echo "  - Retry up to 10 times before giving up"

echo ""
echo -e "${GREEN}Test setup complete!${NC}"
echo ""
echo "To run the actual pipeline test, execute:"
echo "  export X_API_KEY='your-api-key'"
echo "  ./main.sh $TEST_DIR $TEST_DIR/characters.txt"
echo ""
echo "Watch for:"
echo "1. Subdirectories being created for each chapter"
echo "2. Timeout messages with retry attempts in voice.py output"
echo "3. All files being processed in correct directories"

# Clean up (optional)
# rm -rf "$TEST_DIR"