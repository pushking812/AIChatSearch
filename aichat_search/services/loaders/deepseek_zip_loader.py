# aichat_search/services/loaders/deepseek_zip_loader.py

import json
import zipfile
import logging
import re
from datetime import datetime
from typing import List, Optional

from ...model import Chat, MessagePair
from ...utils import parse_datetime
from .base import ChatLoader

logger = logging.getLogger(__name__)


class DeepSeekZipLoader(ChatLoader):
    """Загрузчик для ZIP-архивов DeepSeek, содержащих conversations.json."""

    # Опциональный паттерн для имени файла (можно убрать, если не нужен)
    FILENAME_PATTERN = re.compile(r'deepseek_data-\d{4}-\d{2}-\d{2}\.zip$')

    @classmethod
    def can_load(cls, file_path: str) -> bool:
        # Проверяем расширение .zip
        if not file_path.lower().endswith('.zip'):
            return False

        # Проверяем наличие conversations.json внутри архива
        try:
            with zipfile.ZipFile(file_path, 'r') as zf:
                return 'conversations.json' in zf.namelist()
        except (zipfile.BadZipFile, FileNotFoundError):
            return False

    def load(self, file_path: str) -> List[Chat]:
        chats: List[Chat] = []

        try:
            with zipfile.ZipFile(file_path, "r") as z:
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
                chat = self._process_chat(chat_item)
                if chat:
                    chats.append(chat)
            except Exception as e:
                logger.warning(f"Failed to process chat {chat_item.get('id')}: {e}")

        return chats

    def _build_timeline_from_mapping(self, mapping: dict) -> List[tuple]:
        """Строит список фрагментов (timeline) из mapping'а чата."""
        timeline = []
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
                timeline.append((node_id, f_type, f_text, msg_time))
        return timeline

    def _process_fragments(self, timeline: List[tuple]) -> List[MessagePair]:
        """Обрабатывает отсортированный timeline и возвращает список пар сообщений."""
        pairs = []
        pending_request = None
        think_buffer = []

        def finalize_pending():
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
                pairs.append(pair)
                pending_request = None
                think_buffer = []

        for node_id, f_type, f_text, msg_time in timeline:
            if f_type == "REQUEST":
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
                    pairs.append(pair)
                    pending_request = None
                    think_buffer = []
                else:
                    logger.debug(f"Orphan response (node {node_id})")

        finalize_pending()
        return pairs

    def _process_chat(self, chat_item: dict) -> Optional[Chat]:
        """Обрабатывает один элемент чата из JSON и возвращает объект Chat."""
        chat_id = chat_item.get("id")
        title = chat_item.get("title", "Untitled")

        created_at = parse_datetime(chat_item.get("inserted_at"))
        updated_at = parse_datetime(chat_item.get("updated_at"))

        chat = Chat(chat_id, title, created_at, updated_at)

        mapping = chat_item.get("mapping", {})
        if not isinstance(mapping, dict):
            logger.warning(f"Invalid mapping in chat {chat_id}")
            return None

        timeline = self._build_timeline_from_mapping(mapping)

        # Сортировка по времени с добавлением индекса для стабильности
        timeline_with_idx = [(t[0], t[1], t[2], t[3], idx) for idx, t in enumerate(timeline)]
        timeline_with_idx.sort(key=lambda x: (x[3] or datetime.min, x[4]))
        sorted_timeline = [(t[0], t[1], t[2], t[3]) for t in timeline_with_idx]

        pairs = self._process_fragments(sorted_timeline)
        for pair in pairs:
            chat.add_pair(pair)

        return chat