# code_structure/models/block.py

"""
Модели уровня блоков (Block).
"""

from dataclasses import dataclass
from typing import Optional

# Импортируем существующие классы из aichat_search (они будут использоваться)
from aichat_search.model import Chat, MessagePair


@dataclass(frozen=True)
class Block:
    """
    Блок кода, извлечённый из сообщения.
    """
    id: str                     # уникальный идентификатор (например, "chat_{id}_msg_{pair.index}_block{idx}")
    chat: Chat                  # ссылка на чат, которому принадлежит сообщение
    message_pair: MessagePair   # ссылка на пару сообщений (запрос-ответ)
    language: str               # язык программирования
    content: str                # исходный код блока
    block_idx: int              # порядковый номер блока в сообщении
    global_index: int           # сквозной индекс при загрузке (для сортировки)

    @property
    def timestamp(self) -> float:
        """Возвращает временную метку блока (время ответа или запроса)."""
        ts = self.message_pair.response_time or self.message_pair.request_time
        return ts.timestamp() if ts else 0.0

    @property
    def pair_index(self) -> str:
        """Удобный доступ к индексу пары сообщений."""
        return self.message_pair.index

    @property
    def chat_id(self) -> str:
        return self.chat.id

    def __repr__(self) -> str:
        return f"<Block id={self.id} lang={self.language} lines={len(self.content.splitlines())}>"