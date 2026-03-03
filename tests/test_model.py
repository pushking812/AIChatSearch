import json
import zipfile
import tempfile
import os
import pytest

from deepseek.model import load_from_zip
from deepseek.utils import parse_datetime


def create_test_zip(json_content: str) -> str:
    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, "test.zip")

    with zipfile.ZipFile(zip_path, "w") as z:
        z.writestr("conversations.json", json_content)

    return zip_path


def test_load_from_zip_success():
    test_json = json.dumps([
        {
            "id": "chat1",
            "title": "Test Chat",
            "inserted_at": "2024-01-01T10:00:00+00:00",
            "updated_at": "2024-01-01T10:05:00+00:00",
            "mapping": {
                "root": {
                    "id": "root",
                    "parent": None,
                    "children": ["1"],
                    "message": None
                },
                "1": {
                    "id": "1",
                    "parent": "root",
                    "children": ["2"],
                    "message": {
                        "inserted_at": "2024-01-01T10:00:00+00:00",
                        "fragments": [
                            {"type": "REQUEST", "content": "Hello"}
                        ]
                    }
                },
                "2": {
                    "id": "2",
                    "parent": "1",
                    "children": [],
                    "message": {
                        "inserted_at": "2024-01-01T10:01:00+00:00",
                        "fragments": [
                            {"type": "THINK", "content": "..."},
                            {"type": "RESPONSE", "content": "Hi there!"}
                        ]
                    }
                }
            }
        }
    ])

    zip_path = create_test_zip(test_json)
    chats = load_from_zip(zip_path)

    assert len(chats) == 1
    assert len(chats[0].pairs) == 1
    assert chats[0].pairs[0].request_text == "Hello"
    assert "Hi there!" in chats[0].pairs[0].response_text


def test_skip_invalid_pair():
    test_json = json.dumps([
        {
            "id": "chat1",
            "mapping": {
                "root": {
                    "id": "root",
                    "parent": None,
                    "children": ["1"],
                    "message": None
                },
                "1": {
                    "id": "1",
                    "parent": "root",
                    "children": [],
                    "message": {
                        "inserted_at": "2024-01-01T10:00:00+00:00",
                        "fragments": [
                            {"type": "RESPONSE", "content": "Oops"}
                        ]
                    }
                }
            }
        }
    ])

    zip_path = create_test_zip(test_json)
    chats = load_from_zip(zip_path)

    assert len(chats[0].pairs) == 0


def test_invalid_json():
    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, "bad.zip")

    with zipfile.ZipFile(zip_path, "w") as z:
        z.writestr("conversations.json", "not json")

    with pytest.raises(ValueError):
        load_from_zip(zip_path)


def test_missing_conversation_file():
    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, "bad.zip")

    with zipfile.ZipFile(zip_path, "w") as z:
        z.writestr("other.json", "{}")

    with pytest.raises(FileNotFoundError):
        load_from_zip(zip_path)


def test_parse_datetime():
    dt = parse_datetime("2024-01-01T10:00:00+02:00")
    assert dt.year == 2024
    assert dt.tzinfo is None

import json
import zipfile
import pytest
from deepseek.model import MessagePair, Chat, load_from_zip


# ---------- ADDITIONAL MODEL COVERAGE TESTS ----------

def test_messagepair_repr():
    pair = MessagePair("1", "req", "resp", None, None, "n1", "n2")
    r = repr(pair)
    assert "MessagePair" in r
    assert "index=1" in r


def test_chat_repr_and_get_pairs():
    chat = Chat("1", "Title", None, None)
    assert chat.get_pairs() == []
    r = repr(chat)
    assert "Chat" in r
    assert "Title" in r


def test_load_from_zip_invalid_zip(tmp_path):
    p = tmp_path / "bad.zip"
    p.write_text("not a zip")
    with pytest.raises(ValueError):
        load_from_zip(str(p))


def test_load_from_zip_invalid_raw_data(tmp_path):
    zip_path = tmp_path / "test.zip"
    with zipfile.ZipFile(zip_path, "w") as z:
        z.writestr("conversations.json", json.dumps({}))
    with pytest.raises(ValueError):
        load_from_zip(str(zip_path))


def test_load_from_zip_invalid_mapping(tmp_path):
    data = [{
        "id": "1",
        "title": "Chat",
        "inserted_at": None,
        "updated_at": None,
        "mapping": []
    }]

    zip_path = tmp_path / "test2.zip"
    with zipfile.ZipFile(zip_path, "w") as z:
        z.writestr("conversations.json", json.dumps(data))

    chats = load_from_zip(str(zip_path))
    assert len(chats) == 1
    assert chats[0].get_pairs() == []


def test_load_from_zip_empty_fragments(tmp_path):
    data = [{
        "id": "1",
        "title": "Chat",
        "inserted_at": None,
        "updated_at": None,
        "mapping": {
            "node1": {
                "message": {
                    "fragments": [],
                    "inserted_at": None
                }
            }
        }
    }]

    zip_path = tmp_path / "test3.zip"
    with zipfile.ZipFile(zip_path, "w") as z:
        z.writestr("conversations.json", json.dumps(data))

    chats = load_from_zip(str(zip_path))
    assert len(chats) == 1
    assert chats[0].get_pairs() == []


def test_load_from_zip_exception_branch(tmp_path):
    data = [{
        "id": "1",
        "title": "Chat",
        "inserted_at": None,
        "updated_at": None,
        "mapping": None
    }]

    zip_path = tmp_path / "test4.zip"
    with zipfile.ZipFile(zip_path, "w") as z:
        z.writestr("conversations.json", json.dumps(data))

    chats = load_from_zip(str(zip_path))
    assert isinstance(chats, list)
