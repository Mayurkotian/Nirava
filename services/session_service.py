"""Session Service Module

Capstone Requirements:
- Sessions & State Management (InMemorySessionService pattern)
- Long-running Operations (Pause/Resume with checkpoints)

This module provides:
1. In-memory session storage (following ADK patterns)
2. Session persistence to JSON (for pause/resume)
3. Checkpoint creation and restoration
"""
import json
import logging
import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from config.settings import SESSION_STORAGE_PATH

logger = logging.getLogger(__name__)

# Session storage directory
SESSION_DIR = SESSION_STORAGE_PATH
SESSION_DIR.mkdir(exist_ok=True)


@dataclass
class SessionCheckpoint:
    """A checkpoint that can be used to resume a session."""
    checkpoint_id: str
    created_at: str
    phase: str  # INTAKE, ANALYSIS, COMPLETE
    issue_type: Optional[str]
    collected_data: Dict[str, Any]
    history: List[Dict[str, str]]
    context_summary: str  # Compacted context
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "SessionCheckpoint":
        return cls(**data)


@dataclass  
class Session:
    """Represents a user session with full state."""
    session_id: str
    user_id: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    phase: str = "INTAKE"
    issue_type: Optional[str] = None
    profile: Dict[str, Any] = field(default_factory=dict)
    checkin: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, str]] = field(default_factory=list)
    checkpoints: List[str] = field(default_factory=list)  # List of checkpoint IDs
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "Session":
        return cls(**data)


class InMemorySessionService:
    """
    In-memory session service following Google ADK patterns.
    
    Features:
    - Create/Get/Update/Delete sessions
    - Checkpoint creation for pause/resume
    - Optional persistence to disk
    """
    
    def __init__(self, persist: bool = True):
        self._sessions: Dict[str, Session] = {}
        self._checkpoints: Dict[str, SessionCheckpoint] = {}
        self._persist = persist
        
        # Load existing sessions from disk
        if persist:
            self._load_from_disk()
    
    # === Core Session Operations ===
    
    def create_session(self, user_id: str, session_id: str = None) -> Session:
        """Create a new session for a user."""
        if session_id is None:
            session_id = f"session_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        session = Session(
            session_id=session_id,
            user_id=user_id,
            profile={"name": "Friend", "age": 30}  # Defaults
        )
        
        self._sessions[session_id] = session
        logger.info(f"Created session: {session_id}")
        
        if self._persist:
            self._save_session(session)
        
        return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID."""
        return self._sessions.get(session_id)
    
    def update_session(self, session: Session) -> Session:
        """Update a session."""
        session.updated_at = datetime.now().isoformat()
        self._sessions[session.session_id] = session
        
        if self._persist:
            self._save_session(session)
        
        return session
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session and its checkpoints."""
        if session_id in self._sessions:
            session = self._sessions.pop(session_id)
            
            # Delete checkpoints
            for cp_id in session.checkpoints:
                self._checkpoints.pop(cp_id, None)
                if self._persist:
                    cp_path = SESSION_DIR / f"{cp_id}.checkpoint.json"
                    cp_path.unlink(missing_ok=True)
            
            if self._persist:
                session_path = SESSION_DIR / f"{session_id}.json"
                session_path.unlink(missing_ok=True)
            
            logger.info(f"Deleted session: {session_id}")
            return True
        return False
    
    def list_sessions(self, user_id: str = None) -> List[Session]:
        """List all sessions, optionally filtered by user."""
        sessions = list(self._sessions.values())
        if user_id:
            sessions = [s for s in sessions if s.user_id == user_id]
        return sessions
    
    # === Checkpoint Operations (Pause/Resume) ===
    
    def create_checkpoint(self, session_id: str, 
                         context_summary: str = "") -> Optional[SessionCheckpoint]:
        """
        Create a checkpoint to pause a session.
        
        This allows long-running agent operations to be paused and resumed later.
        """
        session = self.get_session(session_id)
        if not session:
            logger.error(f"Cannot checkpoint: session {session_id} not found")
            return None
        
        checkpoint_id = f"cp_{session_id}_{datetime.now().strftime('%H%M%S')}"
        
        checkpoint = SessionCheckpoint(
            checkpoint_id=checkpoint_id,
            created_at=datetime.now().isoformat(),
            phase=session.phase,
            issue_type=session.issue_type,
            collected_data=session.checkin.copy(),
            history=session.history.copy(),
            context_summary=context_summary
        )
        
        self._checkpoints[checkpoint_id] = checkpoint
        session.checkpoints.append(checkpoint_id)
        self.update_session(session)
        
        if self._persist:
            self._save_checkpoint(checkpoint)
        
        logger.info(f"Created checkpoint: {checkpoint_id} for session {session_id}")
        return checkpoint
    
    def resume_from_checkpoint(self, checkpoint_id: str) -> Optional[Session]:
        """
        Resume a session from a checkpoint.
        
        Returns the session restored to the checkpoint state.
        """
        checkpoint = self._checkpoints.get(checkpoint_id)
        if not checkpoint:
            # Try loading from disk
            if self._persist:
                checkpoint = self._load_checkpoint(checkpoint_id)
            
            if not checkpoint:
                logger.error(f"Checkpoint {checkpoint_id} not found")
                return None
        
        # Find the parent session
        session_id = checkpoint_id.split("_")[1] + "_" + checkpoint_id.split("_")[2]
        for sid, session in self._sessions.items():
            if checkpoint_id in session.checkpoints:
                # Restore session state from checkpoint
                session.phase = checkpoint.phase
                session.issue_type = checkpoint.issue_type
                session.checkin = checkpoint.collected_data.copy()
                session.history = checkpoint.history.copy()
                
                self.update_session(session)
                logger.info(f"Resumed session {session.session_id} from checkpoint {checkpoint_id}")
                return session
        
        logger.error(f"Could not find session for checkpoint {checkpoint_id}")
        return None
    
    def get_latest_checkpoint(self, session_id: str) -> Optional[SessionCheckpoint]:
        """Get the most recent checkpoint for a session."""
        session = self.get_session(session_id)
        if not session or not session.checkpoints:
            return None
        
        latest_id = session.checkpoints[-1]
        return self._checkpoints.get(latest_id)
    
    # === Persistence ===
    
    def _save_session(self, session: Session):
        """Save session to disk."""
        path = SESSION_DIR / f"{session.session_id}.json"
        with open(path, "w") as f:
            json.dump(session.to_dict(), f, indent=2)
    
    def _save_checkpoint(self, checkpoint: SessionCheckpoint):
        """Save checkpoint to disk."""
        path = SESSION_DIR / f"{checkpoint.checkpoint_id}.checkpoint.json"
        with open(path, "w") as f:
            json.dump(checkpoint.to_dict(), f, indent=2)
    
    def _load_from_disk(self):
        """Load all sessions and checkpoints from disk."""
        # Load sessions
        for path in SESSION_DIR.glob("*.json"):
            if ".checkpoint." in path.name:
                continue
            try:
                with open(path) as f:
                    data = json.load(f)
                    session = Session.from_dict(data)
                    self._sessions[session.session_id] = session
            except Exception as e:
                logger.warning(f"Failed to load session {path}: {e}")
        
        # Load checkpoints
        for path in SESSION_DIR.glob("*.checkpoint.json"):
            try:
                with open(path) as f:
                    data = json.load(f)
                    cp = SessionCheckpoint.from_dict(data)
                    self._checkpoints[cp.checkpoint_id] = cp
            except Exception as e:
                logger.warning(f"Failed to load checkpoint {path}: {e}")
        
        logger.info(f"Loaded {len(self._sessions)} sessions, {len(self._checkpoints)} checkpoints")
    
    def _load_checkpoint(self, checkpoint_id: str) -> Optional[SessionCheckpoint]:
        """Load a specific checkpoint from disk."""
        path = SESSION_DIR / f"{checkpoint_id}.checkpoint.json"
        if path.exists():
            try:
                with open(path) as f:
                    return SessionCheckpoint.from_dict(json.load(f))
            except Exception as e:
                logger.error(f"Failed to load checkpoint: {e}")
        return None


# Global session service instance
_session_service = None

def get_session_service() -> InMemorySessionService:
    """Get or create the global session service."""
    global _session_service
    if _session_service is None:
        _session_service = InMemorySessionService(persist=True)
    return _session_service
