#!/usr/bin/env python3
"""
Main entry point for the Blog Writing Agent Streamlit UI.
This wrapper ensures proper imports when running from the project root.
"""

import os
import sys
from pathlib import Path

# CRITICAL: Load environment variables FIRST before any imports
from dotenv import load_dotenv

# Get project root and load .env
project_root = Path(__file__).parent
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)

# Verify API key is loaded
if not os.getenv("OPENAI_API_KEY"):
    print("=" * 60)
    print("ERROR: OPENAI_API_KEY not found!")
    print("=" * 60)
    print(f"Checked .env file at: {env_path}")
    print(f"File exists: {env_path.exists()}")
    print("")
    print("Please ensure your .env file contains:")
    print("OPENAI_API_KEY=sk-your-key-here")
    print("=" * 60)
    sys.exit(1)

# Add project root to path
sys.path.insert(0, str(project_root))

# Run the Streamlit app
if __name__ == "__main__":
    from src.ui.app import main
    main()
