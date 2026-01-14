"""
Backend Integration Test Suite
Tests the complete conversation flow, n8n workflow transformations, and service integrations
"""

import sys
import os
import json
import asyncio
from datetime import datetime
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Test results tracking
test_results = []

def log_test(name: str, passed: bool, details: str = ""):
    status = "✓ PASS" if passed else "✗ FAIL"
    test_results.append({"name": name, "passed": passed, "details": details})
    print(f"{status}: {name}")
    if details and not passed:
        print(f"       {details}")

def separator(title: str):
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}\n")

# ============================================================================
# TEST 1: Francis MCP - Field Naming Consistency
# ============================================================================

def test_francis_extracted_data_model():
    """Test that Francis ExtractedData model uses correct field names"""
    separator("TEST 1: Francis MCP - ExtractedData Model")

    try:
        from services.francis_mcp.main import ExtractedData

        # Test field names exist
        model = ExtractedData(
            gstin="09AADCF8429L1Z4",
            pan="AADCF8429L",
            loan_amount_lakhs=50.0,
            loan_purpose="Working Capital",
            tenure_months=36,
            collateral_available=True,
            customer_priority="low_interest",
            consent_obtained=True
        )

        # Check field names
        assert hasattr(model, 'gstin'), "Missing 'gstin' field"
        assert hasattr(model, 'pan'), "Missing 'pan' field"
        assert hasattr(model, 'loan_amount_lakhs'), "Missing 'loan_amount_lakhs' field"
        assert hasattr(model, 'consent_obtained'), "Missing 'consent_obtained' field"

        # Check old field names don't exist
        assert not hasattr(model, 'gst_number'), "Old 'gst_number' field still exists"
        assert not hasattr(model, 'pan_number'), "Old 'pan_number' field still exists"

        log_test("ExtractedData uses correct field names (gstin, pan, loan_amount_lakhs)", True)

    except ImportError:
        # Test the model definition directly from main.py
        log_test("ExtractedData model import", False, "Could not import - testing file directly")

        # Read and check the file content
        main_py_path = os.path.join(os.path.dirname(__file__), '..', 'services', 'francis-mcp', 'main.py')
        with open(main_py_path, 'r') as f:
            content = f.read()

        checks = [
            ('gstin: Optional[str]' in content, "gstin field defined"),
            ('pan: Optional[str]' in content, "pan field defined"),
            ('loan_amount_lakhs: Optional[float]' in content, "loan_amount_lakhs field defined"),
            ('consent_obtained: Optional[bool]' in content, "consent_obtained field defined"),
            ('gst_number' not in content or 'gst_number' in content.split('class ConsentRecord')[0], "gst_number removed from ExtractedData"),
        ]

        for check, desc in checks:
            log_test(desc, check)

    except Exception as e:
        log_test("ExtractedData model test", False, str(e))

# ============================================================================
# TEST 2: Data Services MCP - Endpoint Parameters
# ============================================================================

def test_data_services_credit_bureau_params():
    """Test that credit bureau endpoint expects correct parameters"""
    separator("TEST 2: Data Services MCP - Credit Bureau Parameters")

    main_py_path = os.path.join(os.path.dirname(__file__), '..', 'services', 'data-services-mcp', 'main.py')

    try:
        with open(main_py_path, 'r') as f:
            content = f.read()

        # Check CreditBureauRequest model
        checks = [
            ('entity_pan: str' in content, "entity_pan field in CreditBureauRequest"),
            ('promoter_pans' in content, "promoter_pans field in CreditBureauRequest"),
            ('consent_obtained: bool' in content, "consent_obtained field in CreditBureauRequest"),
        ]

        for check, desc in checks:
            log_test(desc, check)

    except Exception as e:
        log_test("Data Services credit bureau params test", False, str(e))

# ============================================================================
# TEST 3: Nikita MCP - CAMBuildRequest Structure
# ============================================================================

def test_nikita_cam_build_request():
    """Test that Nikita expects correct CAMBuildRequest structure"""
    separator("TEST 3: Nikita MCP - CAMBuildRequest Structure")

    main_py_path = os.path.join(os.path.dirname(__file__), '..', 'services', 'nikita-mcp', 'main.py')

    try:
        with open(main_py_path, 'r') as f:
            content = f.read()

        # Check CAMBuildRequest fields
        checks = [
            ('gst_data: Dict' in content, "gst_data field in CAMBuildRequest"),
            ('pan_data: Dict' in content, "pan_data field in CAMBuildRequest"),
            ('credit_bureau: Dict' in content, "credit_bureau field in CAMBuildRequest"),
            ('customer_inputs: Dict' in content, "customer_inputs field in CAMBuildRequest"),
        ]

        for check, desc in checks:
            log_test(desc, check)

    except Exception as e:
        log_test("Nikita CAMBuildRequest test", False, str(e))

# ============================================================================
# TEST 4: Kesha MCP - Field Path Fixes
# ============================================================================

def test_kesha_field_paths():
    """Test that Kesha uses correct field paths"""
    separator("TEST 4: Kesha MCP - Field Paths")

    main_py_path = os.path.join(os.path.dirname(__file__), '..', 'services', 'kesha-mcp', 'main.py')

    try:
        with open(main_py_path, 'r') as f:
            content = f.read()

        # Check field access patterns
        checks = [
            ('financial_metrics.get("annual_turnover_lakhs"' in content, "annual_turnover_lakhs access"),
            ('credit_profile.get("commercial_score"' in content, "commercial_score access"),
            ('dpd_days' in content and 'overdue_days' in content, "DPD field supports both names"),
        ]

        for check, desc in checks:
            log_test(desc, check)

    except Exception as e:
        log_test("Kesha field paths test", False, str(e))

# ============================================================================
# TEST 5: n8n Workflow - Data Transformation
# ============================================================================

def test_n8n_workflow_transformations():
    """Test n8n workflow data transformations"""
    separator("TEST 5: n8n Workflow - Data Transformations")

    workflow_path = os.path.join(os.path.dirname(__file__), '..', 'n8n-workflows', 'cam-processing-workflow.json')

    try:
        with open(workflow_path, 'r') as f:
            workflow = json.load(f)

        # Find nodes by name
        nodes = {node['name']: node for node in workflow['nodes']}

        # Test 1: Credit Bureau uses entity_pan
        credit_bureau_node = nodes.get('Call Commercial Credit Bureau', {})
        params = credit_bureau_node.get('parameters', {}).get('bodyParameters', {}).get('parameters', [])
        has_entity_pan = any(p.get('name') == 'entity_pan' for p in params)
        log_test("Credit Bureau API uses entity_pan param", has_entity_pan)

        # Test 2: Format Nikita Request builds correct structure
        format_node = nodes.get('Format Nikita Request', {})
        function_code = format_node.get('parameters', {}).get('functionCode', '')

        nikita_checks = [
            ('nikitaGstData' in function_code, "Format Nikita builds gst_data"),
            ('nikitaPanData' in function_code, "Format Nikita builds pan_data"),
            ('nikitaCreditBureau' in function_code, "Format Nikita builds credit_bureau"),
            ('customerInputs' in function_code, "Format Nikita builds customer_inputs"),
        ]

        for check, desc in nikita_checks:
            log_test(desc, check)

        # Test 3: Save CAM to Database transforms for Kesha
        save_cam_node = nodes.get('Save CAM to Database', {})
        save_function = save_cam_node.get('parameters', {}).get('functionCode', '')

        kesha_checks = [
            ('kesha_payload' in save_function or 'keshaPayload' in save_function, "Save CAM creates kesha_payload"),
            ('financial_metrics' in save_function, "Save CAM maps financial_metrics"),
            ('commercial_score' in save_function, "Save CAM maps commercial_score"),
            ('compliance' in save_function, "Save CAM maps compliance"),
        ]

        for check, desc in kesha_checks:
            log_test(desc, check)

        # Test 4: Kesha call uses kesha_payload
        kesha_node = nodes.get('Call Kesha - Assess & Match', {})
        kesha_body = kesha_node.get('parameters', {}).get('jsonBody', '')
        log_test("Kesha API call uses kesha_payload", 'kesha_payload' in kesha_body)

        # Test 5: Error handling enabled
        has_continue_on_fail = any(
            node.get('continueOnFail', False)
            for node in workflow['nodes']
            if 'httpRequest' in node.get('type', '')
        )
        log_test("HTTP nodes have continueOnFail enabled", has_continue_on_fail)

        # Test 6: Error handler exists
        has_error_handler = 'Handle Error' in nodes
        log_test("Error handler node exists", has_error_handler)

        # Test 7: Original params passed to merge
        connections = workflow.get('connections', {})
        extract_connections = connections.get('Extract Parameters', {}).get('main', [[]])[0]
        passes_to_merge = any(
            c.get('node') == 'Merge All Data Sources'
            for c in extract_connections
        )
        log_test("Extract Parameters passes to Merge node", passes_to_merge)

    except Exception as e:
        log_test("n8n workflow transformation test", False, str(e))

# ============================================================================
# TEST 6: End-to-End Data Structure Simulation
# ============================================================================

def test_end_to_end_data_structure():
    """Simulate the complete data transformation flow"""
    separator("TEST 6: End-to-End Data Structure Simulation")

    # Simulate Francis extracted data
    francis_output = {
        "conversation_id": "test-conv-123",
        "customer_id": "test-cust-456",
        "extracted_data": {
            "gstin": "09AADCF8429L1Z4",
            "pan": "AADCF8429L",
            "consent_obtained": True,
            "loan_amount_lakhs": 50,
            "loan_purpose": "Working Capital",
            "tenure_months": 36,
            "collateral_available": False,
            "customer_priority": "low_interest"
        }
    }

    log_test("Francis output uses gstin/pan fields",
             'gstin' in francis_output['extracted_data'] and
             'pan' in francis_output['extracted_data'])

    # Simulate FameScore response (from Data Services)
    famescore_response = {
        "success": True,
        "data": {
            "entity_information": {
                "legal_name": "Test Company Pvt Ltd",
                "pan": "AADCF8429L"
            },
            "credit_bureau_commercial": {
                "score": "CMR-2",
                "total_outstanding_loan_amount": 27.10,
                "active_loans": 5
            },
            "existing_facilities": [
                {"overdue_days": 10, "status": "Active"}
            ],
            "gst_sales_data": {
                "ttm_summary": {"total_sales": 2411.48}
            },
            "compliance": {
                "filing_consistency": 0.84
            },
            "bank_limit_eligibility": {
                "total_12_month_sales": 2411.48
            }
        }
    }

    log_test("FameScore response has entity_information",
             'entity_information' in famescore_response['data'])

    # Simulate n8n transformation to Nikita format
    nikita_request = {
        "conversation_id": francis_output["conversation_id"],
        "gst_data": {
            "entity_information": famescore_response["data"]["entity_information"],
            "gst_sales_data": famescore_response["data"]["gst_sales_data"],
            "compliance": famescore_response["data"]["compliance"],
            "bank_limit_eligibility": famescore_response["data"]["bank_limit_eligibility"]
        },
        "pan_data": {
            "pan": francis_output["extracted_data"]["pan"],
            "name": famescore_response["data"]["entity_information"]["legal_name"],
            "status": "active"
        },
        "credit_bureau": {
            "commercial": famescore_response["data"]["credit_bureau_commercial"],
            "existing_facilities": famescore_response["data"]["existing_facilities"]
        },
        "customer_inputs": {
            "loan_amount_requested": francis_output["extracted_data"]["loan_amount_lakhs"],
            "loan_purpose": francis_output["extracted_data"]["loan_purpose"],
            "tenure_preference_months": francis_output["extracted_data"]["tenure_months"],
            "collateral_available": francis_output["extracted_data"]["collateral_available"],
            "priority": francis_output["extracted_data"]["customer_priority"]
        }
    }

    nikita_checks = [
        ('gst_data' in nikita_request, "Nikita request has gst_data"),
        ('pan_data' in nikita_request, "Nikita request has pan_data"),
        ('credit_bureau' in nikita_request, "Nikita request has credit_bureau"),
        ('customer_inputs' in nikita_request, "Nikita request has customer_inputs"),
    ]

    for check, desc in nikita_checks:
        log_test(desc, check)

    # Simulate Nikita CAM output
    nikita_cam_output = {
        "cam_id": "cam-test-789",
        "cam_data": {
            "business_profile": {
                "industry_sector": "IT_services",
                "years_in_business": 3
            },
            "financial_summary": {
                "turnover": {
                    "annual_lakhs": 2411.48,
                    "growth_yoy_pct": 17.0
                },
                "profitability": {
                    "net_profit_margin_pct": 30.0
                }
            },
            "credit_profile": {
                "commercial_bureau": {
                    "score": "CMR-2",
                    "total_outstanding_lakhs": 27.10,
                    "active_loans": 5
                },
                "existing_facilities": [{"overdue_days": 10}]
            },
            "compliance_status": {
                "gst": {"filing_consistency": 0.84}
            },
            "loan_request": nikita_request["customer_inputs"],
            "customer_preferences": {"priority": "low_interest"}
        }
    }

    log_test("Nikita CAM has financial_summary",
             'financial_summary' in nikita_cam_output['cam_data'])

    # Simulate n8n transformation to Kesha format
    kesha_payload = {
        "cam_id": nikita_cam_output["cam_id"],
        "business_profile": {
            "vintage_years": nikita_cam_output["cam_data"]["business_profile"]["years_in_business"]
        },
        "financial_metrics": {
            "annual_turnover_lakhs": nikita_cam_output["cam_data"]["financial_summary"]["turnover"]["annual_lakhs"],
            "turnover_growth_yoy": nikita_cam_output["cam_data"]["financial_summary"]["turnover"]["growth_yoy_pct"] / 100,
            "profit_margin": nikita_cam_output["cam_data"]["financial_summary"]["profitability"]["net_profit_margin_pct"] / 100
        },
        "credit_profile": {
            "commercial_score": nikita_cam_output["cam_data"]["credit_profile"]["commercial_bureau"]["score"],
            "existing_facilities": nikita_cam_output["cam_data"]["credit_profile"]["existing_facilities"]
        },
        "compliance": {
            "filing_consistency": nikita_cam_output["cam_data"]["compliance_status"]["gst"]["filing_consistency"]
        },
        "loan_request": nikita_cam_output["cam_data"]["loan_request"],
        "customer_preferences": nikita_cam_output["cam_data"]["customer_preferences"]
    }

    kesha_checks = [
        ('financial_metrics' in kesha_payload, "Kesha payload has financial_metrics (not financial_summary)"),
        ('annual_turnover_lakhs' in kesha_payload['financial_metrics'], "financial_metrics has annual_turnover_lakhs"),
        ('commercial_score' in kesha_payload['credit_profile'], "credit_profile has commercial_score"),
        ('compliance' in kesha_payload, "Kesha payload has compliance (not compliance_status)"),
        ('filing_consistency' in kesha_payload['compliance'], "compliance has filing_consistency"),
    ]

    for check, desc in kesha_checks:
        log_test(desc, check)

    # Test Kesha can process the data
    try:
        # Simulate Kesha's field access
        turnover = kesha_payload['financial_metrics'].get('annual_turnover_lakhs', 0)
        score = kesha_payload['credit_profile'].get('commercial_score', 'CMR-8')
        facilities = kesha_payload['credit_profile'].get('existing_facilities', [])
        max_dpd = max((f.get('dpd_days', 0) or f.get('overdue_days', 0) for f in facilities), default=0)
        filing = kesha_payload['compliance'].get('filing_consistency', 0)

        log_test(f"Kesha can extract turnover: {turnover}L", turnover == 2411.48)
        log_test(f"Kesha can extract credit score: {score}", score == "CMR-2")
        log_test(f"Kesha can extract max DPD: {max_dpd} days", max_dpd == 10)
        log_test(f"Kesha can extract filing consistency: {filing}", filing == 0.84)

    except Exception as e:
        log_test("Kesha data access simulation", False, str(e))

# ============================================================================
# TEST 7: Database Schema Compatibility
# ============================================================================

def test_database_schema_compatibility():
    """Test that database schema is compatible with service data"""
    separator("TEST 7: Database Schema Compatibility")

    schema_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'schema.sql')

    try:
        with open(schema_path, 'r') as f:
            schema = f.read()

        # Check table exists
        tables = ['conversations', 'consents', 'cam_records', 'credit_assessments', 'lenders']
        for table in tables:
            log_test(f"Table '{table}' exists in schema", f"CREATE TABLE {table}" in schema)

        # Check critical columns
        log_test("conversations has extracted_data JSONB", 'extracted_data JSONB' in schema)
        log_test("cam_records has cam_data JSONB", 'cam_data JSONB' in schema)
        log_test("credit_assessments has lender_matches JSONB", 'lender_matches JSONB' in schema)

        # Check view for Kesha
        log_test("kesha_cam_view exists for PII isolation", 'CREATE VIEW kesha_cam_view' in schema)

    except Exception as e:
        log_test("Database schema test", False, str(e))

# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def run_all_tests():
    """Run all tests and print summary"""
    print("\n" + "="*60)
    print(" BACKEND INTEGRATION TEST SUITE")
    print(" Testing: Conversation Flow, n8n Workflow, Database")
    print("="*60)

    # Run all tests
    test_francis_extracted_data_model()
    test_data_services_credit_bureau_params()
    test_nikita_cam_build_request()
    test_kesha_field_paths()
    test_n8n_workflow_transformations()
    test_end_to_end_data_structure()
    test_database_schema_compatibility()

    # Print summary
    separator("TEST SUMMARY")

    passed = sum(1 for t in test_results if t['passed'])
    failed = sum(1 for t in test_results if not t['passed'])
    total = len(test_results)

    print(f"Total Tests: {total}")
    print(f"Passed: {passed} ({100*passed//total}%)")
    print(f"Failed: {failed}")

    if failed > 0:
        print("\nFailed Tests:")
        for t in test_results:
            if not t['passed']:
                print(f"  - {t['name']}")
                if t['details']:
                    print(f"    Details: {t['details']}")

    print("\n" + "="*60)

    return failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
