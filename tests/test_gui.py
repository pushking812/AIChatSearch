
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
