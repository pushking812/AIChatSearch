import json
import zipfile
import tempfile
import os
import pytest

from src.model import load_from_zip
from src.utils import parse_datetime


def create_test_zip(json_content: str) -> str:
    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, "test.zip")

    with zipfile.ZipFile(zip_path, "w") as z:
        z.writestr("conversation.json", json_content)

    return zip_path


def test_load_from_zip_success():
    test_json = json.dumps([
        {
            "id": "chat1",
            "title": "Test Chat",
            "inserted_at": "2024-01-01T10:00:00+00:00",
            "updated_at": "2024-01-01T10:05:00+00:00",
            "mapping": {
                "1": {
                    "inserted_at": "2024-01-01T10:00:00+00:00",
                    "message": {
                        "role": "user",
                        "content": {"parts": ["Hello"]}
                    }
                },
                "2": {
                    "inserted_at": "2024-01-01T10:01:00+00:00",
                    "message": {
                        "role": "assistant",
                        "content": {"parts": ["Hi there!"]}
                    }
                }
            }
        }
    ])

    zip_path = create_test_zip(test_json)
    chats = load_from_zip(zip_path)

    assert len(chats) == 1
    assert len(chats[0].pairs) == 1


def test_skip_invalid_pair():
    test_json = json.dumps([
        {
            "id": "chat1",
            "mapping": {
                "1": {
                    "inserted_at": "2024-01-01T10:00:00+00:00",
                    "message": {"role": "assistant", "content": {"parts": ["Oops"]}}
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
        z.writestr("conversation.json", "not json")

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
