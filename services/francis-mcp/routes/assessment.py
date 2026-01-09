"""
Assessment result receiver endpoint
Handles results from Kesha MCP after credit assessment
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Assessment"])

class AssessmentResult(BaseModel):
    conversation_id: str
    assessment_id: str
    overall_eligibility: str
    max_eligible_amount: float
    top_lenders: List[str]
    customer_report: Dict[str, Any]

class AssessmentResponse(BaseModel):
    success: bool
    message_to_customer: str

@router.post("/receive-assessment", response_model=AssessmentResponse)
async def receive_assessment(result: AssessmentResult):
    """
    Receive assessment results from Kesha (via n8n workflow)

    This endpoint:
    - Receives lender matches and eligibility
    - Formats customer-friendly message
    - Updates conversation state
    - Can be modified to change messaging without restarting other endpoints
    """
    try:
        logger.info(f"Received assessment for conversation: {result.conversation_id}")

        # Format message based on eligibility (supports multilingual with templates)
        if result.overall_eligibility == "high":
            message = f"""🎉 Great news! Based on your business profile, you're eligible for up to ₹{result.max_eligible_amount}L.

**Top Lender Options:**
{chr(10).join(f'{i+1}. {lender}' for i, lender in enumerate(result.top_lenders[:3]))}

**Your Strengths:**
{chr(10).join(f'✓ {s}' for s in result.customer_report.get('strengths', []))}

**Next Steps:**
{chr(10).join(f'{i+1}. {step}' for i, step in enumerate(result.customer_report.get('next_steps', [])))}

Would you like to proceed with any of these lenders?

---

🎉 बढ़िया खबर! आपके व्यवसाय प्रोफ़ाइल के आधार पर, आप ₹{result.max_eligible_amount}L तक के लिए पात्र हैं।"""

        elif result.overall_eligibility == "medium":
            message = f"""Good news! You're eligible for up to ₹{result.max_eligible_amount}L.

**Available Lenders:**
{chr(10).join(f'{i+1}. {lender}' for i, lender in enumerate(result.top_lenders))}

**Your Profile:**
{chr(10).join(f'✓ {s}' for s in result.customer_report.get('strengths', []))}

**To Improve Your Eligibility:**
{chr(10).join(f'• {imp}' for imp in result.customer_report.get('improvements', []))}

Would you like to proceed with the application?"""

        elif result.overall_eligibility == "low":
            message = f"""Thank you for your application. Based on current assessment, you have limited options with an eligibility of up to ₹{result.max_eligible_amount}L.

**Available Options:**
{chr(10).join(f'{i+1}. {lender}' for i, lender in enumerate(result.top_lenders)) if result.top_lenders else 'Currently no lenders available'}

**To Improve Your Chances:**
{chr(10).join(f'• {imp}' for imp in result.customer_report.get('improvements', []))}

We recommend working on these areas and reapplying in 3-6 months. Would you like guidance on improving your credit profile?"""

        else:  # ineligible
            message = f"""Thank you for your interest. Unfortunately, based on current criteria, you don't meet the minimum requirements for our lending partners at this time.

**Recommended Actions:**
{chr(10).join(f'• {imp}' for imp in result.customer_report.get('improvements', []))}

We recommend working on these areas for 3-6 months. Our team can provide guidance on improving your business's financial profile. Would you like to speak with a credit advisor?"""

        # In production, this would update the conversation in database
        # and potentially send notification via WhatsApp/Email

        return AssessmentResponse(
            success=True,
            message_to_customer=message
        )

    except Exception as e:
        logger.error(f"Error processing assessment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
