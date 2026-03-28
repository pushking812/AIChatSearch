# aichat_search/tools/code_structure/ui/dto_builder.py

from typing import Dict, Any
from aichat_search.tools.code_structure.ui.dto import TreeDisplayNode


class DtoBuilder:
    """Построитель DTO из внутренних моделей приложения."""

    @staticmethod
    def container_to_dto_node(container) -> TreeDisplayNode:
        """Рекурсивно преобразует контейнер (Container) в TreeDisplayNode."""
        node = TreeDisplayNode(
            text=container.name,
            type=container.node_type,
            signature="",
            version="",
            sources=""
        )
        if hasattr(container, 'versions') and container.versions:
            max_version = len(container.versions)
            node.version = f"v{max_version}" if max_version > 0 else ''
        for child in container.children:
            node.children.append(DtoBuilder.container_to_dto_node(child))
        return node

    @staticmethod
    def tree_dict_to_dto(root_dict: Dict[str, Any]) -> TreeDisplayNode:
        """Преобразует словарь от TreeBuilder.build_display_tree в TreeDisplayNode."""
        def convert(node_dict):
            node = TreeDisplayNode(
                text=node_dict.get('text', ''),
                type=node_dict.get('type', ''),
                signature=node_dict.get('signature', ''),
                version=node_dict.get('version', ''),
                sources=node_dict.get('sources', '')
            )
            for child in node_dict.get('children', []):
                node.children.append(convert(child))
            return node
        return convert(root_dict)