#!/usr/bin/env python3
"""
Obsidian Vault Reviewer
A script to review and clean up Obsidian vault notes using Gemini AI.
"""

import os
import sys
import json
import time
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
        
    def setup_gemini(self):
        """Configure Gemini API."""
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash-lite-preview-06-17')
        
    def find_markdown_files(self) -> List[Path]:
        """Recursively find all markdown files in the vault."""
        print(f"Scanning vault: {self.vault_path}")
        md_files = list(self.vault_path.rglob("*.md"))
        md_files.sort()  # Sort files alphabetically
        print(f"Found {len(md_files)} markdown files")
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
- **IMPORTANT: Increase score if contains sensitive information like API keys, passwords, tokens, or credentials (+2-3 points)**
- **IMPORTANT: Increase score if contains Obsidian links [[note name]] showing connections to other notes (+1-2 points)**
- **IMPORTANT: Increase score if it's a hub/index note with many outgoing links (+2-3 points)**
- **IMPORTANT: Increase score if note appears personal/autobiographical (+1-2 points)**
- **IMPORTANT: Decrease score if content is easily recreated from Google or Wikipedia (-2-3 points)**

SCORING BONUSES:
- Contains API keys, passwords, or credentials: +2-3 points (important to keep secure info)
- Contains [[wiki-style links]] to other notes: +1-2 points (shows interconnectedness)
- Has many outgoing links (hub note): +2-3 points (central to knowledge network)
- Template files: +1-2 points (reusable structure)
- Personal/autobiographical content: +1-2 points (unique to the user)

SCORING PENALTIES:
- Easily recreated from Google/Wikipedia: -2-3 points (generic information)

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
            print("  [s] Skip for now")
            print("  [q] Quit the review process")
            
            choice = input("\nEnter your choice (k/d/s/q): ").lower().strip()
            
            if choice in ['k', 'keep']:
                return 'keep'
            elif choice in ['d', 'delete']:
                return 'delete'
            elif choice in ['s', 'skip']:
                return 'skip'
            elif choice in ['q', 'quit']:
                return 'quit'
            else:
                print("Invalid choice. Please enter k, d, s, or q.")
                
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
        
        # Find all markdown files
        md_files = self.find_markdown_files()
        
        if not md_files:
            print("No markdown files found in the vault.")
            return
            
        print(f"\nReady to review {len(md_files)} files")
        print("Tip: Consider backing up your vault before proceeding!")
        
        input("\nPress Enter to start the review process...")
        
        for i, file_path in enumerate(md_files, 1):
            print(f"\nProgress: {i}/{len(md_files)} files")
            
            # Read file content
            content = self.read_file_content(file_path)
            
            # Analyze with Gemini
            print(f"Analyzing: {file_path.name}...")
            analysis = self.analyze_note_relevance(file_path, content)
            
            # Display results
            self.display_analysis(file_path, analysis, content)
            
            # Get user decision
            decision = self.get_user_decision(analysis)
            
            if decision == 'quit':
                print("\nReview process stopped by user.")
                break
            elif decision == 'delete':
                if self.delete_file(file_path):
                    self.deleted_files.append(file_path)
            elif decision == 'keep':
                self.kept_files.append(file_path)
                print(f"Kept: {file_path}")
            elif decision == 'skip':
                print(f"Skipped: {file_path}")
                
            # Small delay to avoid API rate limits
            time.sleep(1)
            
        # Show summary
        self.show_summary()
        self.save_session_log()
        
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
    vault_path = input(f"Enter vault path (default: current directory): ").strip()
    if not vault_path:
        vault_path = os.getcwd()
        
    if not os.path.exists(vault_path):
        print(f"Vault path does not exist: {vault_path}")
        sys.exit(1)
        
    # Create reviewer and start
    reviewer = ObsidianVaultReviewer(api_key, vault_path)
    reviewer.review_vault()


if __name__ == "__main__":
    main() 