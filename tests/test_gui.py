
import tkinter as tk
import pytest
from deepseek.gui import ChatGUI


class DummyController:
    def __init__(self):
        self._filtered = []
        self.filter_called = False

    def get_filtered_chats(self):
        return self._filtered

    def filter_chats(self, value):
        self.filter_called = True

    def set_chats(self, chats):
        pass

    def select_pair(self, chat, pair):
        return pair

    def get_nav_state(self):
        return False, False


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
def gui():
    root = tk.Tk()
    root.withdraw()
    controller = DummyController()
    app = ChatGUI(root, controller)
    yield app
    root.destroy()


def test_update_chat_list(gui):
    chat = DummyChat("Chat1", [])
    gui.controller._filtered = [chat]
    gui._update_chat_list()
    assert gui.chat_listbox.size() == 1


def test_filter_chats_calls_controller(gui):
    gui.filter_chats()
    assert gui.controller.filter_called is True


def test_display_pair(gui):
    pair = DummyPair(1, "req", "resp")
    gui._display_pair(pair)
    assert "req" in gui.request_text.get("1.0", tk.END)
    assert "resp" in gui.response_text.get("1.0", tk.END)


def test_select_all_and_clear(gui):
    gui.select_all_chats()
    gui.clear_chat_selection()
    assert gui.current_selected_chats == []


def test_reset_search(gui):
    gui.search_var.set("test")
    gui.reset_search()
    assert gui.search_var.get() == ""
