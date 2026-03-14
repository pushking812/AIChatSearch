# aichat_search/tools/code_structure/core/structure_builder.py

from typing import Dict, List, Optional
import logging
import sys
from aichat_search.tools.code_structure.models.node import Node, ClassNode, FunctionNode, MethodNode, CodeBlockNode
from aichat_search.tools.code_structure.models.block_info import MessageBlockInfo
from aichat_search.tools.code_structure.models.containers import (
    Container, ModuleContainer, ClassContainer, FunctionContainer,
    MethodContainer, CodeBlockContainer, Version
)
from aichat_search.tools.code_structure.core.signature_utils import extract_function_signature

# Настройка логирования
logger = logging.getLogger(__name__)
console = logging.StreamHandler(sys.stdout)
console.setLevel(logging.DEBUG)
console.setFormatter(logging.Formatter('%(asctime)s - BUILDER - %(levelname)s - %(message)s'))
logger.addHandler(console)
logger.setLevel(logging.DEBUG)


class StructureBuilder:
    """Строит и сливает контейнерные структуры."""

    def build_initial_structure(self, module_name: str, base_block: MessageBlockInfo) -> ModuleContainer:
        """Строит начальную структуру из базового блока."""
        logger.info(f"=== build_initial_structure для модуля {module_name} ===")
        logger.info(f"  Базовый блок: {base_block.block_id}")

        module_container = ModuleContainer(module_name)
        if base_block.tree is None:
            logger.warning(f"  Дерево базового блока пустое")
            return module_container

        logger.info(f"  Корневой узел: {base_block.tree.node_type}")
        self._build_from_node(base_block.tree, module_container, base_block, "root")
        return module_container

    def _build_from_node(self, node: Node, parent_container: Container, block_info: MessageBlockInfo, path: str):
        """Рекурсивно строит контейнеры из узла."""
        node_type = node.node_type
        node_name = node.name
        current_path = f"{path}/{node_type}:{node_name}"

        logger.debug(f"  [BUILD] {current_path}")
        logger.debug(f"    parent: {parent_container.node_type}:{parent_container.name}")

        if isinstance(node, ClassNode):
            logger.info(f"    [BUILD] КЛАСС: {node_name}")
            class_container = ClassContainer(node.name)
            parent_container.add_child(class_container)

            for child in node.children:
                self._build_from_node(child, class_container, block_info, f"{current_path}/child")

        elif isinstance(node, FunctionNode):
            has_self, params = extract_function_signature(node)
            logger.info(f"    [BUILD] ФУНКЦИЯ: {node_name}, has_self={has_self}, params={params}")
            logger.debug(f"      parent_container_type={parent_container.node_type}")

            if has_self and parent_container.node_type == "class":
                logger.info(f"      Функция {node_name} с self -> метод в классе {parent_container.name}")
                method_container = MethodContainer(node.name)
                parent_container.add_child(method_container)
                version = Version(node, block_info.block_id, block_info.global_index, block_info.content)
                method_container.add_version(version)
            else:
                logger.info(f"      Функция {node_name} без self или вне класса -> FunctionContainer")
                func_container = FunctionContainer(node.name)
                parent_container.add_child(func_container)
                version = Version(node, block_info.block_id, block_info.global_index, block_info.content)
                func_container.add_version(version)

        elif isinstance(node, MethodNode):
            logger.info(f"    [BUILD] МЕТОД: {node_name}")
            logger.debug(f"      parent_container_type={parent_container.node_type}")

            # Если метод уже внутри класса – добавляем как MethodContainer
            if parent_container.node_type == "class":
                logger.info(f"      Метод {node_name} добавлен в класс {parent_container.name}")
                method_container = MethodContainer(node.name)
                parent_container.add_child(method_container)
                version = Version(node, block_info.block_id, block_info.global_index, block_info.content)
                method_container.add_version(version)
            else:
                # Если метод вне класса, ищем подходящий класс среди детей
                logger.warning(f"      Метод {node_name} вне класса, ищем подходящий класс")
                found = False
                for child in parent_container.children:
                    if child.node_type == "class":
                        logger.info(f"        Найден класс {child.name}, добавляем метод {node_name}")
                        method_container = MethodContainer(node.name)
                        child.add_child(method_container)
                        version = Version(node, block_info.block_id, block_info.global_index, block_info.content)
                        method_container.add_version(version)
                        found = True
                        break
                if not found:
                    logger.warning(f"      Класс не найден, метод {node_name} добавлен как функция")
                    func_container = FunctionContainer(node.name)
                    parent_container.add_child(func_container)
                    version = Version(node, block_info.block_id, block_info.global_index, block_info.content)
                    func_container.add_version(version)

        elif isinstance(node, CodeBlockNode):
            logger.info(f"    [BUILD] БЛОК КОДА")
            block_container = CodeBlockContainer(f"CodeBlock_{len(parent_container.children)}")
            version = Version(node, block_info.block_id, block_info.global_index, block_info.content)
            block_container.add_version(version)
            parent_container.add_child(block_container)

        else:
            logger.warning(f"    [BUILD] НЕИЗВЕСТНЫЙ ТИП: {node_type}")
            for child in node.children:
                self._build_from_node(child, parent_container, block_info, f"{current_path}/child")

    def merge_node_into_container(self, node: Node, container: Container, block_info: MessageBlockInfo, path: str = ""):
        """Сливает узел в существующий контейнер."""
        node_type = node.node_type
        node_name = node.name
        container_type = container.node_type
        container_name = container.name
        current_path = f"{path}/{node_type}:{node_name}" if path else f"{node_type}:{node_name}"

        logger.info(f"=== MERGE {current_path} ===")
        logger.info(f"  Узел: тип={node_type}, имя={node_name}")
        logger.info(f"  Контейнер: тип={container_type}, имя={container_name}")

        if isinstance(node, ClassNode):
            logger.info(f"  Обработка КЛАССА {node_name}")
            class_container = None
            for child in container.children:
                if child.node_type == "class" and child.name == node_name:
                    class_container = child
                    logger.info(f"    Найден существующий класс {node_name}")
                    break
            if class_container is None:
                class_container = ClassContainer(node.name)
                container.add_child(class_container)
                logger.info(f"    Создан новый класс {node_name}")
            for child in node.children:
                self.merge_node_into_container(child, class_container, block_info, f"{current_path}/child")

        elif isinstance(node, FunctionNode):
            logger.info(f"  Обработка ФУНКЦИИ {node_name}")
            has_self, params = extract_function_signature(node)
            logger.info(f"    has_self={has_self}, params={params}")

            # Пытаемся найти подходящий класс, если функция с self
            found_in_class = False
            if has_self:
                for child in container.children:
                    if child.node_type == "class":
                        logger.info(f"    Проверяем класс {child.name} на наличие метода {node_name}")
                        method_container = None
                        for method_child in child.children:
                            if method_child.node_type == "method" and method_child.name == node_name:
                                method_container = method_child
                                logger.info(f"      Найден существующий метод {node_name} в классе {child.name}")
                                break
                        if method_container:
                            version = Version(node, block_info.block_id, block_info.global_index, block_info.content)
                            existing = self._find_version_by_content(method_container.versions, version.cleaned_content)
                            if existing:
                                existing.add_source(block_info.block_id, node.lineno_start, node.lineno_end, block_info.global_index)
                                logger.info(f"      Добавлен источник к версии метода {node_name}")
                            else:
                                method_container.add_version(version)
                                logger.info(f"      Создана новая версия метода {node_name} v{len(method_container.versions)}")
                            found_in_class = True
                            break
                        else:
                            logger.info(f"      Создаём новый метод {node_name} в классе {child.name}")
                            method_container = MethodContainer(node.name)
                            child.add_child(method_container)
                            version = Version(node, block_info.block_id, block_info.global_index, block_info.content)
                            method_container.add_version(version)
                            logger.info(f"      Метод {node_name} создан в классе {child.name}")
                            found_in_class = True
                            break

            if not found_in_class:
                logger.info(f"    Подходящий класс не найден, создаём как функцию")
                func_container = None
                for child in container.children:
                    if child.node_type == "function" and child.name == node_name:
                        func_container = child
                        logger.info(f"    Найдена существующая функция {node_name}")
                        break
                if func_container is None:
                    func_container = FunctionContainer(node.name)
                    container.add_child(func_container)
                    logger.info(f"    Создана новая функция {node_name}")
                version = Version(node, block_info.block_id, block_info.global_index, block_info.content)
                existing = self._find_version_by_content(func_container.versions, version.cleaned_content)
                if existing:
                    existing.add_source(block_info.block_id, node.lineno_start, node.lineno_end, block_info.global_index)
                    logger.info(f"    Добавлен источник к версии функции {node_name}")
                else:
                    func_container.add_version(version)
                    logger.info(f"    Создана новая версия функции {node_name} v{len(func_container.versions)}")

        elif isinstance(node, MethodNode):
            logger.info(f"  Обработка МЕТОДА {node_name}")

            # Если контейнер – класс, ищем метод среди его детей
            if container_type == "class":
                method_container = None
                for child in container.children:
                    if child.node_type == "method" and child.name == node_name:
                        method_container = child
                        logger.info(f"      Найден существующий метод {node_name} в классе {container_name}")
                        break
                if method_container:
                    version = Version(node, block_info.block_id, block_info.global_index, block_info.content)
                    existing = self._find_version_by_content(method_container.versions, version.cleaned_content)
                    if existing:
                        existing.add_source(block_info.block_id, node.lineno_start, node.lineno_end, block_info.global_index)
                        logger.info(f"      Добавлен источник к версии метода {node_name}")
                    else:
                        method_container.add_version(version)
                        logger.info(f"      Создана новая версия метода {node_name} v{len(method_container.versions)}")
                else:
                    logger.info(f"      Создаём новый метод {node_name} в классе {container_name}")
                    method_container = MethodContainer(node.name)
                    container.add_child(method_container)
                    version = Version(node, block_info.block_id, block_info.global_index, block_info.content)
                    method_container.add_version(version)
                    logger.info(f"      Метод {node_name} создан в классе {container_name}")
            else:
                # Контейнер не класс – ищем подходящий класс среди детей
                found = False
                for child in container.children:
                    if child.node_type == "class":
                        logger.info(f"    Проверяем класс {child.name}")
                        method_container = None
                        for method_child in child.children:
                            if method_child.node_type == "method" and method_child.name == node_name:
                                method_container = method_child
                                logger.info(f"      Найден существующий метод {node_name} в классе {child.name}")
                                break
                        if method_container:
                            version = Version(node, block_info.block_id, block_info.global_index, block_info.content)
                            existing = self._find_version_by_content(method_container.versions, version.cleaned_content)
                            if existing:
                                existing.add_source(block_info.block_id, node.lineno_start, node.lineno_end, block_info.global_index)
                                logger.info(f"      Добавлен источник к версии метода {node_name}")
                            else:
                                method_container.add_version(version)
                                logger.info(f"      Создана новая версия метода {node_name} v{len(method_container.versions)}")
                            found = True
                            break
                        else:
                            logger.info(f"      Создаём новый метод {node_name} в классе {child.name}")
                            method_container = MethodContainer(node.name)
                            child.add_child(method_container)
                            version = Version(node, block_info.block_id, block_info.global_index, block_info.content)
                            method_container.add_version(version)
                            logger.info(f"      Метод {node_name} создан в классе {child.name}")
                            found = True
                            break
                if not found:
                    logger.warning(f"    Класс не найден, создаём метод {node_name} как функцию")
                    func_container = None
                    for child in container.children:
                        if child.node_type == "function" and child.name == node_name:
                            func_container = child
                            break
                    if func_container is None:
                        func_container = FunctionContainer(node.name)
                        container.add_child(func_container)
                    version = Version(node, block_info.block_id, block_info.global_index, block_info.content)
                    existing = self._find_version_by_content(func_container.versions, version.cleaned_content)
                    if existing:
                        existing.add_source(block_info.block_id, node.lineno_start, node.lineno_end, block_info.global_index)
                    else:
                        func_container.add_version(version)

        elif isinstance(node, CodeBlockNode):
            logger.info(f"  Обработка БЛОКА КОДА")
            version = Version(node, block_info.block_id, block_info.global_index, block_info.content)
            found = False
            for child in container.children:
                if child.node_type == "code_block":
                    for ver in child.versions:
                        if ver.cleaned_content == version.cleaned_content:
                            ver.add_source(block_info.block_id, node.lineno_start, node.lineno_end, block_info.global_index)
                            logger.info(f"    Добавлен источник к существующему блоку кода")
                            found = True
                            break
                    if found:
                        break
            if not found:
                block_container = CodeBlockContainer(f"CodeBlock_{len(container.children)}")
                block_container.add_version(version)
                container.add_child(block_container)
                logger.info(f"    Создан новый блок кода")

        else:
            logger.warning(f"  НЕИЗВЕСТНЫЙ ТИП УЗЛА: {node_type}")
            for child in node.children:
                self.merge_node_into_container(child, container, block_info, f"{current_path}/child")

    def _find_version_by_content(self, versions: List[Version], cleaned_content: str) -> Optional[Version]:
        """Ищет версию по содержимому."""
        for v in versions:
            if v.cleaned_content == cleaned_content:
                return v
        return None