"""
Health check endpoint
Can be updated independently without affecting other routes
"""

from fastapi import APIRouter
from datetime import datetime

router = APIRouter(tags=["Health"])

@router.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "service": "francis-mcp",
        "timestamp": datetime.now().isoformat()
    }
