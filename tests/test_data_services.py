"""
Unit tests for Data Services MCP
Tests mock API endpoints for GST, PAN, Credit Bureau, FameScore
"""

import pytest
from fastapi.testclient import TestClient
import importlib.util
import os
import sys

# Add data services directory to sys.path before loading module
data_services_dir = os.path.join(os.path.dirname(__file__), '../services/data-services-mcp')
sys.path.insert(0, data_services_dir)

# Load Data Services main module directly by path
data_services_main_path = os.path.join(data_services_dir, 'main.py')
spec = importlib.util.spec_from_file_location("data_services_main", data_services_main_path)
data_services_main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(data_services_main)

app = data_services_main.app

client = TestClient(app)

class TestHealthEndpoint:
    def test_health_check(self):
        """Test health endpoint returns 200"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "data-services-mcp"

class TestGSTVerification:
    def test_verify_gst_success(self):
        """Test GST verification with valid GSTIN"""
        payload = {"gstin": "29ABCDE1234F1Z5"}
        response = client.post("/verify-gst", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data

    def test_verify_gst_invalid_length(self):
        """Test GST verification with invalid GSTIN length"""
        payload = {"gstin": "INVALID"}
        response = client.post("/verify-gst", json=payload)

        assert response.status_code == 422  # Validation error

class TestPANVerification:
    def test_verify_pan_success(self):
        """Test PAN verification with valid PAN"""
        payload = {"pan": "ABCDE1234F"}
        response = client.post("/verify-pan", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data

    def test_verify_pan_invalid_length(self):
        """Test PAN verification with invalid format"""
        payload = {"pan": "INVALID"}
        response = client.post("/verify-pan", json=payload)

        assert response.status_code == 422  # Validation error

class TestCreditBureau:
    def test_pull_credit_bureau_with_consent(self):
        """Test credit bureau pull with consent"""
        payload = {
            "entity_pan": "ABCDE1234F",
            "promoter_pans": [],
            "consent_obtained": True
        }
        response = client.post("/pull-credit-bureau", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "commercial" in data["data"]
        assert "consumer" in data["data"]

    def test_credit_bureau_without_consent(self):
        """Test credit bureau without consent - should fail"""
        payload = {
            "entity_pan": "ABCDE1234F",
            "promoter_pans": [],
            "consent_obtained": False
        }
        response = client.post("/pull-credit-bureau", json=payload)

        assert response.status_code == 403
        assert "consent" in response.json()["detail"].lower()

class TestFameScore:
    def test_famescore_report_success(self):
        """Test FameScore comprehensive report"""
        payload = {
            "gstin": "29ABCDE1234F1Z5",
            "pan": "ABCDE1234F",
            "include_bureau": True
        }
        response = client.post("/famescore-report", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        report = data["data"]
        # Verify all major sections exist
        assert "entity_information" in report
        assert "credit_bureau_commercial" in report
        assert "existing_facilities" in report
        assert "gst_sales_data" in report
        assert "bank_limit_eligibility" in report

        # Verify entity info structure
        entity = report["entity_information"]
        assert entity["legal_name"] == "FINAGG TECHNOLOGIES PRIVATE LIMITED"
        assert len(entity["gst_numbers"]) > 0

class TestUdyamLookup:
    def test_udyam_lookup_success(self):
        """Test Udyam registration lookup"""
        payload = {"pan": "ABCDE1234F"}
        response = client.post("/lookup-udyam", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # Check for udyam registration fields
        assert "udyam_number" in data["data"]
        assert "entity_name" in data["data"]

class TestBankStatementParsing:
    def test_parse_bank_statement(self):
        """Test bank statement parsing (mock)"""
        response = client.post("/parse-bank-statement?file_reference=test-file-123")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "total_credits_lakhs" in data["data"]
        assert "average_monthly_balance_lakhs" in data["data"]

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
