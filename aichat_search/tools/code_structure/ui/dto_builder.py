# aichat_search/tools/code_structure/ui/dto_builder.py

from typing import Dict, Any, List
from aichat_search.tools.code_structure.ui.dto import TreeDisplayNode, FlatListItem


class DtoBuilder:
    """Построитель DTO из внутренних моделей приложения."""

    @staticmethod
    def container_to_dto_node(container) -> TreeDisplayNode:
        full_name = container.full_path if hasattr(container, 'full_path') else container.name
        node = TreeDisplayNode(
            text=container.name,
            type=container.node_type,
            full_name=full_name
        )
        if hasattr(container, 'versions') and container.versions:
            max_version = len(container.versions)
            node.version = f"v{max_version}" if max_version > 0 else ''
        for child in container.children:
            node.children.append(DtoBuilder.container_to_dto_node(child))
        return node

    @staticmethod
    def tree_dict_to_dto(root_dict: Dict[str, Any]) -> TreeDisplayNode:
        def convert(node_dict):
            # Получаем полное имя из текста (упрощённо)
            # В реальном дереве полное имя может быть в _container.full_path
            # Но так как в словаре нет _container, используем текст
            # Для улучшения можно сохранять полное имя в словаре
            full_name = node_dict.get('text', '')
            node = TreeDisplayNode(
                text=node_dict.get('text', ''),
                type=node_dict.get('type', ''),
                signature=node_dict.get('signature', ''),
                version=node_dict.get('version', ''),
                sources=node_dict.get('sources', ''),
                full_name=full_name
            )
            for child in node_dict.get('children', []):
                node.children.append(convert(child))
            return node
        return convert(root_dict)


    @staticmethod
    def flat_items_to_dto(items: List[Dict[str, Any]]) -> List[FlatListItem]:
        """Преобразует список словарей плоского списка в список DTO."""
        result = []
        for item in items:
            result.append(FlatListItem(
                block_id=item.get('block_id', ''),
                block_name=item.get('block_name', ''),
                node_path=item.get('node_path', ''),
                parent_path=item.get('parent_path', ''),
                lines=item.get('lines', ''),
                module=item.get('module', ''),
                class_name=item.get('class', '-'),
                strategy=item.get('strategy', '')
            ))
        return result
        
        
    @staticmethod
    def tree_dict_to_dto(root_dict: Dict[str, Any]) -> TreeDisplayNode:
        def convert(node_dict):
            node = TreeDisplayNode(
                text=node_dict.get('text', ''),
                type=node_dict.get('type', ''),
                signature=node_dict.get('signature', ''),
                version=node_dict.get('version', ''),
                sources=node_dict.get('sources', ''),
                full_name=node_dict.get('text', '')
            )
            # Если узел имеет версии, можно взять данные из первой версии
            # Но это сложно без доступа к контейнеру. Пока оставим пустым.
            for child in node_dict.get('children', []):
                node.children.append(convert(child))
            return node
        return convert(root_dict)