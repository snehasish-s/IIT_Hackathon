"""
Explanation Generator - Convert causal chains into natural language
No LLMs needed - uses templates and direct evidence quotes
"""

from typing import List, Dict, Tuple
from src.causal_model import CausalExplanation, CausalChain, Signal


class ExplanationGenerator:
    """Generate human-readable explanations from causal chains and evidence"""
    
    # Templates for common causal patterns
    TEMPLATES = {
        # Single signal
        ("customer_frustration",): [
            "The customer expressed frustration early in the conversation.",
            "Customer frustration was the primary factor in this escalation.",
            "The customer showed signs of being frustrated.",
        ],
        ("agent_delay",): [
            "The agent's delayed response was the main issue.",
            "Slow response times from the agent contributed to the outcome.",
            "The agent took time to respond, which affected the conversation.",
        ],
        ("agent_denial",): [
            "The agent denied the customer's request.",
            "The customer faced a policy denial from the agent.",
            "When the agent denied the request, the outcome shifted.",
        ],
        
        # Two-signal chains
        ("customer_frustration", "agent_delay"): [
            "The customer was frustrated, and when the agent delayed responding, "
            "the situation escalated.",
            "First, the customer showed frustration. Then, the agent's slow response "
            "made it worse.",
            "Customer frustration combined with agent delays led to escalation.",
        ],
        ("customer_frustration", "agent_denial"): [
            "The customer was frustrated to begin with. When the agent then denied "
            "their request, escalation occurred.",
            "Frustration plus a policy denial from the agent triggered the escalation.",
            "The combination of frustation and denial drove this outcome.",
        ],
        ("agent_delay", "customer_frustration"): [
            "The agent's initial delay caused customer frustration, leading to escalation.",
            "When the agent delayed, the customer became frustrated, causing escalation.",
            "Slow responses led to customer frustration and escalation.",
        ],
        
        # Three-signal chains
        ("customer_frustration", "agent_delay", "agent_denial"): [
            "This was a critical sequence: customer frustration → agent delay → agent denial. "
            "At each stage, the situation deteriorated.",
            "Three factors compounded: the customer's frustration, the agent's delay, "
            "and then a denial of service. This led to escalation.",
            "The customer was already frustrated, the agent delayed, and then denied the request. "
            "This escalated the situation.",
        ],
    }
    
    @classmethod
    def generate(cls, explanation: CausalExplanation) -> str:
        """
        Generate a natural language explanation from a CausalExplanation object
        
        Args:
            explanation: CausalExplanation with chain and evidence
        
        Returns:
            Readable English explanation
        """
        # Get the chain signature
        chain_signature = tuple(explanation.causal_chain.signals)
        
        # Select a template if available
        if chain_signature in cls.TEMPLATES:
            # Pick the first template (could randomize for variety)
            template_text = cls.TEMPLATES[chain_signature][0]
        else:
            # Fallback for unknown chains
            template_text = cls._generate_generic_explanation(explanation)
        
        # Build full explanation with confidence and evidence
        parts = [template_text]
        
        # Add confidence if notable
        confidence = explanation.confidence
        if confidence >= 0.7:
            confidence_text = "This pattern is quite common in our data."
        elif confidence >= 0.5:
            confidence_text = "This pattern appears in about half of similar cases."
        elif confidence >= 0.3:
            confidence_text = "This pattern appears in some similar cases."
        else:
            confidence_text = "This pattern is less common, but fits this case."
        
        parts.append(confidence_text)
        
        # Add evidence quotes
        if explanation.evidence_quotes:
            parts.append("\n📋 Supporting evidence:")
            for quote in explanation.evidence_quotes[:3]:  # Show top 3
                turn_num = quote["turn_number"]
                speaker = quote["speaker"].title()
                text_snippet = quote["text"][:80]
                if len(quote["text"]) > 80:
                    text_snippet += "..."
                parts.append(f"  Turn {turn_num} ({speaker}): \"{text_snippet}\"")
        
        # Add alternatives if they exist
        if explanation.alternative_chains:
            parts.append("\n💭 Alternative explanations:")
            for alt in explanation.alternative_chains[:2]:
                alt_chain = " → ".join(alt.signals)
                parts.append(f"  • {alt_chain}")
        
        return "\n".join(parts)
    
    @classmethod
    def _generate_generic_explanation(cls, explanation: CausalExplanation) -> str:
        """Generate explanation for an unknown chain pattern"""
        chain = explanation.causal_chain
        signal_names = [s.replace("_", " ").title() for s in chain.signals]
        chain_string = " → ".join(signal_names)
        
        return (f"This escalation followed the pattern: {chain_string}. "
                f"This specific sequence occurred with {explanation.confidence:.0%} confidence.")
    
    @classmethod
    def generate_short(cls, explanation: CausalExplanation) -> str:
        """
        Generate a one-line summary
        
        Example: "Customer frustration + Agent delay → Escalation (78% confidence)"
        """
        chain_signals = " + ".join([s.replace("_", " ").title() 
                                   for s in explanation.causal_chain.signals])
        return (f"{chain_signals} → "
                f"{explanation.outcome.value.title()} "
                f"({explanation.confidence:.0%} confidence)")
    
    @classmethod
    def generate_detailed_report(cls, explanation: CausalExplanation) -> str:
        """
        Generate a detailed multi-paragraph report
        """
        parts = []
        
        # Header
        parts.append(f"🎯 CAUSAL ANALYSIS REPORT")
        parts.append(f"Transcript ID: {explanation.transcript_id}")
        parts.append(f"Outcome: {explanation.outcome.value.upper()}")
        parts.append(f"Analysis Confidence: {explanation.confidence:.1%}")
        parts.append("")
        
        # Executive Summary
        parts.append("📊 EXECUTIVE SUMMARY")
        parts.append(cls.generate(explanation))
        parts.append("")
        
        # Chain Details
        parts.append("🔗 CAUSAL CHAIN")
        parts.append(f"Primary Cause: {explanation.primary_cause().replace('_', ' ').title()}")
        if explanation.secondary_causes():
            parts.append(f"Contributing Factors: {', '.join([s.replace('_', ' ').title() for s in explanation.secondary_causes()])}")
        parts.append("")
        
        # Evidence
        parts.append("📝 EVIDENCE (Direct Quotes)")
        if explanation.evidence_quotes:
            for i, quote in enumerate(explanation.evidence_quotes, 1):
                parts.append(f"\n  {i}. Turn {quote['turn_number']} ({quote['speaker'].upper()})")
                parts.append(f"     \"{quote['text']}\"")
                parts.append(f"     → Signals: {quote['signal']} (confidence: {quote['confidence']:.0%})")
        else:
            parts.append("  No direct evidence available.")
        parts.append("")
        
        # Statistical Context
        parts.append("📈 STATISTICAL CONTEXT")
        if explanation.causal_chain.evidence_count > 0:
            parts.append(f"  This chain pattern occurs in {explanation.causal_chain.evidence_count} transcripts.")
            parts.append(f"  In {explanation.causal_chain.escalation_count} of those, the conversation escalated.")
        parts.append("")
        
        # Alternatives
        if explanation.alternative_chains:
            parts.append("💡 ALTERNATIVE EXPLANATIONS")
            for alt in explanation.alternative_chains:
                alt_signals = " → ".join(alt.signals)
                parts.append(f"  • {alt_signals}")
        
        return "\n".join(parts)
    
    @classmethod
    def compare_transcripts(cls, exp1: CausalExplanation, 
                           exp2: CausalExplanation) -> str:
        """
        Compare explanations for two transcripts (for multi-turn analysis)
        
        Returns analysis of similarities/differences
        """
        parts = []
        
        parts.append("📊 COMPARISON ANALYSIS")
        parts.append(f"Transcript A: {exp1.transcript_id} → {exp1.outcome.value}")
        parts.append(f"Transcript B: {exp2.transcript_id} → {exp2.outcome.value}")
        parts.append("")
        
        # Chain comparison
        chain_a = tuple(exp1.causal_chain.signals)
        chain_b = tuple(exp2.causal_chain.signals)
        
        if chain_a == chain_b:
            parts.append("✓ Both transcripts follow the SAME causal pattern:")
            parts.append(f"  {' → '.join(chain_a)}")
        else:
            parts.append("Different causal patterns:")
            parts.append(f"  A: {' → '.join(chain_a)}")
            parts.append(f"  B: {' → '.join(chain_b)}")
            
            # Find common signals
            signals_a = set(exp1.causal_chain.signals)
            signals_b = set(exp2.causal_chain.signals)
            common = signals_a & signals_b
            if common:
                parts.append(f"  Common factors: {', '.join(common)}")
        
        parts.append("")
        parts.append(f"Confidence A: {exp1.confidence:.0%}")
        parts.append(f"Confidence B: {exp2.confidence:.0%}")
        
        return "\n".join(parts)


# Example usage and testing
def demo_generate():
    """Demo: show what generated explanations look like"""
    from src.causal_model import CausalChain, CausalExplanation, Outcome, Signal
    
    # Create sample explanation
    chain = CausalChain(
        signals=["customer_frustration", "agent_delay"],
        outcome=Outcome.ESCALATED,
        confidence=0.78,
        evidence_count=243,
        escalation_count=158
    )
    
    explanation = CausalExplanation(
        transcript_id="DEMO_001",
        outcome=Outcome.ESCALATED,
        causal_chain=chain,
        confidence=0.78,
        evidence_quotes=[
            {
                "turn_number": 2,
                "speaker": "customer",
                "text": "I'm really frustrated with this situation",
                "signal": "customer_frustration",
                "confidence": 0.95
            },
            {
                "turn_number": 5,
                "speaker": "agent",
                "text": "Let me check on that for you, please hold a moment",
                "signal": "agent_delay",
                "confidence": 0.85
            }
        ]
    )
    
    print("SHORT EXPLANATION:")
    print(ExplanationGenerator.generate_short(explanation))
    print("\n" + "="*70 + "\n")
    
    print("FULL EXPLANATION:")
    print(ExplanationGenerator.generate(explanation))
    print("\n" + "="*70 + "\n")
    
    print("DETAILED REPORT:")
    print(ExplanationGenerator.generate_detailed_report(explanation))


if __name__ == "__main__":
    demo_generate()
