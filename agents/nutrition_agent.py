"""NutritionAgent - Personalized Meal Planning

Capstone Concepts Demonstrated:
- LLM-Powered Agent (Gemini 2.0 Flash)
- Structured JSON Output
- Few-Shot Prompting for meal planning
- Conditional Agent (only runs for "Build a Plan" journey)

This agent creates personalized meal plans based on:
- TDEE (from MetricsAgent)
- Dietary preferences (vegetarian, vegan, pescatarian, omnivore)
- Weight goals (lose, gain, maintain)
- Food restrictions (gluten-free, lactose-intolerant, etc.)

Design Decisions:
    1. Runs AFTER MetricsAgent (needs TDEE) and PlannerAgent (aligns timing)
    2. Only activates for Journey Mode = "Build a Plan"
    3. Respects dietary restrictions strictly
    4. Provides macro split (protein/carbs/fats) for transparency
    5. Includes meal timing recommendations

Prompt Engineering:
    - Few-Shot Examples for different dietary preferences
    - Structured JSON output with meal breakdown
    - Calorie and macro calculations
"""
from typing import Dict, Any, List
import json
import logging
from config.llm import get_gemini_model

logger = logging.getLogger(__name__)


class NutritionAgent:
    """Creates personalized meal plans based on metabolic needs and dietary preferences."""

    def __init__(self):
        self.model = get_gemini_model()

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a personalized meal plan."""
        if not self.model:
            return self._fallback(context)
        
        # Check if we have the required data
        metrics = context.get("metrics", {})
        profile = context.get("profile", {})
        sources = context.get("sources", [])  # NEW: Research sources
        issue_type = context.get("issue_type", "general_wellness")  # NEW: Issue awareness
        
        if not metrics.get("tdee"):
            logger.warning("NutritionAgent: No TDEE available, skipping meal plan")
            return context
        
        prompt = self._build_prompt(context, metrics, sources, issue_type)
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            text = response.text.replace("```json", "").replace("```", "").strip()
            result = json.loads(text)
            
            meal_plan = result.get("meal_plan", {})
            context["meal_plan"] = meal_plan
            
            # Log meal plan details
            logger.info(f"NutritionAgent: Generated meal plan for {profile.get('dietary_preference', 'omnivore')} ({issue_type})")
            logger.debug(f"Meal plan details: {len(meal_plan.get('meals', []))} meals, {meal_plan.get('daily_calories')} kcal")
            
        except Exception as e:
            logger.error(f"NutritionAgent error: {e}", exc_info=True)
            return self._fallback(context)
        
        return context

    def _build_prompt(self, context: Dict[str, Any], metrics: Dict[str, Any], sources: List[Dict[str, Any]], issue_type: str) -> str:
        """Build nutrition-specific prompt."""
        
        profile = context.get("profile", {})
        
        # Extract key data
        tdee = metrics.get("tdee", 2000)
        bmr = metrics.get("bmr", 1600)
        current_weight = profile.get("weight_kg", 70)
        target_weight = profile.get("target_weight_kg")
        dietary_pref = profile.get("dietary_preference", "omnivore").lower()
        restrictions = profile.get("food_restrictions", [])
        age = profile.get("age", 30)
        sex = profile.get("sex", "unknown")
        origin = profile.get("origin", "unknown")  # NEW: Origin for cultural context
        religion = profile.get("religion", "unknown") # NEW: Religion for dietary laws
        
        # Advanced Metrics for Health Targeting
        liver_stress = metrics.get("liver_stress_indicator")
        burnout_risk = metrics.get("burnout_risk_score")
        dehydration_risk = metrics.get("dehydration_risk")
        toxin_load = metrics.get("toxin_load_score")
        
        # Determine goal
        if target_weight:
            if target_weight < current_weight:
                goal = "weight_loss"
                calorie_target = int(tdee * 0.85)  # 15% deficit
            elif target_weight > current_weight:
                goal = "weight_gain"
                calorie_target = int(tdee * 1.15)  # 15% surplus
            else:
                goal = "maintenance"
                calorie_target = int(tdee)
        else:
            goal = "maintenance"
            calorie_target = int(tdee)
        
        # Macro split (protein-focused)
        protein_g = int(current_weight * 1.6)  # 1.6g per kg (evidence-based)
        protein_cal = protein_g * 4
        fat_cal = int(calorie_target * 0.25)  # 25% from fats
        carb_cal = calorie_target - protein_cal - fat_cal
        carb_g = int(carb_cal / 4)
        fat_g = int(fat_cal / 9)
        
        restrictions_str = ", ".join(restrictions) if restrictions else "None"
        
        # Build source citations
        source_citations = ""
        if sources:
            source_citations = "\n\n=== RESEARCH SOURCES (For Citation) ===\n"
            for i, source in enumerate(sources[:3], 1):
                source_citations += f"[{i}] {source.get('title', 'Unknown')} ({source.get('domain', 'unknown')})\n"

        return f"""You are a certified nutritionist creating a personalized meal plan.

USER PROFILE:
- Age: {age}y, Sex: {sex}
- Origin/Culture: {origin} (Prioritize culturally relevant foods)
- Religion: {religion} (Strictly adhere to religious dietary laws)
- Current Weight: {current_weight}kg
- Target Weight: {target_weight or 'N/A'}kg
- Goal: {goal.upper().replace('_', ' ')}
- Dietary Preference: {dietary_pref.upper()}
- Food Restrictions: {restrictions_str}
- Health Issue: {issue_type.upper().replace('_', ' ')}

METABOLIC DATA:
- BMR: {bmr} kcal/day
- TDEE: {tdee} kcal/day
- Target Calories: {calorie_target} kcal/day

MACRO TARGETS:
- Protein: {protein_g}g ({protein_cal} kcal) — Muscle preservation
- Carbs: {carb_g}g ({carb_cal} kcal) — Energy
- Fats: {fat_g}g ({fat_cal} kcal) — Hormones

HEALTH INSIGHTS (Customize meals based on this):
- Liver Stress: {liver_stress} (If HIGH: Avoid fried foods, alcohol, processed sugar)
- Burnout Risk: {burnout_risk}/10 (If >7: Include magnesium-rich foods like spinach, almonds)
- Dehydration Risk: {dehydration_risk} (If HIGH: Include hydrating foods like cucumber, watermelon)
- Toxin Load: {toxin_load}/10 (If >5: Include antioxidants, cruciferous veggies)

=== CULTURAL & RELIGIOUS RULES (CRITICAL) ===
1. **Indian Vegetarian:** NO meat, fish, poultry. NO eggs (unless specified). Dairy is allowed (Lacto-vegetarian).
2. **Jain:** NO meat, fish, poultry, eggs. NO root vegetables (onions, garlic, potatoes).
3. **Hindu:** STRICTLY NO BEEF.
4. **Muslim (Halal):** STRICTLY NO PORK or alcohol. Meat must be Halal.
5. **Jewish (Kosher):** STRICTLY NO PORK or shellfish. Do not mix meat and dairy.
6. **Western Vegetarian:** No meat, fish, poultry. Eggs and dairy allowed.

=== MEAL PLANNING RULES ===
1. **Dietary Compliance:** Respect preference AND origin/religion.
2. **Food Restrictions:** Strictly avoid listed items.
3. **Structure:** 3 main meals + 1 snack.
4. **Nutrient Focus:**
   - If 'mental_fatigue': Focus on Omega-3s (walnuts, flax, fish)
   - If 'physical_fatigue': Focus on Iron and B-vitamins
   - If 'sleep_issues': Focus on Tryptophan (dairy, nuts) and Magnesium

{source_citations}

=== YOUR OUTPUT ===
Create a meal plan. Explain WHY specific foods were chosen (e.g., "Spinach for magnesium to help sleep [1]").

OUTPUT JSON:
{{
  "meal_plan": {{
    "daily_calories": int,
    "macros": {{"protein_g": int, "carbs_g": int, "fats_g": int}},
    "meals": [
      {{
        "name": "Breakfast",
        "time": "7:00 AM",
        "foods": ["Food 1 (Qty)", "Food 2 (Qty)"],
        "calories": int,
        "protein_g": int,
        "key_nutrients": "Vitamin/Mineral focus",
        "reasoning": "Why this meal helps their specific issue/goal (Cite source if applicable)"
      }}
    ],
    "notes": "Explanation of cultural/religious considerations and health focus"
  }}
}}"""

    def _fallback(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Smart fallback meal plan respecting dietary preference and culture."""
        metrics = context.get("metrics", {})
        tdee = metrics.get("tdee", 2000)
        profile = context.get("profile", {})
        diet_pref = profile.get("dietary_preference", "omnivore").lower()
        origin = profile.get("origin", "Western").lower()
        
        # Select template based on diet and origin
        if "indian" in origin:
            if "veg" in diet_pref or "vegan" in diet_pref:
                template = self._get_indian_veg_template(tdee)
            else:
                template = self._get_indian_nonveg_template(tdee)
        else:
            if "vegan" in diet_pref:
                template = self._get_western_vegan_template(tdee)
            elif "veg" in diet_pref:
                template = self._get_western_veg_template(tdee)
            else:
                template = self._get_western_omnivore_template(tdee)
        
        context["meal_plan"] = template
        return context

    def _get_indian_veg_template(self, tdee: int) -> Dict[str, Any]:
        return {
            "daily_calories": tdee,
            "macros": {"protein_g": 70, "carbs_g": 250, "fats_g": 60},
            "meals": [
                {"name": "Breakfast", "time": "8:00 AM", "foods": ["Poha with peanuts", "Chai (tea)"], "calories": int(tdee*0.25), "protein_g": 10},
                {"name": "Lunch", "time": "1:00 PM", "foods": ["Dal Tadka", "Roti (2)", "Sabzi (seasonal)"], "calories": int(tdee*0.35), "protein_g": 20},
                {"name": "Dinner", "time": "8:00 PM", "foods": ["Khichdi", "Curd (yogurt)"], "calories": int(tdee*0.30), "protein_g": 15},
                {"name": "Snack", "time": "4:00 PM", "foods": ["Roasted Chana", "Fruit"], "calories": int(tdee*0.10), "protein_g": 5}
            ],
            "notes": "Balanced Indian vegetarian plan focused on protein from lentils and dairy."
        }

    def _get_indian_nonveg_template(self, tdee: int) -> Dict[str, Any]:
        return {
            "daily_calories": tdee,
            "macros": {"protein_g": 100, "carbs_g": 200, "fats_g": 70},
            "meals": [
                {"name": "Breakfast", "time": "8:00 AM", "foods": ["Egg Bhurji", "Multigrain Bread"], "calories": int(tdee*0.25), "protein_g": 20},
                {"name": "Lunch", "time": "1:00 PM", "foods": ["Chicken Curry", "Rice", "Salad"], "calories": int(tdee*0.35), "protein_g": 35},
                {"name": "Dinner", "time": "8:00 PM", "foods": ["Fish Fry (shallow)", "Dal", "Roti"], "calories": int(tdee*0.30), "protein_g": 30},
                {"name": "Snack", "time": "4:00 PM", "foods": ["Sprouts Chaat"], "calories": int(tdee*0.10), "protein_g": 10}
            ],
            "notes": "High-protein Indian plan suitable for non-vegetarians."
        }

    def _get_western_vegan_template(self, tdee: int) -> Dict[str, Any]:
        return {
            "daily_calories": tdee,
            "macros": {"protein_g": 80, "carbs_g": 280, "fats_g": 60},
            "meals": [
                {"name": "Breakfast", "time": "7:30 AM", "foods": ["Oatmeal with chia seeds", "Almond milk"], "calories": int(tdee*0.25), "protein_g": 15},
                {"name": "Lunch", "time": "12:30 PM", "foods": ["Quinoa Buddha Bowl", "Tofu", "Tahini dressing"], "calories": int(tdee*0.35), "protein_g": 25},
                {"name": "Dinner", "time": "7:00 PM", "foods": ["Lentil Stew", "Sweet potato"], "calories": int(tdee*0.30), "protein_g": 20},
                {"name": "Snack", "time": "3:30 PM", "foods": ["Apple", "Walnuts"], "calories": int(tdee*0.10), "protein_g": 5}
            ],
            "notes": "Plant-based plan rich in fiber and healthy fats."
        }

    def _get_western_veg_template(self, tdee: int) -> Dict[str, Any]:
        return {
            "daily_calories": tdee,
            "macros": {"protein_g": 90, "carbs_g": 250, "fats_g": 70},
            "meals": [
                {"name": "Breakfast", "time": "7:30 AM", "foods": ["Greek Yogurt with berries", "Granola"], "calories": int(tdee*0.25), "protein_g": 20},
                {"name": "Lunch", "time": "12:30 PM", "foods": ["Spinach & Feta Salad", "Chickpeas", "Olive oil"], "calories": int(tdee*0.35), "protein_g": 25},
                {"name": "Dinner", "time": "7:00 PM", "foods": ["Whole wheat pasta", "Marinara sauce", "Mozzarella"], "calories": int(tdee*0.30), "protein_g": 20},
                {"name": "Snack", "time": "3:30 PM", "foods": ["Hard boiled egg", "Fruit"], "calories": int(tdee*0.10), "protein_g": 8}
            ],
            "notes": "Vegetarian plan including dairy and eggs for protein."
        }

    def _get_western_omnivore_template(self, tdee: int) -> Dict[str, Any]:
        return {
            "daily_calories": tdee,
            "macros": {"protein_g": 120, "carbs_g": 200, "fats_g": 80},
            "meals": [
                {"name": "Breakfast", "time": "7:30 AM", "foods": ["Scrambled Eggs (2)", "Avocado Toast"], "calories": int(tdee*0.25), "protein_g": 20},
                {"name": "Lunch", "time": "12:30 PM", "foods": ["Grilled Chicken Breast", "Brown Rice", "Broccoli"], "calories": int(tdee*0.35), "protein_g": 40},
                {"name": "Dinner", "time": "7:00 PM", "foods": ["Baked Salmon", "Asparagus", "Quinoa"], "calories": int(tdee*0.30), "protein_g": 35},
                {"name": "Snack", "time": "3:30 PM", "foods": ["Protein Shake", "Almonds"], "calories": int(tdee*0.10), "protein_g": 20}
            ],
            "notes": "Balanced high-protein omnivore plan."
        }
