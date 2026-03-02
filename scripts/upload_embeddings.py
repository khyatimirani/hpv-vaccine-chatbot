"""
One-time script to upload document embeddings to Pinecone.

Usage:
    python scripts/upload_embeddings.py [--docs-path PATH] [--chunk-size N] [--chunk-overlap N]

This script must NOT be imported in the production runtime.  It is intended
to be run once (or whenever the knowledge base is updated) to populate the
Pinecone index that the Flask app queries at inference time.

Environment variables required:
    OPENAI_API_KEY        – OpenAI API key for generating embeddings.
    PINECONE_API_KEY      – Pinecone API key.
    PINECONE_INDEX_NAME   – Name of the target Pinecone index.
"""

import argparse
import sys
from pathlib import Path

# Make chatbot source importable when running the script directly
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "chatbot"))

from bot.memory.openai_embedder import embed  # noqa: E402
from bot.memory.vector_database.id_generator import generate_deterministic_id  # noqa: E402
from bot.memory.vector_database.pinecone_store import PineconeStore  # noqa: E402
from document_loader.loader import DirectoryLoader  # noqa: E402
from document_loader.text_splitter import create_recursive_text_splitter  # noqa: E402
from dotenv import load_dotenv  # noqa: E402
from helpers.log import get_logger  # noqa: E402

load_dotenv()

logger = get_logger(__name__)


def upload_embeddings(
    docs_path: Path,
    index_name: str,
    chunk_size: int = 512,
    chunk_overlap: int = 25,
) -> None:
    """
    Load documents, generate OpenAI embeddings, and upsert them into Pinecone.

    Args:
        docs_path:     Path to the directory containing source documents.
        index_name:    Name of the Pinecone index to populate.
        chunk_size:    Maximum character size of each text chunk.
        chunk_overlap: Overlap between consecutive chunks.
    """
    logger.info("Loading documents from: %s", docs_path)
    loader = DirectoryLoader(path=docs_path, glob="**/*.md")
    documents = loader.load()
    if not documents:
        logger.warning("No documents found in %s. Exiting.", docs_path)
        return
    logger.info("Loaded %d document(s).", len(documents))

    splitter = create_recursive_text_splitter(
        format="markdown", chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )
    chunks = splitter.split_documents(documents)
    logger.info("Generated %d chunk(s).", len(chunks))

    store = PineconeStore(index_name=index_name)

    vectors = []
    for chunk in chunks:
        text = chunk.page_content
        source = chunk.metadata.get("source", "")
        vector_id = generate_deterministic_id(text)
        embedding = embed(text)
        vectors.append(
            {
                "id": vector_id,
                "values": embedding,
                "metadata": {"text": text, "source": source},
            }
        )

    # Upsert in batches of 100 (Pinecone recommended batch size)
    batch_size = 100
    for i in range(0, len(vectors), batch_size):
        batch = vectors[i : i + batch_size]
        store.upsert(batch)
        logger.info("Upserted batch %d/%d.", i // batch_size + 1, -(-len(vectors) // batch_size))

    logger.info("Upload complete. %d vector(s) upserted.", len(vectors))


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Upload document embeddings to Pinecone")
    parser.add_argument(
        "--docs-path",
        type=Path,
        default=_REPO_ROOT / "docs",
        help="Path to the docs directory. Defaults to <repo_root>/docs.",
    )
    parser.add_argument(
        "--index-name",
        type=str,
        default=None,
        help="Pinecone index name. Defaults to PINECONE_INDEX_NAME env var.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=512,
        help="Maximum size of each text chunk. Defaults to 512.",
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=25,
        help="Overlap between consecutive chunks. Defaults to 25.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    import os

    args = get_args()
    index_name = args.index_name or os.environ.get("PINECONE_INDEX_NAME")
    if not index_name:
        logger.error("PINECONE_INDEX_NAME must be set via --index-name or the environment variable.")
        sys.exit(1)

    upload_embeddings(
        docs_path=args.docs_path,
        index_name=index_name,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
    )
