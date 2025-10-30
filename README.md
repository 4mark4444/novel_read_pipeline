# Chinese Novel Audiobook Generator

An AI-powered pipeline for converting Chinese text novels into character-specific voice audiobooks using Azure edge-tts and Grok-4 character attribution.

## Features

- **AI Character Attribution**: Automatic speaker identification using Grok-4-fast-reasoning
- **Character-Specific Voices**: Maps each character to a unique Azure Neural voice (22 Chinese voices available)
- **Smart Text Processing**: Automatically separates dialogue from narration
- **Batch Processing**: Handle multiple chapters efficiently
- **Checkpoint/Resume**: Recover from interruptions without losing progress
- **Hallucination Detection**: Identifies and handles AI-invented characters
- **Robust Error Handling**: Aggressive retry logic with exponential backoff
- **Silence Detection**: Generates appropriate silence for ellipsis-only dialogue

## Prerequisites

- Python 3.x
- ffmpeg (for audio merging)
- X.AI API key (for Grok-4 access)

## Installation

1. Install Python dependencies:
```bash
pip install edge-tts==7.2.3 openai==1.107.0 httpx==0.28.1 tqdm==4.67.1
```

2. Install ffmpeg:
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install ffmpeg
```

3. Set up your API key:
```bash
export X_API_KEY="your-x-ai-api-key"
```

## Quick Start

### Basic Usage

```bash
# Full pipeline: voice selection + character assignment + audio generation
./main.sh <book_directory> <character_file.txt>

# Using existing voice mapping (skip voice selection)
./main.sh <book_directory> <voice_mapping.json>
```

### Example

```bash
# Create a character file
cat > characters.txt <<EOF
莓原树
户川凛
安达
视角角色
EOF

# Run the pipeline
./main.sh ./my_novel characters.txt
```

## Pipeline Stages

### 1. Text Cleaning (`clean.py`)

Separates dialogue from narration and removes metadata.

```bash
python3 clean.py input.txt output_cleaned.txt
```

**Features:**
- Auto-detects encoding (UTF-8/16, GBK, GB18030, Big5)
- Extracts dialogue using Chinese quote patterns (「」)
- Removes annotation lines (starting with `&&&&&&`)

### 2. Character Attribution (`char.py`)

Uses Grok-4 AI to identify which character speaks each line.

```bash
python3 char.py cleaned_text.txt character_file.txt --output assignments.json
```

**Features:**
- Processes 50 lines per API call for efficiency
- Supports character aliases: `岛村抱月:抱月,小月`
- Checkpoint/resume capability
- Temperature: 0.3, Max retries: 3, Timeout: 300s

### 3. Voice Selection (`select_voices.py`)

Interactive tool to map characters to voices.

```bash
python3 select_voices.py character_file.txt
```

**Outputs:** `voice_mapping.json`

### 4. Audio Generation (`voice.py`)

Synthesizes audio using Azure edge-tts.

```bash
python3 voice.py assignments.json voice_mapping.json --output audiobook.mp3
```

**Features:**
- Concurrent processing (3 simultaneous operations)
- 10 retries with exponential backoff
- Handles unmapped characters interactively
- Detects ellipsis-only lines and generates silence
- Merges with 0.5s pauses between lines

## File Formats

### Character File (`.txt`)

Simple format:
```
莓原树
户川凛
安达
```

With aliases:
```
岛村抱月:抱月,小月
户川凛:凛,小凛
```

### Voice Mapping (`.json`)

```json
{
  "莓原树": "zh-CN-XiaohanNeural",
  "户川凛": "zh-CN-XiaoxiaoNeural",
  "安达": "zh-CN-XiaoxuanNeural",
  "视角角色": "zh-CN-YunxiNeural"
}
```

### Character Assignments (`.json`)

```json
[
  {
    "id": 1,
    "text": "「来打桌球吧。」",
    "character": "安达"
  },
  {
    "id": 2,
    "text": "一起跷课的安达如此提议。",
    "character": "视角角色"
  }
]
```

## Output Structure

```
book_directory/
├── chapter1.txt                    # Original text
├── chapter1.mp3                    # Final audiobook
└── chapter1_processing/            # Intermediate files
    ├── chapter1_cleaned.txt        # Cleaned text
    ├── chapter1.json               # Character assignments
    └── chapter1_lines/             # Individual line audio files
```

## Available Chinese Voices

The system supports 22 Azure Neural voices:

| Voice ID | Gender | Description |
|----------|--------|-------------|
| zh-CN-XiaoxiaoNeural | Female | Warm, suitable for young female characters |
| zh-CN-XiaoyiNeural | Female | Gentle, suitable for children |
| zh-CN-YunjianNeural | Male | Professional, suitable for adult males |
| zh-CN-YunxiNeural | Male | Warm, suitable for narration |
| zh-CN-YunyangNeural | Male | News anchor style |
| ... and 17 more | - | Run `select_voices.py` to see all |

## Advanced Usage

### Resuming Interrupted Processing

Character attribution automatically saves checkpoints:
```bash
# If interrupted, simply run the same command again
python3 char.py cleaned_text.txt characters.txt --output assignments.json
# Progress resumes from last checkpoint
```

Audio generation skips existing files:
```bash
# If interrupted, re-run the same command
python3 voice.py assignments.json voice_mapping.json --output audiobook.mp3
# Existing audio files are preserved and reused
```

### Merging Existing Audio

If you need to merge audio files manually:
```bash
python3 merge_existing_audio.py chapter1_lines/ --output merged.mp3
```

### Individual Components

```bash
# Just clean text
python3 clean.py input.txt output.txt

# Just assign characters
python3 char.py cleaned.txt characters.txt --output assignments.json

# Just generate audio
python3 voice.py assignments.json voice_mapping.json --output audio.mp3
```

## Troubleshooting

### API Key Error
```bash
# Ensure X_API_KEY is set
echo $X_API_KEY
export X_API_KEY="your-x-ai-api-key"
```

### Encoding Issues
The system auto-detects UTF-8/16, GBK, GB18030, and Big5. If you encounter issues, convert your file:
```bash
iconv -f GB18030 -t UTF-8 input.txt > output.txt
```

### AI Hallucinations
When Grok invents characters not in your list, `voice.py` will prompt you to map them:
```
Character '小明' not found in voice mapping. Enter voice ID:
```
Type a valid voice ID or press Enter to skip that line.

### Audio Generation Failures
Check individual audio files:
```bash
ls -lh chapter1_processing/chapter1_lines/
```

Use the recovery tool:
```bash
python3 merge_existing_audio.py chapter1_processing/chapter1_lines/ --output chapter1.mp3
```

## Performance Tuning

Configuration in `voice.py`:
- `MAX_CONCURRENT`: Number of simultaneous TTS operations (default: 3)
- `MAX_RETRIES`: Retry attempts per line (default: 10)
- `TIMEOUT`: Seconds before timing out (default: 30)

Configuration in `char.py`:
- Batch size: 50 lines per API call
- Temperature: 0.3 (low for consistency)
- Timeout: 300s per batch

## License

[Add your license here]

## Contributing

Contributions welcome! Please open an issue or submit a pull request.

## Acknowledgments

- Azure edge-tts for high-quality Chinese speech synthesis
- X.AI Grok-4 for accurate character attribution
- ffmpeg for audio processing
