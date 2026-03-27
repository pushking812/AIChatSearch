# aichat_search/tools/code_structure/core/tree_builder.py

import logging
from typing import Dict, Any, Optional

from aichat_search.tools.code_structure.models.containers import Container, Version

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class TreeBuilder:
    def build_display_tree(self, module_containers: Dict[str, Container]) -> Dict[str, Any]:
        if not module_containers:
            return self._empty_tree()

        max_version = 0
        children = []

        for name, container in module_containers.items():
            node = self._container_to_node(container)
            if node:
                children.append(node)
                if 'max_version' in node:
                    max_version = max(max_version, node['max_version'])

        return {
            'text': 'Все модули',
            'type': 'root',
            'signature': '',
            'version': f"v{max_version}" if max_version > 0 else '',
            'sources': '',
            'children': children
        }

    def _empty_tree(self) -> Dict[str, Any]:
        return {
            'text': 'Все модули',
            'type': 'root',
            'signature': '',
            'version': '',
            'sources': '',
            'children': []
        }

    def _container_to_node(self, container: Container) -> Optional[Dict[str, Any]]:
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
                for i, version in enumerate(container.versions):
                    node['children'].append(self._version_to_node(version, i + 1))

            elif container.node_type in ('module', 'class', 'package'):
                for child in container.children:
                    child_node = self._container_to_node(child)
                    if child_node:
                        node['children'].append(child_node)

            return node

        except Exception as e:
            logger.error(f"Ошибка преобразования контейнера {container.name}: {e}")
            return None

    def _version_to_node(self, version: Version, index: int) -> Dict[str, Any]:
        last_source = version.get_last_source()
        if last_source:
            block_id, start, end, _ = last_source
            sources = f"{block_id}:{start}-{end}"
            # Добавляем количество источников
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