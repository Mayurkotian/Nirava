"""Context Engineering Module

Capstone Requirement: Context Engineering (Context Compaction)

This module provides:
1. Context compaction - summarizes long conversations to stay within token limits
2. Smart context windowing - keeps recent + important messages
3. Memory extraction - identifies key facts for long-term retention
"""
import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from config.llm import get_gemini_model
from config.settings import MAX_CONTEXT_TOKENS, MAX_RECENT_MESSAGES

logger = logging.getLogger(__name__)

# Token limits (approximate, 1 token ≈ 4 chars)
CHARS_PER_TOKEN = 4
MAX_CONTEXT_CHARS = MAX_CONTEXT_TOKENS * CHARS_PER_TOKEN


@dataclass
class CompactedContext:
    """Represents a compacted conversation context."""
    summary: str  # Summarized older messages
    recent_messages: List[Dict[str, str]]  # Last N messages kept verbatim
    extracted_facts: Dict[str, Any]  # Key facts extracted from conversation
    original_length: int  # Original message count
    compacted_length: int  # After compaction


class ContextEngine:
    """Manages context window and performs compaction when needed."""
    
    def __init__(self, max_recent_messages: int = MAX_RECENT_MESSAGES):
        self.model = get_gemini_model()
        self.max_recent = max_recent_messages
        self.compaction_count = 0
    
    def should_compact(self, history: List[Dict[str, str]]) -> bool:
        """Check if context needs compaction."""
        total_chars = sum(len(m.get("content", "")) for m in history)
        return total_chars > MAX_CONTEXT_CHARS or len(history) > 12
    
    def compact(self, history: List[Dict[str, str]], 
                current_facts: Dict[str, Any] = None) -> CompactedContext:
        """
        Compact conversation history while preserving key information.
        
        Strategy:
        1. Keep last N messages verbatim (most relevant)
        2. Summarize older messages into a brief context
        3. Extract key facts for session state
        """
        if len(history) <= self.max_recent:
            # No compaction needed
            return CompactedContext(
                summary="",
                recent_messages=history,
                extracted_facts=current_facts or {},
                original_length=len(history),
                compacted_length=len(history)
            )
        
        # Split into older (to summarize) and recent (to keep)
        older_messages = history[:-self.max_recent]
        recent_messages = history[-self.max_recent:]
        
        # Summarize older messages
        summary = self._summarize_messages(older_messages)
        
        # Extract any new facts from older messages
        extracted = self._extract_facts(older_messages, current_facts)
        
        self.compaction_count += 1
        logger.info(f"Context compacted: {len(history)} → {len(recent_messages)} messages (compaction #{self.compaction_count})")
        
        return CompactedContext(
            summary=summary,
            recent_messages=recent_messages,
            extracted_facts=extracted,
            original_length=len(history),
            compacted_length=len(recent_messages)
        )
    
    def _summarize_messages(self, messages: List[Dict[str, str]]) -> str:
        """Summarize a list of messages into a brief context."""
        if not messages:
            return ""
        
        # Try LLM summarization
        if self.model:
            try:
                conversation_text = "\n".join([
                    f"{m['role']}: {m['content']}" for m in messages
                ])
                
                prompt = f"""Summarize this health conversation in 2-3 sentences.
Focus on: What issue was discussed, what data was collected, what advice was given.

Conversation:
{conversation_text}

Summary:"""
                
                response = self.model.generate_content(prompt)
                return response.text.strip()
            except Exception as e:
                logger.warning(f"LLM summarization failed: {e}")
        
        # Fallback: simple extraction
        return self._fallback_summary(messages)
    
    def _fallback_summary(self, messages: List[Dict[str, str]]) -> str:
        """Rule-based summary when LLM is unavailable."""
        user_msgs = [m["content"] for m in messages if m["role"] == "user"]
        
        if not user_msgs:
            return "Previous conversation context."
        
        # Extract key phrases
        first_issue = user_msgs[0][:100] if user_msgs else ""
        msg_count = len(messages)
        
        return f"User initially discussed: '{first_issue}...' ({msg_count} messages exchanged)"
    
    def _extract_facts(self, messages: List[Dict[str, str]], 
                       existing_facts: Dict[str, Any] = None) -> Dict[str, Any]:
        """Extract key facts from messages for long-term memory."""
        facts = existing_facts.copy() if existing_facts else {}
        
        # Simple pattern matching for common facts
        all_text = " ".join([m["content"] for m in messages]).lower()
        
        # Extract sleep mentions
        import re
        sleep_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:hours?|hrs?)\s*(?:of\s+)?sleep', all_text)
        if sleep_match:
            facts["mentioned_sleep"] = float(sleep_match.group(1))
        
        # Extract stress mentions
        stress_match = re.search(r'stress(?:ed)?.*?(\d+)\s*(?:out of|/)\s*10', all_text)
        if stress_match:
            facts["mentioned_stress"] = int(stress_match.group(1))
        
        # Extract mood indicators
        if any(word in all_text for word in ["happy", "great", "amazing", "good"]):
            facts["mood_indicator"] = "positive"
        elif any(word in all_text for word in ["sad", "down", "depressed", "anxious"]):
            facts["mood_indicator"] = "negative"
        
        return facts
    
    def build_prompt_context(self, compacted: CompactedContext) -> str:
        """Build a prompt-ready context string from compacted context."""
        parts = []
        
        if compacted.summary:
            parts.append(f"[Previous conversation summary: {compacted.summary}]")
        
        if compacted.extracted_facts:
            facts_str = ", ".join([f"{k}: {v}" for k, v in compacted.extracted_facts.items()])
            parts.append(f"[Known facts: {facts_str}]")
        
        # Add recent messages
        for msg in compacted.recent_messages:
            parts.append(f"{msg['role']}: {msg['content']}")
        
        return "\n".join(parts)


# Singleton instance
_context_engine = None

def get_context_engine() -> ContextEngine:
    """Get or create the global context engine."""
    global _context_engine
    if _context_engine is None:
        _context_engine = ContextEngine()
    return _context_engine
