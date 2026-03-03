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
