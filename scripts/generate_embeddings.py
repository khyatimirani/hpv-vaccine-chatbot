"""
Offline embedding generation script.

Run this script locally (not in production) to build the Chroma vector store
from the docs directory. The same lightweight ONNX-based embedding model
(chromadb's DefaultEmbeddingFunction / all-MiniLM-L6-v2) is used here as in
the production runtime Embedder so that query-time and index-time embeddings
are always in the same vector space.

If you need a multilingual model (e.g. for Hindi/English content), swap in
sentence-transformers as the embedder *and* update chatbot/bot/memory/embedder.py
to use the matching model — both must stay in sync.

Usage:
    python scripts/generate_embeddings.py [--chunk-size N] [--chunk-overlap N]

The generated vector store is persisted to ./vector_store/docs_index and should
be committed (or otherwise made available) before deploying the production image.
"""

import argparse
import sys
from pathlib import Path

import chromadb
import chromadb.config
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
from cleantext import clean

ROOT_FOLDER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_FOLDER / "chatbot"))

from bot.memory.vector_database.id_generator import generate_deterministic_ids  # noqa: E402
from chromadb.utils.batch_utils import create_batches  # noqa: E402
from document_loader.format import Format  # noqa: E402
from document_loader.loader import DirectoryLoader  # noqa: E402
from document_loader.text_splitter import create_recursive_text_splitter  # noqa: E402
from helpers.log import get_logger  # noqa: E402

logger = get_logger(__name__)


def build_vector_store(docs_path: Path, vector_store_path: Path, chunk_size: int, chunk_overlap: int) -> None:
    """Load documents, chunk them, embed with DefaultEmbeddingFunction, and persist to ChromaDB."""
    logger.info(f"Loading documents from: {docs_path}")
    loader = DirectoryLoader(path=docs_path, glob="**/*.txt", show_progress=True)
    documents = loader.load()
    if not documents:
        logger.error("No documents found. Aborting.")
        sys.exit(1)
    logger.info(f"Loaded {len(documents)} document(s).")

    logger.info("Chunking documents...")
    splitter = create_recursive_text_splitter(
        format=Format.MARKDOWN.value, chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )
    chunks = splitter.split_documents(documents)
    logger.info(f"Generated {len(chunks)} chunk(s).")

    # Use the same embedding function as the production Embedder so that
    # stored document vectors and runtime query vectors share the same space.
    embedder = DefaultEmbeddingFunction()

    logger.info(f"Persisting vector store to: {vector_store_path}")
    vector_store_path.mkdir(parents=True, exist_ok=True)
    client_settings = chromadb.config.Settings(is_persistent=True, persist_directory=str(vector_store_path))
    chroma_client = chromadb.Client(client_settings)
    collection = chroma_client.get_or_create_collection(
        name="default",
        embedding_function=None,
        configuration={"hnsw": {"space": "cosine"}},
    )

    texts = [clean(doc.page_content, no_emoji=True) for doc in chunks]
    metadata = [doc.metadata for doc in chunks]
    ids = generate_deterministic_ids(texts)

    for batch in create_batches(api=chroma_client, ids=ids, metadatas=metadata, documents=texts):
        batch_texts = batch[3] if batch[3] else []
        batch_metadata = batch[2] if batch[2] else None
        batch_ids = batch[0]
        batch_embeddings = list(embedder(batch_texts))
        collection.upsert(
            embeddings=batch_embeddings,
            documents=batch_texts,
            metadatas=batch_metadata,
            ids=batch_ids,
        )

    logger.info(f"Vector store built successfully with {collection.count()} item(s).")


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Offline embedding generation for HPV Vaccine Chatbot")
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=512,
        help="Maximum size of each chunk. Defaults to 512.",
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=25,
        help="Overlap between consecutive chunks. Defaults to 25.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    try:
        args = get_args()
        build_vector_store(
            docs_path=ROOT_FOLDER / "docs",
            vector_store_path=ROOT_FOLDER / "vector_store" / "docs_index",
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
        )
    except Exception as error:
        logger.error(f"An error occurred: {error}", exc_info=True)
        sys.exit(1)
