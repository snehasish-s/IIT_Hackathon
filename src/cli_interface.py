#!/usr/bin/env python3
"""
Interactive CLI Interface for Causal Chat Analysis
Run: python -m src.cli_interface
Or: python src/cli_interface.py
"""

import sys
from pathlib import Path
from typing import Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.load_data import load_transcripts
from src.preprocess import preprocess_transcripts
from src.causal_chains import CausalChainDetector
from src.causal_query_engine import CausalQueryEngine
from src.explanation_generator import ExplanationGenerator
from src.causal_model import Outcome


class CausalCLI:
    """Interactive command-line interface for causal reasoning"""
    
    def __init__(self):
        self.engine = None
        self.detector = None
        self.transcripts_dict = {}
        self.loaded = False
        self._load_system()
    
    def _load_system(self):
        """Load data and initialize query engine"""
        print("🔄 Initializing Causal Analysis Engine...")
        print("   Loading transcripts...", end="", flush=True)
        transcripts = load_transcripts()
        self.transcripts_dict = {t["transcript_id"]: t for t in transcripts}
        print(f" {len(transcripts)} loaded")
        
        print("   Preprocessing...", end="", flush=True)
        processed_turns = preprocess_transcripts(transcripts)
        print(f" {len(processed_turns)} turns")
        
        print("   Computing causal chains...", end="", flush=True)
        self.detector = CausalChainDetector()
        self.detector.compute_chain_statistics(transcripts, processed_turns)
        print(f" {len(self.detector.chain_stats)} chains")
        
        print("   Initializing query engine...", end="", flush=True)
        self.engine = CausalQueryEngine(self.detector, self.transcripts_dict, processed_turns)
        print(" ✓")
        
        self.loaded = True
        print("\n✅ System ready!\n")
    
    def print_header(self):
        """Print welcome message"""
        print("\n" + "="*70)
        print("  🎯 CAUSAL CHAT ANALYSIS - Interactive Query Engine")
        print("="*70)
        print("\nAsk 'why' questions about conversation transcripts.")
        print("Example: explain ABC123")
        print("Type 'help' for commands, 'quit' to exit.\n")
    
    def print_help(self):
        """Print available commands"""
        help_text = """
Available Commands:
───────────────────────────────────────────────────────────────

  Basic Queries:
    explain <transcript_id>      Why did this transcript behave this way?
    why <transcript_id>          Alias for 'explain'
    
  Analysis:
    similar <transcript_id>      Find cases with similar patterns
    chain <signal1> <signal2>    Statistics on a causal chain pattern
    top-chains                   Show top causal chains by confidence
    
  System:
    stats                        Overall system statistics
    list-signals                 Show all signal types
    help                         Show this message
    quit                         Exit

Examples:
───────────────────────────────────────────────────────────────
  > explain conv_12345
  > similar conv_12345
  > chain customer_frustration agent_delay
  > top-chains
  > list-signals

"""
        print(help_text)
    
    def print_prompt(self):
        """Print input prompt"""
        print("causal> ", end="", flush=True)
    
    def handle_explain(self, transcript_id: str):
        """Handle 'explain' command"""
        if transcript_id not in self.transcripts_dict:
            print(f"❌ Transcript '{transcript_id}' not found")
            print(f"   Try with one of: {list(self.transcripts_dict.keys())[:5]}...")
            return
        
        explanation = self.engine.explain_escalation(transcript_id)
        if not explanation:
            print("❌ Could not analyze this transcript")
            return
        
        # Print detailed report
        print("\n" + ExplanationGenerator.generate_detailed_report(explanation))
        print()
    
    def handle_similar(self, transcript_id: str):
        """Handle 'similar' command"""
        if transcript_id not in self.transcripts_dict:
            print(f"❌ Transcript '{transcript_id}' not found")
            return
        
        similar_cases = self.engine.find_similar_cases(transcript_id, top_k=10)
        
        print(f"\n📊 Transcripts with similar causal patterns:")
        print(f"   Reference: {transcript_id}")
        print(f"   Found: {len(similar_cases)} similar cases\n")
        
        for i, case_id in enumerate(similar_cases, 1):
            exp = self.engine.explain_escalation(case_id)
            if exp:
                chain_str = " → ".join(exp.causal_chain.signals)
                print(f"   {i}. {case_id}")
                print(f"      Chain: {chain_str}")
                print(f"      Outcome: {exp.outcome.value}")
                print()
    
    def handle_chain(self, args: list):
        """Handle 'chain' command"""
        if len(args) < 2:
            print("❌ Usage: chain <signal1> <signal2> [signal3]")
            return
        
        chain_tuple = tuple(args)
        stats = self.engine.analyze_chain_pattern(chain_tuple)
        
        if not stats:
            print(f"❌ Chain pattern {' → '.join(chain_tuple)} not found in data")
            return
        
        print(f"\n📈 Chain Statistics: {' → '.join(chain_tuple)}")
        print(f"───────────────────────────────────────")
        print(f"  Total occurrences:     {stats['occurrences']}")
        print(f"  Escalated:             {stats['escalated_count']} ({stats['escalated_count']/stats['occurrences']*100:.1f}%)")
        print(f"  Resolved:              {stats['resolved_count']} ({stats['resolved_count']/stats['occurrences']*100:.1f}%)")
        print(f"  Confidence:            {stats['confidence']:.1%}")
        print(f"  95% CI:                ({stats['confidence_interval'][0]:.2f}, {stats['confidence_interval'][1]:.2f})")
        
        if stats['examples']:
            print(f"\n  Example transcripts:")
            for example_id in stats['examples'][:3]:
                print(f"    • {example_id}")
        print()
    
    def handle_top_chains(self):
        """Handle 'top-chains' command"""
        print("\n📊 Top Causal Chains (by confidence and evidence):")
        print("───────────────────────────────────────────────────────────────")
        self.detector.print_top_chains(top_k=15, min_confidence=0.25)
        print()
    
    def handle_stats(self):
        """Handle 'stats' command"""
        total_transcripts = len(self.transcripts_dict)
        total_chains = len(self.detector.chain_stats)
        
        escalated = sum(1 for t in self.transcripts_dict.values() 
                       if self._get_outcome(t) == Outcome.ESCALATED)
        resolved = total_transcripts - escalated
        
        print(f"\n📊 System Statistics:")
        print(f"───────────────────────────────────────")
        print(f"  Total transcripts:     {total_transcripts}")
        print(f"  Escalated:             {escalated} ({escalated/total_transcripts*100:.1f}%)")
        print(f"  Resolved:              {resolved} ({resolved/total_transcripts*100:.1f}%)")
        print(f"  Causal chains found:   {total_chains}")
        print()
    
    def handle_list_signals(self):
        """Handle 'list-signals' command"""
        # Get unique signal types from chain stats
        signal_types = set()
        for chain_key in self.detector.chain_stats.keys():
            for signal in chain_key:
                signal_types.add(signal)
        
        print(f"\n🔍 Available Signal Types:")
        print(f"───────────────────────────────────────")
        for signal in sorted(signal_types):
            readable = signal.replace("_", " ").title()
            print(f"  • {readable} ({signal})")
        print()
    
    def _get_outcome(self, transcript: dict) -> Outcome:
        """Get outcome for a transcript"""
        from src.preprocess import label_outcome
        outcome_str = label_outcome(transcript).lower()
        return Outcome.ESCALATED if "escalat" in outcome_str else Outcome.RESOLVED
    
    def parse_command(self, user_input: str):
        """Parse and execute user command"""
        user_input = user_input.strip()
        if not user_input:
            return
        
        parts = user_input.split()
        command = parts[0].lower()
        args = parts[1:]
        
        # Route to handler
        if command in ["explain", "why"]:
            if args:
                self.handle_explain(args[0])
            else:
                print("❌ Usage: explain <transcript_id>")
        
        elif command == "similar":
            if args:
                self.handle_similar(args[0])
            else:
                print("❌ Usage: similar <transcript_id>")
        
        elif command == "chain":
            self.handle_chain(args)
        
        elif command == "top-chains":
            self.handle_top_chains()
        
        elif command == "stats":
            self.handle_stats()
        
        elif command == "list-signals":
            self.handle_list_signals()
        
        elif command == "help":
            self.print_help()
        
        elif command == "quit":
            print("\n👋 Goodbye!\n")
            sys.exit(0)
        
        else:
            print(f"❌ Unknown command: {command}")
            print("   Type 'help' for available commands")
    
    def run(self):
        """Main interactive loop"""
        if not self.loaded:
            print("❌ Failed to initialize system")
            return
        
        self.print_header()
        
        try:
            while True:
                self.print_prompt()
                user_input = input()
                self.parse_command(user_input)
        except KeyboardInterrupt:
            print("\n\n👋 Interrupted. Goodbye!")
            sys.exit(0)
        except Exception as e:
            print(f"\n❌ Error: {e}")
            sys.exit(1)


def main():
    """Entry point"""
    cli = CausalCLI()
    cli.run()


if __name__ == "__main__":
    main()
