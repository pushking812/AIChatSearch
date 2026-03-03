import pytest

from deepseek.controller import ChatController


# ---------- Test doubles ----------

class DummyPair:
    def __init__(self, request_text="", response_text=""):
        self.request_text = request_text
        self.response_text = response_text


class DummyChat:
    def __init__(self, title, pairs):
        self.title = title
        self._pairs = pairs

    def get_pairs(self):
        return self._pairs


# ---------- DATA / FILTER ----------

def test_set_chats_and_reset_navigation():
    controller = ChatController()
    chat = DummyChat("Test Chat", [])
    controller.set_chats([chat])

    assert controller.get_filtered_chats() == [chat]
    assert controller.current_chat is None
    assert controller.current_index_in_chat is None


def test_filter_chats_by_title():
    controller = ChatController()

    chat1 = DummyChat("Alpha Chat", [])
    chat2 = DummyChat("Beta Chat", [])

    controller.set_chats([chat1, chat2])
    controller.filter_chats("alpha")

    assert controller.get_filtered_chats() == [chat1]


def test_filter_chats_empty_query_restores_all():
    controller = ChatController()

    chat1 = DummyChat("Alpha", [])
    chat2 = DummyChat("Beta", [])

    controller.set_chats([chat1, chat2])
    controller.filter_chats("alpha")
    controller.filter_chats("")

    assert len(controller.get_filtered_chats()) == 2


# ---------- SEARCH ----------

def test_search_by_request():
    controller = ChatController()

    pair = DummyPair("hello world", "response")
    chat = DummyChat("Chat", [pair])

    result = controller.search(chat, "hello", "Запрос")
    assert result == [pair]


def test_search_by_response():
    controller = ChatController()

    pair = DummyPair("request", "great answer")
    chat = DummyChat("Chat", [pair])

    result = controller.search(chat, "answer", "Ответ")
    assert result == [pair]


def test_search_empty_query_returns_all_pairs():
    controller = ChatController()

    pair1 = DummyPair("a", "b")
    pair2 = DummyPair("c", "d")
    chat = DummyChat("Chat", [pair1, pair2])

    result = controller.search(chat, "", "Запрос")
    assert result == [pair1, pair2]


def test_search_with_positions():
    controller = ChatController()

    pair = DummyPair("hello world", "response")
    chat = DummyChat("Chat", [pair])

    results = controller.search_with_positions(chat, "hello", "Запрос")

    assert len(results) == 1
    found_chat, found_pair, field, start, end = results[0]

    assert found_chat is chat
    assert found_pair is pair
    assert field == "request"
    assert start == 0
    assert end == 5


# ---------- SELECT / NAVIGATION ----------

def test_select_and_navigation():
    controller = ChatController()

    pair1 = DummyPair("r1", "a1")
    pair2 = DummyPair("r2", "a2")
    pair3 = DummyPair("r3", "a3")

    chat = DummyChat("Chat", [pair1, pair2, pair3])

    selected = controller.select_pair(chat, pair2)

    assert selected is pair2
    assert controller.current_index_in_chat == 1

    # prev
    prev_pair = controller.prev_pair()
    assert prev_pair is pair1

    # next (back to pair2)
    next_pair = controller.next_pair()
    assert next_pair is pair2

    # next (to pair3)
    next_pair = controller.next_pair()
    assert next_pair is pair3

    # next at end -> None
    assert controller.next_pair() is None


def test_get_nav_state_and_position_info():
    controller = ChatController()

    pair1 = DummyPair("r1", "a1")
    pair2 = DummyPair("r2", "a2")

    chat = DummyChat("My Chat", [pair1, pair2])
    controller.select_pair(chat, pair1)

    can_prev, can_next = controller.get_nav_state()
    assert can_prev is False
    assert can_next is True

    title, position, total = controller.get_position_info()
    assert title == "My Chat"
    assert position == 1
    assert total == 2

# ---------- EXTRA COVERAGE ----------

def test_search_by_chat_title():
    controller = ChatController()

    pair = DummyPair("req", "res")
    chat = DummyChat("Special Title", [pair])

    result = controller.search(chat, "special", "Название чата")
    assert result == [pair]


def test_search_with_positions_both_fields():
    controller = ChatController()

    pair = DummyPair("hello", "world")
    chat = DummyChat("Chat", [pair])

    results = controller.search_with_positions(chat, "o", "Все")

    assert len(results) >= 1


def test_select_pair_not_found():
    controller = ChatController()

    pair1 = DummyPair("a", "b")
    pair2 = DummyPair("c", "d")
    chat = DummyChat("Chat", [pair1])

    result = controller.select_pair(chat, pair2)
    assert result is None


def test_navigation_when_none():
    controller = ChatController()

    assert controller.prev_pair() is None
    assert controller.next_pair() is None


def test_get_position_info_without_selection():
    controller = ChatController()

    title, position, total = controller.get_position_info()
    assert title is None
    assert position is None
    assert total is None


# ---------- ADDITIONAL COVERAGE TESTS ----------

def test_reset_search_state_initializes_attrs():
    controller = ChatController()
    controller._reset_search_state()
    assert controller.visible_pairs == []
    assert controller.search_active is False


def test_search_with_none_chat():
    controller = ChatController()
    assert controller.search(None, "a", "Запрос") == []


def test_search_with_positions_none_chat():
    controller = ChatController()
    assert controller.search_with_positions(None, "a", "Запрос") == []


def test_search_with_positions_empty_query():
    controller = ChatController()
    chat = DummyChat("Chat", [])
    assert controller.search_with_positions(chat, "", "Запрос") == []


def test_search_with_positions_response_field():
    controller = ChatController()
    pair = DummyPair("req", "hello world")
    chat = DummyChat("Chat", [pair])

    results = controller.search_with_positions(chat, "hello", "Ответ")
    assert len(results) == 1
    found_chat, found_pair, field, start, end = results[0]

    assert found_chat is chat
    assert found_pair is pair
    assert field == "response"
    assert start == 0
    assert end == 5


def test_prev_pair_at_start_returns_none():
    controller = ChatController()
    pair = DummyPair("r", "a")
    chat = DummyChat("Chat", [pair])

    controller.select_pair(chat, pair)
    assert controller.prev_pair() is None


def test_get_nav_state_when_none():
    controller = ChatController()
    assert controller.get_nav_state() == (False, False)
