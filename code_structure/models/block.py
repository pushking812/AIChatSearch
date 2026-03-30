# code_structure/models/block.py

import re
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

from aichat_search.model import Chat, MessagePair

if TYPE_CHECKING:
    from .code_node import ModuleNode


@dataclass(frozen=True)
class Block:
    chat: Chat
    message_pair: MessagePair
    language: str
    content: str
    block_idx: int
    global_index: int
    code_tree: Optional['ModuleNode'] = None
    module_hint: Optional[str] = None
    id: str = field(init=False)   # вычисляется автоматически

    def __post_init__(self):
        """Вычисляет служебный идентификатор блока."""
        object.__setattr__(
            self, 'id',
            f"chat_{self.chat_display_name}_msg_{self.message_pair.index}_block{self.block_idx}"
        )

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

    @property
    def chat_display_name(self) -> str:
        """Очищенное название чата для использования в именах."""
        title = self.chat.title or "unknown"
        return re.sub(r'\W+', '_', title)

    @property
    def display_name(self) -> str:
        """Человекочитаемое имя блока, используемое в UI и логах."""
        return f"chat_{self.chat_display_name}_msg_{self.pair_index}_block{self.block_idx}"

    def __repr__(self) -> str:
        return f"<Block name={self.display_name} lang={self.language} lines={len(self.content.splitlines())}>"