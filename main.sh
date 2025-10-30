#!/bin/bash

# Main pipeline script - Smart router for audiobook generation
# Handles both .txt character files (needs voice selection) and .json voice mappings

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored messages
print_error() {
    echo -e "${RED}✗ $1${NC}" >&2
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}" >&2
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}" >&2
}

print_header() {
    echo -e "\n${BLUE}========================================${NC}" >&2
    echo -e "${BLUE}$1${NC}" >&2
    echo -e "${BLUE}========================================${NC}\n" >&2
}

# Check usage
if [[ $# -lt 2 ]]; then
    echo "Usage: $0 <book_directory> <character_file.txt|voice_mapping.json>"
    echo ""
    echo "Arguments:"
    echo "  book_directory   Directory containing .txt files to process"
    echo "  character_file   Either:"
    echo "                   - .txt file with character names (will prompt for voice selection)"
    echo "                   - .json file with voice mappings (skip voice selection)"
    echo ""
    echo "Examples:"
    echo "  $0 sample_book sample_char.txt      # Interactive voice selection"
    echo "  $0 sample_book voice_mapping.json    # Use existing voice mapping"
    exit 1
fi

BOOK_DIR="$1"
CHAR_INPUT="$2"

# Validate inputs
if [[ ! -d "$BOOK_DIR" ]]; then
    print_error "Book directory not found: $BOOK_DIR"
    exit 1
fi

if [[ ! -f "$CHAR_INPUT" ]]; then
    print_error "Character/voice file not found: $CHAR_INPUT"
    exit 1
fi


# Check dependencies
command -v python3 >/dev/null 2>&1 || {
    print_error "Python 3 not installed"
    exit 1
}

command -v ffmpeg >/dev/null 2>&1 || {
    print_error "ffmpeg not installed"
    exit 1
}

print_header "Audiobook Generation Pipeline"

# Determine if we need voice selection
if [[ "$CHAR_INPUT" == *.txt ]]; then
    # Character file provided - need voice selection
    print_info "Character file detected: $CHAR_INPUT"
    print_info "Starting voice selection..."

    python3 select_voices.py "$CHAR_INPUT"

    if [[ ! -f "voice_mapping.json" ]]; then
        print_error "Voice selection failed or cancelled"
        exit 1
    fi

    VOICE_MAPPING="voice_mapping.json"
    CHARACTER_FILE="$CHAR_INPUT"

elif [[ "$CHAR_INPUT" == *.json ]]; then
    # Voice mapping provided - skip selection
    print_info "Voice mapping detected: $CHAR_INPUT"
    VOICE_MAPPING="$CHAR_INPUT"

    # We still need a character file for the API
    # Extract characters from voice mapping
    CHARACTER_FILE="temp_characters.txt"
    python3 -c "
import json
with open('$VOICE_MAPPING', 'r') as f:
    mapping = json.load(f)
    for char in mapping.keys():
        print(char)
" > "$CHARACTER_FILE"

else
    print_error "Unknown file type: $CHAR_INPUT"
    print_error "Must be .txt (character file) or .json (voice mapping)"
    exit 1
fi

print_success "Voice mapping ready: $VOICE_MAPPING"

# Process each text file in the book directory
for TEXT_FILE in "$BOOK_DIR"/*.txt; do
    if [[ ! -f "$TEXT_FILE" ]]; then
        continue
    fi

    BASE_NAME=$(basename "$TEXT_FILE" .txt)

    # Skip character files
    if [[ "$BASE_NAME" == *"char"* ]] || [[ "$BASE_NAME" == *"character"* ]]; then
        continue
    fi

    print_header "Processing: $BASE_NAME"

    # Create chapter subdirectory for all intermediate files
    CHAPTER_DIR="${BOOK_DIR}/${BASE_NAME}_processing"
    mkdir -p "$CHAPTER_DIR"
    print_info "Created processing directory: $CHAPTER_DIR"

    # Step 1: Clean text
    print_info "Step 1/3: Cleaning text..."
    CLEANED_FILE="${CHAPTER_DIR}/${BASE_NAME}_cleaned.txt"
    python3 clean.py "$TEXT_FILE" "$CLEANED_FILE"

    if [[ ! -f "$CLEANED_FILE" ]]; then
        print_error "Text cleaning failed"
        continue
    fi
    print_success "Text cleaned"

    # Step 2: Assign characters
    print_info "Step 2/3: Assigning characters..."
    ASSIGNED_FILE="${CHAPTER_DIR}/${BASE_NAME}.json"
    python3 char.py "$CLEANED_FILE" "$CHARACTER_FILE" --output "$ASSIGNED_FILE"

    if [[ ! -f "$ASSIGNED_FILE" ]]; then
        print_error "Character assignment failed"
        continue
    fi
    print_success "Characters assigned"

    # Step 3: Generate audio
    print_info "Step 3/3: Generating audio..."
    TEMP_AUDIO_FILE="${CHAPTER_DIR}/${BASE_NAME}.mp3"
    LINES_DIR="${CHAPTER_DIR}/${BASE_NAME}_lines"
    python3 voice.py "$ASSIGNED_FILE" "$VOICE_MAPPING" --output "$TEMP_AUDIO_FILE" --lines-dir "$LINES_DIR"

    if [[ ! -f "$TEMP_AUDIO_FILE" ]]; then
        print_error "Audio generation failed"
        continue
    fi

    # Move final audio to main directory for easy access
    FINAL_AUDIO_FILE="${BOOK_DIR}/${BASE_NAME}.mp3"
    mv "$TEMP_AUDIO_FILE" "$FINAL_AUDIO_FILE"

    print_success "Audio generated: $FINAL_AUDIO_FILE"

    # Optional: Clean up intermediate files after successful processing
    # Uncomment the next line to remove the processing directory after success
    # rm -rf "$CHAPTER_DIR"
done

# Clean up temp character file if created
if [[ "$CHAR_INPUT" == *.json ]] && [[ -f "temp_characters.txt" ]]; then
    rm -f "temp_characters.txt"
fi

print_header "Pipeline Complete!"
print_success "All files processed successfully"