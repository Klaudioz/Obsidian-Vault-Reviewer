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
import random
from pathlib import Path
from typing import List, Dict, Optional
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable
from colorama import init, Fore, Style
from tqdm import tqdm
from count_tokens.count import count_tokens_in_string

# Cross-platform single character input
try:
    # Windows
    import msvcrt
    def getch():
        ch = msvcrt.getch().decode('utf-8')
        # Handle Ctrl-C (ASCII 3)
        if ord(ch) == 3:
            raise KeyboardInterrupt
        return ch.lower()
except ImportError:
    # Unix/Linux/macOS
    import tty
    import termios
    def getch():
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
            # Handle Ctrl-C (ASCII 3)
            if ord(ch) == 3:
                raise KeyboardInterrupt
            return ch.lower()
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
        self.enhanced_files = []
        self.atomic_notes_created = []  # Track atomic notes created during enhancement
        self.atomic_notes_reviewed = []  # Track atomic notes that were also reviewed in same session
        self.progress_file = self.vault_path / ".obsidian_review_progress.json"
        self.processed_files = set()  # Track which files have been processed
        self.original_session_start = time.strftime("%Y-%m-%d %H:%M:%S")  # Track session start time
        self.setup_signal_handlers()  # Handle Ctrl-C gracefully
        
        # Save this vault path as the most recent
        self.save_last_used_vault_path(vault_path)
        
        # Load or initialize configuration
        self.config_file = Path.home() / ".obsidian_vault_reviewer_settings.json"
        self.config = self.load_config()
        
        # Vault knowledge base cache
        self.vault_knowledge = {}  # Will store all note contents
        self.vault_knowledge_summary = ""  # Summary if full content is too large
        self.token_limit = 1000000  # Gemini 2.0 Flash has 1M token context window
        self.knowledge_loaded = False
        
        # Initialize count-tokens for accurate token counting
        try:
            # Test count-tokens functionality (no encoding parameter needed)
            test_count = count_tokens_in_string("test")
            print(f"✅ Initialized count-tokens successfully")
            self.token_counter_available = True
        except Exception as e:
            print(f"❌ Failed to initialize count-tokens: {e}")
            self.token_counter_available = False
        
    def setup_gemini(self):
        """Configure Gemini API."""
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
    def setup_signal_handlers(self):
        """Set up signal handlers to save progress on interruption."""
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
    def is_file_size_acceptable(self, file_path: Path) -> tuple[bool, int]:
        """
        Check if file size is within acceptable limits.
        Returns (is_acceptable, size_in_kb)
        """
        try:
            size_bytes = file_path.stat().st_size
            size_kb = size_bytes / 1024
            max_size_kb = self.config.get("max_file_size_kb", 30)
            return size_kb <= max_size_kb, int(size_kb)
        except Exception:
            return False, 0
        
    def handle_rate_limiting(self, func, *args, max_retries=5, base_delay=5, **kwargs):
        """
        Handle API rate limiting with exponential backoff.
        
        Args:
            func: The function to call
            *args: Arguments for the function
            max_retries: Maximum number of retry attempts (default: 5)
            base_delay: Base delay in seconds (default: 5)
            **kwargs: Keyword arguments for the function
            
        Returns:
            The result of the function call
            
        Raises:
            The last exception encountered if all retries fail
        """
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                return func(*args, **kwargs)
                
            except (ResourceExhausted, ServiceUnavailable) as e:
                last_exception = e
                
                if attempt == max_retries:
                    tqdm.write(f"❌ API rate limiting: All {max_retries} retries exhausted")
                    raise e
                
                # Calculate delay with exponential backoff + jitter
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                
                # Cap the delay at 60 seconds
                delay = min(delay, 60)
                
                tqdm.write(f"⏳ API rate limited. Waiting {delay:.1f}s before retry {attempt + 1}/{max_retries}...")
                time.sleep(delay)
                
            except Exception as e:
                # For non-rate-limiting errors, don't retry
                tqdm.write(f"❌ API error (not rate limiting): {e}")
                raise e
                
        # This should never be reached, but just in case
        if last_exception:
            raise last_exception
        
    def clear_screen(self):
        """Clear the terminal screen (cross-platform)."""
        os.system('cls' if os.name == 'nt' else 'clear')
        
    def soft_clear_for_tqdm(self, keep_lines=3):
        """Clear screen while preserving tqdm progress bar."""
        # Instead of clearing entire screen, just add some space
        for _ in range(keep_lines):
            tqdm.write("")
            
    def pause_progress_bar(self, progress_bar):
        """Temporarily pause the progress bar for clean user input."""
        progress_bar.clear()
        return progress_bar
        
    def resume_progress_bar(self, progress_bar):
        """Resume the progress bar after user input."""
        progress_bar.refresh()
        return progress_bar
        
    def write_with_spacing(self, text, spacing_before=1, spacing_after=0):
        """Write text with controlled spacing for better readability."""
        for _ in range(spacing_before):
            tqdm.write("")
        tqdm.write(text)
        for _ in range(spacing_after):
            tqdm.write("")
        
    def get_yes_no_input(self, prompt: str, default: Optional[str] = None) -> bool:
        """Get a yes/no decision using single-key input with optional default."""
        if default:
            default_display = f" (default: {default})"
            prompt_text = f"{prompt} (y/n{default_display}): "
        else:
            prompt_text = f"{prompt} (y/n): "
            
        while True:
            print(prompt_text, end="", flush=True)
            
            try:
                choice = getch()
                
                # Handle Enter key (newline)
                if choice in ['\r', '\n', ''] and default:
                    print(f"{default} (default)")
                    return default.lower() == 'y'
                elif choice == 'y':
                    print("y")
                    return True
                elif choice == 'n':
                    print("n")  
                    return False
                else:
                    if default:
                        print(f"{choice} - Invalid choice. Please press 'y' for yes, 'n' for no, or Enter for default ({default}).")
                    else:
                        print(f"{choice} - Invalid choice. Please press 'y' for yes or 'n' for no.")
            except (KeyboardInterrupt, EOFError):
                print("\nExiting...")
                sys.exit(0)
                
    def configure_auto_decisions(self):
        """Configure auto-decision settings."""
        print(f"\n{Fore.CYAN}⚙️  Auto-Decision Configuration{Style.RESET_ALL}")
        print("="*50)
        
        # Auto-keep configuration
        if self.get_yes_no_input(f"Enable auto-keep for high-scoring notes? (currently: {'YES' if self.config['auto_keep_enabled'] else 'NO'})"):
            self.config["auto_keep_enabled"] = True
            print(f"Current auto-keep threshold: {self.config['auto_keep_threshold']}")
            print("Enter new threshold (7-10) or press Enter to keep current: ", end="", flush=True)
            try:
                threshold_input = input().strip()
                if threshold_input:
                    threshold = int(threshold_input)
                    if 7 <= threshold <= 10:
                        self.config["auto_keep_threshold"] = threshold
                        print(f"Auto-keep threshold set to: {threshold}")
                    else:
                        print("Invalid threshold. Keeping current value.")
            except ValueError:
                print("Invalid input. Keeping current value.")
        else:
            self.config["auto_keep_enabled"] = False
            
        # Auto-delete configuration
        if self.get_yes_no_input(f"Enable auto-delete for low-scoring notes? (currently: {'YES' if self.config['auto_delete_enabled'] else 'NO'})"):
            self.config["auto_delete_enabled"] = True
            print(f"Current auto-delete threshold: {self.config['auto_delete_threshold']}")
            print("Enter new threshold (0-3) or press Enter to keep current: ", end="", flush=True)
            try:
                threshold_input = input().strip()
                if threshold_input:
                    threshold = int(threshold_input)
                    if 0 <= threshold <= 3:
                        self.config["auto_delete_threshold"] = threshold
                        print(f"Auto-delete threshold set to: {threshold}")
                    else:
                        print("Invalid threshold. Keeping current value.")
            except ValueError:
                print("Invalid input. Keeping current value.")
        else:
            self.config["auto_delete_enabled"] = False
            
        # Show auto-decisions
        show_auto = self.get_yes_no_input(f"Show auto-decision notifications? (currently: {'YES' if self.config['show_auto_decisions'] else 'NO'})")
        self.config["show_auto_decisions"] = show_auto
        
        # File size limit configuration
        if self.get_yes_no_input(f"Configure file size limit? (currently: {self.config['max_file_size_kb']}KB max)"):
            print(f"Current max file size: {self.config['max_file_size_kb']}KB")
            print("Enter new size limit in KB (10-100) or press Enter to keep current: ", end="", flush=True)
            try:
                size_input = input().strip()
                if size_input:
                    size_kb = int(size_input)
                    if 10 <= size_kb <= 100:
                        self.config["max_file_size_kb"] = size_kb
                        print(f"File size limit set to: {size_kb}KB")
                    else:
                        print("Invalid size. Keeping current value.")
            except ValueError:
                print("Invalid input. Keeping current value.")
        
        # Show skipped files option
        show_skipped = self.get_yes_no_input(f"Show skipped large files? (currently: {'YES' if self.config['show_skipped_files'] else 'NO'})")
        self.config["show_skipped_files"] = show_skipped
        
        # Subfolder inclusion option
        include_subfolders = self.get_yes_no_input(f"Include subfolders when scanning? (currently: {'YES' if self.config['include_subfolders'] else 'NO'})")
        self.config["include_subfolders"] = include_subfolders
        
        # Save configuration to file
        self.save_config()
        
        print(f"\n{Fore.GREEN}✅ Configuration saved!{Style.RESET_ALL}")
        if self.config["auto_keep_enabled"]:
            print(f"   Auto-keep: Notes scoring {self.config['auto_keep_threshold']}+ will be kept automatically")
        if self.config["auto_delete_enabled"]:
            print(f"   Auto-delete: Notes scoring {self.config['auto_delete_threshold']} or below will be deleted automatically")
        print(f"   Notifications: {'Enabled' if self.config['show_auto_decisions'] else 'Disabled'}")
        print(f"   File size limit: {self.config['max_file_size_kb']}KB maximum")
        print(f"   Show skipped files: {'Enabled' if self.config['show_skipped_files'] else 'Disabled'}")
        print(f"   Subfolders: {'Included' if self.config['include_subfolders'] else 'Root only'}")
        print(f"   Settings saved to: {self.config_file}")
        print("")
        
    def check_auto_decision(self, file_path: Path, analysis: Dict) -> Optional[str]:
        """Check if an auto-decision should be made based on score and configuration."""
        score = analysis['score']
        
        # Auto-keep check
        if (self.config["auto_keep_enabled"] and 
            score >= self.config["auto_keep_threshold"]):
            if self.config["show_auto_decisions"]:
                tqdm.write(f"\n🤖 AUTO-KEEP: Score {score}/{self.config['auto_keep_threshold']}+ → {Fore.GREEN}Automatically kept{Style.RESET_ALL}")
                tqdm.write(f"📄 {file_path.name}")
                tqdm.write(f"💡 {analysis['reasoning'][:100]}...")
            return "auto_keep"
            
        # Auto-delete check  
        if (self.config["auto_delete_enabled"] and 
            score <= self.config["auto_delete_threshold"]):
            if self.config["show_auto_decisions"]:
                tqdm.write(f"\n🤖 AUTO-DELETE: Score {score}/{self.config['auto_delete_threshold']}- → {Fore.RED}Automatically deleted{Style.RESET_ALL}")
                tqdm.write(f"📄 {file_path.name}")
                tqdm.write(f"💡 {analysis['reasoning'][:100]}...")
            return "auto_delete"
            
        return None
        
    def estimate_token_count(self, text: str) -> int:
        """
        Accurately estimate token count using count-tokens package.
        """
        try:
            if self.token_counter_available and text.strip():
                # Use count-tokens (uses cl100k_base encoding by default)
                return count_tokens_in_string(text)
            else:
                # Fallback to character-based estimation
                return len(text) // 4
        except Exception as e:
            # Fallback to character-based estimation
            return len(text) // 4
        
    def load_vault_knowledge(self):
        """
        Load all vault notes into memory for comparative analysis.
        If content exceeds token limit, create summaries instead.
        """
        if self.knowledge_loaded:
            return
            
        print("\n📚 Loading vault knowledge base for comparative analysis...")
        
        try:
            # Find all markdown files (.md extension only)
            # Respect subfolder configuration
            if self.config.get("include_subfolders", True):
                md_files = list(self.vault_path.rglob("*.md"))
                scan_type = "recursively (including subfolders)"
            else:
                md_files = list(self.vault_path.glob("*.md"))
                scan_type = "in root directory only"
                
            print(f"Found {len(md_files)} markdown files (.md) - scanning {scan_type}")
            
            # Filter out any non-markdown files that might have slipped through
            md_files = [f for f in md_files if f.suffix.lower() == '.md']
            
            # Filter by file size
            acceptable_files = []
            skipped_files = []
            max_size_kb = self.config.get("max_file_size_kb", 30)
            
            for file_path in md_files:
                is_acceptable, size_kb = self.is_file_size_acceptable(file_path)
                if is_acceptable:
                    acceptable_files.append(file_path)
                else:
                    skipped_files.append((file_path, size_kb))
            
            md_files = acceptable_files
            total_files = len(md_files)
            total_chars = 0
            loaded_count = 0
            
            # Report filtering results
            if skipped_files:
                print(f"📏 Filtered by size: {len(md_files)} files ≤{max_size_kb}KB, {len(skipped_files)} files skipped")
                if self.config.get("show_skipped_files", True) and len(skipped_files) <= 10:
                    print("   Skipped files:")
                    for file_path, size_kb in skipped_files[:10]:
                        print(f"     - {file_path.name} ({size_kb}KB)")
                    if len(skipped_files) > 10:
                        print(f"     ... and {len(skipped_files) - 10} more")
            else:
                print(f"📏 All {len(md_files)} files are ≤{max_size_kb}KB")
            
            # First pass: calculate total size and tokens
            print(f"Scanning {total_files} markdown files...")
            all_content = []
            for file_path in tqdm(md_files, desc="Calculating vault size"):
                try:
                    content = self.read_file_content(file_path)
                    if content.strip():  # Only count non-empty markdown files
                        total_chars += len(content)
                        all_content.append(content)
                except:
                    pass
                    
            # Test count-tokens with a small sample first
            test_text = "This is a test sentence to verify count-tokens is working correctly."
            test_tokens = self.estimate_token_count(test_text)
            expected_range = (10, 20)  # Should be around 15 tokens
            
            if test_tokens < expected_range[0] or test_tokens > expected_range[1]:
                print(f"⚠️ Token counting may be inaccurate. Test: '{test_text}' = {test_tokens} tokens")
                print(f"Expected range: {expected_range[0]}-{expected_range[1]} tokens")
            else:
                print(f"✅ Token counting verified: '{test_text}' = {test_tokens} tokens")
            
            # Calculate tokens for the entire vault content
            print("🔢 Calculating tokens for entire vault...")
            
            # For large vaults, estimate tokens by sampling instead of processing entire content
            if len(all_content) > 100:
                # Sample 100 random notes for estimation
                import random
                sample_content = random.sample(all_content, min(100, len(all_content)))
                sample_text = "\n\n".join(sample_content)
                sample_chars = len(sample_text)
                sample_tokens = self.estimate_token_count(sample_text)
                
                # Extrapolate to full vault
                if sample_chars > 0:
                    token_ratio = sample_tokens / sample_chars
                    estimated_tokens = int(total_chars * token_ratio)
                else:
                    estimated_tokens = total_chars // 4
                    
                print(f"📊 Sampled {len(sample_content)} notes for estimation")
                print(f"📊 Sample: {sample_chars:,} chars = {sample_tokens:,} tokens")
            else:
                # For small vaults, process all content
                vault_text = "\n\n".join(all_content)
                estimated_tokens = self.estimate_token_count(vault_text)
            
            # Show token density
            token_density = estimated_tokens / total_chars if total_chars > 0 else 0
            print(f"📊 Token density: {token_density:.3f} tokens per character")
            
            # Verify token calculation makes sense
            if token_density < 0.1 or token_density > 0.5:
                print(f"⚠️ Unusual token density detected!")
                print(f"   Expected range: 0.15-0.35 tokens per character")
                print(f"   Actual: {token_density:.3f}")
                if token_density < 0.1:
                    print(f"   This suggests tokens are being under-counted")
                else:
                    print(f"   This suggests tokens are being over-counted")
            print(f"\nVault statistics:")
            print(f"  Total files: {total_files}")
            print(f"  Total characters: {total_chars:,}")
            print(f"  Estimated tokens: {estimated_tokens:,}")
            print(f"  Token limit: {self.token_limit:,}")
            
            # Decide loading strategy
            if estimated_tokens < self.token_limit * 0.8:  # Use 80% of limit for safety
                # Load full content
                print("\n✅ Loading full vault content (within token limits)...")
                
                for file_path in tqdm(md_files, desc="Loading markdown notes"):
                    try:
                        content = self.read_file_content(file_path)
                        if content.strip():  # Only store non-empty markdown notes
                            note_title = file_path.stem
                            self.vault_knowledge[note_title] = {
                                'path': str(file_path.relative_to(self.vault_path)),
                                'content': content,
                                'length': len(content)
                            }
                            loaded_count += 1
                    except Exception as e:
                        pass
                        
                print(f"✅ Loaded {loaded_count} markdown notes into memory")
                self.knowledge_loaded = True
                
            else:
                # Create summaries for large vaults
                print(f"\n⚠️ Vault too large for full content ({estimated_tokens:,} tokens > {int(self.token_limit * 0.8):,} limit). Creating summaries...")
                
                # Load titles and brief excerpts from markdown files
                for file_path in tqdm(md_files, desc="Creating markdown summaries"):
                    try:
                        content = self.read_file_content(file_path)
                        if content.strip():
                            note_title = file_path.stem
                            # Store title, path, and first 500 chars
                            self.vault_knowledge[note_title] = {
                                'path': str(file_path.relative_to(self.vault_path)),
                                'excerpt': content[:500] + "..." if len(content) > 500 else content,
                                'length': len(content),
                                'full_content': False
                            }
                            loaded_count += 1
                    except:
                        pass
                        
                print(f"✅ Created summaries for {loaded_count} markdown notes")
                self.knowledge_loaded = True
                
                # Create a high-level vault summary
                self.create_vault_summary()
                
        except Exception as e:
            print(f"❌ Error loading vault knowledge: {e}")
            print("Continuing without full vault context...")
            
    def create_vault_summary(self):
        """Create a high-level summary of the vault for large vaults."""
        try:
            # Use the smart categorization system
            categories = self.categorize_vault_notes()
                
            # Build summary
            summary_parts = [f"Vault contains {len(self.vault_knowledge)} notes in categories:"]
            for cat, notes in sorted(categories.items(), key=lambda x: len(x[1]), reverse=True)[:20]:
                summary_parts.append(f"  - {cat}: {len(notes)} notes")
                
            self.vault_knowledge_summary = "\n".join(summary_parts)
            print(f"\n📊 Vault summary created with {len(categories)} categories")
            
        except Exception as e:
            print(f"Warning: Could not create vault summary: {e}")
            # Fallback to simple categorization
            categories = {}
            for title, info in self.vault_knowledge.items():
                category = title.split()[0] if ' ' in title else "Misc"
                if category not in categories:
                    categories[category] = []
                categories[category].append(title)
            print(f"📊 Fallback categorization created {len(categories)} categories")
            
    def get_comprehensive_vault_context(self) -> str:
        """
        Get comprehensive vault context for smart analysis.
        Returns structured information about the entire vault.
        """
        if not self.knowledge_loaded:
            return "No vault context available."
            
        context_parts = []
        
        # Vault overview
        context_parts.append(f"VAULT OVERVIEW:")
        context_parts.append(f"Total notes: {len(self.vault_knowledge)}")
        
        # If we have full content, provide comprehensive context
        if any(info.get('content') for info in self.vault_knowledge.values()):
            # Categorize notes by topic/type
            categories = self.categorize_vault_notes()
            context_parts.append(f"\nNOTE CATEGORIES:")
            for category, notes in sorted(categories.items(), key=lambda x: len(x[1]), reverse=True)[:15]:
                context_parts.append(f"  {category}: {len(notes)} notes")
                # Show a few example titles
                examples = ", ".join(notes[:3])
                if len(notes) > 3:
                    examples += f", ... (+{len(notes)-3} more)"
                context_parts.append(f"    Examples: {examples}")
            
            # Show all note titles for reference
            context_parts.append(f"\nALL NOTE TITLES:")
            all_titles = sorted(self.vault_knowledge.keys())
            context_parts.append(", ".join(all_titles))
            
        else:
            # Use summary for large vaults
            context_parts.append(f"\nVAULT SUMMARY:")
            context_parts.append(self.vault_knowledge_summary)
            
        return "\n".join(context_parts)
    
    def categorize_vault_notes(self) -> Dict[str, List[str]]:
        """Categorize vault notes by topic/type using smart pattern matching."""
        categories = {}
        
        # Define comprehensive categorization rules
        category_rules = {
            # Technology & Cloud
            "AWS/Cloud": ['aws', 'amazon', 'ec2', 's3', 'lambda', 'cloudfront', 'route', 'elb', 'rds', 'dynamodb', 'sqs', 'sns', 'cloudwatch', 'iam', 'vpc', 'cloudformation'],
            "Google Cloud": ['google', 'gcp', 'firebase', 'bigquery', 'kubernetes', 'gke'],
            "Microsoft/Azure": ['microsoft', 'azure', 'office', 'outlook', 'teams', 'sharepoint'],
            "Apple/iOS": ['apple', 'ios', 'swift', 'xcode', 'macos', 'iphone', 'ipad'],
            
            # Programming & Development
            "Python": ['python', 'django', 'flask', 'pandas', 'numpy', 'jupyter', 'pip'],
            "JavaScript/Web": ['javascript', 'js', 'react', 'vue', 'angular', 'node', 'npm', 'html', 'css'],
            "DevOps/Tools": ['docker', 'kubernetes', 'git', 'github', 'jenkins', 'terraform', 'ansible', 'linux', 'bash', 'shell'],
            "Databases": ['mysql', 'postgresql', 'mongodb', 'redis', 'database', 'sql'],
            
            # AI & Data
            "AI/Machine Learning": ['ai', 'machine', 'learning', 'neural', 'deep', 'tensorflow', 'pytorch', 'model', 'algorithm'],
            "Data Science": ['data', 'analytics', 'visualization', 'statistics', 'analysis'],
            
            # Business & Finance
            "Business/Finance": ['business', 'finance', 'money', 'investment', 'tax', 'accounting', 'revenue', 'profit', 'budget'],
            "Cryptocurrency": ['bitcoin', 'crypto', 'blockchain', 'ethereum', 'defi', 'nft'],
            
            # Personal & Life
            "Health/Fitness": ['health', 'fitness', 'exercise', 'diet', 'nutrition', 'medical', 'doctor'],
            "Travel": ['travel', 'trip', 'vacation', 'flight', 'hotel', 'country', 'city'],
            "Learning/Education": ['course', 'book', 'tutorial', 'learning', 'study', 'education', 'university'],
            
            # Project Management
            "Projects": ['project', 'task', 'todo', 'planning', 'milestone', 'deadline'],
            "Meetings/Events": ['meeting', 'conference', 'event', 'presentation', 'workshop'],
            
            # Personal Knowledge
            "Personal Notes": ['journal', 'diary', 'thoughts', 'ideas', 'reflection', 'personal'],
            "Reference": ['reference', 'cheat', 'sheet', 'guide', 'documentation', 'manual'],
        }
        
        for title, info in self.vault_knowledge.items():
            title_lower = title.lower()
            category = "Uncategorized"
            
            # Check against category rules
            for cat_name, keywords in category_rules.items():
                if any(keyword in title_lower for keyword in keywords):
                    category = cat_name
                    break
            
            # Special handling for single-word technical terms
            if category == "Uncategorized" and ' ' not in title:
                if title_lower in ['git', 'docker', 'kubernetes', 'linux', 'bash', 'vim', 'ssh']:
                    category = "DevOps/Tools"
                elif title_lower in ['python', 'javascript', 'java', 'css', 'html', 'sql']:
                    category = "Programming Languages"
                elif title_lower in ['aws', 'gcp', 'azure']:
                    category = "Cloud Platforms"
                elif len(title) <= 4 and title.isupper():  # Acronyms like API, REST, HTTP
                    category = "Technical Acronyms"
                else:
                    category = "Single Concepts"
            
            # If still uncategorized, use first word as category (but clean it up)
            if category == "Uncategorized" and ' ' in title:
                first_word = title.split()[0]
                if len(first_word) > 2:  # Avoid very short categories
                    category = first_word.capitalize()
                else:
                    category = "Misc"
            
            if category not in categories:
                categories[category] = []
            categories[category].append(title)
        
        # Merge small categories into "Misc"
        final_categories = {}
        misc_notes = []
        
        for cat_name, notes in categories.items():
            if len(notes) >= 3:  # Keep categories with 3+ notes
                final_categories[cat_name] = notes
            else:
                misc_notes.extend(notes)
        
        if misc_notes:
            final_categories["Misc"] = misc_notes
            
        return final_categories

    def get_vault_context_for_analysis(self, current_file: Path) -> str:
        """
        Get relevant vault context for analyzing a specific note.
        Returns a context string optimized for the current analysis.
        """
        if not self.knowledge_loaded:
            return ""
            
        context_parts = []
        
        # If we have full content loaded
        if any(info.get('content') for info in self.vault_knowledge.values()):
            # Find related notes (simple keyword matching)
            current_title = current_file.stem
            current_words = set(current_title.lower().split())
            
            related_notes = []
            for title, info in self.vault_knowledge.items():
                if title == current_title:
                    continue
                    
                title_words = set(title.lower().split())
                if current_words & title_words:  # Common words
                    related_notes.append((title, info))
                    
            # Add up to 10 most relevant notes
            if related_notes:
                context_parts.append("RELATED NOTES IN VAULT:")
                for title, info in related_notes[:10]:
                    if 'content' in info:
                        preview = info['content'][:200] + "..." if len(info['content']) > 200 else info['content']
                    else:
                        preview = info.get('excerpt', '')
                    context_parts.append(f"\n[{title}]:\n{preview}")
            
            # Also add vault overview for context
            context_parts.append(f"\nVAULT OVERVIEW: {len(self.vault_knowledge)} total notes")
                
        else:
            # Use summary for large vaults
            context_parts.append("VAULT OVERVIEW:")
            context_parts.append(self.vault_knowledge_summary)
            
        return "\n".join(context_parts)

    def scan_vault_for_existing_notes(self) -> Dict[str, str]:
        """
        Scan the entire vault to build a map of existing note titles to their file paths.
        This enables the AI to reference existing notes with proper [[WikiLinks]].
        """
        existing_notes = {}
        
        try:
            # If vault knowledge is already loaded, use it
            if self.knowledge_loaded:
                for note_title, info in self.vault_knowledge.items():
                    existing_notes[note_title] = info['path']
                return existing_notes
                
            # Otherwise, do a quick scan
            # Find all markdown files in the vault (.md extension only)
            md_files = list(self.vault_path.rglob("*.md"))
            md_files = [f for f in md_files if f.suffix.lower() == '.md']  # Ensure only .md files
            
            # Filter by file size
            md_files = [f for f in md_files if self.is_file_size_acceptable(f)[0]]
            
            for file_path in md_files:
                # Use the filename without extension as the note title
                note_title = file_path.stem
                # Store the relative path from vault root
                relative_path = file_path.relative_to(self.vault_path)
                existing_notes[note_title] = str(relative_path)
                
                # Also read the first line to check for alternate titles (like # Header)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        first_line = f.readline().strip()
                        if first_line.startswith('#'):
                            # Extract header text as alternate title
                            header_title = first_line.lstrip('#').strip()
                            if header_title and header_title != note_title:
                                existing_notes[header_title] = str(relative_path)
                except Exception:
                    # If we can't read the file, skip alternate title
                    pass
                    
        except Exception as e:
            tqdm.write(f"Warning: Failed to scan vault for existing notes: {e}")
            
        return existing_notes
        
    def identify_atomic_concepts(self, content: str, file_path: Path) -> List[str]:
        """
        Use AI to identify concepts in the content that should be atomic notes.
        Now uses full vault context for smarter concept identification.
        """
        if not self.knowledge_loaded:
            return []
            
        # Get comprehensive vault context
        vault_context = self.get_comprehensive_vault_context()
        
        prompt = f"""
Analyze this note content and identify concepts that should be atomic notes in a second brain/Zettelkasten system.

CURRENT NOTE: {file_path.name}
CONTENT TO ANALYZE:
{content}

FULL VAULT KNOWLEDGE CONTEXT:
{vault_context}

SMART ATOMIC NOTE IDENTIFICATION:
Using the full vault context above, identify concepts that:
1. Are mentioned in this note but don't have dedicated notes yet
2. Would benefit multiple notes if extracted as atomic concepts  
3. Represent foundational knowledge that appears across the vault
4. Fill gaps in the existing knowledge network
5. Would create valuable connections between existing notes

ATOMIC NOTE PRINCIPLES:
- Each note should contain ONE concept or idea
- Notes should be understandable on their own
- Notes should be linkable and reusable
- Focus on concepts that appear multiple times or are foundational
- Avoid duplicating existing notes (check vault context carefully)

IDENTIFY MISSING ATOMIC CONCEPTS:
1. Scan the vault context to see what concepts already exist
2. Look for concepts in this note that would benefit the entire vault
3. Consider concepts that would bridge knowledge gaps
4. Think about foundational concepts that support multiple areas

Return a JSON list of atomic concept titles that should exist as separate notes:
{{
    "atomic_concepts": [
        "Concept Name 1",
        "Concept Name 2", 
        "Concept Name 3"
    ]
}}

IMPORTANT:
- Focus on 2-4 key concepts maximum (quality over quantity)
- Use clear, descriptive titles (2-4 words)
- DON'T suggest concepts that already exist in the vault (check the context above)
- Prioritize concepts that would be useful across multiple existing notes
- Consider how these concepts would connect to existing notes via [[WikiLinks]]
"""

        try:
            response = self.handle_rate_limiting(self.model.generate_content, prompt)
            response_text = response.text.strip()
            
            # Clean up JSON response
            if response_text.startswith('```json'):
                response_text = response_text.split('```json')[1].split('```')[0]
            elif response_text.startswith('```'):
                response_text = response_text.split('```')[1].split('```')[0]
            
            response_text = response_text.strip()
            
            # Parse JSON
            result = json.loads(response_text)
            return result.get('atomic_concepts', [])
            
        except Exception as e:
            tqdm.write(f"Warning: Failed to identify atomic concepts: {e}")
            return []
            
    def create_atomic_note(self, concept_title: str, original_content: str, file_context: str) -> str:
        """
        Create content for a new atomic note based on a concept.
        Now uses full vault context for smarter note creation.
        """
        # Get comprehensive vault context
        vault_context = self.get_comprehensive_vault_context()
        
        prompt = f"""
Create content for a new atomic note in a second brain/Zettelkasten system.

ATOMIC NOTE TITLE: {concept_title}

CONTEXT (from original note):
{original_content}

ORIGINAL NOTE CONTEXT: {file_context}

FULL VAULT KNOWLEDGE CONTEXT:
{vault_context}

SMART ATOMIC NOTE CREATION:
Using the full vault context above, create an atomic note that:
1. Focuses solely on the concept: {concept_title}
2. Connects to existing notes in the vault via [[WikiLinks]]
3. Fills knowledge gaps identified in the vault
4. Uses terminology consistent with existing notes
5. References related concepts that already exist
6. Provides unique value not covered elsewhere

WRITING GUIDELINES:
- Use conversational but professional tone
- Use inclusive language with "we," "let's," and "us"
- Write clearly and concisely without Latin abbreviations
- Use active voice over passive voice
- Use globally accessible language, avoid idioms and colloquialisms
- Do not reference timeframes or external content
- Do not assume prior knowledge
- Use precise, consistent terminology
- Create stand-alone content that does not rely on external materials
- Write content that is both technically accurate and engaging
- Use generic references to AI assistants unless specifically needed
- Use Oxford commas and proper formatting
- Provide educational and thorough explanations with clear examples
- Build understanding progressively
- Use human and concise format
- Avoid emojis and double dashes

AVOID these complex or abstract terms: 'delve', 'meticulous,' 'navigating,' 'complexities,' 'realm,' 'bespoke,' 'tailored,' 'towards,' 'underpins,' 'ever-changing,' 'ever-evolving,' 'the world of,' 'not only,' 'seeking more than just,' 'designed to enhance,' 'it's not merely,' 'our suite,' 'it is advisable,' 'daunting,' 'in the heart of,' 'when it comes to,' 'in the realm of,' 'amongst,' 'unlock the secrets,' 'unveil the secrets,' 'transforms' and 'robust.'

CREATE ATOMIC NOTE CONTENT:
- Focus on ONE concept: {concept_title}
- Make it understandable on its own
- Include practical information, examples, or definitions
- Add relevant context for personal knowledge management
- Use clear structure with headers
- Aim for 150-400 words (atomic but comprehensive)
- Include related concepts using [[WikiLinks]] where appropriate

ATOMIC NOTE PRINCIPLES:
- Autonomy: Should be understandable without other notes
- Atomicity: Contains only one main idea or concept
- Linkability: Can be connected to other notes
- Usefulness: Valuable for future reference

Return ONLY the note content (no JSON, no explanations):
"""

        try:
            response = self.handle_rate_limiting(self.model.generate_content, prompt)
            content = response.text.strip()
            
            # Remove markdown code blocks if present
            if content.startswith('```markdown'):
                content = content.split('```markdown')[1].split('```')[0].strip()
            elif content.startswith('```'):
                content = content.split('```')[1].split('```')[0].strip()
                
            return content
            
        except Exception as e:
            tqdm.write(f"Warning: Failed to create atomic note for {concept_title}: {e}")
            return f"# {concept_title}\n\n*Concept extracted from {file_context}*"
            
    def save_atomic_note(self, concept_title: str, content: str) -> bool:
        """
        Save a new atomic note to the vault.
        """
        try:
            # Clean the title to make it filename-safe
            import re
            safe_title = re.sub(r'[<>:"/\\|?*]', '', concept_title)
            safe_title = safe_title.strip()
            
            # Create the file path
            file_path = self.vault_path / f"{safe_title}.md"
            
            # Check if file already exists
            if file_path.exists():
                tqdm.write(f"Note already exists: {safe_title}")
                return False
                
            # Save the file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            # Add to newly created atomic notes queue for review
            if hasattr(self, 'new_atomic_notes_queue'):
                self.new_atomic_notes_queue.append(file_path)
                tqdm.write(f"✅ Created atomic note: {safe_title}.md (added to review queue)")
            else:
                tqdm.write(f"✅ Created atomic note: {safe_title}.md")
            return True
            
        except Exception as e:
            tqdm.write(f"❌ Failed to save atomic note {concept_title}: {e}")
            return False

    def enhance_note(self, file_path: Path, content: str) -> str:
        """
        Use Gemini to enhance a sparse note using atomic note principles and existing vault notes.
        
        SAFETY GUARANTEE: This method will NEVER delete or modify existing content.
        It only adds new content and creates atomic notes. If the AI accidentally removes any 
        original content, the safety validation will catch it and return the original content unchanged.
        
        Returns:
            Enhanced content with original content preserved + new additions + atomic note links,
            or original content unchanged if enhancement fails or safety check fails.
        """
        
        # Step 1: Use loaded vault knowledge (no need to scan again)
        if self.knowledge_loaded:
            existing_notes = {title: info['path'] for title, info in self.vault_knowledge.items()}
            tqdm.write(f"📚 Using loaded vault knowledge: {len(existing_notes)} notes")
        else:
            tqdm.write("🔍 Scanning vault for existing notes...")
            existing_notes = self.scan_vault_for_existing_notes()
            tqdm.write(f"Found {len(existing_notes)} existing notes")
        
        # Step 2: Identify atomic concepts that should be extracted
        tqdm.write("🧠 Identifying atomic concepts...")
        atomic_concepts = self.identify_atomic_concepts(content, file_path)
        
        if atomic_concepts:
            tqdm.write(f"📝 Identified {len(atomic_concepts)} atomic concepts: {', '.join(atomic_concepts)}")
            
            # Step 3: Create atomic notes for new concepts
            created_notes = []
            for concept in atomic_concepts:
                if concept not in existing_notes:
                    tqdm.write(f"Creating atomic note: {concept}")
                    atomic_content = self.create_atomic_note(concept, content, file_path.name)
                    if self.save_atomic_note(concept, atomic_content):
                        created_notes.append(concept)
                        # Track atomic notes created for progress reporting
                        self.atomic_notes_created.append(concept)
                        # Add to existing_notes for subsequent linking
                        existing_notes[concept] = f"{concept}.md"
                else:
                    tqdm.write(f"Atomic note already exists: {concept}")
        
        # Step 4: Get comprehensive vault context for smart enhancement
        vault_context = self.get_comprehensive_vault_context()
        
        # Step 5: Enhance the original note with full vault knowledge
        prompt = f"""
You are enhancing a note in a personal knowledge management system using atomic note principles.

CURRENT NOTE TO ENHANCE:
File: {file_path.name}
===BEGIN ORIGINAL CONTENT===
{content}
===END ORIGINAL CONTENT===

FULL VAULT KNOWLEDGE CONTEXT:
{vault_context}

NEWLY CREATED ATOMIC NOTES (link to these):
{', '.join([f"[[{note}]]" for note in created_notes]) if created_notes else "None"}

SMART NOTE ENHANCEMENT:
Using the full vault context above, enhance this note by:
1. Adding [[WikiLinks]] to existing notes throughout the content
2. Connecting this note to the broader knowledge network
3. Referencing newly created atomic notes where relevant
4. Identifying knowledge gaps this note fills
5. Using consistent terminology with existing notes
6. Creating meaningful connections between concepts

WRITING GUIDELINES:
- Use conversational but professional tone
- Use inclusive language with "we," "let's," and "us"
- Write clearly and concisely without Latin abbreviations
- Use active voice over passive voice
- Use globally accessible language, avoid idioms and colloquialisms
- Do not reference timeframes or external content
- Do not assume prior knowledge
- Use precise, consistent terminology
- Create stand-alone content that does not rely on external materials
- Write content that is both technically accurate and engaging
- Use generic references to AI assistants unless specifically needed
- Use Oxford commas and proper formatting
- Provide educational and thorough explanations with clear examples
- Build understanding progressively
- Use human and concise format
- Avoid emojis and double dashes

AVOID these complex or abstract terms: 'delve', 'meticulous,' 'navigating,' 'complexities,' 'realm,' 'bespoke,' 'tailored,' 'towards,' 'underpins,' 'ever-changing,' 'ever-evolving,' 'the world of,' 'not only,' 'seeking more than just,' 'designed to enhance,' 'it's not merely,' 'our suite,' 'it is advisable,' 'daunting,' 'in the heart of,' 'when it comes to,' 'in the realm of,' 'amongst,' 'unlock the secrets,' 'unveil the secrets,' 'transforms' and 'robust.'

YOUR TASK:
Return the enhanced note content with ALL original content preserved exactly as written, plus your enhancements following atomic note principles.

STRICT RULES FOR ENHANCEMENT:
1. PRESERVE ALL ORIGINAL CONTENT: Keep every character, word, line, and formatting exactly as written above
2. ONLY ADD NEW CONTENT: You may append or insert additional content, but never modify existing text
3. NO CORRECTIONS: Do not fix typos, grammar, or formatting in the original content
4. FOCUSED ENHANCEMENT: Add 1-3 meaningful sections only, avoid repetition
5. NO DUPLICATE HEADERS: Never repeat the same header or content multiple times

ATOMIC NOTE ENHANCEMENT FOCUS:
- Link to relevant existing notes using [[WikiLinks]] - this is CRITICAL
- Reference the newly created atomic notes where relevant
- Add 1-2 sections maximum that provide value
- Connect this note to the broader knowledge network
- Include practical applications or personal insights
- Use tags (#tag) for categorization
- Aim for 2-4x the original length (not 10x+)
- Keep sections focused and non-repetitive

SMART LINKING STRATEGY:
- Scan the vault context to identify ALL relevant existing notes
- Use [[Note Name]] for existing notes whenever concepts are mentioned
- Create natural connections throughout the content, not just at the end
- Reference newly created atomic notes when discussing their concepts
- Connect to 5-15 relevant existing notes (be comprehensive)
- Use the exact note titles from the vault context
- Create a rich knowledge network with meaningful connections
- Add a "Related Notes" section if it adds value beyond inline links

CRITICAL OUTPUT REQUIREMENTS:
- Return ONLY the enhanced note content
- Include ALL original content exactly as written
- Do NOT repeat headers or create duplicate sections
- Do NOT include any instructions, explanations, or commentary
- Do NOT include any safety requirement text in the output
- Do NOT include any metadata about the enhancement process
- MUST include WikiLinks to existing notes - this is essential for knowledge management
- Keep enhancement focused and concise (2-4x original length maximum)

Begin your response with the enhanced note content now:
"""

        try:
            # Use rate limiting handler for the API call
            response = self.handle_rate_limiting(self.model.generate_content, prompt)
            enhanced_content = response.text.strip()
            
            # Remove any markdown code blocks if present
            if enhanced_content.startswith('```markdown'):
                enhanced_content = enhanced_content.split('```markdown')[1].split('```')[0].strip()
            elif enhanced_content.startswith('```'):
                enhanced_content = enhanced_content.split('```')[1].split('```')[0].strip()
            
            # ADDITIONAL SAFETY CHECK: Remove any leaked prompt instructions
            enhanced_content = self.clean_leaked_instructions(enhanced_content)
            
            # SAFETY CHECK: Verify that all original content is preserved
            if not self.validate_content_preservation(content, enhanced_content):
                tqdm.write(f"⚠️ Safety check failed: Original content not fully preserved in enhanced note")
                tqdm.write(f"Returning original content unchanged for safety")
                return content
                
            # Report on what was created
            if created_notes:
                tqdm.write(f"🎉 Enhanced note with {len(created_notes)} new atomic notes and knowledge links")
            else:
                tqdm.write(f"🎉 Enhanced note with existing knowledge links")
                
            return enhanced_content
            
        except Exception as e:
            tqdm.write(f"Error enhancing note: {e}")
            return content  # Return original content if enhancement fails
            
    def clean_leaked_instructions(self, enhanced_content: str) -> str:
        """
        Remove any leaked prompt instructions from the enhanced content.
        This is a safety net to catch when the AI accidentally includes instruction text.
        """
        # List of instruction phrases that should never appear in the actual note content
        instruction_indicators = [
            "🚨 CRITICAL SAFETY REQUIREMENTS",
            "CRITICAL SAFETY REQUIREMENTS", 
            "SAFETY REQUIREMENTS",
            "NEVER DELETE OR MODIFY ANY EXISTING CONTENT",
            "ONLY ADD NEW CONTENT",
            "PRESERVE ALL FORMATTING",
            "NO CORRECTIONS",
            "MUST BE FOLLOWED:",
            "Enhancement Goals:",
            "REPEATED FOR EMPHASIS",
            "===BEGIN ORIGINAL CONTENT===",
            "===END ORIGINAL CONTENT===",
            "BEGIN ORIGINAL CONTENT",
            "END ORIGINAL CONTENT",
            "===BEGIN ENHANCEMENT===",
            "===END ENHANCEMENT===", 
            "===TEXT ENHANCEMENT===",
            "===ENHANCEMENT===",
            "BEGIN ENHANCEMENT",
            "END ENHANCEMENT",
            "File:",
            "CURRENT NOTE TO ENHANCE:",
            "YOUR TASK:",
            "STRICT RULES FOR ENHANCEMENT:",
            "ATOMIC NOTE ENHANCEMENT FOCUS:",
            "LINKING STRATEGY:",
            "CRITICAL OUTPUT REQUIREMENTS:"
        ]
        
        # First, remove the content markers specifically
        enhanced_content = enhanced_content.replace("===BEGIN ORIGINAL CONTENT===", "")
        enhanced_content = enhanced_content.replace("===END ORIGINAL CONTENT===", "")
        enhanced_content = enhanced_content.replace("BEGIN ORIGINAL CONTENT", "")
        enhanced_content = enhanced_content.replace("END ORIGINAL CONTENT", "")
        enhanced_content = enhanced_content.replace("===BEGIN ENHANCEMENT===", "")
        enhanced_content = enhanced_content.replace("===END ENHANCEMENT===", "")
        enhanced_content = enhanced_content.replace("===TEXT ENHANCEMENT===", "")
        enhanced_content = enhanced_content.replace("===ENHANCEMENT===", "")
        enhanced_content = enhanced_content.replace("BEGIN ENHANCEMENT", "")
        enhanced_content = enhanced_content.replace("END ENHANCEMENT", "")
        
        # Use regex to remove any pattern like ===ANYTHING=== that looks like a marker
        import re
        enhanced_content = re.sub(r'={3,}[A-Z\s]+={3,}', '', enhanced_content)
        # Also remove lines that are just === or similar
        enhanced_content = re.sub(r'^={3,}$', '', enhanced_content, flags=re.MULTILINE)
        
        lines = enhanced_content.split('\n')
        clean_lines = []
        skip_mode = False
        
        for line in lines:
            line_upper = line.upper()
            
            # Check if this line contains instruction text
            contains_instruction = any(indicator.upper() in line_upper for indicator in instruction_indicators)
            
            # Skip lines that start with "File:" (from prompt)
            if line.strip().startswith("File:") and len(line.strip()) < 50:
                continue
                
            # If we hit a safety requirements section, start skipping
            if "SAFETY REQUIREMENT" in line_upper or "CRITICAL" in line_upper and "REQUIREMENT" in line_upper:
                skip_mode = True
                continue
                
            # If we're in skip mode and hit a line that looks like content, stop skipping
            if skip_mode:
                # Check if this looks like actual note content (starts with #, -, *, or regular text)
                if (line.strip() and 
                    not line.strip().startswith(('1.', '2.', '3.', '4.', '5.', '-', '✅', '❌')) and
                    not any(indicator.upper() in line_upper for indicator in instruction_indicators)):
                    skip_mode = False
                else:
                    continue  # Still in instruction mode, skip this line
            
            # If not skipping and doesn't contain instructions, keep the line
            if not skip_mode and not contains_instruction:
                clean_lines.append(line)
        
        # Clean up any remaining empty lines at the beginning
        while clean_lines and not clean_lines[0].strip():
            clean_lines.pop(0)
                
        return '\n'.join(clean_lines)
    

            
    def validate_content_preservation(self, original: str, enhanced: str) -> bool:
        """
        Validate that the enhanced content contains all original content.
        This is a safety check to ensure no content is deleted during enhancement.
        """
        # Basic check: enhanced content should be longer than original
        if len(enhanced) < len(original):
            return False
        
        # Normalize both strings for comparison - remove extra whitespace but preserve structure
        def normalize_text(text):
            # Split into lines, strip each line, and remove empty lines for comparison
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            return '\n'.join(lines)
        
        original_normalized = normalize_text(original)
        enhanced_normalized = normalize_text(enhanced)
        
        # Primary check: original content should be contained in enhanced content
        if original_normalized in enhanced_normalized:
            return True
        
        # Secondary check: line-by-line matching with more flexibility
        original_lines = [line.strip() for line in original.split('\n') if line.strip()]
        enhanced_lines = [line.strip() for line in enhanced.split('\n') if line.strip()]
        
        # Check that most original lines appear in the enhanced version
        # Allow for minor formatting differences
        matched_lines = 0
        
        for orig_line in original_lines:
            for enh_line in enhanced_lines:
                # Exact match
                if orig_line == enh_line:
                    matched_lines += 1
                    break
                # Fuzzy match - check if the core content is preserved
                elif len(orig_line) > 10 and orig_line in enh_line:
                    matched_lines += 1
                    break
                # Handle cases where formatting might change slightly
                elif len(orig_line) > 5:
                    # Remove special characters for comparison
                    import re
                    orig_clean = re.sub(r'[^\w\s]', '', orig_line.lower())
                    enh_clean = re.sub(r'[^\w\s]', '', enh_line.lower())
                    if orig_clean and orig_clean in enh_clean:
                        matched_lines += 1
                        break
        
        # Require at least 80% of original lines to be preserved
        preservation_ratio = matched_lines / len(original_lines) if original_lines else 1
        
        # Additional safety: check for key content preservation
        # Look for important patterns like [[links]], #tags, images, etc.
        import re
        
        # Extract important elements from original
        orig_links = re.findall(r'\[\[([^\]]+)\]\]', original)
        orig_tags = re.findall(r'#(\w+)', original)
        orig_images = re.findall(r'!\[[^\]]*\]\([^)]+\)', original)
        
        # Check these are preserved in enhanced version
        enh_links = re.findall(r'\[\[([^\]]+)\]\]', enhanced)
        enh_tags = re.findall(r'#(\w+)', enhanced)
        enh_images = re.findall(r'!\[[^\]]*\]\([^)]+\)', enhanced)
        
        # All original links, tags, and images should be preserved
        links_preserved = all(link in enh_links for link in orig_links)
        tags_preserved = all(tag in enh_tags for tag in orig_tags) 
        images_preserved = all(img in enhanced for img in orig_images)
        
        # Final validation: good line preservation AND important elements preserved
        return (preservation_ratio >= 0.8 and links_preserved and tags_preserved and images_preserved)
            
    def save_enhanced_note(self, file_path: Path, enhanced_content: str) -> bool:
        """Save the enhanced note content to file."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(enhanced_content)
            return True
        except Exception as e:
            tqdm.write(f"Error saving enhanced note: {e}")
            return False
        
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
            "enhanced_files": [str(f) for f in self.enhanced_files],
            "atomic_notes_created": self.atomic_notes_created,
            "atomic_notes_reviewed": getattr(self, 'atomic_notes_reviewed', []),
            "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
            "config": self.config
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
            self.enhanced_files = [Path(f) for f in progress_data.get("enhanced_files", [])]
            self.atomic_notes_created = progress_data.get("atomic_notes_created", [])
            self.atomic_notes_reviewed = progress_data.get("atomic_notes_reviewed", [])
            self.original_session_start = progress_data.get("session_start", time.strftime("%Y-%m-%d %H:%M:%S"))
            
            # Load configuration (merge with defaults for new settings)
            saved_config = progress_data.get("config", {})
            self.config.update(saved_config)
            
            print(f"Found previous review session from: {progress_data.get('session_start', 'Unknown')}")
            print(f"Files already processed: {len(self.processed_files)}")
            print(f"Files deleted: {len(self.deleted_files)}")
            print(f"Files kept: {len(self.kept_files)}")
            print(f"Files enhanced: {len(self.enhanced_files)}")
            print(f"Atomic notes created: {len(self.atomic_notes_created)}")
            
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
            
    def save_last_used_vault_path(self, vault_path: str):
        """Save the most recently used vault path."""
        config_file = Path.home() / ".obsidian_vault_reviewer_config.json"
        try:
            config_data = {"last_vault_path": str(vault_path)}
            with open(config_file, 'w') as f:
                json.dump(config_data, f)
        except Exception as e:
            # Silently fail - this is just a convenience feature
            pass
            
    def load_config(self) -> Dict:
        """Load configuration from file or return defaults."""
        default_config = {
            "auto_keep_enabled": True,
            "auto_keep_threshold": 7,
            "auto_delete_enabled": False,
            "auto_delete_threshold": 2,
            "show_auto_decisions": True,
            "max_file_size_kb": 20,  # Ignore files larger than 20 KB
            "show_skipped_files": True,  # Show which files are skipped due to size
            "include_subfolders": True  # Include subfolders when scanning for files
        }
        
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    saved_config = json.load(f)
                # Merge with defaults to handle new settings
                default_config.update(saved_config)
                subfolder_status = "including" if default_config['include_subfolders'] else "excluding"
                print(f"📁 Loaded settings: max file size {default_config['max_file_size_kb']}KB, {subfolder_status} subfolders")
        except Exception as e:
            print(f"Warning: Could not load settings file: {e}")
            
        return default_config
        
    def save_config(self):
        """Save current configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save settings file: {e}")

    @staticmethod
    def get_last_used_vault_path() -> Optional[str]:
        """Get the most recently used vault path."""
        config_file = Path.home() / ".obsidian_vault_reviewer_config.json"
        try:
            if config_file.exists():
                with open(config_file, 'r') as f:
                    config_data = json.load(f)
                return config_data.get("last_vault_path")
        except Exception as e:
            # Silently fail - this is just a convenience feature
            pass
        return None
        
    def find_markdown_files(self) -> List[Path]:
        """Recursively find all markdown files in the vault."""
        print(f"Scanning vault: {self.vault_path}")
        
        # Respect subfolder configuration
        if self.config.get("include_subfolders", True):
            md_files = list(self.vault_path.rglob("*.md"))
            scan_type = "recursively (including subfolders)"
        else:
            md_files = list(self.vault_path.glob("*.md"))
            scan_type = "in root directory only"
            
        print(f"Scanning {scan_type}")
        
        # Ensure only .md files (filter out any edge cases)
        md_files = [f for f in md_files if f.suffix.lower() == '.md']
        
        # Filter by file size
        acceptable_files = []
        skipped_files = []
        max_size_kb = self.config.get("max_file_size_kb", 30)
        
        for file_path in md_files:
            is_acceptable, size_kb = self.is_file_size_acceptable(file_path)
            if is_acceptable:
                acceptable_files.append(file_path)
            else:
                skipped_files.append((file_path, size_kb))
        
        md_files = acceptable_files
        md_files.sort()  # Sort files alphabetically
        
        print(f"Found {len(md_files)} markdown files (.md only, ≤{max_size_kb}KB)")
        if skipped_files:
            print(f"Skipped {len(skipped_files)} large files (>{max_size_kb}KB)")
        
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
            tqdm.write(f"Error reading {file_path}: {e}")
            return ""
            
    def parse_ai_response_fallback(self, response_text: str) -> Dict:
        """Fallback parser using regex when JSON parsing fails completely."""
        import re
        
        # Try to extract score using various patterns
        score = 5  # default
        score_patterns = [
            r'"score":\s*(\d+)',
            r'"score":\s*"(\d+)"',
            r'score:\s*(\d+)',
            r'Score:\s*(\d+)',
            r'relevance score.*?(\d+)',
            r'(\d+)/10',
            r'score.*?(\d+)'
        ]
        
        for pattern in score_patterns:
            match = re.search(pattern, response_text, re.IGNORECASE)
            if match:
                try:
                    score = int(match.group(1))
                    if 0 <= score <= 10:
                        break
                except ValueError:
                    continue
        
        # Try to extract reasoning
        reasoning = "AI analysis completed but response format was unclear."
        reasoning_patterns = [
            r'"reasoning":\s*"([^"]+)"',
            r'"reasoning":\s*([^,}]+)',
            r'reasoning:\s*([^,}]+)',
            r'Reasoning:\s*([^,}]+)',
            r'because\s+([^.]+)',
            r'This\s+([^.]+\.)' 
        ]
        
        for pattern in reasoning_patterns:
            match = re.search(pattern, response_text, re.IGNORECASE | re.DOTALL)
            if match:
                extracted = match.group(1).strip().strip('"').strip("'")
                if len(extracted) > 10:  # Make sure we got something meaningful
                    reasoning = extracted[:200] + "..." if len(extracted) > 200 else extracted
                    break
        
        # Determine recommendation based on score
        if score <= 4:
            recommendation = "remove"
        elif score <= 7:
            recommendation = "enhance"
        else:
            recommendation = "keep"
            
        return {
            "score": score,
            "reasoning": reasoning,
            "recommendation": recommendation
        }
    
    def clean_json_response(self, json_text: str) -> str:
        """Clean up common JSON formatting issues from AI responses."""
        import re
        
        # Remove any leading/trailing whitespace
        json_text = json_text.strip()
        
        # Remove any text before the first {
        if '{' in json_text:
            json_text = json_text[json_text.find('{'):]
        
        # Remove any text after the last }
        if '}' in json_text:
            json_text = json_text[:json_text.rfind('}') + 1]
        
        # Fix unquoted property names (common issue)
        json_text = re.sub(r'(\w+):', r'"\1":', json_text)
        
        # Fix single quotes to double quotes
        json_text = re.sub(r"'([^']*)'", r'"\1"', json_text)
        
        # Remove trailing commas before closing braces/brackets
        json_text = re.sub(r',\s*}', '}', json_text)
        json_text = re.sub(r',\s*]', ']', json_text)
        
        # Fix common number/string formatting issues
        lines = json_text.split('\n')
        fixed_lines = []
        
        for line in lines:
            if ':' in line:
                # Split on the first colon to separate key from value
                parts = line.split(':', 1)
                if len(parts) == 2:
                    key_part = parts[0].strip()
                    value_part = parts[1].strip()
                    
                    # Ensure key is properly quoted
                    if not key_part.startswith('"') or not key_part.endswith('"'):
                        # Remove any existing quotes and re-add them properly
                        key_clean = key_part.strip('"').strip("'").strip()
                        key_part = f'"{key_clean}"'
                    
                    # Handle value formatting
                    if value_part.endswith(','):
                        value_part = value_part[:-1]  # Remove trailing comma
                        trailing_comma = ','
                    else:
                        trailing_comma = ''
                    
                    # If value is a number, don't quote it
                    if re.match(r'^\d+$', value_part.strip()):
                        line = f"{key_part}: {value_part}{trailing_comma}"
                    # If value is already quoted string, fix any internal quote issues
                    elif value_part.startswith('"') and value_part.endswith('"'):
                        # Extract content and escape internal quotes
                        content = value_part[1:-1]
                        content = content.replace('"', '\\"')
                        line = f"{key_part}: \"{content}\"{trailing_comma}"
                    # If value is unquoted string, quote it properly
                    else:
                        # Clean the value and escape quotes
                        content = value_part.strip().strip('"').strip("'")
                        content = content.replace('"', '\\"')
                        line = f"{key_part}: \"{content}\"{trailing_comma}"
            
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)
    
    def analyze_note_relevance(self, file_path: Path, content: str) -> Dict:
        """Use Gemini to analyze note relevance and provide scoring."""
        if not content.strip():
            return {
                "score": 0,
                "reasoning": "Empty file with no content",
                "recommendation": "remove"
            }
            
        # Get vault context for comparative analysis
        vault_context = self.get_vault_context_for_analysis(file_path)
        
        prompt = f"""
Analyze this Obsidian note and provide a relevance assessment compared to the existing vault knowledge.

File: {file_path.name}
Path: {file_path.relative_to(self.vault_path)}

Content:
{content[:2000]}...

{vault_context}

Please provide:
1. A relevance score from 0-10 where:
   - 0-2: Poor quality, redundant with existing notes, or no unique value (should delete)
   - 3-4: Low value compared to existing knowledge, adds little new information
   - 5-6: Moderate value, has some unique content but could be improved
   - 7-8: High value, provides useful information not well covered elsewhere
   - 9-10: Essential content, unique and valuable knowledge

2. Brief reasoning for the score
3. Recommendation: "remove" (0-4), "enhance" (5-7), or "keep" (8-10)

IMPORTANT: Base the REMOVE recommendation on whether this note adds value compared to your existing knowledge base. Consider:
- Does this note contain information already covered better in other notes?
- Is this note of poor quality compared to similar notes in the vault?
- Does this note provide unique insights or information not found elsewhere?
- Would removing this note result in any loss of unique knowledge?

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

**MAJOR PENALTIES (-3-4 points each) - Content That Should Be Removed:**
- **Copy-pasted content without personal input**: -4 points (not your thoughts, just storage)
- **Information already covered better in other vault notes**: -4 points (redundant, inferior duplicate)
- **Easily recreated from Google/Wikipedia**: -4 points (generic information, not personal knowledge)
- **Temporary/outdated task lists** (completed todos, old project notes): -3 points (served their purpose)
- **Duplicate information** (same content exists in multiple places): -4 points (knowledge fragmentation, keep the better version)
- **Empty placeholder notes** (titles with no content, "TODO" notes never filled): -4 points (intellectual debt)
- **Poor quality compared to similar notes in vault**: -3 points (inferior version of existing knowledge)

**MODERATE PENALTIES (-2-3 points each) - Reduced Value Content:**
- **No WikiLinks or tags**: -3 points (isolated from knowledge network, defeats Obsidian's purpose)
- **No Obsidian links [[note name]]**: -3 points (not connected to other notes, missing knowledge graph value)
- **No tags or metadata**: -2 points (poor organization, hard to find and categorize)
- **Outdated technology/software notes** (unless personal setup): -2 points (temporal relevance lost)
- **Generic templates from internet** (unchanged, not personalized): -2 points (not your system)
- **Pure link collections** (no commentary, context, or personal organization): -2 points (no added value)
- **Work-only content** (company-specific info with no personal insight): -2 points (less relevant to personal knowledge)

**REMEMBER: Personal = Valuable. WikiLinks/Tags = Essential. Any note containing personal data, tracking, or financial information should score 7+ points. Notes with WikiLinks [[note name]] and tags #tag are the backbone of your knowledge network and should be strongly favored.**

CRITICAL: Respond with ONLY valid JSON in exactly this format (no additional text, no markdown formatting):
{{
    "score": 7,
    "reasoning": "Your explanation here",
    "recommendation": "enhance"
}}

JSON REQUIREMENTS:
- Use double quotes for all strings
- Score must be a number 0-10 (no quotes around numbers)
- Recommendation must be exactly one of: remove, enhance, keep
- No trailing commas
- No additional fields or text outside the JSON object
"""

        try:
            # Use rate limiting handler for the API call
            response = self.handle_rate_limiting(self.model.generate_content, prompt)
            # Extract JSON from response
            response_text = response.text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith('```json'):
                response_text = response_text.split('```json')[1].split('```')[0]
            elif response_text.startswith('```'):
                response_text = response_text.split('```')[1].split('```')[0]
            
            # Clean up the JSON response
            response_text = response_text.strip()
            
            # Try to parse JSON directly first
            try:
                result = json.loads(response_text)
            except json.JSONDecodeError:
                # If direct parsing fails, try cleaning and parsing again
                try:
                    cleaned_response = self.clean_json_response(response_text)
                    result = json.loads(cleaned_response)
                except json.JSONDecodeError:
                    # If all JSON parsing fails, use fallback regex parser
                    tqdm.write(f"JSON parsing failed for {file_path.name}, using fallback parser")
                    result = self.parse_ai_response_fallback(response_text)
            
            # Validate the result has required fields
            if not all(key in result for key in ['score', 'reasoning', 'recommendation']):
                # Try fallback parser if fields are missing
                result = self.parse_ai_response_fallback(response_text)
                
            # Validate score is in valid range
            if not isinstance(result['score'], (int, float)) or not (0 <= result['score'] <= 10):
                result['score'] = 5  # Default to middle score
                
            # Validate recommendation is valid
            if result['recommendation'] not in ['remove', 'enhance', 'keep']:
                if result['score'] <= 4:
                    result['recommendation'] = 'remove'
                elif result['score'] <= 7:
                    result['recommendation'] = 'enhance'
                else:
                    result['recommendation'] = 'keep'
            
            return result
            
        except Exception as e:
            tqdm.write(f"Error analyzing {file_path}: {e}")
            return {
                "score": 5,
                "reasoning": "AI analysis failed - unable to parse response. This note needs manual review.",
                "recommendation": "enhance"
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
        if recommendation == 'REMOVE':
            rec_color = Fore.RED
            emoji = "🗑️"
        elif recommendation == 'ENHANCE':
            rec_color = Fore.YELLOW
            emoji = "✨"
        else:  # KEEP
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
        if recommendation == 'REMOVE':
            rec_color = Fore.RED
            emoji = "🗑️"
        elif recommendation == 'ENHANCE':
            rec_color = Fore.YELLOW
            emoji = "✨"
        else:  # KEEP
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
            print("  [e] Enhance/Expand this note with AI")
            print("  [s] Skip for now")
            print("  [q] Quit the review process")
            
            print("\nPress a key (k/d/v/s/e/q) or Enter for default (keep): ", end="", flush=True)
            
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
                elif choice == 'e':
                    print("e")
                    return 'enhance'
                elif choice == 's':
                    print("s")
                    return 'skip'
                elif choice == 'q':
                    print("q")
                    return 'quit'
                else:
                    print(f"{choice} - Invalid choice. Please press k, d, v, s, e, q, or Enter for default (keep).")
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
            "enhanced_files": [str(f) for f in self.enhanced_files],
            "atomic_notes_created": self.atomic_notes_created,
            "atomic_notes_reviewed": getattr(self, 'atomic_notes_reviewed', []),
            "total_deleted": len(self.deleted_files),
            "total_kept": len(self.kept_files),
            "total_enhanced": len(self.enhanced_files),
            "total_atomic_notes_created": len(self.atomic_notes_created),
            "total_atomic_notes_reviewed": len(getattr(self, 'atomic_notes_reviewed', []))
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
        
        # Check for existing progress first
        continuing_session = False
        if self.load_progress():
            continuing_session = self.get_yes_no_input("\nDo you want to continue the previous review session?", default="y")
            if continuing_session:
                print("Continuing previous session...")
            else:
                print("Starting fresh review session...")
                # Reset progress
                self.processed_files = set()
                self.deleted_files = []
                self.kept_files = []
                self.enhanced_files = []
                self.atomic_notes_created = []
                self.atomic_notes_reviewed = []
        
        # Configure auto-decisions FIRST (before any vault scanning or token counting)
        if not continuing_session:
            # For new sessions, offer configuration more prominently
            if self.get_yes_no_input("Configure auto-decision settings before starting?", default="y"):
                self.configure_auto_decisions()
        else:
            # For continuing sessions, make it optional
            if self.get_yes_no_input("Configure auto-decision settings?", default="n"):
                self.configure_auto_decisions()
        
        # Now load vault knowledge for comparative analysis (this does token counting)
        self.load_vault_knowledge()
        
        # Find all markdown files (respects subfolder configuration set above)
        md_files = self.find_markdown_files()
        
        # Initialize queue for newly created atomic notes
        self.new_atomic_notes_queue = []
        
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
            # Convert to list to allow dynamic additions
            files_to_process = list(md_files)
            i = 0
            
            while i < len(files_to_process):
                file_path = files_to_process[i]
                i += 1
                current_position = processed_count + i
                
                # Don't clear screen at start of each file - just add spacing
                if i > 1:  # Skip spacing for first file
                    self.soft_clear_for_tqdm(5)
                
                # Show progress (use current list length for dynamic total)
                current_total = len(files_to_process) + len(self.processed_files)
                files_completed = processed_count + i - 1
                tqdm.write(f"Progress: {files_completed}/{current_total} files processed ({files_completed/current_total*100:.1f}%)")
                tqdm.write("")  # Add blank line for readability
                
                # Update progress bar with dynamic total
                progress_bar.total = current_total
                progress_bar.set_description(f"Processing: {file_path.name[:30]}...")
                
                # Read file content
                content = self.read_file_content(file_path)
                
                # Analyze with Gemini
                tqdm.write(f"Analyzing: {file_path.name}...")
                
                # Check if this is an atomic note that was created in this session
                is_created_atomic_note = file_path.stem in self.atomic_notes_created
                if is_created_atomic_note:
                    tqdm.write(f"📝 Note: This is an atomic note created during this session")
                
                analysis = self.analyze_note_relevance(file_path, content)
                
                # Check for auto-decision
                auto_decision = self.check_auto_decision(file_path, analysis)
                
                if auto_decision == "auto_keep":
                    self.kept_files.append(file_path)
                    if is_created_atomic_note:
                        self.atomic_notes_reviewed.append(file_path.stem)
                    self.processed_files.add(str(file_path))
                    self.save_progress()
                    decision = 'keep'
                elif auto_decision == "auto_delete":
                    if self.delete_file(file_path):
                        self.deleted_files.append(file_path)
                        if is_created_atomic_note:
                            self.atomic_notes_reviewed.append(file_path.stem)
                    self.processed_files.add(str(file_path))
                    self.save_progress()
                    decision = 'delete'
                else:
                    # Display results using tqdm.write
                    self.display_analysis_with_tqdm(file_path, analysis, content)
                    
                    # Get user decision (loop until they make a final choice)
                    while True:
                        # Temporarily clear progress bar for user input
                        progress_bar.clear()
                        decision = self.get_user_decision(analysis)
                        progress_bar.refresh()
                        
                        if decision == 'quit':
                            tqdm.write("\nReview process stopped by user.")
                            tqdm.write("Progress has been saved. You can continue later by running the script again.")
                            break
                        elif decision == 'view':
                            self.display_full_content_with_tqdm(file_path, content)
                            # Add spacing after viewing
                            self.soft_clear_for_tqdm(3)
                            # Show progress
                            files_completed = processed_count + i - 1
                            tqdm.write(f"Progress: {files_completed}/{total_files} files processed ({files_completed/total_files*100:.1f}%)")
                            tqdm.write("")  # Add blank line for readability
                            self.display_analysis_with_tqdm(file_path, analysis, content)
                            # Continue the loop to ask for decision again
                            continue
                        elif decision == 'enhance':
                            tqdm.write(f"\n🤖 Enhancing note with AI...")
                            enhanced_content = self.enhance_note(file_path, content)
                            
                            if enhanced_content != content:
                                # Don't clear screen here - just add spacing
                                self.soft_clear_for_tqdm(2)
                                
                                # Show the enhanced content
                                tqdm.write(f"{Fore.GREEN}✨ Enhanced Content Preview:{Style.RESET_ALL}")
                                tqdm.write("="*80)
                                preview = self.format_markdown_preview(enhanced_content, 800)
                                tqdm.write(preview)
                                tqdm.write("="*80)
                                
                                # Ask user if they want to save the enhancement
                                if len(content) > 0:
                                    ratio = len(enhanced_content) / len(content)
                                    tqdm.write(f"\nEnhanced from {len(content)} to {len(enhanced_content)} characters ({ratio:.1f}x longer)")
                                else:
                                    tqdm.write(f"\nEnhanced from empty file to {len(enhanced_content)} characters")
                                
                                # Temporarily pause tqdm to get user input
                                progress_bar.clear()
                                save_enhancement = self.get_yes_no_input("Save this enhanced version?")
                                progress_bar.refresh()
                                
                                if save_enhancement:
                                    if self.save_enhanced_note(file_path, enhanced_content):
                                        tqdm.write(f"{Fore.GREEN}✅ Note enhanced and saved!{Style.RESET_ALL}")
                                        self.enhanced_files.append(file_path)
                                        
                                        # Re-analyze the enhanced note
                                        tqdm.write(f"\n🔄 Re-analyzing enhanced note...")
                                        new_analysis = self.analyze_note_relevance(file_path, enhanced_content)
                                        
                                        # Add spacing instead of clearing
                                        self.soft_clear_for_tqdm(3)
                                        
                                        # Show progress
                                        files_completed = processed_count + i - 1
                                        tqdm.write(f"Progress: {files_completed}/{total_files} files processed ({files_completed/total_files*100:.1f}%)")
                                        tqdm.write("")
                                        
                                        tqdm.write(f"{Fore.GREEN}🎉 ENHANCED NOTE RE-ANALYSIS:{Style.RESET_ALL}")
                                        tqdm.write(f"📈 Score improved from {analysis['score']}/10 to {new_analysis['score']}/10 ({'+' if new_analysis['score'] > analysis['score'] else ''}{new_analysis['score'] - analysis['score']} points)")
                                        tqdm.write("")
                                        
                                        # Show the enhanced note analysis
                                        self.display_analysis_with_tqdm(file_path, new_analysis, enhanced_content)
                                        
                                        # Check for auto-decision on enhanced note
                                        enhanced_auto_decision = self.check_auto_decision(file_path, new_analysis)
                                        
                                        if enhanced_auto_decision == "auto_keep":
                                            self.kept_files.append(file_path)
                                            if is_created_atomic_note:
                                                self.atomic_notes_reviewed.append(file_path.stem)
                                            tqdm.write(f"Enhanced note auto-kept: {file_path}")
                                            self.processed_files.add(str(file_path))
                                            self.save_progress()
                                            break
                                        elif enhanced_auto_decision == "auto_delete":
                                            if self.delete_file(file_path):
                                                self.deleted_files.append(file_path)
                                                if is_created_atomic_note:
                                                    self.atomic_notes_reviewed.append(file_path.stem)
                                            self.processed_files.add(str(file_path))
                                            self.save_progress()
                                            break
                                        
                                        # Ask final decision on enhanced note
                                        enhanced_decision = None
                                        while True:
                                            # Pause tqdm for user input
                                            progress_bar.clear()
                                            enhanced_decision = self.get_user_decision(new_analysis)
                                            progress_bar.refresh()
                                            
                                            if enhanced_decision in ['keep', 'delete', 'skip', 'quit']:
                                                break
                                            elif enhanced_decision == 'view':
                                                self.display_full_content_with_tqdm(file_path, enhanced_content)
                                                self.soft_clear_for_tqdm(3)
                                                files_completed = processed_count + i - 1
                                                tqdm.write(f"Progress: {files_completed}/{total_files} files processed ({files_completed/total_files*100:.1f}%)")
                                                tqdm.write("")
                                                tqdm.write(f"{Fore.GREEN}🎉 ENHANCED NOTE RE-ANALYSIS:{Style.RESET_ALL}")
                                                tqdm.write(f"📈 Score improved from {analysis['score']}/10 to {new_analysis['score']}/10 ({'+' if new_analysis['score'] > analysis['score'] else ''}{new_analysis['score'] - analysis['score']} points)")
                                                tqdm.write("")
                                                self.display_analysis_with_tqdm(file_path, new_analysis, enhanced_content)
                                                continue
                                            elif enhanced_decision == 'enhance':
                                                tqdm.write("Note was already enhanced. Choose keep, delete, or skip.")
                                                continue
                                                
                                        if enhanced_decision == 'keep':
                                            self.kept_files.append(file_path)
                                            if is_created_atomic_note:
                                                self.atomic_notes_reviewed.append(file_path.stem)
                                            tqdm.write(f"Enhanced note kept: {file_path}")
                                        elif enhanced_decision == 'delete':
                                            if self.delete_file(file_path):
                                                self.deleted_files.append(file_path)
                                                if is_created_atomic_note:
                                                    self.atomic_notes_reviewed.append(file_path.stem)
                                        elif enhanced_decision == 'skip':
                                            if is_created_atomic_note:
                                                self.atomic_notes_reviewed.append(file_path.stem)
                                            tqdm.write(f"Enhanced note skipped: {file_path}")
                                        elif enhanced_decision == 'quit':
                                            decision = 'quit'
                                            
                                        self.processed_files.add(str(file_path))
                                        self.save_progress()
                                        break
                                    else:
                                        tqdm.write(f"{Fore.RED}❌ Failed to save enhanced note{Style.RESET_ALL}")
                                        # Continue the loop to ask for decision again
                                        continue
                                else:
                                    tqdm.write("Enhancement cancelled. Original note unchanged.")
                                    # Add spacing and re-display analysis
                                    self.soft_clear_for_tqdm(3)
                                    files_completed = processed_count + i - 1
                                    tqdm.write(f"Progress: {files_completed}/{total_files} files processed ({files_completed/total_files*100:.1f}%)")
                                    tqdm.write("")
                                    self.display_analysis_with_tqdm(file_path, analysis, content)
                                    continue
                            else:
                                tqdm.write(f"{Fore.YELLOW}⚠️ Enhancement failed or no changes made{Style.RESET_ALL}")
                                # Continue the loop to ask for decision again
                                continue
                        elif decision == 'delete':
                            if self.delete_file(file_path):
                                self.deleted_files.append(file_path)
                                if is_created_atomic_note:
                                    self.atomic_notes_reviewed.append(file_path.stem)
                            self.processed_files.add(str(file_path))
                            self.save_progress()  # Save progress after each file
                            break
                        elif decision == 'keep':
                            self.kept_files.append(file_path)
                            if is_created_atomic_note:
                                self.atomic_notes_reviewed.append(file_path.stem)
                            tqdm.write(f"Kept: {file_path}")
                            self.processed_files.add(str(file_path))
                            self.save_progress()  # Save progress after each file
                            break
                        elif decision == 'skip':
                            if is_created_atomic_note:
                                self.atomic_notes_reviewed.append(file_path.stem)
                            tqdm.write(f"Skipped: {file_path}")
                            self.processed_files.add(str(file_path))
                            self.save_progress()  # Save progress after each file
                            break
                        
                # Update progress bar
                progress_bar.update(1)
                
                # Process any newly created atomic notes
                if self.new_atomic_notes_queue:
                    tqdm.write(f"\n🔄 Processing {len(self.new_atomic_notes_queue)} newly created atomic notes...")
                    
                    # Add new atomic notes to the processing queue (insert at current position for alphabetical order)
                    new_notes = list(self.new_atomic_notes_queue)
                    self.new_atomic_notes_queue.clear()
                    
                    # Insert new notes in correct alphabetical position
                    for new_note_path in sorted(new_notes):
                        # Find the correct insertion point to maintain alphabetical order
                        insert_pos = i  # Start from current position
                        for j in range(i, len(files_to_process)):
                            if str(new_note_path) < str(files_to_process[j]):
                                insert_pos = j
                                break
                        
                        # Only add if not already processed and not already in queue
                        if (str(new_note_path) not in self.processed_files and 
                            new_note_path not in files_to_process):
                            files_to_process.insert(insert_pos, new_note_path)
                            tqdm.write(f"   📝 Added to review queue: {new_note_path.name}")
                        
                # Break out of outer loop if user chose quit
                if decision == 'quit':
                    break
                    
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
        print(f"{Fore.YELLOW}Files enhanced: {len(self.enhanced_files)}{Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}Atomic notes created: {len(self.atomic_notes_created)}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Total processed: {len(self.deleted_files) + len(self.kept_files)}{Style.RESET_ALL}")
        
        if self.atomic_notes_created:
            print(f"\n{Fore.MAGENTA}🔗 Atomic notes created:{Style.RESET_ALL}")
            for note_title in self.atomic_notes_created:
                if note_title in self.atomic_notes_reviewed:
                    print(f"   - {note_title}.md ✅ (also reviewed)")
                else:
                    print(f"   - {note_title}.md")
        
        if self.enhanced_files:
            print(f"\n{Fore.YELLOW}✨ Enhanced files:{Style.RESET_ALL}")
            for file_path in self.enhanced_files:
                print(f"   - {file_path.relative_to(self.vault_path)}")
        
        if self.deleted_files:
            print(f"\n{Fore.RED}🗑️ Deleted files:{Style.RESET_ALL}")
            for file_path in self.deleted_files:
                print(f"   - {file_path.relative_to(self.vault_path)}")

    def restore_note_from_backup(self, file_path: Path, original_content: str) -> bool:
        """
        Restore a note to its original content (useful if enhancement went wrong).
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(original_content)
            tqdm.write(f"✅ Restored note to original content: {file_path.name}")
            return True
        except Exception as e:
            tqdm.write(f"❌ Failed to restore note: {e}")
            return False


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
    
    # Get vault path (suggest last used path or current directory)
    last_used_path = ObsidianVaultReviewer.get_last_used_vault_path()
    
    if last_used_path and os.path.exists(last_used_path):
        # Show last used path as default
        default_display = f"last used: {last_used_path}"
        default_path = last_used_path
    else:
        # Fall back to current directory
        default_display = "current directory"
        default_path = os.getcwd()
    
    while True:
        vault_path = input(f"Enter vault path (default: {default_display}): ").strip()
        if not vault_path:
            vault_path = default_path
            
        if os.path.exists(vault_path):
            break
        else:
            print(f"❌ Vault path does not exist: {vault_path}")
            print(f"Please enter a valid directory path or press Enter for default ({default_display}).")
            continue
        
    # Create reviewer
    reviewer = ObsidianVaultReviewer(api_key, vault_path)
    
    # Quick file size configuration option
    current_size = reviewer.config.get("max_file_size_kb", 20)
    print(f"\nCurrent file size limit: {current_size}KB")
    size_input = input(f"Enter new file size limit in KB (10-100) or press Enter to keep {current_size}KB: ").strip()
    if size_input:
        try:
            new_size = int(size_input)
            if 10 <= new_size <= 100:
                reviewer.config["max_file_size_kb"] = new_size
                reviewer.save_config()
                print(f"File size limit updated to: {new_size}KB")
            else:
                print("Invalid size. Using current value.")
        except ValueError:
            print("Invalid input. Using current value.")
    
    # Start review
    reviewer.review_vault()


if __name__ == "__main__":
    main() 