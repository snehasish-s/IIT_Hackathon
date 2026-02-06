"""
Causal Query Engine - Answer "Why did this escalate?" questions
Main interface for query-driven causal reasoning
"""

from typing import List, Dict, Optional, Tuple
import json

from src.causal_model import CausalExplanation, CausalChain, Signal, Outcome, TemporalSignalSequence
from src.causal_chains import CausalChainDetector
from src.signal_extraction import extract_signals, get_signal_confidence
from src.preprocess import label_outcome


class CausalQueryEngine:
    """
    Main query interface: "Why did transcript X have outcome Y?"
    """
    
    def __init__(self, chain_detector: CausalChainDetector, 
                 all_transcripts: Dict[str, dict],
                 all_processed_turns: List[dict]):
        """
        Initialize query engine
        
        Args:
            chain_detector: Pre-computed CausalChainDetector with statistics
            all_transcripts: Dict mapping transcript_id → transcript
            all_processed_turns: All turns with signal info
        """
        self.detector = chain_detector
        self.transcripts = all_transcripts
        self.processed_turns = all_processed_turns
        self.turn_index = self._build_turn_index(all_processed_turns)
    
    def _build_turn_index(self, turns: List[dict]) -> Dict[str, List[dict]]:
        """Build index: transcript_id → turns for fast lookup"""
        index = {}
        for turn in turns:
            tid = turn["transcript_id"]
            if tid not in index:
                index[tid] = []
            index[tid].append(turn)
        return index
    
    def explain_escalation(self, transcript_id: str) -> Optional[CausalExplanation]:
        """
        MAIN QUERY FUNCTION: "Why did this transcript escalate?"
        
        Algorithm:
        1. Validate transcript exists
        2. Build temporal signal sequence
        3. Find best matching causal chain
        4. Collect evidence (direct quotes)
        5. Rank alternative explanations
        6. Compute confidence
        
        Args:
            transcript_id: ID of transcript to explain
        
        Returns:
            CausalExplanation with chain, evidence, and confidence
            or None if transcript not found
        """
        
        # Get transcript
        if transcript_id not in self.transcripts:
            return None
        
        transcript = self.transcripts[transcript_id]
        
        # Get turns for this transcript
        turns = self.turn_index.get(transcript_id, [])
        if not turns:
            return None
        
        # Build temporal sequence
        sequence = self.detector.build_temporal_sequence(transcript, turns)
        
        # Find best chain(s)
        ranked_chains = self.detector.find_best_chain_for_transcript(
            transcript_id, sequence, top_k=3
        )
        
        if not ranked_chains:
            # No chains found, create default explanation
            return self._create_default_explanation(transcript_id, sequence)
        
        best_chain, best_score = ranked_chains[0]
        best_chain.confidence = best_score
        
        # Build explanation
        explanation = CausalExplanation(
            transcript_id=transcript_id,
            outcome=sequence.outcome,
            causal_chain=best_chain,
            confidence=best_score
        )
        
        # Add evidence (quotes from turns)
        explanation.evidence = sequence.signals
        explanation.evidence_quotes = self._extract_evidence_quotes(
            transcript_id, best_chain.signals
        )
        
        # Add alternatives
        explanation.alternative_chains = self.detector.get_alternative_chains(
            best_chain, sequence, top_k=2
        )
        
        return explanation
    
    def explain_resolution(self, transcript_id: str) -> Optional[CausalExplanation]:
        """
        Similar to explain_escalation, but for RESOLVED conversations
        "Why did this conversation resolve successfully?"
        """
        # Same logic as escalation, just different outcome focus
        return self.explain_escalation(transcript_id)
    
    def find_similar_cases(self, transcript_id: str, 
                          top_k: int = 5) -> List[str]:
        """
        Find other transcripts with similar causal patterns
        
        Args:
            transcript_id: Reference transcript
            top_k: Return top K similar cases
        
        Returns:
            List of similar transcript IDs
        """
        # Get explanation for reference
        explanation = self.explain_escalation(transcript_id)
        if not explanation:
            return []
        
        # Get the best chain
        chain_key = tuple(explanation.causal_chain.signals)
        
        # Find all transcripts with this chain
        similar = self.detector.chain_stats.get(chain_key, {}).get("examples", [])
        
        # Remove the reference transcript itself
        similar = [tid for tid in similar if tid != transcript_id]
        
        return similar[:top_k]
    
    def analyze_chain_pattern(self, chain_signals: Tuple[str, ...]) -> Optional[dict]:
        """
        Get detailed statistics for a specific causal chain pattern
        
        Args:
            chain_signals: Tuple like ("customer_frustration", "agent_delay")
        
        Returns:
            Statistics dict or None if chain not found
        """
        chain_key = tuple(chain_signals)
        return self.detector.chain_stats.get(chain_key)
    
    def query(self, question: str, context: Optional[dict] = None) -> dict:
        """
        Parse and answer a natural language question
        
        Supported questions:
        - "Why did ABC123 escalate?"
        - "Explain ABC123"
        - "What caused the escalation in ABC123?"
        - "Similar to ABC123"
        
        Args:
            question: Natural language question
            context: Optional previous query context
        
        Returns:
            Response dict with answer and metadata
        """
        question_lower = question.lower()
        
        # Pattern 1: "why/explain/what ABC123 [escalate]?"
        if any(word in question_lower for word in ["why", "explain", "what caused"]):
            # Extract transcript ID
            tid = self._extract_transcript_id(question)
            if tid and tid in self.transcripts:
                explanation = self.explain_escalation(tid)
                if explanation:
                    return self._format_explanation_response(explanation)
        
        # Pattern 2: "similar to ABC123"
        if "similar" in question_lower:
            tid = self._extract_transcript_id(question)
            if tid:
                similar = self.find_similar_cases(tid)
                return {
                    "type": "similar_cases",
                    "reference_transcript": tid,
                    "similar_cases": similar,
                    "count": len(similar)
                }
        
        # Pattern 3: "stats on [chain pattern]"
        if "stats" in question_lower or "pattern" in question_lower:
            # Try to extract signal types
            pass
        
        return {"error": "Could not parse question", "question": question}
    
    def _extract_transcript_id(self, text: str) -> Optional[str]:
        """Extract transcript ID from text (simple heuristic)"""
        # Look for patterns like ABC123, conv_123, etc.
        words = text.split()
        for word in words:
            # Remove punctuation
            word = word.strip('.,?!')
            if word in self.transcripts:
                return word
            # Check if it's a reasonable ID length
            if len(word) > 4 and (word[0].isalpha() or word[0].isdigit()):
                if word in self.transcripts:
                    return word
        return None
    
    def _extract_evidence_quotes(self, transcript_id: str, 
                                 signal_types: List[str]) -> List[dict]:
        """
        Extract direct quotes that support the causal chain
        
        Args:
            transcript_id: Transcript ID
            signal_types: List of signal types in the chain
        
        Returns:
            List of quote dicts: {turn, speaker, text}
        """
        turns = self.turn_index.get(transcript_id, [])
        quotes = []
        
        # For each signal type, find a supporting quote
        for signal_type in signal_types:
            for turn in turns:
                # Check if this turn has the signal
                signals = extract_signals(turn)
                if signal_type in signals:
                    quotes.append({
                        "turn_number": turn["turn_number"],
                        "speaker": turn["speaker"],
                        "text": turn["text"],
                        "signal": signal_type,
                        "confidence": get_signal_confidence(turn, signal_type)
                    })
                    break  # One quote per signal type
        
        return quotes
    
    def _create_default_explanation(self, transcript_id: str,
                                   sequence: TemporalSignalSequence) -> CausalExplanation:
        """Create a basic explanation when no chains are found"""
        # Get the first signal as primary cause
        primary_signal = sequence.signals[0].type if sequence.signals else "unknown"
        
        chain = CausalChain(
            signals=[primary_signal],
            outcome=sequence.outcome,
            confidence=0.5,
            evidence_count=1
        )
        
        explanation = CausalExplanation(
            transcript_id=transcript_id,
            outcome=sequence.outcome,
            causal_chain=chain,
            evidence=sequence.signals,
            confidence=0.5
        )
        
        return explanation
    
    def _format_explanation_response(self, explanation: CausalExplanation) -> dict:
        """Convert CausalExplanation to API response format"""
        return {
            "type": "explanation",
            "transcript_id": explanation.transcript_id,
            "outcome": explanation.outcome.value,
            "causal_chain": {
                "signals": explanation.causal_chain.signals,
                "confidence": explanation.causal_chain.confidence,
                "chain_string": " → ".join(explanation.causal_chain.signals)
            },
            "primary_cause": explanation.primary_cause(),
            "secondary_causes": explanation.secondary_causes(),
            "confidence": explanation.confidence,
            "explanation_text": explanation.explain_text(),
            "evidence": [
                {
                    "turn": q["turn_number"],
                    "speaker": q["speaker"],
                    "text": q["text"],
                    "signal": q["signal"],
                    "confidence": round(q["confidence"], 2)
                }
                for q in explanation.evidence_quotes
            ],
            "alternatives": [
                {
                    "signals": alt.signals,
                    "confidence": alt.confidence
                }
                for alt in explanation.alternative_chains
            ]
        }
