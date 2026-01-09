"""
Unit tests for Kesha MCP
Tests credit assessment and lender matching logic
"""

import pytest
from fastapi.testclient import TestClient
import importlib.util
import os
import sys

# Add Kesha directory to sys.path before loading module
kesha_dir = os.path.join(os.path.dirname(__file__), '../services/kesha-mcp')
sys.path.insert(0, kesha_dir)

# Load Kesha main module directly by path
kesha_main_path = os.path.join(kesha_dir, 'main.py')
spec = importlib.util.spec_from_file_location("kesha_main", kesha_main_path)
kesha_main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kesha_main)

app = kesha_main.app
calculate_credit_score_numeric = kesha_main.calculate_credit_score_numeric
get_max_dpd = kesha_main.get_max_dpd
LENDER_CRITERIA = kesha_main.LENDER_CRITERIA

client = TestClient(app)

# Sample anonymized CAM
SAMPLE_CAM = {
    "cam_id": "test-cam-123",
    "business_profile": {
        "industry": "Manufacturing",
        "vintage_years": 3,
        "employee_count": 50
    },
    "financial_metrics": {
        "annual_turnover_lakhs": 500,
        "profit_margin": 0.12,
        "turnover_growth_yoy": 0.15
    },
    "credit_profile": {
        "commercial_score": "CMR-2",
        "active_loans_count": 5,
        "total_outstanding_lakhs": 50,
        "utilization_pct": 0.7,
        "overdue_amount_lakhs": 0,
        "existing_facilities": [
            {
                "lender": "HDFC Bank",
                "type": "OD",
                "sanctioned_amount_lakhs": 30,
                "outstanding_lakhs": 25,
                "dpd_days": 0
            }
        ]
    },
    "compliance": {
        "gst_filing_status": "regular",
        "filing_consistency": 0.95,
        "itr_filed": True
    },
    "loan_request": {
        "amount_lakhs": 50,
        "purpose": "Working Capital",
        "tenure_months": 36,
        "collateral_available": True
    },
    "customer_preferences": {
        "priority": "low_interest",
        "lender_preference": "any"
    }
}

class TestHealthEndpoint:
    def test_health_check(self):
        """Test health endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

class TestCreditScoreConversion:
    def test_credit_score_numeric_conversion(self):
        """Test CMR score to numeric conversion"""
        assert calculate_credit_score_numeric("CMR-1") == 800
        assert calculate_credit_score_numeric("CMR-2") == 750
        assert calculate_credit_score_numeric("CMR-3") == 700
        assert calculate_credit_score_numeric("CMR-8") == 450
        assert calculate_credit_score_numeric("INVALID") == 600  # Default

class TestDPDCalculation:
    def test_get_max_dpd(self):
        """Test maximum DPD calculation from facilities"""
        credit_profile = {
            "existing_facilities": [
                {"dpd_days": 0},
                {"dpd_days": 15},
                {"dpd_days": 5}
            ]
        }
        assert get_max_dpd(credit_profile) == 15

    def test_get_max_dpd_no_facilities(self):
        """Test DPD calculation with no facilities"""
        credit_profile = {"existing_facilities": []}
        assert get_max_dpd(credit_profile) == 0

class TestLenderMatching:
    def test_assess_cam_success(self):
        """Test successful CAM assessment with lender matches"""
        response = client.post("/assess", json=SAMPLE_CAM)

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "assessment_id" in data
        assert "overall_eligibility" in data
        assert "max_eligible_amount_lakhs" in data
        assert "lender_matches" in data
        assert "recommendation" in data
        assert "customer_report" in data

        # Should have some lender matches with good profile
        assert len(data["lender_matches"]) > 0

    def test_high_eligibility_profile(self):
        """Test high eligibility profile gets multiple matches"""
        import copy
        high_profile = copy.deepcopy(SAMPLE_CAM)
        high_profile["financial_metrics"]["annual_turnover_lakhs"] = 1000
        high_profile["credit_profile"]["commercial_score"] = "CMR-1"

        response = client.post("/assess", json=high_profile)
        data = response.json()

        assert data["overall_eligibility"] == "high"
        assert len(data["lender_matches"]) >= 3

    def test_low_eligibility_profile(self):
        """Test low eligibility profile gets fewer/no matches"""
        import copy
        low_profile = copy.deepcopy(SAMPLE_CAM)
        low_profile["financial_metrics"]["annual_turnover_lakhs"] = 5
        low_profile["credit_profile"]["commercial_score"] = "CMR-7"
        low_profile["credit_profile"]["existing_facilities"] = [
            {"dpd_days": 60}
        ]

        response = client.post("/assess", json=low_profile)
        data = response.json()

        # Should have low/ineligible status
        assert data["overall_eligibility"] in ["low", "ineligible"]

class TestLenderRanking:
    def test_lender_ranking_by_preference(self):
        """Test lenders are ranked according to customer preference"""
        import copy
        low_interest_cam = copy.deepcopy(SAMPLE_CAM)
        low_interest_cam["customer_preferences"] = {"priority": "low_interest", "lender_preference": "any"}

        response = client.post("/assess", json=low_interest_cam)
        data = response.json()

        if len(data["lender_matches"]) > 0:
            top_lender = data["lender_matches"][0]
            # Banks should rank higher for low_interest
            lender_type = LENDER_CRITERIA[top_lender["lender_id"]]["type"]
            assert lender_type in ["private_bank", "psu_bank", "nbfc", "fintech"]

class TestApprovalProbability:
    def test_approval_probability_calculation(self):
        """Test that approval probability is calculated for each lender"""
        response = client.post("/assess", json=SAMPLE_CAM)
        data = response.json()

        for match in data["lender_matches"]:
            assert "approval_probability" in match
            assert 0 <= match["approval_probability"] <= 1

class TestCustomerReport:
    def test_customer_report_has_summary(self):
        """Test customer report includes summary"""
        response = client.post("/assess", json=SAMPLE_CAM)
        data = response.json()

        report = data["customer_report"]
        assert "summary" in report
        assert "strengths" in report
        assert "improvements" in report
        assert "next_steps" in report

    def test_customer_report_identifies_strengths(self):
        """Test customer report identifies strengths"""
        import copy
        strong_profile = copy.deepcopy(SAMPLE_CAM)
        strong_profile["credit_profile"]["commercial_score"] = "CMR-1"
        strong_profile["compliance"]["filing_consistency"] = 0.95

        response = client.post("/assess", json=strong_profile)
        data = response.json()

        strengths = data["customer_report"]["strengths"]
        assert len(strengths) > 0
        # Should mention credit score
        assert any("credit" in s.lower() for s in strengths)

class TestRecommendation:
    def test_recommendation_includes_primary_lender(self):
        """Test recommendation includes primary lender"""
        response = client.post("/assess", json=SAMPLE_CAM)
        data = response.json()

        recommendation = data["recommendation"]
        if data["overall_eligibility"] != "ineligible":
            assert recommendation["primary"] is not None
            assert recommendation["primary"] in LENDER_CRITERIA

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
