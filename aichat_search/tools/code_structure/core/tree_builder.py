# aichat_search/tools/code_structure/core/tree_builder.py

import logging
from typing import Dict, Any, Optional, List, Tuple

from aichat_search.tools.code_structure.models.containers import Container, Version

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class TreeBuilder:
    def build_display_tree(self, module_containers: Dict[str, Container], local_only: bool = False) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Строит дерево для отображения и плоский список узлов с версиями.

        Returns:
            tuple: (root_node, flat_items)
        """
        if not module_containers:
            return self._empty_tree(), []

        max_version = 0
        children = []
        flat_items = []

        for name, container in module_containers.items():
            # Фильтрация по локальности
            if local_only and not self._is_container_local(container):
                continue
            node = self._container_to_node(container, local_only, flat_items)
            if node:
                children.append(node)
                if 'max_version' in node:
                    max_version = max(max_version, node['max_version'])

        root = {
            'text': 'Все модули',
            'type': 'root',
            'signature': '',
            'version': f"v{max_version}" if max_version > 0 else '',
            'sources': '',
            'children': children
        }
        return root, flat_items

    def _empty_tree(self):
        return {
            'text': 'Все модули',
            'type': 'root',
            'signature': '',
            'version': '',
            'sources': '',
            'children': []
        }

    def _is_container_local(self, container: Container) -> bool:
        """Проверяет, является ли контейнер локальным (не импортированным)."""
        if container.node_type == 'module':
            return not getattr(container, 'is_imported', False)
        # Для пакета: проверяем детей
        for child in container.children:
            if self._is_container_local(child):
                return True
        return False

    def _container_to_node(self, container: Container, local_only: bool, flat_items: List[Dict[str, Any]], parent_path: str = "") -> Optional[Dict[str, Any]]:
        try:
            node = {
                'text': container.name,
                'type': container.node_type,
                'signature': '',
                'version': '',
                'sources': '',
                'children': [],
                'max_version': 0,
                '_container': container
            }

            if container.node_type in ('function', 'method', 'code_block', 'import'):
                max_version = len(container.versions)
                node['version'] = f"v{max_version}" if max_version > 0 else ''
                node['max_version'] = max_version
                # Добавляем версии как детей
                for i, version in enumerate(container.versions):
                    version_node = self._version_to_node(version, i + 1)
                    node['children'].append(version_node)
                # Добавляем информацию в плоский список
                self._add_flat_item(container, node, flat_items, parent_path)

            elif container.node_type in ('module', 'class', 'package'):
                current_path = f"{parent_path}.{container.name}" if parent_path else container.name
                for child in container.children:
                    child_node = self._container_to_node(child, local_only, flat_items, current_path)
                    if child_node:
                        node['children'].append(child_node)

            return node

        except Exception as e:
            logger.error(f"Ошибка преобразования контейнера {container.name}: {e}")
            return None

    def _add_flat_item(self, container: Container, node_data: Dict[str, Any], flat_items: List[Dict[str, Any]], parent_path: str):
        """Добавляет информацию об узле в плоский список."""
        latest = container.get_latest_version()
        if latest and latest.sources:
            block_id, start, end, _ = latest.sources[0]
            item = {
                'block_id': block_id,
                'block_name': block_id,  # пока используем block_id как имя
                'node_path': node_data['text'],
                'parent_path': parent_path,
                'lines': f"{start}-{end}",
                'node_type': container.node_type,
                'module': None,  # будет заполнено позже в контроллере
                'class': None,
                'strategy': None
            }
            flat_items.append(item)

    def _version_to_node(self, version: Version, index: int) -> Dict[str, Any]:
        last_source = version.get_last_source()
        if last_source:
            block_id, start, end, _ = last_source
            sources = f"{block_id}:{start}-{end}"
            sources_count = len(version.sources)
            if sources_count > 1:
                sources += f" ({sources_count})"
        else:
            sources = ''
        return {
            'text': version.node.name,
            'type': 'version',
            'signature': version.node.signature,
            'version': f"v{index}",
            'sources': sources,
            'children': [],
            '_version_data': version
        }