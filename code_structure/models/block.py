# code_structure/models/block.py

"""
Модели уровня блоков (Block).
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

from aichat_search.model import Chat, MessagePair

if TYPE_CHECKING:
    from .code_node import ModuleNode


@dataclass(frozen=True)
class Block:
    """
    Блок кода, извлечённый из сообщения.
    """
    id: str                     # уникальный идентификатор
    chat: Chat                  # ссылка на чат
    message_pair: MessagePair   # ссылка на пару сообщений
    language: str               # язык программирования
    content: str                # исходный код блока
    block_idx: int              # порядковый номер в сообщении
    global_index: int           # сквозной индекс при загрузке
    code_tree: Optional['ModuleNode'] = None   # дерево парсинга
    module_hint: Optional[str] = None          # имя определённого модуля

    @property
    def timestamp(self) -> float:
        ts = self.message_pair.response_time or self.message_pair.request_time
        return ts.timestamp() if ts else 0.0

    @property
    def pair_index(self) -> str:
        return self.message_pair.index

    @property
    def chat_id(self) -> str:
        return self.chat.id

    def __repr__(self) -> str:
        return f"<Block id={self.id} lang={self.language} lines={len(self.content.splitlines())}>"