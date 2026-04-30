#!/usr/bin/env python3
"""
Quick test script to verify the environment setup.
Tests that all modules can be imported and basic functionality works.
"""

import sys
import os

def test_imports():
    """Test that all required modules can be imported."""
    print("Testing imports...")
    
    try:
        import torch
        print(f"✓ PyTorch {torch.__version__}")
        print(f"  - MPS (Apple Silicon GPU) available: {torch.backends.mps.is_available()}")
        
        import numpy as np
        print(f"✓ NumPy {np.__version__}")
        
        import matplotlib
        print(f"✓ Matplotlib {matplotlib.__version__}")
        
        import gymnasium
        print(f"✓ Gymnasium {gymnasium.__version__}")
        
        import sumo_rl
        print(f"✓ SUMO-RL {sumo_rl.__version__}")
        
        print("\n✓ All imports successful!")
        return True
        
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False

def test_custom_modules():
    """Test that custom modules can be imported."""
    print("\nTesting custom modules...")
    
    try:
        from modules.config_loader import get_config
        print("✓ config_loader")
        
        from modules.logging_config import get_logger
        print("✓ logging_config")
        
        # Try to load config
        config = get_config()
        print(f"✓ Config loaded successfully")
        
        print("\n✓ All custom modules working!")
        return True
        
    except Exception as e:
        print(f"✗ Custom module test failed: {e}")
        return False

def test_sumo_files():
    """Check that SUMO configuration files exist."""
    print("\nChecking SUMO configuration files...")
    
    config_dir = "configuration_files"
    required_files = [
        "grid4x4.net.xml",
        "grid4x4_realistic.rou.xml"
    ]
    
    all_exist = True
    for filename in required_files:
        filepath = os.path.join(config_dir, filename)
        if os.path.exists(filepath):
            print(f"✓ {filename}")
        else:
            print(f"✗ {filename} NOT FOUND")
            all_exist = False
    
    if all_exist:
        print("\n✓ All SUMO files present!")
    return all_exist

if __name__ == "__main__":
    print("=" * 60)
    print("Environment Setup Verification")
    print("=" * 60)
    
    results = []
    results.append(test_imports())
    results.append(test_custom_modules())
    results.append(test_sumo_files())
    
    print("\n" + "=" * 60)
    if all(results):
        print("✓ ALL TESTS PASSED! Environment is ready.")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Activate the virtual environment:")
        print("   source venv/bin/activate")
        print("\n2. Start training:")
        print("   python train_custom_multienv.py --episodes 100 --num-envs 4")
        print("\n3. Or run a quick test:")
        print("   python train_custom_multienv.py --episodes 10 --num-envs 2")
        sys.exit(0)
    else:
        print("✗ SOME TESTS FAILED. Please check the errors above.")
        print("=" * 60)
        sys.exit(1)
