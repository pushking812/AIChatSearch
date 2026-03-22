# aichat_search/tools/code_structure/services/tree_service.py

from typing import Dict, Any
import logging

from aichat_search.tools.code_structure.core.tree_builder import TreeBuilder
from aichat_search.tools.code_structure.models.containers import Container

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class TreeService:
    def __init__(self):
        self.tree_builder = TreeBuilder()
        self.display_root = None

    def build_display_tree(self, module_containers: Dict[str, Container]) -> Dict[str, Any]:
        self.display_root = self.tree_builder.build_display_tree(module_containers)
        logger.info(f"Построено дерево с {len(self.display_root.get('children', []))} модулями")
        return self.display_root

    def build_package_tree(
        self,
        module_containers: Dict[str, Container],
        imported_items: Dict[str, str],
        local_only: bool = True
    ) -> Dict[str, Any]:
        self.display_root = self.tree_builder.build_display_tree_with_packages(
            module_containers, imported_items, local_only
        )
        logger.info(f"Построено дерево с пакетами, корень: {self.display_root.get('text')}")
        return self.display_root