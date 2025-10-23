"""
Local test script for Docker healthcheck.

Tests the healthcheck logic without Docker to verify it works correctly.
"""

import os
import sys
from pathlib import Path

## Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

## Load environment variables
load_dotenv()

## Import and run healthcheck
from healthcheck import main

if __name__ == "__main__":
    print("Testing healthcheck script...")
    print(f"BOT_TOKEN present: {'Yes' if os.getenv('BOT_TOKEN') else 'No'}")
    print("-" * 50)
    
    exit_code = main()
    
    print("-" * 50)
    if exit_code == 0:
        print("✅ Healthcheck PASSED")
    else:
        print("❌ Healthcheck FAILED")
    
    sys.exit(exit_code)

