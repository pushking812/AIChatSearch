
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

import tkinter as tk
from unittest.mock import patch
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


def test_open_archive_success(monkeypatch):
    import tkinter as _tk
    _orig_init = _tk.Tk.__init__
    _tk.Tk.__init__ = lambda self: None
    app = Application()
    _tk.Tk.__init__ = _orig_init
    app.withdraw()

    dummy_chat = DummyChat("Chat1", [])

    monkeypatch.setattr("deepseek.gui.filedialog.askopenfilename", lambda **kwargs: "file.zip")
    monkeypatch.setattr("deepseek.gui.model.load_from_zip", lambda path: [dummy_chat])

    app.open_archive()
    assert app.chat_listbox.size() == 1

    app.destroy()


def test_open_archive_exception(monkeypatch):
    import tkinter as _tk
    _orig_init = _tk.Tk.__init__
    _tk.Tk.__init__ = lambda self: None
    app = Application()
    _tk.Tk.__init__ = _orig_init
    app.withdraw()

    monkeypatch.setattr("deepseek.gui.filedialog.askopenfilename", lambda **kwargs: "file.zip")
    monkeypatch.setattr("deepseek.gui.model.load_from_zip", lambda path: (_ for _ in ()).throw(Exception("fail")))
    monkeypatch.setattr("deepseek.gui.messagebox.showerror", lambda *args, **kwargs: None)

    app.open_archive()
    app.destroy()


def test_on_chat_select_and_tree_select():
    import tkinter as _tk
    _orig_init = _tk.Tk.__init__
    _tk.Tk.__init__ = lambda self: None
    app = Application()
    _tk.Tk.__init__ = _orig_init
    app.withdraw()

    pair = DummyPair(1, "req", "resp")
    chat = DummyChat("Chat1", [pair])

    app.controller.set_chats([chat])
    app._update_chat_list()

    app.chat_listbox.selection_set(0)
    app.on_chat_select()

    items = app.tree.get_children()
    assert len(items) == 1

    app.tree.selection_set(items[0])
    app.on_tree_select()

    app.destroy()


def test_perform_search_no_selected_chats():
    import tkinter as _tk
    _orig_init = _tk.Tk.__init__
    _tk.Tk.__init__ = lambda self: None
    app = Application()
    _tk.Tk.__init__ = _orig_init
    app.withdraw()

    app.search_var.set("abc")
    app.perform_search()

    assert app.search_counter.cget("text") == "0 / 0"

    app.destroy()
