/**
 * API Service for MSME Lending Platform
 * Handles all backend communication
 */

const API_BASE_URL = 'http://localhost:8000';

/**
 * Submit a loan application and get assessment results
 * @param {Object} applicationData - The loan application data
 * @returns {Promise<Object>} - Assessment results with lender matches
 */
export async function submitLoanApplication(applicationData) {
    const response = await fetch(`${API_BASE_URL}/loan/submit`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            gstin: applicationData.gstNumber,
            pan: applicationData.panNumber,
            loan_amount_lakhs: applicationData.loanAmount,
            loan_purpose: applicationData.loanPurpose,
            tenure_months: applicationData.tenure || 36,
            priority: applicationData.priority || 'low_interest',
            has_collateral: applicationData.hasCollateral || false,
            consent_credit_bureau: applicationData.consents?.creditBureau || true,
            consent_data_sharing: applicationData.consents?.dataSharing || true,
        }),
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to submit application');
    }

    return response.json();
}

/**
 * Get application status by ID
 * @param {string} applicationId - The application ID
 * @returns {Promise<Object>} - Application status
 */
export async function getApplicationStatus(applicationId) {
    const response = await fetch(`${API_BASE_URL}/loan/status/${applicationId}`);

    if (!response.ok) {
        throw new Error('Failed to fetch application status');
    }

    return response.json();
}

/**
 * Verify GST number
 * @param {string} gstin - The GST number to verify
 * @returns {Promise<Object>} - Verification result
 */
export async function verifyGST(gstin) {
    const response = await fetch('http://localhost:8001/verify-gst', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ gstin }),
    });

    if (!response.ok) {
        throw new Error('GST verification failed');
    }

    return response.json();
}

/**
 * Verify PAN number
 * @param {string} pan - The PAN number to verify
 * @returns {Promise<Object>} - Verification result
 */
export async function verifyPAN(pan) {
    const response = await fetch('http://localhost:8001/verify-pan', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ pan }),
    });

    if (!response.ok) {
        throw new Error('PAN verification failed');
    }

    return response.json();
}

/**
 * Health check for all services
 * @returns {Promise<Object>} - Health status of all services
 */
export async function checkHealth() {
    const services = [
        { name: 'Francis', url: 'http://localhost:8000/health' },
        { name: 'Data Services', url: 'http://localhost:8001/health' },
        { name: 'Nikita', url: 'http://localhost:8002/health' },
        { name: 'Kesha', url: 'http://localhost:8003/health' },
    ];

    const results = await Promise.all(
        services.map(async (service) => {
            try {
                const response = await fetch(service.url);
                const data = await response.json();
                return { ...service, status: data.status, healthy: data.status === 'healthy' };
            } catch {
                return { ...service, status: 'unreachable', healthy: false };
            }
        })
    );

    return results;
}

export default {
    submitLoanApplication,
    getApplicationStatus,
    verifyGST,
    verifyPAN,
    checkHealth,
};
