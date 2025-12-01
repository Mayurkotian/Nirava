"""MetricsAgent - Health Metrics Calculation

Capstone Concepts Demonstrated:
- Custom Tools (Day 2: Function Calling)
- Deterministic computation (no LLM needed)
- Error handling with graceful fallbacks

This agent computes health snapshots using deterministic tools from health_metrics.py.
It calculates BMI, BMR, TDEE, and compares user data against clinical benchmarks.

Design Decision:
    Unlike other agents, MetricsAgent does NOT use an LLM. Health calculations
    should be precise and reproducible, not generated. This follows the principle
    of using the right tool for the job.
"""
from typing import Dict, Any, Optional
import logging

from tools.health_metrics import (
    build_standard_health_snapshot,
    get_ideal_benchmarks,
    # Pillar 1: Sleep
    calc_sleep_efficiency,
    calc_sleep_debt,
    calc_sleep_quality_score,
    # Pillar 2: Hydration
    calc_dehydration_risk,
    calc_hydration_score,
    # Pillar 3: Movement
    calc_met_score,
    estimate_vo2_max,
    calc_active_calorie_burn,
    calc_sedentary_risk_score,
    # Pillar 4: Mental Health
    calc_stress_load_index,
    calc_burnout_risk_score,
    calc_mental_resilience_score,
    # Pillar 5: Social Connection
    calc_loneliness_risk_index,
    calc_social_wellness_score,
    # Pillar 6: Toxin Avoidance
    calc_toxin_load_score,
    calc_liver_stress_indicator,
    calc_cardiovascular_toxin_impact,
)

logger = logging.getLogger(__name__)


class MetricsAgent:
    """
    MetricsAgent - Deterministic Health Calculations

    Uses the shared health_metrics tools to compute a standard health snapshot
    for the user based on their profile and today's check-in.

    This agent:
    - Calls build_standard_health_snapshot(profile, checkin).
    - Adds comparison fields to highlight gaps between current state and
      typical "healthy" ranges (for prevention and awareness).
    - Does not perform any medical diagnosis.
    - Handles missing data gracefully with sensible defaults.
    """

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Run metrics calculation with robust error handling."""
        try:
            return self._run_internal(context)
        except Exception as e:
            logger.error(f"MetricsAgent failed: {e}")
            return self._fallback(context, str(e))

    def _run_internal(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Internal run method with actual logic."""
        # Safe extraction with defaults
        profile = context.get("profile") or {}
        checkin = context.get("checkin") or {}

        snapshot = build_standard_health_snapshot(profile, checkin)
        
        # Get Clinical Ideals
        ideals = get_ideal_benchmarks(profile.get("age"), profile.get("sex"))
        snapshot["ideals"] = ideals

        # Attach some convenience fields from check-in
        sleep_hours = checkin.get("sleep_hours")
        water_glasses = checkin.get("water_glasses", 0)

        approx_water_ml_today: Optional[float] = None
        if water_glasses is not None:
            approx_water_ml_today = water_glasses * 250.0

        snapshot["sleep_hours_last_night"] = sleep_hours
        snapshot["water_glasses_today"] = water_glasses
        snapshot["approx_water_ml_today"] = approx_water_ml_today

        # Add comparison / "gap" style fields for preventive insight
        bmi = snapshot.get("bmi")
        bmi_category = snapshot.get("bmi_category")
        # For adults, "normal" is usually 18.5 to 24.9. We look at gap from 24.9.
        bmi_gap_above_normal: Optional[float] = None
        if bmi is not None and bmi_category in ("overweight", "obese"):
            bmi_gap_above_normal = round(bmi - 24.9, 1)

        snapshot["bmi_gap_above_normal"] = bmi_gap_above_normal

        # Sleep gap from the midpoint of recommended hours
        sleep_rec = snapshot.get("sleep_recommendation_hours")
        sleep_gap_midpoint: Optional[float] = None
        if sleep_hours is not None and sleep_rec is not None:
            sleep_min = sleep_rec.get("min")
            sleep_max = sleep_rec.get("max")
            if sleep_min is not None and sleep_max is not None:
                mid = (sleep_min + sleep_max) / 2.0
                sleep_gap_midpoint = round(sleep_hours - mid, 1)
        snapshot["sleep_gap_from_mid_recommendation"] = sleep_gap_midpoint

        # Hydration coverage ratio (e.g. 0.6 means 60 percent of target)
        hydration_coverage_ratio: Optional[float] = None
        daily_target_ml = snapshot.get("daily_water_target_ml")
        if approx_water_ml_today is not None and daily_target_ml:
            hydration_coverage_ratio = round(
                approx_water_ml_today / daily_target_ml, 2
            )
        snapshot["hydration_coverage_ratio"] = hydration_coverage_ratio

        # ====================================================================
        # PILLAR 1: ADVANCED SLEEP METRICS
        # ====================================================================
        sleep_hours = checkin.get("sleep_hours")
        stress_score = checkin.get("stress_score")
        alcohol_units = checkin.get("alcohol_units", 0)
        
        # Sleep Quality Score
        sleep_quality = calc_sleep_quality_score(sleep_hours, stress_score, alcohol_units)
        if sleep_quality is not None:
            snapshot["sleep_quality_score"] = sleep_quality
            if sleep_quality <= 4:
                snapshot["sleep_quality_concern"] = True
        
        # Sleep Debt
        sleep_rec = snapshot.get("sleep_recommendation_hours")
        if sleep_rec and sleep_hours is not None:
            recommended_min = sleep_rec.get("min", 7)
            sleep_debt = calc_sleep_debt(sleep_hours, recommended_min)
            if sleep_debt is not None:
                snapshot["sleep_debt_hours"] = sleep_debt
                if sleep_debt > 2:
                    snapshot["chronic_sleep_deficit"] = True
        
        # ====================================================================
        # PILLAR 2: ADVANCED HYDRATION METRICS
        # ====================================================================
        water_ml = approx_water_ml_today
        target_ml = daily_target_ml
        exercise_minutes = checkin.get("exercise_minutes", 0)
        
        # Dehydration Risk
        dehydration_risk = calc_dehydration_risk(water_ml, target_ml, exercise_minutes)
        if dehydration_risk:
            snapshot["dehydration_risk"] = dehydration_risk
            if dehydration_risk == "high":
                snapshot["dehydration_warning"] = True
        
        # Hydration Score
        target_glasses = int(target_ml / 250) if target_ml else 8
        hydration_score = calc_hydration_score(water_glasses, target_glasses)
        if hydration_score is not None:
            snapshot["hydration_score"] = hydration_score
        
        # ====================================================================
        # PILLAR 3: ADVANCED MOVEMENT METRICS
        # ====================================================================
        exercise_type = checkin.get("exercise_type")
        weight_kg = profile.get("weight_kg")
        age = profile.get("age")
        sex = profile.get("sex")
        
        # MET Score
        met_score = calc_met_score(exercise_minutes, exercise_type)
        if met_score is not None:
            snapshot["met_score"] = met_score
            snapshot["met_note"] = "Metabolic Equivalent of Task (higher = more intense)"
        
        # Active Calorie Burn
        if met_score and weight_kg:
            active_calories = calc_active_calorie_burn(exercise_minutes, met_score, weight_kg)
            if active_calories:
                snapshot["active_calories_burned"] = active_calories
        
        # VO2 Max Estimation (requires weekly exercise estimate)
        # Assume today's exercise is representative
        exercise_weekly = exercise_minutes * 7  # Rough estimate
        vo2_max = estimate_vo2_max(age, sex, exercise_weekly)
        if vo2_max is not None:
            snapshot["estimated_vo2_max"] = vo2_max
            snapshot["vo2_max_note"] = "Cardiorespiratory fitness (ml/kg/min)"
        
        # Sedentary Risk
        sedentary_risk = calc_sedentary_risk_score(exercise_minutes)
        if sedentary_risk is not None:
            snapshot["sedentary_risk_score"] = sedentary_risk
            if sedentary_risk >= 7:
                snapshot["sedentary_warning"] = True
        
        # ====================================================================
        # PILLAR 4: ADVANCED MENTAL HEALTH METRICS
        # ====================================================================
        mood_score = checkin.get("mood_score")
        energy_score = checkin.get("energy_score")
        social_hours = checkin.get("social_hours")
        
        # Stress Load Index
        stress_load = calc_stress_load_index(stress_score, sleep_hours, social_hours)
        if stress_load is not None:
            snapshot["stress_load_index"] = stress_load
            if stress_load >= 7:
                snapshot["high_stress_load"] = True
                snapshot["stress_load_note"] = "High stress load - risk of burnout"
        
        # Burnout Risk
        burnout_risk = calc_burnout_risk_score(stress_score, energy_score, mood_score, sleep_hours)
        if burnout_risk is not None:
            snapshot["burnout_risk_score"] = burnout_risk
            if burnout_risk >= 7:
                snapshot["burnout_warning"] = True
                snapshot["burnout_note"] = "High burnout risk detected - urgent self-care needed"
            elif burnout_risk >= 4:
                snapshot["burnout_note"] = "Moderate burnout risk - monitor closely"
        
        # Mental Resilience
        mental_resilience = calc_mental_resilience_score(stress_score, mood_score, social_hours, exercise_minutes)
        if mental_resilience is not None:
            snapshot["mental_resilience_score"] = mental_resilience
            if mental_resilience >= 8:
                snapshot["resilience_note"] = "Strong mental resilience"
            elif mental_resilience <= 4:
                snapshot["resilience_note"] = "Low resilience - focus on social connection and exercise"
        
        # ====================================================================
        # PILLAR 5: ADVANCED SOCIAL CONNECTION METRICS
        # ====================================================================
        
        # Loneliness Risk
        loneliness_risk = calc_loneliness_risk_index(social_hours, mood_score)
        if loneliness_risk:
            snapshot["loneliness_risk"] = loneliness_risk
            if loneliness_risk == "high":
                snapshot["social_isolation_risk"] = True
                snapshot["social_note"] = "High loneliness risk - social connection critical for health"
            elif loneliness_risk == "moderate":
                snapshot["social_note"] = "Moderate loneliness risk - consider increasing social time"
        
        # Social Wellness Score
        social_wellness = calc_social_wellness_score(social_hours, mood_score, stress_score)
        if social_wellness is not None:
            snapshot["social_wellness_score"] = social_wellness
            if social_wellness >= 8:
                snapshot["social_wellness_note"] = "Thriving socially"
            elif social_wellness <= 4:
                snapshot["social_wellness_note"] = "Social wellness concern - prioritize connection"
        
        # ====================================================================
        # PILLAR 6: ADVANCED TOXIN AVOIDANCE METRICS
        # ====================================================================
        smoking_today = checkin.get("smoking_today", False)
        
        # Toxin Load Score
        toxin_load = calc_toxin_load_score(alcohol_units, smoking_today)
        if toxin_load is not None:
            snapshot["toxin_load_score"] = toxin_load
            if toxin_load >= 6:
                snapshot["high_toxin_exposure"] = True
                snapshot["toxin_note"] = "High toxin exposure - significant health risk"
            elif toxin_load >= 3:
                snapshot["toxin_note"] = "Moderate toxin exposure - consider reduction"
        
        # Liver Stress Indicator
        bmi = snapshot.get("bmi")
        liver_stress = calc_liver_stress_indicator(alcohol_units, bmi)
        if liver_stress:
            snapshot["liver_stress_indicator"] = liver_stress
            if liver_stress == "high":
                snapshot["liver_warning"] = True
                snapshot["liver_note"] = "High liver stress - reduce alcohol and consider medical consultation"
        
        # Cardiovascular Toxin Impact
        cv_toxin_impact = calc_cardiovascular_toxin_impact(smoking_today, alcohol_units, stress_score)
        if cv_toxin_impact is not None:
            snapshot["cardiovascular_toxin_impact"] = cv_toxin_impact
            if cv_toxin_impact >= 7:
                snapshot["cardiovascular_warning"] = True
                snapshot["cv_toxin_note"] = "High cardiovascular risk from toxins - urgent lifestyle change needed"
        
        # Legacy flags (keep for backward compatibility)
        if alcohol_units and alcohol_units > 2:
            snapshot["alcohol_warning"] = True
        if smoking_today:
            snapshot["smoking_warning"] = True

        context["metrics"] = snapshot

        debug_log = context.setdefault("debug", [])
        debug_log.append("MetricsAgent: standard health snapshot computed with comparisons.")

        return context

    def _fallback(self, context: Dict[str, Any], error: str = "") -> Dict[str, Any]:
        """Provide minimal metrics when calculation fails."""
        logger.warning(f"MetricsAgent using fallback: {error}")
        
        # Provide safe defaults so downstream agents don't crash
        context["metrics"] = {
            "bmi": None,
            "bmi_category": None,
            "bmr": None,
            "tdee": None,
            "daily_water_target_ml": 2000,  # Safe default
            "sleep_recommendation_hours": {"min": 7, "max": 9},
            "sleep_ok": None,
            "hydration_ok": None,
            "ideals": {},
            "sleep_hours_last_night": None,
            "water_glasses_today": None,
            "approx_water_ml_today": None,
            "bmi_gap_above_normal": None,
            "sleep_gap_from_mid_recommendation": None,
            "hydration_coverage_ratio": None,
        }
        
        debug_log = context.setdefault("debug", [])
        debug_log.append(f"MetricsAgent: Fallback used ({error})")
        
        return context
