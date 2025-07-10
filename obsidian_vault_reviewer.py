#!/usr/bin/env python3
"""
Obsidian Vault Reviewer
A script to review and clean up Obsidian vault notes using Gemini AI.
"""

import os
import sys
import json
import time
import signal
import re
from pathlib import Path
from typing import List, Dict, Optional
import google.generativeai as genai
from colorama import init, Fore, Style
from tqdm import tqdm

# Cross-platform single character input
try:
    # Windows
    import msvcrt
    def getch():
        return msvcrt.getch().decode('utf-8').lower()
except ImportError:
    # Unix/Linux/macOS
    import tty
    import termios
    def getch():
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1).lower()
            return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

class ObsidianVaultReviewer:
    def __init__(self, api_key: str, vault_path: str):
        """Initialize the reviewer with Gemini API key and vault path."""
        init(autoreset=True)  # Initialize colorama
        self.vault_path = Path(vault_path)
        self.api_key = api_key
        self.setup_gemini()
        self.deleted_files = []
        self.kept_files = []
        self.progress_file = self.vault_path / ".obsidian_review_progress.json"
        self.processed_files = set()  # Track which files have been processed
        self.original_session_start = time.strftime("%Y-%m-%d %H:%M:%S")  # Track session start time
        self.setup_signal_handlers()  # Handle Ctrl-C gracefully
        
    def setup_gemini(self):
        """Configure Gemini API."""
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash-lite-preview-06-17')
        
    def setup_signal_handlers(self):
        """Set up signal handlers to save progress on interruption."""
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
    def clear_screen(self):
        """Clear the terminal screen (cross-platform)."""
        os.system('cls' if os.name == 'nt' else 'clear')
        
    def get_yes_no_input(self, prompt: str) -> bool:
        """Get a yes/no decision using single-key input."""
        while True:
            print(f"{prompt} (y/n): ", end="", flush=True)
            
            try:
                choice = getch()
                
                if choice == 'y':
                    print("y")
                    return True
                elif choice == 'n':
                    print("n")  
                    return False
                else:
                    print(f"{choice} - Invalid choice. Please press 'y' for yes or 'n' for no.")
            except (KeyboardInterrupt, EOFError):
                print("\nExiting...")
                sys.exit(0)
        
    def signal_handler(self, signum, frame):
        """Handle interruption signals (Ctrl-C) gracefully."""
        print(f"\n\n🛑 Interrupted! Saving progress...")
        try:
            self.save_progress()
            print("✅ Progress saved successfully.")
            print("You can continue the review by running the script again.")
        except Exception as e:
            print(f"❌ Failed to save progress: {e}")
            print("Some progress may be lost.")
        sys.exit(0)
        
    def format_markdown_preview(self, content: str, max_length: int = 600) -> str:
        """Format markdown content for a readable preview."""
        lines = content.split('\n')
        formatted_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Handle headers
            if line.startswith('#'):
                level = len(line) - len(line.lstrip('#'))
                header_text = line.lstrip('# ').strip()
                # Apply bold and italic formatting to header text
                formatted_header = re.sub(r'\*\*([^*]+)\*\*', rf'{Style.BRIGHT}\1{Style.NORMAL}', header_text)
                formatted_header = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', rf'\033[3m\1\033[0m', formatted_header)
                if level == 1:
                    formatted_lines.append(f"\n📋 {formatted_header}")
                elif level == 2:
                    formatted_lines.append(f"\n📌 {formatted_header}")
                else:
                    formatted_lines.append(f"\n• {formatted_header}")
                    
            # Handle tables
            elif '|' in line and line.count('|') >= 2:
                # Parse table row
                cells = [cell.strip() for cell in line.split('|')[1:-1]]  # Remove empty first/last
                if len(cells) > 0:
                    # Skip table separator lines
                    if not all(c in '-:| ' for c in line):
                        # Apply bold formatting to cells
                        formatted_cells = []
                        for cell in cells:
                            formatted_cell = re.sub(r'\*\*([^*]+)\*\*', rf'{Style.BRIGHT}\1{Style.NORMAL}', cell)
                            formatted_cell = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', rf'\033[3m\1\033[0m', formatted_cell)
                            formatted_cells.append(formatted_cell)
                        formatted_lines.append(f"  {' • '.join(formatted_cells)}")
                        
            # Handle lists
            elif line.startswith(('- ', '* ', '+ ')):
                list_content = re.sub(r'\*\*([^*]+)\*\*', rf'{Style.BRIGHT}\1{Style.NORMAL}', line[2:])
                list_content = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', rf'\033[3m\1\033[0m', list_content)
                formatted_lines.append(f"  • {list_content}")
            elif re.match(r'^\d+\. ', line):
                list_content = re.sub(r'\*\*([^*]+)\*\*', rf'{Style.BRIGHT}\1{Style.NORMAL}', line)
                list_content = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', rf'\033[3m\1\033[0m', list_content)
                formatted_lines.append(f"  {list_content}")
                
            # Handle code blocks (skip content but show indicator)
            elif line.startswith('```'):
                formatted_lines.append("  [Code Block]")
                
            # Handle regular text
            else:
                # Remove markdown links and formatting, but preserve bold
                cleaned = re.sub(r'\[\[([^\]]+)\]\]', r'→\1', line)  # Obsidian links
                cleaned = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', cleaned)  # Regular links
                cleaned = re.sub(r'\*\*([^*]+)\*\*', rf'{Style.BRIGHT}\1{Style.NORMAL}', cleaned)  # Bold
                cleaned = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', rf'\033[3m\1\033[0m', cleaned)  # Italic (true italics)
                if cleaned.strip():
                    formatted_lines.append(f"  {cleaned}")
        
        # Join and truncate
        preview_text = '\n'.join(formatted_lines)
        if len(preview_text) > max_length:
            preview_text = preview_text[:max_length] + "..."
            
        return preview_text

    def format_markdown_table(self, content: str) -> str:
        """Format markdown tables for better readability."""
        lines = content.split('\n')
        formatted_lines = []
        in_table = False
        
        for line in lines:
            if '|' in line and line.count('|') >= 2:
                # This looks like a table row
                cells = [cell.strip() for cell in line.split('|')[1:-1]]
                
                # Skip separator lines
                if all(c in '-:| ' for c in line):
                    if not in_table:
                        formatted_lines.append("  " + "─" * 60)
                    in_table = True
                    continue
                    
                if len(cells) > 0:
                    # Apply bold formatting to cells and format table row with better spacing
                    formatted_cells = []
                    for cell in cells:
                        # Apply bold and italic formatting to cell content
                        formatted_cell = re.sub(r'\*\*([^*]+)\*\*', rf'{Style.BRIGHT}\1{Style.NORMAL}', cell)
                        formatted_cell = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', rf'\033[3m\1\033[0m', formatted_cell)
                        # Calculate visual width (excluding ANSI codes) for proper spacing
                        visual_width = len(re.sub(r'\x1b\[[0-9;]*m', '', formatted_cell))
                        padding = max(0, 15 - visual_width)
                        formatted_cells.append(formatted_cell + ' ' * padding)
                    
                    formatted_row = "  │ " + " │ ".join(formatted_cells) + " │"
                    formatted_lines.append(formatted_row)
                    in_table = True
            else:
                if in_table:
                    formatted_lines.append("  " + "─" * 60)
                    in_table = False
                formatted_lines.append(line)
                
        if in_table:
            formatted_lines.append("  " + "─" * 60)
            
        return '\n'.join(formatted_lines)
        
    def make_clickable_path(self, file_path: Path) -> str:
        """Create a clickable file path that opens in Obsidian or default application."""
        # Get absolute path for file:// URL
        abs_path = file_path.resolve()
        
        # Try to create Obsidian URL (obsidian://open?file=...)
        rel_path = file_path.relative_to(self.vault_path)
        vault_name = self.vault_path.name
        obsidian_url = f"obsidian://open?vault={vault_name}&file={rel_path}"
        
        # Create clickable link with both Obsidian and file URLs as fallback
        clickable = f"\033]8;;{obsidian_url}\033\\{file_path.name}\033]8;;\033\\"
        
        return clickable
        
    def save_progress(self):
        """Save current progress to file."""
        # Preserve original session start time if continuing a session
        session_start = getattr(self, 'original_session_start', time.strftime("%Y-%m-%d %H:%M:%S"))
        
        progress_data = {
            "session_start": session_start,
            "vault_path": str(self.vault_path),
            "processed_files": list(self.processed_files),
            "deleted_files": [str(f) for f in self.deleted_files],
            "kept_files": [str(f) for f in self.kept_files],
            "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        try:
            with open(self.progress_file, 'w') as f:
                json.dump(progress_data, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save progress: {e}")
            
    def load_progress(self) -> bool:
        """Load progress from file if it exists. Returns True if progress was loaded."""
        if not self.progress_file.exists():
            return False
            
        try:
            with open(self.progress_file, 'r') as f:
                progress_data = json.load(f)
                
            # Verify this progress file is for the same vault
            if progress_data.get("vault_path") != str(self.vault_path):
                print(f"Progress file is for a different vault: {progress_data.get('vault_path')}")
                return False
                
            # Load progress
            self.processed_files = set(progress_data.get("processed_files", []))
            self.deleted_files = [Path(f) for f in progress_data.get("deleted_files", [])]
            self.kept_files = [Path(f) for f in progress_data.get("kept_files", [])]
            self.original_session_start = progress_data.get("session_start", time.strftime("%Y-%m-%d %H:%M:%S"))
            
            print(f"Found previous review session from: {progress_data.get('session_start', 'Unknown')}")
            print(f"Files already processed: {len(self.processed_files)}")
            print(f"Files deleted: {len(self.deleted_files)}")
            print(f"Files kept: {len(self.kept_files)}")
            
            return True
            
        except Exception as e:
            print(f"Error loading progress file: {e}")
            return False
            
    def cleanup_progress_file(self):
        """Remove the progress file when review is complete."""
        try:
            if self.progress_file.exists():
                self.progress_file.unlink()
                print("Progress file cleaned up.")
        except Exception as e:
            print(f"Warning: Failed to cleanup progress file: {e}")
        
    def find_markdown_files(self) -> List[Path]:
        """Recursively find all markdown files in the vault."""
        print(f"Scanning vault: {self.vault_path}")
        md_files = list(self.vault_path.rglob("*.md"))
        md_files.sort()  # Sort files alphabetically
        print(f"Found {len(md_files)} markdown files")
        
        # Filter out already processed files
        if self.processed_files:
            unprocessed_files = [f for f in md_files if str(f) not in self.processed_files]
            print(f"Unprocessed files: {len(unprocessed_files)}")
            return unprocessed_files
        
        return md_files
        
    def read_file_content(self, file_path: Path) -> str:
        """Read the content of a markdown file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return ""
            
    def analyze_note_relevance(self, file_path: Path, content: str) -> Dict:
        """Use Gemini to analyze note relevance and provide scoring."""
        if not content.strip():
            return {
                "score": 0,
                "reasoning": "Empty file with no content",
                "recommendation": "delete"
            }
            
        prompt = f"""
Analyze this Obsidian note and provide a relevance assessment:

File: {file_path.name}
Path: {file_path.relative_to(self.vault_path)}

Content:
{content[:2000]}...

Please provide:
1. A relevance score from 0-10 where:
   - 0-2: Outdated, redundant, or no value (should delete)
   - 3-4: Low value, probably safe to delete
   - 5-6: Moderate value, review carefully
   - 7-8: High value, likely keep
   - 9-10: Essential content, definitely keep

2. Brief reasoning for the score
3. Recommendation: "keep" or "delete"

Consider factors like:
- Content quality and depth
- Uniqueness of information
- Practical utility
- Recency and relevance
- Whether it's a template, reference, or personal note

**CRITICAL SCORING RULES - PERSONAL KNOWLEDGE IS MOST VALUABLE:**

**MAXIMUM VALUE (+4-5 points each) - Core "Second Brain" Content:**
- **Personal financial data** (401k, investments, portfolio tracking, bank info, taxes): +5 points (irreplaceable personal records)
- **Personal medical/health records** (symptoms, treatments, doctor visits, health tracking): +5 points (important health history)
- **Original thoughts and insights** (personal reflections, unique ideas, "aha moments"): +4 points (irreplaceable creativity)
- **Personal learning synthesis** (combining multiple sources with your own understanding): +4 points (knowledge building)
- **Life experiences and stories** (travel, relationships, major events, lessons learned): +4 points (personal history)
- **API keys, passwords, credentials, secrets**: +5 points (critical security info)

**HIGH VALUE (+3-4 points each) - Personal Development & Systems:**
- **Personal project tracking** (goals, habits, progress logs, reviews): +4 points (self-improvement data)
- **Career development** (job history, performance reviews, salary info, career planning): +4 points (career tracking)
- **Personal workflows and systems** (custom templates, processes you created): +3 points (reusable personal systems)
- **Book notes with personal commentary** (highlights + your thoughts and connections): +3 points (learning with insight)
- **Meeting notes with personal action items** (decisions you made, follow-ups): +3 points (personal responsibility tracking)
- **Time-series data/tracking** (charts, logs, measurements over time): +3 points (historical value)
- **Daily notes and journal entries** (personal reflections, mood, daily planning): +3 points (life documentation)

**SOLID VALUE (+2-3 points each) - Knowledge Network & Organization:**
- **Hub/index notes** with many outgoing links (MOCs - Maps of Content): +3 points (central to knowledge network)
- **Multiple WikiLinks [[note name]]** (3+ internal links): +3 points (highly interconnected knowledge)
- **Tags and metadata** (#tag, YAML frontmatter): +3 points (organized knowledge structure)
- **Personal contacts/relationships** (addresses, phone numbers, personal notes about people): +3 points (relationship management)
- **Personal research with insights** (your questions, hypotheses, conclusions): +2 points (original investigation)
- **Project planning and documentation** (your projects, not work assignments): +2 points (personal organization)
- **Obsidian links [[note name]]** connecting to other notes: +2 points (shows interconnectedness)
- **Personal definitions and explanations** (your way of understanding complex topics): +2 points (personal knowledge building)

**MINOR VALUE (+1-2 points each) - Supporting Content:**
- **Learning notes with some personal insight** (courses, tutorials with your notes): +2 points (active learning)
- **Reference materials you curated** (useful links, resources you collected): +1 point (personal curation)
- **Templates from others you modified** (adapted to your needs): +1 point (personalization)
- **Event notes** (conferences, talks you attended with takeaways): +1 point (learning documentation)

**MAJOR PENALTIES (-3-4 points each) - Anti-"Second Brain" Content:**
- **Copy-pasted content without personal input**: -4 points (not your thoughts, just storage)
- **Easily recreated from Google/Wikipedia**: -4 points (generic information, not personal knowledge)
- **Temporary/outdated task lists** (completed todos, old project notes): -3 points (served their purpose)
- **Duplicate information** (same content in multiple places): -3 points (knowledge fragmentation)
- **Empty placeholder notes** (titles with no content, "TODO" notes never filled): -3 points (intellectual debt)

**MODERATE PENALTIES (-2-3 points each) - Reduced Value Content:**
- **No WikiLinks or tags**: -3 points (isolated from knowledge network, defeats Obsidian's purpose)
- **No Obsidian links [[note name]]**: -3 points (not connected to other notes, missing knowledge graph value)
- **No tags or metadata**: -2 points (poor organization, hard to find and categorize)
- **Outdated technology/software notes** (unless personal setup): -2 points (temporal relevance lost)
- **Generic templates from internet** (unchanged, not personalized): -2 points (not your system)
- **Pure link collections** (no commentary, context, or personal organization): -2 points (no added value)
- **Work-only content** (company-specific info with no personal insight): -2 points (less relevant to personal knowledge)

**REMEMBER: Personal = Valuable. WikiLinks/Tags = Essential. Any note containing personal data, tracking, or financial information should score 7+ points. Notes with WikiLinks [[note name]] and tags #tag are the backbone of your knowledge network and should be strongly favored.**

Respond in JSON format:
{{
    "score": <number>,
    "reasoning": "<brief explanation>",
    "recommendation": "<keep|delete>"
}}
"""

        try:
            response = self.model.generate_content(prompt)
            # Extract JSON from response
            response_text = response.text.strip()
            # Remove markdown code blocks if present
            if response_text.startswith('```json'):
                response_text = response_text.split('```json')[1].split('```')[0]
            elif response_text.startswith('```'):
                response_text = response_text.split('```')[1].split('```')[0]
                
            result = json.loads(response_text)
            return result
            
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
            return {
                "score": 5,
                "reasoning": f"Analysis failed: {e}",
                "recommendation": "keep"
            }
            
    def display_analysis(self, file_path: Path, analysis: Dict, content: str):
        """Display the analysis results to the user."""
        print("\n" + "="*80)
        clickable_name = self.make_clickable_path(file_path)
        print(f"📄 File: {Fore.CYAN}{clickable_name}{Style.RESET_ALL}")
        print(f"📁 Path: {file_path.relative_to(self.vault_path)}")
        print(f"📊 Size: {len(content):,} characters")
        
        # Color-coded relevance score
        score = analysis['score']
        if score <= 2:
            color = Fore.RED
        elif score <= 4:
            color = Fore.YELLOW
        elif score <= 6:
            color = Fore.CYAN
        elif score <= 8:
            color = Fore.GREEN
        else:
            color = Fore.LIGHTGREEN_EX
            
        print(f"⭐ Relevance Score: {color}{score}/10{Style.RESET_ALL}")
        
        # Show formatted preview
        print(f"\n{Fore.LIGHTBLUE_EX}📖 Preview:{Style.RESET_ALL}")
        preview = self.format_markdown_preview(content, 600)
        print(preview)
        
        print(f"\n{Fore.LIGHTMAGENTA_EX}🤖 AI Reasoning:{Style.RESET_ALL}")
        print(f"  {analysis['reasoning']}")
        
        # Color-coded AI recommendation
        recommendation = analysis['recommendation'].upper()
        if recommendation == 'DELETE':
            rec_color = Fore.RED
            emoji = "🗑️"
        else:
            rec_color = Fore.GREEN
            emoji = "✅"
            
        print(f"\n{emoji} AI Recommendation: {rec_color}{recommendation}{Style.RESET_ALL}")
        print("="*80)
        
    def display_analysis_with_tqdm(self, file_path: Path, analysis: Dict, content: str):
        """Display the analysis results using tqdm.write to avoid interfering with progress bar."""
        tqdm.write("\n" + "="*80)
        clickable_name = self.make_clickable_path(file_path)
        tqdm.write(f"📄 File: {Fore.CYAN}{clickable_name}{Style.RESET_ALL}")
        tqdm.write(f"📁 Path: {file_path.relative_to(self.vault_path)}")
        tqdm.write(f"📊 Size: {len(content):,} characters")
        
        # Color-coded relevance score
        score = analysis['score']
        if score <= 2:
            color = Fore.RED
        elif score <= 4:
            color = Fore.YELLOW
        elif score <= 6:
            color = Fore.CYAN
        elif score <= 8:
            color = Fore.GREEN
        else:
            color = Fore.LIGHTGREEN_EX
            
        tqdm.write(f"⭐ Relevance Score: {color}{score}/10{Style.RESET_ALL}")
        
        # Show formatted preview
        tqdm.write(f"\n{Fore.LIGHTBLUE_EX}📖 Preview:{Style.RESET_ALL}")
        preview = self.format_markdown_preview(content, 600)
        tqdm.write(preview)
        
        tqdm.write(f"\n{Fore.LIGHTMAGENTA_EX}🤖 AI Reasoning:{Style.RESET_ALL}")
        tqdm.write(f"  {analysis['reasoning']}")
        
        # Color-coded AI recommendation
        recommendation = analysis['recommendation'].upper()
        if recommendation == 'DELETE':
            rec_color = Fore.RED
            emoji = "🗑️"
        else:
            rec_color = Fore.GREEN
            emoji = "✅"
            
        tqdm.write(f"\n{emoji} AI Recommendation: {rec_color}{recommendation}{Style.RESET_ALL}")
        tqdm.write("="*80)
        
    def get_user_decision(self, analysis: Dict) -> str:
        """Get user decision on whether to keep or delete the file."""
        while True:
            print("\nWhat would you like to do?")
            print("  [k] Keep this file (default)")
            print("  [d] Delete this file")
            print("  [v] View entire note content")
            print("  [s] Skip for now")
            print("  [q] Quit the review process")
            
            print("\nPress a key (k/d/v/s/q) or Enter for default (keep): ", end="", flush=True)
            
            try:
                choice = getch()
                
                # Handle Enter key (newline)
                if choice in ['\r', '\n', '']:
                    print("k (default)")
                    return 'keep'
                elif choice == 'k':
                    print("k")
                    return 'keep'
                elif choice == 'd':
                    print("d")
                    return 'delete'
                elif choice == 'v':
                    print("v")
                    return 'view'
                elif choice == 's':
                    print("s")
                    return 'skip'
                elif choice == 'q':
                    print("q")
                    return 'quit'
                else:
                    print(f"{choice} - Invalid choice. Please press k, d, v, s, q, or Enter for default (keep).")
            except (KeyboardInterrupt, EOFError):
                print("\nq")
                return 'quit'
                
    def display_full_content(self, file_path: Path, content: str):
        """Display the full content of a note with better formatting."""
        print("\n" + "="*80)
        clickable_name = self.make_clickable_path(file_path)
        print(f"📄 FULL CONTENT: {Fore.CYAN}{clickable_name}{Style.RESET_ALL}")
        print(f"📁 Path: {file_path.relative_to(self.vault_path)}")
        print(f"📊 Size: {len(content):,} characters")
        print("="*80)
        
        # Format the content for better readability
        formatted_content = self.format_markdown_table(content)
        # Apply bold and italic formatting to the entire content
        formatted_content = re.sub(r'\*\*([^*]+)\*\*', rf'{Style.BRIGHT}\1{Style.NORMAL}', formatted_content)
        formatted_content = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', rf'\033[3m\1\033[0m', formatted_content)
        print(formatted_content)
        
        print("="*80)
        print(f"{Fore.GREEN}📝 End of file content{Style.RESET_ALL}")
        print("="*80)
        
    def display_full_content_with_tqdm(self, file_path: Path, content: str):
        """Display the full content of a note using tqdm.write."""
        tqdm.write("\n" + "="*80)
        clickable_name = self.make_clickable_path(file_path)
        tqdm.write(f"📄 FULL CONTENT: {Fore.CYAN}{clickable_name}{Style.RESET_ALL}")
        tqdm.write(f"📁 Path: {file_path.relative_to(self.vault_path)}")
        tqdm.write(f"📊 Size: {len(content):,} characters")
        tqdm.write("="*80)
        
        # Format the content for better readability
        formatted_content = self.format_markdown_table(content)
        # Apply bold and italic formatting to the entire content
        formatted_content = re.sub(r'\*\*([^*]+)\*\*', rf'{Style.BRIGHT}\1{Style.NORMAL}', formatted_content)
        formatted_content = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', rf'\033[3m\1\033[0m', formatted_content)
        tqdm.write(formatted_content)
        
        tqdm.write("="*80)
        tqdm.write(f"{Fore.GREEN}📝 End of file content{Style.RESET_ALL}")
        tqdm.write("="*80)
        
    def delete_file(self, file_path: Path) -> bool:
        """Delete a file and return success status."""
        try:
            file_path.unlink()
            print(f"Deleted: {file_path}")
            return True
        except Exception as e:
            print(f"Failed to delete {file_path}: {e}")
            return False
            
    def save_session_log(self):
        """Save a log of the review session."""
        log_data = {
            "session_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "vault_path": str(self.vault_path),
            "deleted_files": [str(f) for f in self.deleted_files],
            "kept_files": [str(f) for f in self.kept_files],
            "total_deleted": len(self.deleted_files),
            "total_kept": len(self.kept_files)
        }
        
        log_file = self.vault_path / "vault_review_log.json"
        try:
            with open(log_file, 'w') as f:
                json.dump(log_data, f, indent=2)
            print(f"\nSession log saved to: {log_file}")
        except Exception as e:
            print(f"Failed to save log: {e}")
            
    def review_vault(self):
        """Main method to review the entire vault."""
        print("Starting Obsidian Vault Review")
        print("="*50)
        
        # Check for existing progress
        continuing_session = False
        if self.load_progress():
            continuing_session = self.get_yes_no_input("\nDo you want to continue the previous review session?")
            if continuing_session:
                print("Continuing previous session...")
            else:
                print("Starting fresh review session...")
                # Reset progress
                self.processed_files = set()
                self.deleted_files = []
                self.kept_files = []
        
        # Find all markdown files
        md_files = self.find_markdown_files()
        
        if not md_files:
            if continuing_session:
                print("All files have been processed in the previous session!")
                self.show_summary()
                self.cleanup_progress_file()
                return
            else:
                print("No markdown files found in the vault.")
                return
                
        total_files = len(md_files) + len(self.processed_files)
        processed_count = len(self.processed_files)
        
        print(f"\nReady to review {len(md_files)} remaining files")
        if continuing_session:
            print(f"Progress: {processed_count}/{total_files} files already processed")
        print("Tip: Consider backing up your vault before proceeding!")
        
        # Save initial progress to create the file
        self.save_progress()
        
        # Clear screen to start fresh
        self.clear_screen()
        print("🚀 Starting Obsidian Vault Review")
        print("="*50)
        print(f"Reviewing {len(md_files)} remaining files")
        if continuing_session:
            print(f"Progress: {processed_count}/{total_files} files already processed")
        print("")
        
        # Create progress bar
        progress_bar = tqdm(
            total=total_files,
            desc="Reviewing files",
            initial=processed_count,
            unit="files",
            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} files [{elapsed}<{remaining}, {rate_fmt}]"
        )
        
        try:
            for i, file_path in enumerate(md_files, 1):
                current_position = processed_count + i
                
                # Update progress bar description with current file
                progress_bar.set_description(f"Processing: {file_path.name[:30]}...")
                
                # Read file content
                content = self.read_file_content(file_path)
                
                # Analyze with Gemini
                tqdm.write(f"\nAnalyzing: {file_path.name}...")
                analysis = self.analyze_note_relevance(file_path, content)
                
                # Display results using tqdm.write to avoid interfering with progress bar
                self.display_analysis_with_tqdm(file_path, analysis, content)
                
                # Get user decision (loop until they make a final choice)
                while True:
                    decision = self.get_user_decision(analysis)
                    
                    if decision == 'quit':
                        tqdm.write("\nReview process stopped by user.")
                        tqdm.write("Progress has been saved. You can continue later by running the script again.")
                        break
                    elif decision == 'view':
                        self.display_full_content_with_tqdm(file_path, content)
                        # Clear screen after viewing full content and re-display analysis
                        self.clear_screen()
                        # Show progress after clearing screen
                        current_progress = processed_count + i
                        tqdm.write(f"Progress: {current_progress}/{total_files} files processed ({current_progress/total_files*100:.1f}%)")
                        tqdm.write("")  # Add blank line for readability
                        self.display_analysis_with_tqdm(file_path, analysis, content)
                        # Continue the loop to ask for decision again
                        continue
                    elif decision == 'delete':
                        if self.delete_file(file_path):
                            self.deleted_files.append(file_path)
                        self.processed_files.add(str(file_path))
                        self.save_progress()  # Save progress after each file
                        break
                    elif decision == 'keep':
                        self.kept_files.append(file_path)
                        tqdm.write(f"Kept: {file_path}")
                        self.processed_files.add(str(file_path))
                        self.save_progress()  # Save progress after each file
                        break
                    elif decision == 'skip':
                        tqdm.write(f"Skipped: {file_path}")
                        self.processed_files.add(str(file_path))
                        self.save_progress()  # Save progress after each file
                        break
                        
                # Update progress bar
                progress_bar.update(1)
                        
                # Break out of outer loop if user chose quit
                if decision == 'quit':
                    break
                    
                # Clear screen before next file to reduce clutter
                if decision != 'quit':
                    self.clear_screen()
                    # Show progress after clearing screen
                    current_progress = processed_count + i
                    tqdm.write(f"Progress: {current_progress}/{total_files} files processed ({current_progress/total_files*100:.1f}%)")
                    tqdm.write("")  # Add blank line for readability
                    
                # Small delay to avoid API rate limits
                time.sleep(1)
                
        finally:
            # Close progress bar
            progress_bar.close()
            
        # Show summary and cleanup
        self.show_summary()
        self.save_session_log()
        
        # If we completed all files, cleanup progress file
        if decision != 'quit':
            self.cleanup_progress_file()
        
    def show_summary(self):
        """Display summary of the review session."""
        print("\n" + "="*60)
        print("REVIEW SESSION SUMMARY")
        print("="*60)
        print(f"{Fore.RED}Files deleted: {len(self.deleted_files)}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}Files kept: {len(self.kept_files)}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Total processed: {len(self.deleted_files) + len(self.kept_files)}{Style.RESET_ALL}")
        
        if self.deleted_files:
            print(f"\n{Fore.RED}Deleted files:{Style.RESET_ALL}")
            for file_path in self.deleted_files:
                print(f"   - {file_path.relative_to(self.vault_path)}")


def main():
    """Main function to run the vault reviewer."""
    print("Obsidian Vault Reviewer")
    print("="*40)
    
    # Get API key
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("\nAPI Key Options:")
        print("   1. Set environment variable: export GEMINI_API_KEY='your-key-here'")
        print("   2. Or enter it now when prompted")
        print("   Get your key at: https://makersuite.google.com/app/apikey")
        api_key = input("\nEnter your Gemini API key: ").strip()
        if not api_key:
            print("API key is required!")
            sys.exit(1)
    
    # Get vault path (default to current directory)
    while True:
        vault_path = input(f"Enter vault path (default: current directory): ").strip()
        if not vault_path:
            vault_path = os.getcwd()
            
        if os.path.exists(vault_path):
            break
        else:
            print(f"❌ Vault path does not exist: {vault_path}")
            print("Please enter a valid directory path or press Enter for current directory.")
            continue
        
    # Create reviewer and start
    reviewer = ObsidianVaultReviewer(api_key, vault_path)
    reviewer.review_vault()


if __name__ == "__main__":
    main() 