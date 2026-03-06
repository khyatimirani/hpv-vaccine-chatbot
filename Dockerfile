# ---------------------------------------------------------------------------
# Build stage: install Python dependencies via Poetry
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS builder

WORKDIR /app

# Install system build tools needed by some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Read Poetry version from the version file and install it
COPY version/poetry ./version/poetry
RUN pip install --no-cache-dir "poetry==$(cat version/poetry)"

# Copy dependency manifests and install production deps only
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.in-project true \
    && poetry install --no-root --no-ansi --only main

# ---------------------------------------------------------------------------
# Runtime stage
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application source
COPY chatbot/          ./chatbot/
COPY docs/             ./docs/
COPY images/           ./images/
COPY gunicorn.conf.py  ./
COPY wsgi.py           ./

# Make sure the virtualenv binaries are on PATH
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/chatbot" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# ---------------------------------------------------------------------------
# Environment Variables (must be set at runtime, not build time)
# ---------------------------------------------------------------------------
# Required:
#   OPENAI_API_KEY      - OpenAI API key for embeddings and chat
#   PINECONE_API_KEY    - Pinecone API key for vector database
#   PINECONE_INDEX_NAME - Name of the Pinecone index
#
# Optional:
#   SECRET_KEY          - Flask secret key for session management
#   PORT                - Server port (default: 8000, Cloud Run sets 8080)
#   SYNTHESIS_STRATEGY  - Context synthesis strategy
#   RAG_K               - Number of chunks from similarity search
#   MAX_NEW_TOKENS      - Maximum tokens to generate
#
# Set via:
#   docker run: docker run -e OPENAI_API_KEY=xxx -e PINECONE_API_KEY=xxx ...
#   docker-compose: env_file: .env (see docker-compose.yml)
#   Cloud Run: --set-env-vars or --set-secrets (see deploy.sh)
# ---------------------------------------------------------------------------

EXPOSE 8080

# Gunicorn serves the Flask app created by chatbot/web_app.py with dynamic port for Cloud Run
CMD ["gunicorn", "--config", "gunicorn.conf.py", "wsgi:app"]
