import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
PDF_DIR = BASE_DIR / "data" / "pdf"
CHROMA_DIR = BASE_DIR / "chroma_db"

PDF_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DIR.mkdir(parents=True, exist_ok=True)

GROQ_API_KEY = os.getenv("GROQ_API_KEY") or os.getenv("GROQ_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

NOMIC_API_KEY = os.getenv("NOMIC_API_KEY", "")

# Comma-separated list of allowed frontend origins. Defaults to localhost dev
# server plus wildcard so a first deploy isn't blocked before the Vercel URL
# is known; tighten CORS_ORIGINS once the real frontend URL is set.
_cors_env = os.getenv("CORS_ORIGINS", "")
CORS_ORIGINS = [o.strip() for o in _cors_env.split(",") if o.strip()] or [
    "http://localhost:5173",
    "*",
]

EMBED_MODEL_NAME = "nomic-embed-text-v1.5"
COLLECTION_NAME = "rag_explorer"

CHUNK_SIZE = 800
CHUNK_OVERLAP = 120
TOP_K = 4
