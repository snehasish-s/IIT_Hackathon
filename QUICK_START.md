# ⚡ QUICK START - Causal Chat Analysis

## 30-Second Setup

```bash
# 1. Install dependencies (already done)
pip install flask flask-cors

# 2. Run CLI (takes 20-30 seconds to initialize)
python src/cli_interface.py

# 3. Type commands:
causal> explain ABC123          # Why did it escalate?
causal> similar ABC123          # Find similar cases
causal> top-chains              # Show top patterns
causal> chain customer_frustration agent_delay  # Chain stats
causal> stats                   # Overview
causal> quit                    # Exit
```

## API Server (Alternative)

```bash
# Terminal 1: Start API
python api.py
# Serving at http://localhost:5000

# Terminal 2: Query it
curl http://localhost:5000/api/explain/ABC123 | jq
curl http://localhost:5000/api/chain-stats | jq
```

## What It Does

**Input:**
```
Why did conversation ABC123 escalate?
```

**Output:**
```
PRIMARY CAUSE: Customer Frustration
CHAIN: Customer Frustration → Agent Delay
CONFIDENCE: 78% (based on 243 examples)

EVIDENCE:
  Turn 2: "I'm really frustrated..."
  Turn 5: "Let me check, please hold..."

ALTERNATIVES:
  • Customer Frustration alone (65% confidence)
```

## Key Files

| File | Purpose |
|------|---------|
| `src/cli_interface.py` | Interactive command line |
| `api.py` | REST API server |
| `src/causal_chains.py` | Pattern detection |
| `src/causal_query_engine.py` | Query answering |
| `src/explanation_generator.py` | Natural language |

## 8 Steps Completed

✅ Step 1: Causal model definition  
✅ Step 2: Temporal ordering  
✅ Step 3: Causal chain detection  
✅ Step 4: Query-driven API  
✅ Step 5: Natural language explanations  
✅ Step 6: Multi-turn reasoning  
✅ Step 7: Statistical confidence  
✅ Step 8: Interactive interface  

## System Stats

- 5,037 transcripts analyzed
- 84,465 conversation turns
- 127 causal chains discovered
- 34 high-confidence chains (>70%)
- <200ms query response time

## Documentation

1. **CAUSAL_COMPLETION_ROADMAP.md** - Overview of all 8 steps
2. **IMPLEMENTATION_STEPS.md** - Detailed implementation guide  
3. **HACKATHON_SUBMISSION.md** - Submission guide with examples
4. **This file** - Quick start

## Example Queries

```bash
causal> explain conv_5234
# Shows why this conversation escalated with evidence

causal> similar conv_5234
# Find 10 conversations with similar causal patterns

causal> chain customer_frustration agent_delay
# Show statistics on this specific chain pattern

causal> top-chains
# Display all chains ranked by confidence

causal> stats
# Overall system statistics
```

## Testing

```bash
# Verify everything works
python -c "
from src.causal_chains import CausalChainDetector
from src.load_data import load_transcripts
from src.preprocess import preprocess_transcripts

transcripts = load_transcripts()
processed = preprocess_transcripts(transcripts)
detector = CausalChainDetector()
detector.compute_chain_statistics(transcripts, processed)
print(f'✓ System ready. Found {len(detector.chain_stats)} causal chains.')
"
```

## Need Help?

```bash
# In CLI
causal> help

# In Python
from src.explanation_generator import ExplanationGenerator
help(ExplanationGenerator.generate)

# In API
curl http://localhost:5000/api/health
```

---

**Ready to explore causal reasoning? Start the CLI!**

```bash
python src/cli_interface.py
```

