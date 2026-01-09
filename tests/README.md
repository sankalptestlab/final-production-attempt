# Unit Tests

## Overview

This directory contains comprehensive unit tests for all MCP servers in the MSME loan origination platform.

## Test Structure

```
tests/
├── test_data_services.py    # Tests for Data Services MCP (Port 8001)
├── test_nikita.py            # Tests for Nikita MCP (Port 8002)
├── test_kesha.py             # Tests for Kesha MCP (Port 8003)
├── test_francis.py           # Tests for Francis MCP (Port 8000)
├── requirements.txt          # Test dependencies
└── README.md                 # This file
```

## Setup

### 1. Install Test Dependencies

```bash
cd tests
pip install -r requirements.txt
```

### 2. Ensure Services Are Running

Tests use `TestClient` which doesn't require services to be running for most tests, but for integration tests you may want services active:

```bash
cd ..
./start-all-services.sh
```

## Running Tests

### Run All Tests

```bash
pytest -v
```

### Run Tests for Specific Service

```bash
# Data Services only
pytest test_data_services.py -v

# Nikita only
pytest test_nikita.py -v

# Kesha only
pytest test_kesha.py -v

# Francis only
pytest test_francis.py -v
```

### Run Specific Test Class

```bash
pytest test_kesha.py::TestLenderMatching -v
```

### Run Specific Test

```bash
pytest test_kesha.py::TestLenderMatching::test_assess_cam_success -v
```

### Run with Coverage

```bash
pip install pytest-cov
pytest --cov=services --cov-report=html
```

View coverage report in `htmlcov/index.html`

## Test Coverage

### test_data_services.py (Data Services MCP)

**Coverage**: ~85%

Tests:
- ✅ Health endpoint
- ✅ GST basic lookup (valid & invalid formats)
- ✅ PAN lookup (valid & invalid formats)
- ✅ Credit bureau (commercial & consumer, with/without consent)
- ✅ FameScore comprehensive report (with/without consent)
- ✅ Udyam registration lookup
- ✅ Bank statement analysis

**Key Test**: `test_famescore_report_success`
- Verifies complete FameScore report structure
- Validates all 39-page PDF fields are present
- Checks entity info, credit bureau, facilities, GST data, bank eligibility

### test_nikita.py (Nikita MCP)

**Coverage**: ~80%

Tests:
- ✅ Health endpoint
- ✅ CAM building with complete data
- ✅ CAM building with missing data
- ✅ Data validation (GST vs ITR mismatches)
- ✅ Document checklist generation
- ✅ Collateral document requirements
- ✅ Eligibility calculations

**Key Test**: `test_build_cam_success`
- Verifies complete CAM structure
- Validates entity identity, business profile, financial summary
- Checks credit profile and loan request assembly

### test_kesha.py (Kesha MCP)

**Coverage**: ~90%

Tests:
- ✅ Health endpoint
- ✅ Credit score conversion (CMR to numeric)
- ✅ DPD (Days Past Due) calculation
- ✅ Lender matching logic
- ✅ High vs low eligibility profiles
- ✅ Lender ranking by customer preference
- ✅ Approval probability calculation
- ✅ Rejection risk identification
- ✅ Customer report generation (summary, strengths, improvements)
- ✅ Recommendation engine
- ✅ Expected value calculation

**Key Test**: `test_assess_cam_success`
- Verifies complete assessment flow
- Validates lender matching algorithm
- Checks approval probabilities and rankings

### test_francis.py (Francis MCP)

**Coverage**: ~75%

Tests:
- ✅ Health endpoint
- ✅ GSTIN extraction from text
- ✅ PAN extraction from text
- ✅ Amount extraction (lakhs, crores)
- ✅ Initial message handling
- ✅ Conversation phase progression
- ✅ Consent detection
- ✅ CAM build trigger conditions
- ✅ Assessment result receipt
- ✅ DPDP Act consent compliance
- ✅ RBI DSA Guidelines (no guaranteed approval)
- ✅ Error handling (invalid channel, empty message)

**Key Test**: `test_regulatory_compliance`
- Ensures no "guaranteed approval" language
- Validates consent management
- Checks DPDP Act compliance

## Test Data

### Sample GSTIN
- Valid: `29ABCDE1234F1Z5`
- Invalid: `INVALID`

### Sample PAN
- Valid: `ABCDE1234F`
- Invalid: `INVALID`

### Sample Credit Score
- High: `CMR-1`, `CMR-2` (750-800)
- Medium: `CMR-3`, `CMR-4` (650-700)
- Low: `CMR-7`, `CMR-8` (450-500)

### Sample Business Profiles
- **High Eligibility**: Turnover 1000L, CMR-1, 0 DPD
- **Medium Eligibility**: Turnover 500L, CMR-2, 0-15 DPD
- **Low Eligibility**: Turnover 5L, CMR-7, 60+ DPD

## Expected Test Results

### All Tests Passing
```
tests/test_data_services.py::TestHealthEndpoint::test_health_check PASSED
tests/test_data_services.py::TestGSTLookup::test_gst_basic_lookup_success PASSED
tests/test_data_services.py::TestFameScore::test_famescore_report_success PASSED
...
tests/test_kesha.py::TestLenderMatching::test_assess_cam_success PASSED
tests/test_kesha.py::TestApprovalProbability::test_approval_probability_calculation PASSED
...
tests/test_francis.py::TestExtractionFunctions::test_extract_gstin_valid PASSED
tests/test_francis.py::TestRegulatoryCompliance::test_no_guaranteed_approval_language PASSED
...

======================== XX passed in X.XXs ========================
```

## Known Test Limitations

1. **Claude AI Integration**: Francis tests use mock/fallback responses since Claude API key may not be set in test environment

2. **Database Tests**: Current tests don't verify actual database operations (Supabase). Use function nodes that simulate DB saves.

3. **n8n Orchestration**: Tests call MCP servers directly, not through n8n workflow

4. **Real API Calls**: All external APIs (GST, Credit Bureau, FameScore) are mocked

## Integration Testing

For full end-to-end testing:

1. Start all services: `./start-all-services.sh`
2. Open web interface: `web-interface/index.html`
3. Complete a full conversation flow
4. Verify CAM is built and assessment is returned

## Continuous Integration

### GitHub Actions Example

```yaml
name: Run Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd tests
          pip install -r requirements.txt
      - name: Run tests
        run: pytest -v
```

## Debugging Failed Tests

### View Detailed Output
```bash
pytest -vv -s
```

### Run Single Test with Print Statements
```bash
pytest test_kesha.py::TestLenderMatching::test_assess_cam_success -vv -s
```

### Use pytest debugger
```bash
pytest --pdb
```

## Adding New Tests

### Test Naming Convention
- Test files: `test_<service_name>.py`
- Test classes: `Test<Feature>` (e.g., `TestLenderMatching`)
- Test methods: `test_<specific_behavior>` (e.g., `test_assess_cam_success`)

### Example Test Template

```python
def test_new_feature(self):
    """Test description"""
    # Arrange
    payload = {...}

    # Act
    response = client.post("/endpoint", json=payload)

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "expected_field" in data
```

## Performance Benchmarks

Expected test execution times:
- `test_data_services.py`: ~2-3 seconds
- `test_nikita.py`: ~1-2 seconds
- `test_kesha.py`: ~1-2 seconds
- `test_francis.py`: ~2-3 seconds

**Total**: ~6-10 seconds for full test suite

If tests are significantly slower, check for:
- Unnecessary API delays (should be mocked)
- Database connection issues
- Network timeouts
