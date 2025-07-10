# Obsidian Vault Reviewer

An AI-powered tool to help you clean up and organize your Obsidian vault by analyzing note relevance using Google's Gemini AI. Designed specifically for "second brain" and zettelkasten workflows.

## ✨ Key Features

- 🧠 **"Second Brain" Optimized**: Prioritizes personal knowledge, insights, and interconnected notes
- 🤖 **Auto-Decision System**: Automatically keeps high-scoring notes (7+) and optionally deletes low-scoring ones
- ⚡ **Single-Key Interface**: Fast review with k/d/v/s/q keys - no Enter needed!
- 📊 **Progress Tracking**: Resume interrupted sessions, visual progress bar with time estimates
- 🔗 **WikiLink Aware**: Heavily favors notes with [[internal links]] and #tags
- 🖥️ **Clean Interface**: Auto-clearing screen shows only current note analysis
- 🎯 **Smart Scoring**: Enhanced 0-10 scoring system emphasizing personal value
- 🔐 **Security-Conscious**: Protects notes containing API keys, passwords, or credentials
- 📋 **Session Management**: Save/resume progress, configurable auto-decisions
- 🖱️ **Clickable Paths**: File names link directly to Obsidian for easy access

## 🎯 Enhanced Scoring System

The AI uses a sophisticated "second brain" scoring system that heavily favors personal knowledge:

### 🌟 **Maximum Value (9-10 points) - Core "Second Brain" Content:**
- **Personal financial data** (investments, 401k, portfolio tracking): +5 points
- **Personal medical/health records** (symptoms, treatments, health tracking): +5 points  
- **Original thoughts and insights** (unique ideas, "aha moments"): +4 points
- **Personal learning synthesis** (combining sources with your understanding): +4 points
- **Life experiences and stories** (travel, relationships, major events): +4 points
- **API keys, passwords, credentials**: +5 points

### 🚀 **High Value (7-8 points) - Personal Development:**
- **Personal project tracking** (goals, habits, progress logs): +4 points
- **Career development** (job history, performance reviews, planning): +4 points
- **Book notes with personal commentary** (your thoughts + highlights): +3 points
- **Daily notes and journal entries** (personal reflections, planning): +3 points
- **Personal workflows and systems** (custom templates, processes): +3 points

### 🔗 **Knowledge Network Value (5-7 points) - Organization:**
- **Multiple WikiLinks [[note name]]** (3+ internal links): +3 points
- **Tags and metadata** (#tag, YAML frontmatter): +3 points
- **Hub/index notes** (MOCs - Maps of Content): +3 points
- **Personal research with insights** (your questions, conclusions): +2 points
- **Obsidian links [[note name]]**: +2 points

### ❌ **Major Penalties (Anti-"Second Brain" Content):**
- **Copy-pasted content without personal input**: -4 points
- **No WikiLinks or tags**: -3 points (defeats Obsidian's purpose)
- **Easily recreated from Google/Wikipedia**: -4 points
- **Empty placeholder notes**: -3 points

## 🤖 Auto-Decision System

Configure intelligent automation to speed up your review:

### **Auto-Keep (Default: 7+ points)**
- High-scoring personal notes automatically kept
- Bypass manual review for valuable content
- Focus your time on borderline cases

### **Auto-Delete (Optional: 2- points)**  
- Very low-scoring notes can be auto-deleted
- Disabled by default for safety
- Configurable threshold (0-3 points)

### **Configuration**
```
Configure auto-decision settings? (y/n): y

⚙️ Auto-Decision Configuration
==================================================
Enable auto-keep for high-scoring notes? (currently: ON) (y/n): y
Current auto-keep threshold: 7
Enter new threshold (7-10) or press Enter to keep current: 8

Enable auto-delete for low-scoring notes? (currently: OFF) (y/n): n

Show auto-decision notifications? (currently: ON) (y/n): y

✅ Configuration saved!
   Auto-keep: Notes scoring 8+ will be kept automatically
   Notifications: Enabled
```

## 🔧 Setup

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

### 4. Backup Your Vault (Recommended)

```bash
cp -r /path/to/your/vault /path/to/backup/location
```

## 🚀 Usage

### Basic Usage

```bash
python obsidian_vault_reviewer.py
```

### First-Time Setup Flow

1. **API Key**: Enter your Gemini API key (if not set as environment variable)
2. **Vault Path**: Specify your vault directory (defaults to current directory)
3. **Auto-Configuration**: Choose whether to configure auto-decision settings
4. **Review Start**: Clean interface begins analyzing files

### Session Continuation

```
Found previous review session from: 2024-01-15 14:30:25
Files already processed: 847
Files deleted: 23
Files kept: 824

Do you want to continue the previous review session? (y/n): y
Continuing previous session...
```

### Review Interface

**Single-Key Controls (No Enter Required):**
- **k** - Keep this file (default - just press Enter)
- **d** - Delete this file  
- **v** - View entire note content
- **s** - Skip for now
- **q** - Quit and save progress

### Example Auto-Decision

```
🤖 AUTO-KEEP: Score 8/7+ → Automatically kept
📄 Personal-Investment-Strategy.md
💡 This note contains personal financial planning with specific investment goals...

🤖 AUTO-KEEP: Score 9/7+ → Automatically kept  
📄 Book-Notes-Atomic-Habits-Personal-Insights.md
💡 Excellent synthesis of book content with personal applications and unique insights...
```

### Manual Review Example

```
================================================================================
📄 File: Weekly-Review-Template.md
📁 Path: templates/Weekly-Review-Template.md
📊 Size: 1,847 characters
⭐ Relevance Score: 6/10

📖 Preview:
📋 Weekly Review Template
  • **What went well this week?**
  • **What could be improved?**
  • **Key accomplishments:**
  • **Next week's priorities:**

🤖 AI Reasoning:
  This is a well-structured personal template for weekly reviews. Contains good prompts for self-reflection and planning. Templates like this support consistent personal development practices and should be retained.

✅ AI Recommendation: KEEP
================================================================================

What would you like to do?
  [k] Keep this file (default)
  [d] Delete this file
  [v] View entire note content
  [s] Skip for now
  [q] Quit the review process

Press a key (k/d/v/s/q) or Enter for default (keep): k
Kept: templates/Weekly-Review-Template.md
```

## 📊 Progress Tracking

**Visual Progress Bar:**
```
Processing: Daily-Note-2024-01-15.md: 23%|████▌     | 1847/8012 files [15:32<45:21, 2.27files/s]
```

**Session Management:**
- Automatic progress saving after each file
- Resume interrupted sessions exactly where you left off
- Progress file: `.obsidian_review_progress.json` (auto-cleanup when complete)
- Graceful handling of Ctrl+C interruptions

## 💡 Smart Features

### **🖱️ Clickable File Paths**
File names become clickable terminal links that open directly in Obsidian:
```
📄 File: My-Important-Note.md  [Click to open in Obsidian]
```

### **🧹 Clean Interface**
- Screen clears after each decision
- Shows only current file analysis
- No accumulated clutter from previous files
- Progress indicator after each clear

### **⌨️ Fast Input System**
- Cross-platform single-key input (Windows, macOS, Linux)
- No need to press Enter for any decision
- Immediate visual feedback for key presses
- Enter key works as default (keep) for convenience

### **🔄 Session Interruption Handling**
- Ctrl+C gracefully saves progress
- Signal handlers for SIGINT and SIGTERM
- Continue exactly where you left off
- No lost work from unexpected interruptions

## 🎯 Best Practices

### **For "Second Brain" Optimization:**
1. **WikiLinks are Essential**: Notes without [[internal links]] or #tags get penalty points
2. **Personal > Generic**: Your thoughts and insights score much higher than copied content  
3. **Connected Knowledge**: Hub notes with many outgoing links are highly valued
4. **Original Synthesis**: Combining multiple sources with your understanding gets top scores

### **Review Strategy:**
1. **Configure Auto-Decisions**: Set auto-keep at 7+ to skip obvious keepers
2. **Focus on Middle Range**: Spend time on 3-6 score notes that need human judgment
3. **Use View Option**: Press 'v' to see full content when unsure
4. **Take Breaks**: Progress is saved automatically - quit and resume anytime

### **Performance Tips:**
1. **Start with Auto-Keep**: Configure threshold to automatically keep high-value notes
2. **Progressive Cleanup**: Review in chunks, use session continuation
3. **Backup First**: Always backup before major cleanup sessions
4. **Monitor Progress**: Use the progress bar to estimate time remaining

## 📋 Output & Logging

**Session Summary:**
```
================================================================================
REVIEW SESSION SUMMARY
================================================================================
Files deleted: 127
Files kept: 3,456  
Total processed: 3,583

Deleted files:
   - old-notes/outdated-software-guide.md
   - temporary/draft-notes-2020.md
   - ...
```

**Automatic Logs:**
- `vault_review_log.json` - Complete session record
- `.obsidian_review_progress.json` - Progress tracking (auto-cleaned)

## 🔧 Requirements

- Python 3.7+
- Dependencies: `google-generativeai`, `colorama`, `tqdm`
- Gemini API key (free from Google AI Studio)
- Internet connection for AI analysis

## 🐛 Troubleshooting

### **Common Issues:**

**API Key Error:**
```bash
export GEMINI_API_KEY="your-actual-key-here"
# Make sure quotes are included and key is valid
```

**File Permission Error:**
- Ensure write permissions for vault directory
- Check that files aren't locked by Obsidian

**Unicode/Encoding Error:**  
- Files with encoding issues are skipped with warnings
- UTF-8 encoding is assumed

**Rate Limit Issues:**
- Script includes 1-second delays between API calls
- If limits hit, script continues with default scoring

### **Performance Issues:**

**Slow Processing:**
- Configure auto-keep threshold to skip obvious high-value notes
- Use session continuation for large vaults
- Close Obsidian during review to avoid file conflicts

**Memory Usage:**
- Progress is saved incrementally  
- Large vaults are handled efficiently
- Progress bar shows memory-friendly file streaming

## 📄 License

This script is provided as-is for personal use. Please review and test thoroughly before using on important data. Always backup your vault before running cleanup operations. 