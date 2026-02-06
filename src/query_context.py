"""
Query Context - Maintain session state for multi-turn reasoning
Enables follow-up questions that reference previous answers
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid


@dataclass
class Query:
    """Record of a single query and response"""
    query_id: str
    timestamp: datetime
    question: str
    response_type: str  # "explanation", "similar_cases", "chain_stats", etc.
    response_data: Dict[str, Any]
    transcript_id: Optional[str] = None  # Reference transcript if applicable
    
    def __repr__(self):
        return f"Query({self.question[:40]}... → {self.response_type})"


class QueryContext:
    """
    Maintains session state for multi-turn reasoning
    
    Enables:
    - Query 1: "Why did ABC123 escalate?" → Sets current_transcript
    - Query 2: "Tell me about turn 5" → Uses current_transcript context
    - Query 3: "Are there similar cases?" → References previous explanation
    """
    
    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or uuid.uuid4().hex[:8]
        
        # Core state
        self.current_transcript_id: Optional[str] = None
        self.current_explanation: Optional[Dict] = None
        
        # History
        self.query_history: List[Query] = []
        self.max_history = 10  # Keep last N queries
        
        # Derived context
        self.inferred_intent = None  # What the user is trying to do
        self.conversation_theme = None  # Running theme
    

    def add_query(self, question: str, response_type: str, 
                  response_data: Dict[str, Any], 
                  transcript_id: Optional[str] = None) -> Query:
        """
        Record a query and response
        
        Args:
            question: User's question
            response_type: Type of response ("explanation", "similar_cases", etc.)
            response_data: Response content
            transcript_id: Related transcript if applicable
        
        Returns:
            Query object that was added
        """
        query = Query(
            query_id=uuid.uuid4().hex[:8],
            timestamp=datetime.now(),
            question=question,
            response_type=response_type,
            response_data=response_data,
            transcript_id=transcript_id
        )
        
        self.query_history.append(query)
        
        # Maintain max history size
        if len(self.query_history) > self.max_history:
            self.query_history.pop(0)
        
        # Update current state if applicable
        if response_type == "explanation" and transcript_id:
            self.current_transcript_id = transcript_id
            self.current_explanation = response_data
        
        return query
    
    def get_context(self) -> Dict[str, Any]:
        """
        Get current context for next query
        
        Useful for: query engine can use this to enhance responses
        
        Returns:
            Dict with:
            - current_transcript: current focus
            - last_explanation: most recent explanation
            - recent_queries: last few queries
            - inferred_theme: what user is exploring
        """
        return {
            "session_id": self.session_id,
            "current_transcript": self.current_transcript_id,
            "last_explanation": self.current_explanation,
            "recent_queries": [
                {
                    "question": q.question,
                    "type": q.response_type,
                    "transcript": q.transcript_id
                }
                for q in self.query_history[-3:]
            ],
            "conversation_theme": self.conversation_theme,
            "query_count": len(self.query_history)
        }
    
    def reference_previous_query(self, offset: int = -1) -> Optional[Query]:
        """
        Get a previous query by offset
        
        Args:
            offset: -1 for last query, -2 for second-to-last, etc.
        
        Returns:
            Query object or None
        """
        try:
            return self.query_history[offset]
        except IndexError:
            return None
    
    def set_theme(self, theme: str):
        """Set conversation theme for context"""
        self.conversation_theme = theme
    
    def get_transcript_history(self) -> List[str]:
        """Get all transcript IDs mentioned in this session"""
        seen = []
        for query in self.query_history:
            if query.transcript_id and query.transcript_id not in seen:
                seen.append(query.transcript_id)
        return seen
    
    def clear_history(self):
        """Clear query history (but keep session ID)"""
        self.query_history = []
        self.current_transcript_id = None
        self.current_explanation = None
    
    def export_session(self) -> Dict:
        """Export session data as JSON-serializable dict"""
        return {
            "session_id": self.session_id,
            "queries": [
                {
                    "query_id": q.query_id,
                    "timestamp": q.timestamp.isoformat(),
                    "question": q.question,
                    "response_type": q.response_type,
                    "transcript_id": q.transcript_id
                }
                for q in self.query_history
            ],
            "current_transcript": self.current_transcript_id,
            "theme": self.conversation_theme
        }
    
    def __repr__(self):
        return f"QueryContext(session={self.session_id}, queries={len(self.query_history)}, current={self.current_transcript_id})"


class SessionManager:
    """
    Manage multiple query contexts (for multi-user or multi-session scenarios)
    """
    
    def __init__(self):
        self.sessions: Dict[str, QueryContext] = {}
    
    def create_session(self, session_id: Optional[str] = None) -> QueryContext:
        """Create a new session"""
        context = QueryContext(session_id)
        self.sessions[context.session_id] = context
        return context
    
    def get_session(self, session_id: str) -> Optional[QueryContext]:
        """Get existing session"""
        return self.sessions.get(session_id)
    
    def delete_session(self, session_id: str):
        """Delete a session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
    
    def list_sessions(self) -> List[str]:
        """List all active session IDs"""
        return list(self.sessions.keys())


# Example multi-turn conversation flow
def demo_multi_turn():
    """Demo: show how multi-turn reasoning works"""
    
    context = QueryContext()
    
    # Turn 1: User asks about a specific transcript
    print("🤖 Turn 1: User asks 'Why did conv_12345 escalate?'")
    context.add_query(
        question="Why did conv_12345 escalate?",
        response_type="explanation",
        response_data={
            "transcript_id": "conv_12345",
            "chain": ["customer_frustration", "agent_delay"],
            "confidence": 0.78
        },
        transcript_id="conv_12345"
    )
    print(f"Context after Turn 1:\n{context.get_context()}\n")
    
    # Turn 2: User asks about a specific turn in the explanation
    print("🤖 Turn 2: User asks 'What was happening at turn 5?'")
    context.add_query(
        question="What was happening at turn 5?",
        response_type="turn_detail",
        response_data={
            "turn_number": 5,
            "speaker": "agent",
            "text": "Let me hold for a moment...",
            "signals": ["agent_delay"]
        },
        transcript_id="conv_12345"  # System infers this from context
    )
    print(f"Context after Turn 2:\n{context.get_context()}\n")
    
    # Turn 3: User asks about similar cases
    print("🤖 Turn 3: User asks 'Are there similar escalations?'")
    context.add_query(
        question="Are there similar escalations?",
        response_type="similar_cases",
        response_data={
            "reference": "conv_12345",
            "similar": ["conv_12346", "conv_12347", "conv_12348"],
            "chain": ["customer_frustration", "agent_delay"]
        }
    )
    print(f"Context after Turn 3:\n{context.get_context()}\n")
    
    # Show session export
    print("\n📋 Session Export:")
    import json
    print(json.dumps(context.export_session(), indent=2, default=str))


if __name__ == "__main__":
    demo_multi_turn()
