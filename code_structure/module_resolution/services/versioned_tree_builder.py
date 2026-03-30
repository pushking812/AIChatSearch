# code_structure/module_resolution/services/versioned_tree_builder.py

"""
Построитель версионированного дерева (VersionedNode) из новых блоков.
"""

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

from code_structure.utils.logger import get_logger

logger = get_logger(__name__, level=logging.INFO)


class VersionedTreeBuilder:
    """
    Строит дерево VersionedNode из списка блоков с заполненными code_tree.
    """

    def __init__(self):
        pass

    def build_from_blocks(self, blocks: List[Block]) -> Tuple[Dict[str, VersionedModule], List[Block]]:
        """
        Строит дерево версионированных модулей.

        Args:
            blocks: список блоков (с code_tree, если есть)

        Returns:
            tuple: (словарь {module_name: VersionedModule}, список неразрешённых блоков)
        """
        # 1. Собираем все CodeNode из блоков, у которых есть module_hint
        all_code_nodes: List[CodeNode] = []
        unknown_blocks: List[Block] = []
        for block in blocks:
            # Определяем модуль для блока (пока используем существующий hint)
            module_name = self._resolve_module_hint(block)
            if module_name is None:
                unknown_blocks.append(block)
                continue
            # Получаем дерево узлов блока (если есть)
            if block.code_tree is None:
                continue
            # Обходим дерево и собираем все узлы, которые могут быть версионированы
            self._collect_versionable_nodes(block.code_tree, all_code_nodes, module_name)

        # 2. Группируем узлы по модулям (полный путь модуля)
        grouped_by_module: Dict[str, List[CodeNode]] = defaultdict(list)
        for node in all_code_nodes:
            # Здесь module_name уже определён при сборе
            # Для каждого узла нужно знать его полный путь (модуль + иерархия)
            # Но в CodeNode есть full_path, который включает имя класса и т.д.
            # Нам нужно извлечь именно модуль (первые части пути). Например, если node.full_path = "mypkg.submod.ClassName.method", то модуль = "mypkg.submod"
            # Получаем модуль из node.module_name (передаём при сборе) или из пути.
            # Пока будем использовать переданный module_name (для всех узлов блока один).
            grouped_by_module[module_name].append(node)

        # 3. Для каждого модуля строим VersionedModule и его детей
        result = {}
        for module_name, nodes in grouped_by_module.items():
            vmodule = VersionedModule(module_name)
            self._add_nodes_to_versioned(vmodule, nodes)
            result[module_name] = vmodule

        return result, unknown_blocks

    def _resolve_module_hint(self, block: Block) -> Optional[str]:
        """
        Определяет имя модуля для блока.
        Пока возвращает сохранённый module_hint из метаданных.
        Позже будет использовать стратегии разрешения.
        """
        # Временная заглушка: используем module_hint из метаданных (если есть)
        # В новых блоках пока нет module_hint, поэтому возвращаем None.
        # Позже нужно будет либо сохранять hint в блок, либо получать из контекста.
        # Для итерации 4 просто возвращаем None, чтобы все блоки попали в unknown.
        return None

    def _collect_versionable_nodes(self, node: CodeNode, result: List[CodeNode], module_name: str):
        """
        Рекурсивно собирает узлы, подлежащие версионированию.
        """
        # Добавляем текущий узел, если он должен быть версионирован
        if isinstance(node, (FunctionNode, MethodNode, CodeBlockNode, ImportNode)):
            # Сохраняем module_name как атрибут узла? Можно добавить временное поле.
            # Пока просто добавляем узел, но для группировки по модулям нужна связь.
            result.append(node)
        # Рекурсивно обходим детей
        for child in node.children:
            self._collect_versionable_nodes(child, result, module_name)

    def _add_nodes_to_versioned(self, vmodule: VersionedModule, nodes: List[CodeNode]):
        """
        Добавляет узлы в версионированное дерево.
        """
        # Строим иерархию: для каждого узла находим или создаём родительские контейнеры
        for node in nodes:
            # Получаем путь относительно модуля: node.full_path может содержать полный путь с модулем.
            # Нам нужно отделить модуль от остальной иерархии.
            # Для простоты предположим, что node.full_path начинается с module_name.
            # Тогда parts = node.full_path.split('.') после module_name
            # Например, full_path = "mypkg.submod.ClassName.method", module_name = "mypkg.submod"
            # parts = ["ClassName", "method"]
            path_parts = node.full_path.split('.')
            # Находим индекс, где заканчивается модуль
            # module_parts = module_name.split('.')
            module_parts = vmodule.name.split('.')
            # Сравниваем первые len(module_parts) частей пути
            if path_parts[:len(module_parts)] != module_parts:
                # Не совпадает – возможно, node.full_path не содержит модуль? Пропускаем
                logger.warning(f"Путь {node.full_path} не начинается с модуля {vmodule.name}")
                continue
            # Оставшаяся часть пути – иерархия внутри модуля
            remaining = path_parts[len(module_parts):]
            if not remaining:
                # Сам модуль (не может быть, так как node не модуль)
                continue

            # Спускаемся по дереву, создавая контейнеры
            current = vmodule
            for i, part in enumerate(remaining):
                is_last = (i == len(remaining) - 1)
                # Определяем тип узла, который нужно создать (класс, функция, метод, блок)
                if is_last:
                    # Создаём версионированный узел нужного типа
                    if isinstance(node, ClassNode):
                        # Классы не версионируются – пропускаем? Они не должны попасть в collect, но на всякий случай.
                        continue
                    elif isinstance(node, FunctionNode):
                        vnode = VersionedFunction(part)
                    elif isinstance(node, MethodNode):
                        vnode = VersionedMethod(part)
                    elif isinstance(node, CodeBlockNode):
                        vnode = VersionedCodeBlock(part)
                    elif isinstance(node, ImportNode):
                        vnode = VersionedImport(part)
                    else:
                        # fallback
                        vnode = VersionedNode(part, node.node_type)
                    # Добавляем версию
                    vnode.add_version(node)
                    # Добавляем в текущий контейнер
                    existing = self._find_child(current, part)
                    if existing:
                        # Если уже есть, добавляем версию в существующий
                        existing.add_version(node)
                    else:
                        current.add_child(vnode)
                else:
                    # Промежуточный узел – должен быть классом (или пакетом)
                    # Создаём контейнер класса (или пакета)
                    # Если текущий узел – класс, то создаём VersionedClass
                    # Для простоты пока создаём VersionedClass
                    vnode = VersionedClass(part)
                    existing = self._find_child(current, part)
                    if existing:
                        current = existing
                    else:
                        current.add_child(vnode)
                        current = vnode

    def _find_child(self, parent: VersionedNode, name: str) -> Optional[VersionedNode]:
        """Ищет дочерний узел с заданным именем."""
        for child in parent.children:
            if child.name == name:
                return child
        return None