# Obsidian Vault Reviewer

An AI-powered tool to help you clean up and organize your Obsidian vault by analyzing note relevance using Google's Gemini AI. Designed specifically for "second brain" and zettelkasten workflows with intelligent enhancement capabilities.

## ✨ Key Features

- 🧠 **"Second Brain" Optimized**: Prioritizes personal knowledge, insights, and interconnected notes
- 🤖 **Auto-Decision System**: Automatically keeps high-scoring notes (7+) and optionally deletes low-scoring ones
- ✨ **AI Note Enhancement**: Transform sparse notes into comprehensive knowledge with automatic re-evaluation
- ⚡ **Single-Key Interface**: Fast review with k/d/v/s/e/q keys - no Enter needed!
- 📊 **Session Continuity**: Resume interrupted sessions exactly where you left off
- 🔗 **WikiLink Aware**: Heavily favors notes with [[internal links]] and #tags
- 🖥️ **Clean Interface**: Auto-clearing screen shows only current note analysis
- 🎯 **Smart Scoring**: Enhanced 0-10 scoring system emphasizing personal value
- 🔐 **Security-Conscious**: Protects notes containing API keys, passwords, or credentials
- 📋 **Progress Management**: Visual progress bars, graceful interruption handling
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

## ✨ AI Note Enhancement System

The most innovative feature - transform sparse notes into valuable knowledge assets:

### **Enhancement Features:**
- **Intelligent Content Addition**: AI adds 1-2 meaningful paragraphs
- **Preserves Original Content**: Never overwrites your existing text
- **Adds WikiLinks**: Automatically suggests [[related concepts]]
- **Includes Examples**: Practical use cases and real-world applications
- **Improves Structure**: Better formatting, headers, and organization
- **Automatic Re-evaluation**: Enhanced notes get fresh AI analysis
- **Score Tracking**: See immediate improvements (e.g., 5/10 → 8/10)

### **Enhancement Workflow:**
1. **Press 'e'** on any note during review
2. **AI Enhancement** generates expanded content (2-3x longer)
3. **Preview Enhanced Content** before deciding to save
4. **Choose to Save** or cancel enhancement
5. **Automatic Re-analysis** of enhanced note with new scoring
6. **Final Decision** on enhanced note (keep/delete/skip)

### **Perfect For:**
- Basic definitions that need depth
- Sparse notes with potential
- Concept stubs that could be expanded
- Notes lacking examples or context
- Isolated notes that need better connections

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
Files enhanced: 15

Do you want to continue the previous review session? (y/n): y
Continuing previous session...
```

### Review Interface

**Single-Key Controls (No Enter Required):**
- **k** - Keep this file (default - just press Enter)
- **d** - Delete this file  
- **v** - View entire note content
- **e** - Enhance/Expand this note with AI
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
Progress: 31/4458 files processed (0.7%)

Analyzing: Weekly-Review-Template.md...
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

Press a key (k/d/v/s/e/q) or Enter for default (keep): k
Kept: templates/Weekly-Review-Template.md
```

### Complete AI Enhancement Example

```
Progress: 32/4458 files processed (0.7%)

Analyzing: ARN.md...
================================================================================
📄 File: ARN.md
📁 Path: ARN.md
📊 Size: 73 characters
⭐ Relevance Score: 5/10

📖 Preview:
📋 ARN
  • Amazon Resource Name
  • It uniquely identifies [[AWS]] resources.

🤖 AI Reasoning:
  This note provides a basic definition but lacks depth and examples...

✅ AI Recommendation: KEEP
================================================================================

Press a key (k/d/v/s/e/q) or Enter for default (keep): e

🤖 Enhancing note with AI...

✨ Enhanced Content Preview:
================================================================================
# ARN (Amazon Resource Name)

Amazon Resource Names (ARNs) uniquely identify [[AWS]] resources across all of AWS. They provide a standardized way to reference resources regardless of the AWS region or account.

## Format
ARNs follow this general format:
`arn:partition:service:region:account-id:resource-type/resource-id`

## Common Examples
- **S3 Bucket**: `arn:aws:s3:::my-bucket-name`
- **Lambda Function**: `arn:aws:lambda:us-east-1:123456789012:function:my-function`
- **IAM Role**: `arn:aws:iam::123456789012:role/my-role`

## Use Cases
ARNs are essential for [[IAM]] policies, [[CloudFormation]] templates, and cross-service resource references. They enable precise resource targeting in complex AWS environments.

Related: [[AWS]], [[IAM]], [[S3]], [[Lambda]], [[CloudFormation]]
================================================================================

Enhanced from 73 to 847 characters (11.6x longer)
Save this enhanced version? (y/n): y
✅ Note enhanced and saved!

🔄 Re-analyzing enhanced note...

🎉 ENHANCED NOTE RE-ANALYSIS:
📈 Score improved from 5/10 to 8/10 (+3 points)

================================================================================
📄 File: ARN.md
📁 Path: ARN.md
📊 Size: 847 characters
⭐ Relevance Score: 8/10

🤖 AI Reasoning:
  This enhanced note now provides comprehensive coverage of ARNs with practical examples, format details, and use cases. The addition of multiple WikiLinks creates strong connections to related AWS concepts. Excellent reference material for personal AWS knowledge management.

✅ AI Recommendation: KEEP
================================================================================

Press a key (k/d/v/s/e/q) or Enter for default (keep): k
Enhanced note kept: ARN.md
```

## 📊 Progress Tracking & Session Management

### **Visual Progress Bar:**
```
Processing: Daily-Note-2024-01-15.md: 23%|████▌     | 1847/8012 files [15:32<45:21, 2.27files/s]
```

### **Session Features:**
- **Automatic Progress Saving** after each file decision
- **Resume Interrupted Sessions** exactly where you left off  
- **Graceful Ctrl+C Handling** saves progress before exit
- **Progress File**: `.obsidian_review_progress.json` (auto-cleanup when complete)
- **Configuration Persistence** auto-decision settings saved between sessions

### **Session Interruption Handling:**
```bash
# Press Ctrl+C at any time
^C
🛑 Interrupted! Saving progress...
✅ Progress saved successfully.
You can continue the review by running the script again.
```

## 💡 Smart Features

### **🖱️ Clickable File Paths**
File names become clickable terminal links that open directly in Obsidian:
```
📄 File: My-Important-Note.md  [Click to open in Obsidian]
```

### **🧹 Clean Interface**
- Screen clears between each file for focused analysis
- Shows only current file information and decision options
- Progress indicator shows completion status
- No accumulated clutter from previous files

### **⌨️ Fast Input System**
- Cross-platform single-key input (Windows, macOS, Linux)
- No need to press Enter for any decision
- Immediate visual feedback for key presses
- Enter key works as default (keep) for convenience

### **✨ AI Note Enhancement**
- Transform sparse notes into comprehensive knowledge
- Uses Gemini AI to add 1-2 meaningful paragraphs
- Preserves original content while expanding depth
- Adds practical examples, use cases, and [[WikiLinks]]
- Preview enhanced content before saving
- **Automatic re-evaluation** - Enhanced notes get fresh AI analysis and scoring
- See immediate score improvements (e.g., 5/10 → 8/10)
- Perfect for turning basic definitions into valuable references

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
4. **Enhance Instead of Delete**: Press 'e' to improve sparse notes rather than deleting potentially useful stubs
5. **Trust the Re-evaluation**: Enhanced notes get fresh scoring - watch for improvements
6. **Take Breaks**: Progress is saved automatically - quit and resume anytime

### **Enhancement Strategy:**
1. **Target Sparse Notes**: Perfect for basic definitions, concept stubs, short explanations
2. **Preview First**: Always review enhanced content before saving
3. **Watch Score Improvements**: Enhanced notes typically jump 2-4 points in scoring
4. **Build Your Knowledge**: Turn scattered notes into comprehensive references
5. **Create Connections**: AI adds relevant [[WikiLinks]] to build your knowledge graph

### **Performance Tips:**
1. **Start with Auto-Keep**: Configure threshold to automatically keep high-value notes
2. **Use Enhancement Liberally**: Better to enhance and keep than to delete potentially useful content
3. **Progressive Cleanup**: Review in chunks, use session continuation for large vaults
4. **Backup First**: Always backup before major cleanup sessions
5. **Monitor Progress**: Use the progress bar to estimate time remaining

## 📋 Output & Logging

### **Session Summary:**
```
================================================================================
REVIEW SESSION SUMMARY
================================================================================
Files deleted: 127
Files kept: 3,456
Files enhanced: 23
Total processed: 3,583

✨ Enhanced files:
   - ARN.md
   - API.md
   - HTTP-Status-Codes.md
   - Database-Normalization.md
   - Git-Commands.md
   - ...

🗑️ Deleted files:
   - old-notes/outdated-software-guide.md
   - temporary/draft-notes-2020.md
   - ...
```

### **Automatic Logs:**
- `vault_review_log.json` - Complete session record with enhancement tracking
- `.obsidian_review_progress.json` - Progress tracking (auto-cleaned when complete)
- Enhanced files tracked separately for post-review reference

## 🔧 Requirements

- Python 3.7+
- Dependencies: `google-generativeai`, `colorama`, `tqdm`
- Gemini API key (free from Google AI Studio)
- Internet connection for AI analysis and enhancement

## 🐛 Troubleshooting

### **Common Issues:**

**API Key Error:**
```bash
export GEMINI_API_KEY="your-actual-key-here"
# Make sure quotes are included and key is valid
```

**File Permission Error:**
- Ensure write permissions for vault directory
- Check that files aren't locked by Obsidian during review

**Unicode/Encoding Error:**  
- Files with encoding issues are skipped with warnings
- UTF-8 encoding is assumed for all markdown files

**Rate Limit Issues:**
- Script includes 1-second delays between API calls
- If limits hit, script continues with default scoring
- Enhancement uses additional API calls but includes proper throttling

### **Performance Issues:**

**Slow Processing:**
- Configure auto-keep threshold to skip obvious high-value notes
- Use session continuation for large vaults (1000+ files)
- Close Obsidian during review to avoid file conflicts
- Enhancement feature adds processing time but significantly improves note quality

**Memory Usage:**
- Progress is saved incrementally to handle large vaults
- Enhanced content is processed in memory-efficient chunks
- Progress bar shows memory-friendly file streaming

**Enhancement Quality:**
- AI enhancement quality depends on original content having some substance
- Very short notes (< 20 characters) may not enhance well
- Technical accuracy depends on AI knowledge - always review enhanced content

## 📄 License

This script is provided as-is for personal use. Please review and test thoroughly before using on important data. Always backup your vault before running cleanup operations. Enhanced notes are saved immediately - ensure you're comfortable with AI-generated additions to your knowledge base. 