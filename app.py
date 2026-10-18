"""
Root entry point alias for Flask dashboard application.
Runs dashboard.app preserving all routes and configurations.
"""

import os
import sys

# Ensure root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from dashboard.app import app

if __name__ == '__main__':
    app.run(port=5000, debug=True)
