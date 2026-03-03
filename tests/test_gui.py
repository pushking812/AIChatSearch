
import tkinter as tk
import pytest
from deepseek.gui import Application


class DummyChat:
    def __init__(self, title, pairs):
        self.title = title
        self._pairs = pairs

    def get_pairs(self):
        return self._pairs


class DummyPair:
    def __init__(self, index, request, response):
        self.index = index
        self.request_text = request
        self.response_text = response


@pytest.fixture
def app():
    application = Application()
    application.withdraw()
    yield application
    application.destroy()


def test_update_chat_list(app):
    chat = DummyChat("Chat1", [])
    app.controller.set_chats([chat])
    app._update_chat_list()
    assert app.chat_listbox.size() == 1


def test_filter_chats(app):
    app.chat_filter_var.set("test")
    app.filter_chats()
    # just ensure no crash and list updated
    assert isinstance(app.chat_listbox.size(), int)


def test_display_pair(app):
    pair = DummyPair(1, "req", "resp")
    app._display_pair(pair)
    assert "req" in app.request_text.get("1.0", tk.END)
    assert "resp" in app.response_text.get("1.0", tk.END)


def test_select_all_and_clear(app):
    chat = DummyChat("Chat1", [])
    app.controller.set_chats([chat])
    app._update_chat_list()

    app.select_all_chats()
    app.clear_chat_selection()

    assert app.current_selected_chats == []


def test_reset_search(app):
    app.search_var.set("abc")
    app.reset_search()
    assert app.search_var.get() == ""


def test_update_nav_buttons_no_selection(app):
    app.update_nav_buttons()
    # ensure buttons exist and state is valid
    assert app.prev_button["state"] in ("normal", "disabled")
    assert app.next_button["state"] in ("normal", "disabled")


def test_prev_search_result_no_results(app):
    app.search_results = []
    app.current_result_index = -1
    app.prev_search_result()  # should not crash
    assert app.current_result_index == -1


def test_next_search_result_no_results(app):
    app.search_results = []
    app.current_result_index = -1
    app.next_search_result()  # should not crash
    assert app.current_result_index == -1


def test_update_position_label_without_selection(app):
    app.position_label.config(text="")
    app._update_position_label()
    # label should remain a string
    assert isinstance(app.position_label.cget("text"), str)


def test_on_chat_select_populates_tree(app):
    # create chat with one pair
    class Pair:
        def __init__(self):
            self.index = 1
            self.request_text = "req"
            self.response_text = "resp"

    class Chat:
        def __init__(self):
            self.title = "Chat1"
            self._pairs = [Pair()]
        def get_pairs(self):
            return self._pairs

    chat = Chat()
    app.controller.set_chats([chat])
    app._update_chat_list()

    # select first chat
    app.chat_listbox.selection_set(0)
    app.on_chat_select()

    items = app.tree.get_children()
    assert len(items) == 1


def test_on_tree_select_displays_pair(app):
    class Pair:
        def __init__(self):
            self.index = 1
            self.request_text = "hello"
            self.response_text = "world"

    class Chat:
        def __init__(self):
            self.title = "Chat1"
            self._pairs = [Pair()]
        def get_pairs(self):
            return self._pairs

    chat = Chat()
    app.controller.set_chats([chat])
    app._update_chat_list()

    app.chat_listbox.selection_set(0)
    app.on_chat_select()

    items = app.tree.get_children()
    app.tree.selection_set(items[0])
    app.on_tree_select()

    assert "hello" in app.request_text.get("1.0", "end")
    assert "world" in app.response_text.get("1.0", "end")
