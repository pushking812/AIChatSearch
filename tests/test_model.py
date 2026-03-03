import pytest
from src.model import Chat, MessagePair


def test_chat_creation():
    chat = Chat()
    assert isinstance(chat, Chat)


def test_message_pair_creation():
    pair = MessagePair()
    assert isinstance(pair, MessagePair)