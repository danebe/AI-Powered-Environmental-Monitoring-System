"""
SIH 2026 Environmental Monitoring Network
Root Server Launcher Script
"""

import sys
import os

# Add project root to Python search path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.server import run_server

if __name__ == "__main__":
    port = 8000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass

    static_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dashboard")
    run_server(host="0.0.0.0", port=port, static_dir=static_folder)
