"""
Causal Chains Module - Detect and analyze causal signal sequences
Builds chains like: customer_frustration → agent_delay → escalation (78% confidence)
"""

from collections import defaultdict
from typing import List, Dict, Tuple, Optional
import json

from src.causal_model import CausalChain, TemporalSignalSequence, Outcome, Signal, DEFAULT_CAUSAL_PATTERNS
from src.signal_extraction import extract_signals, get_signal_confidence
from src.preprocess import label_outcome


class CausalChainDetector:
    """Detect and analyze causal signal chains"""
    
    def __init__(self):
        self.chain_stats = {}  # Computed chain statistics
        self.chain_examples = defaultdict(list)  # Examples for each chain
        
    def build_temporal_sequence(self, transcript: dict, 
                               processed_turns: List[dict]) -> TemporalSignalSequence:
        """
        Build ordered signal sequence for a single transcript
        
        Args:
            transcript: Original transcript dict
            processed_turns: Turns from this transcript (must be pre-filtered)
        
        Returns:
            TemporalSignalSequence with signals in order
        """
        transcript_id = transcript["transcript_id"]
        outcome = Outcome(label_outcome(transcript).lower())
        
        sequence = TemporalSignalSequence(transcript_id=transcript_id, outcome=outcome)
        
        # Extract signals with temporal info
        for turn in processed_turns:
            signals_list = extract_signals(turn)
            
            for signal_type in signals_list:
                confidence = get_signal_confidence(turn, signal_type)
                signal = Signal(
                    type=signal_type,
                    turn_number=turn["turn_number"],
                    speaker=turn["speaker"],
                    confidence=confidence,
                    text=turn["text"]
                )
                sequence.add_signal(signal)
        
        return sequence
    
    def extract_chains_from_sequence(self, sequence: TemporalSignalSequence, 
                                    max_chain_length: int = 3) -> List[CausalChain]:
        """
        Extract all possible causal chains from a sequence
        
        A chain is a sub-sequence of signals that may lead to the outcome
        
        Args:
            sequence: TemporalSignalSequence to analyze
            max_chain_length: Maximum signals to consider in a chain
        
        Returns:
            List of CausalChain objects
        """
        chains = []
        
        # Get all possible chains from this sequence
        chain_lists = sequence.get_chains_up_to_length(max_chain_length)
        
        for chain_list in chain_lists:
            chain = CausalChain(
                signals=chain_list,
                outcome=sequence.outcome,
                confidence=0.0,  # Will be computed later
                evidence_count=1  # This transcript is one example
            )
            chains.append(chain)
        
        return chains
    
    def compute_chain_statistics(self, all_transcripts: List[dict],
                                all_processed_turns: List[dict],
                                min_evidence: int = 5) -> Dict[Tuple[str, ...], dict]:
        """
        Compute statistics for all detected causal chains
        
        This is the CORE algorithm:
        - Find all chains across all transcripts
        - Count: how many transcripts have this chain?
        - Count: how many of those escalated?
        - Compute: P(escalated | chain)
        
        Args:
            all_transcripts: All transcript dicts
            all_processed_turns: All processed turns (pre-filtered by transcript)
            min_evidence: Minimum transcripts needed for a chain to be reported
        
        Returns:
            {
                ("customer_frustration", "agent_delay"): {
                    "occurrences": 243,
                    "escalated_count": 158,
                    "resolved_count": 85,
                    "confidence": 0.65,
                    "examples": ["id1", "id2", ...],
                    "confidence_interval": (0.59, 0.71)
                },
                ...
            }
        """
        chain_tracker = defaultdict(lambda: {
            "occurrences": 0,
            "escalated_count": 0,
            "resolved_count": 0,
            "examples": []
        })
        
        # Build sequences for each transcript
        for transcript in all_transcripts:
            transcript_id = transcript["transcript_id"]
            
            # Get turns for this transcript
            transcript_turns = [t for t in all_processed_turns 
                              if t["transcript_id"] == transcript_id]
            
            if not transcript_turns:
                continue
            
            # Build temporal sequence
            sequence = self.build_temporal_sequence(transcript, transcript_turns)
            
            # Extract chains
            chains = self.extract_chains_from_sequence(sequence)
            
            # Record each chain
            for chain in chains:
                chain_key = tuple(chain.signals)
                chain_tracker[chain_key]["occurrences"] += 1
                
                if sequence.outcome == Outcome.ESCALATED:
                    chain_tracker[chain_key]["escalated_count"] += 1
                else:
                    chain_tracker[chain_key]["resolved_count"] += 1
                
                # Store example IDs (limit storage)
                if len(chain_tracker[chain_key]["examples"]) < 10:
                    chain_tracker[chain_key]["examples"].append(transcript_id)
        
        # Convert to final format with confidence scores
        self.chain_stats = {}
        for chain_key, stats in chain_tracker.items():
            if stats["occurrences"] < min_evidence:
                continue  # Skip chains with insufficient evidence
            
            confidence = stats["escalated_count"] / stats["occurrences"]
            confidence_interval = self._wilson_ci(stats["escalated_count"], 
                                                  stats["occurrences"])
            
            self.chain_stats[chain_key] = {
                "occurrences": stats["occurrences"],
                "escalated_count": stats["escalated_count"],
                "resolved_count": stats["resolved_count"],
                "confidence": confidence,
                "confidence_interval": confidence_interval,
                "examples": stats["examples"],
                "valid": True
            }
        
        return self.chain_stats
    
    def find_best_chain_for_transcript(self, transcript_id: str,
                                      sequence: TemporalSignalSequence,
                                      top_k: int = 3) -> List[Tuple[CausalChain, float]]:
        """
        Find the best causal chain(s) that explain this specific transcript
        
        Returns chains ranked by how well they explain the outcome
        
        Args:
            transcript_id: ID to explain
            sequence: Its signal sequence
            top_k: Return top K chains
        
        Returns:
            List of (CausalChain, match_score) tuples, ranked by match_score
        """
        chains = self.extract_chains_from_sequence(sequence)
        chain_scores = []
        
        for chain in chains:
            chain_key = tuple(chain.signals)
            
            # Look up statistics for this chain
            if chain_key in self.chain_stats:
                stats = self.chain_stats[chain_key]
                match_score = stats["confidence"]
            else:
                # Chain not in statistics, use default low score
                match_score = 0.1
            
            chain_scores.append((chain, match_score))
        
        # Sort by score, descending
        chain_scores.sort(key=lambda x: x[1], reverse=True)
        
        return chain_scores[:top_k]
    
    def get_alternative_chains(self, primary_chain: CausalChain,
                              sequence: TemporalSignalSequence,
                              top_k: int = 2) -> List[CausalChain]:
        """
        Get alternative causal chains that could explain the same outcome
        
        Useful for: "This escalation could also be explained by X..."
        """
        ranked_chains = self.find_best_chain_for_transcript(
            sequence.transcript_id, sequence, top_k=5
        )
        
        # Exclude the primary chain
        alternatives = [c for c, _ in ranked_chains 
                       if c.signals != primary_chain.signals]
        
        return alternatives[:top_k]
    
    @staticmethod
    def _wilson_ci(successes: int, total: int, z: float = 1.96) -> Tuple[float, float]:
        """
        Compute Wilson score confidence interval
        More appropriate than binomial CI for small samples
        
        Args:
            successes: Number of escalations
            total: Total number of occurrences
            z: Z-score (1.96 for 95% CI)
        
        Returns:
            (lower_bound, upper_bound)
        """
        if total == 0:
            return (0.0, 1.0)
        
        p = successes / total
        denominator = 1 + z**2 / total
        
        centre = (p + z**2 / (2 * total)) / denominator
        margin = z * (p * (1 - p) / total + z**2 / (4 * total))**0.5 / denominator
        
        lower = max(0.0, centre - margin)
        upper = min(1.0, centre + margin)
        
        return (lower, upper)
    
    def export_chains(self, filepath: str):
        """Export chain statistics to JSON for inspection"""
        # Convert tuples to strings for JSON serialization
        export_data = {}
        for chain_key, stats in self.chain_stats.items():
            chain_str = " → ".join(chain_key)
            export_data[chain_str] = {
                **stats,
                "confidence_interval": [round(x, 3) for x in stats["confidence_interval"]]
            }
        
        with open(filepath, "w") as f:
            json.dump(export_data, f, indent=2)
    
    def print_top_chains(self, top_k: int = 10, min_confidence: float = 0.3):
        """Print top causal chains sorted by confidence and evidence"""
        chains = sorted(
            self.chain_stats.items(),
            key=lambda x: (x[1]["confidence"], -x[1]["occurrences"]),
            reverse=True
        )
        
        print(f"\n{'':40} {'Conf':>8} {'Occur':>6} {'Esc':>5} {'CI (95%)':>20}")
        print("─" * 90)
        
        for chain_key, stats in chains[:top_k]:
            if stats["confidence"] < min_confidence:
                break
            
            chain_name = " → ".join(chain_key)
            conf = stats["confidence"]
            ci_lower, ci_upper = stats["confidence_interval"]
            
            print(f"{chain_name:40} {conf:>7.1%} {stats['occurrences']:>6} "
                  f"{stats['escalated_count']:>5} ({ci_lower:.2f}, {ci_upper:.2f})")
