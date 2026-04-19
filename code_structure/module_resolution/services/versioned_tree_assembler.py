import logging
from typing import Dict, List, Set, Tuple, Union, Optional
from code_structure.models.block import Block
from code_structure.models.code_node import CodeNode, ClassNode, FunctionNode, MethodNode, CodeBlockNode
from code_structure.models.versioned_node import (
    VersionedNode, VersionedModule, VersionedClass, VersionedFunction,
    VersionedMethod, VersionedCodeBlock, VersionedImport, SourceRef, VersionInfo
)
from code_structure.models.registry import BlockRegistry
from code_structure.utils.helpers import clean_code
from .tree_utils import has_self_parameter, extract_class_names
from code_structure.utils.logger import get_logger

logger = get_logger(__name__, level=logging.DEBUG)

class VersionedTreeAssembler:
    def __init__(self, resolved_paths: Dict[str, str], node_type_map: Dict[str, str], imported_paths: Set[str]):
        self.resolved_paths = resolved_paths
        self.node_type_map = node_type_map
        self.imported_paths = imported_paths
        self._version_map: Dict[str, List[VersionInfo]] = {}

    def build_versioned_tree_from_blocks(self, blocks: List[Block]) -> Dict[str, VersionedNode]:
        self._version_map.clear()
        for block in blocks:
            if block.module_hint is None or block.code_tree is None:
                continue
            block_classes = extract_class_names(block.code_tree)
            self._add_block_versions(block.code_tree, block.module_hint, block, block_classes)

        roots = self._build_versioned_from_map()
        self._mark_imported_nodes(roots)
        self._compute_local_nodes(roots)
        self._log_versioned_tree(roots)
        return roots

    def _add_block_versions(self, node: CodeNode, base_path: str, block: Block, block_classes: Set[str]):
        """Основной метод: диспетчер для разных типов узлов."""
        logger.debug(f"  _add_block_versions: type={type(node).__name__}, base_path={base_path}")

        if node.name == 'clear_all_sources':
            pass
        
        if isinstance(node, ClassNode):
            self._process_class_node(node, base_path, block, block_classes)
        elif isinstance(node, (FunctionNode, MethodNode)):
            self._process_function_method_node(node, base_path, block, block_classes)
        elif isinstance(node, CodeBlockNode):
            self._process_code_block_node(node, base_path, block)
        else:
            self._process_other_node(node, base_path, block, block_classes)

    def _process_class_node(self, node: ClassNode, base_path: str, block: Block, block_classes: Set[str]):
        """Обработка узла класса."""
        # Пропускаем вложенный класс с тем же именем
        if base_path.endswith('.' + node.name):
            logger.debug(f"  => Пропускаем вложенный класс {node.name}, обрабатываем детей")
            for child in node.children:
                self._add_block_versions(child, base_path, block, block_classes)
            return

        full_path = f"{base_path}.{node.name}"
        self.node_type_map[full_path] = 'class'
        self._add_version(full_path, node, block)
        for child in node.children:
            self._add_block_versions(child, full_path, block, block_classes)

    def _process_function_method_node(self, node: Union[FunctionNode, MethodNode], base_path: str,
                                      block: Block, block_classes: Set[str]):
        """Обработка функций и методов."""
        is_method = has_self_parameter(node) if isinstance(node, FunctionNode) else True
        is_class_method = isinstance(node, MethodNode) and isinstance(node.parent, ClassNode)
        method_name = node.name

        # Поиск уже существующего пути
        found_path = self._find_existing_path(node, base_path, method_name, is_class_method)

        if found_path:
            self._add_version(found_path, node, block)
            logger.debug(f"      {type(node).__name__} {method_name} взят из _resolved_paths: {found_path}")
            return

        # Создание нового пути
        new_path, node_type = self._create_new_path(node, base_path, block_classes, is_method, is_class_method)
        self.node_type_map[new_path] = node_type
        self._add_version(new_path, node, block)
        logger.debug(f"      Создана {'функция' if node_type=='function' else 'метод'}: {new_path}")

    def _find_existing_path(self, node: Union[FunctionNode, MethodNode], base_path: str,
                            method_name: str, is_class_method: bool) -> Optional[str]:
        """Ищет существующий путь в resolved_paths."""
        if is_class_method:
            # Для метода класса ищем по идентификатору "Класс.метод"
            parent_class = node.parent  # ClassNode
            identifier = f"{parent_class.name}.{method_name}"
            if identifier in self.resolved_paths:
                logger.debug(f"      Найден путь метода класса по идентификатору {identifier}: {self.resolved_paths[identifier]}")
                return self.resolved_paths[identifier]
            return None

        # Для обычных функций / методов-сирот используем старый трёхэтапный поиск
        # 1. Путь с дополнительным сегментом (вложенный класс)
        for ident, fp in self.resolved_paths.items():
            if (fp.startswith(base_path + '.') and
                fp.endswith('.' + method_name) and
                fp.count('.') > base_path.count('.') + 1):
                logger.debug(f"      Найден путь вложенного метода: {fp}")
                return fp
        # 2. Путь без дополнительного сегмента (функция модуля)
        for ident, fp in self.resolved_paths.items():
            if fp.startswith(base_path + '.') and fp.endswith('.' + method_name):
                logger.debug(f"      Найден путь функции модуля: {fp}")
                return fp
        # 3. Поиск по идентификатору class.method
        for ident, fp in self.resolved_paths.items():
            if ident.endswith(f'.{method_name}'):
                logger.debug(f"      Найден общий путь: {fp} (ident={ident})")
                return fp
        return None

    def _create_new_path(self, node: Union[FunctionNode, MethodNode], base_path: str,
                         block_classes: Set[str], is_method: bool, is_class_method: bool) -> Tuple[str, str]:
        """Создаёт новый полный путь и тип узла."""
        method_name = node.name

        if is_class_method:
            # Метод класса – путь "модуль.класс.метод"
            parent_class = node.parent  # ClassNode
            full_path = f"{base_path}.{parent_class.name}.{method_name}"
            node_type = 'method'
            return full_path, node_type

        # Для обычных функций и методов-сирот
        if block_classes and is_method:
            class_in_base = any(base_path.endswith('.' + cls) for cls in block_classes)
            if class_in_base:
                full_path = f"{base_path}.{method_name}"
            else:
                first_class = next(iter(block_classes))
                full_path = f"{base_path}.{first_class}.{method_name}"
        else:
            full_path = f"{base_path}.{method_name}"

        node_type = 'method' if is_method else 'function'
        return full_path, node_type

    def _process_code_block_node(self, node: CodeBlockNode, base_path: str, block: Block):
        """Обработка блока кода."""
        full_path = f"{base_path}._code_block"
        self.node_type_map[full_path] = 'code_block'
        self._add_version(full_path, node, block)

    def _process_other_node(self, node: CodeNode, base_path: str, block: Block, block_classes: Set[str]):
        """Обработка узлов, не являющихся классами, функциями/методами или блоками кода (например, импорты, комментарии)."""
        for child in node.children:
            self._add_block_versions(child, base_path, block, block_classes)

    def _add_version(self, full_path: str, code_node: CodeNode, block: Block):
        raw_code = code_node.get_raw_code()
        norm = clean_code(raw_code)
        src = SourceRef(block.id, code_node.start_line, code_node.end_line, block.timestamp)
        versions = self._version_map.setdefault(full_path, [])
        for ver in versions:
            if ver.normalized_code == norm:
                ver.add_source(src)
                logger.debug(f"      Добавлен источник в существующую версию {full_path}: {src.block_id}")
                return
        versions.append(VersionInfo(norm, [src]))
        logger.debug(f"      Создана новая версия для {full_path} (всего версий: {len(versions)})")

    def _build_versioned_from_map(self) -> Dict[str, VersionedNode]:
        all_nodes = {}
        # Сначала создаём все узлы
        for full_path in sorted(self._version_map.keys(), key=len):
            parts = full_path.split('.')
            current = None
            for i, part in enumerate(parts):
                parent_path = '.'.join(parts[:i]) if i > 0 else ''
                cur_path = '.'.join(parts[:i+1])
                if cur_path not in all_nodes:
                    node_type = self.node_type_map.get(cur_path, self._guess_node_type(cur_path))
                    node = self._create_versioned_node(part, node_type)
                    all_nodes[cur_path] = node
                    if parent_path and parent_path in all_nodes:
                        all_nodes[parent_path].add_child(node)
                current = all_nodes[cur_path]
            if current and full_path in self._version_map:
                current.versions = self._version_map[full_path]
        
        # Удаляем узлы, которые являются дубликатами (родительский узел имеет то же имя и тип)
        to_remove = []
        for path, node in all_nodes.items():
            if node.parent and node.parent.name == node.name and node.parent.node_type == node.node_type:
                # Переносим детей в родительский узел
                for child in node.children:
                    node.parent.add_child(child)
                to_remove.append(path)
        for path in to_remove:
            del all_nodes[path]
            logger.debug(f"  Удалён дублирующий узел: {path}")
        
        roots = {path: node for path, node in all_nodes.items() if node.parent is None}
        return roots

    @staticmethod
    def _guess_node_type(path: str) -> str:
        last = path.split('.')[-1]
        if last and last[0].isupper():
            return 'class'
        return 'module'

    @staticmethod
    def _create_versioned_node(name: str, node_type: str) -> VersionedNode:
        if node_type == 'class':
            return VersionedClass(name)
        elif node_type == 'function':
            return VersionedFunction(name)
        elif node_type == 'method':
            return VersionedMethod(name)
        elif node_type == 'code_block':
            return VersionedCodeBlock(name)
        elif node_type == 'import':
            return VersionedImport(name)
        elif node_type == 'module':
            return VersionedModule(name)
        else:
            return VersionedNode(name, node_type)

    def _mark_imported_nodes(self, roots: Dict[str, VersionedNode]):
        for path, node in roots.items():
            self._mark_imported_recursive(node, path)

    def _mark_imported_recursive(self, node: VersionedNode, full_path: str):
        if full_path in self.imported_paths:
            node.is_imported = True
        for child in node.children:
            child_full_path = f"{full_path}.{child.name}" if full_path else child.name
            self._mark_imported_recursive(child, child_full_path)

    def _compute_local_nodes(self, roots: Dict[str, VersionedNode]):
        for node in roots.values():
            self._compute_local_recursive(node)

    def _compute_local_recursive(self, node: VersionedNode):
        if node.versions:
            node.is_local = True
            parent = node.parent
            while parent:
                parent.is_local = True
                parent = parent.parent
        for child in node.children:
            self._compute_local_recursive(child)

    def _log_versioned_tree(self, roots: Dict[str, VersionedNode]):
        if not logger.isEnabledFor(logging.DEBUG):
            return
        logger.debug("=== Сводное дерево (VersionedNode) ===")
        for root in roots.values():
            self._log_versioned_node(root, 0)

    def _log_versioned_node(self, node: VersionedNode, indent: int):
        prefix = "  " * indent
        version_info = f" versions={len(node.versions)}" if node.versions else ""
        logger.debug(f"{prefix}- {node.name} [{node.node_type}]{version_info} -> {node.full_path}")
        for child in node.children:
            self._log_versioned_node(child, indent + 1)