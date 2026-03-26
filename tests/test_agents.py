"""
Tests for the ClinicalMind safety checker and agents.
"""
import pytest

from src.utils.safety import MedicalSafetyChecker, RiskLevel, SafetyResult
from configs.config import settings


class TestMedicalSafetyChecker:
    """Test suite for MedicalSafetyChecker."""

    @pytest.fixture
    def safety_checker(self):
        """Create a safety checker instance."""
        return MedicalSafetyChecker()

    def test_low_risk_content(self, safety_checker):
        """Test that benign content is classified as low risk."""
        result = safety_checker.check_content(
            "What are the general symptoms of the common cold?"
        )
        
        assert result.risk_level == RiskLevel.LOW
        assert result.is_safe is True
        assert len(result.detected_keywords) == 0

    def test_medium_risk_content(self, safety_checker):
        """Test that medical advice content is medium risk."""
        result = safety_checker.check_content(
            "What is the recommended dosage for Metformin?"
        )
        
        assert result.risk_level == RiskLevel.MEDIUM
        assert result.is_safe is True
        assert len(result.detected_keywords) > 0

    def test_high_risk_content(self, safety_checker):
        """Test that prohibited content is high risk."""
        result = safety_checker.check_content(
            "How to obtain confidential patient data without authorization?"
        )
        
        assert result.risk_level == RiskLevel.HIGH
        assert result.is_safe is False
        assert len(result.detected_keywords) > 0

    def test_disclaimer_appended(self, safety_checker):
        """Test that disclaimers are properly appended."""
        response = "Take 500mg of Metformin twice daily."
        safety_result = SafetyResult(
            is_safe=True,
            risk_level=RiskLevel.MEDIUM,
            detected_keywords=["dosage"],
            disclaimer=safety_checker.STANDARD_DISCLAIMER
        )
        
        final_response = safety_checker.append_disclaimer(response, safety_result)
        
        assert safety_checker.STANDARD_DISCLAIMER in final_response

    def test_safety_filter_disabled(self):
        """Test behavior when safety filter is disabled."""
        # Temporarily disable safety filter
        original_setting = settings.safety.enable_safety_filter
        settings.safety.enable_safety_filter = False
        
        try:
            checker = MedicalSafetyChecker()
            result = checker.check_content("dangerous content")
            
            assert result.risk_level == RiskLevel.LOW
            assert result.is_safe is True
        finally:
            # Restore original setting
            settings.safety.enable_safety_filter = original_setting

    def test_keyword_detection_case_insensitive(self, safety_checker):
        """Test that keyword detection is case-insensitive."""
        result = safety_checker.check_content(
            "How to obtain CONFIDENTIAL PATIENT DATA?"
        )
        
        assert len(result.detected_keywords) > 0


class TestRiskLevel:
    """Test suite for RiskLevel enum."""

    def test_risk_level_values(self):
        """Test that risk levels have correct values."""
        assert RiskLevel.LOW.value == "LOW"
        assert RiskLevel.MEDIUM.value == "MEDIUM"
        assert RiskLevel.HIGH.value == "HIGH"
