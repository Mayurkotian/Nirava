"""LLM Configuration for Nirava Health Companion.

This module handles Gemini model initialization with appropriate safety settings.
"""
import logging
from pathlib import Path
import google.generativeai as genai
from config.settings import GOOGLE_API_KEY

logger = logging.getLogger(__name__)

def get_gemini_model(model_name: str = "gemini-2.0-flash"):
    """
    Configures and returns a Gemini model instance.
    
    Args:
        model_name: Gemini model to use (default: gemini-2.0-flash)
    
    Returns:
        GenerativeModel instance or None if API key is missing.
    """
    if not GOOGLE_API_KEY:
        logger.warning("GOOGLE_API_KEY not set. AI agents will use fallback mode.")
        return None

    genai.configure(api_key=GOOGLE_API_KEY)

    # Standard safety settings for a health agent
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    ]

    model = genai.GenerativeModel(
        model_name=model_name,
        safety_settings=safety_settings,
    )
    return model