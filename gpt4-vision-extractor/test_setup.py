"""
Test script to verify the receipt extractor setup.
This script checks if all dependencies are installed and configured correctly.
"""

import sys
import os
from pathlib import Path


def check_python_version():
    """Check if Python version is 3.8 or higher."""
    print("Checking Python version...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"✓ Python {version.major}.{version.minor}.{version.micro} (OK)")
        return True
    else:
        print(f"✗ Python {version.major}.{version.minor}.{version.micro} (Need 3.8+)")
        return False


def check_dependencies():
    """Check if required packages are installed."""
    print("\nChecking dependencies...")
    required_packages = {
        'openai': 'OpenAI',
        'dotenv': 'python-dotenv',
        'PIL': 'Pillow'
    }
    
    all_installed = True
    for module, package_name in required_packages.items():
        try:
            __import__(module)
            print(f"✓ {package_name} installed")
        except ImportError:
            print(f"✗ {package_name} not installed")
            all_installed = False
    
    return all_installed


def check_env_file():
    """Check if .env file exists and has API key."""
    print("\nChecking environment configuration...")
    
    if not os.path.exists('.env'):
        print("✗ .env file not found")
        print("  Run: cp .env.example .env")
        return False
    
    print("✓ .env file exists")
    
    # Check if API key is set
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key or api_key == 'your_openai_api_key_here':
        print("✗ OPENAI_API_KEY not configured in .env")
        print("  Please add your OpenAI API key to .env file")
        return False
    
    print("✓ OPENAI_API_KEY is configured")
    return True


def check_directories():
    """Check if required directories exist."""
    print("\nChecking directories...")
    
    directories = ['receipts', 'output']
    all_exist = True
    
    for directory in directories:
        if os.path.exists(directory):
            print(f"✓ {directory}/ directory exists")
        else:
            print(f"⚠ {directory}/ directory not found (will be created)")
            os.makedirs(directory, exist_ok=True)
            print(f"  Created {directory}/ directory")
    
    return True


def check_receipt_files():
    """Check if there are any receipt files to process."""
    print("\nChecking for receipt images...")
    
    receipts_dir = Path('receipts')
    image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']
    
    image_files = []
    for ext in image_extensions:
        image_files.extend(receipts_dir.glob(f"*{ext}"))
        image_files.extend(receipts_dir.glob(f"*{ext.upper()}"))
    
    if image_files:
        print(f"✓ Found {len(image_files)} receipt image(s)")
        for img in image_files[:5]:  # Show first 5
            print(f"  - {img.name}")
        if len(image_files) > 5:
            print(f"  ... and {len(image_files) - 5} more")
        return True
    else:
        print("⚠ No receipt images found in receipts/ directory")
        print("  Add some receipt images to test the extractor")
        return False


def test_import():
    """Test if the receipt extractor can be imported."""
    print("\nTesting module imports...")
    
    try:
        from receipt_extractor import ReceiptExtractor
        print("✓ receipt_extractor module imported successfully")
        
        from batch_processor import BatchReceiptProcessor
        print("✓ batch_processor module imported successfully")
        
        return True
    except Exception as e:
        print(f"✗ Error importing modules: {e}")
        return False


def main():
    """Run all checks."""
    print("=" * 60)
    print("RECEIPT EXTRACTOR - SETUP VERIFICATION")
    print("=" * 60)
    print()
    
    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_dependencies),
        ("Environment File", check_env_file),
        ("Directories", check_directories),
        ("Receipt Files", check_receipt_files),
        ("Module Imports", test_import)
    ]
    
    results = {}
    for check_name, check_func in checks:
        try:
            results[check_name] = check_func()
        except Exception as e:
            print(f"✗ Error during {check_name} check: {e}")
            results[check_name] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for check_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {check_name}")
    
    print(f"\nPassed: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 All checks passed! You're ready to use the receipt extractor.")
        print("\nQuick start:")
        print("  python receipt_extractor.py receipts/your_receipt.jpg")
    else:
        print("\n⚠️  Some checks failed. Please fix the issues above.")
        print("\nSetup instructions:")
        print("  1. Install dependencies: pip install -r requirements.txt")
        print("  2. Configure API key: cp .env.example .env (then edit .env)")
        print("  3. Add receipt images to receipts/ directory")
    
    print("=" * 60)
    print()
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
