from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

class ConversationPhase(Enum):
    INTAKE = "intake"
    POST_ANALYSIS = "post_analysis"

@dataclass
class UserProfile:
    """Long-term memory: Who the user is."""
    # Core Identity (Safe defaults for conversational flow)
    name: str = "Friend"  # OK to default - not used in calculations
    
    # Critical Data (MUST be collected - used in BMI/BMR/TDEE calculations)
    age: Optional[int] = None           # ❌ No default - MUST collect
    sex: Optional[str] = None           # ❌ No default - MUST collect  
    height_cm: Optional[float] = None   # ❌ No default - MUST collect
    weight_kg: Optional[float] = None   # ❌ No default - MUST collect
    
    # Goals & Preferences (Safe defaults)
    primary_goal: str = "General Health"
    target_weight_kg: Optional[float] = None
    
    # Medical Context
    conditions: List[str] = field(default_factory=list)
    
    # Dietary Preferences (for NutritionAgent)
    dietary_preference: str = "omnivore"
    food_restrictions: List[str] = field(default_factory=list)
    
    # Cultural Context (NEW - for NutritionAgent)
    origin: Optional[str] = None        # e.g., "India", "USA", "UK"
    religion: Optional[str] = None      # e.g., "Hindu", "Muslim", "Jain"

class JourneyMode(Enum):
    """What the user wants from this session."""
    QUICK_CHECK = "quick_check"      # Just data + snapshot
    DEEP_DIVE = "deep_dive"          # Data + education on WHY
    BUILD_PLAN = "build_plan"        # Data + actionable weekly plan

@dataclass
class DailyCheckIn:
    """Short-term memory: The facts we extracted TODAY.
    
    Metrics mapped to the 'Nirava 6' Preventative Pillars:
    1. Sleep: sleep_hours
    2. Metabolic: water_glasses (+ BMI/BMR from profile)
    3. Movement: exercise_minutes, exercise_type
    4. Mental: stress_score, mood_score
    5. Social: social_hours
    6. Toxins: alcohol_units, smoking_today
    """
    # Pillar 1: Sleep
    sleep_hours: Optional[float] = None          # Hours (1-12)
    
    # Pillar 2: Metabolic
    water_glasses: Optional[int] = None          # Glasses (0-20)
    
    # Pillar 3: Movement
    exercise_minutes: Optional[int] = None       # Minutes (0-180)
    exercise_type: Optional[str] = None          # "cardio", "strength", "both", "none"
    
    # Pillar 4: Mental
    mood_score: Optional[int] = None             # 1-5 (1=low, 5=great)
    stress_score: Optional[int] = None           # 1-10 (1=calm, 10=overwhelmed)
    energy_score: Optional[int] = None           # 1-5 (1=exhausted, 5=energized)
    
    # Pillar 5: Social (NEW)
    social_hours: Optional[float] = None         # Hours of meaningful connection today (0-8)
    
    # Pillar 6: Toxins (NEW)
    alcohol_units: Optional[int] = None          # Units today (0-10, 1 unit = 1 beer/glass wine)
    smoking_today: Optional[bool] = None         # Did you smoke today?
    
    # Other
    symptoms: List[str] = field(default_factory=list)  # e.g. ["Headache", "Knee pain"]
    
    @property
    def is_complete(self) -> bool:
        """Do we have the 'Minimum Viable Data' to give advice?"""
        # We don't strictly require exercise/stress to be 'complete' to avoid a 20-question interrogation,
        # but we capture them if offered. For MVP, let's stick to core 4 mandatory, others optional?
        # Actually, let's make them mandatory for the "Robust" experience you requested.
        return (
            self.sleep_hours is not None and 
            self.water_glasses is not None and 
            self.mood_score is not None and
            self.energy_score is not None and
            self.stress_score is not None and
            self.exercise_minutes is not None
        )
    
    @property
    def missing_fields(self) -> List[str]:
        missing = []
        if self.sleep_hours is None: missing.append("sleep duration")
        if self.water_glasses is None: missing.append("water intake")
        if self.mood_score is None: missing.append("mood (1-5)")
        if self.energy_score is None: missing.append("energy level (1-5)")
        if self.stress_score is None: missing.append("stress level (1-5)")
        if self.exercise_minutes is None: missing.append("daily movement/exercise")
        return missing

@dataclass
class ConversationState:
    """The flowing state of the chat."""
    history: List[Dict[str, str]] = field(default_factory=list) # [{"role": "user", "content": "..."}]
    profile: UserProfile = field(default_factory=UserProfile)
    current_checkin: DailyCheckIn = field(default_factory=DailyCheckIn)
    phase: ConversationPhase = ConversationPhase.INTAKE
    journey_mode: Optional[JourneyMode] = None  # What the user wants from this session
    
    def add_user_message(self, msg: str):
        self.history.append({"role": "user", "content": msg})
        
    def add_agent_message(self, msg: str):
        self.history.append({"role": "model", "content": msg})