"""
Unit tests for Francis MCP
Tests conversation handling, extraction, and flow management
"""

import pytest
from fastapi.testclient import TestClient
import importlib.util
import os
import sys

# Add Francis directory to sys.path before loading module
francis_dir = os.path.join(os.path.dirname(__file__), '../services/francis-mcp')
sys.path.insert(0, francis_dir)

# Load Francis main module directly by path
francis_main_path = os.path.join(francis_dir, 'main.py')
spec = importlib.util.spec_from_file_location("francis_main", francis_main_path)
francis_main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(francis_main)

app = francis_main.app
extract_gstin = francis_main.extract_gstin
extract_pan = francis_main.extract_pan
extract_amount = francis_main.extract_amount

client = TestClient(app)

class TestHealthEndpoint:
    def test_health_check(self):
        """Test health endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

class TestExtractionFunctions:
    def test_extract_gstin_valid(self):
        """Test GSTIN extraction from text"""
        text = "My GSTIN is 29ABCDE1234F1Z5 please proceed"
        result = extract_gstin(text)
        assert result == "29ABCDE1234F1Z5"

    def test_extract_gstin_not_found(self):
        """Test GSTIN extraction when not present"""
        text = "I need a loan"
        result = extract_gstin(text)
        assert result is None

    def test_extract_pan_valid(self):
        """Test PAN extraction from text"""
        text = "My PAN is ABCDE1234F"
        result = extract_pan(text)
        assert result == "ABCDE1234F"

    def test_extract_pan_not_found(self):
        """Test PAN extraction when not present"""
        text = "I need a loan"
        result = extract_pan(text)
        assert result is None

    def test_extract_amount_lakhs(self):
        """Test amount extraction in lakhs"""
        assert extract_amount("I need 50 lakhs") == 50
        assert extract_amount("50L loan") == 50
        assert extract_amount("50 lakh") == 50

    def test_extract_amount_crores(self):
        """Test amount extraction in crores"""
        assert extract_amount("I need 2 crore") == 200  # 2 crore = 200 lakhs
        assert extract_amount("1.5 cr") == 150

class TestMessageProcessing:
    def test_initial_message(self):
        """Test initial conversation message"""
        # Don't send null values - just omit optional fields
        payload = {
            "channel": "web",
            "message": "Hi, I need a business loan"
        }

        response = client.post("/process-message", json=payload)

        assert response.status_code == 200
        data = response.json()

        # Should create conversation_id and customer_id
        assert "conversation_id" in data
        assert "customer_id" in data
        assert data["conversation_id"] is not None
        assert data["customer_id"] is not None

        # Should have a response
        assert "response_to_customer" in data
        assert len(data["response_to_customer"]) > 0

    def test_conversation_phase_progression(self):
        """Test conversation progresses through phases"""
        # Create new conversation - omit optional fields
        payload = {
            "channel": "web",
            "message": "I need a business loan"
        }
        response = client.post("/process-message", json=payload)

        assert response.status_code == 200
        data = response.json()

        # Should be in intake phase
        assert "current_phase" in data
        # Initial phase should be intake or similar
        assert data["current_phase"] in ["intake", "greeting", "building"]

class TestAssessmentReceival:
    def test_receive_assessment(self):
        """Test Francis receives assessment results"""
        payload = {
            "conversation_id": "test-conv-123",
            "assessment_id": "assess-456",
            "overall_eligibility": "high",
            "max_eligible_amount": 80,
            "top_lenders": ["HDFC Bank", "ICICI Bank", "Bajaj Finserv"],
            "customer_report": {
                "summary": "You are eligible for up to 80L",
                "strengths": ["Strong credit score"],
                "improvements": [],
                "next_steps": ["Review lenders", "Submit documents"]
            }
        }

        response = client.post("/receive-assessment", json=payload)

        assert response.status_code == 200
        data = response.json()

        # Should have formatted message for customer
        assert "message_to_customer" in data
        assert len(data["message_to_customer"]) > 0

        # Message should mention eligibility
        message = data["message_to_customer"]
        assert "80" in message or "eligible" in message.lower()

class TestErrorHandling:
    def test_invalid_channel(self):
        """Test handling of invalid channel"""
        payload = {
            "channel": "invalid_channel",
            "message": "Hello"
        }

        response = client.post("/process-message", json=payload)
        # Should either accept or return error
        assert response.status_code in [200, 400, 422]

    def test_empty_message(self):
        """Test handling of empty message"""
        payload = {
            "conversation_id": "test-123",
            "customer_id": "cust-456",
            "channel": "web",
            "message": ""
        }

        response = client.post("/process-message", json=payload)
        # Should handle gracefully
        assert response.status_code in [200, 400, 422]

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
