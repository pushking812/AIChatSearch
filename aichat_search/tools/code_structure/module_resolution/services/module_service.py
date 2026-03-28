# aichat_search/tools/code_structure/services/module_service.py

from typing import List, Dict, Optional, Tuple
import logging
import sys

from aichat_search.tools.code_structure.module_resolution.models.block_info import MessageBlockInfo
from aichat_search.tools.code_structure.module_resolution.models.containers import (
    Container, CodeBlockContainer, ImportContainer, Version
)
from aichat_search.tools.code_structure.module_resolution.services.module_resolver_service import ModuleResolverService
from aichat_search.tools.code_structure.imports.services.import_service import ImportService
from aichat_search.tools.code_structure.module_resolution.core.module_identifier import ModuleIdentifier
from aichat_search.tools.code_structure.imports.models.import_models import ImportInfo
from aichat_search.tools.code_structure.parsing.models.node import CodeBlockNode

from aichat_search.tools.code_structure.utils.logger import get_logger
logger = get_logger(__name__, level = logging.WARNING)


class ModuleService:
    def __init__(self):
        self.import_service = ImportService()
        self.resolver_service = ModuleResolverService(self.import_service)
        self.module_containers: Dict[str, Container] = {}
        self.unknown_blocks: List[MessageBlockInfo] = []

    @property
    def identifier(self) -> ModuleIdentifier:
        return self.resolver_service.module_identifier

    def process_blocks(
        self,
        blocks: List[MessageBlockInfo],
        imported_by_module: Optional[Dict[str, List[ImportInfo]]] = None,
        text_blocks_by_pair: Optional[Dict[str, Dict[int, str]]] = None,
        full_texts_by_pair: Optional[Dict[str, str]] = None
    ) -> Tuple[Dict[str, Container], List[MessageBlockInfo]]:
        # 1. Разрешаем модули (получаем базовые контейнеры с иерархией)
        containers, unknown = self.resolver_service.resolve_blocks(
            blocks,
            text_blocks_by_pair or {},
            full_texts_by_pair or {}
        )
        # 2. Добавляем блоки кода и импорты
        self._add_code_blocks_from_blocks(blocks, containers)
        self.module_containers = containers
        self.unknown_blocks = unknown
        logger.info(f"Обработано блоков: {len(blocks)}, определено модулей: {len(containers)}")
        return containers, unknown

    def _find_container_by_path(self, root_containers: Dict[str, Container], path_parts: List[str]) -> Optional[Container]:
        current = root_containers
        for i, part in enumerate(path_parts):
            if part in current:
                container = current[part]
                if i == len(path_parts) - 1:
                    return container
                if hasattr(container, 'children_dict'):
                    current = container.children_dict
                else:
                    return None
            else:
                return None
        return None

    def _add_code_blocks_from_blocks(self, blocks: List[MessageBlockInfo], containers: Dict[str, Container]):
        for block in blocks:
            if not block.module_hint or not block.tree or block.syntax_error:
                continue

            path_parts = block.module_hint.split('.')
            module_container = self._find_container_by_path(containers, path_parts)
            if not module_container:
                logger.warning(f"Модуль {block.module_hint} не найден в контейнерах для блока {block.block_id}")
                continue

            def process_node(node, parent_container):
                for child in node.children:
                    if isinstance(child, CodeBlockNode):
                        content_lines = block.content.splitlines()
                        start = max(0, child.lineno_start - 1)
                        end = min(len(content_lines), child.lineno_end)
                        fragment = '\n'.join(content_lines[start:end])
                        is_import = any(line.strip().startswith(('import ', 'from ')) for line in fragment.splitlines())

                        if is_import:
                            container_type = ImportContainer
                            container_name = f"import_{child.lineno_start}_{child.lineno_end}"
                        else:
                            container_type = CodeBlockContainer
                            container_name = f"code_block_{child.lineno_start}_{child.lineno_end}"

                        block_container = container_type(container_name)
                        version = Version(child, block.block_id, block.global_index, block.content,
                                          block.timestamp, block.block_idx)
                        block_container.add_version(version)

                        existing = parent_container.find_child_container(container_name, block_container.node_type)
                        if existing:
                            for v in block_container.versions:
                                existing.add_version(v)
                        else:
                            parent_container.add_child(block_container)

                    elif child.node_type == 'class':
                        class_container = parent_container.find_child_container(child.name, 'class')
                        if class_container:
                            process_node(child, class_container)
                        else:
                            logger.warning(f"Класс {child.name} не найден в {parent_container.node_type} {parent_container.name} для блока {block.block_id}")
                    else:
                        process_node(child, parent_container)

            process_node(block.tree, module_container)

    def get_known_modules(self) -> List[str]:
        return sorted(self.identifier.get_known_modules())

    def get_module_source(self, module_name: str, blocks: List[MessageBlockInfo]) -> Optional[str]:
        for block in blocks:
            if block.module_hint == module_name and block.tree:
                return f"{block.block_id} – ..."
        return None

    def get_module_code(self, module_name: str, blocks: List[MessageBlockInfo]) -> Optional[str]:
        for block in blocks:
            if block.module_hint == module_name and block.content:
                return block.content
        return None

    def assign_module_to_block(self, block: MessageBlockInfo, module_name: str):
        old_hint = block.module_hint
        block.module_hint = module_name
        logger.info(f"Блок {block.block_id}: {old_hint} -> {module_name}")
        if block.tree and not block.syntax_error:
            self.identifier.collect_from_tree(block.tree, module_name, block_info=block)

    def reset_assignments(self, blocks: List[MessageBlockInfo]):
        for block in blocks:
            block.module_hint = None
        self.module_containers = {}

    def remove_temp_modules(self):
        self.identifier.remove_temp_modules()
        self.module_containers = {}