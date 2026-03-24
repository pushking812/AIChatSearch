# aichat_search/tools/code_structure/core/tree_builder.py

import logging
import textwrap
from typing import Dict, Any, Optional, List, Set

from aichat_search.tools.code_structure.models.containers import Container, Version

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class TreeBuilder:
    def build_display_tree(self, module_containers: Dict[str, Container]) -> Dict[str, Any]:
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

    def build_display_tree_with_packages(
        self,
        module_containers: Dict[str, Container],
        imported_items: Dict[str, str],
        local_only: bool = True
    ) -> Dict[str, Any]:
        existing_modules = set(module_containers.keys())
        all_names = existing_modules | set(imported_items.keys())

        if local_only:
            local_names = self._get_local_names(all_names, module_containers)
            all_names = local_names

        package_tree = self._build_package_hierarchy(all_names, imported_items)
        self._insert_module_contents(package_tree, module_containers)

        children = list(package_tree.values())
        self._flatten_children(children)

        return {
            'text': 'Все модули',
            'type': 'root',
            'signature': '',
            'version': '',
            'sources': '',
            'children': children
        }

    def _get_local_names(self, names: Set[str], module_containers: Dict[str, Container]) -> Set[str]:
        local_names = set()
        local_names.update(module_containers.keys())
        for module in module_containers.keys():
            parts = module.split('.')
            for i in range(len(parts)):
                prefix = '.'.join(parts[:i+1])
                local_names.add(prefix)
        for name in names:
            if self._is_local_module(name, module_containers):
                local_names.add(name)
                parts = name.split('.')
                for i in range(len(parts)):
                    prefix = '.'.join(parts[:i+1])
                    local_names.add(prefix)
        return local_names

    def _is_local_module(self, name: str, module_containers: Dict[str, Container]) -> bool:
        if name in module_containers:
            return True
        parts = name.split('.')
        for i in range(len(parts)):
            parent = '.'.join(parts[:i+1])
            if parent in module_containers:
                return True
        for module in module_containers.keys():
            if module.startswith(name + '.') or module == name:
                return True
        return False

    def _build_package_hierarchy(self, names: Set[str], types: Optional[Dict[str, str]] = None) -> Dict[str, Dict[str, Any]]:
        root = {}
        for name in sorted(names):
            parts = name.split('.')
            current = root
            for i, part in enumerate(parts):
                is_last = (i == len(parts) - 1)
                if is_last and types and name in types:
                    node_type = types[name]
                else:
                    node_type = 'module' if is_last else 'package'
                if part not in current:
                    current[part] = {
                        'text': part,
                        'type': node_type,
                        'signature': '',
                        'version': '',
                        'sources': '',
                        'children': {},
                        'is_module': (node_type == 'module')
                    }
                current = current[part]['children']
        return root

    def _insert_module_contents(self, package_tree: Dict[str, Dict[str, Any]], module_containers: Dict[str, Container]):
        for module_name, container in module_containers.items():
            parts = module_name.split('.')
            current = package_tree
            node = None
            for i, part in enumerate(parts):
                if part in current:
                    node = current[part]
                    if i == len(parts) - 1:
                        container_node = self._container_to_node(container)
                        if container_node:
                            node['children'] = container_node.get('children', [])
                            node['signature'] = container_node.get('signature', '')
                            node['version'] = container_node.get('version', '')
                            node['sources'] = container_node.get('sources', '')
                            node['_container'] = container
                    else:
                        current = node['children']
                else:
                    logger.warning(f"Узел {part} для модуля {module_name} не найден в дереве")
                    break

    def _flatten_children(self, nodes: List[Dict[str, Any]]):
        for node in nodes:
            if 'children' in node and isinstance(node['children'], dict):
                children_list = list(node['children'].values())
                node['children'] = children_list
                self._flatten_children(children_list)

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

            elif container.node_type in ('module', 'class'):
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