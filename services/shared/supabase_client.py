"""
Supabase Database Client
Shared database operations for all microservices
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import os
import json

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    Client = None

# Environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# Global client
_supabase_client: Optional[Any] = None


def get_client() -> Optional[Any]:
    """Get or create Supabase client"""
    global _supabase_client
    
    if not SUPABASE_AVAILABLE:
        return None
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    
    if _supabase_client is None:
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    return _supabase_client


class ConversationDB:
    """Database operations for conversations"""
    
    @staticmethod
    def create(
        customer_id: str,
        channel: str = "web",
        initial_data: Optional[Dict] = None
    ) -> Optional[Dict]:
        """Create a new conversation"""
        client = get_client()
        if not client:
            return None
        
        try:
            data = {
                "customer_id": customer_id,
                "channel": channel,
                "status": "active",
                "current_phase": "intake",
                "message_history": [],
                "extracted_data": initial_data or {}
            }
            
            result = client.table("conversations").insert(data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error creating conversation: {e}")
            return None
    
    @staticmethod
    def get(conversation_id: str) -> Optional[Dict]:
        """Get conversation by ID"""
        client = get_client()
        if not client:
            return None
        
        try:
            result = client.table("conversations").select("*").eq("id", conversation_id).single().execute()
            return result.data
        except Exception as e:
            print(f"Error getting conversation: {e}")
            return None
    
    @staticmethod
    def update(
        conversation_id: str,
        updates: Dict[str, Any]
    ) -> Optional[Dict]:
        """Update conversation"""
        client = get_client()
        if not client:
            return None
        
        try:
            result = client.table("conversations").update(updates).eq("id", conversation_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error updating conversation: {e}")
            return None
    
    @staticmethod
    def add_message(
        conversation_id: str,
        role: str,
        content: str
    ) -> bool:
        """Add message to conversation history"""
        client = get_client()
        if not client:
            return False
        
        try:
            # Get current messages
            conv = ConversationDB.get(conversation_id)
            if not conv:
                return False
            
            messages = conv.get("message_history", [])
            messages.append({
                "role": role,
                "content": content,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Update with new message
            client.table("conversations").update({
                "message_history": messages,
                "last_message_at": datetime.utcnow().isoformat()
            }).eq("id", conversation_id).execute()
            
            return True
        except Exception as e:
            print(f"Error adding message: {e}")
            return False


class ConsentDB:
    """Database operations for consents"""
    
    @staticmethod
    def create(
        conversation_id: str,
        consent_type: str,
        granted: bool,
        capture_method: str = "text",
        ip_address: Optional[str] = None,
        device_info: Optional[Dict] = None,
        customer_id: Optional[str] = None
    ) -> Optional[Dict]:
        """Create consent record for DPDP Act 2023 compliance"""
        client = get_client()
        if not client:
            return None

        try:
            # Get customer_id from conversation if not provided
            if not customer_id:
                conv = ConversationDB.get(conversation_id)
                customer_id = conv.get("customer_id") if conv else conversation_id

            data = {
                "conversation_id": conversation_id,
                "customer_id": customer_id,
                "consent_type": consent_type,
                "granted": granted,
                "method": capture_method,  # Schema uses 'method' not 'capture_method'
                "ip_address": ip_address,
                "device_info": device_info or {}
            }

            result = client.table("consents").insert(data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error creating consent: {e}")
            return None
    
    @staticmethod
    def get_by_conversation(conversation_id: str) -> List[Dict]:
        """Get all consents for a conversation"""
        client = get_client()
        if not client:
            return []
        
        try:
            result = client.table("consents").select("*").eq("conversation_id", conversation_id).execute()
            return result.data or []
        except Exception as e:
            print(f"Error getting consents: {e}")
            return []


class CAMRecordDB:
    """Database operations for CAM records"""
    
    @staticmethod
    def create(
        conversation_id: str,
        gstin: str,
        pan: str,
        entity_name: str,
        cam_data: Dict,
        annual_turnover_lakhs: float,
        credit_score: Optional[int] = None,
        missing_fields: List[str] = None,
        data_flags: List[Dict] = None
    ) -> Optional[Dict]:
        """Create CAM record"""
        client = get_client()
        if not client:
            return None
        
        try:
            data = {
                "conversation_id": conversation_id,
                "gstin": gstin,
                "pan": pan,
                "entity_name": entity_name,
                "cam_data": cam_data,
                "annual_turnover_lakhs": annual_turnover_lakhs,
                "credit_score": credit_score,
                "missing_fields": missing_fields or [],
                "data_flags": data_flags or [],
                "status": "pending"
            }
            
            result = client.table("cam_records").insert(data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error creating CAM record: {e}")
            return None
    
    @staticmethod
    def get(cam_id: str) -> Optional[Dict]:
        """Get CAM record by ID"""
        client = get_client()
        if not client:
            return None
        
        try:
            result = client.table("cam_records").select("*").eq("id", cam_id).single().execute()
            return result.data
        except Exception as e:
            print(f"Error getting CAM record: {e}")
            return None
    
    @staticmethod
    def update_status(cam_id: str, status: str) -> bool:
        """Update CAM status"""
        client = get_client()
        if not client:
            return False
        
        try:
            client.table("cam_records").update({"status": status}).eq("id", cam_id).execute()
            return True
        except Exception as e:
            print(f"Error updating CAM status: {e}")
            return False


class CreditAssessmentDB:
    """Database operations for credit assessments"""

    @staticmethod
    def create(
        cam_id: str,
        conversation_id: str,
        overall_eligibility: str,
        max_eligible_amount_lakhs: float,
        lender_matches: List[Dict],
        customer_report: Dict
    ) -> Optional[Dict]:
        """Create credit assessment record"""
        client = get_client()
        if not client:
            return None

        try:
            data = {
                "cam_id": cam_id,
                "conversation_id": conversation_id,
                "overall_eligibility": overall_eligibility,
                "max_eligible_amount_lakhs": max_eligible_amount_lakhs,
                "lender_matches": lender_matches,
                "assessment_data": {},
                "customer_report": customer_report
            }

            result = client.table("credit_assessments").insert(data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error creating credit assessment: {e}")
            return None
    
    @staticmethod
    def get_by_cam(cam_id: str) -> Optional[Dict]:
        """Get assessment by CAM ID"""
        client = get_client()
        if not client:
            return None
        
        try:
            result = client.table("credit_assessments").select("*").eq("cam_id", cam_id).single().execute()
            return result.data
        except Exception as e:
            print(f"Error getting credit assessment: {e}")
            return None


class AuditLogDB:
    """Database operations for audit logging"""
    
    @staticmethod
    def log(
        action: str,
        entity_type: str,
        entity_id: str,
        actor_id: str,
        actor_type: str = "system",
        details: Optional[Dict] = None,
        ip_address: Optional[str] = None
    ) -> bool:
        """Create audit log entry"""
        client = get_client()
        if not client:
            return False
        
        try:
            data = {
                "action": action,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "actor_id": actor_id,
                "actor_type": actor_type,
                "details": details or {},
                "ip_address": ip_address
            }
            
            client.table("audit_log").insert(data).execute()
            return True
        except Exception as e:
            print(f"Error creating audit log: {e}")
            return False


class LenderDB:
    """Database operations for lenders"""
    
    @staticmethod
    def get_all_active() -> List[Dict]:
        """Get all active lenders"""
        client = get_client()
        if not client:
            return []
        
        try:
            result = client.table("lenders").select("*").eq("status", "active").execute()
            return result.data or []
        except Exception as e:
            print(f"Error getting lenders: {e}")
            return []
    
    @staticmethod
    def get(lender_id: str) -> Optional[Dict]:
        """Get lender by ID"""
        client = get_client()
        if not client:
            return None
        
        try:
            result = client.table("lenders").select("*").eq("id", lender_id).single().execute()
            return result.data
        except Exception as e:
            print(f"Error getting lender: {e}")
            return None


class LenderSubmissionDB:
    """Database operations for lender submissions"""
    
    @staticmethod
    def create(
        assessment_id: str,
        lender_id: str,
        submitted_amount_lakhs: float,
        submitted_data: Dict
    ) -> Optional[Dict]:
        """Create lender submission record"""
        client = get_client()
        if not client:
            return None
        
        try:
            data = {
                "assessment_id": assessment_id,
                "lender_id": lender_id,
                "submitted_amount_lakhs": submitted_amount_lakhs,
                "submitted_data": submitted_data,
                "status": "pending"
            }
            
            result = client.table("lender_submissions").insert(data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error creating lender submission: {e}")
            return None
    
    @staticmethod
    def update_status(
        submission_id: str,
        status: str,
        lender_response: Optional[Dict] = None
    ) -> bool:
        """Update submission status"""
        client = get_client()
        if not client:
            return False
        
        try:
            updates = {"status": status}
            if lender_response:
                updates["lender_response"] = lender_response
            
            client.table("lender_submissions").update(updates).eq("id", submission_id).execute()
            return True
        except Exception as e:
            print(f"Error updating submission status: {e}")
            return False


# Test connection
def test_connection() -> bool:
    """Test Supabase connection"""
    client = get_client()
    if not client:
        return False
    
    try:
        # Simple query to test connection
        client.table("lenders").select("id").limit(1).execute()
        return True
    except Exception as e:
        print(f"Supabase connection test failed: {e}")
        return False
