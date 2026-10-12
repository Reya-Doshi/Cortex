"""Vercel Serverless Function entrypoint for FastAPI backend."""

from backend.app import app

# Vercel's Python runtime natively detects ASGI applications named 'app'
__all__ = ["app"]
