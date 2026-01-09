"""
Francis MCP Server - Modular Architecture
Customer Interface Agent with hot-reloadable routes

Each endpoint is in a separate file for independent updates without server restart.
Supports hot-reload with uvicorn --reload
"""

# Load environment variables first
import load_env

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Francis MCP - Customer Interface",
    description="Multilingual customer-facing conversation and intent extraction agent",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include routers
# Each router is a separate file - can be updated independently
try:
    from routes import health, conversation, assessment

    app.include_router(health.router)
    app.include_router(conversation.router)
    app.include_router(assessment.router)

    logger.info("All routes loaded successfully")
except ImportError as e:
    logger.error(f"Failed to load routes: {e}")
    # Capture error message before scope ends
    _import_error = str(e)
    # Fallback to basic health check
    @app.get("/health")
    async def fallback_health():
        return {"status": "degraded", "error": _import_error}

# Root endpoint
@app.get("/")
async def root():
    return {
        "service": "Francis MCP",
        "version": "2.0.0",
        "description": "Multilingual Customer Interface Agent",
        "endpoints": {
            "health": "/health",
            "process_message": "/process-message",
            "receive_assessment": "/receive-assessment",
            "docs": "/docs"
        },
        "supported_languages": [
            "English", "Hindi", "Tamil", "Telugu", "Bengali",
            "Marathi", "Gujarati", "Kannada", "Malayalam",
            "Punjabi", "Urdu", "Odia", "and 90+ others"
        ],
        "features": [
            "Multilingual conversation (Claude AI)",
            "Automatic language detection",
            "DPDP Act 2023 compliant",
            "RBI DSA Guidelines compliant",
            "Hot-reloadable routes"
        ]
    }

if __name__ == "__main__":
    # Run with hot reload enabled
    # Changes to route files will automatically reload without restarting server
    uvicorn.run(
        "main_modular:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Enable hot reload
        reload_dirs=["routes", "utils"],  # Watch these directories for changes
        log_level="info"
    )
