import sys
from unittest.mock import MagicMock, patch

import pytest

# Stub heavy optional dependencies before any chatbot modules are imported
for _mod in [
    "llama_cpp",
    "unstructured",
    "unstructured.partition",
    "unstructured.partition.auto",
    "tqdm",
]:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

from entities.document import Document  # noqa: E402
from memory_builder import auto_seed_index  # noqa: E402


@pytest.fixture
def mock_index():
    """A mock Chroma index with an empty collection."""
    index = MagicMock()
    index.collection.count.return_value = 0
    return index


@pytest.fixture
def docs_dir(tmp_path):
    """A temporary docs directory containing one Markdown file."""
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "sample.md").write_text("# HPV\nHPV is a virus that can cause cancer.", encoding="utf-8")
    return docs


def test_auto_seed_skips_when_already_populated(docs_dir):
    """auto_seed_index should be a no-op when the collection already has documents."""
    index = MagicMock()
    index.collection.count.return_value = 5

    auto_seed_index(index, docs_path=docs_dir)

    index.from_chunks.assert_not_called()


def test_auto_seed_skips_when_docs_path_missing(mock_index, tmp_path):
    """auto_seed_index should log a warning and do nothing when docs_path doesn't exist."""
    nonexistent = tmp_path / "no_such_dir"

    auto_seed_index(mock_index, docs_path=nonexistent)

    mock_index.from_chunks.assert_not_called()


def test_auto_seed_skips_when_no_markdown_files(mock_index, tmp_path):
    """auto_seed_index should do nothing when the docs directory contains no .md files."""
    empty_docs = tmp_path / "empty_docs"
    empty_docs.mkdir()
    (empty_docs / "readme.txt").write_text("not markdown")

    with patch("memory_builder.DirectoryLoader") as MockLoader:
        MockLoader.return_value.load.return_value = []
        auto_seed_index(mock_index, docs_path=empty_docs)

    mock_index.from_chunks.assert_not_called()


def test_auto_seed_calls_from_chunks_when_empty(mock_index, docs_dir):
    """auto_seed_index should load docs and call from_chunks when the collection is empty."""
    fake_doc = Document(page_content="HPV is a virus.", metadata={"source": str(docs_dir / "sample.md")})

    with (
        patch("memory_builder.DirectoryLoader") as MockLoader,
        patch("memory_builder.create_recursive_text_splitter") as MockSplitter,
    ):
        MockLoader.return_value.load.return_value = [fake_doc]
        mock_splitter_instance = MagicMock()
        mock_splitter_instance.split_documents.return_value = [fake_doc]
        MockSplitter.return_value = mock_splitter_instance

        auto_seed_index(mock_index, docs_path=docs_dir)

        MockLoader.assert_called_once_with(path=docs_dir, glob="**/*.md")
        mock_index.from_chunks.assert_called_once_with([fake_doc])
