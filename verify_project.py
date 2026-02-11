#!/usr/bin/env python
"""Verify project structure and dependencies."""

import sys
from pathlib import Path


def check_structure():
    """Check if all required files and directories exist."""
    print("Checking project structure...")
    
    required_items = [
        # Root files
        "README.md",
        "INSTALL.md",
        "USAGE.md",
        "ARCHITECTURE.md",
        "config.yaml",
        "requirements.txt",
        "setup.py",
        "process_meeting.py",
        ".gitignore",
        
        # Source directories
        "src/__init__.py",
        "src/pipeline.py",
        "src/utils/__init__.py",
        "src/utils/config.py",
        "src/utils/logging.py",
        "src/audio/__init__.py",
        "src/audio/processor.py",
        "src/audio/transcript.py",
        "src/video/__init__.py",
        "src/video/processor.py",
        "src/fusion/__init__.py",
        "src/fusion/processor.py",
        "src/naming/__init__.py",
        "src/naming/extractor.py",
        "src/output/__init__.py",
        "src/output/generator.py",
    ]
    
    project_root = Path(__file__).parent
    missing = []
    
    for item in required_items:
        path = project_root / item
        if not path.exists():
            missing.append(item)
            print(f"  ✗ Missing: {item}")
        else:
            print(f"  ✓ Found: {item}")
    
    if missing:
        print(f"\n❌ Missing {len(missing)} required files/directories")
        return False
    else:
        print(f"\n✅ All {len(required_items)} required files/directories present")
        return True


def check_imports():
    """Check if main modules can be imported."""
    print("\nChecking Python imports...")
    
    modules_to_check = [
        ("numpy", "NumPy"),
        ("yaml", "PyYAML"),
        ("click", "Click"),
        ("cv2", "OpenCV"),
    ]
    
    missing = []
    for module, name in modules_to_check:
        try:
            __import__(module)
            print(f"  ✓ {name} importable")
        except ImportError:
            print(f"  ✗ {name} not found (install with: pip install)")
            missing.append(name)
    
    if missing:
        print(f"\n⚠️  {len(missing)} optional dependencies not installed")
        print("Run: pip install -r requirements.txt")
        return False
    else:
        print("\n✅ Core dependencies available")
        return True


def check_config():
    """Check if config file is valid."""
    print("\nChecking configuration...")
    
    try:
        import yaml
        config_path = Path(__file__).parent / "config.yaml"
        
        with open(config_path) as f:
            config = yaml.safe_load(f)
        
        required_sections = ['audio', 'video', 'fusion', 'naming', 'output', 'processing']
        
        for section in required_sections:
            if section in config:
                print(f"  ✓ Config section: {section}")
            else:
                print(f"  ✗ Missing config section: {section}")
                return False
        
        print("\n✅ Configuration valid")
        return True
        
    except Exception as e:
        print(f"\n❌ Configuration error: {e}")
        return False


def main():
    """Run all checks."""
    print("=" * 80)
    print("Webex Speaker Labeling - Project Verification")
    print("=" * 80)
    
    results = []
    
    # Run checks
    results.append(check_structure())
    results.append(check_imports())
    results.append(check_config())
    
    # Summary
    print("\n" + "=" * 80)
    if all(results):
        print("✅ All checks passed! Project is ready.")
        print("\nNext steps:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Set HuggingFace token: export HF_TOKEN='your_token'")
        print("3. Run test: python process_meeting.py --help")
        return 0
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
