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
from pathlib import Path
from typing import List, Dict, Optional
import google.generativeai as genai
from colorama import init, Fore, Style

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

**CRITICAL SCORING RULES - PERSONAL DATA IS VALUABLE:**

**MAJOR BONUSES (+3-4 points each):**
- **Personal financial data** (401k, investments, portfolio tracking, bank info, taxes): +4 points (irreplaceable personal records)
- **Personal medical/health records** (symptoms, treatments, doctor visits): +4 points (important health history)
- **Personal career data** (job history, performance reviews, salary info): +3 points (career tracking)
- **Personal project tracking** (goals, habits, progress logs): +3 points (self-improvement data)
- **API keys, passwords, credentials, secrets**: +4 points (critical security info)
- **Personal contacts/relationships** (addresses, phone numbers, personal notes about people): +3 points

**SIGNIFICANT BONUSES (+2-3 points each):**
- **Time-series data/tracking** (charts, logs, measurements over time): +3 points (historical value)
- **Hub/index notes** with many outgoing links: +3 points (central to knowledge network)
- **Personal autobiographical content** (diary, memories, experiences): +2 points (unique life data)
- **Templates and workflows** you created: +2 points (reusable personal systems)
- **Obsidian links [[note name]]** connecting to other notes: +2 points (shows interconnectedness)

**MINOR BONUSES (+1 point each):**
- **Meeting notes** with action items or decisions: +1 point
- **Research notes** with sources and synthesis: +1 point
- **Learning notes** with personal insights: +1 point

**PENALTIES (-2-3 points each):**
- **Easily recreated from Google/Wikipedia**: -3 points (generic information)
- **Outdated technology/software notes**: -2 points (unless personal setup)
- **Empty or minimal content**: -2 points

**REMEMBER: Personal = Valuable. Any note containing personal data, tracking, or financial information should score 7+ points.**

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
        print(f"File: {file_path.name}")
        print(f"Path: {file_path.relative_to(self.vault_path)}")
        print(f"Size: {len(content)} characters")
        
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
            
        print(f"Relevance Score: {color}{score}/10{Style.RESET_ALL}")
        
        # Show preview of content (larger and above reasoning)
        preview = content[:800].replace('\n', ' ')
        if len(content) > 800:
            preview += "..."
        print(f"Preview: {preview}")
        print(f"AI Reasoning: {analysis['reasoning']}")
        
        # Color-coded AI recommendation
        recommendation = analysis['recommendation'].upper()
        if recommendation == 'DELETE':
            rec_color = Fore.RED
        else:
            rec_color = Fore.GREEN
            
        print(f"AI Recommendation: {rec_color}{recommendation}{Style.RESET_ALL}")
        print("="*80)
        
    def get_user_decision(self, analysis: Dict) -> str:
        """Get user decision on whether to keep or delete the file."""
        while True:
            print("\nWhat would you like to do?")
            print("  [k] Keep this file")
            print("  [d] Delete this file")
            print("  [v] View entire note content")
            print("  [s] Skip for now")
            print("  [q] Quit the review process")
            
            choice = input("\nEnter your choice (k/d/v/s/q): ").lower().strip()
            
            if choice in ['k', 'keep']:
                return 'keep'
            elif choice in ['d', 'delete']:
                return 'delete'
            elif choice in ['v', 'view']:
                return 'view'
            elif choice in ['s', 'skip']:
                return 'skip'
            elif choice in ['q', 'quit']:
                return 'quit'
            else:
                print("Invalid choice. Please enter k, d, v, s, or q.")
                
    def display_full_content(self, file_path: Path, content: str):
        """Display the full content of a note."""
        print("\n" + "="*80)
        print(f"FULL CONTENT: {file_path.name}")
        print(f"Path: {file_path.relative_to(self.vault_path)}")
        print("="*80)
        print(content)
        print("="*80)
        print("End of file content")
        print("="*80)
        
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
            while True:
                choice = input("\nDo you want to continue the previous review session? (y/n): ").lower().strip()
                if choice in ['y', 'yes']:
                    continuing_session = True
                    print("Continuing previous session...")
                    break
                elif choice in ['n', 'no']:
                    print("Starting fresh review session...")
                    # Reset progress
                    self.processed_files = set()
                    self.deleted_files = []
                    self.kept_files = []
                    break
                else:
                    print("Please enter 'y' or 'n'")
        
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
        
        input("\nPress Enter to start the review process...")
        
        # Save initial progress to create the file
        self.save_progress()
        
        for i, file_path in enumerate(md_files, 1):
            current_position = processed_count + i
            print(f"\nProgress: {current_position}/{total_files} files")
            
            # Read file content
            content = self.read_file_content(file_path)
            
            # Analyze with Gemini
            print(f"Analyzing: {file_path.name}...")
            analysis = self.analyze_note_relevance(file_path, content)
            
            # Display results
            self.display_analysis(file_path, analysis, content)
            
            # Get user decision (loop until they make a final choice)
            while True:
                decision = self.get_user_decision(analysis)
                
                if decision == 'quit':
                    print("\nReview process stopped by user.")
                    print("Progress has been saved. You can continue later by running the script again.")
                    break
                elif decision == 'view':
                    self.display_full_content(file_path, content)
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
                    print(f"Kept: {file_path}")
                    self.processed_files.add(str(file_path))
                    self.save_progress()  # Save progress after each file
                    break
                elif decision == 'skip':
                    print(f"Skipped: {file_path}")
                    self.processed_files.add(str(file_path))
                    self.save_progress()  # Save progress after each file
                    break
                    
            # Break out of outer loop if user chose quit
            if decision == 'quit':
                break
                
            # Small delay to avoid API rate limits
            time.sleep(1)
            
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