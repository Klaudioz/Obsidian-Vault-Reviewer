# Obsidian Vault Reviewer

An AI-powered tool to help you clean up and organize your Obsidian vault by analyzing note relevance using Google's Gemini AI.

## Features

- 🔍 **Automated Analysis**: Uses Gemini AI to analyze each note's relevance
- ⭐ **Relevance Scoring**: Provides 0-10 relevance scores for each note
- 🎯 **Smart Recommendations**: AI suggests whether to keep or delete each note
- 📊 **Progress Tracking**: Shows progress through your entire vault
- 📋 **Session Logging**: Keeps a record of all decisions made
- 🛡️ **Safe Operations**: Asks for confirmation before deleting files
- 🔗 **Link-Aware**: Gives higher scores to notes with many [[wiki-style]] connections
- 🔐 **Security-Conscious**: Protects notes containing API keys, passwords, or credentials

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Get Gemini API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key (it's free!)

### 3. Set Your API Key (Choose One Option):

**Option A: Environment Variable (Recommended)**
```bash
export GEMINI_API_KEY="your-api-key-here"
```

**Option B: Enter When Prompted**
- The script will ask for your API key when you run it
- Just paste it when prompted

### 4. Backup Your Vault (Recommended)

Before running the script, make a backup of your Obsidian vault:

```bash
cp -r /path/to/your/vault /path/to/backup/location
```

## Usage

### Basic Usage

```bash
python obsidian_vault_reviewer.py
```

The script will:
1. Ask for your Gemini API key (if not set as environment variable)
2. Ask for your vault path (defaults to current directory)
3. Scan for all markdown files
4. Analyze each file and present you with options

### During Review

For each note, you'll see:
- **File information**: Name, path, size
- **AI Analysis**: Relevance score (0-10) and reasoning
- **AI Recommendation**: Keep or delete suggestion
- **Content Preview**: First 300 characters of the note

Then choose:
- `k` - Keep the file
- `d` - Delete the file
- `s` - Skip for now
- `q` - Quit the review process

### Example Session

```
📄 File: Old Meeting Notes.md
📁 Path: work/Old Meeting Notes.md
📏 Size: 1205 characters
⭐ Relevance Score: 2/10
🤔 AI Reasoning: Contains outdated meeting notes from 2020 with no actionable items
💡 AI Recommendation: DELETE
👀 Preview: Meeting notes from March 2020 - discussed project xyz...

What would you like to do?
  [k] Keep this file
  [d] Delete this file
  [s] Skip for now
  [q] Quit the review process

Enter your choice (k/d/s/q): d
✅ Deleted: work/Old Meeting Notes.md
```

## Enhanced Scoring Criteria

The AI evaluates notes with these score ranges:

- **0-2**: Outdated, redundant, or no value (should delete)
- **3-4**: Low value, probably safe to delete
- **5-6**: Moderate value, review carefully
- **7-8**: High value, likely keep
- **9-10**: Essential content, definitely keep

### Scoring Bonuses

The AI automatically adds bonus points for:

- **🔐 Sensitive Information** (+2-3 points): Notes containing API keys, passwords, tokens, or credentials
- **🔗 Connected Notes** (+1-2 points): Notes with Obsidian [[wiki-style links]] to other notes
- **🌟 Hub Notes** (+2-3 points): Notes with many outgoing links (central to your knowledge network)
- **📝 Template Files** (+1-2 points): Reusable template structures

## Factors Considered

The AI considers:
- Content quality and depth
- Uniqueness of information
- Practical utility
- Recency and relevance
- Whether it's a template, reference, or personal note
- **NEW: Presence of sensitive information (API keys, passwords)**
- **NEW: Interconnectedness via [[Obsidian links]]**
- **NEW: Role as a hub/index note with many connections**

## Safety Features

- **Confirmation Required**: You must manually confirm each deletion
- **Session Logging**: All actions are logged in `vault_review_log.json`
- **Progress Tracking**: See exactly which files have been processed
- **Error Handling**: Gracefully handles API failures and file read errors
- **Security Awareness**: Protects notes with sensitive information

## Output

After the session, you'll get:
- Summary of files deleted and kept
- Detailed log saved as `vault_review_log.json` in your vault
- List of all deleted files for reference

## Tips

1. **Start Small**: Consider testing on a small folder first
2. **Backup First**: Always backup your vault before running
3. **Review AI Suggestions**: The AI provides recommendations, but you make the final decision
4. **Session Logs**: Keep the log files for reference
5. **API Limits**: The script includes delays to respect API rate limits
6. **Connected Notes**: The AI will score notes with many [[links]] higher (they're often important hubs)
7. **Sensitive Data**: Notes with API keys or passwords get bonus points automatically

## Requirements

- Python 3.7+
- Gemini API key (free from Google AI Studio)
- Internet connection for AI analysis

## Troubleshooting

### Common Issues

1. **API Key Error**: Make sure your Gemini API key is valid and has sufficient quota
2. **File Permission Error**: Ensure you have write permissions for the vault directory
3. **Unicode Error**: Some files may have encoding issues - these will be skipped with a warning

### Rate Limits

The script includes a 1-second delay between API calls to respect rate limits. If you encounter rate limit errors, the script will continue with default scoring.

## License

This script is provided as-is for personal use. Please review and test thoroughly before using on important data. 