from unittest.mock import MagicMock, patch

import pytest
from bot.memory.vector_database.pinecone_store import PineconeStore


@pytest.fixture
def pinecone_store(monkeypatch):
    """Create a PineconeStore with mocked Pinecone client."""
    monkeypatch.setenv("PINECONE_API_KEY", "test-api-key")
    with patch("bot.memory.vector_database.pinecone_store.Pinecone") as MockPinecone:
        mock_pc = MagicMock()
        mock_index = MagicMock()
        MockPinecone.return_value = mock_pc
        mock_pc.Index.return_value = mock_index
        store = PineconeStore(index_name="test-index")
        store._index = mock_index
        yield store


def test_initialization(monkeypatch):
    """PineconeStore raises ValueError when PINECONE_API_KEY is missing."""
    monkeypatch.delenv("PINECONE_API_KEY", raising=False)
    with pytest.raises(ValueError, match="PINECONE_API_KEY"):
        PineconeStore(index_name="test-index")


def test_api_key_whitespace_only_raises(monkeypatch):
    """PineconeStore raises ValueError when PINECONE_API_KEY contains only whitespace."""
    monkeypatch.setenv("PINECONE_API_KEY", "  \n\t  ")
    with pytest.raises(ValueError, match="PINECONE_API_KEY"):
        PineconeStore(index_name="test-index")


def test_api_key_trailing_newline_is_stripped(monkeypatch):
    """PineconeStore strips trailing newlines from PINECONE_API_KEY before use."""
    monkeypatch.setenv("PINECONE_API_KEY", "valid-key\n")
    with patch("bot.memory.vector_database.pinecone_store.Pinecone") as MockPinecone:
        mock_pc = MagicMock()
        MockPinecone.return_value = mock_pc
        mock_pc.Index.return_value = MagicMock()
        PineconeStore(index_name="test-index")
        MockPinecone.assert_called_once_with(api_key="valid-key")


def test_index_name_whitespace_stripped(monkeypatch):
    """PineconeStore strips whitespace from index_name and uses the clean value."""
    monkeypatch.setenv("PINECONE_API_KEY", "valid-key")
    with patch("bot.memory.vector_database.pinecone_store.Pinecone") as MockPinecone:
        mock_pc = MagicMock()
        MockPinecone.return_value = mock_pc
        mock_pc.Index.return_value = MagicMock()
        PineconeStore(index_name="  test-index\n")
        mock_pc.Index.assert_called_once_with("test-index")


def test_empty_index_name_raises(monkeypatch):
    """PineconeStore raises ValueError when index_name is empty after stripping."""
    monkeypatch.setenv("PINECONE_API_KEY", "valid-key")
    with patch("bot.memory.vector_database.pinecone_store.Pinecone"):
        with pytest.raises(ValueError, match="index name"):
            PineconeStore(index_name="  \n  ")


def test_query_returns_matches(pinecone_store):
    """query() calls the Pinecone index and returns match objects."""
    mock_match = MagicMock()
    mock_match.metadata = {"text": "HPV is a virus.", "source": "hpv.txt"}
    mock_match.score = 0.95

    pinecone_store._index.query.return_value = MagicMock(matches=[mock_match])

    embedding = [0.1] * 1536
    results = pinecone_store.query(embedding, top_k=3)

    pinecone_store._index.query.assert_called_once_with(
        vector=embedding, top_k=3, include_metadata=True
    )
    assert len(results) == 1
    assert results[0].metadata["text"] == "HPV is a virus."


def test_upsert_calls_index(pinecone_store):
    """upsert() forwards vector records to the Pinecone index."""
    vectors = [
        {"id": "abc123", "values": [0.1] * 1536, "metadata": {"text": "Test", "source": "test.txt"}}
    ]
    pinecone_store.upsert(vectors)
    pinecone_store._index.upsert.assert_called_once_with(vectors=vectors)


def test_count_returns_total(pinecone_store):
    """count() returns the total_vector_count from describe_index_stats."""
    pinecone_store._index.describe_index_stats.return_value = MagicMock(total_vector_count=42)
    assert pinecone_store.count() == 42
