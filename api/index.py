"""
Vercel Serverless entry point.
Imports the Flask app so Vercel can serve it as a serverless function.
"""

import sys
import os

# Add project root to Python path so imports work correctly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
