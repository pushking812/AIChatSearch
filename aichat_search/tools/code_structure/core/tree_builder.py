# aichat_search/tools/code_structure/core/tree_builder.py

"""Построение деревьев отображения из контейнеров."""

import logging
from typing import Dict, Any, Optional
from aichat_search.tools.code_structure.models.containers import Container, Version

logger = logging.getLogger(__name__)


class TreeBuilder:
    """Преобразует контейнеры в деревья для отображения."""

    def build_display_tree(self, module_containers: Dict[str, Container]) -> Dict[str, Any]:
        """Строит корневое дерево из контейнеров модулей."""
        if not module_containers:
            return self._empty_tree()

        max_version = 0
        children = []

        for module_name, container in module_containers.items():
            module_node = self._container_to_node(container)
            if module_node:
                children.append(module_node)
                if 'max_version' in module_node:
                    max_version = max(max_version, module_node['max_version'])

        return {
            'text': 'Все модули',
            'type': 'root',
            'signature': '',
            'version': f"v{max_version}" if max_version > 0 else '',
            'sources': '',
            'children': children
        }

    def _empty_tree(self) -> Dict[str, Any]:
        """Возвращает пустое дерево."""
        return {
            'text': 'Все модули',
            'type': 'root',
            'signature': '',
            'version': '',
            'sources': '',
            'children': []
        }

    def _container_to_node(self, container: Container) -> Optional[Dict[str, Any]]:
        """Преобразует контейнер в узел дерева."""
        try:
            # Определяем максимальную версию
            max_version = len(container.versions) if container.versions else 0

            node = {
                'text': container.name,
                'type': container.node_type,
                'signature': '',
                'version': f"v{max_version}" if max_version > 0 else '',
                'sources': '',
                'children': [],
                'max_version': max_version
            }

            # Обработка дочерних элементов
            if container.node_type in ('module', 'class'):
                child_max = 0
                for child in container.children:
                    child_node = self._container_to_node(child)
                    if child_node:
                        node['children'].append(child_node)
                        if 'max_version' in child_node:
                            child_max = max(child_max, child_node['max_version'])

                # Обновляем версию с учётом детей
                if child_max > max_version:
                    max_version = child_max
                    node['version'] = f"v{max_version}"
                    node['max_version'] = max_version

            # Добавление версий для function/method/code_block
            elif container.node_type in ('function', 'method', 'code_block'):
                for i, version in enumerate(container.versions):
                    node['children'].append(self._version_to_node(version, i + 1))

            return node

        except Exception as e:
            logger.error(f"Ошибка преобразования контейнера {container.name}: {e}")
            return None

    def _version_to_node(self, version: Version, index: int) -> Dict[str, Any]:
        """Преобразует версию в узел дерева."""
        sources = ', '.join(src[0] for src in version.sources) if version.sources else ''

        return {
            'text': version.node.name,
            'type': 'version',
            'signature': version.node.signature,
            'version': f"v{index}",
            'sources': sources,
            'children': [],
            '_version_data': version
        }