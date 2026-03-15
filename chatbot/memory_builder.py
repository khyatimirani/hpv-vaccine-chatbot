from pathlib import Path

from document_loader.format import Format
from document_loader.loader import DirectoryLoader
from document_loader.text_splitter import create_recursive_text_splitter
from entities.document import Document
from helpers.log import get_logger

logger = get_logger(__name__)


def load_documents(docs_path: Path) -> list[Document]:
    """
    Loads Markdown documents from the specified path.

    Args:
        docs_path (Path): The path to the documents.

    Returns:
        List[Document]: A list of loaded documents.
    """
    loader = DirectoryLoader(
        path=docs_path,
        glob="**/*.txt",
        show_progress=True,
    )
    return loader.load()


def split_chunks(sources: list, chunk_size: int = 512, chunk_overlap: int = 25) -> list:
    """
    Splits a list of sources into smaller chunks.

    Args:
        sources (List): The list of sources to be split into chunks.
        chunk_size (int, optional): The maximum size of each chunk. Defaults to 512.
        chunk_overlap (int, optional): The amount of overlap between consecutive chunks. Defaults to 25.

    Returns:
        List: A list of smaller chunks obtained from the input sources.
    """
    chunks = []
    splitter = create_recursive_text_splitter(
        format=Format.MARKDOWN.value, chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )
    for chunk in splitter.split_documents(sources):
        chunks.append(chunk)
    return chunks


def auto_seed_index(index, docs_path: Path, chunk_size: int = 512, chunk_overlap: int = 25) -> None:
    """
    Automatically seeds the vector store from the docs directory if the index is empty.

    This is called at application startup so that the chatbot works out-of-the-box
    without needing to run the upload script separately.

    Args:
        index: The vector store instance. Must expose a ``count()`` method and a
            ``from_chunks(chunks)`` method.
        docs_path (Path): Path to the directory containing source documents.
        chunk_size (int): Maximum size of each text chunk. Defaults to 512.
        chunk_overlap (int): Overlap between consecutive chunks. Defaults to 25.
    """
    if index.count() > 0:
        return

    logger.info("Vector store is empty — seeding from docs directory...")
    if not docs_path.exists():
        logger.warning(f"Docs path does not exist: {docs_path}. Skipping auto-seed.")
        return

    loader = DirectoryLoader(path=docs_path, glob="**/*.txt")
    documents = loader.load()
    if not documents:
        logger.warning("No Markdown documents found in docs directory. Skipping auto-seed.")
        return

    splitter = create_recursive_text_splitter(
        format=Format.MARKDOWN.value, chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )
    chunks = splitter.split_documents(documents)
    logger.info(f"Auto-seeding vector store with {len(chunks)} chunks from {len(documents)} document(s)...")
    index.from_chunks(chunks)
    logger.info("Vector store seeded successfully.")

