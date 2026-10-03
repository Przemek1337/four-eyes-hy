import threading
import pytest
from foureyes.core.session import SessionStore

ORDER = ["public", "personal_data", "bank_secret"]


def test_class_is_sticky_and_monotonic():
    s = SessionStore().get_or_create("s1", "agent", "public")
    assert s.raise_class("personal_data", ORDER, "read", "mcp:x") is True
    assert s.raise_class("public", ORDER, "later", "mcp:y") is False
    assert s.data_class == "personal_data"
    events = s.drain_events()
    assert [e["event"] for e in events] == ["class.raised"]
    assert events[0]["from"] == "public" and events[0]["to"] == "personal_data"
    assert s.drain_events() == []


def test_unknown_class_rejected():
    s = SessionStore().get_or_create("s1", "agent", "public")
    with pytest.raises(ValueError):
        s.raise_class("top_secret", ORDER, "x", "y")


def test_labels_are_sticky_and_emit_once():
    s = SessionStore().get_or_create("s1", "agent", "public")
    assert s.add_label("untrusted", "doc") is True
    assert s.add_label("untrusted", "doc") is False
    assert [e["event"] for e in s.drain_events()] == ["label.added"]


def test_get_or_create_returns_same_session():
    store = SessionStore()
    assert store.get_or_create("s", "a", "public") is store.get_or_create("s", "a", "public")


def test_concurrent_bumps():
    s = SessionStore().get_or_create("s", "a", "public")
    threads = [threading.Thread(target=lambda: [s.bump_steps() for _ in range(50)]) for _ in range(20)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert s.steps == 1000
