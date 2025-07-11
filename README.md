# Obsidian Vault Reviewer

An AI-powered tool that helps you clean up and organize your Obsidian vault by analyzing note relevance using Google's Gemini AI. Built specifically for second brain and zettelkasten workflows with intelligent enhancement capabilities.

## ⚠️ IMPORTANT DISCLAIMER

**USER RESPONSIBILITY WARNING**: You are solely responsible for any files that may be deleted, edited, or corrupted by this program. While the tool includes safety measures and content preservation systems, **NO SOFTWARE IS PERFECT**. This tool directly modifies your vault files and could potentially cause data loss.

**BEFORE USING THIS TOOL:**
1. **BACKUP YOUR ENTIRE VAULT** - Create a complete copy of your Obsidian vault
2. **TEST ON A COPY FIRST** - Run this tool on a backup copy before using on your main vault  
3. **REVIEW THE SOURCE CODE** - Examine the code yourself to understand what it does
4. **USE AT YOUR OWN RISK** - The authors assume no responsibility for any data loss or corruption

**By using this tool, you acknowledge that you have read, understood, and accepted full responsibility for any potential consequences to your files.**

## Key Features

- **Second Brain Optimized**: Prioritizes personal knowledge, insights, and interconnected notes
- **Auto-Decision System**: Automatically keeps high-scoring notes (7+) and optionally deletes low-scoring ones
- **AI Note Enhancement**: Transforms sparse notes into comprehensive knowledge with complete content safety
- **Atomic Note Creation**: Automatically identifies concepts and creates atomic notes following Zettelkasten principles
- **Single-Key Interface**: Fast review with k/d/v/s/e/q keys (no Enter needed)
- **Session Continuity**: Resume interrupted sessions exactly where you left off
- **WikiLink Awareness**: Heavily favors notes with internal links and tags
- **Clean Interface**: Auto-clearing screen shows only current note analysis
- **Smart Scoring**: Enhanced 0-10 scoring system emphasizing personal value
- **Security-Conscious**: Protects notes containing API keys, passwords, or credentials
- **Progress Management**: Visual progress bars and graceful interruption handling
- **Rate Limit Resilience**: Intelligent exponential backoff for API rate limiting with automatic retry

## Demo

https://github.com/user-attachments/assets/05a46ecd-9822-47e3-a73a-c9fef3392d51

## 🎯 Enhanced Scoring System

The AI uses a sophisticated second brain scoring system that heavily favors personal knowledge:

### Maximum Value (9-10 points)
- Personal financial data (investments, 401k, portfolio tracking): +5 points
- Personal medical/health records (symptoms, treatments, health tracking): +5 points  
- Original thoughts and insights (unique ideas, aha moments): +4 points
- Personal learning synthesis (combining sources with your understanding): +4 points
- Life experiences and stories (travel, relationships, major events): +4 points
- API keys, passwords, credentials: +5 points

### High Value (7-8 points)
- Personal project tracking (goals, habits, progress logs): +4 points
- Career development (job history, performance reviews, planning): +4 points
- Book notes with personal commentary (your thoughts plus highlights): +3 points
- Daily notes and journal entries (personal reflections, planning): +3 points
- Personal workflows and systems (custom templates, processes): +3 points

### Knowledge Network Value (5-7 points)
- Multiple WikiLinks (3+ internal links): +3 points
- Tags and metadata (YAML frontmatter): +3 points
- Hub/index notes (Maps of Content): +3 points
- Personal research with insights: +2 points
- Obsidian links: +2 points

### Major Penalties
- Copy-pasted content without personal input: -4 points
- No WikiLinks or tags: -3 points
- Easily recreated from Google/Wikipedia: -4 points
- Empty placeholder notes: -3 points

## Auto-Decision System

Configure intelligent automation to speed up your review:

### Auto-Keep (Default: 7+ points)
High-scoring personal notes are automatically kept, letting you focus on borderline cases.

### Auto-Delete (Optional: 2- points)  
Very low-scoring notes can be auto-deleted. This feature is disabled by default for safety.

### Configuration Example
```
Configure auto-decision settings? (y/n): y

Auto-Decision Configuration
Enable auto-keep for high-scoring notes? (currently: YES) (y/n): y
Current auto-keep threshold: 7
Enter new threshold (7-10) or press Enter to keep current: 8

Enable auto-delete for low-scoring notes? (currently: NO) (y/n): n

Show auto-decision notifications? (currently: YES) (y/n): y

Configure file size limit? (currently: 20KB max) (y/n): n

Show skipped large files? (currently: YES) (y/n): y

Include subfolders when scanning? (currently: YES) (y/n): y

Configuration saved!
Auto-keep: Notes scoring 8+ will be kept automatically
Notifications: Enabled
File size limit: 20KB maximum
Show skipped files: Enabled
Subfolders: Included
```

### Subfolder Configuration

The tool can be configured to scan only the root directory or include all subfolders:

- **Include Subfolders (Default)**: Scans all markdown files recursively throughout the vault
- **Root Only**: Scans only markdown files in the vault root directory, ignoring subfolders

This is useful for:
- **Large Vaults**: Skip subfolder archives or reference materials
- **Organized Vaults**: Focus only on top-level notes while preserving organized subfolder content
- **Selective Cleanup**: Clean main notes while keeping project-specific subfolder notes untouched

## AI Note Enhancement System

Transform sparse notes into valuable knowledge assets with complete safety:

### Enhancement Features
- **Complete Content Safety**: Triple-layer safety system ensures no existing text is ever deleted or modified
- **Atomic Note Creation**: Automatically identifies concepts that should be separate notes and creates them
- **Intelligent Linking**: Scans vault for existing notes and creates [[WikiLinks]] connections
- **Knowledge Graph Building**: Connects notes to build a comprehensive knowledge network
- **Concept Extraction**: Uses AI to identify 3-5 key concepts that deserve their own atomic notes
- **Intelligent Content Addition**: AI adds meaningful content while preserving original text
- **Automatic Re-evaluation**: Enhanced notes get fresh AI analysis
- **Score Tracking**: See immediate improvements (e.g., 5/10 to 8/10)

### Triple-Layer Safety System

**Layer 1: AI Safety Instructions**
- Explicit warnings in AI prompt to never delete or modify existing content
- Clear visual markers showing forbidden vs. allowed actions
- Repeated emphasis on preserving all original content exactly as written

**Layer 2: Content Validation**
- Automatic verification that all original content is preserved
- Line-by-line checking to ensure nothing was removed or changed
- Length validation (enhanced content must be longer than original)

**Layer 3: Safety Fallback**
- Automatic rejection if any original content is missing
- Returns original content unchanged if validation fails
- Clear user notification when safety checks trigger

## Atomic Notes & Zettelkasten Integration

The enhancement system follows atomic note principles for building a true "second brain":

### What Are Atomic Notes?
- **One Concept Per Note**: Each note contains a single, focused idea
- **Self-Contained**: Understandable without requiring other notes
- **Highly Linkable**: Designed to connect with other atomic concepts
- **Reusable**: Can be referenced in multiple contexts

### How the AI Creates Atomic Notes
1. **Concept Identification**: AI analyzes content to identify 3-5 key concepts
2. **Vault Scanning**: Checks existing notes to avoid duplicates
3. **Atomic Note Creation**: Creates new notes for concepts that don't exist
4. **Intelligent Linking**: Updates original note with [[WikiLinks]] to atomic notes
5. **Knowledge Graph Building**: Connects related concepts automatically

### Benefits of This Approach
- **No Duplicate Information**: Concepts exist once but are linked everywhere
- **Scalable Knowledge**: Easy to find and connect related ideas
- **Emergent Insights**: Connections reveal new relationships between concepts  
- **Future-Proof**: New notes automatically connect to existing atomic concepts
- **Better Search**: Find information through multiple entry points

### Example Transformation
**Before Enhancement:**
```
Machine Learning

A way to train computers to recognize patterns.
```

**After Enhancement:**
```
# Machine Learning

[[Machine Learning]] is a subset of [[Artificial Intelligence]] that enables computers to learn and improve from experience without being explicitly programmed.

## Core Concepts
- [[Pattern Recognition]] - How algorithms identify patterns in data
- [[Training Data]] - Information used to teach algorithms
- [[Model Validation]] - Testing accuracy of trained models

## Applications
- [[Computer Vision]] - Image and video analysis
- [[Natural Language Processing]] - Text and speech understanding
- [[Predictive Analytics]] - Forecasting based on historical data

## Related Topics
- [[Deep Learning]] - Advanced ML using neural networks
- [[Data Science]] - Broader field encompassing ML
- [[Statistics]] - Mathematical foundation of ML algorithms
```

**New Atomic Notes Created:**
- Pattern Recognition.md
- Training Data.md  
- Model Validation.md
- Computer Vision.md
- Natural Language Processing.md

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Get Gemini API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key (it's free)
3. **Note**: Free tier has rate limits, but the tool handles this automatically with smart retry logic

### 3. Set Your API Key

**Option A: Environment Variable (Recommended)**
```bash
export GEMINI_API_KEY="your-api-key-here"
```

**Option B: Enter When Prompted**
The script will ask for your API key when you run it.

### 4. Backup Your Vault (Recommended)

```bash
cp -r /path/to/your/vault /path/to/backup/location
```

## Usage

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

The script defaults to starting fresh sessions for safety:

```
Found previous review session from: 2024-01-15 14:30:25
Files already processed: 847
Files deleted: 23
Files kept: 824
Files enhanced: 15

Do you want to continue the previous review session? (y/n (default: n)): 
```

Press Enter to start fresh (recommended) or 'y' to resume.

### Review Interface

**Single-Key Controls (No Enter Required):**
- **k** - Keep this file
- **d** - Delete this file  
- **v** - View entire note content
- **e** - Enhance/Expand this note with AI
- **s** - Skip for now
- **q** - Quit and save progress

### Enhancement Example with Atomic Notes

```
Press a key (k/d/v/s/e/q) or Enter for default (keep): e

🤖 Enhancing note with AI...
🔍 Scanning vault for existing notes...
Found 247 existing notes
🧠 Identifying atomic concepts...
📝 Identified 3 atomic concepts: AWS Resources, Resource Identifiers, Cloud Architecture
Creating atomic note: AWS Resources
✅ Created atomic note: AWS Resources.md
Creating atomic note: Resource Identifiers  
✅ Created atomic note: Resource Identifiers.md
Atomic note already exists: Cloud Architecture

Enhanced Content Preview:
ARN (Amazon Resource Name)

Amazon Resource Names (ARNs) uniquely identify [[AWS Resources]] across all of AWS. They provide a standardized way to reference resources regardless of the AWS region or account.

## Format
ARNs follow this general format:
arn:partition:service:region:account-id:resource-type/resource-id

## Common Examples
- S3 Bucket: arn:aws:s3:::my-bucket-name
- Lambda Function: arn:aws:lambda:us-east-1:123456789012:function:my-function
- IAM Role: arn:aws:iam::123456789012:role/my-role

## Related Concepts
- [[Resource Identifiers]] - General patterns for identifying cloud resources
- [[Cloud Architecture]] - How ARNs fit into overall AWS design
- [[IAM Policies]] - How ARNs are used for permissions

Enhanced from 73 to 1,247 characters (17.1x longer)
🎉 Enhanced note with 2 new atomic notes and knowledge links

Save this enhanced version? (y/n): y
✅ Note enhanced and saved!

🔄 Re-analyzing enhanced note...
📈 Score improved from 5/10 to 9/10 (+4 points)
```

## Best Practices

### For Second Brain Optimization
1. **WikiLinks are Essential**: Notes without internal links or tags get penalty points
2. **Personal Over Generic**: Your thoughts and insights score much higher than copied content  
3. **Connected Knowledge**: Hub notes with many outgoing links are highly valued
4. **Original Synthesis**: Combining multiple sources with your understanding gets top scores

### Review Strategy
1. **Configure Auto-Decisions**: Set auto-keep at 7+ to skip obvious keepers
2. **Focus on Middle Range**: Spend time on 3-6 score notes that need human judgment
3. **Use View Option**: Press 'v' to see full content when unsure
4. **Enhance Instead of Delete**: Press 'e' to improve sparse notes rather than deleting useful stubs
5. **Trust the Re-evaluation**: Enhanced notes get fresh scoring

### Enhancement Strategy
1. **Use Fearlessly**: Complete content safety means you can enhance any note without risk
2. **Target Sparse Notes**: Perfect for basic definitions, concept stubs, short explanations
3. **Let AI Create Atomic Notes**: System automatically identifies concepts worthy of separate notes
4. **Review the Knowledge Graph**: Enhanced notes create [[WikiLink]] connections to existing notes
5. **Preview Everything**: Always review enhanced content and new atomic notes before saving
6. **Watch Score Improvements**: Enhanced notes typically jump 3-5 points due to better linking
7. **Build Connected Knowledge**: Turn isolated notes into an interconnected knowledge network

## Requirements

- Python 3.7+
- Dependencies: `google-generativeai`, `colorama`, `tqdm`
- Gemini API key (free from Google AI Studio)
- Internet connection for AI analysis and enhancement

## Troubleshooting

### Common Issues

**API Key Error:**
```bash
export GEMINI_API_KEY="your-actual-key-here"
```
Make sure quotes are included and key is valid.

**File Permission Error:**
Ensure write permissions for vault directory and that files aren't locked by Obsidian during review.

**Unicode/Encoding Error:**  
Files with encoding issues are skipped with warnings. UTF-8 encoding is assumed for all markdown files.

**Rate Limit Issues:**
Script includes intelligent rate limiting handling with exponential backoff:
- **Automatic Detection**: Detects API rate limiting errors automatically
- **Smart Retry**: Uses exponential backoff (5s → 10s → 20s → 40s → 60s) with random jitter
- **Progress Preservation**: Shows retry status without losing your review progress
- **Maximum Attempts**: Retries up to 5 times before giving up on a request
- **Graceful Degradation**: If all retries fail, the review continues with manual scoring

Example rate limit handling:
```
⏳ API rate limited. Waiting 5.3s before retry 1/5...
⏳ API rate limited. Waiting 10.7s before retry 2/5...
```

### Performance Tips
1. **Fresh Start Default**: Script defaults to starting fresh sessions for safety
2. **Start with Auto-Keep**: Configure threshold to automatically keep high-value notes
3. **Use Enhancement Liberally**: Better to enhance and keep than to delete potentially useful content
4. **Progressive Cleanup**: Review in chunks, use session continuation for large vaults
5. **Backup First**: Always backup before major cleanup sessions
6. **Smart Token Management**: Tool uses 80% of Gemini's 1M token limit, allowing vaults up to ~800K tokens to load full content
7. **Subfolder Control**: Exclude subfolders to focus on main notes and reduce token usage

## License & Responsibility

**⚠️ CRITICAL REMINDER**: See the disclaimer at the top of this document. **YOU ARE SOLELY RESPONSIBLE** for any files deleted, edited, or corrupted by this program. The authors assume **NO LIABILITY** for data loss or corruption.

This script is provided as-is for personal use. You must:
- **Read and understand the source code** before using
- **Backup your entire vault** before running any operations  
- **Test on a copy first** before using on your main vault
- **Accept full responsibility** for any consequences

**Content Safety Features**: The enhancement feature includes a triple-layer safety system designed to preserve original content, but **no software is perfect**. While the system is designed to never delete or modify existing text, you should still backup your vault and verify results.

**Use this tool entirely at your own risk.**
