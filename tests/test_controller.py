
import pytest
from deepseek.controller import ChatController
from deepseek.model import Chat, MessagePair


def create_pair(idx, req, resp):
    return MessagePair(str(idx), req, resp, None, None, None, None)


def create_chat(chat_id, title, pairs):
    chat = Chat(chat_id, title, None, None)
    for p in pairs:
        chat.add_pair(p)
    return chat


# ---------------- SEARCH CONTRACT ----------------

def test_search_returns_only_matching_request_pairs():
    controller = ChatController()

    p1 = create_pair(1, "hello world", "x")
    p2 = create_pair(2, "no match", "hello response")
    chat = create_chat("1", "Chat", [p1, p2])

    controller.set_chats([chat])

    results = controller.search(chat, "hello", "Запрос")

    assert results == [p1]


def test_search_returns_only_matching_response_pairs():
    controller = ChatController()

    p1 = create_pair(1, "req", "hello world")
    p2 = create_pair(2, "req2", "no match")
    chat = create_chat("1", "Chat", [p1, p2])

    controller.set_chats([chat])

    results = controller.search(chat, "hello", "Ответ")

    assert results == [p1]


# ---------------- NAVIGATION CONTRACT ----------------

def test_navigation_moves_between_pairs():
    controller = ChatController()

    p1 = create_pair(1, "a", "b")
    p2 = create_pair(2, "c", "d")
    chat = create_chat("1", "Chat", [p1, p2])

    controller.select_pair(chat, p1)

    assert controller.next_pair() == p2
    assert controller.prev_pair() == p1


def test_navigation_does_not_exceed_bounds():
    controller = ChatController()

    p1 = create_pair(1, "a", "b")
    chat = create_chat("1", "Chat", [p1])

    controller.select_pair(chat, p1)

    assert controller.prev_pair() is None
    assert controller.next_pair() is None


# ---------------- SELECTION CONTRACT ----------------

def test_select_pair_sets_current_chat_and_returns_pair():
    controller = ChatController()

    p1 = create_pair(1, "a", "b")
    chat = create_chat("1", "Chat", [p1])

    selected = controller.select_pair(chat, p1)

    assert selected == p1
    assert controller.current_chat == chat


# ---------------- FILTER CONTRACT ----------------

def test_filter_chats_returns_only_matching_titles():
    controller = ChatController()

    chat1 = create_chat("1", "Alpha", [])
    chat2 = create_chat("2", "Beta", [])

    controller.set_chats([chat1, chat2])
    controller.filter_chats("Al")

    filtered = controller.get_filtered_chats()

    assert filtered == [chat1]
