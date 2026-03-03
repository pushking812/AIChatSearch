# deepseek/model.py

import json
import zipfile
import logging
from datetime import datetime
from typing import List, Optional

from .utils import parse_datetime

raw_data = None
logger = logging.getLogger(__name__)


# =========================
# MessagePair
# =========================


class MessagePair:
    def __init__(
        self,
        index: str,
        request_text: str,
        response_text: str,
        request_time: Optional[datetime],
        response_time: Optional[datetime],
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


# =========================
# Chat
# =========================

class Chat:
    def __init__(
        self,
        chat_id: str,
        title: str,
        created_at: Optional[datetime],
        updated_at: Optional[datetime],
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


# =========================
# ZIP Loader
# =========================

def load_from_zip(zip_path: str) -> List[Chat]:
    global raw_data
    chats: List[Chat] = []

    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            if "conversations.json" not in z.namelist():
                raise FileNotFoundError("conversations.json not found in archive")

            with z.open("conversations.json") as f:
                raw_data = json.load(f)

    except zipfile.BadZipFile:
        raise ValueError("Invalid or corrupted ZIP archive")

    if not isinstance(raw_data, list):
        raise ValueError("conversations.json must contain a list of chats")

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

            timeline = []

            # --- Формируем timeline из ВСЕХ fragments ---
            for node_id, node_data in mapping.items():
                message = node_data.get("message")
                if not message:
                    continue

                fragments = message.get("fragments", [])
                if not fragments:
                    continue  # узлы типа #5 просто пропускаем

                msg_time = parse_datetime(message.get("inserted_at"))

                for fragment in fragments:
                    f_type = fragment.get("type")
                    f_text = fragment.get("content", "")

                    timeline.append(
                        (node_id, f_type, f_text, msg_time)
                    )

            # --- сортировка по времени ---
            timeline.sort(key=lambda x: x[3] or datetime.min)

            pending_request = None
            think_buffer = []

            for node_id, f_type, f_text, msg_time in timeline:

                if f_type == "REQUEST":
                    pending_request = (node_id, f_text, msg_time)
                    think_buffer = []

                elif f_type == "THINK":
                    think_buffer.append(f_text)

                elif f_type == "RESPONSE":
                    if pending_request:
                        req_node_id, req_text, req_time = pending_request

                        full_response = ""

                        if think_buffer:
                            full_response += (
                                "=== THINK ===\n"
                                + "\n\n".join(think_buffer)
                                + "\n\n=== RESPONSE ===\n"
                            )

                        full_response += f_text

                        pair = MessagePair(
                            index=req_node_id,
                            request_text=req_text,
                            response_text=full_response,
                            request_time=req_time,
                            response_time=msg_time,
                            request_node_id=req_node_id,
                            response_node_id=node_id,
                        )

                        chat.add_pair(pair)

                        pending_request = None
                        think_buffer = []
                    else:
                        # если нет запроса — просто игнорируем
                        logger.debug(
                            f"Orphan response in chat {chat_id} (node {node_id})"
                        )

            chats.append(chat)

        except Exception as e:
            logger.warning(
                f"Failed to process chat {chat_item.get('id')}: {e}"
            )

    return chats