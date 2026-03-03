"""
Flask-based web application for the HPV Vaccine Assistant.

Provides a clean, polished web interface with three sections:
  - Ask a Question (RAG chatbot)
  - Myth vs Fact viewer
  - Eligibility Checker

Run with:
    python chatbot/web_app.py [--synthesis-strategy STRATEGY] [--k K] \
                              [--max-new-tokens N] [--host HOST] [--port PORT]
"""

import argparse
import os
import sys
from pathlib import Path

from bot.client.openai_client import OpenAIClient
from bot.conversation.chat_history import ChatHistory
from bot.conversation.conversation_handler import (
    answer_with_context,
    extract_content_after_reasoning,
    refine_question,
    trim_response,
)
from bot.conversation.ctx_strategy import (
    get_ctx_synthesis_strategies,
    get_ctx_synthesis_strategy,
)
from bot.conversation.intent_classifier import (
    PREDEFINED_RESPONSES,
    VALID_HEALTH_QUERY,
    classify_intent,
    get_rag_query,
)
from bot.memory.openai_embedder import embed
from bot.memory.vector_database.id_generator import generate_deterministic_id
from bot.memory.vector_database.pinecone_store import PineconeStore
from document_loader.format import Format
from document_loader.text_splitter import create_recursive_text_splitter
from eligibility import check_eligibility
from entities.document import Document
from flask import Flask, jsonify, render_template, request, send_from_directory
from helpers.log import get_logger
from helpers.prettier import prettify_source

logger = get_logger(__name__)

ROOT_FOLDER = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Route handler helpers
# ---------------------------------------------------------------------------


def _get_myth_vs_fact():
    """Return Myth vs Fact markdown content."""
    myth_path = ROOT_FOLDER / "docs" / "myth_vs_fact.md"
    if myth_path.exists():
        return jsonify({"content": myth_path.read_text(encoding="utf-8")})
    return jsonify({"content": "Myth vs Fact content not found."}), 404


def _post_chat(llm, ctx_synthesis_strategy, chat_history, pinecone_store, parameters):
    """Handle a chat message and return the assistant response."""
    if pinecone_store is None:
        return jsonify({"error": "Vector store is unavailable. Please check server configuration."}), 503
    data = request.get_json(silent=True) or {}
    user_input = (data.get("message") or "").strip()
    if not user_input:
        return jsonify({"error": "Empty message"}), 400

    try:
        # Pre-RAG intent classification — skip RAG for non-health queries
        intent = classify_intent(user_input)
        if intent != VALID_HEALTH_QUERY:
            return jsonify({"answer": PREDEFINED_RESPONSES[intent], "sources": []})

        rag_input = get_rag_query(user_input)
        refined_input = refine_question(llm, rag_input, chat_history=chat_history, max_new_tokens=128)

        query_embedding = embed(refined_input)
        matches = pinecone_store.query(query_embedding, top_k=parameters.k)
        retrieved_contents = [
            Document(
                page_content=m.metadata.get("text", ""),
                metadata={"source": m.metadata.get("source", "")},
            )
            for m in matches
            if m.metadata.get("text")
        ]
        sources = [
            {
                "score": round(m.score, 3),
                "document": m.metadata.get("source"),
                "content_preview": m.metadata.get("text", "")[:256] + "...",
            }
            for m in matches
            if m.metadata.get("text")
        ]

        if not retrieved_contents:
            safety_msg = (
                "I'm unable to answer that based on the available HPV vaccine information. "
                "Please consult a qualified health provider for personalised advice."
            )
            return jsonify({"answer": safety_msg, "sources": []})

        streamer, _ = answer_with_context(
            llm, ctx_synthesis_strategy, rag_input, chat_history, retrieved_contents, parameters.max_new_tokens
        )

        full_response = ""
        for token in streamer:
            full_response += llm.parse_token(token)

        if llm.model_settings.reasoning:
            answer = extract_content_after_reasoning(full_response, llm.model_settings.reasoning_stop_tag)
            if not answer:
                answer = "I wasn't able to provide the answer; do you want me to try again?"
        else:
            answer = full_response

        answer = trim_response(answer, rag_input)
        chat_history.append(f"question: {rag_input}, answer: {answer}")

        source_list = [prettify_source(s) for s in sources]
        return jsonify({"answer": answer, "sources": source_list})

    except Exception as exc:
        logger.error(f"Error generating answer: {exc}", exc_info=True)
        return jsonify({"error": "An error occurred while generating the answer."}), 500


def _post_eligibility():
    """Evaluate HPV vaccine eligibility and return the result."""
    data = request.get_json(silent=True) or {}
    try:
        age = int(data.get("age", 0))
        gender = str(data.get("gender", ""))
        already_vaccinated = bool(data.get("already_vaccinated", False))
        is_pregnant = bool(data.get("is_pregnant", False))
    except (TypeError, ValueError) as exc:
        return jsonify({"error": f"Invalid input: {exc}"}), 400

    result = check_eligibility(
        age=age,
        gender=gender,
        already_vaccinated=already_vaccinated,
        is_pregnant=is_pregnant,
    )
    return jsonify(
        {
            "eligible": result.eligible,
            "recommendation": result.recommendation,
            "dose_schedule": result.dose_schedule,
            "notes": result.notes,
        }
    )


def _post_upload_document(pinecone_store, parameters):
    """Add an uploaded Markdown document to the knowledge base."""
    if pinecone_store is None:
        return jsonify({"error": "Vector store is unavailable. Please check server configuration."}), 503
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    uploaded_file = request.files["file"]
    filename = uploaded_file.filename or "uploaded.md"

    try:
        content = uploaded_file.read().decode("utf-8")
    except Exception as exc:
        return jsonify({"error": f"Could not read file: {exc}"}), 400

    document = Document(page_content=content, metadata={"source": filename})
    splitter = create_recursive_text_splitter(
        format=Format.MARKDOWN.value, chunk_size=parameters.chunk_size, chunk_overlap=parameters.chunk_overlap
    )
    chunks = splitter.split_documents([document])

    vectors = []
    for chunk in chunks:
        text = chunk.page_content
        source = chunk.metadata.get("source", "")
        vector_id = generate_deterministic_id(text)
        embedding = embed(text)
        vectors.append({"id": vector_id, "values": embedding, "metadata": {"text": text, "source": source}})

    pinecone_store.upsert(vectors)
    return jsonify({"message": f"Added {len(chunks)} chunk(s) from '{filename}'."})


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------


def create_app(parameters) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__, template_folder="templates", static_folder="static")

    # Initialise shared resources once at startup
    index_name = os.environ.get("PINECONE_INDEX_NAME", "hpv-guide-v2").strip()
    llm = OpenAIClient()
    chat_history = ChatHistory(total_length=2)
    ctx_synthesis_strategy = get_ctx_synthesis_strategy(parameters.synthesis_strategy, llm=llm)
    try:
        pinecone_store = PineconeStore(index_name=index_name)
    except Exception as exc:  # broad catch intentional: any init failure must not crash workers
        logger.error(
            "Pinecone initialisation failed: %s. Chat and upload endpoints will be unavailable.", exc
        )
        pinecone_store = None

    @app.route("/health")
    def health():
        return jsonify({"status": "ok"}), 200

    @app.route("/")
    def home():
        return render_template("index.html")

    @app.route("/images/<filename>")
    def serve_image(filename):
        response = send_from_directory(ROOT_FOLDER / "images", filename)
        response.headers.setdefault("Accept-Ranges", "bytes")
        return response

    @app.route("/api/myth-vs-fact")
    def myth_vs_fact():
        return _get_myth_vs_fact()

    @app.route("/api/chat", methods=["POST"])
    def chat():
        return _post_chat(llm, ctx_synthesis_strategy, chat_history, pinecone_store, parameters)

    @app.route("/api/eligibility", methods=["POST"])
    def eligibility():
        return _post_eligibility()

    @app.route("/api/upload-document", methods=["POST"])
    def upload_document():
        return _post_upload_document(pinecone_store, parameters)

    @app.route("/api/clear-history", methods=["POST"])
    def clear_history():
        chat_history.clear()
        return jsonify({"message": "Conversation history cleared."})

    return app


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="HPV Vaccine Assistant - Flask Web App")

    synthesis_strategy_list = get_ctx_synthesis_strategies()
    default_synthesis_strategy = synthesis_strategy_list[0]

    parser.add_argument(
        "--synthesis-strategy",
        type=str,
        choices=synthesis_strategy_list,
        help=f"Context synthesis strategy. Defaults to {default_synthesis_strategy}.",
        required=False,
        const=default_synthesis_strategy,
        nargs="?",
        default=default_synthesis_strategy,
    )
    parser.add_argument(
        "--k",
        type=int,
        help="Number of chunks to return from similarity search. Defaults to 2.",
        required=False,
        default=2,
    )
    parser.add_argument(
        "--max-new-tokens",
        type=int,
        help="Maximum number of tokens to generate. Defaults to 512.",
        required=False,
        default=512,
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        help="Maximum size of each chunk for document splitting.",
        required=False,
        default=1000,
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        help="Amount of overlap between consecutive chunks.",
        required=False,
        default=50,
    )
    parser.add_argument(
        "--host",
        type=str,
        help="Host to bind the server to. Defaults to 127.0.0.1.",
        required=False,
        default="127.0.0.1",
    )
    parser.add_argument(
        "--port",
        type=int,
        help="Port to listen on. Defaults to 5000.",
        required=False,
        default=5000,
    )
    return parser.parse_args()


if __name__ == "__main__":
    try:
        args = get_args()
        flask_app = create_app(args)
        # Use PORT environment variable for Cloud Run compatibility
        port = int(os.environ.get("PORT", args.port))
        flask_app.run(host=args.host, port=port, debug=False)
    except Exception as error:
        logger.error(f"An error occurred: {error}", exc_info=True, stack_info=True)
        sys.exit(1)
