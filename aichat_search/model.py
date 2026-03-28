# aichat_search/model.py

import os
from datetime import datetime
from typing import List, Optional



# =========================
# MessagePair
# =========================

class MessagePair:
    """Хранит одну пару «запрос–ответ» из чата."""
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
    """Представляет один чат с метаданными и списком пар сообщений."""
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
# DataSource
# =========================

class DataSource:
    """Источник данных – один загруженный ZIP-архив (или импортированный набор)."""
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.chats: List[Chat] = []
        self.id = os.path.basename(file_path)  # упрощённо, имя файла

    def __repr__(self):
        return f"<DataSource id={self.id} chats={len(self.chats)}>"