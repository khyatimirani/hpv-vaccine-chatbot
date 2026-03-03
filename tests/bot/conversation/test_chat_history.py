import pytest

from bot.conversation.chat_history import ChatHistory


def test_chat_history_append_within_limit():
    """Messages within the total_length are all retained."""
    history = ChatHistory(total_length=3)
    history.append("msg1")
    history.append("msg2")
    assert list(history) == ["msg1", "msg2"]


def test_chat_history_append_evicts_oldest_when_full():
    """Oldest message is evicted when total_length is reached."""
    history = ChatHistory(total_length=2)
    history.append("msg1")
    history.append("msg2")
    history.append("msg3")
    assert list(history) == ["msg2", "msg3"]


def test_chat_history_clear_empties_history():
    """clear() removes all messages from the history."""
    history = ChatHistory(total_length=3)
    history.append("msg1")
    history.append("msg2")
    history.clear()
    assert list(history) == []
    assert len(history) == 0


def test_chat_history_clear_preserves_total_length():
    """After clear(), new messages can still be appended up to total_length."""
    history = ChatHistory(total_length=2)
    history.append("msg1")
    history.append("msg2")
    history.clear()
    history.append("new_msg1")
    history.append("new_msg2")
    assert list(history) == ["new_msg1", "new_msg2"]


def test_chat_history_clear_on_empty_history():
    """Calling clear() on an already-empty history is safe."""
    history = ChatHistory(total_length=2)
    history.clear()
    assert list(history) == []


def test_chat_history_str_representation():
    """__str__ returns messages joined by newlines."""
    history = ChatHistory(total_length=3)
    history.append("question: A, answer: B")
    history.append("question: C, answer: D")
    assert str(history) == "question: A, answer: B\nquestion: C, answer: D"


def test_chat_history_str_empty():
    """__str__ on empty history returns empty string."""
    history = ChatHistory(total_length=2)
    assert str(history) == ""
