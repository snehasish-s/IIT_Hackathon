"""
Causal Model - Core data structures for causal reasoning
Bridges the gap between signal detection and causal explanation
"""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from enum import Enum


class Outcome(Enum):
    """Possible transcript outcomes"""
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"


@dataclass
class Signal:
    """A single detected signal with temporal and confidence metadata"""
    type: str  # "customer_frustration", "agent_delay", "agent_denial"
    turn_number: int  # When in conversation?
    speaker: str  # "customer" or "agent"
    confidence: float  # 0.0-1.0, how sure are we?
    text: str  # Direct quote from the turn
    
    def __repr__(self):
        return f"Signal({self.type} @turn{self.turn_number}, conf={self.confidence:.2f})"


@dataclass
class CausalChain:
    """A sequence of signals that leads to an outcome"""
    signals: List[str]  # ["customer_frustration", "agent_delay", ...]
    outcome: Outcome
    confidence: float  # P(outcome | signals)
    evidence_count: int = 0  # How many transcripts show this pattern?
    escalation_count: int = 0  # Of those, how many escalated?
    
    def chain_str(self) -> str:
        """Human-readable chain representation"""
        return " → ".join(self.signals) + f" → {self.outcome.value}"
    
    def __repr__(self):
        return f"CausalChain({self.chain_str()}, conf={self.confidence:.2f})"


@dataclass
class CausalExplanation:
    """A human-readable explanation of why an outcome occurred"""
    transcript_id: str
    outcome: Outcome
    causal_chain: CausalChain
    
    # Evidence from the actual transcript
    evidence: List[Signal] = field(default_factory=list)
    evidence_quotes: List[Dict] = field(default_factory=list)  # turn, speaker, text
    
    # Confidence and alternatives
    confidence: float = 0.0
    alternative_chains: List[CausalChain] = field(default_factory=list)
    
    def primary_cause(self) -> str:
        """The first signal in the chain"""
        return self.causal_chain.signals[0] if self.causal_chain.signals else "unknown"
    
    def secondary_causes(self) -> List[str]:
        """All signals after the first"""
        return self.causal_chain.signals[1:] if len(self.causal_chain.signals) > 1 else []
    
    def explain_text(self) -> str:
        """Generate a simple text explanation"""
        parts = []
        
        # Main cause
        primary = self.primary_cause().replace("_", " ").title()
        parts.append(f"The primary cause: {primary}")
        
        # Chain
        if self.causal_chain.signals:
            chain_text = " → ".join([s.replace("_", " ").title() 
                                    for s in self.causal_chain.signals])
            parts.append(f"Pattern: {chain_text}")
        
        # Confidence
        parts.append(f"Confidence: {self.confidence:.0%}")
        
        # Evidence count
        if self.evidence_quotes:
            parts.append(f"Evidence: {len(self.evidence_quotes)} supporting quotes")
        
        return "\n".join(parts)


@dataclass
class TemporalSignalSequence:
    """Ordered sequence of signals within a single transcript"""
    transcript_id: str
    signals: List[Signal] = field(default_factory=list)  # Ordered by turn_number
    outcome: Outcome = Outcome.UNRESOLVED
    
    def get_chains_up_to_length(self, max_length: int = 3) -> List[List[str]]:
        """
        Extract all possible signal chains up to max_length
        
        If transcript has signals at turns [3, 5, 8]:
        Returns: [
            [sig@3],
            [sig@3, sig@5],
            [sig@3, sig@5, sig@8],
            [sig@5],
            [sig@5, sig@8],
            [sig@8]
        ]
        """
        chains = []
        signal_types = [s.type for s in self.signals]
        
        for start_idx in range(len(signal_types)):
            for end_idx in range(start_idx + 1, min(start_idx + max_length + 1, len(signal_types) + 1)):
                chain = signal_types[start_idx:end_idx]
                chains.append(chain)
        
        return chains
    
    def add_signal(self, signal: Signal):
        """Add signal and maintain temporal order"""
        self.signals.append(signal)
        self.signals.sort(key=lambda s: s.turn_number)
    
    def __repr__(self):
        if not self.signals:
            return f"TemporalSignalSequence({self.transcript_id}, empty)"
        return f"TemporalSignalSequence({self.transcript_id}, {len(self.signals)} signals, {self.outcome.value})"


# Configuration: What causal chains are most important?
DEFAULT_CAUSAL_PATTERNS = {
    ("customer_frustration",): 0.35,  # Base rate for single signal
    ("agent_delay",): 0.20,
    ("agent_denial",): 0.25,
    ("customer_frustration", "agent_delay"): 0.65,  # Two-signal chains
    ("customer_frustration", "agent_denial"): 0.68,
    ("agent_delay", "customer_frustration"): 0.60,
    ("customer_frustration", "agent_delay", "agent_denial"): 0.82,  # Three-signal chain
}
