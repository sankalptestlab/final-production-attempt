"""
Unit tests for Nikita MCP
Tests CAM building, validation, and document preparation
"""

import pytest
from fastapi.testclient import TestClient
import importlib.util
import os
import sys

# Add Nikita directory to sys.path before loading module
nikita_dir = os.path.join(os.path.dirname(__file__), '../services/nikita-mcp')
sys.path.insert(0, nikita_dir)

# Load Nikita main module directly by path
nikita_main_path = os.path.join(nikita_dir, 'main.py')
spec = importlib.util.spec_from_file_location("nikita_main", nikita_main_path)
nikita_main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nikita_main)

app = nikita_main.app

client = TestClient(app)

# Sample test data matching actual API schema
SAMPLE_GST_DATA = {
    "entity_information": {
        "legal_name": "TEST COMPANY PVT LTD",
        "trade_name": "TEST COMPANY",
        "constitution": "Private Limited",
        "date_of_incorporation": "2020-01-15",
        "gst_numbers": ["29ABCDE1234F1Z5"],
        "registered_address": {
            "city": "Bangalore",
            "state": "Karnataka"
        }
    }
}

SAMPLE_PAN_DATA = {
    "pan": "ABCDE1234F",
    "name": "TEST COMPANY PVT LTD",
    "status": "Active"
}

SAMPLE_CREDIT_BUREAU = {
    "commercial": {
        "score": "CMR-2",
        "active_loans": 5,
        "total_outstanding": 25.5
    },
    "consumer": {
        "promoters": [
            {
                "name": "Promoter 1",
                "pan": "PQRST1234U",
                "score": 750,
                "bureau_type": "CIBIL",
                "total_outstanding": 10.5,
                "overdue_amount": 0,
                "active_loans": 2
            }
        ]
    }
}

SAMPLE_CUSTOMER_INPUTS = {
    "loan_amount_lakhs": 50,
    "loan_purpose": "Working Capital",
    "tenure_months": 36,
    "collateral_available": True,
    "preferred_lender": "any"
}

class TestHealthEndpoint:
    def test_health_check(self):
        """Test health endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

class TestCAMBuilding:
    def test_build_cam_success(self):
        """Test successful CAM building with complete data"""
        payload = {
            "conversation_id": "test-conv-123",
            "gst_data": SAMPLE_GST_DATA,
            "pan_data": SAMPLE_PAN_DATA,
            "credit_bureau": SAMPLE_CREDIT_BUREAU,
            "customer_inputs": SAMPLE_CUSTOMER_INPUTS,
            "udyam_data": {
                "udyam_number": "UDYAM-DL-00-0012345",
                "entity_name": "TEST COMPANY PVT LTD",
                "activity_code": "NIC 224"
            }
        }

        response = client.post("/build-cam", json=payload)

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "cam_id" in data
        assert "cam_status" in data
        assert "cam_data" in data
        assert "missing_fields" in data
        assert "data_flags" in data
        assert "kesha_ready" in data

        # Verify CAM data structure
        cam = data["cam_data"]
        assert "entity_identity" in cam
        assert "business_profile" in cam
        assert "financial_summary" in cam
        assert "credit_profile" in cam

    def test_build_cam_minimal_data(self):
        """Test CAM building with minimal required data"""
        payload = {
            "conversation_id": "test-conv-123",
            "gst_data": SAMPLE_GST_DATA,
            "pan_data": SAMPLE_PAN_DATA,
            "credit_bureau": SAMPLE_CREDIT_BUREAU,
            "customer_inputs": SAMPLE_CUSTOMER_INPUTS
        }

        response = client.post("/build-cam", json=payload)
        # Should succeed with minimal required data
        assert response.status_code == 200

class TestDataValidation:
    def test_data_flags_returned(self):
        """Test data flags are returned"""
        payload = {
            "conversation_id": "test-conv-123",
            "gst_data": SAMPLE_GST_DATA,
            "pan_data": SAMPLE_PAN_DATA,
            "credit_bureau": SAMPLE_CREDIT_BUREAU,
            "customer_inputs": SAMPLE_CUSTOMER_INPUTS
        }

        response = client.post("/build-cam", json=payload)
        data = response.json()

        # Check for data flags
        flags = data.get("data_flags", [])
        assert isinstance(flags, list)

class TestMissingFieldsDetection:
    def test_missing_fields_detected(self):
        """Test that missing optional fields are reported"""
        payload = {
            "conversation_id": "test-conv-123",
            "gst_data": SAMPLE_GST_DATA,
            "pan_data": SAMPLE_PAN_DATA,
            "credit_bureau": SAMPLE_CREDIT_BUREAU,
            "customer_inputs": SAMPLE_CUSTOMER_INPUTS
            # Missing: bank_statements, udyam_data, itr_data
        }

        response = client.post("/build-cam", json=payload)
        data = response.json()

        # Should list missing optional fields
        missing = data.get("missing_fields", [])
        assert isinstance(missing, list)

class TestKeshaReadiness:
    def test_kesha_ready_flag(self):
        """Test that kesha_ready flag is set correctly"""
        payload = {
            "conversation_id": "test-conv-123",
            "gst_data": SAMPLE_GST_DATA,
            "pan_data": SAMPLE_PAN_DATA,
            "credit_bureau": SAMPLE_CREDIT_BUREAU,
            "customer_inputs": SAMPLE_CUSTOMER_INPUTS
        }

        response = client.post("/build-cam", json=payload)
        data = response.json()

        # Should have kesha_ready boolean
        assert "kesha_ready" in data
        assert isinstance(data["kesha_ready"], bool)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
