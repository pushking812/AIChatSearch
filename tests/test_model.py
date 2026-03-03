import json
import zipfile
import tempfile
import os

from src.model import load_from_zip


def create_test_zip(json_content: str) -> str:
    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, "test.zip")

    with zipfile.ZipFile(zip_path, "w") as z:
        z.writestr("conversation.json", json_content)

    return zip_path


def test_load_from_zip():
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
    chat = chats[0]
    assert chat.title == "Test Chat"
    assert len(chat.pairs) == 1

    pair = chat.pairs[0]
    assert pair.request_text == "Hello"
    assert pair.response_text == "Hi there!"
