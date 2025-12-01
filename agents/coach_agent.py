"""CoachAgent - Empathetic Health Response Synthesis

Capstone Concepts Demonstrated:
- LLM-Powered Agent (Gemini 2.0 Flash)
- Self-Reflection Prompting
- Source Attribution (Day 4)
- Tone Calibration

This agent produces the final conversational response, synthesizing data from
all previous agents into a warm, human-like message that feels personal.

Design Decisions:
    1. Self-Reflection: Before responding, agent considers tone appropriateness
    2. Dynamic Empathy: Matches response tone to user's emotional state
    3. Time-Aware Greetings: Morning/afternoon/evening appropriate
    4. Source Display: Shows verified citations from Google Search
    5. No Medical Advice: Explicitly avoids diagnosis or medication suggestions

Prompt Engineering:
    - Self-Reflection Block: Pre-response checks for emotional intelligence
    - Tone Matching: Gentle for low mood, celebratory for high mood
    - Structured Input: Receives metrics, insights, actions from prior agents
    - Safety Constraints: Hard-coded refusals for medical claims
"""
from typing import Dict, Any, List
import json
import logging
import datetime
from config.llm import get_gemini_model

logger = logging.getLogger(__name__)


class CoachAgent:
    """
    CoachAgent - The empathetic voice of Nirava.
    
    Synthesizes all pipeline outputs into a cohesive, caring response.
    Uses self-reflection prompting to ensure appropriate tone and
    displays verified sources for transparency.
    
    Day 4 Features:
    - Displays grounded sources from Google Search
    - Safety-aware messaging for concerning symptoms
    """

    def __init__(self):
        self.model = get_gemini_model()

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        metrics = context.get("metrics", {})
        insights = context.get("insights", [])
        plan = context.get("plan", {})
        actions = plan.get("detailed_actions", [])  # NEW: Use detailed actions
        if not actions:
            actions = plan.get("actions", [])
            
        profile = context.get("profile", {})
        checkin = context.get("checkin", {})
        sources = context.get("sources", [])  # Day 4: Grounded sources
        meal_plan = context.get("meal_plan")  # From NutritionAgent (if available)

        # Fallback if model isn't configured (e.g. missing API key)
        if not self.model:
            return self._fallback_run(context)

        # Construct the prompt with sources and meal plan
        prompt = self._build_prompt(profile, checkin, metrics, insights, actions, sources, meal_plan)

        try:
            # Call Gemini
            response = self.model.generate_content(prompt)
            response_text = response.text
            
            # Basic cleanup
            response_text = response_text.replace("```", "").replace("json", "").strip()
            
            context["response"] = response_text
            
            # Enhanced Logging
            debug_log = context.setdefault("debug", [])
            debug_log.append("CoachAgent: AI response generated via Gemini.")
            logger.info("CoachAgent: Generated synthesized response")
            
        except Exception as e:
            logger.error(f"Gemini generation failed: {e}", exc_info=True)
            debug_log = context.setdefault("debug", [])
            debug_log.append(f"CoachAgent: Gemini failed ({e}), using fallback.")
            return self._fallback_run(context)

        return context

    def _build_prompt(self, profile, checkin, metrics, insights, actions, sources=None, meal_plan=None) -> str:
        """
        Constructs the system-like prompt for the Coach.
        Day 4: Now includes grounded sources for citation.
        Includes meal plan if NutritionAgent was run.
        """
        sources = sources or []
        user_name = profile.get("name", "Friend")
        
        # Time Context
        current_hour = datetime.datetime.now().hour
        if 5 <= current_hour < 12:
            time_of_day = "Morning"
        elif 12 <= current_hour < 17:
            time_of_day = "Afternoon"
        else:
            time_of_day = "Evening"

        # Helper for safe display
        def fmt(val, suffix=""):
             return f"{val}{suffix}" if val is not None else "N/A"
             
        # Basic Metrics
        sleep_disp = fmt(checkin.get('sleep_hours'), 'h')
        water_disp = fmt(checkin.get('water_glasses'), ' gls')
        stress_disp = fmt(checkin.get('stress_score'), '/10')
        move_disp = fmt(checkin.get('exercise_minutes'), ' mins')
        mood_disp = fmt(checkin.get('mood'), '/5')
        
        # Advanced Metrics (Pillar Scores)
        sleep_quality = metrics.get('sleep_quality_score')
        burnout_risk = metrics.get('burnout_risk_score')
        social_wellness = metrics.get('social_wellness_score')
        toxin_load = metrics.get('toxin_load_score')
        dehydration_risk = metrics.get('dehydration_risk')
        sedentary_risk = metrics.get('sedentary_risk_score')
        
        # Handle None values with safe defaults
        mood_val = checkin.get('mood') or checkin.get('mood_score') or 3
        
        # Day 4: Format grounded sources for display
        sources_section = ""
        if sources:
            source_lines = []
            seen_titles = set()  # Deduplicate
            idx = 1
            for s in sources[:5]:  # Top 5 sources max
                title = s.get('title', 'Source')
                uri = s.get('uri', '')
                if title not in seen_titles and uri:
                    source_lines.append(f"[{idx}] {title}: {uri}")
                    seen_titles.add(title)
                    idx += 1
            if source_lines:
                sources_section = "VERIFIED SOURCES:\n" + "\n".join(source_lines)

        # Determine emotional state for tone calibration
        stress_val = checkin.get('stress_score') or 5
        
        # Dynamic Empathy Logic
        high_burnout = burnout_risk is not None and burnout_risk > 7
        high_loneliness = social_wellness is not None and social_wellness < 4
        
        is_struggling = mood_val <= 2 or stress_val >= 7 or high_burnout
        is_thriving = mood_val >= 4 and stress_val <= 3 and not high_burnout
        
        return f"""
You are Nirava, a premium health companion with emotional intelligence.

=== SELF-REFLECTION BEFORE RESPONDING ===

**CHECK 1: Emotional State**
- Mood: {mood_val}/5, Stress: {stress_val}/10
- Burnout Risk: {fmt(burnout_risk)}/10
- User is: {'STRUGGLING - Be extra gentle' if is_struggling else 'THRIVING - Celebrate!' if is_thriving else 'NEUTRAL - Be warm and helpful'}
- My tone should be: {'Soft, no exclamation marks, validating' if is_struggling else 'Energetic, celebratory!' if is_thriving else 'Warm and encouraging'}

**CHECK 2: What matters most right now?**
- If they're struggling: Lead with empathy, not data. Validate their feelings first.
- If they're thriving: Lead with celebration, then optimize.
- If Burnout is HIGH: Focus on REST, not achievement.
- If Loneliness is HIGH: Focus on CONNECTION, not tasks.

**CHECK 3: Is my response too clinical?**
- Avoid: "Your metrics indicate..." (sounds robotic)
- Prefer: "I noticed you only got 5h of sleep..." (sounds caring)

**CHECK 4: EDUCATION & CLARITY (ELI5)**
- If I use a medical term (e.g., Cortisol, Adenosine, BDNF, Ghrelin), I MUST explain it immediately in simple terms.
- Example: "High stress spikes cortisol (the hormone that keeps you awake)."

**CHECK 5: SCOPE ADHERENCE**
- I only solve problems I can measure: Sleep, Hydration, Stress, Energy, Movement.
- I do NOT speculate on rashes, pains, or complex diseases.
- If the insight touches on complex medicine, I soften it: "Research suggests..." and refer to a doctor.

=== CONTEXT ===
- User: {user_name}, {profile.get('age')}y
- Goal: {profile.get('primary_goal')}
- Time: {time_of_day}

=== 6-PILLAR HEALTH DASHBOARD ===
1. 🌙 Sleep: {sleep_disp} (Quality Score: {fmt(sleep_quality)}/10)
2. 💧 Hydration: {water_disp} (Risk: {fmt(dehydration_risk)})
3. 🏃 Movement: {move_disp} (Sedentary Risk: {fmt(sedentary_risk)}/10)
4. 🧠 Mental: Stress {stress_disp} (Burnout Risk: {fmt(burnout_risk)}/10)
5. 🤝 Social: Wellness {fmt(social_wellness)}/10
6. 🛡️ Toxins: Load {fmt(toxin_load)}/10

=== INSIGHTS (The "Why") ===
{json.dumps(insights, indent=2)}

=== PLAN (The "How") ===
{json.dumps(actions, indent=2)}

{self._format_meal_plan(meal_plan) if meal_plan else ""}

{sources_section}

=== OUTPUT FORMAT ===

**SECTION 1: Personalized Greeting**
- Match {time_of_day} + Mood {mood_val}/5
- If struggling: "Hey... I see you're having a tough time."
- If thriving: "Good {time_of_day.lower()}! You're crushing it!"
- If neutral: "Good {time_of_day.lower()}, {user_name}."

**SECTION 2: The Snapshot**
Use the emoji format above to show their data. Keep it scannable.

**SECTION 3: Key Insight (ELI5 Style)**
Pick the #1 most impactful insight.
- Start with their data, connect to the mechanism, explain the impact.
- **CRITICAL:** Explain any technical terms simply (ELI5).
- Keep it to 2-3 sentences max.
- Cite sources if relevant (e.g., [1]).

**SECTION 4: Your Micro-Actions**
List 2-3 actions with checkboxes [ ].
- Show which PILLAR each action addresses.
- Example: "[ ] Set phone to DND at 9pm (Sleep)"

**SECTION 5: Your Meal Plan** (if provided)
If a meal plan is available, display it in a clean format:
- Show daily calorie target and macros
- List each meal with time, foods, and calories
- Keep it scannable (use emojis: 🍳 Breakfast, 🥗 Lunch, 🍽️ Dinner, 🍎 Snack)

**SECTION 6: Sources** (if available)
List sources matching [1], [2] format.

**SECTION 7: Closing**
- Brief encouragement matching their state
- Footer: "I'm an AI companion specializing in sleep, stress, and metabolic health. For other medical concerns, please consult a healthcare provider."

=== FINAL CHECK ===
✓ Does my greeting match their mood?
✓ Did I acknowledge high burnout/loneliness if present?
✓ Did I explain jargon simply?
✓ Does my tone feel human, not clinical?
"""

    def _format_meal_plan(self, meal_plan: Dict[str, Any]) -> str:
        """Format meal plan for inclusion in prompt."""
        if not meal_plan:
            return ""
        
        meals = meal_plan.get("meals", [])
        if not meals:
            return ""
        
        formatted = "=== MEAL PLAN (From NutritionAgent) ===\n"
        formatted += f"Daily Target: {meal_plan.get('daily_calories', 'N/A')} kcal\n"
        macros = meal_plan.get("macros", {})
        formatted += f"Macros: Protein {macros.get('protein_g', 0)}g | Carbs {macros.get('carbs_g', 0)}g | Fats {macros.get('fats_g', 0)}g\n\n"
        
        for meal in meals:
            formatted += f"{meal.get('name', 'Meal')} ({meal.get('time', 'N/A')}):\n"
            formatted += f"  Foods: {', '.join(meal.get('foods', []))}\n"
            formatted += f"  Calories: {meal.get('calories', 0)} kcal | Protein: {meal.get('protein_g', 0)}g\n\n"
        
        if meal_plan.get("notes"):
            formatted += f"Notes: {meal_plan['notes']}\n"
        
        return formatted

    def _fallback_run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        The original rule-based logic, kept as a fallback if API fails.
        """
        # ... (Previous logic could go here, or a simple static message)
        context["response"] = (
            "Thanks for checking in! I'm having trouble connecting to my AI brain right now, "
            "but please keep hydrated and try to get good sleep tonight! "
            "(Error: API Key missing or Connection failed)"
        )
        return context
