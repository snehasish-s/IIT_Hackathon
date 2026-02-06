"""
Signal Extraction Module
Extracts signals (frustration, delays, denials) from conversation turns
"""

from src.config import SIGNAL_CONFIG

# Legacy keyword lists (kept for backward compatibility)
FRUSTRATION_KEYWORDS = SIGNAL_CONFIG["frustration"]["keywords"]
AGENT_DELAY_KEYWORDS = SIGNAL_CONFIG["agent_delay"]["keywords"]
AGENT_DENIAL_KEYWORDS = SIGNAL_CONFIG["agent_denial"]["keywords"]


def extract_signals(turn):
    """
    Extract signals from a single conversation turn.
    
    Args:
        turn (dict): A turn with 'speaker' and 'text' keys
    
    Returns:
        list: List of signal types detected in the turn
    """
    text = turn["text"].lower()
    signals = []

    # Customer frustration
    if turn["speaker"].lower() == "customer":
        if any(word in text for word in FRUSTRATION_KEYWORDS):
            signals.append("customer_frustration")

    # Agent behavior
    if turn["speaker"].lower() == "agent":

        # Agent delay
        if any(word in text for word in AGENT_DELAY_KEYWORDS):
            signals.append("agent_delay")

        # Agent denial (filtered)
        if (
            any(word in text for word in AGENT_DENIAL_KEYWORDS)
            and "sorry" in text
            and len(text.split()) > 5
        ):
            signals.append("agent_denial")

    return signals


def extract_signals_advanced(turn, signal_types=None):
    """
    Extract signals using configuration-based approach.
    
    Args:
        turn (dict): A turn with 'speaker' and 'text' keys
        signal_types (list): List of signal types to check (default: all)
    
    Returns:
        list: List of detected signals
    """
    if signal_types is None:
        signal_types = list(SIGNAL_CONFIG.keys())
    
    text = turn["text"].lower()
    signals = []
    speaker = turn["speaker"].lower()
    
    for signal_type in signal_types:
        if signal_type not in SIGNAL_CONFIG:
            continue
        
        config = SIGNAL_CONFIG[signal_type]
        keywords = config["keywords"]
        
        # Check speaker relevance
        if "frustration" in signal_type and speaker != "customer":
            continue
        if "agent" in signal_type and speaker != "agent":
            continue
        
        # Check keywords
        if any(keyword in text for keyword in keywords):
            # Apply additional filters if specified
            if config.get("must_contain"):
                if not all(keyword in text for keyword in config["must_contain"]):
                    continue
            
            if config.get("min_word_count"):
                if len(text.split()) < config["min_word_count"]:
                    continue
            
            signals.append(signal_type)
    
    return signals


def get_signal_confidence(turn, signal_type):
    """
    Calculate confidence score for a specific signal.
    
    Args:
        turn (dict): A turn with 'speaker' and 'text' keys
        signal_type (str): The signal type to check
    
    Returns:
        float: Confidence score between 0 and 1
    """
    if signal_type not in SIGNAL_CONFIG:
        return 0.0
    
    text = turn["text"].lower()
    config = SIGNAL_CONFIG[signal_type]
    keywords = config["keywords"]
    
    # Count matching keywords
    matches = sum(1 for keyword in keywords if keyword in text)
    
    # Calculate confidence
    confidence = min(matches / max(len(keywords), 1), 1.0)
    
    return confidence


def extract_all_signals(transcript):
    """
    Extract signals from all turns in a transcript.
    
    Args:
        transcript (dict): A transcript with a 'conversation' key
    
    Returns:
        dict: Mapping of turn numbers to detected signals
    """
    signals_by_turn = {}
    
    for idx, turn in enumerate(transcript.get("conversation", []), 1):
        signals = extract_signals(turn)
        if signals:
            signals_by_turn[idx] = signals
    
    return signals_by_turn


def get_dominant_signal(signals_list):
    """
    Get the most significant signal from a list.
    
    Args:
        signals_list (list): List of signal lists
    
    Returns:
        str: The most common signal type
    """
    from collections import Counter
    
    flattened = [s for signals in signals_list for s in signals]
    if not flattened:
        return None
    
    return Counter(flattened).most_common(1)[0][0]


def print_signal_summary(processed_turns):
    """
    Print a summary of all signals in the processed turns.
    
    Args:
        processed_turns (list): List of processed conversation turns
    """
    from collections import Counter
    
    all_signals = []
    for turn in processed_turns:
        if "signals" in turn:
            all_signals.extend(turn["signals"])
    
    signal_counts = Counter(all_signals)
    
    print("\nSignal Summary:")
    print("─" * 40)
    for signal, count in signal_counts.most_common():
        percentage = (count / len(processed_turns)) * 100 if processed_turns else 0
        print(f"  {signal:<25} {count:>6}  ({percentage:>5.1f}%)")
    print("─" * 40)


def extract_signals_temporal(turn):
    """
    Extract signals WITH temporal metadata
    
    Args:
        turn (dict): A turn with 'speaker', 'text', and optionally 'turn_number' keys
    
    Returns:
        dict: {
            "signals": ["customer_frustration"],
            "turn_number": 5,
            "speaker": "customer",
            "confidence": 0.85
        }
    """
    signals = extract_signals(turn)
    confidence = max([get_signal_confidence(turn, s) for s in signals], default=0.0)
    
    return {
        "signals": signals,
        "turn_number": turn.get("turn_number", 0),
        "speaker": turn.get("speaker", "unknown"),
        "confidence": confidence,
        "text": turn.get("text", "")
    }


def build_temporal_signal_sequence(transcript_id, processed_turns):
    """
    Build ordered list of signals for a transcript
    Enables temporal causality analysis: "Did frustration PRECEDE response delay?"
    
    Args:
        transcript_id (str): ID of transcript to analyze
        processed_turns (list): All processed turns
    
    Returns:
        list: Ordered signals with turn numbers
        [
            {"turn": 3, "signal": "customer_frustration", "confidence": 0.9},
            {"turn": 5, "signal": "agent_delay", "confidence": 0.7},
            {"turn": 8, "signal": "customer_frustration", "confidence": 0.95}
        ]
    """
    # Filter turns for this transcript
    transcript_turns = [t for t in processed_turns 
                       if t.get("transcript_id") == transcript_id]
    
    # Sort by turn number
    transcript_turns.sort(key=lambda t: t.get("turn_number", 0))
    
    # Extract signals with temporal info
    signal_timeline = []
    for turn in transcript_turns:
        signals = extract_signals(turn)
        for signal in signals:
            signal_timeline.append({
                "turn": turn.get("turn_number", 0),
                "signal": signal,
                "confidence": get_signal_confidence(turn, signal),
                "speaker": turn.get("speaker", ""),
                "text": turn.get("text", "")
            })
    
    return signal_timeline


def has_precedence(signal_timeline, signal_a, signal_b, max_gap=10):
    """
    Check if signal_a occurs before signal_b in a timeline
    Useful for temporal causality: "Did frustration PRECEDE response?"
    
    Args:
        signal_timeline: Output from build_temporal_signal_sequence
        signal_a: First signal type
        signal_b: Second signal type
        max_gap: Maximum turns between signals (None for no limit)
    
    Returns:
        bool: True if signal_a precedes signal_b
    """
    turns_a = [s["turn"] for s in signal_timeline if s["signal"] == signal_a]
    turns_b = [s["turn"] for s in signal_timeline if s["signal"] == signal_b]
    
    if not turns_a or not turns_b:
        return False
    
    first_a = min(turns_a)
    first_b = min(turns_b)
    
    if max_gap is None:
        return first_a < first_b
    else:
        return first_a < first_b and (first_b - first_a) <= max_gap
