
import pytest
from deepseek.controller import ChatController


class DummyPair:
    def __init__(self, request_text="", response_text=""):
        self.request_text = request_text
        self.response_text = response_text


class DummyChat:
    def __init__(self, title, pairs):
        self.title = title
        self.pairs = pairs


# ---------- INIT ----------

def test_initial_state():
    controller = ChatController()
    assert controller.current_chat is None
    assert controller.current_pair_index is None
    assert controller.search_active is False
    assert controller.visible_pairs == []


# ---------- SET CURRENT CHAT ----------

def test_set_current_chat_with_pairs():
    controller = ChatController()
    chat = DummyChat("Chat", [DummyPair(), DummyPair()])

    controller.set_current_chat(chat)

    assert controller.current_chat is chat
    assert controller.current_pair_index == 0
    assert controller.search_active is False


def test_set_current_chat_empty():
    controller = ChatController()
    chat = DummyChat("Chat", [])

    controller.set_current_chat(chat)

    assert controller.current_pair_index is None


# ---------- RESET ----------

def test_reset_search_state():
    controller = ChatController()
    controller.search_active = True
    controller.visible_pairs = [1]

    controller._reset_search_state()

    assert controller.search_active is False
    assert controller.visible_pairs == []


# ---------- SEARCH CURRENT CHAT ----------

def test_search_current_chat_no_results():
    controller = ChatController()
    chat = DummyChat("Chat", [DummyPair("a", "b")])
    controller.set_current_chat(chat)

    result = controller.search_current_chat("zzz")

    assert result == []
    assert controller.search_active is True
    assert controller.current_pair_index is None


def test_search_current_chat_one_result():
    controller = ChatController()
    pair = DummyPair("hello", "world")
    chat = DummyChat("Chat", [pair])
    controller.set_current_chat(chat)

    result = controller.search_current_chat("hello")

    assert result == [pair]
    assert controller.current_pair_index == 0


def test_search_current_chat_multiple_results():
    controller = ChatController()
    pair1 = DummyPair("hello", "")
    pair2 = DummyPair("hello again", "")
    chat = DummyChat("Chat", [pair1, pair2])
    controller.set_current_chat(chat)

    result = controller.search_current_chat("hello")

    assert len(result) == 2
    assert controller.current_pair_index == 0


# ---------- SEARCH SELECTED CHATS ----------

def test_search_selected_chats():
    controller = ChatController()

    pair1 = DummyPair("alpha", "")
    pair2 = DummyPair("beta", "")

    chat1 = DummyChat("Chat1", [pair1])
    chat2 = DummyChat("Chat2", [pair2])

    result = controller.search_selected_chats("beta", [chat1, chat2])

    assert result == [pair2]
    assert controller.search_active is True
    assert controller.current_pair_index == 0


# ---------- NAVIGATION ----------

def test_navigation_next_prev():
    controller = ChatController()

    pair1 = DummyPair("r1", "a1")
    pair2 = DummyPair("r2", "a2")
    pair3 = DummyPair("r3", "a3")

    chat = DummyChat("Chat", [pair1, pair2, pair3])
    controller.set_current_chat(chat)

    assert controller.current_pair_index == 0

    controller.next_pair()
    assert controller.current_pair_index == 1

    controller.next_pair()
    assert controller.current_pair_index == 2

    # next at end
    controller.next_pair()
    assert controller.current_pair_index == 2

    controller.prev_pair()
    assert controller.current_pair_index == 1

    controller.prev_pair()
    assert controller.current_pair_index == 0

    # prev at start
    controller.prev_pair()
    assert controller.current_pair_index == 0
