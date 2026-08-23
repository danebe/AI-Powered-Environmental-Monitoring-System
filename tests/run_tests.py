"""
SIH 2026 Environmental Monitoring Network
Comprehensive Test Suite Runner
"""

import unittest
import sys
import os

if __name__ == "__main__":
    test_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, os.path.abspath(os.path.join(test_dir, "..", "backend")))

    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=test_dir, pattern="test_*.py")

    print("\n=======================================================")
    print("  SIH 2026 Environmental Monitoring Network Test Suite")
    print("=======================================================\n")

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    sys.exit(0 if result.wasSuccessful() else 1)
