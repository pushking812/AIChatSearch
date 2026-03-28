# aichat_search/tools/code_structure/core/node_processor.py

import logging
from abc import ABC, abstractmethod
from typing import Optional, Union, List, Tuple

from aichat_search.tools.code_structure.models.node import (
    Node, ClassNode, FunctionNode, MethodNode, CodeBlockNode
)
from aichat_search.tools.code_structure.models.containers import (
    Container, ClassContainer, FunctionContainer, MethodContainer, CodeBlockContainer, Version,
    ImportContainer
)
from aichat_search.tools.code_structure.models.block_info import MessageBlockInfo
from aichat_search.tools.code_structure.core.signature_utils import extract_function_signature
from aichat_search.tools.code_structure.core.version_comparator import VersionComparator

from aichat_search.tools.code_structure.utils.logger import get_logger
logger = get_logger(__name__, level = logging.WARNING)


class BaseNodeProcessor(ABC):
    """Базовый класс для процессоров, обрабатывающих узлы AST."""

    def __init__(self, builder):
        self.builder = builder

    def process(self, node: Node, container: Container, block_info: MessageBlockInfo, path: str = "") -> None:
        """Обрабатывает узел дерева и добавляет его в контейнер."""
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

    def _process_class(self, node: ClassNode, container: Container, block_info: MessageBlockInfo, path: str):
        """Обрабатывает класс: создаёт контейнер класса и рекурсивно обрабатывает детей."""
        class_container = self._create_class_container(node)
        container.add_child(class_container)
        for child in node.children:
            self.process(child, class_container, block_info, f"{path}/class:{node.name}")

    @abstractmethod
    def _process_function(self, node: FunctionNode, container: Container, block_info: MessageBlockInfo, path: str):
        """Обрабатывает функцию (должен быть переопределён в наследниках)."""
        pass

    @abstractmethod
    def _process_method(self, node: MethodNode, container: Container, block_info: MessageBlockInfo, path: str):
        """Обрабатывает метод (должен быть переопределён в наследниках)."""
        pass

    def _process_code_block(self, node: CodeBlockNode, container: Container, block_info: MessageBlockInfo, path: str):
        """Обрабатывает блок кода: разделяет импорты и обычный код."""
        if container.node_type != "module":
            block_container = self._create_code_block_container(container)
            self._add_version_to_container(block_container, node, block_info)
            container.add_child(block_container)
            return

        fragment_lines = self._get_block_fragment(node, block_info)
        if not fragment_lines:
            return

        import_lines = []
        code_lines = []
        for line in fragment_lines:
            stripped = line.strip()
            if stripped.startswith(('import ', 'from ')):
                import_lines.append(line)
            else:
                code_lines.append(line)

        if import_lines:
            import_container = None
            for child in container.children:
                if isinstance(child, ImportContainer):
                    import_container = child
                    break
            if import_container is None:
                import_container = ImportContainer()
                container.add_child(import_container)

            first_line = import_lines[0]
            last_line = import_lines[-1]
            start_idx = fragment_lines.index(first_line)
            end_idx = fragment_lines.index(last_line)
            temp_node = CodeBlockNode(
                name=node.name,
                line_range=f"{node.lineno_start + start_idx}-{node.lineno_start + end_idx}",
                lineno_start=node.lineno_start + start_idx,
                lineno_end=node.lineno_start + end_idx
            )
            self._add_version_to_container(import_container, temp_node, block_info)

        if code_lines:
            block_container = self._create_code_block_container(container)
            first_line = code_lines[0]
            last_line = code_lines[-1]
            start_idx = fragment_lines.index(first_line)
            end_idx = fragment_lines.index(last_line)
            temp_node = CodeBlockNode(
                name=node.name,
                line_range=f"{node.lineno_start + start_idx}-{node.lineno_start + end_idx}",
                lineno_start=node.lineno_start + start_idx,
                lineno_end=node.lineno_start + end_idx
            )
            self._add_version_to_container(block_container, temp_node, block_info)
            container.add_child(block_container)

    def _process_children(self, node: Node, container: Container, block_info: MessageBlockInfo, path: str):
        """Рекурсивно обрабатывает детей узла."""
        for child in node.children:
            self.process(child, container, block_info, f"{path}/child")

    # ---------- Вспомогательные методы ----------
    def _get_block_fragment(self, node: CodeBlockNode, block_info: MessageBlockInfo) -> List[str]:
        if node.lineno_start is None or node.lineno_end is None:
            return []
        lines = block_info.content.splitlines()
        start = max(0, node.lineno_start - 1)
        end = min(len(lines), node.lineno_end)
        return lines[start:end]

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
        has_self, _ = extract_function_signature(node)
        return has_self

    def _add_version_to_container(
        self,
        container: Union[FunctionContainer, MethodContainer, CodeBlockContainer, ImportContainer],
        node,
        block_info: MessageBlockInfo
    ):
        version = self._create_version(node, block_info)
        existing = VersionComparator.find_existing(container.versions, version)
        if existing:
            existing.add_source(block_info.block_id, node.lineno_start, node.lineno_end, block_info.global_index)
        else:
            container.add_version(version)

    # ---------- Методы поиска ----------
    def _find_class_by_name(self, container: Container, class_name: str) -> Optional[ClassContainer]:
        for child in container.children:
            if child.node_type == "class" and child.name == class_name:
                return child
        return None

    def _find_function_by_name(self, container: Container, func_name: str) -> Optional[FunctionContainer]:
        for child in container.children:
            if child.node_type == "function" and child.name == func_name:
                return child
        return None

    def _find_method_in_class(self, class_container: ClassContainer, method_name: str) -> Optional[MethodContainer]:
        for child in class_container.children:
            if child.node_type == "method" and child.name == method_name:
                return child
        return None


class InitialBuildProcessor(BaseNodeProcessor):
    """Процессор для начального построения структуры (первый блок модуля)."""

    def __init__(self, builder):
        super().__init__(builder)

    def _process_function(self, node: FunctionNode, container: Container, block_info: MessageBlockInfo, path: str):
        has_self = self._has_self(node)
        if has_self:
            # Ищем класс по имени (не по наличию метода)
            target_class = self._find_class_by_name(container, node.name)
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
        if container.node_type == "class":
            method_container = self._find_method_in_class(container, node.name)
            if method_container is None:
                method_container = self._create_method_container(node)
                container.add_child(method_container)
            self._add_version_to_container(method_container, node, block_info)
        else:
            target_class = self._find_class_by_name(container, node.name)
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


class MergeProcessor(BaseNodeProcessor):
    """Процессор для слияния дополнительных блоков в существующую структуру."""

    def __init__(self, builder):
        super().__init__(builder)

    def _process_class(self, node: ClassNode, container: Container, block_info: MessageBlockInfo, path: str):
        # В отличие от начального процессора, здесь мы ищем существующий контейнер класса
        class_container = self._find_class_by_name(container, node.name)
        if class_container is None:
            class_container = self._create_class_container(node)
            container.add_child(class_container)
        for child in node.children:
            self.process(child, class_container, block_info, f"{path}/class:{node.name}")

    def _process_function(self, node: FunctionNode, container: Container, block_info: MessageBlockInfo, path: str):
        has_self = self._has_self(node)
        if has_self:
            target_class = self._find_class_by_name(container, node.name)
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
        if container.node_type == "class":
            method_container = self._find_method_in_class(container, node.name)
            if method_container is None:
                method_container = self._create_method_container(node)
                container.add_child(method_container)
            self._add_version_to_container(method_container, node, block_info)
        else:
            target_class = self._find_class_by_name(container, node.name)
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