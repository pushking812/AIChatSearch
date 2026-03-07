# deepseek/services/archive_loader.py

import json
import zipfile
import logging
from datetime import datetime
from typing import List, Optional

from ..utils import parse_datetime
from ..model import Chat, MessagePair

logger = logging.getLogger(__name__)


def load_from_zip(zip_path: str) -> List[Chat]:
    chats: List[Chat] = []

    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            if "conversations.json" not in z.namelist():
                raise FileNotFoundError("conversations.json not found in archive")

            with z.open("conversations.json") as f:
                data = json.load(f)

    except zipfile.BadZipFile:
        raise ValueError("Invalid or corrupted ZIP archive")

    if not isinstance(data, list):
        raise ValueError("conversations.json must contain a list of chats")

    for chat_item in data:
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

            # Формируем timeline из всех fragments
            for node_id, node_data in mapping.items():
                message = node_data.get("message")
                if not message:
                    continue

                fragments = message.get("fragments", [])
                if not fragments:
                    continue

                msg_time = parse_datetime(message.get("inserted_at"))

                for fragment in fragments:
                    f_type = fragment.get("type")
                    f_text = fragment.get("content", "")

                    timeline.append(
                        (node_id, f_type, f_text, msg_time)
                    )

            # Сортировка по времени
            timeline.sort(key=lambda x: x[3] or datetime.min)

            pending_request = None
            think_buffer = []

            def finalize_pending():
                """Создаёт пару из текущего pending_request и think_buffer (без ответа)."""
                nonlocal pending_request, think_buffer
                if pending_request:
                    req_node_id, req_text, req_time = pending_request
                    full_response = ""
                    if think_buffer:
                        full_response = "=== THINK ===\n" + "\n\n".join(think_buffer)
                    pair = MessagePair(
                        index=req_node_id,
                        request_text=req_text,
                        response_text=full_response,
                        request_time=req_time,
                        response_time=None,
                        request_node_id=req_node_id,
                        response_node_id=None,
                    )
                    chat.add_pair(pair)
                    pending_request = None
                    think_buffer = []

            for node_id, f_type, f_text, msg_time in timeline:
                if f_type == "REQUEST":
                    # Завершаем предыдущий незавершённый запрос, если он был
                    finalize_pending()
                    pending_request = (node_id, f_text, msg_time)
                    think_buffer = []

                elif f_type == "THINK":
                    think_buffer.append(f_text)

                elif f_type == "RESPONSE":
                    if pending_request:
                        req_node_id, req_text, req_time = pending_request

                        full_response = ""
                        if think_buffer:
                            full_response = (
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
                        logger.debug(
                            f"Orphan response in chat {chat_id} (node {node_id})"
                        )

            # После окончания цикла завершаем последний запрос, если он остался
            finalize_pending()

            chats.append(chat)

        except Exception as e:
            logger.warning(
                f"Failed to process chat {chat_item.get('id')}: {e}"
            )

    return chats