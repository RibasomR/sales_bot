#!/usr/bin/env python3
"""
Test script for Whisper.cpp integration.

Verifies that pywhispercpp is installed correctly and can load models.
Run this script after migration to ensure everything works.

:author: Finance Bot Team
:date: 2025-10-23
"""

import sys
from pathlib import Path


def test_import():
    """
    Test if pywhispercpp can be imported.
    
    :return: True if import succeeds
    :rtype: bool
    """
    try:
        from pywhispercpp.model import Model
        print("✅ pywhispercpp import successful")
        return True
    except ImportError as e:
        print(f"❌ Failed to import pywhispercpp: {e}")
        print("\n💡 Install with: pip install pywhispercpp")
        return False


def test_model_loading():
    """
    Test if Whisper.cpp model can be loaded.
    
    :return: True if model loads successfully
    :rtype: bool
    """
    try:
        from pywhispercpp.model import Model
        
        print("\n📦 Attempting to load Whisper.cpp model (this may download it)...")
        model = Model(model="base", n_threads=2)
        print("✅ Model loaded successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to load model: {e}")
        print("\n💡 Model will be auto-downloaded on first use")
        print("   This is normal if running for the first time")
        return False


def test_config():
    """
    Test if configuration is set up correctly.
    
    :return: True if config is valid
    :rtype: bool
    """
    try:
        import os
        from dotenv import load_dotenv
        
        load_dotenv()
        
        print("\n⚙️ Checking configuration...")
        
        whisper_model = os.getenv("WHISPER_MODEL", "base")
        whisper_threads = os.getenv("WHISPER_THREADS", "4")
        
        print(f"   WHISPER_MODEL: {whisper_model}")
        print(f"   WHISPER_THREADS: {whisper_threads}")
        
        # Check if old config exists
        whisper_device = os.getenv("WHISPER_DEVICE")
        if whisper_device:
            print("\n⚠️  Warning: WHISPER_DEVICE is set but no longer used")
            print("   Remove it from .env and use WHISPER_THREADS instead")
            return False
        
        print("✅ Configuration is correct")
        return True
        
    except Exception as e:
        print(f"❌ Configuration check failed: {e}")
        return False


def main():
    """
    Main test function.
    
    Runs all tests and reports results.
    """
    print("🧪 Testing Whisper.cpp integration...\n")
    print("=" * 50)
    
    results = []
    
    # Test 1: Import
    results.append(("Import", test_import()))
    
    # Test 2: Config
    results.append(("Configuration", test_config()))
    
    # Test 3: Model loading (optional, may take time)
    print("\n" + "=" * 50)
    print("\n📝 Note: Model loading test will download ~150MB on first run")
    response = input("Run model loading test? (y/N): ").strip().lower()
    
    if response == 'y':
        results.append(("Model Loading", test_model_loading()))
    else:
        print("⏭️  Skipping model loading test")
    
    # Summary
    print("\n" + "=" * 50)
    print("\n📊 Test Summary:")
    print("-" * 50)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:20s}: {status}")
    
    print("-" * 50)
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n🎉 All tests passed! Whisper.cpp is ready to use.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

