# aichat_search/tools/code_structure/services/tree_service.py

from typing import Dict, Any, Optional
import logging

from aichat_search.tools.code_structure.core.tree_builder import TreeBuilder
from aichat_search.tools.code_structure.models.containers import Container

logger = logging.getLogger(__name__)


class TreeService:
    """Сервис для построения деревьев отображения."""
    
    def __init__(self):
        self.tree_builder = TreeBuilder()
        self.display_root: Optional[Dict[str, Any]] = None
    
    def build_display_tree(self, module_containers: Dict[str, Container]) -> Dict[str, Any]:
        """Строит дерево для отображения из контейнеров модулей."""
        self.display_root = self.tree_builder.build_display_tree(module_containers)
        logger.info(f"Построено дерево с {len(self.display_root.get('children', []))} модулями")
        return self.display_root
    
    def get_node_by_path(self, path: str) -> Optional[Dict[str, Any]]:
        """Возвращает узел дерева по пути (для будущего использования)."""
        # Можно реализовать при необходимости
        pass