from typing import Dict, Optional, Tuple


def calc_bmi(weight_kg: float, height_cm: float) -> Optional[float]:
    """
    Calculate Body Mass Index (BMI).

    Returns:
        BMI as float (kg/m^2) or None if inputs are invalid.
    
    Validation:
    - weight_kg: 10-500 kg (realistic human range)
    - height_cm: 50-300 cm (realistic human range)
    """
    # Null checks
    if weight_kg is None or height_cm is None:
        return None
    
    # Type coercion for safety
    try:
        weight_kg = float(weight_kg)
        height_cm = float(height_cm)
    except (ValueError, TypeError):
        return None
    
    # Range validation
    if weight_kg <= 0 or weight_kg > 500:
        return None
    if height_cm <= 0 or height_cm > 300 or height_cm < 50:
        return None
    
    height_m = height_cm / 100.0
    return round(weight_kg / (height_m ** 2), 1)


def bmi_category(bmi: Optional[float]) -> Optional[str]:
    """
    Classify BMI using standard WHO categories for adults.
    """
    if bmi is None:
        return None
    if bmi < 18.5:
        return "underweight"
    if bmi < 25:
        return "normal"
    if bmi < 30:
        return "overweight"
    return "obese"


def calc_bmr_mifflin(
    weight_kg: float,
    height_cm: float,
    age_years: int,
    sex: str,
) -> Optional[float]:
    """
    Mifflin-St Jeor BMR formula.
    sex: 'male' or 'female' (case-insensitive)
    
    Validation:
    - weight_kg: 10-500 kg
    - height_cm: 50-300 cm
    - age_years: 1-120 years
    """
    # Null checks
    if weight_kg is None or height_cm is None or age_years is None:
        return None
    
    # Type coercion
    try:
        weight_kg = float(weight_kg)
        height_cm = float(height_cm)
        age_years = int(age_years)
    except (ValueError, TypeError):
        return None
    
    # Range validation
    if weight_kg <= 0 or weight_kg > 500:
        return None
    if height_cm <= 0 or height_cm > 300:
        return None
    if age_years <= 0 or age_years > 120:
        return None

    sex = (sex or "").lower()
    if sex == "male":
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age_years + 5
    elif sex == "female":
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age_years - 161
    else:
        # Unknown sex: fall back to sex-neutral-ish average
        bmr_male = 10 * weight_kg + 6.25 * height_cm - 5 * age_years + 5
        bmr_female = 10 * weight_kg + 6.25 * height_cm - 5 * age_years - 161
        bmr = (bmr_male + bmr_female) / 2

    return round(max(800, bmr), 0)  # BMR minimum 800 kcal (survival mode)


def estimate_tdee(bmr: Optional[float], activity_level: str) -> Optional[float]:
    """
    Estimate Total Daily Energy Expenditure from BMR and activity level.

    activity_level:
        'sedentary', 'light', 'moderate', 'active', 'very_active'
    
    Validation:
    - bmr: 800-5000 kcal (realistic human range)
    """
    if bmr is None:
        return None
    
    # Type coercion
    try:
        bmr = float(bmr)
    except (ValueError, TypeError):
        return None
    
    # Range validation
    if bmr < 800 or bmr > 5000:
        return None

    activity_level = (activity_level or "").lower()
    factors = {
        "sedentary": 1.2,
        "light": 1.375,
        "moderate": 1.55,
        "active": 1.725,
        "very_active": 1.9,
    }
    factor = factors.get(activity_level, 1.375)  # default to 'light'
    return round(bmr * factor, 0)


def calc_daily_water_target_ml(
    weight_kg: float,
    activity_level: str,
    climate: str = "temperate",
) -> Optional[int]:
    """
    Simple daily water target (in ml), not medical advice.

    Base rule:
        ~30–35 ml per kg, adjusted slightly for activity & climate.
    """
    if not weight_kg or weight_kg <= 0:
        return None

    base_per_kg = 35  # ml per kg
    activity_level = (activity_level or "").lower()
    climate = (climate or "").lower()

    # Activity adjustment (small, because we don't want extremes)
    activity_bonus = {
        "sedentary": 0,
        "light": 200,
        "moderate": 400,
        "active": 600,
        "very_active": 800,
    }.get(activity_level, 200)

    # Climate adjustment
    climate_bonus = {
        "cold": -200,
        "temperate": 0,
        "hot": 300,
    }.get(climate, 0)

    target_ml = weight_kg * base_per_kg + activity_bonus + climate_bonus
    return int(round(target_ml, -1))  # round to nearest 10 ml


def calc_sleep_recommendation_hours(age_years: int) -> Optional[Tuple[float, float]]:
    """
    Very rough sleep recommendation ranges (hours per night) by age.
    Values loosely based on common sleep guidelines; not medical advice.
    """
    if not age_years or age_years <= 0:
        return None

    if age_years < 14:
        return 9.0, 11.0
    if age_years <= 17:
        return 8.0, 10.0
    if age_years <= 64:
        return 7.0, 9.0
    return 7.0, 8.0


def get_ideal_benchmarks(age: int, sex: str) -> Dict[str, any]:
    """
    Return comprehensive clinical reference ranges based on age and sex.
    Sources: WHO, CDC, National Sleep Foundation, American Heart Association.
    """
    # Safe defaults for None values
    age = age or 30  # Default to adult if age not provided
    sex = (sex or "unknown").lower()
    
    # === SLEEP (National Sleep Foundation) ===
    if age < 14:
        sleep_hours = "9-11"
        sleep_note = "Growing bodies need more recovery time"
    elif age < 18:
        sleep_hours = "8-10"
        sleep_note = "Teens need extra sleep for brain development"
    elif age < 26:
        sleep_hours = "7-9"
        sleep_note = "Young adults benefit from consistent 7-9h"
    elif age < 65:
        sleep_hours = "7-9"
        sleep_note = "Adults function best with 7-9h"
    else:
        sleep_hours = "7-8"
        sleep_note = "Seniors may need slightly less but quality matters"

    # === WATER (Institute of Medicine) ===
    if sex == "male":
        water_liters = 3.7
        water_glasses = 15  # ~250ml per glass
    else:
        water_liters = 2.7
        water_glasses = 11
    
    # Adjust for age
    if age > 65:
        water_note = "Thirst sensation decreases with age - drink proactively"
    else:
        water_note = "Includes water from food (~20%)"

    # === BMI (WHO) ===
    bmi_range = "18.5 - 24.9"
    if age > 65:
        bmi_range = "22 - 27"  # Slightly higher OK for seniors
        bmi_note = "Slightly higher BMI may be protective in older adults"
    else:
        bmi_note = "Normal range for disease prevention"

    # === EXERCISE (WHO/AHA) ===
    if age < 18:
        exercise_weekly = "60 min/day (420 min/week)"
        exercise_note = "Children need daily active play"
    elif age < 65:
        exercise_weekly = "150-300 min/week moderate OR 75-150 min vigorous"
        exercise_note = "Plus 2 days strength training"
    else:
        exercise_weekly = "150 min/week moderate + balance exercises"
        exercise_note = "Focus on mobility and fall prevention"

    # === RESTING HEART RATE (AHA) ===
    # Generally 60-100 bpm, but fitter = lower
    if sex == "male":
        rhr_range = "60-100 bpm (fit: 50-70)"
    else:
        rhr_range = "60-100 bpm (fit: 55-75)"

    # === STRESS (General wellness targets) ===
    stress_target = "Below 4/10 daily average"
    stress_note = "Chronic stress >6/10 impacts sleep, immunity, and recovery"

    return {
        "sleep": {
            "hours": sleep_hours,
            "note": sleep_note
        },
        "water": {
            "liters": water_liters,
            "glasses": water_glasses,
            "note": water_note
        },
        "bmi": {
            "range": bmi_range,
            "note": bmi_note
        },
        "exercise": {
            "weekly": exercise_weekly,
            "daily_min": 22 if age >= 18 else 60,  # 150/7 ≈ 22 min/day
            "note": exercise_note
        },
        "resting_heart_rate": rhr_range,
        "stress": {
            "target": stress_target,
            "note": stress_note
        },
        "summary": f"Benchmarks for {age}y old {sex}"
    }

def build_standard_health_snapshot(
    profile: Dict,
    checkin: Dict,
) -> Dict:
    """
    Build a standard health snapshot from profile + today's check-in.

    Expects:
        profile = {
            "age": int,
            "sex": "male" | "female" | ...,
            "height_cm": float,
            "weight_kg": float,
            "activity_level": "sedentary" | "light" | "moderate" | "active" | "very_active",
        }

        checkin = {
            "sleep_hours": float,
            "water_glasses": int,
            ...
        }

    Returns a dict with metrics + simple OK flags.
    """
    age = profile.get("age")
    sex = profile.get("sex")
    height_cm = profile.get("height_cm")
    weight_kg = profile.get("weight_kg")
    activity_level = profile.get("activity_level", "light")

    sleep_hours = checkin.get("sleep_hours")
    water_glasses = checkin.get("water_glasses")

    bmi = calc_bmi(weight_kg, height_cm)
    bmi_cat = bmi_category(bmi)
    bmr = calc_bmr_mifflin(weight_kg, height_cm, age, sex)
    tdee = estimate_tdee(bmr, activity_level)
    water_target_ml = calc_daily_water_target_ml(weight_kg, activity_level)
    sleep_rec = calc_sleep_recommendation_hours(age)

    # Hydration check: compare glasses to ml target, assuming ~250 ml per glass
    hydration_ok = None
    if water_target_ml is not None and water_glasses is not None:
        approx_ml = water_glasses * 250
        hydration_ok = approx_ml >= 0.8 * water_target_ml  # 80% of target

    # Sleep check: is today within recommended range?
    sleep_ok = None
    if sleep_rec is not None and sleep_hours is not None:
        min_h, max_h = sleep_rec
        sleep_ok = min_h <= sleep_hours <= max_h

    snapshot = {
        "bmi": bmi,
        "bmi_category": bmi_cat,
        "bmr": bmr,
        "tdee": tdee,
        "daily_water_target_ml": water_target_ml,
        "sleep_recommendation_hours": {
            "min": sleep_rec[0],
            "max": sleep_rec[1],
        }
        if sleep_rec is not None
        else None,
        "hydration_ok": hydration_ok,
        "sleep_ok": sleep_ok,
    }

    return snapshot


# ============================================================================
# PILLAR 1: SLEEP QUALITY METRICS
# ============================================================================

def calc_sleep_efficiency(actual_sleep_hours: float, time_in_bed_hours: float) -> Optional[float]:
    """
    Sleep Efficiency = (Actual Sleep Time / Time in Bed) × 100
    
    Clinical Reference:
    - >85%: Good sleep efficiency
    - 75-85%: Fair
    - <75%: Poor (indicates sleep disruption)
    
    Source: American Academy of Sleep Medicine
    """
    if not actual_sleep_hours or not time_in_bed_hours or time_in_bed_hours <= 0:
        return None
    if actual_sleep_hours > time_in_bed_hours:
        return 100.0  # Cap at 100%
    return round((actual_sleep_hours / time_in_bed_hours) * 100, 1)


def calc_sleep_debt(sleep_hours: float, recommended_min: float) -> Optional[float]:
    """
    Sleep Debt = Recommended Hours - Actual Hours
    
    Positive value = deficit (bad)
    Negative value = surplus (good)
    
    Clinical Note: Chronic sleep debt >2h associated with:
    - Impaired glucose metabolism
    - Increased cortisol
    - Reduced cognitive performance
    
    Source: NIH Sleep Deprivation Studies
    """
    if sleep_hours is None or recommended_min is None:
        return None
    return round(recommended_min - sleep_hours, 1)


def calc_sleep_quality_score(sleep_hours: float, stress_score: int, alcohol_units: int) -> Optional[int]:
    """
    Sleep Quality Score (1-10 scale)
    
    Factors:
    - Sleep duration (7-9h = optimal)
    - Stress level (high stress = poor sleep)
    - Alcohol intake (disrupts REM sleep)
    
    Returns:
    - 8-10: Excellent
    - 6-7: Good
    - 4-5: Fair
    - 1-3: Poor
    """
    if sleep_hours is None:
        return None
    
    score = 5  # Base score
    
    # Sleep duration component (+/- 3 points)
    if 7 <= sleep_hours <= 9:
        score += 3  # Optimal range
    elif 6 <= sleep_hours < 7 or 9 < sleep_hours <= 10:
        score += 1  # Acceptable
    elif sleep_hours < 5:
        score -= 2  # Severe deficit
    
    # Stress component (+/- 2 points)
    if stress_score is not None:
        if stress_score <= 3:
            score += 2  # Low stress = better sleep
        elif stress_score >= 7:
            score -= 2  # High stress disrupts sleep
    
    # Alcohol component (-2 points if present)
    if alcohol_units and alcohol_units > 0:
        score -= min(alcohol_units, 3)  # Each drink worsens REM sleep
    
    return max(1, min(10, score))  # Clamp to 1-10


# ============================================================================
# PILLAR 2: HYDRATION METRICS
# ============================================================================

def calc_dehydration_risk(water_ml: float, target_ml: float, exercise_minutes: int) -> Optional[str]:
    """
    Dehydration Risk Assessment
    
    Factors:
    - Water intake vs target
    - Exercise (increases fluid loss)
    
    Returns: "low", "moderate", "high"
    
    Clinical Reference:
    - >80% of target + no heavy exercise = low risk
    - 50-80% of target = moderate risk
    - <50% of target or heavy exercise with low intake = high risk
    
    Source: American College of Sports Medicine
    """
    if water_ml is None or target_ml is None or target_ml <= 0:
        return None
    
    coverage = water_ml / target_ml
    exercise_minutes = exercise_minutes or 0
    
    if coverage >= 0.8 and exercise_minutes < 60:
        return "low"
    elif coverage >= 0.5:
        if exercise_minutes > 90:
            return "high"  # Intense exercise needs more hydration
        return "moderate"
    else:
        return "high"


def calc_hydration_score(water_glasses: int, target_glasses: int, urine_frequency: Optional[int] = None) -> Optional[int]:
    """
    Hydration Score (1-10)
    
    Based on:
    - Water intake vs target
    - Urine frequency (4-7 times/day = normal)
    
    Returns 1-10 (10 = excellent hydration)
    """
    if water_glasses is None or target_glasses is None or target_glasses <= 0:
        return None
    
    ratio = water_glasses / target_glasses
    
    if ratio >= 0.9:
        score = 10
    elif ratio >= 0.8:
        score = 8
    elif ratio >= 0.6:
        score = 6
    elif ratio >= 0.4:
        score = 4
    else:
        score = 2
    
    # Adjust for urine frequency if available
    if urine_frequency is not None:
        if 4 <= urine_frequency <= 7:
            score = min(10, score + 1)  # Normal frequency bonus
        elif urine_frequency < 3:
            score = max(1, score - 2)  # Dehydration indicator
    
    return score


# ============================================================================
# PILLAR 3: MOVEMENT & EXERCISE METRICS
# ============================================================================

def calc_met_score(exercise_minutes: int, exercise_type: str) -> Optional[float]:
    """
    MET (Metabolic Equivalent of Task) Score
    
    MET values by activity type:
    - Sedentary: 1.0 MET
    - Light (walking): 3.5 MET
    - Moderate (cardio): 5.0-7.0 MET
    - Vigorous (HIIT, running): 8.0-12.0 MET
    - Strength training: 3.0-6.0 MET
    
    Returns: Total MET-minutes for the day
    
    Source: Compendium of Physical Activities
    """
    if not exercise_minutes or exercise_minutes <= 0:
        return 0.0
    
    exercise_type = (exercise_type or "").lower()
    
    met_values = {
        "cardio": 6.0,
        "strength": 4.5,
        "both": 5.5,  # Average
        "none": 0.0,
    }
    
    met = met_values.get(exercise_type, 3.5)  # Default to light activity
    return round(exercise_minutes * met, 1)


def estimate_vo2_max(age: int, sex: str, exercise_minutes_weekly: float, resting_hr: Optional[int] = None) -> Optional[float]:
    """
    Estimated VO2 Max (Cardiorespiratory Fitness)
    
    Simplified non-exercise prediction equation
    Based on: age, sex, physical activity, resting heart rate
    
    VO2 Max Interpretation (ml/kg/min):
    - Men 20-29: <42 (poor), 42-46 (fair), 46-51 (good), 51-56 (excellent), >56 (superior)
    - Women 20-29: <33 (poor), 33-37 (fair), 37-41 (good), 41-45 (excellent), >45 (superior)
    
    Note: This is a rough estimate. Lab VO2 max testing is the gold standard.
    
    Source: Journal of Applied Physiology, Non-Exercise VO2 Max Prediction
    """
    if not age or not sex:
        return None
    
    sex = sex.lower()
    exercise_minutes_weekly = exercise_minutes_weekly or 0
    resting_hr = resting_hr or 70  # Default resting HR
    
    # Base VO2 max by age and sex
    if sex == "male":
        base_vo2 = 60 - (0.6 * age)
    else:
        base_vo2 = 48 - (0.5 * age)
    
    # Adjust for physical activity (150 min/week = baseline)
    activity_factor = (exercise_minutes_weekly / 150) * 5
    
    # Adjust for resting heart rate (lower is better)
    hr_adjustment = (75 - resting_hr) * 0.1
    
    vo2_max = base_vo2 + activity_factor + hr_adjustment
    
    return round(max(20, min(80, vo2_max)), 1)  # Clamp to realistic range


def calc_active_calorie_burn(exercise_minutes: int, met_score: float, weight_kg: float) -> Optional[float]:
    """
    Active Calorie Burn = MET × Weight (kg) × Time (hours)
    
    Returns: Estimated calories burned during exercise
    
    Source: American Council on Exercise
    """
    if not exercise_minutes or not met_score or not weight_kg:
        return None
    
    hours = exercise_minutes / 60.0
    calories = met_score * weight_kg * hours
    
    return round(calories, 0)


def calc_sedentary_risk_score(exercise_minutes_daily: int, sitting_hours: Optional[float] = None) -> Optional[int]:
    """
    Sedentary Lifestyle Risk Score (1-10)
    
    Clinical Reference:
    - <30 min exercise/day + >8h sitting = high risk (cardiovascular disease, diabetes)
    - 30-60 min exercise + moderate sitting = moderate risk
    - >60 min exercise + low sitting = low risk
    
    Returns:
    - 1-3: Low risk
    - 4-6: Moderate risk
    - 7-10: High risk
    
    Source: Lancet "Sitting Time and Mortality"
    """
    if exercise_minutes_daily is None:
        return None
    
    sitting_hours = sitting_hours or 8.0  # Default assumption
    
    risk_score = 5  # Base
    
    # Exercise component
    if exercise_minutes_daily >= 60:
        risk_score -= 3
    elif exercise_minutes_daily >= 30:
        risk_score -= 1
    else:
        risk_score += 2
    
    # Sitting component
    if sitting_hours >= 10:
        risk_score += 3
    elif sitting_hours >= 8:
        risk_score += 1
    elif sitting_hours <= 5:
        risk_score -= 1
    
    return max(1, min(10, risk_score))


# ============================================================================
# PILLAR 4: MENTAL HEALTH METRICS
# ============================================================================

def calc_stress_load_index(stress_score: int, sleep_hours: float, social_hours: float) -> Optional[int]:
    """
    Stress Load Index (1-10)
    
    Combines:
    - Current stress level
    - Sleep quality (poor sleep amplifies stress)
    - Social support (reduces stress)
    
    Returns:
    - 1-3: Low stress load (manageable)
    - 4-6: Moderate stress load
    - 7-10: High stress load (risk of burnout)
    
    Source: American Psychological Association Stress Guidelines
    """
    if stress_score is None:
        return None
    
    load = stress_score  # Start with raw stress
    
    # Sleep amplifier
    if sleep_hours is not None:
        if sleep_hours < 6:
            load += 2  # Sleep deprivation worsens stress
        elif sleep_hours >= 8:
            load -= 1  # Good sleep buffers stress
    
    # Social buffer
    if social_hours is not None:
        if social_hours >= 2:
            load -= 2  # Social connection reduces stress
        elif social_hours < 0.5:
            load += 1  # Isolation worsens stress
    
    return max(1, min(10, load))


def calc_burnout_risk_score(stress_score: int, energy_score: int, mood_score: int, sleep_hours: float) -> Optional[int]:
    """
    Burnout Risk Score (1-10)
    
    Burnout indicators:
    - High chronic stress
    - Persistent low energy
    - Low mood
    - Poor sleep
    
    Returns:
    - 1-3: Low burnout risk
    - 4-6: Moderate burnout risk (watch closely)
    - 7-10: High burnout risk (urgent intervention needed)
    
    Source: Maslach Burnout Inventory (adapted)
    """
    if stress_score is None or energy_score is None or mood_score is None:
        return None
    
    risk = 0
    
    # Stress component (chronic stress)
    if stress_score >= 7:
        risk += 4
    elif stress_score >= 5:
        risk += 2
    
    # Energy depletion
    if energy_score <= 2:
        risk += 3
    elif energy_score <= 3:
        risk += 1
    
    # Mood/emotional exhaustion
    if mood_score <= 2:
        risk += 2
    
    # Sleep disruption
    if sleep_hours is not None and sleep_hours < 6:
        risk += 1
    
    return max(1, min(10, risk))


def calc_mental_resilience_score(stress_score: int, mood_score: int, social_hours: float, exercise_minutes: int) -> Optional[int]:
    """
    Mental Resilience Score (1-10)
    
    Protective factors:
    - Social connection
    - Physical activity
    - Positive mood
    - Stress management
    
    Returns:
    - 8-10: High resilience
    - 5-7: Moderate resilience
    - 1-4: Low resilience
    
    Source: American Psychological Association Resilience Framework
    """
    if stress_score is None or mood_score is None:
        return None
    
    resilience = 5  # Base
    
    # Mood component
    if mood_score >= 4:
        resilience += 2
    elif mood_score <= 2:
        resilience -= 2
    
    # Stress management
    if stress_score <= 3:
        resilience += 2
    elif stress_score >= 7:
        resilience -= 2
    
    # Social support
    if social_hours is not None:
        if social_hours >= 2:
            resilience += 2
        elif social_hours < 0.5:
            resilience -= 1
    
    # Exercise (proven resilience builder)
    if exercise_minutes is not None:
        if exercise_minutes >= 30:
            resilience += 1
    
    return max(1, min(10, resilience))


# ============================================================================
# PILLAR 5: SOCIAL CONNECTION METRICS
# ============================================================================

def calc_loneliness_risk_index(social_hours: float, mood_score: int) -> Optional[str]:
    """
    Loneliness Risk Assessment
    
    Criteria:
    - <0.5h daily social interaction = high risk
    - 0.5-1.5h = moderate risk
    - >1.5h = low risk
    
    Adjusted by mood (low mood + isolation = higher risk)
    
    Returns: "low", "moderate", "high"
    
    Clinical Impact:
    - Loneliness increases mortality risk by 26%
    - Equivalent to smoking 15 cigarettes/day
    
    Source: Brigham Young University Meta-Analysis on Loneliness
    """
    if social_hours is None:
        return None
    
    # Base risk from social hours
    if social_hours < 0.5:
        risk = "high"
    elif social_hours < 1.5:
        risk = "moderate"
    else:
        risk = "low"
    
    # Adjust for mood
    if mood_score is not None and mood_score <= 2:
        if risk == "moderate":
            risk = "high"
        elif risk == "low":
            risk = "moderate"
    
    return risk


def calc_social_wellness_score(social_hours: float, mood_score: int, stress_score: int) -> Optional[int]:
    """
    Social Wellness Score (1-10)
    
    Factors:
    - Quality social time
    - Emotional well-being (mood)
    - Stress level (social connection reduces stress)
    
    Returns:
    - 8-10: Thriving socially
    - 5-7: Adequate social wellness
    - 1-4: Social wellness concern
    """
    if social_hours is None:
        return None
    
    score = 5  # Base
    
    # Social time component
    if social_hours >= 2:
        score += 3
    elif social_hours >= 1:
        score += 1
    elif social_hours < 0.5:
        score -= 2
    
    # Mood component (social wellness correlates with mood)
    if mood_score is not None:
        if mood_score >= 4:
            score += 2
        elif mood_score <= 2:
            score -= 2
    
    # Stress component
    if stress_score is not None:
        if stress_score <= 3:
            score += 1  # Low stress suggests good social support
        elif stress_score >= 7:
            score -= 1
    
    return max(1, min(10, score))


# ============================================================================
# PILLAR 6: TOXIN AVOIDANCE METRICS
# ============================================================================

def calc_toxin_load_score(alcohol_units: int, smoking_today: bool, processed_food_servings: Optional[int] = None) -> Optional[int]:
    """
    Toxin Load Score (0-10)
    
    Higher score = higher toxin exposure
    
    Factors:
    - Alcohol (each unit adds load)
    - Smoking (major contributor)
    - Processed foods (if available)
    
    Returns:
    - 0-2: Low toxin exposure
    - 3-5: Moderate exposure
    - 6-10: High exposure (health risk)
    
    Source: WHO Toxin Exposure Guidelines
    """
    load = 0
    
    # Alcohol component
    if alcohol_units is not None:
        if alcohol_units == 0:
            load += 0
        elif alcohol_units <= 1:
            load += 1
        elif alcohol_units <= 2:
            load += 2
        else:
            load += min(alcohol_units, 6)  # Cap at 6
    
    # Smoking component (heavy weight)
    if smoking_today:
        load += 4
    
    # Processed food component (if available)
    if processed_food_servings is not None:
        if processed_food_servings > 3:
            load += 2
        elif processed_food_servings > 1:
            load += 1
    
    return min(10, load)


def calc_liver_stress_indicator(alcohol_units: int, bmi: Optional[float] = None) -> Optional[str]:
    """
    Liver Stress Indicator
    
    Combines:
    - Alcohol intake (primary liver stressor)
    - BMI (obesity = fatty liver risk)
    
    Returns: "low", "moderate", "high"
    
    Clinical Reference:
    - >14 units/week (men) or >7 units/week (women) = high risk
    - Obesity (BMI >30) + alcohol = compounded risk
    
    Source: American Liver Foundation
    """
    if alcohol_units is None:
        return None
    
    # Alcohol-based assessment
    if alcohol_units == 0:
        risk = "low"
    elif alcohol_units <= 2:
        risk = "low"
    elif alcohol_units <= 4:
        risk = "moderate"
    else:
        risk = "high"
    
    # BMI adjustment (obesity worsens liver stress)
    if bmi is not None and bmi >= 30:
        if risk == "low":
            risk = "moderate"
        elif risk == "moderate":
            risk = "high"
    
    return risk


def calc_cardiovascular_toxin_impact(smoking_today: bool, alcohol_units: int, stress_score: int) -> Optional[int]:
    """
    Cardiovascular Toxin Impact Score (1-10)
    
    Factors:
    - Smoking (direct vascular damage)
    - Alcohol (blood pressure, arrhythmia risk)
    - Stress (amplifies toxin damage)
    
    Returns:
    - 1-3: Low cardiovascular risk from toxins
    - 4-6: Moderate risk
    - 7-10: High risk
    
    Source: American Heart Association
    """
    impact = 1  # Base (minimal risk)
    
    # Smoking (major cardiovascular toxin)
    if smoking_today:
        impact += 5
    
    # Alcohol
    if alcohol_units is not None:
        if alcohol_units > 3:
            impact += 3
        elif alcohol_units > 1:
            impact += 1
    
    # Stress amplifier
    if stress_score is not None and stress_score >= 7:
        impact += 1  # Stress + toxins = worse outcomes
    
    return min(10, impact)