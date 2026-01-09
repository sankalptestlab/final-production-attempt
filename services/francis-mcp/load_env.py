"""
Load environment variables from .env file
"""
import os
from pathlib import Path

def load_env():
    """Load .env file from project root"""
    # Find project root (2 levels up from services/francis-mcp)
    project_root = Path(__file__).parent.parent.parent
    env_file = project_root / ".env"

    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
        print(f"✓ Loaded environment from {env_file}")
    else:
        print(f"⚠ No .env file found at {env_file}")

# Auto-load when imported
load_env()
