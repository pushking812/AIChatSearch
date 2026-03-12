# aichat_search/tools/code_structure/models/block_info.py

from typing import Optional, List, Tuple, Any, Dict
from aichat_search.services.block_parser import MessageBlock
from .node import Node

class MessageBlockInfo:
    """
    Хранит всю информацию о блоке кода из сообщения.
    Добавлено поле metadata для хранения информации о чате и паре.
    """

    def __init__(
        self,
        block: MessageBlock,
        language: str,
        content: str,
        block_id: str = "",
        global_index: int = -1,
        module_hint: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.block = block
        self.language = language
        self.content = content
        self.block_id = block_id
        self.global_index = global_index
        self.module_hint = module_hint
        self.metadata = metadata or {}  # словарь для хранения информации о чате, времени и т.д.

        # Результат парсинга
        self.tree: Optional[Node] = None          # корневой узел (ModuleNode)
        self.syntax_error: Optional[Exception] = None

        # Поле для будущих версий
        self.cleaned_blocks: List[Tuple[int, int, str]] = []  # (start, end, cleaned_content)

    def set_tree(self, tree: Node):
        self.tree = tree

    def set_error(self, error: Exception):
        self.syntax_error = error