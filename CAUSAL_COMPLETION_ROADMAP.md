# 🎯 Causal Chat Analysis - Completion Roadmap

## Vision
Transform keyword-based signal detection into **explicit causal reasoning** with temporal ordering, multi-turn context awareness, and query-driven natural language explanations.

---

## Mandatory Implementation Steps

### Step 1: Define Operational Causal Explanations

**Goal:** Establish what "causality" means in this domain - moving from correlation (signals present) to causation (signal A causes outcome B).

**Files to create/modify:**
- Create: `src/causal_model.py`
- Modify: `src/config.py`

**Concept:** 
In this system, causality is defined as:
- **Precondition**: Signal must occur BEFORE outcome becomes likely
- **Temporal Sequence**: Customer frustration → Agent delay → Further frustration → Escalation
- **Signal Strength**: How often does this signal sequence lead to escalation?
- **Alternative Explanation**: Rule out other signals that might explain the outcome

**Implementation sketch:**
```python
class CausalChain:
    """Represents a sequence of signals leading to an outcome"""
    def __init__(self, signals: List[str], outcome: str, confidence: float):
        self.signals = signals  # ["customer_frustration", "agent_delay", ...]
        self.outcome = outcome  # "escalated"
        self.confidence = confidence  # P(escalated | signals)
        self.evidence_count = 0  # How many transcripts support this
        
class CausalExplanation:
    """A human-readable explanation of why an outcome occurred"""
    def __init__(self, chain: CausalChain, transcript_id: str):
        self.primary_cause = chain.signals[0]
        self.secondary_causes = chain.signals[1:]
        self.confidence = chain.confidence
        self.evidence_quotes = []  # Direct text from turns
```

**Verification:**
- Can you instantiate a `CausalChain` with signals `["customer_frustration", "agent_delay"]` → outcome `"escalated"` with confidence `0.75`?
- Can you explain in natural language: "Frustration leads to escalation 75% of the time"?

---

### Step 2: Add Temporal Ordering to Signal Extraction

**Goal:** Signals must remember WHEN they occurred in the conversation, enabling temporal causality analysis.

**Files to create/modify:**
- Modify: `src/signal_extraction.py` 
- Modify: `src/preprocess.py`

**Concept:**
Current system: "Turn 5 has frustration signal"
Enhanced system: "Turn 5 has frustration signal (timestamp/position=5), followed by Turn 8 agent delay (timestamp/position=8)"

This allows: "Did customer frustration PRECEDE agent's delay response?"

**Implementation sketch:**
```python
def extract_signals_temporal(turn: dict, turn_number: int, 
                            transcript_id: str) -> dict:
    """
    Extract signals WITH temporal metadata
    
    Returns:
    {
        "signals": ["customer_frustration"],
        "turn_number": 5,
        "position_in_transcript": 5,  # ordinal position
        "speaker": "customer",
        "timestamp": None,  # extended later if real timestamps exist
        "text": "...",
        "signal_confidence": {"customer_frustration": 0.85}
    }
    """
    ...

def build_temporal_signal_sequence(transcript_id: str, 
                                  processed_turns: List[dict]) -> List[dict]:
    """
    Build ordered list of signals for a transcript
    
    Returns:
    [
        {"turn": 3, "signal": "customer_frustration", "confidence": 0.9},
        {"turn": 5, "signal": "agent_delay", "confidence": 0.7},
        {"turn": 8, "signal": "customer_frustration", "confidence": 0.95}
    ]
    """
    ...
```

**Verification:**
- Load a transcript, extract signals with turn numbers
- Print timeline: "Turn 2: customer_frustration → Turn 5: agent_delay → Turn 8: escalation detected"
- Verify ordering is chronological

---

### Step 3: Build Causal Chains (Signal → Signal → Outcome)

**Goal:** Detect patterns where signal sequences consistently lead to escalation.

**Files to create/modify:**
- Create: `src/causal_chains.py`
- Modify: `src/config.py` (add chain patterns)

**Concept:**
Instead of: "Frustration causes 20% of escalations"
Build: "Customer frustration → Agent delay → Customer further escalates" (occurs in 65% of escalation cases)

**Implementation sketch:**
```python
class CausalChainDetector:
    """Find recurring causal sequences"""
    
    def find_chains(self, transcript: dict, max_chain_length: int = 3) -> List[CausalChain]:
        """
        Extract all possible signal chains from a transcript
        
        For transcript with signals at turns [3, 5, 8, 12]:
        Returns chains:
        - [sig@3] → outcome
        - [sig@3, sig@5] → outcome
        - [sig@3, sig@5, sig@8] → outcome
        - [sig@5] → outcome
        - etc.
        """
        ...
    
    def compute_chain_statistics(self, all_transcripts: List[dict]) -> Dict:
        """
        Compute P(escalated | chain) for each common chain
        
        Returns:
        {
            ("customer_frustration", "agent_delay"): {
                "occurrences": 243,
                "escalated": 158,
                "confidence": 0.65,
                "examples": [transcript_ids...]
            },
            ...
        }
        """
        ...
```

**Verification:**
- Run on sample data: "customer_frustration → agent_delay" appears in N transcripts
- X of those resulted in escalation
- Report: "This chain has 80% confidence in leading to escalation"

---

### Step 4: Implement Query-Driven API ("Why did X escalate?")

**Goal:** Accept a transcript ID and return causal explanation.

**Files to create/modify:**
- Create: `src/causal_query_engine.py`
- Modify: `api.py` (add new endpoint)

**Concept:**
The system must answer: **"Why did transcript ABC123 escalate?"**

Not: "Generally, frustration causes escalation"
But: "In THIS transcript, the escalation happened because: (1) Customer showed frustration at turn 2, (2) Agent delayed response at turn 5, (3) Customer escalated demand at turn 8."

**Implementation sketch:**
```python
class CausalQueryEngine:
    def __init__(self, chain_stats: Dict, transcripts: Dict):
        self.chain_stats = chain_stats  # Pre-computed from Step 3
        self.transcripts = transcripts
    
    def explain_escalation(self, transcript_id: str) -> CausalExplanation:
        """
        Main query function: "Why did this escalate?"
        
        Algorithm:
        1. Get transcript and its outcome (escalated or resolved)
        2. Extract temporal signal sequence
        3. Find longest matching chain from chain_stats
        4. Rank by confidence: which chain best explains this outcome?
        5. Return explanation with evidence quotes
        
        Returns:
        {
            "transcript_id": "ABC123",
            "outcome": "escalated",
            "primary_cause": "customer_frustration",
            "causal_chain": ["customer_frustration", "agent_delay"],
            "confidence": 0.78,
            "explanation": "Customer showed frustration (turn 2), 
                           agent delayed (turn 5), customer escalated (turn 8)",
            "evidence": [
                {"turn": 2, "speaker": "customer", "text": "..."},
                {"turn": 5, "speaker": "agent", "text": "..."},
                {"turn": 8, "speaker": "customer", "text": "..."}
            ]
        }
        """
        ...
```

**New API endpoint:**
```python
@app.route('/api/explain/<transcript_id>', methods=['GET'])
def explain_transcript(transcript_id: str):
    """
    Query: Why did this transcript escalate/resolve?
    Returns causal explanation with evidence
    """
    ...
```

**Verification:**
- Call `/api/explain/ABC123`
- Receive JSON with explanation, chain, and evidence quotes
- Can read the explanation and understand why escalation happened

---

### Step 5: Add Evidence-Backed Natural Language Explanations

**Goal:** Convert causal chains into human-readable text.

**Files to create/modify:**
- Create: `src/explanation_generator.py`
- Modify: `src/causal_query_engine.py`

**Concept:**
Transform structured data into natural language:
- Input: `{"chain": ["customer_frustration", "agent_delay"], "confidence": 0.78}`
- Output: "The customer expressed frustration at turn 2. The agent then took longer to respond (turn 5). As a result, the conversation escalated."

Use templates + variable substitution, no LLMs needed.

**Implementation sketch:**
```python
class ExplanationGenerator:
    """Build human-readable explanations from causal chains"""
    
    TEMPLATES = {
        ("customer_frustration",): 
            "The customer expressed frustration, which often leads to escalation.",
        
        ("customer_frustration", "agent_delay"):
            "The customer was frustrated (turn {turn1}), and when the agent delayed "
            "their response (turn {turn2}), the frustration intensified.",
        
        ("customer_frustration", "agent_delay", "agent_denial"):
            "The customer was frustrated, the agent delayed, then denied the customer's "
            "request, leading to escalation.",
    }
    
    def generate(self, chain: CausalChain, evidence: List[dict]) -> str:
        """
        Generate natural language explanation
        
        chain: ("customer_frustration", "agent_delay")
        evidence: [{"turn": 2, "text": "..."}, {"turn": 5, "text": "..."}]
        
        Returns: "The customer was frustrated (turn 2)..."
        """
        if tuple(chain.signals) in self.TEMPLATES:
            template = self.TEMPLATES[tuple(chain.signals)]
            return template.format(turn1=evidence[0]['turn'], turn2=evidence[1]['turn'], ...)
        else:
            # Fallback: generic explanation
            return f"This escalation followed the pattern: {' → '.join(chain.signals)}"
```

**Verification:**
- Generate explanation for a known escalation case
- Read it aloud - does it make sense?
- Does it cite specific turns from the transcript?

---

### Step 6: Maintain Context Across Follow-Up Queries (Multi-Turn Reasoning)

**Goal:** Support conversation-like interaction: "Why did it escalate?" → "What was the agent doing during turn 5?" → "Did other similar cases escalate?"

**Files to create/modify:**
- Create: `src/query_context.py`
- Modify: `api.py` (add session management)

**Concept:**
Current: Each query is stateless
Enhanced: Maintain query history so follow-ups can reference previous answers

```
Query 1: "Why did ABC123 escalate?"
Response: "Due to frustration + delay"

Query 2: "What was the agent doing at turn 5?"  
Response: "The agent said 'please hold'..." [uses context from Query 1]

Query 3: "Do similar patterns appear in other transcripts?"
Response: "Yes, 158 other transcripts show the same pattern"
```

**Implementation sketch:**
```python
class QueryContext:
    """Maintain session state for multi-turn reasoning"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.current_transcript_id = None
        self.query_history = []  # Previous queries
        self.current_explanation = None  # Last causal explanation
    
    def add_query(self, question: str, answer: dict):
        """Record query + response"""
        self.query_history.append({"q": question, "a": answer})
    
    def get_context(self) -> dict:
        """Return current context for next query"""
        return {
            "current_transcript": self.current_transcript_id,
            "last_explanation": self.current_explanation,
            "history": self.query_history[-3:]  # Last 3 queries
        }

# API modification:
@app.route('/api/query', methods=['POST'])
def query_engine(session_id: str, question: str):
    """
    Multi-turn reasoning endpoint
    
    question: "Why did ABC123 escalate?"
    or: "What happened at turn 5?" (uses context from previous query)
    """
    context = query_sessions[session_id]
    # Parse question type
    # Use context to enhance answer
    # Return response + update context
    ...
```

**Verification:**
- Create a session
- Query 1: "Why did ABC123 escalate?" → Returns explanation
- Query 2: "Tell me about turn 5" → Should reference turn from explanation
- Query 3: "Are there similar cases?" → Should reference ABC123 from earlier context

---

### Step 7: Add Minimal Statistical Confidence to Causal Claims

**Goal:** Quantify uncertainty: "This chain has 78% confidence, based on 243 examples."

**Files to create/modify:**
- Create: `src/causal_confidence.py`
- Modify: `src/causal_chains.py`

**Concept:**
Every causal claim needs a confidence score:
- High confidence: "Frustration → escalation (87%, 412 cases)"
- Low confidence: "Agent typo → escalation (12%, 3 cases)"

Use Bayesian thinking: P(escalated | chain) = escalations with chain / total with chain

**Implementation sketch:**
```python
class ConfidenceCalculator:
    """Compute confidence scores for causal chains"""
    
    def calculate_chain_confidence(self, chain: Tuple[str, ...], 
                                  transcripts: List[dict]) -> dict:
        """
        Count escalations with this chain pattern
        
        Returns:
        {
            "chain": ("customer_frustration", "agent_delay"),
            "total_occurrences": 243,
            "escalated_count": 158,
            "confidence": 0.65,  # 158/243
            "confidence_interval": (0.59, 0.71),  # 95% CI
            "min_sample_warning": False
        }
        """
        escalations = sum(1 for t in transcripts 
                         if self._matches_chain(t, chain) and t.outcome == 'escalated')
        total = sum(1 for t in transcripts if self._matches_chain(t, chain))
        
        confidence = escalations / total if total > 0 else 0
        ci = self._wilson_ci(escalations, total)  # 95% confidence interval
        
        return {
            "confidence": confidence,
            "confidence_interval": ci,
            "evidence_count": total,
            "escalation_count": escalations
        }
```

**Verification:**
- For a chain with 10 examples, 7 escalated: confidence = 0.70
- For a chain with 500 examples, 350 escalated: confidence = 0.70
- Report different uncertainty levels appropriately

---

### Step 8: Expose Results via Simple Interactive Interface (CLI + API)

**Goal:** Let users query the system easily. No web browser required, but API-ready.

**Files to create/modify:**
- Create: `src/cli_interface.py`
- Modify: `api.py` (add causal endpoints)

**Concept:**
Two interfaces:
1. **CLI**: `python cli_interface.py query "Why did ABC123 escalate?"`
2. **REST API**: GET `/api/explain/ABC123`

Both return structured causal explanations.

**Implementation sketch:**
```python
# cli_interface.py
class CausalCLI:
    """Interactive command-line interface"""
    
    def __init__(self):
        self.engine = CausalQueryEngine(...)
        self.context = QueryContext("cli_session")
    
    def run(self):
        """Interactive REPL"""
        while True:
            question = input("causal> ").strip()
            if not question:
                continue
            
            # Parse question type
            if question.startswith("explain "):
                transcript_id = question.split()[1]
                response = self.engine.explain_escalation(transcript_id)
            elif question.startswith("chain "):
                # Analyze a chain
                ...
            elif question == "help":
                print("Commands: explain <id>, chain <sig1> <sig2>, stats, quit")
            elif question == "quit":
                break
            
            self._print_response(response)
            self.context.add_query(question, response)

# api.py additions
@app.route('/api/explain/<transcript_id>', methods=['GET'])
def explain_transcript(transcript_id):
    """Why did this transcript escalate/resolve?"""
    ...

@app.route('/api/chain-stats', methods=['GET'])
def get_chain_stats():
    """Statistics on all detected causal chains"""
    ...

@app.route('/api/similar-cases/<transcript_id>', methods=['GET'])
def find_similar_cases(transcript_id):
    """Find transcripts with similar causal patterns"""
    ...
```

**Verification:**
- Run CLI: `python cli_interface.py`
- Type: `explain ABC123` → Get explanation
- Type: `chain customer_frustration agent_delay` → Get stats on this chain
- Type: `quit` → Exit cleanly

---

## Implementation Summary Table

| Step | Title | Key Files | Complexity | Dependencies |
|------|-------|-----------|-----------|--------------|
| 1 | Define Operational Causal Explanations | `causal_model.py`, `config.py` | Low | None |
| 2 | Add Temporal Ordering | `signal_extraction.py`, `preprocess.py` | Low | Step 1 |
| 3 | Build Causal Chains | `causal_chains.py`, `config.py` | Medium | Steps 1-2 |
| 4 | Query-Driven API | `causal_query_engine.py`, `api.py` | Medium | Steps 1-3 |
| 5 | Natural Language Explanations | `explanation_generator.py` | Low | Steps 1-4 |
| 6 | Multi-Turn Reasoning | `query_context.py`, `api.py` | Medium | Steps 1-4 |
| 7 | Statistical Confidence | `causal_confidence.py` | Low | Steps 1-3 |
| 8 | Interactive Interface | `cli_interface.py`, `api.py` | Low | Steps 1-7 |

---

## Architecture After Completion

```
User Query
    ↓
[CLI or REST API]
    ↓
[Query Parser] → "Why did ABC123 escalate?"
    ↓
[Query Context] → Retrieve relevant transcript + history
    ↓
[Signal Extractor] → Get temporal signal sequence
    ↓
[Causal Chain Matcher] → Find matching patterns
    ↓
[Confidence Calculator] → Compute P(escalated | chain)
    ↓
[Explanation Generator] → Build natural language response
    ↓
[Response Formatter] → JSON (API) or Text (CLI)
    ↓
[User sees explanation + evidence + confidence]
```

---

## Verification Checklist

- [ ] Step 1: Can instantiate CausalChain and CausalExplanation
- [ ] Step 2: Signal extraction includes turn_number and ordered sequences
- [ ] Step 3: Causal chains computed with statistics and confidence > 0
- [ ] Step 4: `/api/explain/<id>` endpoint returns structured explanation
- [ ] Step 5: Explanations are readable English, not code
- [ ] Step 6: Multi-turn queries work in CLI and maintain context
- [ ] Step 7: Confidence intervals computed and shown in responses
- [ ] Step 8: Both CLI and REST API work, handle edge cases

---

## Hackathon Submission Readiness

After completing all 8 steps, your system can:

✅ **Explain why any conversation escalated** (Query-driven)  
✅ **Show causal chains in temporal order** (Temporal logic)  
✅ **Cite evidence from the actual transcript** (Traceability)  
✅ **Quantify confidence in explanations** (Statistical rigor)  
✅ **Support follow-up questions** (Interactive reasoning)  
✅ **Answer in plain English** (Interpretability)  

**Ready for submission** when all steps have green checkmarks in verification.
