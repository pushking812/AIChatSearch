# code_structure/module_resolution/services/versioned_tree_builder.py

import logging
from typing import List, Dict, Optional, Tuple
from collections import defaultdict

from code_structure.models.block import Block
from code_structure.models.code_node import (
    CodeNode, ClassNode, FunctionNode, MethodNode, CodeBlockNode, ImportNode
)
from code_structure.models.versioned_node import (
    VersionedNode, VersionedModule, VersionedClass, VersionedFunction,
    VersionedMethod, VersionedCodeBlock, VersionedImport
)
from code_structure.module_resolution.core.new_resolution_strategies import (
    ClassStrategy, MethodStrategy, FunctionStrategy, ImportStrategy
)
from code_structure.module_resolution.core.module_identifier import ModuleIdentifier
from code_structure.imports.services.import_service import ImportService
from code_structure.utils.logger import get_logger

logger = get_logger(__name__)


class VersionedTreeBuilder:
    def __init__(self):
        self.module_identifier = ModuleIdentifier()
        self.strategies = [
            ClassStrategy(),
            MethodStrategy(),
            FunctionStrategy(),
            ImportStrategy()
        ]

    def build_from_blocks(self, blocks: List[Block]) -> Tuple[Dict[str, VersionedModule], List[Block]]:
        """Строит дерево версионированных модулей из блоков."""
        # 1. Определяем module_hint для каждого блока
        for block in blocks:
            if block.module_hint is None:
                module_hint = self._resolve_module_hint(block)
                if module_hint:
                    # Создаём новый блок с заполненным module_hint
                    # (т.к. Block неизменяемый)
                    block = Block(
                        id=block.id,
                        chat=block.chat,
                        message_pair=block.message_pair,
                        language=block.language,
                        content=block.content,
                        block_idx=block.block_idx,
                        global_index=block.global_index,
                        code_tree=block.code_tree,
                        module_hint=module_hint
                    )
                    # Обновляем в реестре (нужно обновить ссылку)
                    from code_structure.models.registry import BlockRegistry
                    BlockRegistry().register(block)
            # Если есть module_hint, собираем CodeNode
            if block.module_hint and block.code_tree:
                self._collect_nodes(block.code_tree, block.module_hint)

        # 2. Группируем узлы по модулям (уже есть в module_identifier)
        #    Используем существующие структуры ModuleIdentifier для группировки
        #    Но нам нужно построить VersionedNode дерево из module_identifier
        versioned_roots = {}
        for mod_name in self.module_identifier.get_all_module_names():
            vmodule = VersionedModule(mod_name)
            # Заполняем классы и методы
            module_info = self.module_identifier.get_module_info(mod_name)
            if module_info:
                vmodule.is_imported = module_info.is_imported
                # Классы
                for class_name, class_info in module_info.classes.items():
                    vclass = VersionedClass(class_name)
                    # Методы класса
                    for method_name, method_info in class_info.methods.items():
                        vmethod = VersionedMethod(method_name)
                        # Добавляем версии метода
                        for version in method_info.versions:
                            # version - это объект Version (старый). Нужно преобразовать в новую модель?
                            # Пока пропускаем. В будущем нужно будет заменить старые версии на новые.
                            # Временно: просто создаём VersionedMethod без версий.
                            pass
                        vclass.add_child(vmethod)
                    vmodule.add_child(vclass)
                # Функции верхнего уровня
                for func_name, func_info in module_info.functions.items():
                    vfunc = VersionedFunction(func_name)
                    # Добавляем версии
                    vmodule.add_child(vfunc)
            versioned_roots[mod_name] = vmodule

        # 3. Неразрешённые блоки
        unknown_blocks = [b for b in blocks if b.module_hint is None]
        return versioned_roots, unknown_blocks

    def _resolve_module_hint(self, block: Block) -> Optional[str]:
        """Применяет стратегии для определения module_hint блока."""
        if not block.code_tree:
            return None
        # Контекст для стратегий (пока пустой, но позже можно добавить ModuleIdentifier)
        context = {'identifier': self.module_identifier}
        for strategy in self.strategies:
            module = strategy.resolve(block.code_tree, context)
            if module:
                logger.debug(f"Блок {block.id} определён как {module} по {strategy.__class__.__name__}")
                return module
        return None

    def _collect_nodes(self, node: CodeNode, module_name: str):
        """Собирает информацию о классах/функциях в ModuleIdentifier."""
        # Имитация старого collect_from_tree
        # Вместо этого нужно заполнять ModuleIdentifier, но он пока не умеет работать с CodeNode.
        # Для простоты пока пропустим. В следующих итерациях доработаем.
        pass