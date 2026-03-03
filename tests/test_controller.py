import pytest
from deepseek.controller import ChatController
from deepseek.model import Chat, MessagePair


# ---------- Test Helpers (public construction only) ----------

def create_pair(idx, req, resp):
    return MessagePair(str(idx), req, resp, None, None, None, None)


def create_chat(chat_id, title, pairs):
    chat = Chat(chat_id, title, None, None)
    for p in pairs:
        chat.add_pair(p)
    return chat


# ---------------- SEARCH CONTRACT ----------------

def test_search_request_field():
    controller = ChatController()

    p1 = create_pair(1, "hello world", "x")
    p2 = create_pair(2, "no match", "hello response")
    chat = create_chat("1", "Chat", [p1, p2])

    results = controller.search(chat, "hello", "Запрос")

    assert results == [p1]


def test_search_response_field():
    controller = ChatController()

    p1 = create_pair(1, "req", "hello world")
    p2 = create_pair(2, "req2", "no match")
    chat = create_chat("1", "Chat", [p1, p2])

    results = controller.search(chat, "hello", "Ответ")

    assert results == [p1]


# ---------------- SEARCH WITH POSITIONS CONTRACT ----------------

def test_search_with_positions_request():
    controller = ChatController()

    p1 = create_pair(1, "hello world", "resp")
    chat = create_chat("1", "Chat", [p1])

    results = controller.search_with_positions(chat, "hello", "Запрос")

    assert len(results) == 1
    r_chat, r_pair, field, start, end = results[0]

    assert r_chat == chat
    assert r_pair == p1
    assert field == "request"
    assert p1.request_text[start:end].lower() == "hello"


# ---------------- NAVIGATION CONTRACT ----------------

def test_navigation_between_pairs():
    controller = ChatController()

    p1 = create_pair(1, "a", "b")
    p2 = create_pair(2, "c", "d")
    chat = create_chat("1", "Chat", [p1, p2])

    controller.select_pair(chat, p1)

    assert controller.get_current_pair() == p1
    assert controller.next_pair() == p2
    assert controller.prev_pair() == p1


def test_navigation_does_not_exceed_bounds():
    controller = ChatController()

    p1 = create_pair(1, "a", "b")
    chat = create_chat("1", "Chat", [p1])

    controller.select_pair(chat, p1)

    assert controller.prev_pair() is None
    assert controller.next_pair() is None
    assert controller.get_current_pair() == p1


# ---------------- SELECTION CONTRACT ----------------

def test_select_pair_returns_selected():
    controller = ChatController()

    p1 = create_pair(1, "a", "b")
    chat = create_chat("1", "Chat", [p1])

    selected = controller.select_pair(chat, p1)

    assert selected == p1
    assert controller.get_current_pair() == p1


# ---------------- FILTER CONTRACT ----------------

def test_filter_chats_by_title():
    controller = ChatController()

    chat1 = create_chat("1", "Alpha", [])
    chat2 = create_chat("2", "Beta", [])

    controller.set_chats([chat1, chat2])
    controller.filter_chats("Al")

    assert controller.get_filtered_chats() == [chat1]


def test_filter_empty_query_returns_all():
    controller = ChatController()

    chat1 = create_chat("1", "Alpha", [])
    chat2 = create_chat("2", "Beta", [])

    controller.set_chats([chat1, chat2])
    controller.filter_chats("")

    assert controller.get_filtered_chats() == [chat1, chat2]


# ---------------- POSITION INFO CONTRACT ----------------

def test_get_position_info():
    controller = ChatController()

    p1 = create_pair(1, "a", "b")
    p2 = create_pair(2, "c", "d")
    chat = create_chat("1", "ChatTitle", [p1, p2])

    controller.select_pair(chat, p1)

    title, position, total = controller.get_position_info()

    assert title == "ChatTitle"
    assert position == 1
    assert total == 2
