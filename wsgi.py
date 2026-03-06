"""
WSGI entry point for production deployments (e.g. Gunicorn).

Usage:
    gunicorn --config gunicorn.conf.py wsgi:app

Environment variables can override the default parameters:
    SYNTHESIS_STRATEGY  – context synthesis strategy (default: first available)
    RAG_K               – number of chunks from similarity search (default: 2)
    MAX_NEW_TOKENS      – max tokens to generate (default: 512)
    CHUNK_SIZE          – document chunk size (default: 1000)
    CHUNK_OVERLAP       – document chunk overlap (default: 50)

Required environment variables (must be set via deployment or .env file):
    OPENAI_API_KEY      – OpenAI API key for embeddings and chat
    PINECONE_API_KEY    – Pinecone API key for vector database
    PINECONE_INDEX_NAME – Name of the Pinecone index (defaults to 'hpv-guide-v2')
    SECRET_KEY          – Flask secret key for session management (optional, but recommended)
"""

import os
import sys
from pathlib import Path

# Load environment variables from .env file FIRST, before any other imports.
# This ensures environment variables are available when modules are imported.
# Note: In production (Docker/Cloud Run), environment variables should be
# set via the deployment configuration, not .env files.
from dotenv import load_dotenv

load_dotenv()

# Ensure the chatbot package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent / "chatbot"))

from bot.conversation.ctx_strategy import get_ctx_synthesis_strategies  # noqa: E402
from web_app import create_app  # noqa: E402


class _Parameters:
    """Simple namespace mirroring the argparse.Namespace produced by get_args()."""

    def __init__(self):
        strategies = get_ctx_synthesis_strategies()
        if not strategies:
            raise RuntimeError("No context synthesis strategies are available.")
        self.synthesis_strategy = os.environ.get("SYNTHESIS_STRATEGY", strategies[0])
        self.k = int(os.environ.get("RAG_K", "2"))
        self.max_new_tokens = int(os.environ.get("MAX_NEW_TOKENS", "512"))
        self.chunk_size = int(os.environ.get("CHUNK_SIZE", "1000"))
        self.chunk_overlap = int(os.environ.get("CHUNK_OVERLAP", "50"))


app = create_app(_Parameters())
