import json
import zipfile
import logging
from datetime import datetime
from typing import List
from .utils import parse_datetime

raw_data = None
logger = logging.getLogger(__name__)


class MessagePair:
    def __init__(
        self,
        index: str,
        request_text: str,
        response_text: str,
        request_time: datetime,
        response_time: datetime,
        request_node_id: str,
        response_node_id: str,
    ):
        self.index = index
        self.request_text = request_text
        self.response_text = response_text
        self.request_time = request_time
        self.response_time = response_time
        self.request_node_id = request_node_id
        self.response_node_id = response_node_id
        self.modified = False

    def __repr__(self):
        return (
            f"<MessagePair index={self.index} "
            f"request_len={len(self.request_text)} "
            f"response_len={len(self.response_text)} "
            f"modified={self.modified}>"
        )


class Chat:
    def __init__(
        self,
        chat_id: str,
        title: str,
        created_at: datetime,
        updated_at: datetime,
    ):
        self.id = chat_id
        self.title = title
        self.created_at = created_at
        self.updated_at = updated_at
        self.pairs: List[MessagePair] = []

    def add_pair(self, pair: MessagePair):
        self.pairs.append(pair)

    def get_pairs(self) -> List[MessagePair]:
        return self.pairs

    def __repr__(self):
        return f"<Chat id={self.id} title='{self.title}' pairs={len(self.pairs)}>"


def load_from_zip(zip_path: str) -> List[Chat]:
    global raw_data
    chats: List[Chat] = []

    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            if "conversation.json" not in z.namelist():
                raise FileNotFoundError("conversation.json not found in archive")

            try:
                with z.open("conversation.json") as f:
                    raw_data = json.load(f)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON format: {e}")
    except zipfile.BadZipFile:
        raise ValueError("Invalid or corrupted ZIP archive")
    except FileNotFoundError:
        raise
    except ValueError:
        raise
    except Exception as e:
        raise RuntimeError(f"Unexpected error while reading ZIP: {e}")

    if not isinstance(raw_data, list):
        raise ValueError("conversation.json must contain a list of chats")

    for chat_item in raw_data:
        try:
            chat_id = chat_item.get("id")
            title = chat_item.get("title", "Untitled")
            created_at = parse_datetime(chat_item.get("inserted_at"))
            updated_at = parse_datetime(chat_item.get("updated_at"))

            chat = Chat(chat_id, title, created_at, updated_at)

            mapping = chat_item.get("mapping", {})
            if not isinstance(mapping, dict):
                logger.warning(f"Invalid mapping in chat {chat_id}")
                continue

            nodes = []

            for node_id, node_data in mapping.items():
                message = node_data.get("message")
                if not message:
                    continue

                inserted_at = parse_datetime(node_data.get("inserted_at"))
                nodes.append((node_id, message, inserted_at))

            nodes.sort(key=lambda x: x[2] or datetime.min)

            i = 0
            while i < len(nodes) - 1:
                req_node_id, req_msg, req_time = nodes[i]
                res_node_id, res_msg, res_time = nodes[i + 1]

                req_role = req_msg.get("role")
                res_role = res_msg.get("role")

                if req_role == "user" and res_role == "assistant":
                    request_text = _extract_text(req_msg)
                    response_text = _extract_text(res_msg)

                    pair = MessagePair(
                        index=req_node_id,
                        request_text=request_text,
                        response_text=response_text,
                        request_time=req_time,
                        response_time=res_time,
                        request_node_id=req_node_id,
                        response_node_id=res_node_id,
                    )

                    chat.add_pair(pair)
                    i += 2
                else:
                    logger.warning(
                        f"Invalid pair sequence in chat {chat_id} "
                        f"(nodes {req_node_id}, {res_node_id})"
                    )
                    i += 1

            chats.append(chat)

        except Exception as e:
            logger.warning(f"Failed to process chat {chat_item.get('id')}: {e}")

    return chats


def _extract_text(message_obj: dict) -> str:
    content = message_obj.get("content", {})
    parts = content.get("parts", [])
    if isinstance(parts, list):
        return "\n".join(str(p) for p in parts)
    return ""
