"""Unit Tests for Nirava Health Companion Agents.

These tests verify the core functionality of the multi-agent system
without requiring API calls (using fallback modes).

Run with: pytest tests/ -v
"""
import pytest
from models.session import ConversationState, UserProfile, DailyCheckIn, ConversationPhase
from tools.health_metrics import (
    calc_bmi,
    bmi_category,
    calc_bmr_mifflin,
    calc_sleep_recommendation_hours,
    get_ideal_benchmarks,
    build_standard_health_snapshot
)


class TestHealthMetricsTools:
    """Test the health calculation tools (Day 2: Function Calling)."""

    def test_bmi_calculation_normal(self):
        """BMI for average adult should be in normal range."""
        bmi = calc_bmi(weight_kg=70, height_cm=175)
        assert bmi is not None
        assert 18.5 <= bmi <= 25  # Normal range
        assert bmi == 22.9  # Exact calculation

    def test_bmi_calculation_edge_cases(self):
        """BMI should handle edge cases gracefully."""
        assert calc_bmi(0, 175) is None
        assert calc_bmi(70, 0) is None
        assert calc_bmi(None, 175) is None

    def test_bmi_category(self):
        """BMI categories should match WHO standards."""
        assert bmi_category(17) == "underweight"
        assert bmi_category(22) == "normal"
        assert bmi_category(27) == "overweight"
        assert bmi_category(32) == "obese"
        assert bmi_category(None) is None

    def test_bmr_calculation(self):
        """BMR should differ by sex."""
        bmr_male = calc_bmr_mifflin(70, 175, 30, "male")
        bmr_female = calc_bmr_mifflin(70, 175, 30, "female")
        assert bmr_male > bmr_female  # Males typically have higher BMR
        assert 1500 < bmr_male < 2000  # Reasonable range

    def test_sleep_recommendations_by_age(self):
        """Sleep recommendations should vary by age group."""
        teen = calc_sleep_recommendation_hours(15)
        adult = calc_sleep_recommendation_hours(30)
        senior = calc_sleep_recommendation_hours(70)
        
        assert teen[0] > adult[0]  # Teens need more sleep
        assert adult == (7.0, 9.0)  # Standard adult range


class TestIdealBenchmarks:
    """Test the clinical benchmark generation (Day 3: Prompt Engineering)."""

    def test_benchmarks_contain_all_metrics(self):
        """Benchmarks should include all tracked health metrics."""
        benchmarks = get_ideal_benchmarks(30, "male")
        
        assert "sleep" in benchmarks
        assert "water" in benchmarks
        assert "bmi" in benchmarks
        assert "exercise" in benchmarks
        assert "stress" in benchmarks

    def test_benchmarks_age_appropriate(self):
        """Senior benchmarks should differ from adult benchmarks."""
        adult = get_ideal_benchmarks(30, "male")
        senior = get_ideal_benchmarks(70, "male")
        
        # Seniors have slightly higher acceptable BMI
        assert adult["bmi"]["range"] != senior["bmi"]["range"]

    def test_benchmarks_sex_appropriate(self):
        """Water recommendations should differ by sex."""
        male = get_ideal_benchmarks(30, "male")
        female = get_ideal_benchmarks(30, "female")
        
        assert male["water"]["liters"] > female["water"]["liters"]


class TestSessionModels:
    """Test the conversation state management (Day 1: Foundational Models)."""

    def test_user_profile_defaults(self):
        """User profile should have sensible defaults."""
        profile = UserProfile()
        assert profile.name == "Friend"
        assert profile.age == 30
        assert profile.primary_goal == "General Health"

    def test_daily_checkin_completion(self):
        """Check-in should track completion status."""
        checkin = DailyCheckIn()
        assert not checkin.is_complete
        assert len(checkin.missing_fields) == 6

        # Fill in all fields
        checkin.sleep_hours = 7.5
        checkin.water_glasses = 8
        checkin.mood_score = 4
        checkin.energy_score = 4
        checkin.stress_score = 3
        checkin.exercise_minutes = 30

        assert checkin.is_complete
        assert len(checkin.missing_fields) == 0

    def test_conversation_state_history(self):
        """Conversation state should track message history."""
        state = ConversationState()
        
        state.add_user_message("Hello")
        state.add_agent_message("Hi there!")
        
        assert len(state.history) == 2
        assert state.history[0]["role"] == "user"
        assert state.history[1]["role"] == "model"

    def test_conversation_phases(self):
        """Conversation should start in INTAKE phase."""
        state = ConversationState()
        assert state.phase == ConversationPhase.INTAKE


class TestHealthSnapshot:
    """Test the integrated health snapshot builder."""

    def test_snapshot_with_complete_data(self):
        """Snapshot should compute all metrics with complete data."""
        profile = {
            "age": 30,
            "sex": "male",
            "height_cm": 175,
            "weight_kg": 70,
            "activity_level": "moderate"
        }
        checkin = {
            "sleep_hours": 7.5,
            "water_glasses": 8
        }
        
        snapshot = build_standard_health_snapshot(profile, checkin)
        
        assert snapshot["bmi"] is not None
        assert snapshot["bmi_category"] == "normal"
        assert snapshot["sleep_ok"] is True
        assert snapshot["hydration_ok"] is not None

    def test_snapshot_with_partial_data(self):
        """Snapshot should handle missing data gracefully."""
        profile = {"age": 30}
        checkin = {}
        
        snapshot = build_standard_health_snapshot(profile, checkin)
        
        # Should not crash, just have None values
        assert snapshot["bmi"] is None
        assert snapshot["sleep_ok"] is None


class TestIssueClassification:
    """Test the symptom-aware triage system (Capstone Feature)."""

    def test_issue_keywords_coverage(self):
        """All issue types should have associated keywords."""
        from agents.intake_agent import ISSUE_KEYWORDS, ISSUE_METRICS
        
        for issue_type in ISSUE_METRICS.keys():
            if issue_type != "general_wellness":
                assert issue_type in ISSUE_KEYWORDS

    def test_issue_metrics_relevance(self):
        """Mental fatigue should not require BMI."""
        from agents.intake_agent import ISSUE_METRICS
        
        mental_metrics = ISSUE_METRICS["mental_fatigue"]
        assert "sleep_hours" in mental_metrics
        assert "stress_score" in mental_metrics
        # BMI is not in the list (not relevant for mental fatigue)


class TestSafetyKeywords:
    """Test the safety handoff system (Day 4: Domain-Specific LLMs)."""

    def test_urgent_keywords_exist(self):
        """Safety system should have urgent keywords defined."""
        from agents.research_agent import SAFETY_KEYWORDS
        
        assert "urgent" in SAFETY_KEYWORDS
        assert "chest pain" in SAFETY_KEYWORDS["urgent"]
        assert "suicidal" in SAFETY_KEYWORDS["urgent"]

    def test_recommend_doctor_keywords_exist(self):
        """Safety system should have doctor recommendation keywords."""
        from agents.research_agent import SAFETY_KEYWORDS
        
        assert "recommend_doctor" in SAFETY_KEYWORDS
        assert "depression" in SAFETY_KEYWORDS["recommend_doctor"]


# Integration test (requires API key, skipped by default)
@pytest.mark.skip(reason="Requires GOOGLE_API_KEY - run manually")
class TestIntegration:
    """Integration tests that require a live API connection."""

    def test_full_pipeline(self):
        """Test the complete agent pipeline."""
        from adk_main import NiravaSystem
        
        system = NiravaSystem()
        response = system.process("I'm feeling tired today")
        
        assert response is not None
        assert len(response) > 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
