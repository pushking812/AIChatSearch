# code_structure/module_resolution/services/module_service.py

"""
Заглушка для обратной совместимости.
В новой версии этот модуль не используется.
"""

from typing import List, Dict, Optional, Tuple
from code_structure.models.block import Block
from code_structure.models.versioned_node import VersionedNode


class ModuleService:
    def __init__(self):
        self.module_containers: Dict[str, VersionedNode] = {}
        self.unknown_blocks: List[Block] = []

    def get_known_modules(self) -> List[str]:
        return []

    def get_module_source(self, module_name: str, blocks: List[Block]) -> Optional[str]:
        return None

    def get_module_code(self, module_name: str, blocks: List[Block]) -> Optional[str]:
        return None

    def process_blocks(
        self,
        blocks: List[Block],
        **kwargs
    ) -> Tuple[Dict[str, VersionedNode], List[Block]]:
        return {}, []

    def reset_assignments(self, blocks: List[Block]) -> None:
        pass