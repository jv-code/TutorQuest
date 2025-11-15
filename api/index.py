"""
This is only if you are deploying on Vercel.
If you are not deploying on Vercel, you can delete this file.
"""

from fastapi import FastAPI

# Import the FastAPI app from backend/src/api.py
# PYTHONPATH is set to backend/src in vercel.json, so we can import directly
from api import app as api

# This ASGI app is used by Vercel as a Serverless Function
app = FastAPI()
app.mount("/api", api)
