# Obsidian Vault Reviewer

An AI-powered tool that helps you clean up and organize your Obsidian vault by analyzing note relevance using Google's Gemini AI. Built specifically for second brain and zettelkasten workflows with intelligent enhancement capabilities.

## Key Features

- **Second Brain Optimized**: Prioritizes personal knowledge, insights, and interconnected notes
- **Auto-Decision System**: Automatically keeps high-scoring notes (7+) and optionally deletes low-scoring ones
- **AI Note Enhancement**: Transforms sparse notes into comprehensive knowledge with complete content safety
- **Single-Key Interface**: Fast review with k/d/v/s/e/q keys (no Enter needed)
- **Session Continuity**: Resume interrupted sessions exactly where you left off
- **WikiLink Awareness**: Heavily favors notes with internal links and tags
- **Clean Interface**: Auto-clearing screen shows only current note analysis
- **Smart Scoring**: Enhanced 0-10 scoring system emphasizing personal value
- **Security-Conscious**: Protects notes containing API keys, passwords, or credentials
- **Progress Management**: Visual progress bars and graceful interruption handling

## Demo

https://github.com/user-attachments/assets/05a46ecd-9822-47e3-a73a-c9fef3392d51

## Scoring System

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
Enable auto-keep for high-scoring notes? (currently: ON) (y/n): y
Current auto-keep threshold: 7
Enter new threshold (7-10) or press Enter to keep current: 8

Enable auto-delete for low-scoring notes? (currently: OFF) (y/n): n

Show auto-decision notifications? (currently: ON) (y/n): y

Configuration saved!
Auto-keep: Notes scoring 8+ will be kept automatically
Notifications: Enabled
```

## AI Note Enhancement System

Transform sparse notes into valuable knowledge assets with complete safety:

### Enhancement Features
- **Complete Content Safety**: Triple-layer safety system ensures no existing text is ever deleted or modified
- **Intelligent Content Addition**: AI adds 1-2 meaningful paragraphs
- **Automatic WikiLinks**: Suggests related concepts
- **Practical Examples**: Real-world applications and use cases
- **Better Structure**: Improved formatting and organization
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

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Get Gemini API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key (it's free)

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

### Enhancement Example

```
Press a key (k/d/v/s/e/q) or Enter for default (keep): e

Enhancing note with AI...

Enhanced Content Preview:
ARN (Amazon Resource Name)

Amazon Resource Names (ARNs) uniquely identify AWS resources across all of AWS. They provide a standardized way to reference resources regardless of the AWS region or account.

Format
ARNs follow this general format:
arn:partition:service:region:account-id:resource-type/resource-id

Common Examples
- S3 Bucket: arn:aws:s3:::my-bucket-name
- Lambda Function: arn:aws:lambda:us-east-1:123456789012:function:my-function
- IAM Role: arn:aws:iam::123456789012:role/my-role

Enhanced from 73 to 847 characters (11.6x longer)
Safety Check: All original content preserved
Save this enhanced version? (y/n): y
Note enhanced and saved!

Re-analyzing enhanced note...
Score improved from 5/10 to 8/10 (+3 points)
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
3. **Preview First**: Always review enhanced content before saving
4. **Watch Score Improvements**: Enhanced notes typically jump 2-4 points in scoring
5. **Build Your Knowledge**: Turn scattered notes into comprehensive references

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
Script includes 1-second delays between API calls. If limits are hit, script continues with default scoring.

### Performance Tips
1. **Fresh Start Default**: Script defaults to starting fresh sessions for safety
2. **Start with Auto-Keep**: Configure threshold to automatically keep high-value notes
3. **Use Enhancement Liberally**: Better to enhance and keep than to delete potentially useful content
4. **Progressive Cleanup**: Review in chunks, use session continuation for large vaults
5. **Backup First**: Always backup before major cleanup sessions

## License

This script is provided as-is for personal use. Please review and test thoroughly before using on important data. Always backup your vault before running cleanup operations.

**Content Safety Guarantee**: The enhancement feature includes a triple-layer safety system that ensures your original content is never deleted or modified. Original text is preserved character-for-character, with automatic validation and fallback protection. 