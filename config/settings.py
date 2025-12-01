"""Central Configuration for Nirava System."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Base Directory (Root of the project)
BASE_DIR = Path(__file__).resolve().parent.parent

# Load Environment Variables
load_dotenv(BASE_DIR / ".env")

# LLM Settings
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_MODEL_NAME = "gemini-2.0-flash"

# Paths
SESSION_STORAGE_PATH = BASE_DIR / ".sessions"

# Context Engine Settings
MAX_CONTEXT_TOKENS = 8000
MAX_RECENT_MESSAGES = 6

# Safety & Research Settings
MIN_AUTHORITY_SCORE = 7
TRUSTED_DOMAINS = {
    "pubmed.ncbi.nlm.nih.gov": 10,
    "nih.gov": 10,
    "mayoclinic.org": 8,
    "harvard.edu": 8,
    "cdc.gov": 9,
}
