"""
Database module for Francis MCP - Supabase integration
Handles conversation persistence and state management
"""

import os
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import json

logger = logging.getLogger(__name__)

# Supabase client (initialized lazily)
_supabase_client = None

def get_supabase_client():
    """Get or create Supabase client"""
    global _supabase_client

    if _supabase_client is None:
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_KEY")

        if not supabase_url or not supabase_key:
            logger.warning("Supabase credentials not configured - running without persistence")
            return None

        try:
            from supabase import create_client
            _supabase_client = create_client(supabase_url, supabase_key)
            logger.info("Supabase client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            return None

    return _supabase_client


def get_or_create_conversation(
    conversation_id: str,
    customer_id: str,
    channel: str = "web"
) -> Optional[Dict[str, Any]]:
    """
    Get existing conversation or create a new one
    Returns the conversation record
    """
    client = get_supabase_client()
    if not client:
        return None

    try:
        # Try to get existing conversation
        result = client.table("conversations").select("*").eq("id", conversation_id).execute()

        if result.data and len(result.data) > 0:
            return result.data[0]

        # Create new conversation
        new_conversation = {
            "id": conversation_id,
            "customer_id": customer_id,
            "channel": channel,
            "status": "active",
            "current_phase": "intake",
            "message_history": [],
            "extracted_data": {},
            "preferences": {}
        }

        result = client.table("conversations").insert(new_conversation).execute()

        if result.data and len(result.data) > 0:
            logger.info(f"Created new conversation: {conversation_id}")
            return result.data[0]

        return None

    except Exception as e:
        logger.error(f"Error in get_or_create_conversation: {e}")
        return None


def update_conversation(
    conversation_id: str,
    extracted_data: Dict[str, Any] = None,
    current_phase: str = None,
    message_history: List[Dict] = None,
    preferences: Dict[str, Any] = None
) -> Optional[Dict[str, Any]]:
    """
    Update conversation with new data
    """
    client = get_supabase_client()
    if not client:
        return None

    try:
        updates = {"updated_at": datetime.now().isoformat()}

        if extracted_data is not None:
            updates["extracted_data"] = extracted_data
        if current_phase is not None:
            updates["current_phase"] = current_phase
        if message_history is not None:
            updates["message_history"] = message_history
        if preferences is not None:
            updates["preferences"] = preferences

        result = client.table("conversations").update(updates).eq("id", conversation_id).execute()

        if result.data and len(result.data) > 0:
            return result.data[0]

        return None

    except Exception as e:
        logger.error(f"Error updating conversation: {e}")
        return None


def append_message(
    conversation_id: str,
    role: str,
    content: str
) -> bool:
    """
    Append a message to conversation history
    """
    client = get_supabase_client()
    if not client:
        return False

    try:
        # Get current conversation
        result = client.table("conversations").select("message_history").eq("id", conversation_id).execute()

        if not result.data or len(result.data) == 0:
            return False

        history = result.data[0].get("message_history", []) or []
        history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })

        # Update with new history
        client.table("conversations").update({
            "message_history": history,
            "last_message_at": datetime.now().isoformat()
        }).eq("id", conversation_id).execute()

        return True

    except Exception as e:
        logger.error(f"Error appending message: {e}")
        return False


def save_consent(
    conversation_id: str,
    customer_id: str,
    consent_type: str,
    granted: bool,
    method: str = "explicit_yes"
) -> Optional[Dict[str, Any]]:
    """
    Save a consent record
    """
    client = get_supabase_client()
    if not client:
        return None

    try:
        consent = {
            "conversation_id": conversation_id,
            "customer_id": customer_id,
            "consent_type": consent_type,
            "granted": granted,
            "method": method
        }

        result = client.table("consents").insert(consent).execute()

        if result.data and len(result.data) > 0:
            logger.info(f"Saved consent: {consent_type} = {granted}")
            return result.data[0]

        return None

    except Exception as e:
        logger.error(f"Error saving consent: {e}")
        return None


def get_conversation_state(conversation_id: str) -> Optional[Dict[str, Any]]:
    """
    Get full conversation state including extracted data
    """
    client = get_supabase_client()
    if not client:
        return None

    try:
        result = client.table("conversations").select("*").eq("id", conversation_id).execute()

        if result.data and len(result.data) > 0:
            return result.data[0]

        return None

    except Exception as e:
        logger.error(f"Error getting conversation state: {e}")
        return None


def get_consents_for_conversation(conversation_id: str) -> List[Dict[str, Any]]:
    """
    Get all consents for a conversation
    """
    client = get_supabase_client()
    if not client:
        return []

    try:
        result = client.table("consents").select("*").eq("conversation_id", conversation_id).execute()
        return result.data or []

    except Exception as e:
        logger.error(f"Error getting consents: {e}")
        return []
