"""IntakeAgent - Symptom-Aware Health Companion

Capstone Concepts Demonstrated:
- Loop Agent (continues until data collection complete)
- LLM-Powered Agent (Gemini 2.0 Flash)
- Few-Shot Prompting (15+ extraction examples)
- Structured JSON Output

Philosophy:
    Smart triage - ask only relevant questions based on the issue type.
    Mentally tired? Ask about sleep, stress, mood. NOT BMI.
    Physically lethargic? Ask about sleep, exercise, BMI, water.

Design Decisions:
    1. Issue Classification: Uses keyword matching first, then LLM for nuanced cases
    2. Relevant Metrics: Each issue type has a predefined set of metrics to collect
    3. Loop Until Complete: Continues conversation until 3+ relevant metrics gathered
    4. Graceful Fallback: Uses rule-based responses if LLM fails

Prompt Engineering:
    - Uses 15+ few-shot examples for reliable data extraction
    - JSON mode for structured output parsing
    - Dynamic context based on collected data so far
"""
from typing import Dict, Any, Optional, List
import json
import re
import logging
from config.llm import get_gemini_model
from models.session import ConversationState

logger = logging.getLogger(__name__)

# Issue categories and their relevant metrics - DOCTOR-LIKE DIAGNOSTIC APPROACH
# Each issue has 10-12 targeted questions (like a medical interview)
# Ordered by priority: most critical metrics first

ISSUE_METRICS = {
    # STRESS/EMOTIONAL: Focus on mental health, lifestyle, and coping mechanisms
    "emotional": [
        "stress_score",      # Primary symptom
        "mood_score",        # Core indicator
        "sleep_hours",       # Stress disrupts sleep
        "social_hours",      # Isolation worsens stress
        "exercise_minutes",  # Proven stress relief
        "exercise_type",     # Quality matters
        "energy_score",      # Burnout indicator
        "water_glasses",     # Dehydration affects mood
        "alcohol_units",     # Coping mechanism red flag
        "smoking_today",     # Another coping mechanism
    ],
    
    # MENTAL FATIGUE (brain fog, can't focus): Focus on sleep quality and metabolic factors
    "mental_fatigue": [
        "sleep_hours",       # #1 cause of brain fog
        "stress_score",      # Chronic stress impairs cognition
        "water_glasses",     # Dehydration = cognitive decline
        "mood_score",        # Depression causes brain fog
        "energy_score",      # Related to mental clarity
        "exercise_minutes",  # Blood flow to brain
        "social_hours",      # Loneliness affects cognition
        "alcohol_units",     # Alcohol impairs cognition
        "smoking_today",     # Affects oxygen to brain
    ],
    
    # PHYSICAL FATIGUE: Focus on energy sources and recovery
    "physical_fatigue": [
        "sleep_hours",       # Recovery foundation
        "energy_score",      # Primary complaint
        "exercise_minutes",  # Paradoxically, movement = energy
        "exercise_type",     # Overtraining check
        "water_glasses",     # Dehydration = fatigue
        "stress_score",      # Chronic stress = adrenal fatigue
        "mood_score",        # Depression presents as fatigue
        "social_hours",      # Isolation = low energy
        "alcohol_units",     # Disrupts sleep quality
        "smoking_today",     # Reduces oxygen capacity
    ],
    
    # SLEEP ISSUES: Focus on sleep disruptors
    "sleep_issues": [
        "sleep_hours",       # Quantify the problem
        "stress_score",      # #1 sleep disruptor
        "exercise_minutes",  # Exercise timing affects sleep
        "exercise_type",     # Intense evening exercise = insomnia
        "alcohol_units",     # Ruins REM sleep
        "mood_score",        # Anxiety/depression = insomnia
        "energy_score",      # Daytime fatigue despite sleep?
        "water_glasses",     # Nighttime urination?
        "social_hours",      # Loneliness = rumination at night
        "smoking_today",     # Nicotine is a stimulant
    ],
    
    # GENERAL WELLNESS: Comprehensive baseline
    "general_wellness": [
        "sleep_hours", "water_glasses", "mood_score", "energy_score",
        "stress_score", "exercise_minutes", "exercise_type",
        "social_hours", "alcohol_units", "smoking_today"
    ],
    
    # BUILD PLAN (Journey C): Everything + dietary needs + profile data
    "build_plan": [
        "age", "sex", "height_cm", "weight_kg",  # Profile data for BMI/BMR
        "sleep_hours", "water_glasses", "mood_score", "energy_score",
        "stress_score", "exercise_minutes", "exercise_type",
        "social_hours", "alcohol_units", "smoking_today",
        "dietary_preference", "origin", "religion"  # Cultural context
    ],
}

# Keywords to classify issue type
ISSUE_KEYWORDS = {
    "mental_fatigue": ["brain fog", "can't focus", "mentally tired", "can't think", "concentration", "distracted", "foggy", "mental"],
    "emotional": ["sad", "anxious", "depressed", "down", "worried", "stressed out", "overwhelmed", "upset", "lonely"],
    "physical_fatigue": ["lethargic", "sluggish", "no energy", "exhausted", "physically tired", "weak", "drained", "fatigued"],
    "sleep_issues": ["can't sleep", "insomnia", "restless", "waking up", "sleep problems", "tired but can't sleep"],
}


class IntakeAgent:
    """Symptom-aware agent that asks only relevant questions."""
    def __init__(self):
        self.model = get_gemini_model()
        self.issue_type = None  # Will be classified from first response
        self.relevant_metrics = None

    def run_conversation(self, session: ConversationState) -> Dict[str, Any]:
        """Process conversation with symptom-aware triage."""
        if not self.model:
            return self._fallback(session)

        # Handle Journey Mode selection (A/B/C)
        if session.journey_mode is None and session.history:
            last_msg = session.history[-1].get("content", "").strip().upper()
            if last_msg in ["A", "QUICK CHECK", "QUICK"]:
                from models.session import JourneyMode
                session.journey_mode = JourneyMode.QUICK_CHECK
            elif last_msg in ["B", "DEEP DIVE", "DEEP", "EDUCATE", "EDUCATION"]:
                from models.session import JourneyMode
                session.journey_mode = JourneyMode.DEEP_DIVE
            elif last_msg in ["C", "BUILD PLAN", "PLAN", "BUILD"]:
                from models.session import JourneyMode
                session.journey_mode = JourneyMode.BUILD_PLAN

        # Classify issue type from conversation if not done yet
        if self.issue_type is None and len(session.history) >= 2:
            # Special handling for BUILD_PLAN journey
            from models.session import JourneyMode
            if session.journey_mode == JourneyMode.BUILD_PLAN:
                self.issue_type = "build_plan"
                self.relevant_metrics = ISSUE_METRICS["build_plan"]
            else:
                self._classify_issue(session)
        
        prompt = self._build_prompt(session)
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            text = response.text.replace("```json", "").replace("```", "").strip()
            result = json.loads(text)
            
            # Check if LLM classified the issue
            if result.get("issue_type") and self.issue_type is None:
                self.issue_type = result["issue_type"]
                self.relevant_metrics = ISSUE_METRICS.get(self.issue_type, ISSUE_METRICS["general_wellness"])
                logger.debug(f"Issue classified as: {self.issue_type}")
                logger.debug(f"Relevant metrics: {self.relevant_metrics}")

            updates = result.get("extracted", {})
            self._apply_updates(session, updates)
            
            status = result.get("status", "CONTINUE").upper()
            
            # Check if we have enough RELEVANT data
            if self._has_enough_data(session) or status == "COMPLETE":
                return {"status": "COMPLETE", "reply": None, "extracted_updates": updates, "issue_type": self.issue_type}
            
            return {
                "status": "CONTINUE",
                "reply": result.get("reply", "Tell me more."),
                "extracted_updates": updates,
                "issue_type": self.issue_type
            }

        except Exception as e:
            logger.error(f"IntakeAgent error: {e}")
            return self._fallback(session)
    
    def _classify_issue(self, session: ConversationState):
        """Classify issue type from conversation history with multi-label detection."""
        text = " ".join([m["content"].lower() for m in session.history if m["role"] == "user"])
        
        # Count keyword matches for each issue type
        issue_scores = {}
        for issue_type, keywords in ISSUE_KEYWORDS.items():
            matches = sum(1 for kw in keywords if kw in text)
            if matches > 0:
                issue_scores[issue_type] = matches
        
        # If multiple issues detected (2+ with matches), use general_wellness (comprehensive)
        if len(issue_scores) >= 2:
            logger.info(f"Multiple issues detected: {list(issue_scores.keys())}. Using comprehensive metrics.")
            self.issue_type = "general_wellness"  # Most comprehensive metric set
            self.relevant_metrics = ISSUE_METRICS["general_wellness"]
            return
        
        # If single issue detected, use it
        if len(issue_scores) == 1:
            self.issue_type = list(issue_scores.keys())[0]
            self.relevant_metrics = ISSUE_METRICS[self.issue_type]
            logger.info(f"Issue classified as: {self.issue_type}")
            return
        
        # Default: check if they said they're feeling good
        good_keywords = ["good", "great", "fine", "okay", "well", "amazing", "fantastic"]
        if any(kw in text for kw in good_keywords):
            self.issue_type = "general_wellness"
            self.relevant_metrics = ISSUE_METRICS["general_wellness"]
        else:
            # Default to general_wellness (safest, most comprehensive)
            logger.info("No clear issue detected. Using general_wellness.")
            self.issue_type = "general_wellness"
            self.relevant_metrics = ISSUE_METRICS["general_wellness"]
    
    def _has_enough_data(self, session: ConversationState) -> bool:
        """Check if we have enough RELEVANT metrics (aiming for near-complete data)."""
        if not self.relevant_metrics:
            return session.current_checkin.is_complete
        
        c = session.current_checkin
        p = session.profile
        collected = 0
        
        # Check each metric (including profile data)
        for metric in self.relevant_metrics:
            # Profile metrics (critical for BMI/BMR calculations)
            if metric == "age" and p.age is not None: collected += 1
            elif metric == "sex" and p.sex is not None: collected += 1
            elif metric == "height_cm" and p.height_cm is not None: collected += 1
            elif metric == "weight_kg" and p.weight_kg is not None: collected += 1
            elif metric == "origin" and p.origin is not None: collected += 1
            elif metric == "religion" and p.religion is not None: collected += 1
            # Check-in metrics
            elif metric == "sleep_hours" and c.sleep_hours is not None: collected += 1
            elif metric == "water_glasses" and c.water_glasses is not None: collected += 1
            elif metric == "mood_score" and c.mood_score is not None: collected += 1
            elif metric == "energy_score" and c.energy_score is not None: collected += 1
            elif metric == "stress_score" and c.stress_score is not None: collected += 1
            elif metric == "exercise_minutes" and c.exercise_minutes is not None: collected += 1
            elif metric == "exercise_type" and c.exercise_type is not None: collected += 1
            elif metric == "social_hours" and c.social_hours is not None: collected += 1
            elif metric == "alcohol_units" and c.alcohol_units is not None: collected += 1
            elif metric == "smoking_today" and c.smoking_today is not None: collected += 1
            elif metric == "dietary_preference" and p.dietary_preference != "omnivore": collected += 1
        
        # Require comprehensive data (8+ metrics or 75% of relevant, whichever is lower)
        # This ensures we ask 8-10 questions minimum for solid analysis
        threshold = max(8, int(len(self.relevant_metrics) * 0.75))
        return collected >= threshold

    def _build_prompt(self, session: ConversationState) -> str:
        """Symptom-aware prompt that asks only relevant questions."""
        history = "\n".join([f"{m['role']}: {m['content']}" for m in session.history[-6:]])
        collected = self._get_collected(session)
        turn_count = len([m for m in session.history if m['role'] == 'user'])
        
        # Determine what to ask based on issue type
        if self.issue_type and self.relevant_metrics:
            needed = self._get_missing_relevant(session)
            issue_context = self._get_issue_context()
        else:
            needed = session.current_checkin.missing_fields
            issue_context = "Issue type not yet determined. Classify from their response."
        
        return f"""You are Nirava, a caring friend who understands health science.

PERSONALITY: Warm, understanding, focused. You ask ONLY what's relevant to their specific issue.
NOT: A form, a survey, or someone who asks irrelevant questions.

MODE-SPECIFIC BEHAVIOR:
- **Path A (QUICK_CHECK)**: Be efficient. Ask questions concisely without lengthy explanations.
- **Path B (DEEP_DIVE)**: Be educational. Explain WHY you're asking each question and what the metric means.
  Example: "How many hours did you sleep? (7-9h is ideal for cellular repair and memory consolidation)"
- **Path C (BUILD_PLAN)**: Be comprehensive. Collect detailed data and explain how it connects to the plan.

CONTEXT AWARENESS (CRITICAL):
- ALWAYS check "DATA COLLECTED" before asking questions.
- If a metric is already known (e.g., sleep_hours: 6h), DO NOT re-ask it.
- Instead, ask a FOLLOW-UP question to go deeper:
  Example: "I see you got 6h sleep. Have you been waking up during the night, or sleeping straight through?"
- Use known data to ask smarter, more targeted questions.

SCOPE GUARD (CRITICAL):
- We ONLY handle the 6 Preventative Health Pillars: Sleep, Hydration, Movement, Mental Health, Social Connection, Toxin Avoidance.
- We do NOT handle: Medical diagnosis, injuries, rashes, severe pain, chronic diseases, emergencies.
- If user asks out-of-scope questions: Respond with:
  "I specialize in preventative health (Sleep, Stress, Hydration, Energy, Movement, and Lifestyle). For medical concerns like [their issue], please consult a healthcare provider. 
  
  However, I can help you optimize your basics. How have you been sleeping lately?"
- Always redirect to our core competencies after declining.

USER: {session.profile.name}
CONVERSATION:
{history}

DATA COLLECTED: {collected}
METRICS NEEDED FOR THIS ISSUE: {needed}
TURN COUNT: {turn_count}

{issue_context}

CONVERSATIONAL FLOW (Natural Transitions):
- **Turn 1**: After acknowledging their issue, set expectations.
- **Turn 2-3**: Keep momentum. No need for "Great!" or "Wonderful!". Just flow naturally.
- **Turn 4-6**: Add a brief transition phrase to maintain rapport:
  Examples: "Got it.", "I see.", "Okay.", "That helps."
- **Turn 7+**: If nearing completion, acknowledge progress:
  Examples: "Almost there.", "Just a couple more things.", "Last few questions."
- **NEVER**: "That's great!" after every answer. Be conversational, not robotic.

RULES:

**TURN 1** (First response from user):
- Acknowledge what they said briefly (1 sentence max).
- CLASSIFY their issue type.
- IF they share a health problem within our scope: 
  1. Acknowledge it empathetically.
  2. STATE EXPECTATION based on journey mode:
     - Path A: "I'll ask ~8-10 quick questions to understand what's going on."
     - Path B: "I'll ask ~8-10 questions and explain what each one reveals about your health."
     - Path C: "I'll ask ~10-12 comprehensive questions to build your personalized plan."
  3. IMMEDIATELY ask the FIRST PRIORITY metric from "METRICS NEEDED" (skip if already collected).
     - Path B: Add educational context (e.g., "Sleep is the foundation of cognitive function...")
- DO NOT ask "Are you ready?" or "Shall we start?". NO confirmation steps.
- IF they share a scary medical symptom: Use the SCOPE GUARD rule above.
- IF they ask a vague question: Clarify our scope first, then ask a metric question.

**TURN 2+**:
- CHECK "DATA COLLECTED" first. Skip any metrics already known.
- Ask about the NEXT UNCOLLECTED priority metric from "METRICS NEEDED".
- EXPLAIN RANGES when asking (helps user give accurate answers):
  Example: "What's your stress level? (1=totally calm, 5=manageable, 10=completely overwhelmed)"
- Path B (DEEP_DIVE): Add educational WHY:
  Example: "How much water have you had? (Aim for 8+ glasses. Dehydration reduces cognitive performance by up to 30%.)"
- If a metric is ALREADY COLLECTED, ask a FOLLOW-UP to go deeper:
  Example: If sleep_hours=5, ask: "Do you have trouble falling asleep, or do you wake up frequently?"
- OPTIONAL: Group 2 related metrics if it flows naturally.
- SKIP generic fluff. Be conversational but efficient.
- CRITICAL: The metrics list is ORDERED BY PRIORITY. Work through it sequentially, skipping known data.

=== FEW-SHOT EXTRACTION EXAMPLES (Study these carefully) ===

**EXAMPLE 1: Sleep Extraction**
User: "I got maybe 5-6 hours last night"
→ sleep_hours: 5.5 (average of range)

User: "Slept terribly, like 4 hours max"
→ sleep_hours: 4.0

User: "Got a solid 8"
→ sleep_hours: 8.0

**EXAMPLE 2: Water Extraction**
User: "I've had about 6 glasses"
→ water_glasses: 6

User: "Maybe 2 liters?"
→ water_glasses: 8 (1L = 4 glasses)

User: "Just coffee honestly"
→ water_glasses: 0 (ask about water specifically)

**EXAMPLE 3: Stress Extraction**
User: "I'm super stressed, like 8 out of 10"
→ stress_score: 8

User: "Stress is through the roof"
→ stress_score: 9 (interpret "through the roof" as very high)

User: "Not too bad actually"
→ stress_score: 3 (interpret vague positive as low)

**EXAMPLE 4: Mood/Energy Extraction**
User: "Feeling like a 3 out of 10"
→ mood_score: 2 (convert 3/10 to 1.5, round to 2 on 1-5 scale)

User: "Pretty good actually!"
→ mood_score: 4 (positive = 4)

User: "Exhausted, no energy"
→ energy_score: 1

**EXAMPLE 5: Exercise Extraction**
User: "Went for a run this morning"
→ exercise_minutes: 30 (estimate typical run)

User: "Did an hour at the gym"
→ exercise_minutes: 60

User: "Walked to work, about 20 minutes"
→ exercise_minutes: 20

**EXAMPLE 6: Alcohol Extraction**
User: "I had 4 drinks today"
→ alcohol_units: 4

User: "2 beers"
→ alcohol_units: 2

User: "No alcohol"
→ alcohol_units: 0

**EXAMPLE 7: Profile Data Extraction**
User: "I'm 28 years old"
→ age: 28

User: "Female"
→ sex: "female"

User: "165 cm tall"
→ height_cm: 165.0

User: "I weigh 60 kg"
→ weight_kg: 60.0

=== ASKING QUESTIONS (Use EXACT ranges) ===
When asking for metrics, ALWAYS specify the valid range:

**PROFILE DATA (Ask ONLY if Journey = BUILD_PLAN or if needed for BMI/BMR):**
- 🎂 **Age:** "How old are you? (10-120)"
- ⚧️ **Sex:** "What's your biological sex? (male/female)"
- 📏 **Height:** "Your height in cm? (e.g., 170cm = 5'7\")"
- ⚖️ **Weight:** "Your current weight in kg? (e.g., 70kg = 154lbs)"
- 🌍 **Origin:** "Where are you from? (e.g., India, USA, UK)" [Only for BUILD_PLAN]
- 🕊 **Religion:** "Any religious dietary restrictions? (Hindu/Muslim/Jain/Jewish/None)" [Only for BUILD_PLAN]

**DAILY CHECK-IN DATA:**
- 😴 **Sleep:** "How many hours did you sleep last night? (1-12)"
- 💧 **Water:** "Glasses of water today? (0-20)"
- 😊 **Mood:** "Mood right now? (1=low, 5=great)"
- ⚡ **Energy:** "Energy level? (1=exhausted, 5=energized)"
- 🧘 **Stress:** "Stress level? (1=calm, 10=overwhelmed)"
- 🏃 **Exercise:** "Minutes of movement today? (0-180)"
- 👥 **Social:** "Hours of meaningful social time today? (0-8)"
- 🍺 **Alcohol:** "Alcohol units today? (0=none, 1=one drink)"
- 🚬 **Smoking:** "Did you smoke today? (yes/no)"
- 🥗 **Diet:** "Dietary preference? (vegetarian/vegan/pescatarian/omnivore)" [Only for BUILD_PLAN]

OUTPUT JSON:
{{
  "issue_type": "mental_fatigue" | "emotional" | "physical_fatigue" | "sleep_issues" | "general_wellness" | "build_plan" | null,
  "extracted": {{
    "age": int (10-120) or null,
    "sex": "male" | "female" or null,
    "height_cm": float (100-250) or null,
    "weight_kg": float (30-300) or null,
    "origin": string or null,
    "religion": string or null,
    "sleep_hours": float (1-12) or null,
    "water_glasses": int (0-20) or null,
    "mood_score": int (1-5) or null,
    "energy_score": int (1-5) or null,
    "stress_score": int (1-10) or null,
    "exercise_minutes": int (0-180) or null,
    "exercise_type": "cardio" | "strength" | "both" | "none" | null,
    "social_hours": float (0-8) or null,
    "alcohol_units": int (0-10) or null,
    "smoking_today": boolean or null,
    "dietary_preference": "vegetarian" | "vegan" | "pescatarian" | "omnivore" | null
  }},
  "status": "CONTINUE" or "COMPLETE",
  "reply": "Your natural response"
}}

Set issue_type on Turn 1. Status COMPLETE when 3+ relevant metrics collected."""

    def _get_missing_relevant(self, session: ConversationState) -> List[str]:
        """Get missing metrics that are relevant to this issue type."""
        if not self.relevant_metrics:
            return session.current_checkin.missing_fields
        
        missing = []
        
        for metric in self.relevant_metrics:
            # Use programmatic check instead of manual if/elif
            if not self._is_collected(session, metric):
                # Convert metric name to friendly name
                friendly_name = metric.replace("_", " ").replace(" score", "").replace(" hours", "").replace(" glasses", "").replace(" minutes", "")
                missing.append(friendly_name)
        
        return missing
    
    def _get_issue_context(self) -> str:
        """Get context instructions based on issue type."""
        contexts = {
            "mental_fatigue": """ISSUE: MENTAL FATIGUE (brain fog, can't focus, mentally tired)
RELEVANT: Sleep, Stress, Water, Mood
NOT RELEVANT: BMI, Weight, Exercise (unless they mention it)
FOCUS: Sleep quality and stress are the biggest factors for mental clarity.""",
            
            "emotional": """ISSUE: EMOTIONAL (sad, anxious, overwhelmed)
RELEVANT: Mood, Sleep, Stress, Exercise
NOT RELEVANT: Water, BMI (unless relevant)
FOCUS: Be extra gentle. Sleep and exercise are proven mood boosters.""",
            
            "physical_fatigue": """ISSUE: PHYSICAL FATIGUE (lethargic, sluggish, no energy)
RELEVANT: Sleep, Exercise, Water, Energy level
FOCUS: Physical energy often comes from sleep + movement + hydration basics.""",
            
            "sleep_issues": """ISSUE: SLEEP PROBLEMS (can't sleep, insomnia)
RELEVANT: Stress, Exercise timing, Mood
NOT RELEVANT: Water, BMI
FOCUS: Stress and lack of physical activity are top sleep disruptors.""",
            
            "general_wellness": """ISSUE: GENERAL WELLNESS (feeling good, wants to optimize)
RELEVANT: All metrics for benchmarking
FOCUS: Compare their stats to clinical ideals for their age/sex."""
        }
        return contexts.get(self.issue_type, "Classify the issue type first.")

    def _is_collected(self, session: ConversationState, metric: str) -> bool:
        """Check if a specific metric has been collected."""
        c = session.current_checkin
        p = session.profile
        
        # Profile metrics
        if metric == "age": return p.age is not None
        elif metric == "sex": return p.sex is not None
        elif metric == "height_cm": return p.height_cm is not None
        elif metric == "weight_kg": return p.weight_kg is not None
        elif metric == "origin": return p.origin is not None
        elif metric == "religion": return p.religion is not None
        elif metric == "dietary_preference": return p.dietary_preference != "omnivore"
        # Check-in metrics
        elif metric == "sleep_hours": return c.sleep_hours is not None
        elif metric == "water_glasses": return c.water_glasses is not None
        elif metric == "mood_score": return c.mood_score is not None
        elif metric == "energy_score": return c.energy_score is not None
        elif metric == "stress_score": return c.stress_score is not None
        elif metric == "exercise_minutes": return c.exercise_minutes is not None
        elif metric == "exercise_type": return c.exercise_type is not None
        elif metric == "social_hours": return c.social_hours is not None
        elif metric == "alcohol_units": return c.alcohol_units is not None
        elif metric == "smoking_today": return c.smoking_today is not None
        return False
    
    def _get_collected(self, session: ConversationState) -> str:
        """Return what we've already collected."""
        c = session.current_checkin
        p = session.profile
        parts = []
        
        # Profile data
        if p.age is not None: parts.append(f"age: {p.age}y")
        if p.sex is not None: parts.append(f"sex: {p.sex}")
        if p.height_cm is not None: parts.append(f"height: {p.height_cm}cm")
        if p.weight_kg is not None: parts.append(f"weight: {p.weight_kg}kg")
        if p.origin is not None: parts.append(f"origin: {p.origin}")
        if p.religion is not None: parts.append(f"religion: {p.religion}")
        
        # Check-in data
        if c.sleep_hours is not None: parts.append(f"sleep: {c.sleep_hours}h")
        if c.water_glasses is not None: parts.append(f"water: {c.water_glasses} glasses")
        if c.mood_score is not None: parts.append(f"mood: {c.mood_score}/5")
        if c.energy_score is not None: parts.append(f"energy: {c.energy_score}/5")
        if c.stress_score is not None: parts.append(f"stress: {c.stress_score}/10")
        if c.exercise_minutes is not None: parts.append(f"exercise: {c.exercise_minutes}min")
        if c.social_hours is not None: parts.append(f"social: {c.social_hours}h")
        if c.alcohol_units is not None: parts.append(f"alcohol: {c.alcohol_units} units")
        if c.smoking_today is not None: parts.append(f"smoking: {'yes' if c.smoking_today else 'no'}")
        
        return ", ".join(parts) if parts else "Nothing yet"

    def _apply_updates(self, session: ConversationState, updates: Dict[str, Any]):
        """Apply extracted values with validation and logging."""
        c = session.current_checkin
        
        # Sleep Hours (1-12 expected)
        if updates.get("sleep_hours") is not None:
            val = self._parse_float(updates["sleep_hours"])
            if val is not None and 1 <= val <= 12:
                c.sleep_hours = val
                logger.debug(f"✓ Collected sleep_hours: {val}h")
            elif val is None:
                logger.warning(f"✗ Failed to parse sleep_hours: '{updates.get('sleep_hours')}'")
            else:
                logger.warning(f"✗ Out of range sleep_hours: {val}h (expected 1-12)")
                
        # Water Glasses (0-20 expected)
        if updates.get("water_glasses") is not None:
            val = self._parse_int(updates["water_glasses"])
            if val is not None and 0 <= val <= 20:
                c.water_glasses = val
                logger.debug(f"✓ Collected water_glasses: {val}")
            elif val is None:
                logger.warning(f"✗ Failed to parse water_glasses: '{updates.get('water_glasses')}'")
            else:
                logger.warning(f"✗ Out of range water_glasses: {val} (expected 0-20)")
                
        # Mood Score (1-5 expected)
        if updates.get("mood_score") is not None:
            val = self._parse_int(updates["mood_score"])
            if val is not None and 1 <= val <= 5:
                c.mood_score = val
                logger.debug(f"✓ Collected mood_score: {val}/5")
            elif val is None:
                logger.warning(f"✗ Failed to parse mood_score: '{updates.get('mood_score')}'")
            else:
                logger.warning(f"✗ Out of range mood_score: {val} (expected 1-5)")
                
        if updates.get("energy_score") is not None:
            val = self._parse_int(updates["energy_score"])
            if val is not None and 1 <= val <= 5:
                c.energy_score = val
            elif val is None:
                logger.warning(f"Failed to parse energy_score: {updates.get('energy_score')}")
                
        # Stress Score (1-10 expected)
        if updates.get("stress_score") is not None:
            val = self._parse_int(updates["stress_score"])
            if val is not None and 1 <= val <= 10:
                c.stress_score = val
                logger.debug(f"✓ Collected stress_score: {val}/10")
            elif val is None:
                logger.warning(f"✗ Failed to parse stress_score: '{updates.get('stress_score')}'")
            else:
                logger.warning(f"✗ Out of range stress_score: {val} (expected 1-10)")
                
        if updates.get("exercise_minutes") is not None:
            val = self._parse_int(updates["exercise_minutes"])
            if val is not None and 0 <= val <= 300:
                c.exercise_minutes = val
        
        # New Pillar 3: Exercise Type
        if updates.get("exercise_type") is not None:
            val = str(updates["exercise_type"]).lower().strip()
            if val in ["cardio", "strength", "both", "none"]:
                c.exercise_type = val
        
        # Pillar 5: Social Connection
        if updates.get("social_hours") is not None:
            val = self._parse_float(updates["social_hours"])
            if val is not None and 0 <= val <= 24:
                c.social_hours = val
        
        # Pillar 6: Toxin Avoidance
        if updates.get("alcohol_units") is not None:
            val = self._parse_int(updates["alcohol_units"])
            if val is not None and 0 <= val <= 20:
                c.alcohol_units = val
                
        if updates.get("smoking_today") is not None:
            val = updates["smoking_today"]
            if isinstance(val, bool):
                c.smoking_today = val
            elif str(val).lower() in ["yes", "true", "1"]:
                c.smoking_today = True
            elif str(val).lower() in ["no", "false", "0"]:
                c.smoking_today = False
        
        # Profile Data (Critical for BMI/BMR calculations)
        if updates.get("age") is not None:
            val = self._parse_int(updates["age"])
            if val is not None and 10 <= val <= 120:
                session.profile.age = val
        
        if updates.get("sex") is not None:
            val = str(updates["sex"]).lower().strip()
            # Handle various formats: male/Male/M/m, female/Female/F/f
            if val in ["male", "m", "man"]:
                session.profile.sex = "male"
            elif val in ["female", "f", "woman"]:
                session.profile.sex = "female"
        
        if updates.get("height_cm") is not None:
            val = self._parse_float(updates["height_cm"])
            if val is not None and 100 <= val <= 250:
                session.profile.height_cm = val
        
        if updates.get("weight_kg") is not None:
            val = self._parse_float(updates["weight_kg"])
            if val is not None and 30 <= val <= 300:
                session.profile.weight_kg = val
        
        # Cultural Context (for NutritionAgent)
        if updates.get("origin") is not None:
            session.profile.origin = str(updates["origin"]).strip()
        
        if updates.get("religion") is not None:
            session.profile.religion = str(updates["religion"]).strip()
        
        # Dietary Preference (for NutritionAgent)
        if updates.get("dietary_preference") is not None:
            val = str(updates["dietary_preference"]).lower().strip()
            if val in ["vegetarian", "vegan", "pescatarian", "omnivore"]:
                session.profile.dietary_preference = val

    def _parse_int(self, value: Any) -> Optional[int]:
        """Robust int parsing: handles '5-6' (avg), '8/10' (numerator), '8 out of 10' (numerator), '4 or 5' (avg)."""
        try:
            s = str(value).lower().strip()
            
            # Handle "8 out of 10" → extract first number
            if " out of " in s:
                s = s.split(" out of ")[0].strip()
            
            # Handle "4 or 5" → take average
            if " or " in s:
                parts = s.split(" or ")
                try:
                    nums = [self._extract_first_number(p) for p in parts]
                    nums = [n for n in nums if n is not None]
                    if nums:
                        return int(round(sum(nums) / len(nums)))
                except (ValueError, ZeroDivisionError):
                    pass
            
            # Handle "8/10" → extract numerator (first number)
            if "/" in s:
                s = s.split("/")[0].strip()
            
            # Handle "5-6" → average
            if "-" in s and not s.startswith("-"):
                parts = s.split("-")
                try:
                    nums = [float(p.strip()) for p in parts if p.strip().replace(".", "").isdigit()]
                    if nums:
                        return int(round(sum(nums) / len(nums)))
                except (ValueError, ZeroDivisionError):
                    pass
            
            # Extract first number from string
            match = re.search(r"\d+\.?\d*", s)
            if match:
                return int(round(float(match.group())))
            
            return None
        except (ValueError, AttributeError, TypeError):
            return None
    
    def _extract_first_number(self, text: str) -> Optional[float]:
        """Extract the first number from a string."""
        match = re.search(r"\d+\.?\d*", text)
        return float(match.group()) if match else None

    def _parse_float(self, value: Any) -> Optional[float]:
        """Robust float parsing for decimals and ranges."""
        try:
            s = str(value).lower().strip()
            
            # Handle "X out of Y" → extract first number
            if " out of " in s:
                s = s.split(" out of ")[0].strip()
            
            # Handle "X or Y" → average
            if " or " in s:
                parts = s.split(" or ")
                try:
                    nums = [self._extract_first_number(p) for p in parts]
                    nums = [n for n in nums if n is not None]
                    if nums:
                        return sum(nums) / len(nums)
                except (ValueError, ZeroDivisionError):
                    pass
            
            # Handle "X-Y" range → average
            if "-" in s and not s.startswith("-"):
                parts = s.split("-")
                try:
                    nums = [float(p.strip()) for p in parts if p.strip().replace(".", "").isdigit()]
                    if nums:
                        return sum(nums) / len(nums)
                except (ValueError, ZeroDivisionError):
                    pass
            
            # Extract first number
            match = re.search(r"\d+\.?\d*", s)
            return float(match.group()) if match else None
        except (ValueError, AttributeError, TypeError, ZeroDivisionError):
            return None

    def _fallback(self, session: ConversationState) -> Dict[str, Any]:
        """Human-sounding fallback when LLM fails."""
        turn = len([m for m in session.history if m['role'] == 'user'])
        
        # Early turns: just chat -> ask specific questions
        if turn <= 2:
            replies = [
                "I hear you. To help you best, how many hours of sleep did you get last night?",
                "That sounds tough. Let's check your basics. How is your energy level right now (1-5)?",
                "Got it. Quick check: How much water have you had today?"
            ]
            import random
            return {"status": "CONTINUE", "reply": random.choice(replies), "extracted_updates": {}}
        
        # Later: gently ask about health
        missing = session.current_checkin.missing_fields
        if not missing:
            return {"status": "COMPLETE", "reply": None, "extracted_updates": {}}
        
        # Natural questions for each metric
        questions = {
            "sleep_hours": "How'd you sleep last night?",
            "water_glasses": "Have you been drinking enough water today?",
            "mood_score": "How are you feeling overall?",
            "energy_score": "Energy levels holding up?",
            "stress_score": "Stress been manageable lately?",
            "exercise_minutes": "Get any movement in today?"
        }
        
        import random
        field = random.choice(missing)
        return {
            "status": "CONTINUE",
            "reply": questions.get(field, "How are things going?"),
            "extracted_updates": {}
        }