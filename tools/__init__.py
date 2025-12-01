"""Nirava Tools Module.

This module contains deterministic health calculation tools (Day 2: Function Calling).

Tools:
    calc_bmi: Calculate Body Mass Index.
    bmi_category: Classify BMI into WHO categories.
    calc_bmr_mifflin: Calculate Basal Metabolic Rate.
    estimate_tdee: Estimate Total Daily Energy Expenditure.
    calc_daily_water_target_ml: Calculate hydration targets.
    calc_sleep_recommendation_hours: Get age-appropriate sleep recommendations.
    get_ideal_benchmarks: Get comprehensive clinical reference ranges.
    build_standard_health_snapshot: Build complete health assessment.
"""
from tools.health_metrics import (
    calc_bmi,
    bmi_category,
    calc_bmr_mifflin,
    estimate_tdee,
    calc_daily_water_target_ml,
    calc_sleep_recommendation_hours,
    get_ideal_benchmarks,
    build_standard_health_snapshot,
)

__all__ = [
    "calc_bmi",
    "bmi_category",
    "calc_bmr_mifflin",
    "estimate_tdee",
    "calc_daily_water_target_ml",
    "calc_sleep_recommendation_hours",
    "get_ideal_benchmarks",
    "build_standard_health_snapshot",
]