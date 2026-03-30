# models/registry.py
from typing import Dict, Optional, List
from .block import Block


class BlockRegistry:
    """
    Реестр всех блоков. Позволяет получать блок по его идентификатору.
    Используется как синглтон.
    """
    _instance = None
    _blocks: Dict[str, Block] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def register(self, block: Block) -> None:
        self._blocks[block.id] = block

    def get(self, block_id: str) -> Optional[Block]:
        return self._blocks.get(block_id)

    def get_all(self) -> List[Block]:
        return list(self._blocks.values())

    def clear(self) -> None:
        self._blocks.clear()