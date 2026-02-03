#!/usr/bin/env python3
"""
Main entry point for the Blog Writing Agent.
Loads environment and starts the Streamlit UI.
This is a simplified wrapper - use app.py with Streamlit directly.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

if __name__ == "__main__":
    print("To run the Blog Writing Agent:")
    print("  streamlit run app.py")
    print("")
    print("Or use the run script:")
    print("  Windows: .\\run.ps1")
    print("  Linux/Mac: make venv-run")
