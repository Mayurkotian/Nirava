"""PlannerAgent - Energy-Adaptive Action Planning

Capstone Concepts Demonstrated:
- LLM-Powered Agent (Gemini 2.0 Flash)
- ReAct Pattern (Reason + Act)
- Structured JSON Output
- Energy-Adaptive Recommendations

This agent converts high-level health insights into 2-3 concrete,
micro-habit actions the user can do TODAY, scaled to their current energy.

Design Decisions:
    1. BJ Fogg's Tiny Habits: Actions are small, specific, and achievable
    2. Energy Scaling: Low energy = ultra-gentle tasks, High energy = challenges
    3. Time-Aware: Morning actions differ from evening actions
    4. Specificity: "Take a 5-min walk after lunch" not "Exercise more"

Prompt Engineering:
    - ReAct Pattern: Explicit Thought → Observation → Action structure
    - Few-Shot Examples: 5 examples across different energy levels
    - JSON Mode: Structured output with action + reasoning
"""
from typing import Dict, Any, List
import json
import logging
from config.llm import get_gemini_model

logger = logging.getLogger(__name__)


class PlannerAgent:
    """
    PLANNER AGENT: Converts health insights into actionable micro-habits.
    
    KEY CONCEPT: REACT PATTERN (Reason + Act)
    - Thought: Analyzes user's capacity (energy, mood, stress)
    - Observation: Identifies key problems from MetricsAgent scores
    - Action: Generates specific, achievable micro-habits
    
    DESIGN DECISIONS:
    1. Energy-Adaptive Scaling: Actions match user's current capacity
       - Energy 1-2 (FLOOR_HABITS): "Drink water from nightstand" (zero-effort)
       - Energy 3 (MODERATE_HABITS): "10-min walk after lunch" (habit stacking)
       - Energy 4-5 (GROWTH_HABITS): "20-min HIIT workout" (challenge them!)
    2. BJ Fogg's Tiny Habits Framework:
       - Habit Stacking: "After [existing routine], I will [new habit]"
       - 2-Minute Rule: Every action takes <2 minutes to start
       - Environment Design: Change surroundings to reduce friction
    3. 6-Pillar Coverage Analysis: Tracks which health pillars are addressed
    
    PROMPT ENGINEERING TECHNIQUES:
    - ReAct Pattern: Explicit Thought → Observation → Action structure
    - Few-Shot Examples: 5 examples across different energy levels
    - JSON Mode: Structured output with action + reasoning + technique
    
    FALLBACK STRATEGY:
    If LLM fails, returns safe default actions ("Drink water", "Take a short walk").
    """

    def __init__(self):
        self.model = get_gemini_model()

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        insights = context.get("insights", [])
        checkin = context.get("checkin", {})
        profile = context.get("profile", {})
        metrics = context.get("metrics", {})  # NEW: MetricsAgent scores
        sources = context.get("sources", [])  # NEW: ResearchAgent sources
        issue_type = context.get("issue_type", "general_wellness")  # NEW: Issue awareness

        if not self.model:
            return self._fallback_run(context)

        prompt = self._build_prompt(profile, checkin, insights, metrics, sources, issue_type)

        try:
            response = self.model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            
            # Clean up potential markdown formatting
            response_text = response.text.replace("```json", "").replace("```", "").strip()
            result = json.loads(response_text)
            
            # Handle new structured output format
            raw_actions = result.get("actions", [])
            reasoning = result.get("reasoning", "")
            
            # Extract action strings from structured format
            actions = []
            for item in raw_actions:
                if isinstance(item, dict):
                    actions.append(item.get("action", str(item)))
                else:
                    actions.append(str(item))
            
            # Fallback for empty list
            if not actions:
                actions = ["Take a 5-minute break to stretch and breathe."]

            # Analyze pillar coverage for logging
            pillar_coverage = self._analyze_pillar_coverage(raw_actions, metrics)

            context["plan"] = {
                "actions": actions,
                "reasoning": reasoning,
                "detailed_actions": raw_actions,  # Keep full structure for UI
                "pillar_coverage": pillar_coverage  # NEW: Track which pillars addressed
            }
            
            # Enhanced logging
            logger.info(f"PlannerAgent: {len(actions)} micro-actions generated for issue: {issue_type}")
            logger.info(f"Pillar coverage: {pillar_coverage}")
            if reasoning:
                logger.debug(f"PlannerAgent reasoning: {reasoning}")

        except Exception as e:
            logger.error(f"PlannerAgent error: {e}", exc_info=True)
            return self._fallback_run(context)

        return context

    def _build_prompt(self, profile, checkin, insights, metrics, sources, issue_type) -> str:
        # Handle None values with safe defaults
        mood = checkin.get('mood') or checkin.get('mood_score') or 3
        energy = checkin.get('energy_level') or checkin.get('energy_score') or 3
        stress = checkin.get('stress_score') or 5
        
        # Extract advanced MetricsAgent scores for targeted actions
        sleep_quality = metrics.get('sleep_quality_score')
        sleep_debt = metrics.get('sleep_debt_hours')
        burnout_risk = metrics.get('burnout_risk_score')
        stress_load = metrics.get('stress_load_index')
        mental_resilience = metrics.get('mental_resilience_score')
        dehydration_risk = metrics.get('dehydration_risk')
        sedentary_risk = metrics.get('sedentary_risk_score')
        social_wellness = metrics.get('social_wellness_score')
        loneliness_risk = metrics.get('loneliness_risk')
        toxin_load = metrics.get('toxin_load_score')
        
        # Determine action intensity
        if energy <= 2:
            intensity = "FLOOR_HABITS"
            intensity_desc = "Zero-effort actions they can do lying down"
        elif energy <= 3:
            intensity = "MODERATE_HABITS"
            intensity_desc = "Light effort with habit stacking"
        else:
            intensity = "GROWTH_HABITS"
            intensity_desc = "Challenging actions for high-capacity days"
        
        return f"""You are a Behavioral Health Strategist using BJ Fogg's 'Tiny Habits' method.

=== REACT-STYLE REASONING (Think → Act) ===

**THOUGHT 1: Assess Capacity**
User's Energy: {energy}/5 → Intensity Level: {intensity}
User's Mood: {mood}/5 → Tone: {'Gentle, no pressure' if mood <= 2 else 'Encouraging' if mood <= 4 else 'Challenge them!'}
User's Stress: {stress}/10 → {'Add calming action' if stress >= 7 else 'Standard actions OK'}

**THOUGHT 2: Extract Key Problems from Insights**
Read the insights and identify the #1 problem to solve:
{json.dumps(insights, indent=2)}

**THOUGHT 3: Match Action to Problem**
For each problem, select the SMALLEST action that addresses it.
- If sleep is the issue → Action targets sleep hygiene
- If hydration is the issue → Action targets water intake
- If stress is the issue → Action targets relaxation
- If social isolation detected → Action targets connection ("Text one friend")
- If alcohol/smoking detected → Action targets harm reduction ("Try one alcohol-free day")

**THOUGHT 4: Apply Behavior Design Principles**
- **Habit Stacking**: "After [existing routine], I will [new habit]"
- **Environment Design**: Change surroundings to make action easier
- **Subtraction**: Remove friction, not add complexity
- **2-Minute Rule**: Every action should take <2 minutes to start

=== ACTION INTENSITY GUIDE ===

[{intensity}: {intensity_desc}]

FLOOR_HABITS (Energy 1-2):
✓ "Drink water from the glass on your nightstand"
✓ "Take 3 deep breaths before getting out of bed"
✓ "Set phone to Do Not Disturb at 9pm"
✗ NOT: "Go for a 30-minute run"

MODERATE_HABITS (Energy 3):
✓ "After lunch, take a 10-minute walk around the block"
✓ "Fill a water bottle and keep it visible on your desk"
✓ "After brushing teeth, write 1 thing you're grateful for"
✗ NOT: "Meditate for 30 minutes"

GROWTH_HABITS (Energy 4-5):
✓ "Do a 20-minute HIIT workout before your shower"
✓ "Meal prep lunches for the next 3 days"
✓ "Read one chapter of a challenging book"
✗ NOT: "Just relax" (they have capacity - challenge them!)

=== USER CONTEXT ===
- Name: {profile.get('name', 'Friend')}
- Goal: {profile.get('primary_goal')}
- Capacity: {intensity}

=== YOUR OUTPUT ===
For each action, explain WHY it addresses the insight.

OUTPUT JSON:
{{
  "reasoning": "The main issue is [X], so I'm prioritizing actions that [Y]",
  "actions": [
    {{
      "action": "After [trigger], [specific tiny action]",
      "addresses": "Which insight this solves",
      "technique": "Habit Stacking | Environment Design | Subtraction | 2-Minute Rule"
    }},
    {{
      "action": "...",
      "addresses": "...",
      "technique": "..."
    }},
    {{
      "action": "...",
      "addresses": "...",
      "technique": "..."
    }}
  ]
}}"""

    def _analyze_pillar_coverage(self, raw_actions: List, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze which health pillars are addressed by the generated actions."""
        pillars_addressed = set()
        pillar_actions = {
            "Sleep": [],
            "Hydration": [],
            "Movement": [],
            "Mental Health": [],
            "Social Connection": [],
            "Toxin Avoidance": []
        }
        
        for action in raw_actions:
            if isinstance(action, dict):
                pillar = action.get("pillar", "")
                if pillar in pillar_actions:
                    pillars_addressed.add(pillar)
                    pillar_actions[pillar].append(action.get("action", ""))
        
        # Identify gaps based on metrics
        critical_gaps = []
        if metrics.get("sleep_quality_score") and metrics["sleep_quality_score"] < 6 and "Sleep" not in pillars_addressed:
            critical_gaps.append("Sleep")
        if metrics.get("dehydration_risk") in ["moderate", "high"] and "Hydration" not in pillars_addressed:
            critical_gaps.append("Hydration")
        if metrics.get("sedentary_risk_score") and metrics["sedentary_risk_score"] > 6 and "Movement" not in pillars_addressed:
            critical_gaps.append("Movement")
        if metrics.get("burnout_risk_score") and metrics["burnout_risk_score"] > 7 and "Mental Health" not in pillars_addressed:
            critical_gaps.append("Mental Health")
        if metrics.get("social_wellness_score") and metrics["social_wellness_score"] < 4 and "Social Connection" not in pillars_addressed:
            critical_gaps.append("Social Connection")
        if metrics.get("toxin_load_score") and metrics["toxin_load_score"] > 5 and "Toxin Avoidance" not in pillars_addressed:
            critical_gaps.append("Toxin Avoidance")
        
        return {
            "pillars_addressed": list(pillars_addressed),
            "pillar_count": len(pillars_addressed),
            "critical_gaps": critical_gaps,
            "pillar_actions": {k: v for k, v in pillar_actions.items() if v}
        }

    def _fallback_run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Simple rule-based fallback."""
        actions = ["Drink a glass of water.", "Take a short walk."]
        context["plan"] = {"actions": actions, "pillar_coverage": {"pillars_addressed": [], "pillar_count": 0, "critical_gaps": [], "pillar_actions": {}}}
        return context
