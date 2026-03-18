# aichat_search/tools/code_structure/core/node_processor.py

import logging
from abc import ABC, abstractmethod
from typing import Optional, Union

from aichat_search.tools.code_structure.models.node import (
    Node, ClassNode, FunctionNode, MethodNode, CodeBlockNode
)
from aichat_search.tools.code_structure.models.containers import (
    Container, ClassContainer, FunctionContainer, MethodContainer, CodeBlockContainer, Version
)
from aichat_search.tools.code_structure.models.block_info import MessageBlockInfo
from aichat_search.tools.code_structure.core.signature_utils import extract_function_signature
from aichat_search.tools.code_structure.core.version_comparator import VersionComparator

logger = logging.getLogger(__name__)


class BaseNodeProcessor(ABC):
    """
    Базовый процессор для обхода узлов AST и построения/слияния контейнеров.

    Реализует шаблонный метод process, который диспетчеризует по типу узла.
    Конкретная логика для каждого типа узла реализуется в наследниках.

    Attributes:
        builder: ссылка на экземпляр StructureBuilder
    """

    def __init__(self, builder):
        self.builder = builder

    def process(self, node: Node, container: Container, block_info: MessageBlockInfo, path: str = "") -> None:
        """
        Основной метод обработки узла. Вызывает соответствующий защищённый метод в зависимости от типа узла.

        Args:
            node: узел AST
            container: контейнер, в который добавляется узел
            block_info: информация о блоке, из которого получен узел
            path: путь для логирования (отладочная информация)
        """
        if isinstance(node, ClassNode):
            self._process_class(node, container, block_info, path)
        elif isinstance(node, FunctionNode):
            self._process_function(node, container, block_info, path)
        elif isinstance(node, MethodNode):
            self._process_method(node, container, block_info, path)
        elif isinstance(node, CodeBlockNode):
            self._process_code_block(node, container, block_info, path)
        else:
            self._process_children(node, container, block_info, path)

    # Защищённые методы для переопределения

    def _process_class(self, node: ClassNode, container: Container, block_info: MessageBlockInfo, path: str):
        """
        Обработка класса. Создаёт контейнер и рекурсивно обрабатывает детей.
        """
        class_container = self._create_class_container(node)
        container.add_child(class_container)
        for child in node.children:
            self.process(child, class_container, block_info, f"{path}/class:{node.name}")

    @abstractmethod
    def _process_function(self, node: FunctionNode, container: Container, block_info: MessageBlockInfo, path: str):
        """Обработка функции. Должна быть реализована в наследниках."""
        pass

    @abstractmethod
    def _process_method(self, node: MethodNode, container: Container, block_info: MessageBlockInfo, path: str):
        """Обработка метода. Должна быть реализована в наследниках."""
        pass

    def _process_code_block(self, node: CodeBlockNode, container: Container, block_info: MessageBlockInfo, path: str):
        """
        Обработка блока кода. Создаёт контейнер и версию.
        """
        block_container = self._create_code_block_container(container)
        self._add_version_to_container(block_container, node, block_info)
        container.add_child(block_container)

    def _process_children(self, node: Node, container: Container, block_info: MessageBlockInfo, path: str):
        """Рекурсивная обработка дочерних узлов (для узлов неизвестного типа)."""
        for child in node.children:
            self.process(child, container, block_info, f"{path}/child")

    # Вспомогательные методы

    def _create_class_container(self, node: ClassNode) -> ClassContainer:
        return ClassContainer(node.name)

    def _create_function_container(self, node: FunctionNode) -> FunctionContainer:
        return FunctionContainer(node.name)

    def _create_method_container(self, node: MethodNode) -> MethodContainer:
        return MethodContainer(node.name)

    def _create_code_block_container(self, parent: Container) -> CodeBlockContainer:
        return CodeBlockContainer(f"CodeBlock_{len(parent.children)}")

    def _create_version(self, node, block_info: MessageBlockInfo) -> Version:
        return Version(node, block_info.block_id, block_info.global_index, block_info.content)

    def _has_self(self, node: FunctionNode) -> bool:
        """Определяет, есть ли в функции параметр self."""
        has_self, _ = extract_function_signature(node)
        return has_self

    def _add_version_to_container(
        self,
        container: Union[FunctionContainer, MethodContainer, CodeBlockContainer],
        node,
        block_info: MessageBlockInfo
    ):
        """
        Добавляет версию в контейнер, проверяя наличие дубликата.
        Если версия уже существует, добавляет источник к существующей.
        """
        version = self._create_version(node, block_info)
        existing = VersionComparator.find_existing(container.versions, version)
        if existing:
            existing.add_source(block_info.block_id, node.lineno_start, node.lineno_end, block_info.global_index)
        else:
            container.add_version(version)

    # Методы поиска (линейный обход)

    def _find_class_by_method_name(self, container: Container, method_name: str) -> Optional[ClassContainer]:
        """
        Ищет среди детей контейнера класс, у которого уже есть метод с заданным именем.
        Возвращает первый найденный класс или None.
        """
        for child in container.children:
            if child.node_type == "class":
                for method in child.children:
                    if method.node_type == "method" and method.name == method_name:
                        return child
        return None

    def _find_class_by_name(self, container: Container, class_name: str) -> Optional[ClassContainer]:
        """Ищет класс с указанным именем среди детей контейнера."""
        for child in container.children:
            if child.node_type == "class" and child.name == class_name:
                return child
        return None

    def _find_function_by_name(self, container: Container, func_name: str) -> Optional[FunctionContainer]:
        """Ищет функцию с указанным именем среди детей контейнера."""
        for child in container.children:
            if child.node_type == "function" and child.name == func_name:
                return child
        return None

    def _find_method_in_class(self, class_container: ClassContainer, method_name: str) -> Optional[MethodContainer]:
        """Ищет метод с указанным именем в классе."""
        for child in class_container.children:
            if child.node_type == "method" and child.name == method_name:
                return child
        return None


class InitialBuildProcessor(BaseNodeProcessor):
    """
    Процессор для первоначального построения структуры модуля из базового блока.
    """

    def __init__(self, builder):
        super().__init__(builder)

    def _process_function(self, node: FunctionNode, container: Container, block_info: MessageBlockInfo, path: str):
        has_self = self._has_self(node)
        if has_self:
            # Ищем класс, в котором уже есть метод с таким именем
            target_class = self._find_class_by_method_name(container, node.name)
            if target_class:
                # Прикрепляем как метод к найденному классу
                method_container = self._find_method_in_class(target_class, node.name)
                if method_container is None:
                    method_container = self._create_method_container(node)
                    target_class.add_child(method_container)
                self._add_version_to_container(method_container, node, block_info)
            else:
                # Нет подходящего класса — создаём как функцию
                func_container = self._find_function_by_name(container, node.name)
                if func_container is None:
                    func_container = self._create_function_container(node)
                    container.add_child(func_container)
                self._add_version_to_container(func_container, node, block_info)
        else:
            # Функция без self — обычная функция
            func_container = self._find_function_by_name(container, node.name)
            if func_container is None:
                func_container = self._create_function_container(node)
                container.add_child(func_container)
            self._add_version_to_container(func_container, node, block_info)

    def _process_method(self, node: MethodNode, container: Container, block_info: MessageBlockInfo, path: str):
        # Метод должен быть помещён в класс
        if container.node_type == "class":
            # Уже находимся внутри класса
            method_container = self._find_method_in_class(container, node.name)
            if method_container is None:
                method_container = self._create_method_container(node)
                container.add_child(method_container)
            self._add_version_to_container(method_container, node, block_info)
        else:
            # Метод вне класса — ищем подходящий класс среди детей
            target_class = self._find_class_by_method_name(container, node.name)
            if target_class:
                method_container = self._find_method_in_class(target_class, node.name)
                if method_container is None:
                    method_container = self._create_method_container(node)
                    target_class.add_child(method_container)
                self._add_version_to_container(method_container, node, block_info)
            else:
                # Не нашли класс — создаём как функцию (логирование предупреждения)
                logger.warning(f"Метод {node.name} вне класса и подходящий класс не найден, создаём как функцию")
                func_container = self._find_function_by_name(container, node.name)
                if func_container is None:
                    func_container = FunctionContainer(node.name)
                    container.add_child(func_container)
                self._add_version_to_container(func_container, node, block_info)


class MergeProcessor(BaseNodeProcessor):
    """
    Процессор для слияния дополнительных блоков в уже существующую структуру.
    """

    def __init__(self, builder):
        super().__init__(builder)

    def _process_class(self, node: ClassNode, container: Container, block_info: MessageBlockInfo, path: str):
        # Ищем существующий класс с таким именем
        class_container = self._find_class_by_name(container, node.name)
        if class_container is None:
            class_container = self._create_class_container(node)
            container.add_child(class_container)
        for child in node.children:
            self.process(child, class_container, block_info, f"{path}/class:{node.name}")

    def _process_function(self, node: FunctionNode, container: Container, block_info: MessageBlockInfo, path: str):
        has_self = self._has_self(node)
        order = self.builder._get_block_order(block_info)  # используем для логирования
        if has_self:
            target_class = self._find_class_by_method_name(container, node.name)
            if target_class:
                method_container = self._find_method_in_class(target_class, node.name)
                if method_container is None:
                    method_container = self._create_method_container(node)
                    target_class.add_child(method_container)
                self._add_version_to_container(method_container, node, block_info)
            else:
                func_container = self._find_function_by_name(container, node.name)
                if func_container is None:
                    func_container = self._create_function_container(node)
                    container.add_child(func_container)
                self._add_version_to_container(func_container, node, block_info)
        else:
            func_container = self._find_function_by_name(container, node.name)
            if func_container is None:
                func_container = self._create_function_container(node)
                container.add_child(func_container)
            self._add_version_to_container(func_container, node, block_info)

    def _process_method(self, node: MethodNode, container: Container, block_info: MessageBlockInfo, path: str):
        order = self.builder._get_block_order(block_info)  # для логирования
        if container.node_type == "class":
            method_container = self._find_method_in_class(container, node.name)
            if method_container is None:
                method_container = self._create_method_container(node)
                container.add_child(method_container)
            self._add_version_to_container(method_container, node, block_info)
        else:
            target_class = self._find_class_by_method_name(container, node.name)
            if target_class:
                method_container = self._find_method_in_class(target_class, node.name)
                if method_container is None:
                    method_container = self._create_method_container(node)
                    target_class.add_child(method_container)
                self._add_version_to_container(method_container, node, block_info)
            else:
                logger.warning(f"Метод {node.name} вне класса и подходящий класс не найден, создаём как функцию")
                func_container = self._find_function_by_name(container, node.name)
                if func_container is None:
                    func_container = FunctionContainer(node.name)
                    container.add_child(func_container)
                self._add_version_to_container(func_container, node, block_info)

    def _process_code_block(self, node: CodeBlockNode, container: Container, block_info: MessageBlockInfo, path: str):
        version = self._create_version(node, block_info)
        found = False
        for child in container.children:
            if child.node_type == "code_block":
                existing = VersionComparator.find_existing(child.versions, version)
                if existing:
                    existing.add_source(block_info.block_id, node.lineno_start, node.lineno_end, block_info.global_index)
                    found = True
                    break
        if not found:
            block_container = self._create_code_block_container(container)
            block_container.add_version(version)
            container.add_child(block_container)